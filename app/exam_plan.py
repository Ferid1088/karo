"""Themenblatt aufnehmen und Lernplan vor einer Klassenarbeit.

  1. Ein Ankündigungsblatt wird aufgenommen und liegt bereit. Gelesen wird
     es nicht: dafür müsste das Foto an ein Modell gehen, und ein Foto vom
     Küchentisch trägt mehr als die Ankündigung — den Namen des Kindes, die
     Klasse, was sonst noch danebenlag. Themen und Datum tippt ein Mensch
     ein. Bestätigen musste er sie ohnehin immer.
  2. Sobald die Klassenarbeit angelegt ist, baut Karo daraus einen
     Tag-für-Tag-Lernplan, auf Basis der angekündigten Themen und des
     aktuellen Standes je Thema (siehe `prompts.plan_prompt`) — das ist ein
     Modellaufruf, aber nur mit Text.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging

from . import config, db, ingest, jobs, pii, prompts, topics, faecher
from .llm import ClaudeClient, ClaudeError

log = logging.getLogger("karo.exam_plan")

ROLLE = "klassenarbeit_themenblatt"


def client() -> ClaudeClient:
    return ClaudeClient.from_config(config.load())


# --------------------------------------------------------------------------
# Themenblatt hochladen und lesen
# --------------------------------------------------------------------------

def foto_hochladen(daten: bytes, endung: str) -> int:
    """Nimmt das Foto des Ankündigungsblatts auf und stößt das Lesen an."""
    aufnahme = ingest.aufnehmen(daten, endung, rolle=ROLLE)
    with db.tx() as c:
        cur = c.execute(
            """INSERT INTO exam_scan (document_id, state, created_at)
               VALUES (?, 'offen', ?)""",
            (aufnahme["document_id"], db.now()))
        scan_id = cur.lastrowid
    jobs.enqueue("exam_scan_read", {"scan_id": scan_id},
                 dedup_key=f"exam_scan_read:{scan_id}")
    return scan_id


@jobs.handler("exam_scan_read")
def job_exam_scan_read(payload: dict) -> None:
    """Nimmt das Ankuendigungsblatt auf — ohne es zu lesen.

    Hier ging das Foto an ein Modell, das Themen und Datum ablas. Ein Foto
    vom Küchentisch traegt mehr als die Ankuendigung: den Namen des Kindes,
    die Klasse, was sonst noch danebenlag. Und es liess sich nicht saeubern.

    Bis das Lesen auf dem Geraet laeuft (Schritt 2), tippt ein Mensch die
    Themen und das Datum ein. Das war ohnehin der Weg, auf dem am Ende
    entschieden wurde: der Vorschlag musste immer bestaetigt werden.
    """
    scan_id = int(payload["scan_id"])
    with db.tx() as c:
        c.execute("""UPDATE exam_scan SET state='manuell'
                      WHERE id=? AND state='offen'""", (scan_id,))


def offene_scan() -> dict | None:
    """Der zuletzt hochgeladene Scan, der noch nicht übernommen wurde."""
    row = db.q1(
        """SELECT * FROM exam_scan WHERE state IN ('offen', 'manuell', 'gelesen', 'fehler')
            AND id NOT IN (SELECT scan_id FROM learning_upload)
            ORDER BY id DESC LIMIT 1""")
    if row is None:
        return None
    d = dict(row)
    try:
        d["themen_liste"] = json.loads(d["themen"] or "[]")
    except json.JSONDecodeError:
        d["themen_liste"] = []
    return d


def scan_status(scan_id: int) -> str:
    row = db.q1("SELECT state FROM exam_scan WHERE id = ?", scan_id)
    return row["state"] if row else "weg"


def scan_uebernehmen(scan_id: int) -> None:
    with db.tx() as c:
        c.execute("UPDATE exam_scan SET state='uebernommen' WHERE id=?", (scan_id,))


# --------------------------------------------------------------------------
# Lernplan
# --------------------------------------------------------------------------

def _profil(themen: list[str]) -> list[dict]:
    """Aktueller Stand je angekündigtem Thema, so wie `prompts.plan_prompt`
    ihn erwartet.

    Nur die zu den angekündigten Themen passenden Einträge — sonst würde der
    Lernplan sich mit ALLEN farbig geflaggten Themen im Fach befassen, auch
    mit längst vergangenen, die auf dieser Ankündigung gar nicht stehen (die
    eigentliche Beschränkung steht zusätzlich im Prompt selbst, siehe
    `prompts.plan_prompt` — das hier ist die zweite Absicherung, die nicht
    von der Befolgung einer Anweisung abhängt).
    """
    aktiv = [
        {"code": t["code"], "label": t["label"], "flag": t["flag"],
         "richtig": t["richtig"], "antworten": t["antworten"],
         "haupt_fehler": t["haupt_fehler"]}
        for t in topics.liste(topics.AKTIV) if t["flag"] != "weiss"
    ]
    return topics.passende(themen, aktiv)


def plan_anfordern(exam_id: int) -> None:
    """Reiht die Erstellung eines Lernplans für diese Klassenarbeit ein."""
    with db.tx() as c:
        c.execute(
            """INSERT INTO exam_plan (exam_id, state, created_at)
               VALUES (?, 'offen', ?)
               ON CONFLICT(exam_id) DO UPDATE SET
                   state='offen', einschaetzung=NULL, tagesplan=NULL,
                   fehler=NULL, created_at=excluded.created_at""",
            (exam_id, db.now()))
    jobs.enqueue("exam_plan_build", {"exam_id": exam_id},
                 dedup_key=f"exam_plan_build:{exam_id}")


@jobs.handler("exam_plan_build")
def job_exam_plan_build(payload: dict) -> None:
    exam_id = int(payload["exam_id"])
    exam = db.q1("SELECT * FROM exam WHERE id = ?", exam_id)
    plan = db.q1("SELECT * FROM exam_plan WHERE exam_id = ?", exam_id)
    if exam is None or plan is None or plan["state"] != "offen":
        return

    cfg = config.load()
    try:
        tage = max(1, (dt.date.fromisoformat(exam["exam_date"])
                       - dt.date.today()).days)
    except ValueError:
        tage = 5

    try:
        themen = json.loads(exam["themen"] or "[]")
    except json.JSONDecodeError:
        themen = []
    themen = pii.scrub_all(themen, cfg.learner_name)

    try:
        ergebnis = client().complete(
            purpose="exam_plan_build",
            prompt=prompts.plan_prompt(cfg.learner_grade, faecher.name(exam["subject"]), tage,
                                       themen, _profil(themen)),
            schema=prompts.PLAN_SCHEMA,
            system=prompts.SYSTEM,
        )
    except ClaudeError as exc:
        with db.tx() as c:
            c.execute("UPDATE exam_plan SET state='fehler', fehler=? WHERE id=?",
                      (str(exc), plan["id"]))
        return

    daten = ergebnis.data
    with db.tx() as c:
        c.execute(
            """UPDATE exam_plan SET state='bereit', einschaetzung=?,
                                     tagesplan=? WHERE id=?""",
            (daten.get("einschaetzung") or "",
             json.dumps(daten.get("tagesplan") or [], ensure_ascii=False),
             plan["id"]))


def holen_plan(exam_id: int) -> dict | None:
    row = db.q1("SELECT * FROM exam_plan WHERE exam_id = ?", exam_id)
    if row is None:
        return None
    d = dict(row)
    try:
        d["tagesplan_liste"] = json.loads(d["tagesplan"] or "[]")
    except json.JSONDecodeError:
        d["tagesplan_liste"] = []
    from . import exam_learning
    for index, tag in enumerate(d["tagesplan_liste"]):
        code = tag.get("topic_code")
        thema = db.q1("SELECT id FROM topic WHERE code = ?", code) if code else None
        tag["topic_id"] = thema["id"] if thema else None
        key = json.dumps([index, tag.get("tag"), code, tag.get("inhalt")], ensure_ascii=False)
        tag["row_key"] = hashlib.sha256(key.encode()).hexdigest()[:24]
        tag["materialien"] = exam_learning.fuer_zeile(exam_id, tag["row_key"])
    return d
