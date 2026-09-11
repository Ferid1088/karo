"""Messung (Measurement) - unified Progress + Exams (merged Lernstand + Klassenarbeit)."""

import datetime as dt
import json
import logging
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from starlette.concurrency import run_in_threadpool

from .. import config, db, export, ingest
from ..domain import Flag
from ..topics import liste, AKTIV
from .shared import render, flash, zurueck

log = logging.getLogger("karo.messung")
router = APIRouter(prefix="/messung", tags=["measurement"])


# ─────────────────────────────────────────────────────────────────────────────
# FORTSCHRITT (merged from lernstand.py)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
@router.get("/fortschritt", response_class=HTMLResponse)
def fortschritt(request: Request):
    """Learning progress view."""
    cfg = config.load_safe()
    return render(request, "messung/fortschritt.html",
                  zeilen=export.lernstand_zeilen(),
                  verlauf=export.verlauf_zeilen(limit=200),
                  xlsx_ok=export.verfuegbar(),
                  drive_ok=ingest.drive_available(),
                  drive_writable=ingest.drive_writable(),
                  rule_gruen_tage=cfg.rule_gruen_tage,
                  rule_rot_konzeptfehler=cfg.rule_rot_konzeptfehler,
                  rule_min_evidenz=cfg.rule_min_evidenz)


@router.post("/export")
async def fortschritt_export(request: Request):
    """Export progress to spreadsheet."""
    pfad = await run_in_threadpool(export.nach_freigabe)
    if pfad:
        flash(request, f"Tabelle geschrieben: {__import__('pathlib').Path(pfad).name}")
    else:
        flash(request, "Export nicht verfügbar.", "warn")
    return zurueck("/messung/fortschritt")


# ─────────────────────────────────────────────────────────────────────────────
# EXAMEN (merged from klassenarbeit.py)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/examen", response_class=HTMLResponse)
def examen(request: Request):
    """Exam management - create, predict, grade."""
    zeilen = [dict(r) for r in db.q(
        "SELECT * FROM exam ORDER BY exam_date DESC LIMIT 20")]
    for e in zeilen:
        try:
            e["themen_liste"] = json.loads(e["themen"] or "[]")
        except json.JSONDecodeError:
            e["themen_liste"] = []
        e["kalibrierung"] = _kalibrierung(e["id"])
    return render(request, "messung/examen.html", zeilen=zeilen)


@router.post("/examen/neu")
def examen_neu(request: Request, exam_date: str = Form(...),
               themen: str = Form("")):
    """Create new exam."""
    try:
        dt.date.fromisoformat(exam_date)
    except ValueError:
        flash(request, "Ungültiges Datum.", "err")
        return zurueck("/messung/examen")

    liste_themen = [t.strip()[:120] for t in themen.split(",") if t.strip()][:20]
    cfg = config.load_safe()
    with db.tx() as c:
        cur = c.execute(
            "INSERT INTO exam (subject, exam_date, themen, created_at) "
            "VALUES (?,?,?,?)",
            (cfg.subject, exam_date, json.dumps(liste_themen, ensure_ascii=False),
             db.now()))
        exam_id = cur.lastrowid
        n = 0
        for t in liste(AKTIV):
            if t["flag"] == Flag.WEISS.value:
                continue
            cur2 = c.execute(
                """INSERT INTO prediction (exam_id, topic_id, prognose, frozen_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(exam_id, topic_id) DO NOTHING""",
                (exam_id, t["id"], t["flag"], db.now()))
            n += cur2.rowcount
    flash(request, f"Prognose für {n} Themen eingefroren.")
    return zurueck("/messung/examen")


@router.post("/examen/{exam_id}/ergebnis")
async def examen_ergebnis(request: Request, exam_id: int):
    """Enter exam results."""
    formular = await request.form()
    erlaubt = {f.value for f in Flag}
    gueltig = {r["topic_id"] for r in db.q(
        "SELECT topic_id FROM prediction WHERE exam_id = ?", exam_id)}
    n = 0
    with db.tx() as c:
        for schluessel in formular.keys():
            if not schluessel.startswith("ist_"):
                continue
            roh = schluessel[4:]
            wert = str(formular.get(schluessel) or "")
            if not roh.isdigit() or wert not in erlaubt:
                continue
            if int(roh) not in gueltig:
                continue
            cur = c.execute(
                "UPDATE prediction SET tatsaechlich=? WHERE exam_id=? AND topic_id=?",
                (wert, exam_id, int(roh)))
            n += cur.rowcount
    flash(request, f"{n} Ergebnis{'se' if n != 1 else ''} eingetragen.")
    return zurueck("/messung/examen")


def _kalibrierung(exam_id: int) -> dict:
    """Calculate exam calibration stats."""
    zeilen = [dict(r) for r in db.q(
        """SELECT p.topic_id, p.prognose, p.tatsaechlich, t.label, t.code
             FROM prediction p JOIN topic t ON t.id = p.topic_id
            WHERE p.exam_id=? ORDER BY t.sort""", exam_id)]
    bewertet = [z for z in zeilen if z["tatsaechlich"]]
    treffer = sum(1 for z in bewertet if z["prognose"] == z["tatsaechlich"])
    return {"zeilen": zeilen, "bewertet": len(bewertet), "treffer": treffer,
            "quote": round(treffer / len(bewertet), 2) if bewertet else None}
