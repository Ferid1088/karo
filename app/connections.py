"""Verbindungsstatus — Claude und NotebookLM.

Eine Stelle, die beide Wege auf „verbunden/getrennt" prueft: fuer das
Status-Widget in jeder Seite (`base.html`) und fuer die Karten auf der
Einstellungsseite. Ergebnisse werden kurz zwischengespeichert (siehe
`CACHE_TTL`), damit viele offene Tabs, die alle paar Minuten nachfragen,
nicht bei jedem Aufruf einen echten (bei Claude: kostenpflichtigen) Aufruf
ausloesen.
"""

from __future__ import annotations

import threading
import time

from . import config
from .llm import ClaudeClient, ClaudeError

log = __import__("logging").getLogger("karo.connections")

#: Etwas kuerzer als das Abfrageintervall im Browser (siehe base.html), damit
#: eine Anfrage kurz nach Ablauf nie auf einen veralteten Stand trifft.
CACHE_TTL = 100.0

_lock = threading.Lock()
_cache: dict[str, tuple[float, dict]] = {}


def _claude_status(cfg) -> dict:
    if not cfg.has_credentials:
        return {"ok": False, "note": "Keine Zugangsdaten hinterlegt."}
    try:
        client = ClaudeClient.from_config(cfg)
        if cfg.llm_backend == "api":
            # Reine Modell-Auflistung — kostet nichts, im Gegensatz zu einem
            # echten Modellaufruf.
            if not client.list_models():
                return {"ok": False,
                        "note": "Das Konto hat keine nutzbaren Modelle."}
        else:
            # Fuers Abo gibt es keinen kostenlosen Weg, die Anmeldung zu
            # pruefen — `verify()` ist ein winziger, aber echter Aufruf.
            # Der Cache (siehe oben) haelt das selten.
            client.verify()
        return {"ok": True, "note": "Verbunden."}
    except ClaudeError as exc:
        return {"ok": False, "note": str(exc)}
    except Exception:                                      # pragma: no cover
        log.exception("Unerwarteter Fehler bei der Claude-Statuspruefung")
        return {"ok": False,
                "note": "Beim Prüfen ist ein unerwarteter Fehler aufgetreten."}


def _notebooklm_status() -> dict:
    from .media import notebooklm

    ok, grund = notebooklm.verfuegbar()
    return {"ok": ok, "note": grund}


def status(cfg=None, *, force: bool = False) -> dict:
    """{"claude": {...}, "notebooklm": {...}} — je mit "ok" und "note"."""
    cfg = cfg if cfg is not None else config.load_safe()
    now = time.monotonic()
    pruefungen = {
        "claude": lambda: _claude_status(cfg),
        "notebooklm": _notebooklm_status,
    }
    ergebnis = {}
    with _lock:
        for name, pruefen in pruefungen.items():
            eintrag = _cache.get(name)
            veraltet = eintrag is None or now - eintrag[0] > CACHE_TTL
            if force or veraltet:
                eintrag = (now, pruefen())
                _cache[name] = eintrag
            ergebnis[name] = eintrag[1]
    return ergebnis


__all__ = ["status", "CACHE_TTL"]
