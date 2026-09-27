"""Persönlicher Lernkalender für eine Klassenarbeit.

Der fachliche Lernplan entscheidet WAS geübt wird. Das Kind entscheidet für
jeden Kalendertag bis zur Arbeit separat, ob und wie lange es lernen möchte.
"""
from __future__ import annotations

import datetime as dt
import json

from .. import db, exam_plan, topics
from ..adaptiv import store as adaptiv_store

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
        text = str(raw_minutes or "").strip()
        if text == "":
            value = 0
        else:
            try:
                value = int(text)
            except (TypeError, ValueError):
                raise ExamCalendarError(
                    "Bitte nur ganze Zahlen zwischen 0 und 60 eintragen.") from None
            if not 0 <= value <= 60:
                raise ExamCalendarError(
                    "Die Lernzeit muss zwischen 0 und 60 Minuten liegen.")
        cleaned[raw_date] = value

    stamp = db.now()
    with db.tx() as c:
        c.execute("DELETE FROM exam_schedule_day WHERE exam_id=? AND study_date>=?", (exam_id, str(today)))
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
    """Prüfungsthemen in Lernreihenfolge, bereits sichere Themen zuletzt.

    Der Kalender bleibt beim ersten noch nicht MASTERED Thema. Nach dessen
    Abschluss wird beim nächsten Render automatisch das nächste Thema aktiv.
    """
    from .learning_hub import exam_topics
    members = exam_topics(exam_id)
    return [{"inhalt": t['label'], "topic_id": t['id']} for t in members
            if t['learning_status'] != 'sicher']


def _legacy_content_rows(exam_id: int) -> list[dict]:
    plan = exam_plan.holen_plan(exam_id) or {}
    raw = [dict(row) for row in plan.get("tagesplan_liste", []) if int(row.get("minuten") or 0) > 0]

    if not raw:
        exam = _exam(exam_id)
        try:
            names = json.loads(exam.get("themen") or "[]")
        except json.JSONDecodeError:
            names = []
        matching = topics.passende(names, topics.liste(topics.AKTIV))
        raw = [{"inhalt": item["label"], "topic_id": item["id"]}
               for item in matching]
        if not raw:
            raw = [{"inhalt": str(name), "topic_id": None}
                   for name in names if str(name).strip()]

    # Ein Thema kann im KI-Plan an mehreren Tagen vorkommen. Für die
    # Mastery-Steuerung zählt es trotzdem nur einmal.
    seen, rows = set(), []
    for row in raw:
        key = row.get("topic_id") or row.get("inhalt")
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)

    def mastered(row: dict) -> bool:
        topic_id = row.get("topic_id")
        return bool(topic_id and adaptiv_store.topic_mastery(int(topic_id)) == "MASTERED")

    unsicher = [row for row in rows if not mastered(row)]
    sicher = [row for row in rows if mastered(row)]
    return unsicher + sicher


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
        if minutes > 0 and dt.date.fromisoformat(day) < exam_day
    )
    simulation_day = positive_days[-1] if positive_days else None
    if simulation_day and simulation_early(exam_id):
        earlier = simulation_day - dt.timedelta(days=1)
        simulation_day = earlier

    for day in _date_range(today, exam_day, include_end=True):
        is_exam = day == exam_day
        minutes = 0 if is_exam else int(saved.get(str(day), 0))
        is_simulation = bool(simulation_day and day == simulation_day)
        row = None
        if minutes > 0 and not is_simulation:
            row = content[0] if content else {
                "inhalt": "Alles sicher – Zeit zum Wiederholen",
                "topic_id": None,
            }

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


def simulation_date(exam_id: int) -> str | None:
    exam_day = _exam(exam_id)['exam_date']
    days = sorted(day for day, minutes in get_days(exam_id).items() if minutes > 0 and day < exam_day)
    if not days:
        return None
    day = dt.date.fromisoformat(days[-1])
    if simulation_early(exam_id):
        day -= dt.timedelta(days=1)
    return str(day)


def simulation_topics(exam_id: int) -> list[dict]:
    from .learning_hub import exam_topics
    return exam_topics(exam_id)


