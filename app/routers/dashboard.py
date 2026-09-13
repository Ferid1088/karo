"""Einfache Einstiege: ein nächster Lernschritt und ein eigener Elternbereich."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from .. import db, jobs, kb, quizzes
from ..services import workflow
from .shared import render

router = APIRouter()


@router.get('/', response_class=HTMLResponse)
def dashboard(request: Request):
    themen, schritte, reviews = workflow.offene_schritte()
    naechstes = workflow.get_next_action(themen, schritte)
    return render(request, 'dashboard.html', naechstes=naechstes, reviews=reviews,
                  themen=themen, kb_stat=kb.statistik(),
                  exam=db.q1('SELECT * FROM exam WHERE exam_date>=? ORDER BY exam_date LIMIT 1', db.today()))


@router.get('/lernen', response_class=HTMLResponse)
def lernen(request: Request):
    return workflow.render_lernen_uebersicht(request)


@router.get('/eltern', response_class=HTMLResponse)
def eltern(request: Request):
    _, schritte, reviews = workflow.offene_schritte()
    return render(request, 'eltern.html', reviews=reviews, schritte=schritte,
                  counts=jobs.counts(), kb_stat=kb.statistik(), einig=quizzes.uebereinstimmung(),
                  fehler=[dict(r) for r in db.q("SELECT * FROM job WHERE state='fehler' ORDER BY id DESC LIMIT 20")])
