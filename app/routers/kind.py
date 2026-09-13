"""Kind-Routen: Quizze, Lerneinheiten, Material."""

import logging
from pathlib import Path
from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, FileResponse
from starlette.concurrency import run_in_threadpool

from .. import config, db, ingest, quizzes, teaching
from ..quizzes import QuizError
from ..services import workflow
from ..teaching import TeachingError
from .shared import render, flash, zurueck

log = logging.getLogger("karo.kind")
router = APIRouter()


@router.post("/themen/{topic_id}/pruefen")
def quiz_starten(request: Request, topic_id: int, modus: str = Form("bildschirm")):
    try:
        quiz_id = quizzes.anfordern(topic_id, anlass="evaluation", modus=modus)
    except QuizError as exc:
        flash(request, str(exc), "err")
        return zurueck("/themen")
    flash(request, "Die Fragen werden erstellt.")
    return zurueck(f"/quiz/{quiz_id}")


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
    formular = await request.form()
    datei = datei or formular.get("datei")
    if datei is None or not getattr(datei, "filename", ""):
        flash(request, "Es wurde keine Datei ausgewählt.", "err")
        return zurueck(f"/quiz/{quiz_id}")

    endung = Path(datei.filename).suffix.lower()
    puffer = bytearray()
    while stueck := await datei.read(1 << 20):
        puffer.extend(stueck)
        if len(puffer) > 25 * 1024 * 1024:
            flash(request, f"Die Datei ist zu groß.", "err")
            return zurueck(f"/quiz/{quiz_id}")

    try:
        await run_in_threadpool(quizzes.blatt_hochladen, quiz_id, bytes(puffer), endung)
    except (QuizError, ingest.IngestError) as exc:
        flash(request, str(exc), "err")
        return zurueck(f"/quiz/{quiz_id}")

    flash(request, "Antwortblatt aufgenommen. Karo liest es jetzt ab.")
    return zurueck(f"/quiz/{quiz_id}")


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
    try:
        quiz_id = teaching.fragen_anfordern(lesson_id, modus)
    except (TeachingError, QuizError) as exc:
        flash(request, str(exc), "err")
        return zurueck(f"/lernen/{lesson_id}")
    flash(request, "Die Verständnisfragen werden erstellt.")
    return zurueck(f"/quiz/{quiz_id}")


@router.post("/lernen/{lesson_id}/abbrechen")
def lernen_abbrechen(request: Request, lesson_id: int,
                     prompt_wunsch: str = Form("mehr zum Thema")):
    alte = teaching.holen(lesson_id)
    if alte is None:
        flash(request, "Lerneinheit nicht gefunden.", "err")
        return zurueck("/themen")
    teaching.abbrechen(lesson_id, "Neue Erklärung angefordert")
    try:
        # Bewusst KEIN alte["ausgabe"]: das wuerde das Format der allerersten
        # Runde fuer immer festschreiben. starten() ohne eigene Angabe greift
        # auf die aktuellen Einstellungen zurueck — "Mehr zum Thema" benutzt
        # also immer das, was gerade unter Einstellungen gewaehlt ist.
        neue_id = teaching.starten(alte["topic_id"], None, prompt_wunsch)
    except TeachingError as exc:
        flash(request, str(exc), "err")
        return zurueck("/themen")
    flash(request, "Neue Erklärung wird vorbereitet. Die bisherigen Inhalte "
           "und Videos bleiben erhalten.")
    return zurueck(f"/lernen/{neue_id}")


@router.post("/lernen/{lesson_id}/runde/weiter")
def lernen_naechste_runde(request: Request, lesson_id: int):
    try:
        teaching.naechste_runde_bestaetigen(lesson_id)
    except TeachingError as exc:
        flash(request, str(exc), "err")
    return zurueck(f"/lernen/{lesson_id}")


