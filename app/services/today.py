"""Mein Tag: was heute ansteht, was schon geschafft ist und was motiviert.

"Heute" ist die erste Seite, die das Kind sieht. Sie sammelt den Tag aus den
Stellen, an denen er geplant wird — Zeitziele aus "Ziele planen" und der
Lernkalender einer Klassenarbeit — statt dass jeder Bereich sein eigenes
"Heute" zeigt. Nur echte Planungen stehen auf der Liste: ein Lernthema ohne
geplante Minuten ist ein Vorschlag, keine Aufgabe.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from .. import config, db, faecher
from ..woche import plaene, plaene_store

WOCHENTAGE = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
MONATE = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember")
ERLEDIGT = ("completed", "made_up")
#: Ein Erfolg, der laenger zurueckliegt, ist kein "kleiner Erfolg von heute".
ERFOLG_TAGE = 14


def date_label(day: dt.date) -> str:
    return f"{WOCHENTAGE[day.weekday()]}, {day.day}. {MONATE[day.month - 1]}"


def local_day(value: str) -> dt.date:
    """Kalendertag eines gespeicherten Zeitpunkts in der Zeitzone der Familie.

    `db.now()` schreibt UTC, `db.today()` liefert den lokalen Tag. Wer die
    ersten zehn Zeichen eines UTC-Zeitstempels mit einem lokalen Datum
    vergleicht, liegt jeden Abend nach 22 Uhr (Sommerzeit) einen Tag daneben:
    ein Thema, das gerade sicher wurde, stand dann sofort als "gestern" da.
    """
    roh = str(value)[:19]
    try:
        moment = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return dt.date.fromisoformat(roh[:10])
    if moment.tzinfo is None:
        return moment.date()
    zone = ZoneInfo(getattr(config.load_safe(), "timezone", None) or "Europe/Berlin")
    return moment.astimezone(zone).date()


def relative_day(value: str, today: dt.date) -> str:
    day = local_day(value)
    delta = (today - day).days
    if delta <= 0:
        return "heute"
    if delta == 1:
        return "gestern"
    if delta < 7:
        return f"vor {delta} Tagen"
    return f"am {day.day}. {MONATE[day.month - 1]}"


def _goal_items(today: dt.date) -> list[dict]:
    plaene_store.mark_missed(today)
    return [{
        "kind": "ziel",
        "key": f"ziel-{row['goal_id']}",
        "title": row["statement"],
        "minutes": row["planned_minutes"],
        "done": row["status"] in ERLEDIGT,
        "goal_id": row["goal_id"],
        "tag": "Ziel",
    } for row in plaene_store.sessions(start=today, end=today)
        if row["goal_status"] == "active" and row["status"] != "cancelled"]


def _exam_fach(exam_id: int) -> str | None:
    row = db.q1("SELECT subject FROM exam WHERE id=?", exam_id)
    return row["subject"] if row else None


def _exam_item(today: dt.date) -> dict | None:
    from . import exam_calendar
    task = exam_calendar.today_task()
    if not task:
        return None
    if task["is_simulation"]:
        done = exam_calendar.rehearsal_done(task["exam_id"])
    else:
        done = exam_calendar.learned_on(task["exam_id"], str(today))
    return {
        "kind": "arbeit",
        "key": f"arbeit-{task['exam_id']}",
        "title": "Generalprobe" if task["is_simulation"] else (task.get("thema") or task.get("inhalt")),
        "minutes": task["minutes"],
        "done": done,
        "task": task,
        # Heute ist fachübergreifend, zeigt das Fach aber immer mit an.
        "tag": f"Klassenarbeit · {faecher.name(_exam_fach(task['exam_id']))}",
    }


def activity_days() -> set[str]:
    """Tage, an denen das Kind wirklich etwas getan hat.

    Die Zeitstempel sind UTC. Ein Lernabschnitt um halb eins nachts gehoert
    zum neuen Tag der Familie, nicht zum Vortag — deshalb wird stundengenau
    gelesen und in die eingestellte Zeitzone umgerechnet.
    """
    plaene_store.init()
    sql = ["SELECT substr(created_at,1,13) AS stunde FROM answer_log",
           "SELECT substr(completed_at,1,13) FROM plan_completion WHERE actual_minutes>0"]
    # Die Lernsitzungen gibt es erst, wenn das adaptive Lernen einmal lief.
    if db.q1("SELECT 1 FROM sqlite_master WHERE type='table' AND name='lern_sitzung'"):
        sql.append("SELECT substr(updated_at,1,13) FROM lern_sitzung WHERE runden>0 OR versuche>0")
    zone = ZoneInfo(getattr(config.load_safe(), "timezone", None) or "Europe/Berlin")
    days = set()
    for row in db.q(" UNION ".join(sql)):
        try:
            hour = dt.datetime.fromisoformat(row["stunde"]).replace(tzinfo=dt.timezone.utc)
        except (TypeError, ValueError):
            continue
        days.add(str(hour.astimezone(zone).date()))
    return days


def streak(days: set[str], today: dt.date) -> int:
    """Tage in Folge bis heute. Wer heute noch nichts gemacht hat, verliert
    seine Serie nicht schon am Morgen: dann zaehlt sie bis gestern."""
    day = today if str(today) in days else today - dt.timedelta(days=1)
    count = 0
    while str(day) in days:
        count += 1
        day -= dt.timedelta(days=1)
    return count


def last_success(today: dt.date) -> dict | None:
    row = db.q1("""SELECT label,learned_at FROM topic
                   WHERE learning_visible=1 AND learned_at IS NOT NULL
                     AND deleted_at IS NULL AND purged_at IS NULL
                   ORDER BY learned_at DESC LIMIT 1""")
    if not row or (today - local_day(row["learned_at"])).days > ERFOLG_TAGE:
        return None
    return {"label": row["label"], "when": relative_day(row["learned_at"], today)}


def next_exam(today: dt.date) -> dict | None:
    from . import exam
    item = exam.get_next_exam()
    if not item:
        return None
    days = (dt.date.fromisoformat(item["exam_date"]) - today).days
    when = "heute" if days == 0 else "morgen" if days == 1 else f"in {days} Tagen"
    subject = (item.get("subject") or "").strip()
    return {**item, "days_left": days, "when": when,
            "name": f"{faecher.name(subject)}-Arbeit" if subject else "Klassenarbeit"}


def missed_goal(today: dt.date) -> dict | None:
    # Was laenger als eine Woche her ist, bleibt liegen: "Heute" soll nicht
    # an alte Luecken erinnern.
    rows = [row for row in plaene_store.sessions(start=today - dt.timedelta(days=7),
                                                  end=today - dt.timedelta(days=1))
            if row["status"] == "missed" and row["goal_status"] == "active"]
    return rows[-1] if rows else None


def capsules_today(role: str | None) -> list[dict]:
    """Zeitkapseln, die sich heute oeffnen — solange Meine Welt fuer das
    Kind freigegeben ist. Geoeffnet wird die Kapsel erst in Meine Welt."""
    from ..welten import store as welt
    if role == "child" and not welt.settings()["enabled"]:
        return []
    return welt.capsules_opening_today()


def mein_tag(today: dt.date | None = None, choice: str = "", role: str | None = "child") -> dict:
    """``choice`` ist der Eintrag, den das Kind auf der Liste angetippt hat.
    Ohne Wahl ist der erste offene Eintrag dran."""
    today = today or plaene.today()
    exams_visible = config.load().klassenarbeit_kind
    items = []
    exam_item = _exam_item(today) if exams_visible else None
    if exam_item:
        items.append(exam_item)
    items.extend(_goal_items(today))
    done = sum(item["done"] for item in items)
    minutes = sum(item["minutes"] for item in items)
    if not items:
        state = "frei"
    elif done == len(items):
        state = "fertig"
    elif done:
        state = "unterwegs"
    else:
        state = "start"
    days = activity_days()
    return {
        "date_label": date_label(today),
        "items": items,
        "done": done,
        "minutes": minutes,
        "open_minutes": sum(item["minutes"] for item in items if not item["done"]),
        "state": state,
        "next_item": next((item for item in items if not item["done"] and item["key"] == choice),
                          next((item for item in items if not item["done"]), None)),
        "streak": streak(days, today),
        "active_today": str(today) in days,
        "last_success": last_success(today),
        "exam": next_exam(today) if exams_visible else None,
        "capsules": capsules_today(role),
        # Nachholen nur an einem freien Tag: an einem vollen Tag waere es
        # eine Aufgabe mehr, am geschafften Tag ein Dämpfer.
        "missed": missed_goal(today) if state == "frei" else None,
    }
