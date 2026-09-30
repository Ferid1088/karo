"""Einfache Einstiege: ein nächster Lernschritt und ein eigener Elternbereich."""
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse

from .. import config, db, jobs, kb, quizzes, topics
from ..services import workflow
from .shared import render, flash, zurueck, erfolge_ziel
from ..woche.pilot_store import parent_summary
from ..welten.store import current_companion, current_interest

router = APIRouter()


@router.get('/', response_class=HTMLResponse)
def dashboard(request: Request):
    from ..services import learning_hub, today, family_post
    personal = learning_hub.personal_topics()
    next_topic = next((t for t in personal if t['learning_status'] == 'bearbeitung'), None)
    next_topic = next_topic or next((t for t in personal if t['learning_status'] == 'neu'), None)
    themen, schritte, reviews = workflow.offene_schritte()
    # Heute zeigt den Kind-Bereich, auch wenn Eltern gerade mitlesen.
    aktion = workflow.get_next_action(
        'child', themen, schritte, reviews,
        antworten_pruefen_kind=config.load().antworten_pruefen_kind)
    return render(request, 'dashboard.html', post_neu=family_post.unread(),
                  tag=today.mein_tag(choice=request.query_params.get('jetzt', ''),
                                     role=request.session.get('role')),
                  naechstes=workflow.next_action_display(aktion), next_action_kind=aktion.kind,
                  next_topic=next_topic,
                  safe_count=db.q1("SELECT COUNT(*) AS n FROM topic WHERE learning_visible=1 AND learned_at IS NOT NULL "
                                   "AND deleted_at IS NULL AND purged_at IS NULL")['n'])


@router.get('/lernen/neu', response_class=HTMLResponse)
def neues_thema(request: Request):
    from ..services import learning_hub
    from .shared import aktives_fach
    fach = aktives_fach(request, request.query_params.get('fach'))
    return render(request, 'learning_new.html', fach=fach, katalog=learning_hub.catalog(fach))


@router.post('/lernen/neu')
def thema_anlegen(request: Request, thema: str = Form(''), fach: str = Form(''), klasse: int = Form(6)):
    from ..services import learning_hub
    from .shared import aktives_fach
    from .. import faecher
    if not faecher.schluessel(fach):
        flash(request, 'Bitte wähle zuerst ein Fach: Deutsch, Mathematik oder Englisch.', 'warn')
        return zurueck('/lernen')
    fach = aktives_fach(request, fach)
    try:
        topic_id = learning_hub.create_topic(thema, fach, klasse)
    except ValueError as exc:
        # SUBJECT_MISMATCH: nichts wird gespeichert, das Kind erfährt, wohin
        # das Thema gehört.
        flash(request, str(exc), 'warn')
        return zurueck(f'/lernen/neu?fach={fach}')
    flash(request, 'Dein Thema ist da. Los geht’s, wenn du bereit bist.')
    return zurueck(f'/lernen/thema/{topic_id}')


@router.get('/lernen/thema/{topic_id}', response_class=HTMLResponse)
def thema_einstieg(request: Request, topic_id: int):
    from fastapi import HTTPException
    from ..services import learning_hub
    from ..adaptiv import lektionen
    topic = learning_hub.topic_in_scope(topic_id)
    if topic is None:
        raise HTTPException(404, "Dieses Thema gehört nicht zu deinen Lernthemen.")
    learning_hub.decorate([topic])
    ready = lektionen.fuer_thema(topic['label'], topic['subject'])
    return render(request, 'learning_topic_intro.html', topic=topic, ready=bool(ready))


@router.post('/lernen/{topic_id}/loeschen')
def thema_loeschen(request: Request, topic_id: int):
    """Aus der Themenliste nehmen. Es landet im Archiv unter "Erfolge" und
    kann von dort zurueckgeholt werden — nichts geht verloren."""
    from ..services import learning_hub
    learning_hub.thema_loeschen(topic_id)
    flash(request, 'Das Thema liegt jetzt in deinen Erfolgen. Du kannst es dort zurückholen.')
    return zurueck('/lernen')


