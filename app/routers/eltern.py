"""Eltern-Routen: Wissensbasis, Dashboard, Fortschritt, Entscheidungen."""

import json
import logging
from pathlib import Path
from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from starlette.concurrency import run_in_threadpool

from .. import config, db, export, ingest, kb, quizzes, research, topics, jobs
from ..domain import FLAG_ORDER, Flag, FLAG_LABELS
from .shared import render, flash, zurueck

log = logging.getLogger("karo.eltern")
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    themen = topics.liste(topics.AKTIV)
    themen.sort(key=lambda t: (FLAG_ORDER.index(t["flag"])
                               if t["flag"] in FLAG_ORDER else 9, t["sort"]))
    zaehler = {f: sum(1 for t in themen if t["flag"] == f) for f in FLAG_ORDER}
    return render(
        request, "dashboard.html",
        themen=themen, zaehler=zaehler,
        kb_stat=kb.statistik(),
        offene_quizze=quizzes.offene(),
        offene_lessons=__import__("app.teaching", fromlist=["offene"]).offene(),
        fehler=[dict(r) for r in db.q(
            "SELECT * FROM job WHERE state='fehler' ORDER BY id DESC LIMIT 20")],
        counts=jobs.counts(),
        einig=quizzes.uebereinstimmung(),
    )


@router.get("/wissen", response_class=HTMLResponse)
def wissen(request: Request):
    docu = [dict(r) for r in db.q(
        """SELECT id, rolle, zustand, seite, created_at FROM document
           ORDER BY created_at DESC LIMIT 50""")]
    return render(request, "wissen.html", dokumente=docu, counts=jobs.counts())


@router.post("/wissen/einlesen")
async def wissen_einlesen(request: Request, quelle: str = Form("upload")):
    if quelle == "drive":
        try:
            ok = await run_in_threadpool(ingest.von_drive)
        except ingest.IngestError as exc:
            flash(request, str(exc), "err")
        else:
            flash(request, "Drive wird gelesen." if ok else
                  "Kein Drive-Ordner eingerichtet oder nichts Neues darin.")
    return zurueck("/wissen")


@router.post("/wissen/upload")
async def wissen_upload(request: Request, rolle: str = Form("wissen"),
                       datei: UploadFile | None = None):
    formular = await request.form()
    datei = datei or formular.get("datei")
    if datei is None or not getattr(datei, "filename", ""):
        flash(request, "Es wurde keine Datei ausgewählt.", "err")
        return zurueck("/wissen")

    endung = Path(datei.filename).suffix.lower()
    puffer = bytearray()
    while stueck := await datei.read(1 << 20):
        puffer.extend(stueck)
        if len(puffer) > 25 * 1024 * 1024:
            flash(request, "Datei zu groß.", "err")
            return zurueck("/wissen")

    try:
        await run_in_threadpool(ingest.datei, bytes(puffer), endung, rolle)
    except ingest.IngestError as exc:
        flash(request, str(exc), "err")
    else:
        flash(request, "Datei eingereicht — Karo liest sie jetzt.")
    return zurueck("/wissen")


@router.get("/scan/{doc_id}.jpg")
def scan(doc_id: int):
    from ..media import ingest_view
    return ingest_view.scan_thumbnail(doc_id)


@router.get("/wissen/{doc_id}", response_class=HTMLResponse)
def wissen_detail(request: Request, doc_id: int):
    doc = db.q1("SELECT * FROM document WHERE id = ?", doc_id)
    if doc is None:
        flash(request, "Blatt nicht gefunden.", "err")
        return zurueck("/wissen")
    abschnitte = [dict(r) for r in db.q(
        """SELECT k.*, t.label AS thema_label FROM kb_chunk k
             LEFT JOIN topic t ON t.id = k.topic_id
            WHERE k.document_id=? ORDER BY k.position""", doc_id)]
    return render(request, "wissen_blatt.html", doc=dict(doc),
                  abschnitte=abschnitte)


@router.get("/themen", response_class=HTMLResponse)
def themen(request: Request):
    aktive = topics.liste(topics.AKTIV)
    aktive.sort(key=lambda t: (FLAG_ORDER.index(t["flag"])
                               if t["flag"] in FLAG_ORDER else 9, t["sort"]))
    for t in aktive:
        t["verlauf"] = quizzes.verlauf(t["id"])
    return render(request, "themen.html",
                  vorschlaege=topics.liste(topics.VORSCHLAG),
                  aktive=aktive, einig=quizzes.uebereinstimmung())


