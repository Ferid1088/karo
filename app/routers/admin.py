"""Admin-Routen: Klassenarbeit, Protokoll."""

import datetime as dt
import json
import logging
from pathlib import Path
from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from .. import db, config, exam_plan, ingest
from ..domain import Flag
from ..topics import liste, AKTIV
from .shared import render, flash, zurueck

log = logging.getLogger("karo.admin")
router = APIRouter()


@router.get("/klassenarbeit", response_class=HTMLResponse)
def klassenarbeit(request: Request):
    zeilen = [dict(r) for r in db.q(
        "SELECT * FROM exam ORDER BY exam_date DESC LIMIT 20")]
    for e in zeilen:
        try:
            e["themen_liste"] = json.loads(e["themen"] or "[]")
        except json.JSONDecodeError:
            e["themen_liste"] = []
        e["kalibrierung"] = _kalibrierung(e["id"])
        e["plan"] = exam_plan.holen_plan(e["id"])
    return render(request, "klassenarbeit.html", zeilen=zeilen,
                  scan=exam_plan.offene_scan())


def _kalibrierung(exam_id: int) -> dict:
    zeilen = [dict(r) for r in db.q(
        """SELECT p.topic_id, p.prognose, p.tatsaechlich, t.label, t.code
             FROM prediction p JOIN topic t ON t.id = p.topic_id
            WHERE p.exam_id=? ORDER BY t.sort""", exam_id)]
    bewertet = [z for z in zeilen if z["tatsaechlich"]]
    treffer = sum(1 for z in bewertet if z["prognose"] == z["tatsaechlich"])
    return {"zeilen": zeilen, "bewertet": len(bewertet), "treffer": treffer,
            "quote": round(treffer / len(bewertet), 2) if bewertet else None}


@router.post("/klassenarbeit")
def klassenarbeit_neu(request: Request, exam_date: str = Form(...),
                      themen: str = Form(""), scan_id: str = Form("")):
    try:
        dt.date.fromisoformat(exam_date)
    except ValueError:
        flash(request, "Ungültiges Datum.", "err")
        return zurueck("/klassenarbeit")
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
    if scan_id.isdigit():
        exam_plan.scan_uebernehmen(int(scan_id))
    exam_plan.plan_anfordern(exam_id)
    flash(request, f"Prognose für {n} Themen eingefroren. Karo erstellt jetzt "
                   "einen Lernplan.")
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
        if len(puffer) > 25 * 1024 * 1024:
            flash(request, "Die Datei ist zu groß.", "err")
            return zurueck("/klassenarbeit")

    try:
        exam_plan.foto_hochladen(bytes(puffer), endung)
    except ingest.IngestError as exc:
        flash(request, str(exc), "err")
        return zurueck("/klassenarbeit")

    flash(request, "Themenblatt aufgenommen. Karo liest es jetzt ein.")
    return zurueck("/klassenarbeit")


@router.get("/klassenarbeit/themenblatt/status")
def klassenarbeit_themenblatt_status(scan_id: int):
    return {"signatur": exam_plan.scan_status(scan_id)}


@router.post("/klassenarbeit/{exam_id}/plan/neu")
def klassenarbeit_plan_neu(request: Request, exam_id: int):
    if db.q1("SELECT id FROM exam WHERE id = ?", exam_id) is None:
        flash(request, "Klassenarbeit nicht gefunden.", "err")
        return zurueck("/klassenarbeit")
    exam_plan.plan_anfordern(exam_id)
    flash(request, "Lernplan wird neu erstellt.")
    return zurueck("/klassenarbeit")


@router.get("/klassenarbeit/{exam_id}/plan/status")
def klassenarbeit_plan_status(exam_id: int):
    plan = exam_plan.holen_plan(exam_id)
    return {"signatur": plan["state"] if plan else "weg"}


@router.post("/klassenarbeit/{exam_id}/ergebnis")
async def klassenarbeit_ergebnis(request: Request, exam_id: int):
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
