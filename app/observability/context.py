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

#: Hintergrundarbeit hat keine Anfrage — der Job bekommt eine eigene,
#: stabile Identitaet (die Nummer seiner Zeile in der `job`-Tabelle),
#: statt eine längst beendete HTTP-request_id weiterzutragen.
job_id: contextvars.ContextVar[int] = contextvars.ContextVar(
    "karo_job_id", default=0)


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


def job_beginne(jid: int) -> contextvars.Token:
    return job_id.set(jid)


def job_ende(token: contextvars.Token) -> None:
    job_id.reset(token)


def korrelation() -> str:
    """Was auf einen abgehenden Dienst-Aufruf gehoert.

    Laueft gerade eine Anfrage, ist das ihre request_id. Laueft ein
    Hintergrund-Job, geht `job-<id>` mit — der Lehrplan-Dienst loggt sie
    als seine request_id, und der Auftrag ist auf beiden Seiten unter
    derselben Kennung findbar. Ohne Kontext bleibt der Header weg.
    """
    rid = request_id.get()
    if rid:
        return rid
    jid = job_id.get()
    # Neun Stellen fuehrende Nullen: das Muster des Dienstes verlangt
    # mindestens acht Zeichen, `job-7` wuerde sonst verworfen.
    return f"job-{jid:09d}" if jid else ""
