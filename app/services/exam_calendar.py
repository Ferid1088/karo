"""Persönlicher Lernkalender für eine Klassenarbeit.

Der fachliche Lernplan entscheidet WAS geübt wird. Das Kind entscheidet für
jeden Kalendertag bis zur Arbeit separat, ob und wie lange es lernen möchte.
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


def _date_range(start: dt.date, end: dt.date, *, include_end: bool = False):
    current = start
    limit = end + dt.timedelta(days=1) if include_end else end
    while current < limit:
        yield current
        current += dt.timedelta(days=1)


def save_days(exam_id: int, minutes_by_date: dict[str, int]) -> None:
    """Speichert die Minuten für jeden Tag. 0 Minuten bedeutet kein Lerntag."""
    exam = _exam(exam_id)
    today = dt.date.fromisoformat(db.today())
    exam_day = dt.date.fromisoformat(exam["exam_date"])
    if exam_day <= today:
        raise ExamCalendarError(
            "Für diese Klassenarbeit kann kein Lernkalender mehr geändert werden.")

    allowed = {str(day) for day in _date_range(today, exam_day)}
    cleaned: dict[str, int] = {}
    for raw_date, raw_minutes in minutes_by_date.items():
        if raw_date not in allowed:
            continue
        try:
            value = int(raw_minutes)
        except (TypeError, ValueError):
            raise ExamCalendarError("Bitte für jeden Tag gültige Minuten eintragen.") from None
        if not 0 <= value <= 60:
            raise ExamCalendarError("Die Lernzeit pro Tag muss zwischen 0 und 60 Minuten liegen.")
        cleaned[raw_date] = value

    stamp = db.now()
    with db.tx() as c:
        c.execute("DELETE FROM exam_schedule_day WHERE exam_id=?", (exam_id,))
        c.executemany(
            """INSERT INTO exam_schedule_day(exam_id,study_date,minutes,updated_at)
               VALUES(?,?,?,?)""",
            [(exam_id, day, minutes, stamp)
             for day, minutes in sorted(cleaned.items())],
        )


def get_days(exam_id: int) -> dict[str, int]:
    return {
        row["study_date"]: int(row["minutes"])
        for row in db.q(
            "SELECT study_date,minutes FROM exam_schedule_day WHERE exam_id=?",
            exam_id,
        )
    }


def simulation_early(exam_id: int) -> bool:
    row = db.q1("SELECT simulation_early FROM exam_schedule_pref WHERE exam_id=?", exam_id)
    return bool(row and row["simulation_early"])


def set_simulation_early(exam_id: int, enabled: bool) -> None:
    stamp = db.now()
    with db.tx() as c:
        c.execute(
            """INSERT INTO exam_schedule_pref(exam_id,simulation_early,updated_at)
               VALUES(?,?,?)
               ON CONFLICT(exam_id) DO UPDATE SET
                 simulation_early=excluded.simulation_early,
                 updated_at=excluded.updated_at""",
            (exam_id, int(bool(enabled)), stamp),
        )


def get(exam_id: int) -> dict | None:
    """Kompatible Zusammenfassung für bestehende Views."""
    rows = get_days(exam_id)
    if not rows:
        return None
    positive = {day: minutes for day, minutes in rows.items() if minutes > 0}
    return {
        "days": rows,
        "active_days": positive,
        "total_minutes": sum(positive.values()),
    }


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
    return [{"inhalt": str(name), "topic_id": None}
            for name in names if str(name).strip()]


def calendar(exam_id: int) -> list[dict]:
    """Alle Tage von heute bis einschließlich Prüfungstag.

    Für Lerntage wird Inhalt zugeordnet. Der Prüfungstag selbst ist nur Marker
    und kann keine Lernminuten erhalten.
    """
    exam = _exam(exam_id)
    today = dt.date.fromisoformat(db.today())
    exam_day = dt.date.fromisoformat(exam["exam_date"])
    if exam_day < today:
        return []

    saved = get_days(exam_id)
    content = _content_rows(exam_id)
    learning_index = 0
    result = []

    positive_days = sorted(
        dt.date.fromisoformat(day) for day, minutes in saved.items()
        if minutes > 0 and today <= dt.date.fromisoformat(day) < exam_day
    )
    simulation_day = positive_days[-1] if positive_days else None
    if simulation_day and simulation_early(exam_id):
        earlier = simulation_day - dt.timedelta(days=1)
        if earlier >= today:
            simulation_day = earlier

    for day in _date_range(today, exam_day, include_end=True):
        is_exam = day == exam_day
        minutes = 0 if is_exam else int(saved.get(str(day), 0))
        is_simulation = bool(simulation_day and day == simulation_day)
        row = None
        if minutes > 0 and not is_simulation:
            row = content[learning_index % len(content)] if content else {
                "inhalt": "Wiederholen für die Klassenarbeit",
                "topic_id": None,
            }
            learning_index += 1

        topic_id = row.get("topic_id") if row else None
        topic = topics.get(int(topic_id)) if topic_id else None
        thema = ((topic or {}).get("label") or (row or {}).get("inhalt")
                 or "Wiederholen für die Klassenarbeit")

        result.append({
            "date": str(day),
            "date_label": day.strftime("%d.%m.%Y"),
            "weekday": WEEKDAY_LABELS[day.isoweekday()],
            "minutes": minutes,
            "inhalt": (row or {}).get("inhalt") if row else "",
            "topic_id": topic_id,
            "thema": thema,
            "today": day == today,
            "is_exam": is_exam,
            "is_learning_day": minutes > 0,
            "is_simulation": is_simulation,
            "kind": "simulation" if is_simulation else ("learning" if minutes > 0 else "free"),
        })
    return result


def today_task() -> dict | None:
    today = db.today()
    exams = [dict(row) for row in db.q(
        """SELECT e.* FROM exam e
           WHERE e.exam_date>? ORDER BY e.exam_date,e.id""", today)]
    for exam in exams:
        task = next(
            (item for item in calendar(exam["id"])
             if item["date"] == today and (item["minutes"] > 0 or item["is_simulation"])),
            None,
        )
        if task:
            return {
                **task,
                "exam_id": exam["id"],
                "exam_date": exam["exam_date"],
                "exam_date_label": dt.date.fromisoformat(
                    exam["exam_date"]).strftime("%d.%m.%Y"),
            }
    return None
