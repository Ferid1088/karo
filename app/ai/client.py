"""AIClient — die einzige Stelle, an der Karo mit dem KI-Anbieter spricht.

Waehlt den Anbieter-Adapter aus der Registry (die Wahrheit dafuer ist
`Config.ai_provider`), protokolliert jeden Aufruf und prueft die Antwort,
bevor sie weitergegeben wird. Der Rest der Anwendung kennt nur
`complete(...)`.

Anbieter duerfen asynchron sein: `complete()` kann `AIPending` werfen —
dann laeuft der Auftrag beim Anbieter noch (`ai_run` haelt seine Kennung).
Der Job-Worker stellt den Auftrag zurueck; der naechste identische Aufruf
holt das Ergebnis ab. Synchrone Anbieter liefern direkt — derselbe Weg.
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
)
from .provider import AIProvider
from .registry import build as build_provider
from .runs import get as run_get, key as run_key, save as run_save
from .types import AIRequest, LAEUFT, STATUS_COMPLETED, STATUS_FAILED

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
    """Fassade. Kennt den Adapter und entscheidet nach der Konfiguration."""

    def __init__(self, provider: AIProvider, modell: str = "") -> None:
        self._provider = provider
        self.modell = modell

    # -- Aufbau -------------------------------------------------------------

    @classmethod
    def from_config(cls, cfg, timeout: float | None = None) -> "AIClient":
        return cls(build_provider(cfg, timeout),
                   getattr(cfg, "ai_provider", ""))

    @property
    def backend_name(self) -> str:
        return self._provider.name

    # -- Setup-Hilfe --------------------------------------------------------

    def verify(self) -> str:
        """Billige Zugangsprobe — kein Auftrag, kein Ergebnis."""
        return self._provider.verify()

    # -- Der eigentliche Aufruf --------------------------------------------

    def complete(self, purpose: str, prompt: str, schema: dict, *,
                 system: str = "", max_tokens: int = config.ops().llm_default_max_tokens,
                 model: str | None = None,
                 web_search: bool = False, web_fetch: bool = False,
                 audit_prompt: str | None = None) -> AIResult:
        """Ein Aufruf mit erzwungener Antwortstruktur.

        Gibt entweder ein Objekt zurueck, das die Pflichtfelder des Schemas
        enthaelt, wirft `AIPending` (Anbieter arbeitet noch — Aufruf spaeter
        wiederholen, die Lauf-Kennung liegt gespeichert) oder eine AIError.
        Niemals Freitext, den jemand weiter unten hoffnungsvoll parst.

        `web_search`/`web_fetch`: der Auftrag darf aus dem Netz antworten
        bzw. eine konkrete, freigegebene Quelle abrufen (`research.py`) —
        ob der Anbieter das kann, entscheidet der Adapter.

        `audit_prompt`: fuer Eingaben, deren Inhalt auch geschwärzt zu
        sensibel für den Audit-Speicher ist (z. B. Arbeitsblatt-OCR). Dann
        landet in `llm_call.prompt` nur dieser neutrale Eintrag — etwa ein
        Hash des Prompts samt Metadaten — und von der Antwort nur ihr
        Hash, nicht ihr Inhalt.
        """
        begonnen = time.monotonic()
        request = AIRequest(purpose=purpose, user_prompt=prompt,
                            system_prompt=system, schema=schema,
                            max_output_tokens=max_tokens,
                            model=model or "", web_search=web_search,
                            web_fetch=web_fetch)
        provider = self._provider
        gewaehlt = model or self.modell
        call_id = _log_start(purpose, gewaehlt, audit_prompt or prompt,
                             provider.name)
        try:
            run = self._fuehren(request, provider)
        except AIPending as ausstehend:
            # Kein Fehler: der Auftrag laeuft beim Anbieter weiter. Der Job
            # wird zurueckgestellt und kommt spaeter mit derselben
            # Fingerabdruck-Kennung wieder.
            _log_finish(call_id, None, False,
                        f"ausstehend (Lauf {ausstehend.run_id or '?'})",
                        0, 0, None, _ms(begonnen))
            raise
        except AIError as fehler:
            _log_finish(call_id, None, False, str(fehler), 0, 0, None,
                        _ms(begonnen))
            raise
        except Exception as fehler:                      # pragma: no cover
            log.exception("Unerwarteter Fehler im Anbieter %s", provider.name)
            meldung = redact(str(fehler))[:300] or "Unbekannter Fehler."
            _log_finish(call_id, None, False, meldung, 0, 0, None, _ms(begonnen))
            raise AIError(meldung) from None

        rohtext = json.dumps(run.output, ensure_ascii=False)
        roh_archiv = (f"sha256:{hashlib.sha256(rohtext.encode('utf-8')).hexdigest()}"
                      if audit_prompt is not None else rohtext)

        if run.truncated:
            _log_finish(call_id, roh_archiv, False, "Antwort abgeschnitten",
                        0, 0, None, _ms(begonnen))
            raise AISchemaError(
                "Die Antwort des Anbieters wurde abgeschnitten und war deshalb "
                "unvollständig. Nichts wurde gespeichert.")

        fehlend = _missing_required(run.output, schema)
        if fehlend:
            _log_finish(call_id, roh_archiv, False, f"Felder fehlen: {fehlend}",
                        0, 0, None, _ms(begonnen))
            raise AISchemaError(
                "Die Antwort passte nicht zur erwarteten Struktur "
                f"(fehlend: {', '.join(fehlend)}). Nichts wurde gespeichert.")

        meta = run.meta or {}
        _log_finish(call_id, roh_archiv, True, None,
                    int(meta.get("tokens_in") or 0),
                    int(meta.get("tokens_out") or 0),
                    meta.get("cost_usd"), _ms(begonnen))
        return AIResult(run.output, str(meta.get("model") or gewaehlt),
                        int(meta.get("tokens_in") or 0),
                        int(meta.get("tokens_out") or 0),
                        meta.get("cost_usd"), _ms(begonnen), call_id)

    # -- Lauf-Orchestrierung -------------------------------------------------

    def _fuehren(self, request: AIRequest, provider: AIProvider):
        """Einen Lauf anlegen bzw. weiterführen — der neutrale Kern.

        Fingerabdruck findet den Lauf → fertig: ausgeben → läuft:
        pollen → immer noch: `AIPending` → gescheitert: `AIError`.
        """
        schluessel = run_key(provider.name, request.system_prompt,
                             request.user_prompt, request.schema)
        run = run_get(schluessel)

        if run is not None and run.status == STATUS_FAILED:
            raise AIError(f"KI-Lauf {run.run_id} aufgegeben: {run.error}",
                          retryable=False)
        if run is None:
            run = provider.start(request)
            run_save(schluessel, run, request.purpose)
        if run.status in LAEUFT:
            run = provider.poll(run, request)
            run_save(schluessel, run, request.purpose)
        if run.status in LAEUFT:
            raise AIPending(f"KI-Lauf {run.run_id} läuft beim Anbieter",
                            wait_seconds=getattr(provider, "poll_seconds", 60),
                            run_id=run.run_id)
        if run.status == STATUS_FAILED:
            raise AIError(f"KI-Lauf {run.run_id} fehlgeschlagen: {run.error}",
                          retryable=False)
        if run.status != STATUS_COMPLETED or not run.output:
            raise AIError(f"KI-Lauf {run.run_id} endete ohne Ergebnis",
                          retryable=False)
        return run


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
    "AIClient", "AIResult", "build_provider",
    "AIError", "AIAuthError", "AIConnectionError",
    "AISchemaError", "AISetupError", "AIPending",
]

# Re-Exporte fuer Importe via app.ai.client
from .base import AIAuthError, AIConnectionError, AISetupError  # noqa: E402
