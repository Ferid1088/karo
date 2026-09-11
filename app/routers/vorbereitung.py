"""Vorbereitung (Preparation) - Schulmaterial & Inhalte genehmigen (merged Wissen + Themen + Recherche)."""

import json
import logging
import re
from pathlib import Path
from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from starlette.concurrency import run_in_threadpool

from .. import config, db, ingest, jobs, kb, quizzes, research, topics
from .shared import render, flash, zurueck

log = logging.getLogger("karo.vorbereitung")
router = APIRouter(prefix="/vorbereitung", tags=["preparation"])


# ─────────────────────────────────────────────────────────────────────────────
# SCHULMATERIAL (merged from wissen.py)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def schulmaterial_index(request: Request):
    """Schulmaterial - Upload & manage materials."""
    docu = [dict(r) for r in db.q(
        """SELECT d.*, (SELECT COUNT(*) FROM kb_chunk k WHERE k.document_id=d.id)
                   AS abschnitte FROM document d WHERE d.rolle='wissen'
           ORDER BY d.created_at DESC LIMIT 50""")]
    return render(request, "vorbereitung/schulmaterial.html",
                  dokumente=docu, counts=jobs.counts(),
                  kb_stat=kb.statistik(), drive_ok=ingest.drive_available())


@router.post("/schulmaterial/einlesen")
async def schulmaterial_einlesen(request: Request, quelle: str = Form("drive")):
    """Read from Drive folder."""
    if quelle == "drive":
        try:
            ok = await run_in_threadpool(ingest.scan_inbox)
            for result in ok:
                if result.get("status") == "neu":
                    doc_id = result["document_id"]
                    jobs.enqueue("kb_extract", {"document_id": doc_id},
                                 dedup_key=f"kb_extract:{doc_id}")
        except ingest.IngestError as exc:
            flash(request, str(exc), "err")
        else:
            flash(request, "Drive wird gelesen." if ok else
                  "Kein Drive-Ordner eingerichtet oder nichts Neues darin.")
    return zurueck("/vorbereitung")


@router.post("/schulmaterial/hochladen")
async def schulmaterial_hochladen(request: Request, datei: UploadFile | None = None):
    """Upload material directly."""
    formular = await request.form()
    datei = datei or formular.get("datei")
    if datei is None or not getattr(datei, "filename", ""):
        flash(request, "Es wurde keine Datei ausgewählt.", "err")
        return zurueck("/vorbereitung")

    endung = Path(datei.filename).suffix.lower()
    puffer = bytearray()
    while stueck := await datei.read(1 << 20):
        puffer.extend(stueck)
        if len(puffer) > 25 * 1024 * 1024:
            flash(request, "Datei zu groß.", "err")
            return zurueck("/vorbereitung")

    try:
        ergebnis = await run_in_threadpool(
            ingest.aufnehmen, bytes(puffer), endung, "wissen",
            str(formular.get("themenname") or "").strip()[:200])
        if ergebnis["status"] == "neu":
            jobs.enqueue("kb_extract", {"document_id": ergebnis["document_id"]},
                         dedup_key=f"kb_extract:{ergebnis['document_id']}")
    except ingest.IngestError as exc:
        flash(request, str(exc), "err")
    else:
        flash(request, "Dieses Blatt ist bereits in Ihrer Sammlung." if ergebnis["status"] == "doppelt"
              else "Blatt hinzugefügt. Karo liest es und schlägt passende Themen vor.")
    return zurueck("/vorbereitung")


@router.get("/schulmaterial/{doc_id}", response_class=HTMLResponse)
def schulmaterial_detail(request: Request, doc_id: int):
    """Material detail view."""
    doc = db.q1("SELECT * FROM document WHERE id = ?", doc_id)
    if doc is None:
        flash(request, "Blatt nicht gefunden.", "err")
        return zurueck("/vorbereitung")
    abschnitte = [dict(r) for r in db.q(
        """SELECT k.*, t.label AS thema_label FROM kb_chunk k
             LEFT JOIN topic t ON t.id = k.topic_id
            WHERE k.document_id=? ORDER BY k.position""", doc_id)]
    return render(request, "vorbereitung/schulmaterial_detail.html",
                  doc=dict(doc), abschnitte=abschnitte)


# ─────────────────────────────────────────────────────────────────────────────
# INHALTE GENEHMIGEN (merged from themen.py + recherche.py)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/inhalte", response_class=HTMLResponse)
def inhalte_genehmigen(request: Request):
    """Inhalte genehmigen - approve themes & sources (merged view)."""
    vorschlaege = topics.liste(topics.VORSCHLAG)
    aktive = topics.liste(topics.AKTIV)
    aktive.sort(key=lambda t: (
        __import__("app.domain", fromlist=["FLAG_ORDER"]).FLAG_ORDER.index(t["flag"])
        if t["flag"] in __import__("app.domain", fromlist=["FLAG_ORDER"]).FLAG_ORDER else 9,
        t["sort"]))
    for t in aktive:
        t["verlauf"] = quizzes.verlauf(t["id"])

    return render(request, "vorbereitung/inhalte.html",
                  vorschlaege=vorschlaege, aktive=aktive,
                  einig=quizzes.uebereinstimmung())


@router.post("/inhalte/entscheiden")
async def inhalte_entscheiden(request: Request):
    """Accept/reject theme proposals."""
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
    return zurueck("/vorbereitung/inhalte")


@router.post("/inhalte/neu")
def inhalte_neu(request: Request, label: str = Form(""),
                beschreibung: str = Form("")):
    """Create new theme manually."""
    neu = topics.anlegen(label, beschreibung)
    if neu is None:
        flash(request, "Dieses Thema gibt es schon oder der Name ist leer.", "warn")
    else:
        flash(request, "Thema angelegt.")
    return zurueck("/vorbereitung/inhalte")


@router.get("/inhalte/sources", response_class=HTMLResponse)
def quellen_verwalten(request: Request):
    """Manage research sources (merged Recherche page)."""
    cfg = config.load_safe()
    return render(request, "vorbereitung/quellen.html",
                  vorschlaege=research.vorschlaege(),
                  erlaubte=sorted(set(research.erlaubte_quellen().values())),
                  kanaele=research.ERLAUBTE_KANAELE,
                  aktiv=cfg.recherche_erlaubt)


@router.post("/inhalte/sources/entscheiden")
async def quellen_entscheiden(request: Request):
    """Approve/reject research sources."""
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
    if re.match(r"^/lernzyklus/\d+$", ziel):
        return zurueck(ziel)
    return zurueck("/vorbereitung/inhalte/sources")
