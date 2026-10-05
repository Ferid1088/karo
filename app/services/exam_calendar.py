"""Persönlicher Lernkalender für eine Klassenarbeit.

Der fachliche Lernplan entscheidet WAS geübt wird. Das Kind entscheidet für
jeden Kalendertag bis zur Arbeit separat, ob und wie lange es lernen möchte.
"""
from __future__ import annotations

import datetime as dt

from .. import db, topics, faecher

WEEKDAY_LABELS = {
    1: "Montag", 2: "Dienstag", 3: "Mittwoch", 4: "Donnerstag",
    5: "Freitag", 6: "Samstag", 7: "Sonntag",
}


class ExamCalendarError(ValueError):
    pass


def _exam(exam_id: int) -> dict:
    row = db.q1(f"SELECT * FROM exam WHERE id=? AND deleted_at IS NULL AND purged_at IS NULL AND subject IN {faecher.SQL_FAECHER}", exam_id)
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
        c.executemany(
            """INSERT INTO exam_schedule_day(exam_id,study_date,minutes,updated_at)
               VALUES(?,?,?,?) ON CONFLICT(exam_id,study_date) DO UPDATE SET
                 minutes=excluded.minutes, updated_at=excluded.updated_at""",
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
    # Die Prüfungsthemen einmal holen — Inhaltsliste und Ersatzzeile
    # fragten frueher je Tag erneut danach, die Themenverteilung kostet
    # sonst denselben Rundgang noch einmal.
    from .learning_hub import exam_topics
    members = exam_topics(exam_id)
    # Prüfungsthemen in Lernreihenfolge, bereits sichere Themen zuletzt.
    # Der Kalender bleibt beim ersten noch nicht MASTERED Thema. Nach dessen
    # Abschluss wird beim nächsten Render automatisch das nächste Thema aktiv.
    content = [{"inhalt": t['label'], "topic_id": t['id']} for t in members
               if t['learning_status'] != 'sicher']
    geladen: dict[int, dict | None] = {}
    result = []

    positive_days = sorted(
        dt.date.fromisoformat(day) for day, minutes in saved.items()
        if minutes > 0 and dt.date.fromisoformat(day) < exam_day
    )
    simulation_day = positive_days[-1] if positive_days else None
    if simulation_day and simulation_early(exam_id):
        earlier = simulation_day - dt.timedelta(days=1)
        simulation_day = earlier

    # Themen auf die gewaehlten Lerntage verteilen — nach den Minuten des
    # Tages und der angekuendigten Reihenfolge, die die Voraussetzungen
    # traegt. Vorher stand an jedem Lerntag dasselbe erste offene Thema; ein
    # Kind konnte damit nicht sehen, ob seine Zeit ueberhaupt reicht.
    from . import exam_effort
    lerntage = [(tag, int(saved.get(str(tag), 0))) for tag in positive_days
                if tag >= today and tag != simulation_day]
    verteilt = exam_effort.verteilung(exam_id, lerntage)

    for day in _date_range(today, exam_day, include_end=True):
        is_exam = day == exam_day
        minutes = 0 if is_exam else int(saved.get(str(day), 0))
        is_simulation = bool(simulation_day and day == simulation_day)
        row = None
        tagesthemen = verteilt.get(str(day), []) if not is_simulation else []
        if minutes > 0 and not is_simulation:
            if tagesthemen:
                row = {"inhalt": " · ".join(z["label"] for z in tagesthemen),
                       "topic_id": tagesthemen[0]["topic_id"]}
            else:
                row = content[0] if content else None
                row = row or {
                    "inhalt": ("Alles sicher – Zeit zum Wiederholen" if members
                               else "Zuerst Prüfungsthemen ergänzen"),
                    "topic_id": None,
                }

        topic_id = row.get("topic_id") if row else None
        if topic_id is not None and topic_id not in geladen:
            geladen[topic_id] = topics.get(int(topic_id))
        topic = geladen.get(topic_id) if topic_id else None
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
            "themen": tagesthemen,
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
        f"""SELECT e.* FROM exam e
           WHERE e.exam_date>? AND e.deleted_at IS NULL AND e.purged_at IS NULL
             AND e.subject IN {faecher.SQL_FAECHER}
           ORDER BY e.exam_date,e.id""", today)]
    for exam in exams:
        # Ein Tagespaket gibt es nur an Tagen mit geplanten Minuten oder
        # an der Generalprobe. Beides steht in den gespeicherten Tagen —
        # ohne den billigen Check baute jeder Aufruf den ganzen Kalender
        # jeder anstehenden Arbeit, samt Themenverteilung je Tag.
        saved = get_days(exam["id"])
        if int(saved.get(today, 0) or 0) <= 0 \
                and today != (simulation_date(exam["id"]) or ""):
            continue
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
    exam_day = dt.date.fromisoformat(_exam(exam_id)["exam_date"])
    geplant = {tag: int(minuten) for tag, minuten in get_days(exam_id).items()}

    tage = {d["date"]: d for d in calendar(exam_id)}
    offene = [d for d in tage.values() if d["is_learning_day"] and not d["is_exam"]]
    naechster = next(iter(sorted(offene, key=lambda d: d["date"])), None)
    alle_lerntage = [t for t, m in geplant.items() if m > 0 and t != str(exam_day)]
    return {"next_day": naechster,
            "learning_days": len(alle_lerntage),
            "planned_minutes": sum(geplant[t] for t in alle_lerntage),
            "days_left": (exam_day - heute).days,
            "period": _zeitraum(min(alle_lerntage) if alle_lerntage else str(heute),
                                str(exam_day))}


