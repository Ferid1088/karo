"""Strukturierte Logzeilen: eine JSON-Objekt pro Eintrag, nach stdout.

Der Docker-Log-Treiber sammelt stdout — im Container liegt damit jede Zeile
maschinenlesbar vor. Schwärzung bleibt unverändert Aufgabe von
`security.redact`: sie laeuft ueber die fertige JSON-Zeile, also auch ueber
Meldung und Traceback.

Fachliche Felder kommen als `extra={"fach": {...}}` auf den Record — so
bleibt die Logzeile kompakt und die Feldnamen stabil:

    log.info("…", extra={"fach": {"event": "mastery_gate_checked",
                                  "sitzung_id": 7, "erfolge": 4}})

Ergebnis (eine Zeile):
    {"ts": "…", "level": "INFO", "logger": "karo", "msg": "…",
     "service": "karo", "git_sha": "…", "request_id": "…",
     "event": "mastery_gate_checked", "sitzung_id": 7, "erfolge": 4}
"""

import datetime as dt
import json
import logging
import os
import traceback

from .. import security
from . import context


def _sha() -> str:
    return os.environ.get("KARO_GIT_SHA", "unbekannt")


class JsonFormatter(security.RedactingFormatter):
    """Baut die Zeile als JSON und schwärzt sie danach vollständig."""

    def format(self, record: logging.LogRecord) -> str:
        eintrag = {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(
                timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "service": "karo",
            "env": os.environ.get("KARO_ENV", "prod"),
            "git_sha": _sha(),
        }
        rid = context.aktuell()
        if rid:
            eintrag["request_id"] = rid
        jid = context.job_id.get()
        if jid:
            eintrag["job_id"] = jid
        fach = record.__dict__.get("fach")
        if isinstance(fach, dict):
            eintrag.update(fach)
        if record.exc_info and record.exc_info[0] is not None:
            eintrag["exception_type"] = record.exc_info[0].__name__
            eintrag["exception"] = "".join(
                traceback.format_exception(*record.exc_info)).rstrip()
        return security.redact(json.dumps(eintrag, ensure_ascii=False,
                                          default=str))


def configure(level: str = "INFO") -> None:
    """Richtet die Logwelt ein — dieselbe wie immer, nur als JSON."""
    security.configure_logging(level, formatter=JsonFormatter())
