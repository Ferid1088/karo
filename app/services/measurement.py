"""Messung: Lernfortschritt und Klassenarbeiten.

`/lernstand`+`/export` (eltern.py) und `/klassenarbeit` (admin.py) hatten
ihre Logik direkt in den Router-Funktionen; `messung.py` rief diese
Funktionen dann direkt auf (Router ruft Router). Jetzt lebt die Logik
hier, und alle drei Router rufen dieselben Funktionen auf
(KaroRefactoring_Plan.md Abschnitt 10; change.txt Aufgabe 2/6).

Die restliche Klassenarbeit-Verwaltung (Themenblatt-Scan, KI-Lernplan,
Lernmaterial-Pipeline: admin.py) bleibt bewusst nur unter /klassenarbeit —
/messung/examen zeigt dieselbe Uebersicht, hat aber keine eigenen Formulare
dafuer, es gibt also nichts, was hier dupliziert werden koennte.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import Request
from starlette.concurrency import run_in_threadpool

from .. import config, db, export, ingest, jobs
from ..routers.shared import flash, render, zurueck


def render_lernstand(request: Request):
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


async def handle_export(request: Request, zurueck_ziel: str = "/lernstand"):
    pfad = await run_in_threadpool(export.nach_freigabe)
    if pfad:
        flash(request, f"Lernstand als Tabelle geschrieben: {Path(pfad).name}")
    else:
        flash(request, "Der Tabellenexport ist nicht verfügbar.", "warn")
    return zurueck(zurueck_ziel)


def _kalibrierung(exam_id: int) -> dict:
    zeilen = [dict(r) for r in db.q(
        """SELECT p.topic_id, p.prognose, p.tatsaechlich, t.label, t.code
             FROM prediction p JOIN topic t ON t.id = p.topic_id
            WHERE p.exam_id=? ORDER BY t.sort""", exam_id)]
    bewertet = [z for z in zeilen if z["tatsaechlich"]]
    treffer = sum(1 for z in bewertet if z["prognose"] == z["tatsaechlich"])
    niveau = {"gruen": 100, "gelb": 70, "rot": 30}
    vorbereitet = (sum(niveau.get(z["tatsaechlich"], 0) for z in bewertet)
                   / len(bewertet) if bewertet else None)
    return {"zeilen": zeilen, "bewertet": len(bewertet), "treffer": treffer,
            "quote": round(treffer / len(bewertet), 2) if bewertet else None,
            "vorbereitet": round(vorbereitet) if vorbereitet is not None else None}


def render_klassenarbeit(request: Request):
    from .. import exam_plan
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
                  scan=exam_plan.offene_scan(), counts=jobs.counts())
