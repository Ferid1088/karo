"""Verbindungsstatus — Devin und NotebookLM.

Eine Stelle, die beide Wege auf „verbunden/getrennt" prueft: fuer das
Status-Widget in jeder Seite (`base.html`) und fuer die Karten auf der
Einstellungsseite. Ergebnisse werden kurz zwischengespeichert (siehe
`CACHE_TTL`), damit viele offene Tabs, die alle paar Minuten nachfragen,
nicht bei jedem Aufruf eine echte Anfrage ausloesen.
"""

from __future__ import annotations

import logging
import threading
import time

from . import config
from .ai import AIClient, AIError

log = logging.getLogger("karo.connections")

#: Etwas kuerzer als das Abfrageintervall im Browser (siehe base.html), damit
#: eine Anfrage kurz nach Ablauf nie auf einen veralteten Stand trifft.
CACHE_TTL = config.ops().connections_cache_ttl_seconds

_lock = threading.Lock()
_cache: dict[str, tuple[float, dict]] = {}


def _devin_status(cfg) -> dict:
    if not cfg.has_credentials:
        return {"ok": False,
                "note": "DEVIN_API_KEY ist nicht gesetzt."}
    try:
        # `verify()` liest nur die Session-Liste — billig und ohne Wirkung.
        AIClient.from_config(cfg).verify()
        return {"ok": True, "note": "Verbunden."}
    except AIError as exc:
        return {"ok": False, "note": str(exc)}
    except Exception:                                      # pragma: no cover
        log.exception("Unerwarteter Fehler bei der Devin-Statuspruefung")
        return {"ok": False,
                "note": "Beim Prüfen ist ein unerwarteter Fehler aufgetreten."}


def _notebooklm_status() -> dict:
    from .media import notebooklm

    ok, grund = notebooklm.verfuegbar()
    return {"ok": ok, "note": grund}


def status(cfg=None, *, force: bool = False) -> dict:
    """{"devin": {...}, "notebooklm": {...}} — je mit "ok" und "note"."""
    cfg = cfg if cfg is not None else config.load_safe()
    now = time.monotonic()
    pruefungen = {
        "devin": lambda: _devin_status(cfg),
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
