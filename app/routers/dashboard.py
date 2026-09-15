"""Einfache Einstiege: ein nächster Lernschritt und ein eigener Elternbereich."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from .. import config, db, jobs, kb, quizzes
from ..services import exam, workflow
from .shared import render

router = APIRouter()


@router.get('/', response_class=HTMLResponse)
def dashboard(request: Request):
    themen, schritte, reviews = workflow.offene_schritte()
    # Heute zeigt den Kind-Bereich, auch wenn Eltern gerade mitlesen.
    aktion = workflow.get_next_action(
        'child', themen, schritte, reviews,
        antworten_pruefen_kind=config.load().antworten_pruefen_kind)
    naechstes = workflow.next_action_display(aktion)
    return render(request, 'dashboard.html', naechstes=naechstes, reviews=reviews,
                  hat_erfolge=bool(db.q1("SELECT id FROM topic WHERE state='aktiv' AND learned_at IS NOT NULL LIMIT 1")),
                  themen=themen, kb_stat=kb.statistik(), exam=exam.get_next_exam())


@router.get('/lernen', response_class=HTMLResponse)
def lernen(request: Request):
    return workflow.render_lernen_uebersicht(request)


@router.get('/eltern', response_class=HTMLResponse)
def eltern(request: Request):
    _, schritte, reviews = workflow.offene_schritte()
    if config.load().antworten_pruefen_kind:
        reviews = []
    return render(request, 'eltern.html', reviews=reviews, schritte=schritte,
                  counts=jobs.counts(), kb_stat=kb.statistik(),
                  einig=quizzes.uebereinstimmung(), fehler=jobs.fehlgeschlagen())
