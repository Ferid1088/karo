"""Devin API (v1) als asynchroner KI-Anbieter.

Vertrag (derselbe wie im Lehrplan-Dienst, siehe karo-curriculum-team
`kcteam/providers/devin.py`):

- `POST /v1/sessions` legt eine Session an und liefert sofort eine
  `session_id`; das Ergebnis liegt erst später als `structured_output`
  unter `GET /v1/sessions/{id}`.
- `start()` legt die Session an, `poll()` fragt sie ab. API-Zustände
  werden auf die neutralen `AIStatus`-Werte übersetzt:
  `working` usw. → `running`, `finished` → `completed`,
  `blocked` → einmal nachfassen (`/message`), sonst `failed`,
  `expired` usw. → einmal neu starten, dann `failed`.

An Devin geht nur Text — der geschrubbte Auftrag samt Schema. Der Prompt
wird nie geloggt, der Schlüssel nie: er steckt ausschließlich im
Authorization-Header und kommt nur aus der Umgebungsvariablen
`DEVIN_API_KEY` — niemals aus `config.json`.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from ... import config
from ..base import AIError, AISetupError
from ..http import api_request
from ..types import AIRequest, AIRun, STATUS_COMPLETED, STATUS_FAILED, \
    STATUS_PENDING, STATUS_RUNNING

log = logging.getLogger("karo.ai.devin")

# Devin hat eine VM mit Werkzeugen — die Session soll nichts davon benutzen.
# Der Auftrag kommt sonst zurück mit „habe eine Datei angelegt" statt JSON.
_PREAMBLE = """Du erzeugst Inhalte für eine Kinder-Lern-App — als reiner Inhalts-Generator.

