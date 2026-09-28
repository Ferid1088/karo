"""Two strictly scoped HTTP journeys using the same checked teaching engine."""
from __future__ import annotations

from urllib.parse import urlencode
from itsdangerous import URLSafeTimedSerializer, BadSignature
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from .. import config, topics, db
from ..adaptiv import erzeugung, lektionen, sitzung as zustand, store, unterricht
from ..services import learning_hub, grade_guidance
from .shared import flash, render, zurueck

router = APIRouter(prefix="/lernen/adaptiv", tags=["adaptiv"])
exam_router = APIRouter(prefix="/klassenarbeit/{exam_id}/lernen", tags=["exam-learning"])
eltern_router = APIRouter(prefix="/eltern/lernfortschritt", tags=["adaptiv"])
STAND_LABELS = {"offen": "noch offen", "im_aufbau": "im Aufbau",
                "sicher": "sitzt", "braucht_mensch": "braucht Begleitung"}


def _aus() -> bool:
    return not getattr(config.load_safe(), "adaptive_learning_enabled", False)


def _context(request: Request) -> dict:
    raw = request.path_params.get("exam_id")
    eid = int(raw) if raw is not None and str(raw).isdigit() else None
    if raw is not None and (eid is None or not db.q1(
            "SELECT id FROM exam WHERE id=? AND deleted_at IS NULL AND purged_at IS NULL"
            " AND subject IN ('deutsch','mathematik','englisch')", eid)):
        raise HTTPException(404, "Diese Klassenarbeit gibt es nicht.")
    return {
        "learning_exam_id": eid,
        "learning_base": f"/klassenarbeit/{eid}/lernen" if eid else "/lernen/adaptiv",
        "learning_back": f"/klassenarbeit/{eid}" if eid else "/lernen",
        "learning_area": "Prüfungsvorbereitung" if eid else "Meine Themen",
        "learning_ui": True, "show_nav": False, "adult_page": False,
    }


def _topic(request: Request, raw: str) -> dict | None:
    ctx = _context(request)
    if not raw:
        if ctx["learning_exam_id"]:
            raise HTTPException(400, "Wähle ein Prüfungsthema aus deinem Lernplan.")
        return None
    topic = learning_hub.topic_in_scope(int(raw), ctx["learning_exam_id"]) if raw.isdigit() else None
    if topic is None:
        raise HTTPException(404, "Dieses Thema gehört nicht zu diesem Lernbereich.")
    return topic


def _owns(request: Request, session: dict) -> bool:
    entry = store.eingabe(session.get("eingabe_id")) or {}
    eid = _context(request)["learning_exam_id"]
    tid = entry.get("topic_id")
    return (bool(learning_hub.topic_in_scope(tid, eid)) if tid else eid is None)


def _zeige(request: Request, sitzung: dict) -> HTMLResponse:
    ctx = _context(request)
    entry = store.eingabe(sitzung["eingabe_id"]) or {}
    concept = store.konzept(sitzung["konzept_id"]) or {}
    warning = _grade_gate(request, concept, entry.get('thema_text', ''), entry.get('topic_id'))
    if warning is not None:
        return warning
    request.session["learning_session:" + ctx["learning_base"]] = sitzung["id"]
    screen = unterricht.bildschirm(sitzung)
    steps = {"anker": 1, "diagnose": 1, "vorhersage": 2, "haken": 2,
             "regel": 2, "beispiel": 3, "anders": 2, "transfer": 6, "geschafft": 6}
    step = steps.get(screen["art"], 5 if sitzung.get("phase") == "INDEPENDENT_TASK" else 4)
    return render(request, "adaptiv.html", sitzung=sitzung, schirm=screen,
                  learning_title=entry.get("thema_text") or concept.get("label", "Dein Thema"),
                  learning_step=step, **ctx)


def _grade_signer():
    return URLSafeTimedSerializer(config.session_secret(), salt='learning-grade-confirmation-v1')


