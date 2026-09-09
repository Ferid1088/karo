"""Die Verarbeitungsschritte.

Reihenfolge und Bedingungen bestimmt der Code hier. Das Modell wird an vier
Stellen als Uebersetzer aufgerufen — Bild nach Struktur, Struktur nach Diagnose,
Kompetenz nach Uebungsblatt, Profil nach Lernplan — und trifft an keiner Stelle
eine Entscheidung darueber, was gespeichert wird.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import logging

from pathlib import Path

from . import config, db, ingest, jobs, pii, prompts
from .claude_client import ClaudeClient
from .domain import (
    ERROR_LABELS,
    Observation,
    Rule,
    Status,
    compute_status,
)

log = logging.getLogger("karo.pipeline")


def client() -> ClaudeClient:
    return ClaudeClient.from_config(config.load())


# --------------------------------------------------------------------------
# Schritt 1: Scan lesen
# --------------------------------------------------------------------------

@jobs.handler("extract")
def job_extract(payload: dict) -> None:
    doc_id = int(payload["document_id"])
    doc = db.q1("SELECT * FROM document WHERE id = ?", doc_id)
    if doc is None:
        return
    if doc["state"] == "gelesen":
        # Beim letzten Mal ist zwischen Lesen und Einreihen etwas abgebrochen.
        # Aufgaben sind da, die Diagnose fehlt — also nachholen statt aufgeben.
        jobs.enqueue("diagnose", {"document_id": doc_id}, dedup_key=f"diagnose:{doc_id}")
        return
    if doc["state"] != "neu":
        return

    cfg = config.load()
    result = client().complete(
        purpose="extract",
        prompt=prompts.extract_prompt(cfg.learner_grade, cfg.subject,
                                      pii.scrub(doc["topic"], cfg.learner_name)),
        schema=prompts.EXTRACT_SCHEMA,
        image_path=Path(doc["stored_path"]),
        system=prompts.SYSTEM,
    )
    data = result.data
    raw_items = data.get("aufgaben") or []

    with db.tx() as c:
        c.execute("DELETE FROM task_item WHERE document_id = ?", (doc_id,))
        for index, raw in enumerate(raw_items, start=1):
            model_pos = raw.get("position")
            c.execute(
                """INSERT INTO task_item
                       (document_id, position, model_position, prompt_text,
                        student_answer)
                   VALUES (?, ?, ?, ?, ?)""",
                (doc_id, index,
                 int(model_pos) if isinstance(model_pos, int) else None,
                 (raw.get("aufgabe") or "").strip()[:2000] or "(ohne Text)",
                 ((raw.get("antwort") or "")[:2000] or None)),
            )
        # Ein leeres Blatt bekommt einen Endzustand statt in 'gelesen' haengen
        # zu bleiben, wo es weder eine Schaltflaeche noch eine Fehlermeldung gibt.
        neuer_zustand = "gelesen" if raw_items else "leer"
        note = f"Lesbarkeit: {data.get('lesbarkeit', 'unbekannt')}"
        if not raw_items:
            note += " — es wurde keine einzige Aufgabe erkannt"
        c.execute(
            """UPDATE document
                  SET state=?, doc_type=COALESCE(doc_type, ?),
                      topic=COALESCE(topic, ?), note=?
                WHERE id=?""",
            (neuer_zustand, data.get("dokumenttyp") or None,
             (data.get("thema") or "")[:200] or None, note, doc_id),
        )
        # Im selben Schreibvorgang einreihen: sonst kann ein Absturz genau
        # dazwischen das Dokument fuer immer in 'gelesen' stehen lassen, waehrend
        # der Job als erledigt gilt.
        if raw_items:
            schluessel = f"diagnose:{doc_id}"
            # Denselben Freigabeschritt wie jobs.enqueue: ein abgeschlossener
            # Job darf den Schluessel nicht blockieren.
            c.execute(
                """UPDATE job SET dedup_key = NULL
                    WHERE dedup_key = ? AND state NOT IN ('wartend', 'laeuft')""",
                (schluessel,),
            )
            c.execute(
                """INSERT OR IGNORE INTO job (type, payload, state, dedup_key, created_at)
                   VALUES ('diagnose', ?, 'wartend', ?, ?)""",
                (json.dumps({"document_id": doc_id}), schluessel, db.now()),
            )


# --------------------------------------------------------------------------
# Schritt 2: Diagnose vorschlagen
# --------------------------------------------------------------------------

@jobs.handler("diagnose")
def job_diagnose(payload: dict) -> None:
    doc_id = int(payload["document_id"])
    doc = db.q1("SELECT * FROM document WHERE id = ?", doc_id)
    if doc is None or doc["state"] != "gelesen":
        return

    items = [dict(r) for r in db.q(
        "SELECT * FROM task_item WHERE document_id=? ORDER BY position", doc_id)]
    if not items:
        with db.tx() as c:
            c.execute("UPDATE document SET state='diagnostiziert' WHERE id=?", (doc_id,))
        return

    cfg = config.load()
    comps = [dict(r) for r in db.q(
        "SELECT code, label FROM competency WHERE subject=? ORDER BY sort", cfg.subject)]

    # Was aus dem Scan gelesen wurde, kann einen Namen enthalten. Vor dem
    # zweiten Aufruf wird es deshalb gefiltert.
    scrubbed = [
        {**i,
         "prompt_text": pii.scrub(i["prompt_text"], cfg.learner_name),
         "student_answer": pii.scrub(i["student_answer"], cfg.learner_name)}
        for i in items
    ]

    result = client().complete(
        purpose="diagnose",
        prompt=prompts.diagnose_prompt(cfg.learner_grade, cfg.subject, comps, scrubbed),
        schema=prompts.DIAGNOSE_SCHEMA,
        system=prompts.SYSTEM,
    )

    by_code = {r["code"]: r["id"] for r in db.q(
        "SELECT id, code FROM competency WHERE subject = ?", cfg.subject)}
    by_pos = {i["position"]: i["id"] for i in items}

    with db.tx() as c:
        gesehen: set[int] = set()
        for r in result.data.get("ergebnisse") or []:
            try:
                task_id = by_pos.get(int(r.get("position")))
            except (TypeError, ValueError):
                continue
            # Liefert das Modell dieselbe Position zweimal, entstuende sonst eine
            # Mischung aus zwei Urteilen. Der erste Eintrag gilt.
            if task_id is None or task_id in gesehen:
                continue
            gesehen.add(task_id)
            error = r.get("fehlertyp")
            c.execute(
                """UPDATE task_item
                      SET proposed_correct=?, proposed_error=?, proposed_reason=?,
                          proposed_conf=?, diagnose_call_id=?,
                          competency_id=COALESCE(?, competency_id)
                    WHERE id=?""",
                (
                    int(bool(r.get("richtig"))),
                    error if error in ERROR_LABELS else None,
                    (r.get("begruendung") or "")[:1000],
                    _as_float(r.get("konfidenz")),
                    result.call_id,
                    by_code.get(r.get("kompetenz_code") or ""),
                    task_id,
                ),
            )
        # Mit Zustandsbedingung: waehrend des Modellaufrufs kann das Dokument
        # freigegeben worden sein, und dann darf es nicht zurueckfallen.
        c.execute("UPDATE document SET state='diagnostiziert' "
                  "WHERE id=? AND state='gelesen'", (doc_id,))


def _as_float(value) -> float | None:
    """Unbrauchbare Angaben gelten als niedrige Konfidenz.

    None waere hier falsch: die Oberflaeche liest None als 'sicher gelesen' und
    wuerde die Warnmarkierung ausgerechnet dort weglassen, wo das Modell etwas
    Unerwartetes geantwortet hat."""
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.3


# --------------------------------------------------------------------------
# Schritt 3: Freigabe -> Beobachtungen
# --------------------------------------------------------------------------

class ApprovalError(Exception):
    """Die Freigabe war nicht vollstaendig oder nicht plausibel."""


def approve_document(doc_id: int, decisions: list[dict]) -> dict:
    """Schreibt die freigegebenen Beobachtungen. Append-only.

    Regeln, die hier durchgesetzt werden:
      * Es werden nur Aufgaben akzeptiert, die zu DIESEM Dokument gehoeren.
      * Eine Aufgabe ohne Kompetenz wird uebersprungen, nicht geraten.
      * Das Dokument gilt erst als freigegeben, wenn jede Aufgabe entweder
        bewertet oder bewusst uebersprungen wurde. Ein leeres Formular
        schliesst kein Dokument ab.
    """
    doc = db.q1("SELECT * FROM document WHERE id = ?", doc_id)
    if doc is None:
        raise ApprovalError("Dokument nicht gefunden.")
    if doc["state"] == "freigegeben":
        return {"written": 0, "skipped": 0, "already": True}

    valid_ids = {r["id"] for r in db.q(
        "SELECT id FROM task_item WHERE document_id = ?", doc_id)}
    valid_comps = {r["id"] for r in db.q("SELECT id FROM competency")}
    if not valid_ids:
        raise ApprovalError("Auf diesem Blatt wurden keine Aufgaben erkannt.")

    known = {int(d["task_id"]) for d in decisions if int(d["task_id"]) in valid_ids}
    missing = valid_ids - known
    if missing:
        raise ApprovalError(
            f"{len(missing)} Aufgabe(n) sind noch nicht bewertet. Bitte für jede "
            "Aufgabe „richtig“, „falsch“ oder „überspringen“ wählen."
        )

    observed_on = doc["captured_on"] or db.today()
    written = skipped = 0

    with db.tx() as c:
        for d in decisions:
            task_id = int(d["task_id"])
            if task_id not in valid_ids:
                continue                        # gehoert zu einem anderen Dokument
            if (d.get("skip") or not d.get("competency_id")
                    or int(d["competency_id"]) not in valid_comps):
                skipped += 1
                continue
            if c.execute("SELECT 1 FROM observation WHERE task_item_id = ?",
                         (task_id,)).fetchone():
                continue                        # schon bewertet
            c.execute(
                """INSERT INTO observation
                       (task_item_id, competency_id, observed_on, is_correct,
                        error_type, rationale, confidence, source, model_agreed,
                        llm_call_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task_id, int(d["competency_id"]), observed_on,
                    int(bool(d["is_correct"])),
                    d.get("error_type") or None,
                    (d.get("rationale") or "")[:1000],
                    d.get("confidence"),
                    "lernbegleitung" if d.get("changed") else "llm",
                    0 if d.get("changed") else 1,
                    d.get("llm_call_id"),
                    db.now(),
                ),
            )
            c.execute("UPDATE task_item SET competency_id=? WHERE id=?",
                      (int(d["competency_id"]), task_id))
            written += 1
        c.execute("UPDATE document SET state='freigegeben' WHERE id=?", (doc_id,))

    for comp_id in {int(d["competency_id"]) for d in decisions
                    if d.get("competency_id") and not d.get("skip")
                    and int(d["competency_id"]) in valid_comps}:
        recompute_status(comp_id)

    return {"written": written, "skipped": skipped, "already": False}


