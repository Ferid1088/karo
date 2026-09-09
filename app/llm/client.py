"""ClaudeClient — die einzige Stelle, an der Karo mit einem Sprachmodell spricht.

Waehlt das Backend, protokolliert jeden Aufruf und prueft die Antwort, bevor
sie weitergegeben wird. Der Rest der Anwendung kennt nur `complete(...)`.

Ein Anbieterwechsel — Bedrock, Vertex, ein lokales Modell — ist eine neue Datei
neben `api_backend.py` und ein Eintrag in `_backend()`. Sonst nichts.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import db
from ..security import redact
from .base import (
    Backend,
    ClaudeAuthError,
    ClaudeConnectionError,
    ClaudeError,
    ClaudeSchemaError,
    ClaudeSetupError,
)

log = logging.getLogger("karo.llm")

#: Welches Backend welche Bezeichnung im Setup traegt.
BACKENDS = {
    "abo": "Claude-Abo (20 €/Monat, über claude setup-token)",
    "api": "Anthropic-API-Schlüssel (Abrechnung pro Aufruf)",
}


@dataclass(frozen=True)
class LlmResult:
    data: dict[str, Any]
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float | None
    duration_ms: int
    call_id: int


class ClaudeClient:
    """Fassade. Kennt beide Backends und entscheidet nach der Konfiguration."""

    def __init__(self, backend: Backend, model_vision: str = "",
                 model_text: str = "") -> None:
        self._backend = backend
        self.model_vision = model_vision
        self.model_text = model_text

    # -- Aufbau -------------------------------------------------------------

    @classmethod
    def from_config(cls, cfg) -> "ClaudeClient":
        return cls(build_backend(cfg.llm_backend, cfg),
                   cfg.model_vision, cfg.model_text)

    @property
    def backend_name(self) -> str:
        return self._backend.name

    # -- Setup-Hilfen -------------------------------------------------------

    def verify(self) -> str:
        return self._backend.verify()

    def list_models(self) -> list[dict]:
        return self._backend.list_models()

    # -- Der eigentliche Aufruf --------------------------------------------

    def complete(self, purpose: str, prompt: str, schema: dict, *,
                 image_path: Path | None = None, system: str = "",
                 max_tokens: int = 8192, model: str | None = None,
                 web_search: bool = False, web_fetch: bool = False) -> LlmResult:
        """Ein Modellaufruf mit erzwungener Antwortstruktur.

        Gibt entweder ein Objekt zurueck, das die Pflichtfelder des Schemas
        enthaelt, oder wirft eine ClaudeError. Niemals Freitext, den jemand
        weiter unten hoffnungsvoll parst.

        `web_search`/`web_fetch`: siehe `Backend.call()` — nur für echte
        Websuche bzw. das Abrufen einer freigegebenen Quelle (`research.py`),
        nicht einfach auf jeden Aufruf setzen.
        """
        gewaehlt = model or (self.model_vision if image_path else self.model_text)
        if not gewaehlt:
            raise ClaudeSetupError(
                "Es ist kein Modell konfiguriert. Bitte Einstellungen öffnen.")

        begonnen = time.monotonic()
        call_id = _log_start(purpose, gewaehlt, prompt, image_path is not None,
                             self._backend.name)
        try:
            roh = self._backend.call(prompt, schema, model=gewaehlt,
                                     system=system, image_path=image_path,
                                     max_tokens=max_tokens, web_search=web_search,
                                     web_fetch=web_fetch)
        except ClaudeError as fehler:
            _log_finish(call_id, None, False, str(fehler), 0, 0, None,
                        _ms(begonnen))
            raise
        except Exception as fehler:                      # pragma: no cover
            log.exception("Unerwarteter Fehler im Backend %s", self._backend.name)
            meldung = redact(str(fehler))[:300] or "Unbekannter Fehler."
            _log_finish(call_id, None, False, meldung, 0, 0, None, _ms(begonnen))
            raise ClaudeError(meldung) from None

        rohtext = json.dumps(roh.data, ensure_ascii=False)

        if roh.truncated:
            _log_finish(call_id, rohtext, False, "Antwort abgeschnitten",
                        roh.tokens_in, roh.tokens_out, roh.cost_usd, _ms(begonnen))
            raise ClaudeSchemaError(
                "Die Antwort des Modells wurde abgeschnitten und war deshalb "
                "unvollständig. Nichts wurde gespeichert.")

        fehlend = _missing_required(roh.data, schema)
        if fehlend:
            _log_finish(call_id, rohtext, False, f"Felder fehlen: {fehlend}",
                        roh.tokens_in, roh.tokens_out, roh.cost_usd, _ms(begonnen))
            raise ClaudeSchemaError(
                "Die Antwort passte nicht zur erwarteten Struktur "
                f"(fehlend: {', '.join(fehlend)}). Nichts wurde gespeichert.")

        _log_finish(call_id, rohtext, True, None, roh.tokens_in, roh.tokens_out,
                    roh.cost_usd, _ms(begonnen))
        return LlmResult(roh.data, roh.model, roh.tokens_in, roh.tokens_out,
                         roh.cost_usd, _ms(begonnen), call_id)


# --------------------------------------------------------------------------
# Backend-Auswahl
# --------------------------------------------------------------------------

def build_backend(art: str, cfg) -> Backend:
    if art == "abo":
        from .cli_backend import CliBackend

        return CliBackend(cfg.claude_oauth_token)
    if art == "api":
        from .api_backend import ApiBackend

        return ApiBackend(cfg.anthropic_api_key)
    raise ClaudeSetupError(f"Unbekanntes Backend: {art}")


def models_for(art: str) -> list[dict]:
    """Modellliste ohne Zugangsdaten — fuer die Anzeige im Setup."""
    if art == "abo":
        from .cli_backend import CLI_MODELS

        return list(CLI_MODELS)
    return []


# --------------------------------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------------------------------

def _ms(begonnen: float) -> int:
    return int((time.monotonic() - begonnen) * 1000)


def _missing_required(nutzdaten, schema: dict) -> list[str]:
    """Minimale Schemapruefung: sind die Pflichtfelder oberster Ebene da?

    Keine vollstaendige JSON-Schema-Validierung — die Struktur wird ohnehin
    erzwungen. Hier geht es um den Fall, dass die Antwort trotzdem
    unvollstaendig ankommt.
    """
    if not isinstance(nutzdaten, dict):
        return ["(Antwort ist kein Objekt)"]
    return [k for k in schema.get("required", []) if k not in nutzdaten]


def _log_start(purpose: str, model: str, prompt: str, mit_bild: bool,
               backend: str) -> int:
    with db.tx() as c:
        cur = c.execute(
            """INSERT INTO llm_call (purpose, backend, model, prompt, had_image,
                                     created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (purpose, backend, model, redact(prompt), int(mit_bild), db.now()))
        return cur.lastrowid


def _log_finish(call_id, rohtext, ok, fehler, tin, tout, kosten, ms) -> None:
    with db.tx() as c:
        c.execute(
            """UPDATE llm_call
                  SET response_raw=?, schema_ok=?, error=?, tokens_in=?,
                      tokens_out=?, cost_usd=?, duration_ms=?
                WHERE id=?""",
            (redact(rohtext or ""), int(ok), fehler, tin, tout, kosten, ms, call_id))


__all__ = [
    "ClaudeClient", "LlmResult", "BACKENDS", "build_backend", "models_for",
    "ClaudeError", "ClaudeAuthError", "ClaudeConnectionError",
    "ClaudeSchemaError", "ClaudeSetupError",
]
