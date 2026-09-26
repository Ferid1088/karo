"""Vom Kind gewählte Lerntage für eine Klassenarbeit.

Der KI-Lernplan entscheidet WAS geübt wird. Dieser Kalender entscheidet nur
WANN und WIE LANGE das Kind dafür lernen möchte. So bleibt die fachliche
Priorisierung getrennt von der persönlichen Zeitplanung.
"""
from __future__ import annotations

import datetime as dt
import json

from .. import db, exam_plan, topics

WEEKDAY_LABELS = {
    1: "Montag", 2: "Dienstag", 3: "Mittwoch", 4: "Donnerstag",
    5: "Freitag", 6: "Samstag", 7: "Sonntag",
}


class ExamCalendarError(ValueError):
    pass


def _exam(exam_id: int) -> dict:
    row = db.q1("SELECT * FROM exam WHERE id=?", exam_id)
    if row is None:
        raise ExamCalendarError("Klassenarbeit nicht gefunden.")
    return dict(row)


def _parse_weekdays(raw: str) -> tuple[int, ...]:
    try:
        values = tuple(sorted({int(v) for v in (raw or "").split(",") if v}))
    except ValueError:
        return ()
    return tuple(v for v in values if 1 <= v <= 7)


def save(exam_id: int, weekdays, minutes: int) -> None:
    exam = _exam(exam_id)
    try:
        days = tuple(sorted({int(v) for v in weekdays}))
    except (TypeError, ValueError):
        raise ExamCalendarError("Bitte gültige Lerntage auswählen.") from None
    if not days or any(v < 1 or v > 7 for v in days):
        raise ExamCalendarError("Bitte mindestens einen Lerntag auswählen.")
    if not 1 <= int(minutes) <= 60:
        raise ExamCalendarError("Die Lernzeit muss zwischen 1 und 60 Minuten liegen.")

    today = dt.date.fromisoformat(db.today())
    exam_day = dt.date.fromisoformat(exam["exam_date"])
    if exam_day <= today:
        raise ExamCalendarError("Für diese Klassenarbeit kann kein neuer Lernkalender mehr angelegt werden.")
    if not any(day.isoweekday() in days for day in _date_range(today, exam_day)):
        raise ExamCalendarError("Bis zur Klassenarbeit liegt keiner der gewählten Lerntage.")

    stamp = db.now()
    with db.tx() as c:
        c.execute(
            """INSERT INTO exam_schedule(exam_id, weekdays, minutes, start_date, created_at, updated_at)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(exam_id) DO UPDATE SET
                   weekdays=excluded.weekdays, minutes=excluded.minutes,
                   start_date=excluded.start_date, updated_at=excluded.updated_at""",
            (exam_id, ",".join(map(str, days)), int(minutes), str(today), stamp, stamp),
        )


def get(exam_id: int) -> dict | None:
    row = db.q1("SELECT * FROM exam_schedule WHERE exam_id=?", exam_id)
    if row is None:
        return None
    item = dict(row)
    item["weekdays_list"] = list(_parse_weekdays(item["weekdays"]))
    item["weekday_labels"] = [WEEKDAY_LABELS[d] for d in item["weekdays_list"]]
    return item


def _date_range(start: dt.date, exam_day: dt.date):
    current = start
    while current < exam_day:
        yield current
        current += dt.timedelta(days=1)


def _scheduled_dates(schedule: dict, exam: dict) -> list[dt.date]:
    start = dt.date.fromisoformat(schedule["start_date"])
    exam_day = dt.date.fromisoformat(exam["exam_date"])
    weekdays = set(schedule["weekdays_list"])
    return [day for day in _date_range(start, exam_day)
            if day.isoweekday() in weekdays]


def _content_rows(exam_id: int) -> list[dict]:
    plan = exam_plan.holen_plan(exam_id) or {}
    rows = [dict(row) for row in plan.get("tagesplan_liste", [])
            if int(row.get("minuten") or 0) > 0]
    if rows:
        return rows

    exam = _exam(exam_id)
    try:
        names = json.loads(exam.get("themen") or "[]")
    except json.JSONDecodeError:
        names = []
    active = topics.liste(topics.AKTIV)
    matching = topics.passende(names, active)
    if matching:
        return [{"inhalt": item["label"], "topic_id": item["id"]}
                for item in matching]
    return [{"inhalt": str(name), "topic_id": None} for name in names if str(name).strip()]


def calendar(exam_id: int) -> list[dict]:
    schedule = get(exam_id)
    if schedule is None:
        return []
    exam = _exam(exam_id)
    dates = _scheduled_dates(schedule, exam)
    rows = _content_rows(exam_id)
    result = []
    for index, day in enumerate(dates):
        row = rows[index % len(rows)] if rows else {
            "inhalt": "Wiederholen für die Klassenarbeit", "topic_id": None
        }
        topic_id = row.get("topic_id")
        topic = topics.get(int(topic_id)) if topic_id else None
        result.append({
            "date": str(day),
            "date_label": day.strftime("%d.%m.%Y"),
            "weekday": WEEKDAY_LABELS[day.isoweekday()],
            "minutes": int(schedule["minutes"]),
            "inhalt": row.get("inhalt") or (topic or {}).get("label") or "Wiederholen",
            "topic_id": topic_id,
            "thema": (topic or {}).get("label") or row.get("inhalt") or "Wiederholen",
            "today": str(day) == db.today(),
        })
    return result


def today_task() -> dict | None:
    today = db.today()
    exams = [dict(row) for row in db.q(
        """SELECT e.* FROM exam e
           JOIN exam_schedule s ON s.exam_id=e.id
           WHERE e.exam_date>? ORDER BY e.exam_date,e.id""", today)]
    for exam in exams:
        task = next((item for item in calendar(exam["id"]) if item["date"] == today), None)
        if task:
            return {
                **task,
                "exam_id": exam["id"],
                "exam_date": exam["exam_date"],
                "exam_date_label": dt.date.fromisoformat(exam["exam_date"]).strftime("%d.%m.%Y"),
            }
    return None