ARBEITSREGELN, strikt:
- Liefere ausschließlich das geforderte JSON-Ergebnis als structured output.
- Keine Code-Änderungen, keine Dateien, kein Repository, keine Git-Aktionen, keine Shell-Befehle.
- Keine Rückfragen: fehlende Angaben ergänzt du fachlich sinnvoll.
- Keine erfundenen oder echten personenbezogenen Daten.
- Das Ergebnis muss exakt dem im Prompt genannten JSON-Schema entsprechen.
"""

_WEB_ZUSATZ = ("Für diese Aufgabe ist die Websuche ausdrücklich erlaubt und "
               "erwünscht — Datei-, Git- und Shell-Aktionen bleiben trotzdem "
               "verboten.")

_NUDGE = ("Bitte ohne Rückfragen weiterarbeiten und das geforderte JSON-Ergebnis jetzt als "
          "structured output abgeben. Es sind keinerlei Datei-, Git- oder Shell-Aktionen nötig.")

_BASE_URL = "https://api.devin.ai/v1"

#: Statuswerte der v1-API, bei denen die Session noch arbeitet.
_LAEUFT = {"working", "running", "suspend_requested", "resumed",
           "resume_requested", "queued", "new"}
#: Danach wird die Session aufgegeben — sonst wartet ein Auftrag für immer.
_FERTIG, _BLOCKIERT = "finished", "blocked"


class DevinProvider:
    """Adapter für `api.devin.ai` — Sessions statt Chat-Anfragen."""

    name = "devin"
    display_name = "Devin"
    secret_env = "DEVIN_API_KEY"

    def __init__(self, timeout: float | None = None) -> None:
        ops = config.ops()
        self.base_url = (ops.ai_devin_base_url or _BASE_URL).rstrip("/")
        self.poll_seconds = ops.ai_poll_seconds
        self.max_run_seconds = ops.ai_max_run_seconds
        self.timeout_s = timeout if timeout is not None \
            else ops.ai_http_timeout_seconds
        self.max_restarts = ops.ai_max_restarts
        self.max_acu = ops.ai_devin_max_acu
        self._key: str | None = None

    # ------------------------------------------------------------- HTTP
    def _api(self, method: str, path: str, payload: dict | None = None) -> dict:
        if self._key is None:
            self._key = os.environ.get(self.secret_env)
            if not self._key:
                raise AISetupError(
                    f"{self.secret_env} fehlt: als Umgebungsvariable setzen "
                    "(siehe .env.example).")
        return api_request(self.display_name, method, self.base_url, path,
                           headers={"Authorization": f"Bearer {self._key}"},
                           payload=payload, timeout=self.timeout_s)

    # ------------------------------------------------------------- Devin-Aktionen
    def _create(self, request: AIRequest) -> str:
        """Session anlegen. Gibt die session_id zurück."""
        preamble = _PREAMBLE
        if request.web_search or request.web_fetch:
            preamble += "\n" + _WEB_ZUSATZ + "\n"
        payload: dict[str, Any] = {
            "prompt": (preamble + "\n\n" + request.system_prompt +
                       "\n\n## Aufgabe\n" + request.user_prompt),
            "idempotent": True,           # ein Create-Timeout legt keine zweite Session an
            "unlisted": True,
            "title": ("karo " + (request.purpose or "aufruf"))[:120],
            "tags": ["karo", request.purpose or "aufruf"][:8],
            "secret_ids": [],             # die Session bekommt keinerlei hinterlegte Zugänge
            "knowledge_ids": [],          # und kein Organisations-Wissen fremder Aufträge
        }
        schema = request.schema
        if isinstance(schema, dict) and schema and \
                len(json.dumps(schema, default=str)) <= 60_000:
            payload["structured_output_schema"] = schema   # v1: JSON Schema (Draft 7), max 64 KB
        if self.max_acu:
            payload["max_acu_limit"] = int(self.max_acu)
        try:
            info = self._api("POST", "/sessions", payload)
        except AIError as exc:
            # Lehnt die API das Schema ab, lieber ohne es senden — die
            # Schemavorgabe steht ohnehin im Prompt und die lokale Prüfung bleibt.
            if "structured_output_schema" in payload and "422" in str(exc):
                payload.pop("structured_output_schema")
                info = self._api("POST", "/sessions", payload)
            else:
                raise
        sid = info.get("session_id")
        if not sid:
            raise AIError("Devin API: Antwort ohne session_id", retryable=False)
        return sid

    # ------------------------------------------------------------- Schnittstelle
    def verify(self) -> str:
        """Billige Zugangsprobe: Session-Liste abrufen, keine Session anlegen."""
        self._api("GET", "/sessions?limit=1")
        return self.name

    def start(self, request: AIRequest) -> AIRun:
        sid = self._create(request)
        log.info("ai_request_started run_id=%s purpose=%s provider=devin",
                 sid, request.purpose)
        return AIRun(provider=self.name, run_id=sid, status=STATUS_PENDING)

    def poll(self, run: AIRun, request: AIRequest) -> AIRun:
        sid = run.run_id
        if run.age_seconds > self.max_run_seconds:
            run.status = STATUS_FAILED
            run.error = f"Zeitfenster von {self.max_run_seconds}s überschritten"
            log.warning("ai_request_failed run_id=%s purpose=%s error=zeitfenster",
                        sid, request.purpose)
            return run

        info = self._api("GET", f"/sessions/{sid}")
        state = str(info.get("status_enum") or info.get("status") or "working").lower()
        log.info("ai_request_pending run_id=%s status=%s purpose=%s",
                 sid, state, request.purpose)

        out = info.get("structured_output")
        if state == _FERTIG or (state == _BLOCKIERT and isinstance(out, dict) and out):
            if not isinstance(out, dict) or not out:
                run.status = STATUS_FAILED
                run.error = "finished ohne structured_output"
                return run
            run.status = STATUS_COMPLETED
            run.output = out
            run.truncated = bool(info.get("truncated"))
            log.info("ai_request_completed run_id=%s purpose=%s",
                     sid, request.purpose)
            return run

        if state == _BLOCKIERT:
            if run.meta.get("nudged"):
                run.status = STATUS_FAILED
                run.error = "wartet weiterhin auf Eingabe"
                return run
            # Einmal antworten: die Regeln verbieten Rückfragen, trotzdem kann
            # Devin blockieren.
            self._api("POST", f"/sessions/{sid}/message", {"message": _NUDGE})
            run.meta["nudged"] = True
            run.status = STATUS_RUNNING
            return run

        if state in _LAEUFT:
            run.status = STATUS_RUNNING
            return run

        # expired / failed / unbekannt: einmal neu versuchen, dann aufgeben.
        if run.restarts < self.max_restarts:
            neu = self._create(request)
            log.info("ai_request_started run_id=%s purpose=%s restart=1",
                     neu, request.purpose)
            run.run_id = neu
            run.restarts += 1
            run.meta.pop("nudged", None)
            run.created_ts = time.time()
            run.status = STATUS_PENDING
            return run
        run.status = STATUS_FAILED
        run.error = f"fehlgeschlagen: {state}"
        log.warning("ai_request_failed run_id=%s status=%s purpose=%s",
                    sid, state, request.purpose)
        return run