def _grade_gate(request: Request, concept: dict, thema: str, topic_id: int | None):
    ctx = _context(request)
    info = grade_guidance.guidance(concept, ctx['learning_base'], topic_id, thema)
    if not info['mismatch'] or info['acknowledged']:
        return None
    token = _grade_signer().dumps(dict(key=info['key'], concept_id=concept['id'],
        topic_id=topic_id, thema=thema, area=ctx['learning_base'], csrf=request.session.get('csrf')))
    return render(request, 'learning_grade_warning.html', guidance=info, confirmation=token, **ctx)


@router.post('/klasse-bestaetigen', response_class=HTMLResponse)
@exam_router.post('/klasse-bestaetigen', response_class=HTMLResponse)
def klasse_bestaetigen(request: Request, confirmation: str = Form('')):
    ctx = _context(request)
    if _aus():
        return _auswahl(request)
    try:
        proof = _grade_signer().loads(confirmation, max_age=1800)
    except BadSignature:
        raise HTTPException(400, 'Der Hinweis ist abgelaufen. Bitte öffne dein Thema erneut.')
    if proof.get('area') != ctx['learning_base'] or proof.get('csrf') != request.session.get('csrf'):
        raise HTTPException(403, 'Diese Bestätigung gehört nicht zu diesem Lernbereich.')
    topic = _topic(request, str(proof.get('topic_id') or ''))
    concept = store.konzept(proof['concept_id'])
    if not concept or not concept.get('aktiv') or not concept.get('geprueft_am'):
        raise HTTPException(409, 'Die Lernreihe muss erneut geprüft werden.')
    if topic and (topic['label'] != proof['thema'] or topic['subject'] != concept['fach']):
        raise HTTPException(409, 'Das Thema wurde geändert. Bitte öffne es erneut.')
    info = grade_guidance.guidance(concept, ctx['learning_base'], (topic or {}).get('id'), proof['thema'])
    if proof['key'] != info['key']:
        return _grade_gate(request, concept, proof['thema'], (topic or {}).get('id')) or zurueck(ctx['learning_back'])
    grade_guidance.acknowledge(info)
    previous = store.letzte_fuer_thema((topic or {}).get('id'), concept['id'])
    return _zeige(request, previous or unterricht.starte(concept['id'], proof['thema'], (topic or {}).get('id')))


def _laufende(request: Request) -> dict | None:
    ctx = _context(request)
    selected = request.query_params.get("sitzung") or request.session.get("learning_session:" + ctx["learning_base"])
    if selected:
        session = store.sitzung(int(selected)) if str(selected).isdigit() else None
        if session and _owns(request, session):
            return session
        if request.query_params.get("sitzung"):
            raise HTTPException(404, "Diese Lernrunde gehört nicht zu diesem Lernbereich.")
    # Resume after login, scoped in SQL; never resume the other area's last session.
    eid = ctx["learning_exam_id"]
    if eid:
        row = db.q1("""SELECT s.id FROM lern_sitzung s JOIN lern_eingabe i ON i.id=s.eingabe_id
            JOIN exam_topic x ON x.topic_id=i.topic_id WHERE x.exam_id=?
            AND s.zustand NOT IN ('MASTERED','ESCALATED') ORDER BY s.id DESC LIMIT 1""", eid)
    else:
        row = db.q1("""SELECT s.id FROM lern_sitzung s JOIN lern_eingabe i ON i.id=s.eingabe_id
            LEFT JOIN topic t ON t.id=i.topic_id WHERE (i.topic_id IS NULL OR
            (t.learning_visible=1 AND NOT EXISTS(SELECT 1 FROM exam_topic x WHERE x.topic_id=t.id)))
            AND s.zustand NOT IN ('MASTERED','ESCALATED') ORDER BY s.id DESC LIMIT 1""")
    session = store.sitzung(row["id"]) if row else None
    return session if session and _owns(request, session) else None


def _fach(request: Request, topic: dict | None, wert: str = "") -> str:
    """Das Fach eines Lernwegs: das des Themas, sonst das aktive."""
    from .shared import aktives_fach
    return aktives_fach(request, (topic or {}).get("subject") or wert)


