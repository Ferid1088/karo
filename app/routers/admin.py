"""Admin-Routen: Klassenarbeit, Protokoll.

Reine HTTP-Schicht: Formulardaten entgegennehmen, den passenden Service
aufrufen, Fehler in Flash-Meldungen uebersetzen, Redirect/Response
zurueckgeben. Die eigentliche Klassenarbeits-Logik lebt in
`services/exam.py`, die Uebersicht in `services/measurement.py`
(change.txt Abschnitt 2).

`/protokoll` bleibt hier: eine reine, folgenlose Lese-Anzeige ohne
Geschaeftsentscheidung, fuer die ein eigener Service keinen Mehrwert
haette (change.txt Abschnitt 3: "Do not move trivial presentation-only
reads if doing so adds complexity for no benefit").
"""

import datetime as dt
import logging
from pathlib import Path
from fastapi import APIRouter, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from .. import config, db, quizzes, security, teaching, topics
from ..services import exam, exam_calendar, learning_progress, measurement
from ..services.exam import ExamError
from .shared import alter_generator_aus, render, flash, zurueck

log = logging.getLogger("karo.admin")
router = APIRouter()


@router.get("/klassenarbeit", response_class=HTMLResponse)
def klassenarbeit(request: Request, monat: str = ""):
    return measurement.render_klassenarbeit(request, monat)


@router.post("/klassenarbeit")
def klassenarbeit_neu(request: Request, exam_date: str = Form(...),
                      scan_id: str = Form(""), themen: str = Form(""), fach: str = Form("")):
    try:
        ergebnis = exam.create_exam(exam_date, scan_id, themen, fach)
    except ExamError as exc:
        flash(request, str(exc), "warn")
        return zurueck("/klassenarbeit")
    flash(request, "Deine Klassenarbeit ist angelegt. Wähle jetzt deine Lerntage.")
    return zurueck(f"/klassenarbeit#exam-{ergebnis.exam_id}")


@router.post("/klassenarbeit/themenblatt")
async def klassenarbeit_themenblatt(request: Request,
                                    datei: UploadFile | None = None):
    formular = await request.form()
    datei = datei or formular.get("datei")
    if datei is None or not getattr(datei, "filename", ""):
        flash(request, "Es wurde keine Datei ausgewählt.", "err")
        return zurueck("/klassenarbeit")

    endung = Path(datei.filename).suffix.lower()
    puffer = bytearray()
    while stueck := await datei.read(1 << 20):
        puffer.extend(stueck)
        if len(puffer) > security.MAX_UPLOAD_BYTES:
            flash(request, "Die Datei ist zu groß.", "err")
            return zurueck("/klassenarbeit")

    try:
        exam.upload_exam_topics_sheet(bytes(puffer), endung)
    except ExamError as exc:
        flash(request, str(exc), "err")
        return zurueck("/klassenarbeit")

    flash(request, "Themenblatt aufgenommen. Karo liest es jetzt ein.")
    return zurueck("/klassenarbeit")


@router.get("/klassenarbeit/themenblatt/status")
def klassenarbeit_themenblatt_status(scan_id: int):
    return {"signatur": exam.get_exam_topic_scan_status(scan_id)}


@router.post("/klassenarbeit/{exam_id}/kalender")
async def klassenarbeit_kalender(request: Request, exam_id: int):
    formular = await request.form()
    minuten = {
        key.removeprefix("minutes_"): value
        for key, value in formular.multi_items()
        if key.startswith("minutes_")
    }
    try:
        exam_calendar.save_days(exam_id, minuten)
        exam_calendar.set_simulation_early(
            exam_id, formular.get("simulation_early") == "ja")
    except exam_calendar.ExamCalendarError as exc:
        flash(request, str(exc), "warn")
        return zurueck(f"/klassenarbeit#exam-{exam_id}")
    flash(request, "Dein Lernkalender ist gespeichert. Heutige Lerntage erscheinen unter „Heute“.")
    return zurueck(f"/klassenarbeit#exam-{exam_id}")


@router.get("/klassenarbeit/{exam_id}/simulation", response_class=HTMLResponse)
def klassenarbeit_simulation(request: Request, exam_id: int):
    if not exam_calendar.simulation_available(exam_id):
        raise HTTPException(403, "Die Prüfungssimulation ist erst am geplanten Simulationstag verfügbar.")
    return render(
        request, "exam_simulation.html",
        exam_id=exam_id,
        themen=exam_calendar.simulation_topics(exam_id),
    )


@router.post("/klassenarbeit/{exam_id}/simulation/{topic_id}")
def klassenarbeit_simulation_starten(request: Request, exam_id: int, topic_id: int):
    if not exam_calendar.simulation_available(exam_id):
        raise HTTPException(403, "Die Prüfungssimulation ist heute nicht verfügbar.")
    erlaubt = {t["id"] for t in exam_calendar.simulation_topics(exam_id)}
    if topic_id not in erlaubt:
        raise HTTPException(404, "Dieses Thema gehört nicht zu dieser Klassenarbeit.")
    quiz_id = quizzes.anfordern(topic_id, anlass="probe", modus=quizzes.BILDSCHIRM, anzahl=5)
    return zurueck(f"/quiz/{quiz_id}")


