"""Exam month presentation: accurate totals and exam-only destinations."""
from datetime import date
from pathlib import Path
import re

from jinja2 import Environment, FileSystemLoader, select_autoescape


def _exam(app_env, subject, exam_date):
    with app_env.db.tx() as connection:
        return connection.execute(
            "INSERT INTO exam(subject,exam_date,themen,created_at) VALUES(?,?,?,?)",
            (subject, exam_date, "[]", app_env.db.now()),
        ).lastrowid


def _render(calendar, weekdays):
    env = Environment(
        loader=FileSystemLoader(Path(__file__).parents[1] / "app/templates"),
        autoescape=select_autoescape(),
    )
    return str(env.get_template("_exam_monat.html").module.exam_monat(
        calendar, weekdays, lambda: ""))


def test_month_totals_and_same_day_exam_priority(app_env, monkeypatch):
    from app.services import exam_calendar
    app_env.db.init()
    monkeypatch.setattr("app.db.today", lambda: "2026-09-27")
    later = _exam(app_env, "Mathematik", "2026-10-02")
    today = _exam(app_env, "Deutsch", "2026-09-27")
    other = _exam(app_env, "Englisch", "2026-10-08")
    for exam_id, study_date, minutes in [
        (later, "2026-09-27", 20), (other, "2026-09-27", 15),
        (later, "2026-09-29", 10), (later, "2026-10-01", 12),
    ]:
        with app_env.db.tx() as connection:
            connection.execute(
                "INSERT INTO exam_schedule_day(exam_id,study_date,minutes,updated_at) VALUES(?,?,?,?)",
                (exam_id, study_date, minutes, app_env.db.now()))
    calendar = exam_calendar.monat("2026-09", date(2026, 9, 27))
    assert calendar["pruefungen"] == 1
    assert calendar["lerntage"] == 2
    assert calendar["lernminuten"] == 45
    day = next(t for w in calendar["wochen"] for t in w if t["heute"])
    assert day["lernminuten"] == 35
    assert day["eintraege"][0]["exam_id"] == today
    assert day["eintraege"][0]["art"] == "arbeit"
    assert day["weekday"] == "Sonntag"
    assert all(e["exam_date"] for e in day["eintraege"])
    html = _render(calendar, exam_calendar.WEEKDAY_LABELS)
    assert 'aria-current="date"' in html
    assert "20 Min. lernen" in html
    assert "für 02.10." in html
    assert "/lernen/" not in html
    assert "<form" not in html
    assert "/simulation" not in html
    assert all(h.startswith("/klassenarbeit") for h in re.findall(r'href="([^"]+)"', html))


def test_empty_month_and_year_navigation(app_env):
    from app.services import exam_calendar
    app_env.db.init()
    calendar = exam_calendar.monat("2026-12", date(2026, 9, 27))
    assert calendar["vorher"] == "2026-11"
    assert calendar["nachher"] == "2027-01"
    assert calendar["pruefungen"] == calendar["lerntage"] == calendar["lernminuten"] == 0
    assert all(len(w) == 7 for w in calendar["wochen"])
    html = _render(calendar, exam_calendar.WEEKDAY_LABELS)
    assert "Hier ist noch Platz für deine Pläne." in html
    assert "0 Min." in html


def test_event_statuses_keep_their_own_exam_links(app_env):
    from app.services import exam_calendar
    app_env.db.init()
    calendar = exam_calendar.monat("2026-09", date(2026, 9, 27))
    day = next(t for w in calendar["wochen"] for t in w if t["heute"])
    day["eintraege"] = [
        {"exam_id": 10 + i, "exam_date": "2026-10-02", "subject": "Mathe <Test>",
         "minutes": 15, "farbe": i % 5, "art": kind}
        for i, kind in enumerate(["arbeit", "geplant", "probe", "geschafft", "verpasst"])
    ]
    html = _render(calendar, exam_calendar.WEEKDAY_LABELS)
    for i in range(5):
        assert f'href="/klassenarbeit/{10 + i}' in html
    assert "Mathe &lt;Test&gt;" in html
    assert "15 Min. · Generalprobe" in html
    assert "15 Min. · gelernt" in html
    assert "15 Min. · verpasst" in html
    assert "/simulation" not in html
    assert "/lernen/" not in html