def _auswahl(request: Request, thema: str = "", nichts_gefunden: bool = False, fach: str = ""):
    ctx = _context(request)
    if ctx["learning_exam_id"] or _aus():
        return render(request, "learning_unavailable.html", thema=thema,
                      disabled=_aus(), **ctx)
    fach = _fach(request, None, fach)
    # Vorschläge nur aus dem aktiven Fach — nie die Bruchlektion im Reiter Englisch.
    suggestions = (lektionen.empfehlungen(thema, fach) if nichts_gefunden
                   else lektionen.verfuegbar(fach))
    return render(request, "adaptiv_auswahl.html", lektionen=suggestions, thema=thema,
                  nichts_gefunden=nichts_gefunden, fach=fach, **ctx)


def _wartet(request: Request, thema: str, topic_id: int | None = None, fach: str = ""):
    ctx = _context(request)
    query = urlencode({"thema": thema, "topic_id": topic_id or "", "fach": fach})
    return render(request, "adaptiv_wartet.html", thema=thema, topic_id=topic_id,
                  status_url=ctx["learning_base"] + "/status?" + query,
                  resume_url=ctx["learning_base"] + "/wartet?" + query, **ctx)


@router.get("", response_class=HTMLResponse)
@exam_router.get("", response_class=HTMLResponse)
def start(request: Request):
    if _aus():
        return zurueck(_context(request)["learning_back"])
    active = _laufende(request)
    return _zeige(request, active) if active else _auswahl(request)


@router.post("/start", response_class=HTMLResponse)
@exam_router.post("/start", response_class=HTMLResponse)
def start_thema(request: Request, thema: str = Form(""),
                topic_id: str = Form(""), posted_exam_id: str = Form("", alias="exam_id"),
                fach: str = Form("")):
    ctx = _context(request)
    # A posted exam_id must never turn a personal URL into an exam journey.
    if posted_exam_id and str(ctx["learning_exam_id"]) != str(posted_exam_id):
        raise HTTPException(404, "Bitte öffne den Lernplan deiner Klassenarbeit.")
    topic = _topic(request, str(topic_id))
    if _aus():
        return _auswahl(request, thema=(topic or {}).get("label", thema))
    if topic:
        thema = topic["label"]
    if not thema.strip() or len(thema) > 200:
        return _auswahl(request)
    fach, grade = _fach(request, topic, fach), config.load_safe().learner_grade
    if topic is None:
        # Freier Text: gehört er zum aktiven Fach? Sonst SUBJECT_MISMATCH.
        from .. import faecher
        try:
            faecher.pruefe(thema, fach)
        except faecher.SubjectMismatch as exc:
            flash(request, str(exc), "warn")
            return zurueck(f"/lernen/{fach}")
    tid = (topic or {}).get("id")
    previous = store.offene_fuer_thema(tid) if tid else None
    if previous:
        return _zeige(request, previous)
    lesson = lektionen.fuer_thema(thema, fach)
    if lesson is None:
        from ..adaptiv import curriculum_dienst
        cfg = config.load_safe()
        if curriculum_dienst.configured(cfg) or getattr(cfg, "llm_error_creation_enabled", False):
            erzeugung.anfordern(thema, fach=fach, klasse=grade)
            return _wartet(request, thema, tid, fach)
        return _auswahl(request, thema=thema, nichts_gefunden=True, fach=fach)
    previous = store.letzte_fuer_thema(tid, lesson['konzept_id'])
    if previous:
        return _zeige(request, previous)
    warning = _grade_gate(request, store.konzept(lesson['konzept_id']), thema, tid)
    if warning is not None:
        return warning
    return _zeige(request, unterricht.starte(lesson["konzept_id"], thema, tid))


@router.get("/status")
@exam_router.get("/status")
def erzeugung_status(request: Request, thema: str = "", topic_id: str = "", fach: str = ""):
    topic = _topic(request, topic_id)
    if _aus():
        return {"fertig": False, "laeuft": False}
    thema = (topic or {}).get("label", thema)
    fach, grade = _fach(request, topic, fach), config.load_safe().learner_grade
    return {"fertig": lektionen.fuer_thema(thema, fach) is not None,
            "laeuft": erzeugung.laeuft(thema, fach=fach, klasse=grade), "thema": thema}