def _tage_mit_sitzung(exam_id: int, von: str, bis: str) -> set[str]:
    """Tage, an denen fuer DIESE Arbeit gelernt wurde.

    Ohne die Einschraenkung auf ihre Themen faerbte auch eine Runde in einem
    eigenen Lernthema den Prüfungstag gruen — die Karte behauptete dann einen
    Lerntag, den es nicht gab.
    """
    return {zeile["tag"] for zeile in db.q(
        """SELECT DISTINCT substr(s.updated_at, 1, 10) AS tag
             FROM lern_sitzung s
             JOIN lern_eingabe e ON e.id = s.eingabe_id
             JOIN exam_topic x ON x.topic_id = e.topic_id
            WHERE x.exam_id = ?
              AND substr(s.updated_at, 1, 10) BETWEEN ? AND ?""",
        exam_id, von, bis)}


def learned_on(exam_id: int, day: str) -> bool:
    """Ob an ``day`` fuer diese Arbeit gelernt wurde — fuer die Tagesliste."""
    return day in _tage_mit_sitzung(exam_id, day, day)


def rehearsal_done(exam_id: int) -> bool:
    """Die Generalprobe ist durch, wenn mindestens ein Thema abgeschlossen
    und keines mehr halb bearbeitet ist."""
    from . import exam_rehearsal
    exam_rehearsal.init()
    row = db.q1("""SELECT SUM(finished_at IS NOT NULL) AS fertig, SUM(finished_at IS NULL) AS offen
                     FROM exam_rehearsal WHERE exam_id=?""", exam_id)
    return bool(row and row["fertig"] and not row["offen"])


def _zeitraum(start: str, ende: str) -> str:
    """Zeitraum in deutscher Schreibweise — wie `woche/plaene.period_label`."""
    teile = [dt.date.fromisoformat(w).strftime("%d.%m.%Y") for w in (start, ende) if w]
    return " \u2013 ".join(teile)


def _tages_art(arbeit: dict, tag: str, heute: dt.date) -> str:
    """Ampel je geplanten Tag: geschafft, verpasst, geplant — oder Probe."""
    if tag in arbeit["gelernt"]:
        return "geschafft"
    if arbeit["probe"] == tag:
        return "probe"
    return "verpasst" if dt.date.fromisoformat(tag) < heute else "geplant"


MONATE = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember")

MONATE_KURZ = ("Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug",
               "Sep", "Okt", "Nov", "Dez")