@router.post('/lernstand/thema/{topic_id}/zurueck')
def thema_zurueck(request: Request, topic_id: int, erneut: str = Form(''),
                  ziel: str = Form('')):
    from ..services import learning_hub
    learning_hub.thema_zurueck(topic_id)
    if erneut:
        # Gleich weiterlernen: die Lernrunde startet die adaptive Schicht.
        thema = topics.get(topic_id)
        if thema:
            flash(request, f'„{thema["label"]}" ist zurück. Los geht’s.')
        return zurueck('/lernen')
    flash(request, 'Das Thema ist zurück in deiner Liste.')
    return zurueck(erfolge_ziel(ziel))


@router.post('/lernstand/thema/{topic_id}/entfernen')
def thema_entfernen(request: Request, topic_id: int, ziel: str = Form('')):
    """Endgültig löschen. Die Rückfrage stellt die Seite selbst (?weg=…),
    damit sie auch ohne JavaScript kommt."""
    from ..services import learning_hub
    learning_hub.thema_entfernen(topic_id)
    flash(request, 'Das Thema ist gelöscht.')
    return zurueck(erfolge_ziel(ziel))


@router.post('/lernstand/arbeit/{exam_id}/entfernen')
def arbeit_entfernen(request: Request, exam_id: int, ziel: str = Form('')):
    from ..services import learning_hub
    learning_hub.arbeit_entfernen(exam_id)
    flash(request, 'Die Klassenarbeit ist gelöscht.')
    return zurueck(erfolge_ziel(ziel, 'arbeiten'))


@router.post('/klassenarbeit/{exam_id}/loeschen')
def arbeit_loeschen(request: Request, exam_id: int):
    from ..services import learning_hub
    learning_hub.arbeit_loeschen(exam_id)
    flash(request, 'Die Klassenarbeit liegt jetzt in deinen Erfolgen.')
    return zurueck('/klassenarbeit')


@router.post('/lernstand/arbeit/{exam_id}/zurueck')
def arbeit_zurueck(request: Request, exam_id: int, ziel: str = Form('')):
    from ..services import learning_hub
    learning_hub.arbeit_zurueck(exam_id)
    flash(request, 'Die Klassenarbeit ist zurück in deiner Liste.')
    return zurueck(erfolge_ziel(ziel, 'arbeiten'))


@router.get('/lernen/material', response_class=HTMLResponse)
def lernmaterial(request: Request):
    from .shared import aktives_fach
    fach = aktives_fach(request, request.query_params.get('fach'))
    return render(request, 'learning_upload.html', fach=fach)


# Hier standen „/lernen/material" (Foto hochladen) und sein Status: das Blatt
# ging an ein Modell, das die Themen ablas. Jetzt tippt das Kind sie ab —
# siehe app/llm/base.py. Das Lesen kommt zurück, sobald es auf dem Gerät
# läuft (docs/Karo_Prompts_Schritt_fuer_Schritt.MD, Schritt 2).


@router.post('/lernen/material/uebernehmen')
def material_themen(request: Request, themen: str = Form(''),
                    fach: str = Form(''), klasse: int = Form(6)):
    from ..services import learning_hub
    names = list(dict.fromkeys(n.strip() for n in themen.replace(',', '\n').splitlines() if n.strip()))
    if not names or len(names) > 20 or any(len(n) > 200 for n in names):
        flash(request, 'Bitte mindestens ein Thema eintragen. Bis zu 20 gehen auf einmal.', 'warn')
        return zurueck('/lernen/material')
    from .. import faecher
    fach = faecher.schluessel(fach)
    if fach is None:
        flash(request, 'Bitte wähle zuerst ein Fach: Deutsch, Mathematik oder Englisch.', 'warn')
        return zurueck('/lernen/material')
    if not 1 <= klasse <= 13:
        flash(request, 'Bitte eine Klasse von 1 bis 13 wählen.', 'warn')
        return zurueck('/lernen/material')
    abgewiesen = []
    for name in names:
        try:
            learning_hub.create_topic(name, fach, klasse, modell=False)
        except faecher.SubjectMismatch:
            abgewiesen.append(name)
    if abgewiesen:
        flash(request, f'Nicht aus {faecher.NAMEN[fach]} und deshalb nicht übernommen: '
              + ', '.join(abgewiesen), 'warn')
    else:
        flash(request, 'Deine Themen sind bereit zum Auswählen.')
    return zurueck(f'/lernen/{fach}')


