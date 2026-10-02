"""Devin API (v1) als asynchroner KI-Anbieter.

Vertrag (derselbe wie im Lehrplan-Dienst, siehe karo-curriculum-team
`kcteam/providers/devin.py`):

- `POST /v1/sessions` legt eine Session an und liefert sofort eine
  `session_id`; das Ergebnis liegt erst später als `structured_output`
  unter `GET /v1/sessions/{id}`.
- `call()` ist deshalb keine einmalige Sache:

  - kein Session-Eintrag    → Session anlegen, Kennung speichern, `AIPending`
  - Eintrag, läuft noch     → `AIPending` (der Worker legt den Auftrag zurück)
  - Eintrag, `finished`     → `structured_output` als Ergebnis zurückgeben
  - Eintrag, `blocked`      → einmal nachfassen (`/message`), sonst aufgeben
  - Eintrag, `expired` usw. → einmal neu starten, dann `AIError`

- Damit ein Neustart keine zweite Session anlegt, steht die Zuordnung in
  der Tabelle `provider_session`, indiziert über den Fingerabdruck des
  Aufrufs (Anbieter + System + Prompt). Derselbe Auftrag erzeugt denselben
  Prompt, findet also seine Session wieder; ein geänderter Prompt ist ein
  neuer Auftrag und bekommt eine neue Session.

An Devin gehen nur Text — der geschrubbte Auftrag samt Schema. Der Prompt
wird nie geloggt, der Schlüssel nie: er steckt ausschließlich im
Authorization-Header und kommt nur aus der Umgebungsvariablen
`DEVIN_API_KEY` — niemals aus `config.json`.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

from .. import config, db
from .base import (
    AIAuthError,
    AIConnectionError,
    AIError,
    AIPending,
    AISetupError,
    RawResult,
)

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

#: Statuswerte der v1-API, bei denen die Session noch arbeitet.
_LAEUFT = {"working", "running", "suspend_requested", "resumed",
           "resume_requested", "queued", "new"}
#: Danach wird die Session aufgegeben — sonst wartet ein Auftrag für immer.
_FERTIG, _BLOCKIERT = "finished", "blocked"


def _key(provider: str, system: str, user: str) -> str:
    """Fingerabdruck des Aufrufs — identischer Auftrag findet seine Session wieder."""
    return hashlib.sha256("\x00".join([provider, system, user]).encode()).hexdigest()


class DevinBackend:
    """Der einzige externe KI-Anbieter von Karo."""

    name = "devin"

    def __init__(self, timeout: float | None = None) -> None:
        ops = config.ops()
        self.base_url = (ops.devin_base_url or "https://api.devin.ai/v1").rstrip("/")
        self.poll_seconds = ops.devin_poll_seconds
        self.max_session_seconds = ops.devin_max_session_seconds
        self.timeout_s = timeout if timeout is not None else ops.devin_http_timeout_seconds
        self.max_restarts = ops.devin_max_restarts
        self.max_acu = ops.devin_max_acu
        self._http = None

    # ------------------------------------------------------------- HTTP
    @property
    def client(self):
        if self._http is None:
            import httpx
            key = os.environ.get("DEVIN_API_KEY")
            if not key:
                raise AISetupError(
                    "DEVIN_API_KEY fehlt: als Umgebungsvariable setzen "
                    "(siehe .env.example) — es gibt keinen anderen Anbieter.")
            self._http = httpx.Client(base_url=self.base_url,
                                      headers={"Authorization": f"Bearer {key}"},
                                      timeout=self.timeout_s)
        return self._http

    def _api(self, method: str, path: str, payload: dict | None = None) -> dict:
        """Ein API-Aufruf mit einheitlicher Fehler-Einordnung. Nie Header oder Body loggen."""
        import httpx
        try:
            r = self.client.request(method, path, json=payload)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise AIConnectionError(
                f"Devin API {method} {path}: {exc.__class__.__name__}",
                retryable=True) from exc
        if r.status_code < 400:
            try:
                return r.json()
            except ValueError as exc:
                raise AIError(f"Devin API {method} {path}: ungültige Antwort",
                              retryable=False) from exc
        if r.status_code in (401, 403):
            raise AIAuthError(
                f"Devin API {method} {path}: {r.status_code} — der "
                "DEVIN_API_KEY wird abgelehnt.")
        if r.status_code == 429:
            try:
                ra = float(r.headers.get("retry-after", ""))
            except ValueError:
                ra = None
            raise AIConnectionError(
                f"Devin API {method} {path}: 429 Rate-Limit",
                rate_limited=True, retryable=True, retry_after=ra)
        if r.status_code >= 500:
            raise AIConnectionError(
                f"Devin API {method} {path}: {r.status_code} Serverfehler",
                retryable=True)
        raise AIError(f"Devin API {method} {path}: {r.status_code}",
                      retryable=False)

    # ------------------------------------------------------------- Session-Zustand
    def _row(self, key: str) -> dict | None:
        row = db.q1("SELECT * FROM provider_session WHERE call_key=?", key)
        return dict(row) if row else None

    def _save(self, key: str, sid: str, purpose: str) -> None:
        ts = time.time()
        with db.tx() as c:
            c.execute(
                """INSERT OR IGNORE INTO provider_session
                       (call_key, provider, session_id, status, purpose,
                        created_ts, updated_ts)
                   VALUES (?, 'devin', ?, 'working', ?, ?, ?)""",
                (key, sid, purpose, ts, ts))

    def _mark(self, key: str, status: str, **fields) -> None:
        sets = "".join(f", {k}=?" for k in fields)
        with db.tx() as c:
            c.execute(
                f"UPDATE provider_session SET status=?, updated_ts=?{sets} "
                "WHERE call_key=?",
                (status, time.time(), *fields.values(), key))

    def _restarted(self, key: str, sid: str) -> None:
        with db.tx() as c:
            c.execute(
                """UPDATE provider_session
                      SET session_id=?, status='working', nudged=0,
                          restarts=restarts+1, updated_ts=?
                    WHERE call_key=?""",
                (sid, time.time(), key))

    # ------------------------------------------------------------- Devin-Aktionen
    def _create(self, system: str, user: str, schema: dict,
                purpose: str, web: bool) -> str:
        """Session anlegen. Gibt die session_id zurück."""
        preamble = _PREAMBLE + ("\n" + _WEB_ZUSATZ + "\n" if web else "")
        payload: dict[str, Any] = {
            "prompt": preamble + "\n\n" + system + "\n\n## Aufgabe\n" + user,
            "idempotent": True,           # ein Create-Timeout legt keine zweite Session an
            "unlisted": True,
            "title": ("karo " + (purpose or "aufruf"))[:120],
            "tags": ["karo", purpose or "aufruf"][:8],
            "secret_ids": [],             # die Session bekommt keinerlei hinterlegte Zugänge
            "knowledge_ids": [],          # und kein Organisations-Wissen fremder Aufträge
        }
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

    def call(
        self,
        prompt: str,
        schema: dict,
        *,
        model: str,
        system: str = "",
        max_tokens: int = 8192,          # Devin kennt kein Token-Limit — ignoriert
        web_search: bool = False,
        web_fetch: bool = False,
        purpose: str = "",
    ) -> RawResult:
        key = _key(self.name, system, prompt)
        row = self._row(key)
        if row is None:
            sid = self._create(system, prompt, schema, purpose,
                               web_search or web_fetch)
            self._save(key, sid, purpose)
            log.info("devin_session_started session_id=%s purpose=%s", sid, purpose)
            row = self._row(key)

        if row["status"] == "failed":
            raise AIError(f"Devin-Session {row['session_id']} aufgegeben: "
                          f"{row.get('detail')}", retryable=False)

        if self._age(row) > self.max_session_seconds:
            self._mark(key, "failed", detail="Zeitfenster überschritten")
            log.warning("devin_session_expired session_id=%s purpose=%s",
                        row["session_id"], purpose)
            raise AIError(f"Devin-Session {row['session_id']} älter als "
                          f"{self.max_session_seconds}s — aufgegeben",
                          retryable=False)

        try:
            info = self._api("GET", f"/sessions/{row['session_id']}")
        except AIError as exc:
            log.warning("devin_poll_failed session_id=%s purpose=%s error=%s",
                        row["session_id"], purpose, exc)
            raise exc
        state = str(info.get("status_enum") or info.get("status") or "working").lower()
        log.info("devin_session_status session_id=%s status=%s purpose=%s",
                 row["session_id"], state, purpose)

        out = info.get("structured_output")
        if state == _FERTIG or (state == _BLOCKIERT and isinstance(out, dict) and out):
            if not isinstance(out, dict) or not out:
                self._mark(key, "failed", detail="finished ohne structured_output")
                raise AIError(f"Devin-Session {row['session_id']} endete ohne "
                              "structured_output", retryable=False)
            self._mark(key, "finished")
            log.info("devin_session_completed session_id=%s purpose=%s",
                     row["session_id"], purpose)
            return RawResult(data=out, model=model,
                             truncated=bool(info.get("truncated")))

        if state == _BLOCKIERT:
            if row.get("nudged"):
                self._mark(key, "failed", detail="dauerhaft blocked")
                raise AIError(f"Devin-Session {row['session_id']} wartet weiterhin "
                              "auf Eingabe", retryable=False)
            # Einmal antworten: die Regeln verbieten Rückfragen, trotzdem kann
            # Devin blockieren.
            self._api("POST", f"/sessions/{row['session_id']}/message",
                      {"message": _NUDGE})
            self._mark(key, "working", nudged=1)
            raise AIPending(f"Devin-Session {row['session_id']} nach Rückfrage "
                            "fortgesetzt", wait_seconds=self.poll_seconds,
                            session_id=row["session_id"])

        if state in _LAEUFT:
            self._mark(key, "working")
            raise AIPending(f"Devin-Session {row['session_id']} läuft ({state})",
                            wait_seconds=self.poll_seconds,
                            session_id=row["session_id"])

        # expired / failed / unbekannt: einmal neu versuchen, dann aufgeben.
        if int(row.get("restarts") or 0) < self.max_restarts:
            sid = self._create(system, prompt, schema, purpose,
                               web_search or web_fetch)
            self._restarted(key, sid)
            log.info("devin_session_restarted session_id=%s purpose=%s", sid, purpose)
            raise AIPending(f"Devin-Session {sid} neu gestartet ({state})",
                            wait_seconds=self.poll_seconds, session_id=sid)
        self._mark(key, "failed", detail=f"Status {state}")
        log.warning("devin_session_failed session_id=%s status=%s purpose=%s",
                    row["session_id"], state, purpose)
        raise AIError(f"Devin-Session {row['session_id']} fehlgeschlagen: {state}",
                      retryable=False)

    @staticmethod
    def _age(row: dict) -> float:
        return time.time() - float(row.get("created_ts") or 0.0)