def simulation_available(exam_id: int) -> bool:
    day = simulation_date(exam_id)
    return bool(day and day <= db.today() < _exam(exam_id)['exam_date'])


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


def woche(exam_id: int, heute: dt.date | None = None) -> dict:
    """Eine Klassenarbeit in einer Zeile — wie die Lernwoche eines Ziels
    (`woche/plaene.goal_week`): ein Kreis je Wochentag, in Ampelfarben.

    Ein Kreis je Kalendertag bis zur Arbeit waeren bis zu sechzig Kaesten auf
    der Uebersicht. Die laufende Woche zeigt stattdessen, was zaehlt: was
    geschafft ist (gruen), was ausgefallen ist (rot) und was noch kommt
    (hellgruen). Der vollstaendige Kalender steht auf der Detailseite.
    """
    heute = heute or dt.date.fromisoformat(db.today())
    montag = heute - dt.timedelta(days=heute.isoweekday() - 1)
    exam_day = dt.date.fromisoformat(_exam(exam_id)["exam_date"])
    geplant = {tag: int(minuten) for tag, minuten in get_days(exam_id).items()}
    probe = simulation_date(exam_id)
    gelernt = _tage_mit_sitzung(str(montag), str(montag + dt.timedelta(days=6)))

    reihe = []
    for versatz in range(7):
        tag = montag + dt.timedelta(days=versatz)
        text = str(tag)
        minuten = 0 if tag == exam_day else geplant.get(text, 0)
        if tag == exam_day:
            zustand = "pruefung"
        elif minuten > 0:
            # Rot nur fuer einen Tag, der vorbei ist und an dem nichts lief —
            # die Lernsitzungen sagen das, nicht eine Schaetzung.
            zustand = ("geschafft" if text in gelernt
                       else "verpasst" if tag < heute else "geplant")
            # Gelb steht fuer eine Generalprobe, die noch aussteht. Eine
            # gelaufene faerbt die Ampel, sonst waere nicht zu sehen, ob sie
            # stattgefunden hat.
            if probe and text == probe and zustand == "geplant":
                zustand = "simulation"
        else:
            zustand = "frei"
        reihe.append({"date": text, "weekday": tag.isoweekday(),
                      "state": zustand, "minutes": minuten,
                      "today": tag == heute,
                      "label": _tages_text(zustand, minuten)})

    tage = {d["date"]: d for d in calendar(exam_id)}
    offene = [d for d in tage.values() if d["is_learning_day"] and not d["is_exam"]]
    naechster = next(iter(sorted(offene, key=lambda d: d["date"])), None)
    alle_lerntage = [t for t, m in geplant.items() if m > 0 and t != str(exam_day)]
    return {"days": reihe, "next_day": naechster,
            "learning_days": len(alle_lerntage),
            "planned_minutes": sum(geplant[t] for t in alle_lerntage),
            "days_left": (exam_day - heute).days,
            "period": _zeitraum(min(alle_lerntage) if alle_lerntage else str(heute),
                                str(exam_day))}


def _tage_mit_sitzung(von: str, bis: str) -> set[str]:
    """Tage, an denen tatsaechlich eine Lernsitzung lief."""
    return {zeile["tag"] for zeile in db.q(
        """SELECT DISTINCT substr(updated_at, 1, 10) AS tag
             FROM lern_sitzung
            WHERE substr(updated_at, 1, 10) BETWEEN ? AND ?""", von, bis)}


def _zeitraum(start: str, ende: str) -> str:
    """Zeitraum in deutscher Schreibweise — wie `woche/plaene.period_label`."""
    teile = [dt.date.fromisoformat(w).strftime("%d.%m.%Y") for w in (start, ende) if w]
    return " \u2013 ".join(teile)


_TAGES_TEXT = {"pruefung": "Klassenarbeit", "simulation": "Generalprobe",
               "frei": "frei"}


def _tages_text(zustand: str, minuten: int) -> str:
    if zustand == "geschafft":
        return f"{minuten} Minuten gelernt"
    if zustand == "verpasst":
        return f"{minuten} Minuten geplant, nicht gelernt"
    if zustand == "geplant":
        return f"{minuten} Minuten lernen"
    return _TAGES_TEXT.get(zustand, zustand)
