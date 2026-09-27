"""Einfache Einstiege: ein nächster Lernschritt und ein eigener Elternbereich."""
from fastapi import APIRouter, Request, Form, UploadFile
from fastapi.responses import HTMLResponse

from .. import config, db, jobs, kb, quizzes, topics
from ..services import exam, exam_calendar, workflow
from .shared import render, flash, zurueck
from ..woche.pilot_store import parent_summary
from ..welten.store import current_companion, current_interest

router = APIRouter()


@router.get('/', response_class=HTMLResponse)
def dashboard(request: Request):
    from ..services import learning_hub
    personal = learning_hub.personal_topics()
    next_topic = next((t for t in personal if t['learning_status'] == 'bearbeitung'), None)
    next_topic = next_topic or next((t for t in personal if t['learning_status'] == 'neu'), None)
    gelernt = [t for t in learning_hub.archiv_themen() if not t['gelöscht']]
    themen, schritte, reviews = workflow.offene_schritte()
    # Heute zeigt den Kind-Bereich, auch wenn Eltern gerade mitlesen.
    aktion = workflow.get_next_action(
        'child', themen, schritte, reviews,
        antworten_pruefen_kind=config.load().antworten_pruefen_kind)
    naechstes = workflow.next_action_display(aktion)
    return render(request, 'dashboard.html', naechstes=naechstes, reviews=reviews,
                  hat_erfolge=bool(db.q1("SELECT id FROM topic WHERE state='aktiv' AND learned_at IS NOT NULL LIMIT 1")),
                  themen=themen, kb_stat=kb.statistik(), exam=exam.get_next_exam(),
                  exam_today=exam_calendar.today_task() if config.load().klassenarbeit_kind else None,
                  next_topic=next_topic,
                  personal_count=len(personal) + len(gelernt),
                  safe_count=len(gelernt))


@router.get('/lernen/neu', response_class=HTMLResponse)
def neues_thema(request: Request):
    from ..services import learning_hub
    return render(request, 'learning_new.html', katalog=learning_hub.catalog())


@router.post('/lernen/neu')
def thema_anlegen(request: Request, thema: str = Form(''), fach: str = Form(''), klasse: int = Form(6)):
    from ..services import learning_hub
    try:
        learning_hub.create_topic(thema, fach, klasse)
    except ValueError as exc:
        flash(request, str(exc), 'warn')
        return zurueck('/lernen/neu')
    flash(request, 'Dein Thema ist da. Los geht’s, wenn du bereit bist.')
    return zurueck('/lernen')


@router.post('/lernen/{topic_id}/loeschen')
def thema_loeschen(request: Request, topic_id: int):
    """Aus der Themenliste nehmen. Es landet im Archiv unter "Erfolge" und
    kann von dort zurueckgeholt werden — nichts geht verloren."""
    from ..services import learning_hub
    learning_hub.thema_loeschen(topic_id)
    flash(request, 'Das Thema liegt jetzt in deinen Erfolgen. Du kannst es dort zurückholen.')
    return zurueck('/lernen')


@router.post('/lernstand/thema/{topic_id}/zurueck')
def thema_zurueck(request: Request, topic_id: int, erneut: str = Form('')):
    from ..services import learning_hub
    learning_hub.thema_zurueck(topic_id)
    if erneut:
        # Gleich weiterlernen: die Lernrunde startet die adaptive Schicht.
        thema = topics.get(topic_id)
        if thema:
            flash(request, f'„{thema["label"]}" ist zurück. Los geht’s.')
        return zurueck('/lernen')
    flash(request, 'Das Thema ist zurück in deiner Liste.')
    return zurueck('/lernstand')


@router.post('/lernstand/thema/{topic_id}/entfernen')
def thema_entfernen(request: Request, topic_id: int):
    """Endgültig löschen. Die Rückfrage stellt die Seite selbst (?weg=…),
    damit sie auch ohne JavaScript kommt."""
    from ..services import learning_hub
    learning_hub.thema_entfernen(topic_id)
    flash(request, 'Das Thema ist gelöscht.')
    return zurueck('/lernstand')


@router.post('/lernstand/arbeit/{exam_id}/entfernen')
def arbeit_entfernen(request: Request, exam_id: int):
    from ..services import learning_hub
    learning_hub.arbeit_entfernen(exam_id)
    flash(request, 'Die Klassenarbeit ist gelöscht.')
    return zurueck('/lernstand?tab=arbeiten')


