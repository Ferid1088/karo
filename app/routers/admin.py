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

from .. import config, db, security, teaching
from ..services import exam, measurement
from ..services.exam import ExamError
from .shared import render, flash, zurueck

log = logging.getLogger("karo.admin")
router = APIRouter()


@router.get("/klassenarbeit", response_class=HTMLResponse)
def klassenarbeit(request: Request):
    return measurement.render_klassenarbeit(request)


@router.post("/klassenarbeit")
def klassenarbeit_neu(request: Request, exam_date: str = Form(...),
                      scan_id: str = Form("")):
    try:
        ergebnis = exam.create_exam(exam_date, scan_id)
    except ExamError as exc:
        flash(request, str(exc), "warn")
        return zurueck("/klassenarbeit")
    flash(request, f"Prognose für {ergebnis.themen_eingefroren} Themen eingefroren. "
                   "Karo erstellt jetzt einen Lernplan.")
    return zurueck("/klassenarbeit")


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
    as_json = "application/json" in request.headers.get("accept", "")
    try:
        material_id = exam.start_exam_learning_day(exam_id, row_key, ausgabe)
    except teaching.TeachingError as exc:
        if as_json:
            return JSONResponse({"fehler": str(exc)}, status_code=400)
        return render(request, "material_fehler.html", error=str(exc), status_code=400)
    if as_json:
        return exam.get_exam_material(material_id)
    return zurueck(f"/klassenarbeit/material/{material_id}")


@router.get("/klassenarbeit/material/{material_id}", response_class=HTMLResponse)
def klassenarbeit_material(request: Request, material_id: int):
    material = exam.get_exam_material(material_id)
    if material is None:
        raise HTTPException(404, "Lernmaterial nicht gefunden.")
    return render(request, "klassenarbeit_material.html", material=material,
                  auswertung=exam.get_exam_material_evaluation(material))


@router.get("/klassenarbeit/material/{material_id}/status")
def klassenarbeit_material_status(material_id: int):
    material = exam.get_exam_material(material_id)
    if material is None:
        raise HTTPException(404, "Lernmaterial nicht gefunden.")
    material["signatur"] = material["state"]
    return material


@router.post("/klassenarbeit/material/{material_id}/fragen")
def klassenarbeit_material_fragen(request: Request, material_id: int):
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
