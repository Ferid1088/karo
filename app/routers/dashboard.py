"""Einfache Einstiege: ein nächster Lernschritt und ein eigener Elternbereich."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from .. import db, jobs, kb, quizzes, teaching, topics
from ..domain import FLAG_ORDER
from .shared import render

router = APIRouter()


def _lernen():
    themen = topics.liste(topics.AKTIV)
    themen.sort(key=lambda t: (FLAG_ORDER.index(t['flag']), t['sort']))
    quizze = quizzes.offene()
    lessons = teaching.offene()
    schritte = []
    # Ein Material aus dem Lernplan führt immer zurück zu seinem Materialtab.
    material = {r['lesson_id']: r['id'] for r in db.q('SELECT id, lesson_id FROM exam_material')}
    for q in quizze:
        if q['state'] == 'geprueft':
            continue
        text = {'bereit': 'Deine Fragen sind da', 'offen': 'Deine Fragen werden vorbereitet',
                'beantwortet': 'Deine Antworten werden angeschaut'}.get(q['state'], 'Weiterlernen')
        schritte.append({'titel': q['thema_label'], 'text': text, 'url': f"/quiz/{q['id']}",
                         'topic_id': q['topic_id'], 'bereit': q['state'] == 'bereit'})
    quiz_themen = {q['topic_id'] for q in quizze}
    for l in lessons:
        if l['topic_id'] in quiz_themen:
            continue
        url = f"/klassenarbeit/material/{material[l['id']]}" if l['id'] in material else f"/lernen/{l['id']}"
        schritte.append({'titel': l['thema_label'], 'text': 'Hier geht deine Lernrunde weiter',
                         'url': url, 'topic_id': l['topic_id'], 'bereit': l['state'] == 'bereit'})
    schritte.sort(key=lambda s: not s['bereit'])
    return themen, schritte, [q for q in quizze if q['state'] == 'geprueft']


@router.get('/', response_class=HTMLResponse)
def dashboard(request: Request):
    themen, schritte, reviews = _lernen()
    if schritte:
        naechstes = {**schritte[0], 'button': 'Weiterlernen'}
    elif themen:
        naechstes = {'titel': themen[0]['label'], 'text': 'Ein kleiner Schritt für heute.',
                     'url': f"/lernzyklus/{themen[0]['id']}", 'button': 'Los geht’s'}
    else:
        naechstes = None
    return render(request, 'dashboard.html', naechstes=naechstes, reviews=reviews,
                  themen=themen, kb_stat=kb.statistik(),
                  exam=db.q1('SELECT * FROM exam WHERE exam_date>=? ORDER BY exam_date LIMIT 1', db.today()))


@router.get('/lernen', response_class=HTMLResponse)
def lernen(request: Request):
    themen, schritte, reviews = _lernen()
    return render(request, 'lernen_start.html', themen=themen, schritte=schritte, reviews=reviews)


@router.get('/eltern', response_class=HTMLResponse)
def eltern(request: Request):
    _, schritte, reviews = _lernen()
    return render(request, 'eltern.html', reviews=reviews, schritte=schritte,
                  counts=jobs.counts(), kb_stat=kb.statistik(), einig=quizzes.uebereinstimmung(),
                  fehler=[dict(r) for r in db.q("SELECT * FROM job WHERE state='fehler' ORDER BY id DESC LIMIT 20")])
