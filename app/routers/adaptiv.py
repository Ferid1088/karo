"""Routen des adaptiven Lernens — dünne HTTP-Schicht über `app/adaptiv`.

Der Zustand liegt in der Datenbank, nicht in der Session: der Browser schickt
nur Antworten, nie eine Phase. Alles hier hängt am Schalter
`adaptive_learning_enabled` (§16) und nutzt die bestehende Anmeldung,
CSRF-Prüfung und Kinderrolle unverändert.
"""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from .. import config
from ..adaptiv import lektionen, sitzung as zustand, store, unterricht
from .shared import render, zurueck

router = APIRouter(prefix="/lernen/adaptiv", tags=["adaptiv"])

#: Elternsicht. Eigener Router, weil `/eltern/...` nicht in
#: CHILD_ALLOWED_PREFIXES steht und damit für Kinder gesperrt bleibt.
eltern_router = APIRouter(prefix="/eltern/lernfortschritt", tags=["adaptiv"])

#: §18: beobachtbare Lernsignale, in Worten statt in Kürzeln.
STAND_LABELS = {
    "offen": "noch offen",
    "im_aufbau": "im Aufbau",
    "sicher": "sitzt",
    "braucht_mensch": "braucht Begleitung",
}


def _aus() -> bool:
    return not getattr(config.load_safe(), "adaptive_learning_enabled", False)


def _zeige(request: Request, sitzung: dict) -> HTMLResponse:
    return render(request, "adaptiv.html", sitzung=sitzung,
                  schirm=unterricht.bildschirm(sitzung))


def _laufende(request: Request) -> dict | None:
    sitzung = zustand.laufende()
    return sitzung


def _auswahl(request: Request, thema: str = "", nichts_gefunden: bool = False):
    """Welche Lektionen es gibt — und ehrlich, was es noch nicht gibt."""
    return render(request, "adaptiv_auswahl.html",
                  lektionen=lektionen.verfuegbar(), thema=thema,
                  nichts_gefunden=nichts_gefunden)


@router.get("", response_class=HTMLResponse)
def start(request: Request):
    if _aus():
        return zurueck("/lernen")
    laufend = zustand.laufende()
    if laufend:
        return _zeige(request, laufend)
    # Kein stilles Zurückfallen auf die eine vorhandene Lektion: erst wählen.
    return _auswahl(request)


@router.post("/start", response_class=HTMLResponse)
def start_thema(request: Request, thema: str = Form("")):
    if _aus():
        return zurueck("/lernen")
    lektion = lektionen.fuer_thema(thema)
    if lektion is None:
        return _auswahl(request, thema=thema, nichts_gefunden=bool(thema.strip()))
    return _zeige(request, unterricht.starte(lektion["konzept_id"], thema))


@router.post("/neu", response_class=HTMLResponse)
def neu(request: Request):
    if _aus():
        return zurueck("/lernen")
    laufend = zustand.laufende()
    konzept_id = (laufend or {}).get("konzept_id")
    if konzept_id is None:
        return _auswahl(request)
    return _zeige(request, unterricht.neu_starten(konzept_id))


@router.post("/anker", response_class=HTMLResponse)
def anker(request: Request, antwort: str = Form("")):
    if _aus():
        return zurueck("/lernen")
    sitzung = _laufende(request)
    if sitzung is None:
        return zurueck("/lernen/adaptiv")
    return _zeige(request, unterricht.anker_beantwortet(sitzung, antwort))


@router.post("/diagnose", response_class=HTMLResponse)
def diagnose(request: Request, antwort: str = Form("")):
    if _aus():
        return zurueck("/lernen")
    sitzung = _laufende(request)
    if sitzung is None:
        return zurueck("/lernen/adaptiv")
    return _zeige(request, unterricht.diagnose_beantwortet(sitzung, antwort))


@router.post("/weiter", response_class=HTMLResponse)
def weiter(request: Request):
    if _aus():
        return zurueck("/lernen")
    sitzung = _laufende(request)
    if sitzung is None:
        return zurueck("/lernen/adaptiv")
    if sitzung["phase"] == zustand.ADAPTATION:
        return _zeige(request, unterricht.weiter_nach_adaptation(sitzung))
    return _zeige(request, unterricht.weiter(sitzung))


@router.post("/aufgabe", response_class=HTMLResponse)
def aufgabe(request: Request, antwort: str = Form("")):
    if _aus():
        return zurueck("/lernen")
    sitzung = _laufende(request)
    if sitzung is None:
        return zurueck("/lernen/adaptiv")
    return _zeige(request, unterricht.aufgabe_beantwortet(sitzung, antwort))


@router.post("/vorhersage", response_class=HTMLResponse)
def vorhersage(request: Request, antwort: str = Form("")):
    if _aus():
        return zurueck("/lernen")
    sitzung = _laufende(request)
    if sitzung is None:
        return zurueck("/lernen/adaptiv")
    return _zeige(request, unterricht.vorhersage_beantwortet(sitzung, antwort))


@router.post("/transfer", response_class=HTMLResponse)
def transfer(request: Request, antwort: str = Form("")):
    if _aus():
        return zurueck("/lernen")
    sitzung = _laufende(request)
    if sitzung is None:
        return zurueck("/lernen/adaptiv")
    return _zeige(request, unterricht.transfer_beantwortet(sitzung, antwort))


@eltern_router.get("", response_class=HTMLResponse)
def eltern_lernfortschritt(request: Request):
    """§18: Was das Kind versteht, wo es hakt — ohne Modellgedanken."""
    if _aus():
        return zurueck("/eltern")
    eintraege = store.fortschritt_uebersicht()
    return render(request, "adaptiv_eltern.html", eintraege=eintraege,
                  nachher=[e for e in eintraege if e.get("braucht_mensch")],
                  stand_labels=STAND_LABELS)


@router.post("/tipp", response_class=HTMLResponse)
def tipp(request: Request):
    if _aus():
        return zurueck("/lernen")
    sitzung = _laufende(request)
    if sitzung is None:
        return zurueck("/lernen/adaptiv")
    return _zeige(request, unterricht.tipp(sitzung))