def discard_document(doc_id: int) -> bool:
    """Verwirft ein Dokument, das nicht in das Lernprofil einfliessen soll.

    Der haeufigste Fall: dasselbe Blatt wurde zweimal fotografiert, weil das
    erste Bild unscharf war. Ohne diesen Weg bliebe die Dublette fuer immer im
    Eingang stehen — und wuerde sie freigegeben, zaehlte jede Aufgabe doppelt.
    """
    doc = db.q1("SELECT state FROM document WHERE id = ?", doc_id)
    if doc is None or doc["state"] == "freigegeben":
        return False
    with db.tx() as c:
        c.execute("UPDATE document SET state='verworfen' WHERE id=? AND state!='freigegeben'",
                  (doc_id,))
    return True


# --------------------------------------------------------------------------
# Statusberechnung
# --------------------------------------------------------------------------

def recompute_status(competency_id: int) -> None:
    """Berechnet den Status neu.

    Beobachtungen sind unveraenderlich, eine Korrektur ist eine neue
    Beobachtung. Deshalb zaehlt je Aufgabe nur die jeweils juengste.
    """
    rows = db.q(
        """SELECT o.id, o.observed_on, o.is_correct, o.error_type, o.created_at
             FROM observation o
             JOIN (SELECT task_item_id, MAX(id) AS newest
                     FROM observation WHERE competency_id = ?
                    GROUP BY task_item_id) j
               ON j.newest = o.id
            ORDER BY o.observed_on, o.created_at, o.id""",
        competency_id,
    )
    obs = [Observation(r["observed_on"], bool(r["is_correct"]),
                       r["error_type"], r["created_at"] or "", r["id"]) for r in rows]
    res = compute_status(obs, Rule.from_config(config.load_safe()))
    with db.tx() as c:
        c.execute(
            """INSERT INTO competency_status
                   (competency_id, status, evidence_count, correct_count,
                    dominant_error, last_seen_on, computed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(competency_id) DO UPDATE SET
                   status=excluded.status,
                   evidence_count=excluded.evidence_count,
                   correct_count=excluded.correct_count,
                   dominant_error=excluded.dominant_error,
                   last_seen_on=excluded.last_seen_on,
                   computed_at=excluded.computed_at""",
            (competency_id, res.status, res.evidence_count, res.correct_count,
             res.dominant_error, res.last_seen_on, db.now()),
        )


