"""Dashboard - simplified overview."""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from .. import config, db, export, ingest, jobs, kb, quizzes, research, teaching, topics
from ..domain import FLAG_ORDER, Flag, FLAG_LABELS
from .shared import render

log = logging.getLogger("karo.dashboard")
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    """Simplified dashboard showing only action items."""
    themen = topics.liste(topics.AKTIV)
    themen.sort(key=lambda t: (FLAG_ORDER.index(t["flag"])
                               if t["flag"] in FLAG_ORDER else 9, t["sort"]))
    zaehler = {f: sum(1 for t in themen if t["flag"] == f) for f in FLAG_ORDER}
    offene_quizze = quizzes.offene()
    offene_lessons = teaching.offene()
    reviews = [q for q in offene_quizze if q["state"] == "geprueft"]
    quiz = next((q for q in offene_quizze if q["state"] == "bereit"), None)
    if reviews:
        naechstes = {"titel": "Antworten prüfen", "text": reviews[0]["thema_label"],
                     "url": f"/quiz/{reviews[0]['id']}", "button": "Antworten prüfen", "rolle": "Für Eltern"}
    elif quiz:
        naechstes = {"titel": "Deine Fragen sind bereit", "text": quiz["thema_label"],
                     "url": f"/quiz/{quiz['id']}", "button": "Weiterlernen", "rolle": "Deine Lernzeit"}
    elif offene_quizze:
        quiz = offene_quizze[0]
        naechstes = {"titel": "Karo bereitet den nächsten Schritt vor", "text": quiz["thema_label"],
                     "url": f"/quiz/{quiz['id']}", "button": "Lernrunde öffnen", "rolle": "Deine Lernzeit"}
    elif offene_lessons:
        lesson = offene_lessons[0]
        naechstes = {"titel": "Hier geht es weiter", "text": lesson["thema_label"],
                     "url": f"/lernen/{lesson['id']}", "button": "Weiterlernen", "rolle": "Deine Lernzeit"}
    elif themen:
        naechstes = {"titel": "Ein kleiner Schritt für heute", "text": themen[0]["label"],
                     "url": f"/lernzyklus/{themen[0]['id']}", "button": "Lernrunde vorbereiten", "rolle": "Deine Lernzeit"}
    elif topics.anzahl_vorschlaege():
        naechstes = {"titel": "Die ersten Themen sind da", "text": "Prüfen Sie Karos Vorschläge. Danach kann es losgehen.",
                     "url": "/vorbereitung/inhalte", "button": "Themen bestätigen", "rolle": "Für Eltern"}
    else:
        naechstes = {"titel": "Alles beginnt mit einem Schulblatt", "text": "Ein Foto oder PDF genügt. Karo schlägt daraus passende Themen vor.",
                     "url": "/vorbereitung", "button": "Erstes Blatt hinzufügen", "rolle": "Willkommen bei Karo"}

    return render(
        request, "dashboard.html",
        themen=themen, zaehler=zaehler,
        kb_stat=kb.statistik(),
        offene_quizze=offene_quizze, offene_lessons=offene_lessons,
        reviews=reviews, naechstes=naechstes,
        fehler=[dict(r) for r in db.q(
            "SELECT * FROM job WHERE state='fehler' ORDER BY id DESC LIMIT 20")],
        counts=jobs.counts(),
        einig=quizzes.uebereinstimmung(),
    )
