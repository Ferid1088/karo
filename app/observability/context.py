"""Request-Korrelation: eine ID pro Anfrage, im Kontext verfuegbar.

`contextvars` traegt die ID durch die ganze Anfrage — Router, Domain,
Datenbank, externe Dienste — ohne dass ein Parameter durch jede
Funktion gereicht werden muss. Jede Logzeile, die im Request-Kontext
entsteht, traegt so automatisch dieselbe `request_id`.
"""

import contextvars
import re
import uuid

# Angenommene fremde IDs nur, wenn sie harmlos aussehen: sie landen in
# Headern und Logzeilen, ein beliebiger String waere eine Injektionsflaeche.
_MUSTER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{7,62}$")

request_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "karo_request_id", default="")


def beginne(eingehend: str | None = None) -> contextvars.Token:
    """Startet den Request-Kontext; uebernimmt eine saubere fremde ID."""
    if eingehend and _MUSTER.match(eingehend):
        rid = eingehend
    else:
        rid = uuid.uuid4().hex[:16]
    return request_id.set(rid)


def ende(token: contextvars.Token) -> None:
    request_id.reset(token)


def aktuell() -> str:
    return request_id.get()
