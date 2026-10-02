"""AIClient — die einzige Stelle, an der Karo mit dem KI-Anbieter spricht.

Waehlt das Backend (ausschliesslich Devin), protokolliert jeden Aufruf und
prueft die Antwort, bevor sie weitergegeben wird. Der Rest der Anwendung
kennt nur `complete(...)`.

Devin ist asynchron: `complete()` kann `AIPending` werfen — dann hat das
Backend eine Session angelegt oder sie laeuft noch. Der Job-Worker stellt
den Auftrag zurueck; der naechste identische Aufruf holt das Ergebnis ab.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from .. import config, db
from ..security import redact
from .base import (
    AIError,
    AIPending,
    AISchemaError,
    AISetupError,
    Backend,
    RawResult,
)

log = logging.getLogger("karo.ai")


@dataclass(frozen=True)
class AIResult:
    data: dict[str, Any]
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float | None
    duration_ms: int
    call_id: int


class AIClient:
    """Fassade. Kennt das Backend und entscheidet nach der Konfiguration."""

    def __init__(self, backend: Backend, modell: str = "") -> None:
        self._backend = backend
        self.modell = modell

    # -- Aufbau -------------------------------------------------------------

    @classmethod
    def from_config(cls, cfg, timeout: float | None = None) -> "AIClient":
        return cls(build_backend(cfg, timeout), getattr(cfg, "ai_provider", "devin"))

    @property
    def backend_name(self) -> str:
        return self._backend.name

    # -- Setup-Hilfe --------------------------------------------------------

    def verify(self) -> str:
        """Billige Zugangsprobe — keine Session, kein Auftrag."""
        return self._backend.verify()

    # -- Der eigentliche Aufruf --------------------------------------------

    def complete(self, purpose: str, prompt: str, schema: dict, *,
                 system: str = "", max_tokens: int = config.ops().llm_default_max_tokens,
                 model: str | None = None,
                 web_search: bool = False, web_fetch: bool = False,
                 audit_prompt: str | None = None) -> AIResult:
        """Ein Aufruf mit erzwungener Antwortstruktur.

        Gibt entweder ein Objekt zurueck, das die Pflichtfelder des Schemas
        enthaelt, wirft `AIPending` (Anbieter arbeitet noch — Aufruf spaeter
        wiederholen, die Session liegt gespeichert) oder eine AIError.
        Niemals Freitext, den jemand weiter unten hoffnungsvoll parst.

        `web_search`/`web_fetch`: siehe `Backend.call()` — nur für echte
        Websuche bzw. das Abrufen einer freigegebenen Quelle (`research.py`).

        `audit_prompt`: fuer Eingaben, deren Inhalt auch geschwärzt zu
        sensibel für den Audit-Speicher ist (z. B. Arbeitsblatt-OCR). Dann
        landet in `llm_call.prompt` nur dieser neutrale Eintrag — etwa ein
        Hash des Prompts samt Metadaten — und von der Antwort nur ihr
        Hash, nicht ihr Inhalt.
        """
        gewaehlt = model or self.modell
        begonnen = time.monotonic()
        call_id = _log_start(purpose, gewaehlt, audit_prompt or prompt,
                             self._backend.name)
        try:
            roh = self._backend.call(prompt, schema, model=gewaehlt,
                                     system=system, max_tokens=max_tokens,
                                     web_search=web_search, web_fetch=web_fetch,
                                     purpose=purpose)
        except AIPending as ausstehend:
            # Kein Fehler: die Session laeuft beim Anbieter weiter. Der Job
            # wird zurueckgestellt und kommt spaeter mit derselben
            # Fingerabdruck-Kennung wieder.
            _log_finish(call_id, None, False,
                        f"ausstehend (Session {ausstehend.session_id or '?'})",
                        0, 0, None, _ms(begonnen))
            raise
        except AIError as fehler:
            _log_finish(call_id, None, False, str(fehler), 0, 0, None,
                        _ms(begonnen))
            raise
        except Exception as fehler:                      # pragma: no cover
            log.exception("Unerwarteter Fehler im Backend %s", self._backend.name)
            meldung = redact(str(fehler))[:300] or "Unbekannter Fehler."
            _log_finish(call_id, None, False, meldung, 0, 0, None, _ms(begonnen))
            raise AIError(meldung) from None

        rohtext = json.dumps(roh.data, ensure_ascii=False)
        roh_archiv = (f"sha256:{hashlib.sha256(rohtext.encode('utf-8')).hexdigest()}"
                      if audit_prompt is not None else rohtext)

        if roh.truncated:
            _log_finish(call_id, roh_archiv, False, "Antwort abgeschnitten",
                        roh.tokens_in, roh.tokens_out, roh.cost_usd, _ms(begonnen))
            raise AISchemaError(
                "Die Antwort des Anbieters wurde abgeschnitten und war deshalb "
                "unvollständig. Nichts wurde gespeichert.")

        fehlend = _missing_required(roh.data, schema)
        if fehlend:
            _log_finish(call_id, roh_archiv, False, f"Felder fehlen: {fehlend}",
                        roh.tokens_in, roh.tokens_out, roh.cost_usd, _ms(begonnen))
            raise AISchemaError(
                "Die Antwort passte nicht zur erwarteten Struktur "
                f"(fehlend: {', '.join(fehlend)}). Nichts wurde gespeichert.")

        _log_finish(call_id, roh_archiv, True, None, roh.tokens_in,
                    roh.tokens_out, roh.cost_usd, _ms(begonnen))
        return AIResult(roh.data, roh.model, roh.tokens_in, roh.tokens_out,
                        roh.cost_usd, _ms(begonnen), call_id)


# --------------------------------------------------------------------------
# Backend-Auswahl
# --------------------------------------------------------------------------

def build_backend(cfg, timeout: float | None = None) -> Backend:
    """`timeout` begrenzt die HTTP-Aufrufe zur API, nicht die Sessiondauer."""
    if getattr(cfg, "ai_provider", "devin") != "devin":
        raise AISetupError(
            f"Unbekannter KI-Anbieter: {cfg.ai_provider!r}. Karo kennt nur 'devin'.")
    from .devin import DevinBackend
    return DevinBackend(timeout=timeout)


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


def _log_start(purpose: str, model: str, prompt: str, backend: str) -> int:
    # `had_image` bleibt in der Tabelle und bleibt 0: die alten Zeilen sagen
    # damit weiterhin die Wahrheit ueber das, was damals hinausging.
    with db.tx() as c:
        cur = c.execute(
            """INSERT INTO llm_call (purpose, backend, model, prompt, had_image,
                                     created_at)
               VALUES (?, ?, ?, ?, 0, ?)""",
            (purpose, backend, model, redact(prompt), db.now()))
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
    "AIClient", "AIResult", "build_backend",
    "AIError", "AIAuthError", "AIConnectionError",
    "AISchemaError", "AISetupError", "AIPending",
]