@router.post('/klassenarbeit/{exam_id}/loeschen')
def arbeit_loeschen(request: Request, exam_id: int):
    from ..services import learning_hub
    learning_hub.arbeit_loeschen(exam_id)
    flash(request, 'Die Klassenarbeit liegt jetzt in deinen Erfolgen.')
    return zurueck('/klassenarbeit')


@router.post('/lernstand/arbeit/{exam_id}/zurueck')
def arbeit_zurueck(request: Request, exam_id: int):
    from ..services import learning_hub
    learning_hub.arbeit_zurueck(exam_id)
    flash(request, 'Die Klassenarbeit ist zurück in deiner Liste.')
    return zurueck('/klassenarbeit')


@router.get('/lernen/material', response_class=HTMLResponse)
def lernmaterial(request: Request):
    import json
    row = db.q1('''SELECT s.* FROM exam_scan s JOIN learning_upload u ON u.scan_id=s.id
                  WHERE s.state!='uebernommen' ORDER BY s.id DESC LIMIT 1''')
    scan = dict(row) if row else None
    if scan:
        scan['names'] = json.loads(scan.get('themen') or '[]')
    return render(request, 'learning_upload.html', scan=scan)


@router.post('/lernen/material')
async def material_hochladen(request: Request, datei: UploadFile, fach: str = Form(''), klasse: int = Form(6)):
    from pathlib import Path
    from .. import security
    from ..services.exam import ExamError
    from starlette.concurrency import run_in_threadpool
    if not 1 <= klasse <= 13:
        flash(request, 'Bitte eine Klasse von 1 bis 13 wählen.', 'warn')
        return zurueck('/lernen/material')
    data = await datei.read(security.MAX_UPLOAD_BYTES + 1)
    if len(data) > security.MAX_UPLOAD_BYTES:
        flash(request, 'Die Datei ist zu groß. Bitte ein kleineres Bild oder PDF auswählen.', 'warn')
        return zurueck('/lernen/material')
    try:
        scan_id = await run_in_threadpool(exam.upload_exam_topics_sheet, data, Path(datei.filename or '').suffix.lower())
    except ExamError as exc:
        flash(request, str(exc), 'warn')
        return zurueck('/lernen/material')
    with db.tx() as c:
        c.execute('INSERT INTO learning_upload VALUES(?,?,?)',
                  (scan_id, (fach.strip() or config.load().subject)[:80], klasse))
    return zurueck('/lernen/material')


@router.get('/lernen/material/status')
def material_status(scan_id: int):
    return {'signatur': exam.get_exam_topic_scan_status(scan_id)}


@router.post('/lernen/material/uebernehmen')
def material_themen(request: Request, scan_id: int = Form(...), themen: str = Form('')):
    from ..services import learning_hub
    from .. import exam_plan
    scan = db.q1('''SELECT s.*,u.subject,u.grade FROM exam_scan s JOIN learning_upload u ON u.scan_id=s.id
                   WHERE s.id=? AND s.state='gelesen' ''', scan_id)
    names = list(dict.fromkeys(n.strip() for n in themen.replace(',', '\n').splitlines() if n.strip()))
    if not scan or not names or len(names) > 20 or any(len(n) > 200 for n in names):
        flash(request, 'Prüfe bitte die erkannten Themen. Du kannst bis zu 20 Themen übernehmen.', 'warn')
        return zurueck('/lernen/material')
    for name in names:
        learning_hub.create_topic(name, scan['subject'], scan['grade'])
    exam_plan.scan_uebernehmen(scan_id)
    flash(request, 'Deine Themen sind bereit zum Auswählen.')
    return zurueck('/lernen')


@router.get('/lernen', response_class=HTMLResponse)
def lernen(request: Request):
    return workflow.render_lernen_uebersicht(request)


@router.get('/lernen/themen')
def lernen_themen(request: Request):
    """Alter Weg zur Themenliste. /lernen ist sie inzwischen selbst —
    zwei Adressen für dieselbe Seite waren nur Verwechslungsgefahr."""
    return zurueck('/lernen')


@router.get('/eltern', response_class=HTMLResponse)
def eltern(request: Request):
    _, schritte, reviews = workflow.offene_schritte()
    if config.load().antworten_pruefen_kind:
        reviews = []
    return render(request, 'eltern.html', reviews=reviews, schritte=schritte,
                  woche=parent_summary(), begleiter=current_companion(),
                  begleiter_interesse=current_interest(),
                  counts=jobs.counts(), kb_stat=kb.statistik(),
                  einig=quizzes.uebereinstimmung(), fehler=jobs.fehlgeschlagen())
