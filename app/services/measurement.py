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

import datetime as dt
import json
from pathlib import Path

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool

from .. import config, db, export, ingest, jobs, faecher
from ..routers.shared import flash, render, zurueck


def render_lernstand(request: Request):
    cfg = config.load_safe()
    zeilen = export.lernstand_zeilen()
    from .learning_hub import archiv_themen, archiv_arbeiten, personal_topics
    archiv = archiv_themen()
    sicher = sum(not t["gelöscht"] for t in archiv)
    return render(request, "lernstand.html",
                  safe_count=sicher, personal_count=len(personal_topics()) + sicher,
                  zeilen=zeilen, erfolge=[t for t in zeilen if t.get('learned_at')],
                  archiv_themen=archiv, archiv_arbeiten=archiv_arbeiten(),
                  nachfrage=request.query_params.get("weg", ""),
                  tab=request.query_params.get("tab", ""),
                  full_progress=request.url.path.startswith('/messung'),
                  adult_page=request.url.path.startswith('/messung'),
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


def render_einstufung(request, exam_id: int, naechstes, offen):
    """Die Einstufungsseite: ein Thema, seine Aufgaben, der Fortschritt."""
    from . import exam_placement
    row = db.q1("SELECT * FROM exam WHERE id=? AND deleted_at IS NULL"
                " AND purged_at IS NULL", exam_id)
    if not row:
        raise HTTPException(404, "Diese Klassenarbeit gibt es nicht.")
    return render(request, "klassenarbeit_einstufung.html", e=dict(row),
                  stand=exam_placement.stand(exam_id),
                  inhalte=exam_effort_stand(exam_id),
                  thema=(naechstes or {}).get("topic"), offen=offen,
                  adult_page=not config.load().klassenarbeit_kind,
                  show_nav=False)


def exam_effort_stand(exam_id: int) -> dict:
    from . import exam_effort
    return exam_effort.inhalte_stand(exam_id)


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


def _exam_ansicht(e: dict) -> dict:
    """Eine Klassenarbeit mit allem, was eine Ansicht von ihr zeigt.

    Uebersicht und Detailseite rechnen aus derselben Quelle. Sonst zaehlt
    jede Seite ihre eigene Menge — genau der Fehler, den die Zielseiten
    hinter sich haben.
    """
    from .. import exam_plan, exam_learning
    from . import exam_calendar
    from .learning_hub import exam_topics
    e['topics'] = exam_topics(e['id'])
    e['materials'] = [m for r in db.q(
        "SELECT id FROM exam_material WHERE exam_id=? ORDER BY id DESC", e['id'])
                     if (m := exam_learning.status(r['id']))]
    e['mastered'] = sum(t['learning_status'] == 'sicher' for t in e['topics'])
    # Ein naechster Schritt je Arbeit statt einer Knopfreihe ueber alle
    # Themen — wie "Naechste Einheit" beim Ziel.
    e['next_topic'] = next((t for t in e['topics']
                            if t['learning_status'] != 'sicher'), None)
    e['days_left'] = (dt.date.fromisoformat(e['exam_date']) - dt.date.fromisoformat(db.today())).days
    e['simulation_available'] = exam_calendar.simulation_available(e['id'])
    try:
        e["themen_liste"] = json.loads(e["themen"] or "[]")
    except json.JSONDecodeError:
        e["themen_liste"] = []
    e["kalibrierung"] = _kalibrierung(e["id"])
    e["plan"] = exam_plan.holen_plan(e["id"])
    # Was die Arbeit an Zeit braucht und ob die gewaehlte Zeit dafuer reicht.
    from . import exam_effort
    e["aufwand"] = exam_effort.lage(e["id"])
    e["inhalte"] = exam_effort.inhalte_stand(e["id"])
    from . import exam_placement
    e["einstufung"] = exam_placement.stand(e["id"])
    e["schedule"] = exam_calendar.get(e["id"])
    e["simulation_early"] = exam_calendar.simulation_early(e["id"])
    e["calendar"] = exam_calendar.calendar(e["id"])
    e["today_task"] = next((d for d in e["calendar"] if d["today"]
                            and (d["is_learning_day"] or d["is_simulation"])), None)
    e["sessions"] = [dict(r) for r in db.q("""SELECT s.id, s.zustand, i.thema_text
        FROM lern_sitzung s JOIN lern_eingabe i ON i.id=s.eingabe_id
        JOIN exam_topic x ON x.topic_id=i.topic_id WHERE x.exam_id=?
        ORDER BY s.id DESC LIMIT 20""", e["id"])]
    e["woche"] = exam_calendar.woche(e["id"])
    e["calendar_leading_blanks"] = (
        (dt.date.fromisoformat(e["calendar"][0]["date"]).isoweekday() - 1)
        if e["calendar"] else 0
    )
    return e


def render_klassenarbeit(request: Request, monat: str = ""):
    from .. import exam_plan
    from . import exam_calendar
    # Geloeschte Arbeiten stehen im Archiv unter "Erfolge".
    zeilen = [_exam_ansicht(dict(r)) for r in db.q(
        f"SELECT * FROM exam WHERE deleted_at IS NULL AND purged_at IS NULL AND subject IN {faecher.SQL_FAECHER} "
        "ORDER BY exam_date DESC LIMIT 20")]
    # Parent and child use the same isolated process. The setting controls
    # access, not a second legacy workflow with shared personal topics.
    return render(request, "klassenarbeit_kind.html", zeilen=zeilen,
                  adult_page=not config.load().klassenarbeit_kind,
                  scan=exam_plan.offene_scan(), counts=jobs.counts(),
                  kalender=exam_calendar.monat(monat),
                  monat=monat, nachfrage=request.query_params.get("weg", ""),
                  weekday_labels=exam_calendar.WEEKDAY_LABELS)


def render_klassenarbeit_kalender(request: Request, monat: str = ""):
    """Nur der Kalender über alle Arbeiten — eigener Reiter, eigene Seite."""
    from . import exam_calendar
    return render(request, "klassenarbeit_kalender.html",
                  adult_page=not config.load().klassenarbeit_kind,
                  kalender=exam_calendar.monat(monat), monat=monat,
                  weekday_labels=exam_calendar.WEEKDAY_LABELS)


def render_klassenarbeit_neu(request: Request, draft: dict | None = None):
    """Beide Wege zu einer neuen Arbeit: selbst eintragen oder Blatt hochladen.

    Kommt der Aufruf vom Themenblatt-Upload (`?material={paket_id}`),
    stehen die dort bestätigten Prüfungsinhalte schon im Feld — als
    gewöhnlicher Text, Termin, Fach und das Anlegen entscheidet weiterhin
    das Formular. Mitgereiste Werte (`?termin=&fach=&themen=`) bleiben
    erhalten: das Themenblatt ergänzt das Formular, es überschreibt nicht,
    was der Mensch eingetragen hat.
    """
    from .. import exam_plan, material_paket
    import datetime as dt
    entwurf = dict(draft or {})
    q = request.query_params

    termin = str(q.get("termin") or "").strip()[:10]
    try:
        dt.date.fromisoformat(termin)
    except ValueError:
        termin = ""
    if termin:
        entwurf["exam_date"] = termin
    fach = faecher.schluessel(q.get("fach"))
    if fach:
        entwurf["fach"] = fach
    manuell = [z.strip() for z in str(q.get("themen") or "")
               .replace(",", "\n").splitlines() if z.strip()]

    material_id = str(q.get("material") or "")
    if material_id.isdigit():
        auswahl = material_paket.gewaehlte_pruefinhalte(int(material_id))
        if auswahl:
            # Manuelle Zeilen bleiben, bestätigte Inhalte kommen dazu —
            # keine Dubletten.
            vorhanden = {t.casefold() for t in manuell}
            manuell += [t for t in auswahl["themen"]
                        if t.casefold() not in vorhanden]
            entwurf.setdefault("fach", auswahl["fach"])
            if not entwurf.get("exam_date") and auswahl.get("termin"):
                entwurf["exam_date"] = auswahl["termin"]
    if manuell:
        entwurf["themen"] = "\n".join(dict.fromkeys(manuell))
    return render(request, "klassenarbeit_neu.html",
                  adult_page=not config.load().klassenarbeit_kind,
                  scan=exam_plan.offene_scan(), draft=entwurf)


def render_klassenarbeit_detail(request: Request, exam_id: int):
    """Eine einzelne Arbeit: Themen, Kalender, Generalprobe.

    Das Schwere steht hier, nicht auf der Uebersicht — wie beim Ziel, wo der
    Monatskalender auch erst in den Details auftaucht.
    """
    from fastapi import HTTPException
    from . import exam_calendar
    row = db.q1(f"SELECT * FROM exam WHERE id=? AND deleted_at IS NULL AND purged_at IS NULL AND subject IN {faecher.SQL_FAECHER}", exam_id)
    if row is None:
        raise HTTPException(404, "Diese Klassenarbeit gibt es nicht.")
    return render(request, "klassenarbeit_detail.html", e=_exam_ansicht(dict(row)),
                  adult_page=not config.load().klassenarbeit_kind,
                  weekday_labels=exam_calendar.WEEKDAY_LABELS)