def recompute_all() -> int:
    rows = db.q("SELECT id FROM competency")
    for r in rows:
        recompute_status(r["id"])
    return len(rows)


def profile(subject: str) -> list[dict]:
    return [dict(r) for r in db.q(
        """SELECT c.id, c.code, c.label, c.topic,
                  COALESCE(s.status, 'unbewertet') AS status,
                  COALESCE(s.evidence_count, 0)    AS evidence_count,
                  COALESCE(s.correct_count, 0)     AS correct_count,
                  s.dominant_error, s.last_seen_on
             FROM competency c
             LEFT JOIN competency_status s ON s.competency_id = c.id
            WHERE c.subject = ? ORDER BY c.sort""",
        subject)]


def recent_observations(competency_id: int, limit: int = 12) -> list[dict]:
    rows = db.q(
        """SELECT observed_on, is_correct, error_type, source
             FROM observation WHERE competency_id = ?
            ORDER BY observed_on DESC, created_at DESC, id DESC LIMIT ?""",
        competency_id, limit)
    return [dict(r) for r in reversed(rows)]


# --------------------------------------------------------------------------
# Schritt 4: Uebungsblatt
# --------------------------------------------------------------------------

@jobs.handler("worksheet")
def job_worksheet(payload: dict) -> None:
    comp_id = int(payload["competency_id"])
    comp = db.q1("SELECT * FROM competency WHERE id = ?", comp_id)
    if comp is None:
        return
    st = db.q1("SELECT * FROM competency_status WHERE competency_id = ?", comp_id)
    cfg = config.load()

    result = client().complete(
        purpose="worksheet",
        prompt=prompts.worksheet_prompt(
            cfg.learner_grade, cfg.subject, comp["label"],
            st["dominant_error"] if st else None),
        schema=prompts.WORKSHEET_SCHEMA,
        system=prompts.SYSTEM,
    )
    data = result.data

    with db.tx() as c:
        cur = c.execute(
            """INSERT INTO worksheet (kind, competency_id, title, tasks, created_at)
               VALUES ('uebung', ?, ?, ?, ?)""",
            (comp_id, (data.get("titel") or comp["label"])[:200],
             json.dumps(data, ensure_ascii=False), db.now()))
        ws_id = cur.lastrowid

    path = ingest.write_worksheet(
        f"{db.today()}_{comp['code']}_Uebungsblatt.html",
        worksheet_html(data, comp["label"]))
    if path:
        with db.tx() as c:
            c.execute("UPDATE worksheet SET drive_path=? WHERE id=?", (path, ws_id))


