"""Pure Zeit- und Fortschrittsregeln fuer Meine Plaene."""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .. import config

WEEKDAY_LABELS = {1: "Mo", 2: "Di", 3: "Mi", 4: "Do", 5: "Fr", 6: "Sa", 7: "So"}


def today(now: datetime | None = None) -> date:
    zone = ZoneInfo(getattr(config.load_safe(), "timezone", None) or "Europe/Berlin")
    return (now or datetime.now(ZoneInfo("UTC"))).astimezone(zone).date()


def percent(actual: float, planned: float) -> float:
    return actual / planned * 100 if planned else 0.0


def focused_minutes(actual: int, focus: int) -> float:
    return actual * focus / 100


def aggregate(rows, due_on: date | None = None) -> dict:
    """Eine Formel fuer Tag, Woche, Monat und Gesamtziel."""
    selected = []
    for row in rows:
        scheduled = date.fromisoformat(str(row["scheduled_date"]))
        if due_on is None or scheduled <= due_on:
            selected.append(row)
    planned = sum(int(r["planned_minutes"]) for r in selected if r["status"] != "cancelled")
    actual = sum(int(r.get("actual_minutes") or 0) for r in selected)
    focus_sum = sum(focused_minutes(int(r.get("actual_minutes") or 0), int(r.get("focus_percent") or 0)) for r in selected)
    return {
        "planned": planned,
        "actual": actual,
        "focused": round(focus_sum),
        "focus": round(focus_sum / actual * 100) if actual else 0,
        "percent": round(percent(actual, planned)),
    }


def goal_statistics(rows, selected_date: date) -> dict:
    due = aggregate(rows, selected_date)
    total = aggregate(rows)
    return {
        **total,
        "due_planned": due["planned"],
        "due_actual": due["actual"],
        "adherence": due["percent"],
        "progress": total["percent"],
    }


def motivation(stats: dict) -> dict:
    """Fortschrittsabhängige, ehrliche Kinderansprache für alle Planseiten."""
    planned = int(stats.get("planned") or stats.get("due_planned") or 0)
    actual = int(stats.get("actual") or stats.get("due_actual") or 0)
    score = int(stats.get("adherence", stats.get("percent", 0)) or 0)
    if planned <= 0:
        return {
            "title": "Dein nächster Schritt wartet!",
            "text": "Lege ein Ziel an, wenn du bereit bist.",
            "tone": "ready",
            "fox": "/static/karo-fox-wave.png",
        }
    if actual <= 0:
        return {
            "title": "Heute kannst du anfangen!",
            "text": "Noch ist nichts erledigt. Ein kleiner Schritt reicht für den Start.",
            "tone": "start",
            "fox": "/static/karo-fox-wave.png",
        }
    if score >= 115:
        return {
            "title": "Wow, du bist weit voraus!",
            "text": f"Du hast {score - 100} % mehr geschafft als bis jetzt geplant.",
            "tone": "ahead",
            "fox": "/static/karo-fox-cheer.png",
        }
    if score >= 100:
        return {
            "title": "Du bist deinem Plan voraus!" if score > 100 else "Genau im Plan!",
            "text": (f"Du hast {score - 100} % mehr geschafft als geplant." if score > 100
                     else "Du hast bis heute genau deine geplante Zeit geschafft."),
            "tone": "ahead",
            "fox": "/static/karo-fox-cheer.png",
        }
    if score >= 80:
        return {
            "title": "Du bist gut im Plan!",
            "text": f"Du hast schon {score} % deiner bis heute geplanten Zeit geschafft.",
            "tone": "steady",
            "fox": "/static/karo-fox-star.png",
        }
    if score >= 50:
        return {
            "title": "Du bist auf einem guten Weg!",
            "text": f"Du hast {score} % deiner bis heute geplanten Zeit geschafft.",
            "tone": "steady",
            "fox": "/static/karo-fox-star.png",
        }
    return {
        "title": "Jeder Schritt zählt!",
        "text": f"Du hast {score} % geschafft. Deine nächste Einheit bringt dich weiter.",
        "tone": "encourage",
        "fox": "/static/karo-fox-wave.png",
    }


def week_bounds(day: date) -> tuple[date, date]:
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def month_bounds(day: date) -> tuple[date, date]:
    return day.replace(day=1), day.replace(day=calendar.monthrange(day.year, day.month)[1])


def parse_weekdays(values) -> tuple[int, ...]:
    try:
        result = tuple(sorted({int(value) for value in values}))
    except (TypeError, ValueError):
        raise ValueError("Bitte gültige Lerntage auswählen.") from None
    if not result or any(day < 1 or day > 7 for day in result):
        raise ValueError("Bitte mindestens einen Lerntag auswählen.")
    return result


def schedule_dates(start: date, end: date, weekdays) -> list[date]:
    allowed = set(parse_weekdays(weekdays))
    result, current = [], start
    while current <= end:
        if current.isoweekday() in allowed:
            result.append(current)
        current += timedelta(days=1)
    return result


def validate_goal(statement: str, start: date, end: date, minutes: int, weekdays) -> tuple[str, tuple[int, ...]]:
    statement = " ".join((statement or "").split())
    if not statement or len(statement) > 180:
        raise ValueError("Bitte beschreibe dein Ziel in einem kurzen Satz.")
    if end < start:
        raise ValueError("Das Enddatum muss nach dem Start liegen.")
    if not 1 <= minutes <= 60:
        raise ValueError("Die Zeit muss zwischen 1 und 60 Minuten liegen.")
    days = parse_weekdays(weekdays)
    if not schedule_dates(start, end, days):
        raise ValueError("In diesem Zeitraum liegt keiner deiner Lerntage.")
    return statement, days
