"""Task-oriented entry points for the existing learning and review workflow."""
from fastapi import APIRouter, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse

from .. import config, db, quizzes, teaching, topics
from ..domain import FLAG_ORDER
from . import kind
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
    themen = topics.liste(topics.AKTIV)
    themen.sort(key=lambda t: (FLAG_ORDER.index(t["flag"]), t["sort"]))
    fortsetzungen = {}
    offene_quizze = quizzes.offene()
    priority = {"geprueft": 0, "bereit": 1, "beantwortet": 2, "offen": 3}
    offene_quizze.sort(key=lambda q: priority.get(q["state"], 4))
    labels = {"offen": "Karo bereitet Fragen vor", "bereit": "Fragen beantworten",
              "beantwortet": "Karo prüft die Antworten", "geprueft": "Für Eltern: Antworten prüfen"}
    for quiz in offene_quizze:
        fortsetzungen.setdefault(quiz["topic_id"], {
            "titel": quiz["thema_label"], "text": labels.get(quiz["state"], "Weiterlernen"),
            "url": f"/quiz/{quiz['id']}"})
    for lesson in teaching.offene():
        fortsetzungen.setdefault(lesson["topic_id"], {
            "titel": lesson["thema_label"],
            "text": "Lernrunde vorbereiten" if lesson["state"] == "wartet" else "Mit der Erklärung weiterlernen",
            "url": f"/lernen/{lesson['id']}"})
    return render(request, "lernzyklus/index.html", hat_themen=bool(themen),
                  themen=[t for t in themen if t["id"] not in fortsetzungen],
                  fortsetzungen=list(fortsetzungen.values()))


@router.get("/{topic_id}", response_class=HTMLResponse)
def lernzyklus_seite(request: Request, topic_id: int):
    topic = topics.get(topic_id)
    if not topic or topic["state"] != topics.AKTIV:
        flash(request, "Bitte zuerst das Thema bestätigen.", "warn")
        return zurueck("/vorbereitung/inhalte")
    lesson_id = _lesson_id(topic_id)
    if lesson_id is not None:
        return kind.lernen_seite(request, lesson_id)
    return render(request, "lernzyklus/start.html", topic=topic)


@router.post("/{topic_id}/start")
def lernzyklus_start(request: Request, topic_id: int, ausgabe: str = Form("")):
    try:
        lesson_id = teaching.starten(topic_id, ausgabe or config.load_safe().default_ausgabe)
    except teaching.TeachingError as exc:
        flash(request, str(exc), "err")
        return zurueck("/lernzyklus")
    return zurueck(f"/lernen/{lesson_id}")


@router.post("/{topic_id}/quiz/starten")
def lernzyklus_quiz_starten(request: Request, topic_id: int, modus: str = Form("bildschirm")):
    lesson_id = _lesson_id(topic_id)
    lesson = teaching.holen(lesson_id) if lesson_id is not None else None
    if lesson and lesson["state"] not in ("gelernt", "abgebrochen"):
        return kind.lernen_fragen(request, lesson_id, modus)
    return kind.quiz_starten(request, topic_id, modus)


@router.get("/{topic_id}/quiz/{quiz_id}", response_class=HTMLResponse)
def lernzyklus_quiz(request: Request, topic_id: int, quiz_id: int):
    _check_quiz(topic_id, quiz_id)
    return kind.quiz_seite(request, quiz_id)


@router.post("/{topic_id}/quiz/{quiz_id}/antworten")
async def lernzyklus_quiz_antworten(request: Request, topic_id: int, quiz_id: int):
    _check_quiz(topic_id, quiz_id)
    return await kind.quiz_antworten(request, quiz_id)


@router.post("/{topic_id}/quiz/{quiz_id}/blatt")
async def lernzyklus_quiz_blatt(request: Request, topic_id: int, quiz_id: int,
                              datei: UploadFile | None = None):
    _check_quiz(topic_id, quiz_id)
    return await kind.quiz_blatt(request, quiz_id, datei)


@router.post("/{topic_id}/quiz/{quiz_id}/freigabe")
async def lernzyklus_quiz_freigabe(request: Request, topic_id: int, quiz_id: int):
    _check_quiz(topic_id, quiz_id)
    return await kind.quiz_freigabe(request, quiz_id)


@router.post("/{topic_id}/runde/weiter")
def lernzyklus_runde_weiter(request: Request, topic_id: int):
    return kind.lernen_naechste_runde(request, _require_lesson(topic_id))


@router.post("/{topic_id}/forschen")
def lernzyklus_forschen(request: Request, topic_id: int):
    return kind.lernen_forschen(request, _require_lesson(topic_id))


@router.post("/{topic_id}/abbrechen")
def lernzyklus_abbrechen(request: Request, topic_id: int):
    return kind.lernen_abbrechen(request, _require_lesson(topic_id))


@router.get("/{topic_id}/material/{round_id}", response_class=HTMLResponse)
def lernzyklus_material(topic_id: int, round_id: int):
    row = db.q1("SELECT l.topic_id FROM lesson_round r JOIN lesson l ON l.id=r.lesson_id WHERE r.id=?", round_id)
    if not row or row["topic_id"] != topic_id:
        raise HTTPException(404, "Material nicht gefunden.")
    return kind.material(round_id)