@router.get('/lernen', response_class=HTMLResponse)
def lernen(request: Request):
    """Lernen beginnt immer in einem Fach: im zuletzt gewählten."""
    from .shared import aktives_fach
    return zurueck(f'/lernen/{aktives_fach(request, request.query_params.get("fach"))}'
                   + (f'?{request.url.query}' if request.url.query else ''))


def _fach_seite(fach: str):
    def seite(request: Request):
        return workflow.render_lernen_uebersicht(request, fach)
    seite.__name__ = f'lernen_{fach}'
    return seite


# Drei feste Adressen statt /lernen/{fach}: ein Platzhalter verdeckte
# /lernen/neu, /lernen/material und die übrigen Lernwege.
from .. import faecher as _faecher  # noqa: E402
for _fach in _faecher.FAECHER:
    router.add_api_route(f'/lernen/{_fach}', _fach_seite(_fach),
                         methods=['GET'], response_class=HTMLResponse)


@router.get('/lernen/themen')
def lernen_themen(request: Request):
    """Alter Weg zur Themenliste. /lernen ist sie inzwischen selbst —
    zwei Adressen für dieselbe Seite waren nur Verwechslungsgefahr."""
    return zurueck('/lernen')


@router.get('/eltern/ohne-fach', response_class=HTMLResponse)
def ohne_fach_ordner(request: Request):
    from ..services import ohne_fach
    return render(request, 'eltern_ohne_fach.html', ordner=ohne_fach.inhalte())


@router.post('/eltern/ohne-fach/zuordnen')
def ohne_fach_zuordnen(request: Request, art: str = Form(''), eintrag_id: int = Form(...),
                       fach: str = Form('')):
    from ..services import ohne_fach
    from .. import faecher
    try:
        ohne_fach.zuordnen(art, eintrag_id, fach)
    except ValueError as exc:
        flash(request, str(exc), 'err')
    else:
        flash(request, f'Zugeordnet zu {faecher.NAMEN[faecher.pflicht(fach)]}.')
    return zurueck('/eltern/ohne-fach')


@router.get('/eltern', response_class=HTMLResponse)
def eltern(request: Request):
    _, schritte, reviews = workflow.offene_schritte()
    if config.load().antworten_pruefen_kind:
        reviews = []
    from ..services import ohne_fach, grade_guidance, parent_report, family_post
    try:
        report = parent_report.build(request.query_params.get('ansicht', 'monat'),
            request.query_params.get('datum', ''), request.query_params.get('zurueck', 'monat'),
            request.query_params.get('basis', ''))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    report['post'] = family_post.parent_view(report, config.load_safe().learner_name or '')
    response = render(request, 'eltern.html', reviews=reviews, schritte=schritte,
                  report=report,
                  ohne_fach_anzahl=ohne_fach.anzahl(),
                  grade_notices=grade_guidance.unread(),
                  woche=parent_summary(), begleiter=current_companion(),
                  begleiter_interesse=current_interest(),
                  counts=jobs.counts(), kb_stat=kb.statistik(),
                  einig=quizzes.uebereinstimmung(), fehler=jobs.fehlgeschlagen())
    response.headers['Cache-Control'] = 'no-store'
    return response


@router.get('/eltern/bericht', response_class=HTMLResponse)
def eltern_bericht(request: Request):
    from ..services import parent_report, family_post
    try:
        report = parent_report.build(request.query_params.get('ansicht', 'monat'),
            request.query_params.get('datum', ''), request.query_params.get('zurueck', 'monat'),
            request.query_params.get('basis', ''))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    report['post'] = family_post.parent_view(report, config.load_safe().learner_name or '')
    response = render(request, '_parent_report.html', report=report)
    response.headers['Cache-Control'] = 'no-store'
    return response


@router.post('/eltern/klassenhinweis/{notice_id}/gelesen')
def klassenhinweis_gelesen(request: Request, notice_id: int):
    from ..services import grade_guidance
    grade_guidance.mark_read(notice_id)
    return zurueck('/eltern')