@router.get("/wartet", response_class=HTMLResponse)
@exam_router.get("/wartet", response_class=HTMLResponse)
def wartet(request: Request, thema: str = "", topic_id: str = "", fach: str = ""):
    topic = _topic(request, topic_id)
    if _aus():
        return _auswahl(request)
    thema = (topic or {}).get("label", thema)
    fach = _fach(request, topic, fach)
    lesson = lektionen.fuer_thema(thema, fach)
    if lesson:
        return start_thema(request, thema=thema, topic_id=topic_id, posted_exam_id="", fach=fach)
    return _wartet(request, thema, (topic or {}).get("id"), fach)


@router.post("/neu", response_class=HTMLResponse)
@exam_router.post("/neu", response_class=HTMLResponse)
def neu(request: Request):
    if _aus():
        return _auswahl(request)
    active = _laufende(request)
    if not active:
        return _auswahl(request)
    if active["zustand"] not in zustand.ENDZUSTAENDE:
        return _zeige(request, active)
    entry = store.eingabe(active["eingabe_id"]) or {}
    warning = _grade_gate(request, store.konzept(active['konzept_id']),
                          entry.get('thema_text', ''), entry.get('topic_id'))
    if warning is not None:
        return warning
    return _zeige(request, unterricht.starte(active["konzept_id"],
        entry.get("thema_text", ""), entry.get("topic_id")))


def _answer(request: Request, action: str, answer: str = ""):
    if _aus():
        return _auswahl(request)
    active = _laufende(request)
    if active is None:
        return zurueck(_context(request)["learning_base"])
    entry = store.eingabe(active['eingabe_id']) or {}
    warning = _grade_gate(request, store.konzept(active['konzept_id']),
                          entry.get('thema_text', ''), entry.get('topic_id'))
    if warning is not None:
        return warning
    screen = unterricht.bildschirm(active)
    expected = {"anker": {"anker"}, "diagnose": {"diagnose"},
                "vorhersage": {"vorhersage"}, "transfer": {"transfer"},
                "aufgabe": {"aufgabe"}, "tipp": {"aufgabe"},
                "weiter": {"haken", "regel", "beispiel", "anders"}}
    # Stale forms cannot skip phases or award additional successes.
    if screen["art"] not in expected[action]:
        return _zeige(request, active)
    if action == "weiter":
        result = (unterricht.weiter_nach_adaptation(active)
                  if active["phase"] == zustand.ADAPTATION else unterricht.weiter(active))
    elif action == "tipp":
        result = unterricht.tipp(active)
    else:
        result = getattr(unterricht, action + "_beantwortet")(active, answer)
    return _zeige(request, result)


@router.post("/anker")
@exam_router.post("/anker")
def anker(request: Request, antwort: str = Form("")):
    return _answer(request, "anker", antwort)


@router.post("/diagnose")
@exam_router.post("/diagnose")
def diagnose(request: Request, antwort: str = Form("")):
    return _answer(request, "diagnose", antwort)


@router.post("/weiter")
@exam_router.post("/weiter")
def weiter(request: Request):
    return _answer(request, "weiter")


@router.post("/aufgabe")
@exam_router.post("/aufgabe")
def aufgabe(request: Request, antwort: str = Form("")):
    return _answer(request, "aufgabe", antwort)


@router.post("/vorhersage")
@exam_router.post("/vorhersage")
def vorhersage(request: Request, antwort: str = Form("")):
    return _answer(request, "vorhersage", antwort)


@router.post("/transfer")
@exam_router.post("/transfer")
def transfer(request: Request, antwort: str = Form("")):
    return _answer(request, "transfer", antwort)


@router.post("/tipp")
@exam_router.post("/tipp")
def tipp(request: Request):
    return _answer(request, "tipp")


@eltern_router.get("", response_class=HTMLResponse)
def eltern_lernfortschritt(request: Request):
    if _aus():
        return zurueck("/eltern")
    entries = store.fortschritt_uebersicht()
    return render(request, "adaptiv_eltern.html", eintraege=entries,
                  nachher=[e for e in entries if e.get("braucht_mensch")],
                  stand_labels=STAND_LABELS)
