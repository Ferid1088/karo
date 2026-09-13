"""Task-oriented entry points for the existing learning and review workflow."""
from fastapi import APIRouter, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse

from .. import config, db, teaching, topics
from ..services import workflow
from .shared import render, flash, zurueck

router = APIRouter(prefix="/lernzyklus", tags=["learning"])


def _lesson_id(topic_id: int):
    row = db.q1("SELECT id FROM lesson WHERE topic_id=? ORDER BY id DESC LIMIT 1", topic_id)
    return row["id"] if row else None


def _require_lesson(topic_id: int):
    lesson_id = _lesson_id(topic_id)
    if lesson_id is None:
        raise HTTPException(404, "Lernrunde nicht gefunden.")
    return lesson_id


def _check_quiz(topic_id: int, quiz_id: int):
    row = db.q1("SELECT topic_id FROM quiz WHERE id=?", quiz_id)
    if not row or row["topic_id"] != topic_id:
        raise HTTPException(404, "Fragerunde nicht gefunden.")


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def lernzyklus_index(request: Request):
    return workflow.render_lernen_uebersicht(request)


@router.get("/{topic_id}", response_class=HTMLResponse)
def lernzyklus_seite(request: Request, topic_id: int):
    topic = topics.get(topic_id)
    if not topic or topic["state"] != topics.AKTIV:
        flash(request, "Bitte zuerst das Thema bestätigen.", "warn")
        return zurueck("/themen")
    lesson_id = _lesson_id(topic_id)
    if lesson_id is not None:
        return workflow.render_lernen_page(request, lesson_id)
    return render(request, "lernzyklus/start.html", topic=topic)


@router.post("/{topic_id}/start")
def lernzyklus_start(request: Request, topic_id: int, ausgabe: str = Form("")):
    try:
        lesson_id = teaching.starten(topic_id, ausgabe or config.load_safe().default_ausgabe)
    except teaching.TeachingError as exc:
        flash(request, str(exc), "err")
        return zurueck("/lernzyklus")
    lesson = teaching.holen(lesson_id)
    if lesson and lesson['state'] == 'wartet' and lesson['runden'] == 0:
        try:
            teaching.naechste_runde_bestaetigen(lesson_id)
        except teaching.TeachingError:
            pass  # Die Lernseite zeigt den Weg zum fehlenden Schulmaterial.
    return zurueck(f"/lernen/{lesson_id}")


@router.post("/{topic_id}/quiz/starten")
def lernzyklus_quiz_starten(request: Request, topic_id: int, modus: str = Form("bildschirm")):
    return workflow.handle_quiz_or_lernen_start(request, topic_id, modus)


@router.get("/{topic_id}/quiz/{quiz_id}", response_class=HTMLResponse)
def lernzyklus_quiz(request: Request, topic_id: int, quiz_id: int):
    _check_quiz(topic_id, quiz_id)
    return workflow.render_quiz_page(request, quiz_id)


@router.post("/{topic_id}/quiz/{quiz_id}/antworten")
async def lernzyklus_quiz_antworten(request: Request, topic_id: int, quiz_id: int):
    _check_quiz(topic_id, quiz_id)
    return await workflow.handle_quiz_antworten(request, quiz_id)


@router.post("/{topic_id}/quiz/{quiz_id}/blatt")
async def lernzyklus_quiz_blatt(request: Request, topic_id: int, quiz_id: int,
                              datei: UploadFile | None = None):
    _check_quiz(topic_id, quiz_id)
    return await workflow.handle_quiz_blatt(request, quiz_id, datei)


@router.post("/{topic_id}/quiz/{quiz_id}/freigabe")
async def lernzyklus_quiz_freigabe(request: Request, topic_id: int, quiz_id: int):
    _check_quiz(topic_id, quiz_id)
    return await workflow.handle_quiz_freigabe(request, quiz_id)


@router.post("/{topic_id}/runde/weiter")
def lernzyklus_runde_weiter(request: Request, topic_id: int):
    return workflow.handle_lernen_naechste_runde(request, _require_lesson(topic_id))


@router.post("/{topic_id}/forschen")
def lernzyklus_forschen(request: Request, topic_id: int):
    return workflow.handle_lernen_forschen(request, _require_lesson(topic_id))


@router.post("/{topic_id}/abbrechen")
def lernzyklus_abbrechen(request: Request, topic_id: int):
    return workflow.handle_lernen_abbrechen(request, _require_lesson(topic_id), "mehr zum Thema")


@router.get("/{topic_id}/material/{round_id}", response_class=HTMLResponse)
def lernzyklus_material(topic_id: int, round_id: int):
    row = db.q1("SELECT l.topic_id FROM lesson_round r JOIN lesson l ON l.id=r.lesson_id WHERE r.id=?", round_id)
    if not row or row["topic_id"] != topic_id:
        raise HTTPException(404, "Material nicht gefunden.")
    return workflow.render_material(round_id)
