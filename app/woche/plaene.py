"""Pure Zeit- und Fortschrittsregeln fuer Meine Plaene."""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone

from .. import config

WEEKDAY_LABELS = {1: "Mo", 2: "Di", 3: "Mi", 4: "Do", 5: "Fr", 6: "Sa", 7: "So"}
MONTH_LABELS = (
    "", "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
)


def today(now: datetime | None = None) -> date:
    zone = config.zeitzone()
    return (now or datetime.now(timezone.utc)).astimezone(zone).date()


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


def shift_month(day: date, offset: int) -> date:
    """Erster Tag des Monats ``offset`` Monate vor oder nach ``day``."""
    total = day.year * 12 + day.month - 1 + offset
    year, month_index = divmod(total, 12)
    if not 1 <= year <= 9999:
        raise ValueError("Dieser Monat ist nicht verfügbar.")
    return date(year, month_index + 1, 1)


def selected_goal_month(start: date, end: date, current: date,
                        requested: str = "") -> date:
    """Waehlt einen sinnvollen Monat fuer einen Zielkalender."""
    if requested:
        try:
            selected = date.fromisoformat(requested + "-01")
        except ValueError:
            raise ValueError("Bitte einen gültigen Monat wählen.") from None
        if selected.strftime("%Y-%m") != requested:
            raise ValueError("Bitte einen gültigen Monat wählen.")
        return selected
    current = current.replace(day=1)
    start = start.replace(day=1)
    end = end.replace(day=1)
    return start if current < start else end if current > end else current


def _calendar_state(row: dict | None) -> tuple[str | None, str]:
    if row is None:
        return None, "Keine Lerneinheit geplant"
    if row["status"] == "cancelled":
        return "open", "Keine Planung"
    actual = row.get("actual_minutes")
    if actual is not None:
        achieved = percent(int(actual), int(row["planned_minutes"]))
        if achieved >= 100:
            return "reached", f"Ziel erreicht ({round(achieved)} %)"
        if achieved >= 50:
            return "partial", f"Teilweise erreicht ({round(achieved)} %)"
        return "not-reached", f"Nicht erreicht ({round(achieved)} %)"
    if row["status"] == "missed":
        return "not-reached", "Nicht erreicht"
    return "open", "Noch offen"


# Datumsangaben erscheinen im Kinderbereich deutsch, also 22.09.2026.
def date_label(value: str) -> str:
    if not value:
        return ""
    return date.fromisoformat(str(value)).strftime("%d.%m.%Y")


def period_label(start: str, end: str) -> str:
    return " \u2013 ".join(part for part in (date_label(start), date_label(end)) if part)


# Die sieben Tage der laufenden Woche fuer ein einzelnes Ziel. Jeder Lerntag
# traegt, wie viel Prozent der geplanten Zeit an dem Tag geschafft wurde; die
# Oberflaeche faerbt den Kreis danach ein.
def goal_week(rows: list[dict], current: date) -> list[dict]:
    start, _ = week_bounds(current)
    by_date = {row["scheduled_date"]: row for row in rows}
    days = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        row = by_date.get(str(day))
        share = 0
        if row is None or row["status"] == "cancelled":
            state, label = "off", "Kein Lerntag"
        elif row.get("actual_minutes") is None:
            state = "missed" if row["status"] == "missed" else "planned"
            label = "Nicht gemacht" if state == "missed" else (
                "Heute dran" if day == current else "Noch offen")
        else:
            share = min(100, round(percent(int(row["actual_minutes"]),
                                           int(row["planned_minutes"]))))
            if share >= 100:
                state, label = "done", "Geschafft"
            elif share > 0:
                state, label = "partial", f"Teilweise geschafft ({share} %)"
            else:
                state, label = "missed", "Nicht gemacht"
        days.append({"date": day, "weekday": day.isoweekday(), "state": state,
                     "percent": share, "today": day == current, "label": label})
    return days


def goal_calendar(rows: list[dict], selected: date) -> dict:
    """Vollstaendiges Monatsraster fuer genau ein Ziel."""
    selected = selected.replace(day=1)
    by_date = {str(row["scheduled_date"]): row for row in rows}
    cells = []
    weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(
        selected.year, selected.month)
    for day in (value for week in weeks for value in week):
        in_month = day.month == selected.month
        row = by_date.get(str(day)) if in_month else None
        state, state_label = _calendar_state(row)
        cells.append({
            "date": str(day),
            "day": day.day,
            "in_month": in_month,
            "state": state,
            "state_label": state_label,
            "label": f"{day.day}. {MONTH_LABELS[day.month]} {day.year}: {state_label}",
        })
    return {
        "month": selected.strftime("%Y-%m"),
        "label": f"{MONTH_LABELS[selected.month]} {selected.year}",
        "previous": shift_month(selected, -1).strftime("%Y-%m"),
        "following": shift_month(selected, 1).strftime("%Y-%m"),
        "cells": cells,
    }


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
