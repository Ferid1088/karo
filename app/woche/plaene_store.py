"""SQLite-Repository fuer das zeitbasierte Zielsystem."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .. import db
from . import plaene


def init() -> None:
    db.conn().executescript(Path(__file__).with_name("plaene.sql").read_text(encoding="utf-8"))


def _dict(row):
    return dict(row) if row else None


def goal(goal_id: int) -> dict:
    init()
    row = db.q1("SELECT * FROM plan_goal WHERE id=? AND child_key='installation'", goal_id)
    if not row:
        raise LookupError("Dieses Ziel ist nicht verfügbar.")
    return dict(row)


def goals(statuses=("active", "paused", "completed")) -> list[dict]:
    init()
    marks = ",".join("?" for _ in statuses)
    return [dict(row) for row in db.q(
        f"SELECT * FROM plan_goal WHERE child_key='installation' AND status IN ({marks}) ORDER BY created_at DESC", *statuses)]


def sessions(goal_id: int | None = None, start: date | None = None, end: date | None = None) -> list[dict]:
    init()
    where, args = ["g.child_key='installation'"], []
    if goal_id is not None:
        where.append("s.goal_id=?"); args.append(goal_id)
    if start is not None:
        where.append("s.scheduled_date>=?"); args.append(str(start))
    if end is not None:
        where.append("s.scheduled_date<=?"); args.append(str(end))
    sql = """SELECT s.*,g.statement,g.status AS goal_status,c.actual_minutes,c.focus_percent,
                    c.completed_at,c.is_makeup
             FROM plan_session s JOIN plan_goal g ON g.id=s.goal_id
             LEFT JOIN plan_completion c ON c.planned_session_id=s.id
             WHERE """ + " AND ".join(where) + " ORDER BY s.scheduled_date,s.id"
    return [dict(row) for row in db.q(sql, *args)]


def session(session_id: int) -> dict:
    rows = [row for row in sessions() if row["id"] == session_id]
    if not rows:
        raise LookupError("Diese Einheit ist nicht verfügbar.")
    return rows[0]


def create_goal(statement: str, start: date, end: date, minutes: int, weekdays) -> int:
    init()
    statement, days = plaene.validate_goal(statement, start, end, minutes, weekdays)
    stamp = db.now()
    with db.tx() as connection:
        cursor = connection.execute(
            "INSERT INTO plan_goal(statement,start_date,end_date,planned_minutes,weekdays,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (statement, str(start), str(end), minutes, ",".join(map(str, days)), stamp, stamp))
        goal_id = int(cursor.lastrowid)
        connection.executemany(
            "INSERT INTO plan_session(goal_id,scheduled_date,planned_minutes,created_at) VALUES(?,?,?,?)",
            [(goal_id, str(day), minutes, stamp) for day in plaene.schedule_dates(start, end, days)])
    return goal_id


def update_future(goal_id: int, statement: str, end: date, minutes: int, weekdays, effective: date) -> None:
    old = goal(goal_id)
    if old["status"] == "archived":
        raise ValueError("Ein Ziel in der Schatzkiste ist schreibgeschützt.")
    statement, days = plaene.validate_goal(statement, date.fromisoformat(old["start_date"]), end, minutes, weekdays)
    stamp = db.now()
    with db.tx() as connection:
        connection.execute("DELETE FROM plan_session WHERE goal_id=? AND scheduled_date>=? AND status='planned'", (goal_id, str(effective)))
        connection.execute("UPDATE plan_goal SET statement=?,end_date=?,planned_minutes=?,weekdays=?,updated_at=? WHERE id=?",
                           (statement, str(end), minutes, ",".join(map(str, days)), stamp, goal_id))
        existing = {row[0] for row in connection.execute("SELECT scheduled_date FROM plan_session WHERE goal_id=?", (goal_id,))}
        new_start = max(effective, date.fromisoformat(old["start_date"]))
        new_status = "cancelled" if old["status"] == "paused" else "planned"
        connection.executemany(
            "INSERT INTO plan_session(goal_id,scheduled_date,planned_minutes,status,created_at) VALUES(?,?,?,?,?)",
            [(goal_id, str(day), minutes, new_status, stamp) for day in plaene.schedule_dates(new_start, end, days) if str(day) not in existing])


def mark_missed(day: date) -> None:
    init()
    db.conn().execute("UPDATE plan_session SET status='missed' WHERE status='planned' AND scheduled_date<?", (str(day),))


def complete(session_id: int, actual: int, focus: int, completed_at: datetime | None = None) -> None:
    if not 0 <= actual <= 60 or not 0 <= focus <= 100:
        raise ValueError("Zeit und Konzentration liegen außerhalb des erlaubten Bereichs.")
    item = session(session_id)
    if item["status"] == "cancelled" or item["goal_status"] in ("paused", "archived"):
        raise ValueError("Diese Einheit kann gerade nicht abgeschlossen werden.")
    stamp_dt = completed_at or datetime.now(timezone.utc)
    stamp = stamp_dt.isoformat(timespec="seconds")
    makeup = item["status"] == "missed" or date.fromisoformat(item["scheduled_date"]) < plaene.today(stamp_dt)
    status = "made_up" if makeup else "completed"
    with db.tx() as connection:
        connection.execute("""INSERT INTO plan_completion(planned_session_id,actual_minutes,focus_percent,completed_at,is_makeup)
                              VALUES(?,?,?,?,?) ON CONFLICT(planned_session_id) DO UPDATE SET
                              actual_minutes=excluded.actual_minutes,focus_percent=excluded.focus_percent,
                              completed_at=excluded.completed_at,is_makeup=excluded.is_makeup""",
                           (session_id, actual, focus, stamp, int(makeup)))
        connection.execute("UPDATE plan_session SET status=? WHERE id=?", (status, session_id))


def set_status(goal_id: int, status: str) -> None:
    if status not in ("active", "paused", "completed", "archived"):
        raise ValueError("Unbekannter Zielstatus.")
    old = goal(goal_id)
    now = db.now()
    completed = (now if status == "completed" and not old["completed_at"] else old["completed_at"])
    archived = now if status == "archived" else old["archived_at"]
    if status == "active":
        completed = None
        archived = None
    current = plaene.today()
    with db.tx() as connection:
        connection.execute("UPDATE plan_goal SET status=?,completed_at=?,archived_at=?,updated_at=? WHERE id=?",
                           (status, completed, archived, now, goal_id))
        if status in ("paused", "completed"):
            connection.execute("UPDATE plan_session SET status='cancelled' WHERE goal_id=? AND scheduled_date>=? AND status='planned'",
                               (goal_id, str(current)))
        elif status == "active" and old["status"] in ("paused", "completed", "archived"):
            connection.execute("DELETE FROM plan_session WHERE goal_id=? AND scheduled_date>=? AND status='cancelled'",
                               (goal_id, str(current)))
            existing = {row[0] for row in connection.execute("SELECT scheduled_date FROM plan_session WHERE goal_id=?", (goal_id,))}
            end = date.fromisoformat(old["end_date"])
            stamp = db.now()
            connection.executemany(
                "INSERT INTO plan_session(goal_id,scheduled_date,planned_minutes,created_at) VALUES(?,?,?,?)",
                [(goal_id, str(day), old["planned_minutes"], stamp)
                 for day in plaene.schedule_dates(current, end, old["weekdays"].split(","))
                 if str(day) not in existing])


def delete(goal_id: int) -> None:
    goal(goal_id)
    db.conn().execute("DELETE FROM plan_goal WHERE id=?", (goal_id,))


def repeat(goal_id: int, start: date) -> int:
    old = goal(goal_id)
    duration = date.fromisoformat(old["end_date"]) - date.fromisoformat(old["start_date"])
    return create_goal(old["statement"], start, start + duration, old["planned_minutes"], old["weekdays"].split(","))