def worksheet_html(data: dict, label: str) -> str:
    """Druckbares Schuelerblatt. Ohne Loesungen — die stehen nur in der App."""
    rows = "".join(
        f'<li><p>{_esc(t.get("text", ""))}</p><div class="feld"></div></li>'
        for t in (data.get("aufgaben") or []))
    titel = _esc(data.get("titel") or label)
    return f"""<!doctype html><html lang="de"><meta charset="utf-8">
<title>{titel}</title>
<style>
 body{{font-family:Georgia,serif;max-width:19cm;margin:2cm auto;line-height:1.6;color:#111}}
 h1{{font-size:19pt;margin:0 0 .2cm}}
 .hinweis{{background:#f2f4f8;padding:.5cm;border-left:3px solid #1c3fbf;margin:.6cm 0}}
 ol{{padding-left:1.1cm}} li{{margin-bottom:1.1cm}} li p{{margin:0 0 .35cm}}
 .feld{{border-bottom:1px solid #999;height:1.5cm}}
 .kopf{{display:flex;justify-content:space-between;font-size:10pt;color:#555;
        border-bottom:1px solid #ccc;padding-bottom:.2cm;margin-bottom:.6cm}}
 @media print{{body{{margin:1.5cm}}}}
</style>
<div class="kopf"><span>Übungsblatt</span><span>Datum: __________</span></div>
<h1>{titel}</h1>
<div class="hinweis">{_esc(data.get('hinweis', ''))}</div>
<ol>{rows}</ol>
</html>"""


