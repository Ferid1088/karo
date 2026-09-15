"""Eltern-Routen: Wissensbasis, Themen, Recherche, Lernstand.

Reine HTTP-Schicht — die eigentliche Logik lebt in `services/preparation.py`
und `services/measurement.py`, damit `vorbereitung.py`/`messung.py`
dieselben Funktionen aufrufen koennen, ohne diesen Router direkt
anzusprechen (KaroRefactoring_Plan.md, Abschnitt 10).
"""

import logging
from pathlib import Path
from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, FileResponse

from .. import db, jobs
from ..services import measurement, preparation
from .shared import render, flash, zurueck

log = logging.getLogger("karo.eltern")
router = APIRouter()


@router.get("/wissen", response_class=HTMLResponse)
def wissen(request: Request):
    return preparation.render_wissen(request)


@router.post("/wissen/einlesen")
async def wissen_einlesen(request: Request, quelle: str = Form("drive")):
    return await preparation.handle_wissen_einlesen(request, quelle)


@router.post("/wissen/upload")
async def wissen_upload(request: Request, rolle: str = Form("wissen"),
                       datei: UploadFile | None = None):
    return await preparation.handle_wissen_upload(request, rolle, datei)


@router.get("/scan/{doc_id}.jpg")
def scan(request: Request, doc_id: int):
    doc = db.q1("SELECT stored_path, rolle FROM document WHERE id=?", doc_id)
    if (not doc or (request.session.get("role") == "child" and doc["rolle"] != "wissen")
            or not Path(doc["stored_path"]).is_file()):
        return HTMLResponse("Blatt nicht gefunden.", status_code=404)
    return FileResponse(doc["stored_path"], media_type="image/jpeg")


@router.get("/wissen/{doc_id}", response_class=HTMLResponse)
def wissen_detail(request: Request, doc_id: int):
    return preparation.render_wissen_detail(request, doc_id)


@router.get("/themen", response_class=HTMLResponse)
def themen(request: Request):
    return preparation.render_themen(request)


@router.post("/themen/entscheiden")
async def themen_entscheiden(request: Request):
    return await preparation.handle_themen_entscheiden(request)


@router.post("/themen/neu")
def themen_neu(request: Request, label: str = Form(""),
               beschreibung: str = Form("")):
    return preparation.handle_themen_neu(request, label, beschreibung)


@router.post("/themen/{topic_id}/recherche")
def recherche_starten(request: Request, topic_id: int):
    return preparation.handle_recherche_starten(request, topic_id)


@router.get("/recherche", response_class=HTMLResponse)
def recherche(request: Request):
    return preparation.render_recherche(request)


@router.post("/recherche/quellen/hinzufuegen")
async def recherche_quelle_hinzufuegen(request: Request):
    return await preparation.handle_recherche_quelle_hinzufuegen(request)


@router.post("/recherche/quellen/aktivieren")
async def recherche_quelle_aktivieren(request: Request):
    return await preparation.handle_recherche_quelle_aktivieren(request)


@router.post("/recherche/entscheiden")
async def recherche_entscheiden(request: Request):
    return await preparation.handle_recherche_entscheiden(request)


@router.get("/lernstand", response_class=HTMLResponse)
def lernstand(request: Request):
    return measurement.render_lernstand(request)


@router.get("/hilfe", response_class=HTMLResponse)
def hilfe(request: Request):
    return render(request, "hilfe.html")


@router.post("/export")
async def export_jetzt(request: Request):
    return await measurement.handle_export(request, "/lernstand")


@router.post("/vorgang/{job_id}/erneut")
def vorgang_erneut(request: Request, job_id: int):
    if jobs.retry(job_id):
        flash(request, "Vorgang wird erneut versucht.")
    else:
        flash(request, "Dieser Vorgang läuft bereits oder ist abgeschlossen.",
              "warn")
    return zurueck("/")
