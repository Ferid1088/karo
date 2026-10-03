"""Exam-only rehearsal snapshots, drawn from checked curriculum tasks."""
import json
import random

from .. import config, db
from ..adaptiv import inhalt_store, lektionen, store
from ..adaptiv.unterricht import ist_richtig
from . import exam_calendar, learning_hub


def init():
    with db.tx() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS exam_rehearsal (
            id INTEGER PRIMARY KEY, exam_id INTEGER NOT NULL REFERENCES exam(id),
            topic_id INTEGER NOT NULL REFERENCES topic(id),
            questions TEXT NOT NULL, answers TEXT NOT NULL DEFAULT '{}',
            result TEXT, created_at TEXT NOT NULL, finished_at TEXT,
            UNIQUE(exam_id,topic_id))""")


def _check(exam_id, topic_id):
    if not exam_calendar.simulation_available(exam_id):
        raise ValueError("Die Generalprobe öffnet erst am geplanten Tag.")
    topic = learning_hub.topic_in_scope(topic_id, exam_id)
    if topic is None:
        raise ValueError("Dieses Thema gehört nicht zu dieser Prüfung.")
    return topic


def get(exam_id, topic_id):
    _check(exam_id, topic_id)
    init()
    row = db.q1("SELECT * FROM exam_rehearsal WHERE exam_id=? AND topic_id=?", exam_id, topic_id)
    if not row:
        return None
    attempt = dict(row)
    for key in ("questions", "answers", "result"):
        attempt[key] = json.loads(attempt[key]) if attempt[key] else None
    return attempt


def start(exam_id, topic_id):
    topic = _check(exam_id, topic_id)
    existing = get(exam_id, topic_id)
    if existing:
        return existing
    lesson = lektionen.fuer_thema(topic["label"], topic["subject"], topic.get("grade"))
    if lesson is None:
        raise LookupError("Die geprüfte Lernreihe wird noch benötigt.")
    tasks = []
    seen = set()
    for error in store.fehlertypen(lesson["konzept_id"]):
        for task in inhalt_store.aufgaben(error["id"]):
            if task["rolle"] not in ("selbststaendig", "transfer") or task["frage"] in seen:
                continue
            seen.add(task["frage"])
            tasks.append({"frage": task["frage"], "loesung": task["loesung"],
                          "optionen": task.get("optionen") or [],
                          "art": task["antwort_art"]})
    if len(tasks) < 2:
        raise ValueError("Für diese Generalprobe fehlen noch geprüfte Kontrollaufgaben.")
    random.SystemRandom().shuffle(tasks)
    with db.tx() as c:
        c.execute("""INSERT OR IGNORE INTO exam_rehearsal
            (exam_id,topic_id,questions,created_at) VALUES(?,?,?,?)""",
            (exam_id, topic_id, json.dumps(tasks[:5], ensure_ascii=False), db.now()))
    return get(exam_id, topic_id)


def submit(exam_id, topic_id, answers):
    attempt = get(exam_id, topic_id)
    if not attempt:
        raise ValueError("Öffne zuerst die Generalprobe.")
    if attempt["finished_at"]:
        return attempt
    cleaned = {str(i): str(answers.get(str(i), "")).strip()[:config.ops().probe_antwort_zeichen]
               for i in range(len(attempt["questions"]))}
    if not all(cleaned.values()):
        with db.tx() as c:
            c.execute('UPDATE exam_rehearsal SET answers=? WHERE id=? AND finished_at IS NULL',
                      (json.dumps(cleaned, ensure_ascii=False), attempt['id']))
        raise ValueError("Beantworte bitte jede Aufgabe, bevor du abgibst.")
    result = [ist_richtig(cleaned[str(i)], q["loesung"], q.get("art"))
              for i, q in enumerate(attempt["questions"])]
    with db.tx() as c:
        c.execute("""UPDATE exam_rehearsal SET answers=?,result=?,finished_at=?
            WHERE id=? AND finished_at IS NULL""",
            (json.dumps(cleaned, ensure_ascii=False), json.dumps(result), db.now(), attempt["id"]))
    # A rehearsal result is its own evidence, not a personal topic's mastery.
    return get(exam_id, topic_id)


def overview(exam_id):
    """Per-topic state for the child's next step; no personal learning data."""
    from ..adaptiv import erzeugung
    result = []
    for topic in exam_calendar.simulation_topics(exam_id):
        attempt = get(exam_id, topic['id'])
        waiting = erzeugung.laeuft(topic['label'], fach=topic['subject'], klasse=topic.get('grade'))
        result.append({**topic, 'attempt': attempt, 'waiting': waiting})
    return result