def monat(wunsch: str = "", heute: dt.date | None = None) -> dict:
    """Alle Klassenarbeiten in einem Monatsraster.

    Ein Kind hat selten nur eine Arbeit. Die Karten zeigen je Arbeit ihren
    Stand; dieser Kalender zeigt umgekehrt je Tag, fuer welche Arbeit wie
    lange geplant ist — damit auffaellt, wenn an einem Dienstag drei
    Arbeiten gleichzeitig Zeit wollen.
    """
    heute = heute or dt.date.fromisoformat(db.today())
    try:
        jahr, nummer = (int(teil) for teil in (wunsch or "").split("-"))
        erster = dt.date(jahr, nummer, 1)
    except (ValueError, TypeError):
        erster = heute.replace(day=1)

    letzter = (erster + dt.timedelta(days=31)).replace(day=1) - dt.timedelta(days=1)
    start = erster - dt.timedelta(days=erster.isoweekday() - 1)
    ende = letzter + dt.timedelta(days=7 - letzter.isoweekday())

    arbeiten = [dict(r) for r in db.q(
        f"SELECT id, subject, exam_date FROM exam WHERE deleted_at IS NULL AND purged_at IS NULL AND subject IN {faecher.SQL_FAECHER} ORDER BY exam_date, id")]
    for platz, arbeit in enumerate(arbeiten):
        arbeit["farbe"] = platz % 5
        arbeit["probe"] = simulation_date(arbeit["id"])
        # Je Arbeit nur ihre eigenen Lernrunden — sonst faerbte eine Runde in
        # einem eigenen Lernthema den Tag einer Arbeit gruen.
        arbeit["gelernt"] = _tage_mit_sitzung(arbeit["id"], str(start), str(ende))
        from .learning_hub import exam_topics
        offen = next((t for t in exam_topics(arbeit["id"])
                      if t["learning_status"] != "sicher"), None)
        arbeit["thema_id"] = offen["id"] if offen else None
        arbeit["thema"] = offen["label"] if offen else ""
    nach_id = {arbeit["id"]: arbeit for arbeit in arbeiten}

    plan: dict[str, list[dict]] = {}
    for zeile in db.q(
            """SELECT exam_id, study_date, minutes FROM exam_schedule_day
                WHERE study_date BETWEEN ? AND ? AND minutes > 0
                ORDER BY study_date, exam_id""", str(start), str(ende)):
        arbeit = nach_id.get(zeile["exam_id"])
        if arbeit is None or zeile["study_date"] == arbeit["exam_date"]:
            continue
        plan.setdefault(zeile["study_date"], []).append({
            "exam_id": arbeit["id"], "subject": arbeit["subject"],
            "exam_date": arbeit["exam_date"],
            "farbe": arbeit["farbe"], "minutes": int(zeile["minutes"]),
            "thema_id": arbeit["thema_id"], "thema": arbeit["thema"],
            "art": _tages_art(arbeit, zeile["study_date"], heute)})

    for arbeit in arbeiten:
        # Vorziehen kann die Probe auf einen bisher freien Tag legen. Sie
        # bleibt sichtbar, ohne dem Kind ungeplante Minuten zuzuschreiben.
        probe = arbeit["probe"]
        if (probe and str(start) <= probe <= str(ende)
                and not any(e["exam_id"] == arbeit["id"] for e in plan.get(probe, []))):
            plan.setdefault(probe, []).append({
                "exam_id": arbeit["id"], "subject": arbeit["subject"],
                "exam_date": arbeit["exam_date"], "farbe": arbeit["farbe"],
                "minutes": 0, "thema_id": arbeit["thema_id"],
                "thema": arbeit["thema"], "art": "probe"})
        if str(start) <= arbeit["exam_date"] <= str(ende):
            plan.setdefault(arbeit["exam_date"], []).append({
                "exam_id": arbeit["id"], "subject": arbeit["subject"],
                "exam_date": arbeit["exam_date"],
                "farbe": arbeit["farbe"], "minutes": 0,
                "thema_id": arbeit["thema_id"], "thema": arbeit["thema"],
                "art": "arbeit"})

    wochen, tag = [], start
    while tag <= ende:
        reihe = []
        for _ in range(7):
            eintraege = sorted(plan.get(str(tag), []),
                               key=lambda e: (e["art"] != "arbeit", e["exam_id"]))
            fremd = tag.month != erster.month
            reihe.append({"date": str(tag), "nummer": tag.day,
                          "date_label": tag.strftime("%d.%m.%Y"),
                          "weekday": WEEKDAY_LABELS[tag.isoweekday()],
                          "lernminuten": sum(e["minutes"] for e in eintraege),
                          "im_monat": not fremd,
                          "monat_kurz": MONATE_KURZ[tag.month - 1] if fremd else "",
                          "heute": tag == heute, "eintraege": eintraege})
            tag += dt.timedelta(days=1)
        wochen.append(reihe)

    im_monat = [e for woche in wochen for t in woche if t["im_monat"]
                for e in t["eintraege"]]
    return {"titel": f"{MONATE[erster.month - 1]} {erster.year}",
            "wochen": wochen,
            "vorher": (erster - dt.timedelta(days=1)).strftime("%Y-%m"),
            "nachher": (letzter + dt.timedelta(days=1)).strftime("%Y-%m"),
            "jetzt": heute.strftime("%Y-%m"),
            "arbeiten": [a for a in arbeiten
                         if any(e["exam_id"] == a["id"] for e in im_monat)],
            "pruefungen": sum(e["art"] == "arbeit" for e in im_monat),
            "lerntage": sum(t["lernminuten"] > 0 for w in wochen
                            for t in w if t["im_monat"]),
            "lernminuten": sum(e["minutes"] for e in im_monat)}