@router.post("/themen/entscheiden")
async def themen_entscheiden(request: Request):
    formular = await request.form()
    entscheidungen = []
    for schluessel in formular.keys():
        if not schluessel.startswith("aktion_"):
            continue
        roh = schluessel[7:]
        if not roh.isdigit():
            continue
        entscheidungen.append({
            "id": int(roh),
            "aktion": formular.get(schluessel),
            "label": formular.get(f"label_{roh}", ""),
        })
    ergebnis = topics.entscheiden(entscheidungen)
    if ergebnis["angenommen"] or ergebnis["abgelehnt"]:
        flash(request, f"{ergebnis['angenommen']} übernommen, "
                       f"{ergebnis['abgelehnt']} verworfen"
                       + (f", {ergebnis['umbenannt']} umbenannt"
                          if ergebnis["umbenannt"] else "") + ".")
    else:
        flash(request, "Es wurde nichts entschieden.", "warn")
    return zurueck("/themen")


@router.post("/themen/neu")
def themen_neu(request: Request, label: str = Form(""),
               beschreibung: str = Form("")):
    neu = topics.anlegen(label, beschreibung)
    if neu is None:
        flash(request, "Dieses Thema gibt es schon oder der Name ist leer.",
              "warn")
    else:
        flash(request, "Thema angelegt.")
    return zurueck("/themen")


@router.post("/themen/{topic_id}/recherche")
def recherche_starten(request: Request, topic_id: int):
    if research.anfordern(topic_id):
        flash(request, "Karo sucht auf den zugelassenen Seiten.")
    else:
        flash(request, "Die Recherche ist ausgeschaltet oder läuft schon.",
              "warn")
    return zurueck("/recherche")


@router.get("/recherche", response_class=HTMLResponse)
def recherche(request: Request):
    return render(request, "recherche.html",
                  vorschlaege=research.vorschlaege(),
                  erlaubte=sorted(set(research.ERLAUBTE_QUELLEN.values())),
                  kanaele=research.ERLAUBTE_KANAELE,
                  aktiv=config.load_safe().recherche_erlaubt)


@router.post("/recherche/entscheiden")
async def recherche_entscheiden(request: Request):
    import re
    formular = await request.form()
    entscheidungen: dict[int, str] = {}
    for schluessel in formular.keys():
        if not schluessel.startswith("hit_"):
            continue
        roh = schluessel[4:]
        if roh.isdigit():
            entscheidungen[int(roh)] = str(formular.get(schluessel) or "")
    ergebnis = research.entscheiden(entscheidungen)
    flash(request, f"{ergebnis['freigegeben']} freigegeben, "
                   f"{ergebnis['abgelehnt']} abgelehnt.")
    ziel = str(formular.get("zurueck") or "")
    if re.match(r"^/lernen/\d+$", ziel):
        return zurueck(ziel)
    return zurueck("/recherche")


@router.get("/lernstand", response_class=HTMLResponse)
def lernstand(request: Request):
    cfg = config.load_safe()
    return render(request, "lernstand.html",
                  zeilen=export.lernstand_zeilen(),
                  verlauf=export.verlauf_zeilen(limit=200),
                  xlsx_ok=export.verfuegbar(),
                  drive_ok=ingest.drive_available(),
                  drive_writable=ingest.drive_writable(),
                  rule_gruen_tage=cfg.rule_gruen_tage,
                  rule_rot_konzeptfehler=cfg.rule_rot_konzeptfehler,
                  rule_min_evidenz=cfg.rule_min_evidenz)


@router.post("/export")
async def export_jetzt(request: Request):
    pfad = await run_in_threadpool(export.nach_freigabe)
    if pfad:
        flash(request, f"Lernstand als Tabelle geschrieben: "
                       f"{Path(pfad).name}")
    else:
        flash(request, "Der Tabellenexport ist nicht verfügbar.", "warn")
    return zurueck("/lernstand")


@router.post("/vorgang/{job_id}/erneut")
def vorgang_erneut(request: Request, job_id: int):
    if jobs.retry(job_id):
        flash(request, "Vorgang wird erneut versucht.")
    else:
        flash(request, "Dieser Vorgang läuft bereits oder ist abgeschlossen.",
              "warn")
    return zurueck("/")