@router.post("/klassenarbeit/{exam_id}/plan/neu")
def klassenarbeit_plan_neu(request: Request, exam_id: int):
    try:
        exam.regenerate_exam_plan(exam_id)
    except ExamError as exc:
        flash(request, str(exc), "err")
        return zurueck("/klassenarbeit")
    flash(request, "Lernplan wird neu erstellt.")
    return zurueck("/klassenarbeit")


@router.post("/klassenarbeit/{exam_id}/lerntag")
def klassenarbeit_lerntag(request: Request, exam_id: int,
                          row_key: str = Form(...), ausgabe: str = Form("")):
    # Lernmaterial zur Klassenarbeit entsteht im selben alten
    # Erzeugungsweg (`exam_learning.starten()` → `teaching.starten()`).
    if alter_generator_aus():
        return zurueck("/lernen")
    as_json = "application/json" in request.headers.get("accept", "")
    try:
        material_id = exam.start_exam_learning_day(exam_id, row_key, ausgabe)
    except teaching.TeachingError as exc:
        if as_json:
            return JSONResponse({"fehler": str(exc)}, status_code=400)
        return render(request, "material_fehler.html", error=str(exc), status_code=400)
    material = exam.get_exam_material(material_id)
    if request.session.get('role') == 'child':
        learning_progress.start(teaching.holen(material['lesson_id'])['topic_id'])
    if as_json:
        return material
    return zurueck(f"/klassenarbeit/material/{material_id}")


@router.get("/klassenarbeit/material/{material_id}", response_class=HTMLResponse)
def klassenarbeit_material(request: Request, material_id: int):
    if alter_generator_aus():
        return zurueck("/lernen")
    material = exam.get_exam_material(material_id)
    if material is None:
        raise HTTPException(404, "Lernmaterial nicht gefunden.")
    topic_id = teaching.holen(material['lesson_id'])['topic_id']
    if request.session.get('role') == 'child':
        learning_progress.start(topic_id)
    return render(request, "klassenarbeit_material.html", material=material,
                  progress_topic=topics.get(topic_id),
                  adult_page=request.session.get("role") == "parent" and not config.load().klassenarbeit_kind,
                  auswertung=exam.get_exam_material_evaluation(material))


@router.get("/klassenarbeit/material/{material_id}/status")
def klassenarbeit_material_status(material_id: int):
    if alter_generator_aus():
        return zurueck("/lernen")
    material = exam.get_exam_material(material_id)
    if material is None:
        raise HTTPException(404, "Lernmaterial nicht gefunden.")
    material["signatur"] = material["state"]
    return material


@router.post("/klassenarbeit/material/{material_id}/fragen")
def klassenarbeit_material_fragen(request: Request, material_id: int):
    if alter_generator_aus():
        return zurueck("/lernen")
    try:
        quiz_id = exam.request_exam_questions(material_id)
    except teaching.TeachingError as exc:
        flash(request, str(exc), "err")
        return zurueck(f"/klassenarbeit/material/{material_id}")
    return zurueck(f"/quiz/{quiz_id}")


@router.get("/klassenarbeit/{exam_id}/plan/status")
def klassenarbeit_plan_status(exam_id: int):
    return {"signatur": exam.get_exam_plan_status(exam_id)}


@router.post("/klassenarbeit/{exam_id}/ergebnis")
async def klassenarbeit_ergebnis(request: Request, exam_id: int):
    formular = await request.form()
    n = exam.save_exam_results(exam_id, formular)
    flash(request, f"{n} Ergebnis eingetragen." if n == 1
          else f"{n} Ergebnisse eingetragen.")
    return zurueck("/klassenarbeit")


# Steht bewusst hinter allen festen Pfaden (/klassenarbeit/themenblatt,
# /klassenarbeit/material/...): eine Zahl im Pfad faengt sonst nichts davon ab.
@router.get("/klassenarbeit/{exam_id}", response_class=HTMLResponse)
def klassenarbeit_detail(request: Request, exam_id: int):
    return measurement.render_klassenarbeit_detail(request, exam_id)


@router.get("/protokoll", response_class=HTMLResponse)
def protokoll(request: Request):
    zeilen = [dict(r) for r in db.q(
        """SELECT id, purpose, backend, model, had_image, schema_ok, error,
                  tokens_in, tokens_out, cost_usd, duration_ms, created_at
             FROM llm_call ORDER BY id DESC LIMIT 120""")]
    gesamt = dict(db.q1(
        "SELECT COUNT(*) AS n, COALESCE(SUM(cost_usd),0) AS c FROM llm_call"))
    monat = dict(db.q1(
        "SELECT COUNT(*) AS n, COALESCE(SUM(cost_usd),0) AS c FROM llm_call "
        "WHERE created_at >= ?", dt.date.today().replace(day=1).isoformat()))
    return render(request, "protokoll.html", zeilen=zeilen, gesamt=gesamt,
                  monat=monat, backend=config.load_safe().llm_backend)


@router.get("/protokoll/{call_id}", response_class=HTMLResponse)
def protokoll_detail(request: Request, call_id: int):
    zeile = db.q1("SELECT * FROM llm_call WHERE id = ?", call_id)
    if zeile is None:
        return HTMLResponse("<p>Nicht gefunden.</p>", status_code=404)
    return render(request, "protokoll_detail.html", zeile=dict(zeile))