def _esc(s) -> str:
    return html.escape(str(s), quote=True)


# --------------------------------------------------------------------------
# Schritt 5: Lernplan
# --------------------------------------------------------------------------

@jobs.handler("plan")
def job_plan(payload: dict) -> None:
    exam_id = int(payload["exam_id"])
    exam = db.q1("SELECT * FROM exam WHERE id = ?", exam_id)
    if exam is None:
        return
    cfg = config.load()
    try:
        days = max(1, (dt.date.fromisoformat(exam["exam_date"]) - dt.date.today()).days)
    except ValueError:
        days = 5

    topics = pii.scrub_all(json.loads(exam["topics"] or "[]"), cfg.learner_name)
    result = client().complete(
        purpose="plan",
        prompt=prompts.plan_prompt(cfg.learner_grade, cfg.subject, days,
                                   topics, profile(cfg.subject)),
        schema=prompts.PLAN_SCHEMA,
        system=prompts.SYSTEM,
    )
    with db.tx() as c:
        c.execute(
            """INSERT INTO worksheet (kind, exam_id, title, tasks, created_at)
               VALUES ('plan', ?, ?, ?, ?)""",
            (exam_id, f"Lernplan zur Klassenarbeit am {exam['exam_date']}",
             json.dumps({"plan": result.data}, ensure_ascii=False), db.now()))


def freeze_prediction(exam_id: int) -> int:
    """Friert die aktuelle Einschaetzung ein. Das ist die Messung des Systems."""
    n = 0
    with db.tx() as c:
        for r in profile(config.load_safe().subject):
            if r["status"] == Status.UNBEWERTET.value:
                continue
            cur = c.execute(
                """INSERT INTO prediction (exam_id, competency_id, predicted, frozen_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(exam_id, competency_id) DO NOTHING""",
                (exam_id, r["id"], r["status"], db.now()))
            n += cur.rowcount
    return n


def calibration(exam_id: int) -> dict:
    """Vergleicht die eingefrorene Prognose mit dem tatsaechlichen Ergebnis."""
    rows = [dict(r) for r in db.q(
        """SELECT p.competency_id, p.predicted, p.actual, c.label, c.code
             FROM prediction p JOIN competency c ON c.id = p.competency_id
            WHERE p.exam_id = ? ORDER BY c.sort""", exam_id)]
    scored = [r for r in rows if r["actual"]]
    hits = sum(1 for r in scored if r["predicted"] == r["actual"])
    return {"rows": rows, "scored": len(scored), "hits": hits,
            "quote": round(hits / len(scored), 2) if scored else None}


def record_exam_result(exam_id: int, results: dict[int, str]) -> int:
    valid = {r["competency_id"] for r in db.q(
        "SELECT competency_id FROM prediction WHERE exam_id = ?", exam_id)}
    allowed = {s.value for s in Status}
    n = 0
    with db.tx() as c:
        for comp_id, value in results.items():
            if comp_id not in valid or value not in allowed:
                continue
            cur = c.execute(
                "UPDATE prediction SET actual=? WHERE exam_id=? AND competency_id=?",
                (value, exam_id, comp_id))
            n += cur.rowcount
    return n


# --------------------------------------------------------------------------
# Kennzahl: wie oft musste die Lernbegleitung korrigieren?
# --------------------------------------------------------------------------

def agreement_rate(last_n: int = 100) -> dict:
    rows = db.q(
        """SELECT model_agreed FROM observation
            WHERE model_agreed IS NOT NULL ORDER BY id DESC LIMIT ?""", last_n)
    total = len(rows)
    agreed = sum(1 for r in rows if r["model_agreed"])
    return {"total": total, "agreed": agreed,
            "quote": round(agreed / total, 3) if total else None}
