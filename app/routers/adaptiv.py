"""Routen des adaptiven Lernens — dünne HTTP-Schicht über `app/adaptiv`.

Der Zustand liegt in der Datenbank, nicht in der Session: der Browser schickt
nur Antworten, nie eine Phase. Alles hier hängt am Schalter
`adaptive_learning_enabled` (§16) und nutzt die bestehende Anmeldung,
CSRF-Prüfung und Kinderrolle unverändert.
"""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from .. import config, topics, db
from ..adaptiv import (erzeugung, lektionen, sitzung as zustand,
                       store, unterricht)
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
    request.session['learning_session_id'] = sitzung['id']
    entry = store.eingabe(sitzung['eingabe_id']) if sitzung.get('eingabe_id') else {}
    concept = store.konzept(sitzung['konzept_id']) or {}
    screen = unterricht.bildschirm(sitzung)
    steps = {'anker': 1, 'diagnose': 1, 'vorhersage': 2, 'haken': 2,
             'regel': 2, 'beispiel': 3, 'anders': 2, 'transfer': 6, 'geschafft': 6}
    step = steps.get(screen['art'], 5 if sitzung.get('phase') == 'INDEPENDENT_TASK' else 4)
    return render(request, "adaptiv.html", sitzung=sitzung,
                  schirm=screen, learning_title=(entry or {}).get('thema_text') or concept.get('label', 'Dein Thema'),
                  learning_step=step, learning_back=request.session.get('learning_back', '/lernen'))


def _laufende(request: Request) -> dict | None:
    selected = request.session.get('learning_session_id')
    sitzung = store.sitzung(selected) if selected else zustand.laufende()
    return sitzung


def _auswahl(request: Request, thema: str = "", nichts_gefunden: bool = False):
    """Was es gibt — und ehrlich, was es noch nicht gibt.

    Nach einem vergeblichen Thema zeigt die Seite nur noch Lektionen, die
    damit zu tun haben. Der ganze Katalog waere hier kein Vorschlag,
    sondern ein Inhaltsverzeichnis. Ohne Thema (der Einstieg) steht
    weiterhin alles zur Wahl.
    """
    vorschlaege = (lektionen.empfehlungen(thema) if nichts_gefunden
                   else lektionen.verfuegbar())
    return render(request, "adaptiv_auswahl.html",
                  lektionen=vorschlaege, thema=thema,
                  nichts_gefunden=nichts_gefunden)


@router.get("", response_class=HTMLResponse)
def start(request: Request):
    if _aus():
        return zurueck("/lernen")
    laufend = _laufende(request)
    if laufend:
        return _zeige(request, laufend)
    # Kein stilles Zurückfallen auf die eine vorhandene Lektion: erst wählen.
    return _auswahl(request)


def _geprueftes_thema(topic_id: str) -> int | None:
    """Die Themen-ID kommt aus dem Formular und wird deshalb nachgeschlagen.

    Nur ein aktives Thema zaehlt; alles andere wird stillschweigend zu
    „keine Themen-ID" — die Sitzung selbst haengt am Konzept, nicht daran.
    """
    if not topic_id.isdigit():
        return None
    thema = topics.get(int(topic_id))
    return thema["id"] if thema and thema["state"] == topics.AKTIV else None


def _wartet(request: Request, thema: str, topic_id: int | None = None):
    """§15: Das Kind sieht, dass Karo arbeitet — kein Spinner ohne Worte."""
    return render(request, "adaptiv_wartet.html", thema=thema, topic_id=topic_id)


@router.post("/start", response_class=HTMLResponse)
def start_thema(request: Request, thema: str = Form(""),
                topic_id: str = Form(""), exam_id: str = Form("")):
    tid = _geprueftes_thema(topic_id)
    if topic_id and tid is None:
        return zurueck('/lernen')
    # The adaptive pilot may be switched off. A topic card must still have a
    # useful, visible destination instead of looking like it did nothing.
    if _aus():
        return zurueck(f"/lernzyklus/{tid}" if tid else "/lernen")
    topic = topics.get(tid) if tid else None
    if exam_id:
        if not exam_id.isdigit() or not db.q1('SELECT 1 FROM exam_topic WHERE exam_id=? AND topic_id=?', int(exam_id), tid):
            return zurueck('/klassenarbeit')
        request.session['learning_back'] = f'/klassenarbeit#exam-{exam_id}'
    else:
        request.session['learning_back'] = '/lernen'
    if topic:
        thema = topic['label']
    fach = (topic or {}).get('subject')
    grade = (topic or {}).get('grade')
    lektion = lektionen.fuer_thema(thema, fach, grade)
    if lektion is None:
        gefragt = bool(thema.strip())
        # §6: Katalog zuerst. Erst wenn dort nichts steht, schreibt Modell A
        # eine Lektion — im Hintergrund, und genau einmal pro Thema.
        if gefragt and getattr(config.load_safe(),
                               "llm_error_creation_enabled", False):
            erzeugung.anfordern(thema, fach=fach, klasse=grade)
            request.session['learning_pending'] = {'thema': thema, 'topic_id': tid, 'exam_id': exam_id}
            return _wartet(request, thema, tid)
        return _auswahl(request, thema=thema, nichts_gefunden=gefragt)
    previous = store.letzte_fuer_thema(tid, lektion['konzept_id'])
    return _zeige(request, previous or unterricht.starte(lektion['konzept_id'], thema, tid))


@router.get("/status")
def erzeugung_status(request: Request, thema: str = ""):
    """Womit die Warteseite fragt, ob es losgehen kann."""
    if _aus():
        return {"fertig": False, "laeuft": False}
    pending = request.session.get('learning_pending', {})
    topic = topics.get(pending['topic_id']) if pending.get('topic_id') else {}
    fach, grade = (topic or {}).get('subject'), (topic or {}).get('grade')
    fertig = lektionen.fuer_thema(thema, fach, grade) is not None
    return {"fertig": fertig, "laeuft": erzeugung.laeuft(thema, fach=fach, klasse=grade),
            "thema": thema}


@router.get("/wartet", response_class=HTMLResponse)
def wartet(request: Request, thema: str = ""):
    """Damit ein Neuladen der Warteseite nicht ins Leere führt (A6)."""
    if _aus():
        return zurueck("/lernen")
    if lektionen.fuer_thema(thema):
        return _auswahl(request, thema=thema)
    return _wartet(request, thema)


@router.post("/neu", response_class=HTMLResponse)
def neu(request: Request):
    if _aus():
        return zurueck("/lernen")
    laufend = _laufende(request)
    konzept_id = (laufend or {}).get("konzept_id")
    if konzept_id is None:
        return _auswahl(request)
    if laufend['zustand'] not in zustand.ENDZUSTAENDE:
        return _zeige(request, laufend)
    entry = store.eingabe(laufend['eingabe_id']) or {}
    return _zeige(request, unterricht.starte(konzept_id, entry.get('thema_text', ''), entry.get('topic_id')))


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