@router.post("/lernen/{lesson_id}/forschen")
def lernen_forschen(request: Request, lesson_id: int):
    try:
        ok = teaching.forschung_anfordern(lesson_id)
    except TeachingError as exc:
        flash(request, str(exc), "err")
        return zurueck(f"/lernen/{lesson_id}")
    if ok:
        flash(request, "Karo sucht auf den zugelassenen Seiten. Diese Seite "
                       "in ein bis zwei Minuten neu laden.")
    else:
        flash(request, "Die Recherche ist ausgeschaltet oder läuft schon "
                       "für heute.", "warn")
    return zurueck(f"/lernen/{lesson_id}")


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


def _material_antwort(pfad_text: str | None):
    if not pfad_text:
        return HTMLResponse("<p>Noch kein Material vorhanden.</p>",
                            status_code=404)
    pfad = Path(pfad_text)
    if not pfad.is_file():
        return HTMLResponse("<p>Die Datei ist nicht mehr da.</p>",
                            status_code=404)
    if pfad.suffix.lower() == ".mp4":
        return FileResponse(pfad, media_type="video/mp4", filename=pfad.name)
    if pfad.suffix.lower() == ".txt":
        return PlainTextResponse(pfad.read_text(encoding="utf-8"))
    return HTMLResponse(pfad.read_text(encoding="utf-8"))


@router.get("/material/{round_id}", response_class=HTMLResponse)
def material(round_id: int):
    archiv = _archiv_antwort("runde", round_id)
    if archiv is not None:
        return archiv
    runde = db.q1("SELECT material_pfad FROM lesson_round WHERE id = ?", round_id)
    return _material_antwort(runde["material_pfad"] if runde else None)


@router.get("/material/{round_id}/notebooklm-quelle", response_class=PlainTextResponse)
def material_notebooklm_quelle(round_id: int):
    runde = db.q1(
        "SELECT notebooklm_quelle_pfad FROM lesson_round WHERE id = ?", round_id)
    return _material_antwort(runde["notebooklm_quelle_pfad"] if runde else None)


@router.get("/material/variante/{variant_id}", response_class=HTMLResponse)
def material_variante(variant_id: int):
    archiv = _archiv_antwort("variante", variant_id)
    if archiv is not None:
        return archiv
    v = db.q1("SELECT material_pfad FROM lesson_round_variant WHERE id = ?",
             variant_id)
    return _material_antwort(v["material_pfad"] if v else None)


def _archiv_antwort(art: str, referenz: int):
    import hashlib
    import os
    import tempfile
    from urllib.parse import quote
    from .. import materials
    m = materials.holen(art, referenz)
    if m is None:
        # Bestehende Materialien beim ersten Öffnen ebenfalls archivieren.
        table = "lesson_round" if art == "runde" else "lesson_round_variant"
        row = db.q1(f"SELECT material_pfad FROM {table} WHERE id=?", referenz)
        if not row or not row["material_pfad"] or not Path(row["material_pfad"]).is_file():
            return None
        materials.bestand_uebernehmen()
        m = materials.holen(art, referenz)
        if m is None:
            return None
    if m["mime"] == "video/mp4":
        # FileResponse unterstützt Range-Requests für Springen/Spulen im Video.
        digest = hashlib.sha256(m["inhalt"]).hexdigest()
        cache = config.media_dir() / f"archiv-{digest}.mp4"
        if not cache.exists():
            fd, temp = tempfile.mkstemp(dir=cache.parent, prefix=".video-")
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(m["inhalt"])
                os.replace(temp, cache)
            finally:
                Path(temp).unlink(missing_ok=True)
        return FileResponse(cache, media_type=m["mime"], filename=m["dateiname"],
                            content_disposition_type="inline")
    return HTMLResponse(m["inhalt"], headers={
        "Content-Disposition": "inline; filename*=UTF-8''" + quote(m["dateiname"])})


@router.get("/material/variante/{variant_id}/notebooklm-quelle",
         response_class=PlainTextResponse)
def material_variante_notebooklm_quelle(variant_id: int):
    v = db.q1(
        "SELECT notebooklm_quelle_pfad FROM lesson_round_variant WHERE id = ?",
        variant_id)
    return _material_antwort(v["notebooklm_quelle_pfad"] if v else None)
