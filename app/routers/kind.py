"""Kind-Routen: Quizze, Lerneinheiten, Material.

Reine HTTP-Schicht — die eigentliche Logik lebt in `services/workflow.py`,
damit `lernzyklus.py` dieselben Funktionen aufrufen kann, ohne einen
anderen Router direkt anzusprechen (KaroRefactoring_Plan.md, Abschnitt 10).
"""

import logging
from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse

from .. import quizzes, teaching
from ..teaching import TeachingError
from ..services import workflow
from .shared import flash, zurueck

log = logging.getLogger("karo.kind")
router = APIRouter()


@router.post("/themen/{topic_id}/pruefen")
def quiz_starten(request: Request, topic_id: int, modus: str = Form("bildschirm")):
    return workflow.handle_quiz_starten(request, topic_id, modus)


@router.get("/quiz/{quiz_id}", response_class=HTMLResponse)
def quiz_seite(request: Request, quiz_id: int):
    return workflow.render_quiz_page(request, quiz_id)


@router.get("/quiz/{quiz_id}/status")
def quiz_status(quiz_id: int):
    return {"signatur": workflow.quiz_status_signatur(quiz_id)}


@router.post("/quiz/{quiz_id}/antworten")
async def quiz_antworten(request: Request, quiz_id: int):
    return await workflow.handle_quiz_antworten(request, quiz_id)


@router.post("/quiz/{quiz_id}/blatt")
async def quiz_blatt(request: Request, quiz_id: int,
                     datei: UploadFile | None = None):
    return await workflow.handle_quiz_blatt(request, quiz_id, datei)


@router.get("/quiz/{quiz_id}/drucken", response_class=HTMLResponse)
def quiz_drucken(quiz_id: int, loesungen: str = ""):
    from ..media import sheets
    quiz = quizzes.holen(quiz_id)
    if quiz is None:
        return HTMLResponse("<p>Nicht gefunden.</p>", status_code=404)
    titel = (quiz["thema"] or {}).get("label", "Übung")
    if loesungen == "ja":
        return HTMLResponse(sheets.loesungsblatt(titel, quiz["fragen"]))
    return HTMLResponse(sheets.aufgabenblatt(titel, quiz["fragen"]))


@router.post("/quiz/{quiz_id}/freigabe")
async def quiz_freigabe(request: Request, quiz_id: int):
    return await workflow.handle_quiz_freigabe(request, quiz_id)


@router.post("/themen/{topic_id}/lernen")
def lernen_starten(request: Request, topic_id: int, ausgabe: str = Form("html")):
    try:
        lesson_id = teaching.starten(topic_id, ausgabe)
    except TeachingError as exc:
        flash(request, str(exc), "err")
        return zurueck("/themen")
    flash(request, "Bevor Karo schreibt: soll auch im Netz nach bekannten "
                   "Lernquellen gesucht werden?")
    return zurueck(f"/lernen/{lesson_id}")


@router.get("/lernen/{lesson_id}", response_class=HTMLResponse)
def lernen_seite(request: Request, lesson_id: int):
    return workflow.render_lernen_page(request, lesson_id)


@router.get("/lernen/{lesson_id}/status")
def lernen_status(lesson_id: int):
    return {"signatur": workflow.lernen_status_signatur(lesson_id)}


@router.post("/lernen/{lesson_id}/fragen")
def lernen_fragen(request: Request, lesson_id: int,
                  modus: str = Form("bildschirm")):
    return workflow.handle_lernen_fragen(request, lesson_id, modus)


@router.post("/lernen/{lesson_id}/abbrechen")
def lernen_abbrechen(request: Request, lesson_id: int,
                     prompt_wunsch: str = Form("mehr zum Thema")):
    return workflow.handle_lernen_abbrechen(request, lesson_id, prompt_wunsch)


@router.post("/lernen/{lesson_id}/runde/weiter")
def lernen_naechste_runde(request: Request, lesson_id: int):
    return workflow.handle_lernen_naechste_runde(request, lesson_id)


@router.post("/lernen/{lesson_id}/forschen")
def lernen_forschen(request: Request, lesson_id: int):
    return workflow.handle_lernen_forschen(request, lesson_id)


@router.post("/lernen/{lesson_id}/ausgabe/erneut")
def lernen_ausgabe_erneut(request: Request, lesson_id: int,
                          ausgabe: str = Form("")):
    try:
        teaching.ausgabe_erneut(lesson_id, ausgabe or None)
    except TeachingError as exc:
        flash(request, str(exc), "err")
    else:
        flash(request, "Die Ausgabe wird erneut vorbereitet.")
    return zurueck(f"/lernen/{lesson_id}")


@router.post("/lernen/{lesson_id}/runde/{round_id}/variante")
def lernen_variante(request: Request, lesson_id: int, round_id: int,
                    wunsch: str = Form(""), ausgabe: str = Form("")):
    try:
        teaching.variante_anfordern(round_id, wunsch, ausgabe or None)
    except TeachingError as exc:
        flash(request, str(exc), "err")
    else:
        flash(request, "Karo erzeugt eine weitere Version — das dauert etwas.")
    return zurueck(f"/lernen/{lesson_id}")


@router.get("/material/{round_id}", response_class=HTMLResponse)
def material(round_id: int):
    return workflow.render_material(round_id)


@router.get("/material/{round_id}/notebooklm-quelle", response_class=PlainTextResponse)
def material_notebooklm_quelle(round_id: int):
    return workflow.render_material_notebooklm_quelle(round_id)


@router.get("/material/variante/{variant_id}", response_class=HTMLResponse)
def material_variante(variant_id: int):
    return workflow.render_material_variante(variant_id)


@router.get("/material/variante/{variant_id}/notebooklm-quelle",
         response_class=PlainTextResponse)
def material_variante_notebooklm_quelle(variant_id: int):
    return workflow.render_material_variante_notebooklm_quelle(variant_id)
