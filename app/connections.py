"""Verbindungsstatus — KI-Anbieter und NotebookLM.

Eine Stelle, die beide Wege auf „verbunden/getrennt" prueft: fuer das
Status-Widget in jeder Seite (`base.html`) und fuer die Karten auf der
Einstellungsseite. Ergebnisse werden kurz zwischengespeichert (siehe
`CACHE_TTL`), damit viele offene Tabs, die alle paar Minuten nachfragen,
nicht bei jedem Aufruf eine echte Anfrage ausloesen.

Welcher KI-Anbieter das ist, weiss allein die Registry — hier steht nur
„der konfigurierte Anbieter", dessen Name und Secret-Variable liefert der
Adapter selbst.
"""

from __future__ import annotations

import logging
import threading
import time

from . import config
from .ai import AIClient, AIError, display_name, secret_env

log = logging.getLogger("karo.connections")

#: Etwas kuerzer als das Abfrageintervall im Browser (siehe base.html), damit
#: eine Anfrage kurz nach Ablauf nie auf einen veralteten Stand trifft.
CACHE_TTL = config.ops().connections_cache_ttl_seconds

_lock = threading.Lock()
_cache: dict[str, tuple[float, dict]] = {}


def _ai_status(cfg) -> dict:
    if not cfg.has_credentials:
        env = secret_env(cfg) or "der konfigurierte Schlüssel"
        return {"ok": False, "name": display_name(cfg),
                "note": f"{env} ist nicht gesetzt."}
    try:
        # `verify()` ist eine billige Zugangsprobe — kein Auftrag, keine Wirkung.
        AIClient.from_config(cfg).verify()
        return {"ok": True, "name": display_name(cfg), "note": "Verbunden."}
    except AIError as exc:
        return {"ok": False, "name": display_name(cfg), "note": str(exc)}
    except Exception:                                      # pragma: no cover
        log.exception("Unerwarteter Fehler bei der Anbieter-Statuspruefung")
        return {"ok": False, "name": display_name(cfg),
                "note": "Beim Prüfen ist ein unerwarteter Fehler aufgetreten."}


def _notebooklm_status() -> dict:
    from .media import notebooklm

    ok, grund = notebooklm.verfuegbar()
    return {"ok": ok, "note": grund}


def status(cfg=None, *, force: bool = False) -> dict:
    """{"ai": {...}, "notebooklm": {...}} — je mit "ok" und "note"."""
    cfg = cfg if cfg is not None else config.load_safe()
    now = time.monotonic()
    pruefungen = {
        "ai": lambda: _ai_status(cfg),
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
