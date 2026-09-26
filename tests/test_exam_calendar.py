"""Klassenarbeit + persönlicher Lernkalender + Heute-Einstieg."""
import json
from datetime import date

from .conftest import csrf_from
from .test_app import einrichten, kind_modus_aktivieren


def _exam_with_topic(app_env):
    from app import topics
    app_env.db.init()
    topic_id = topics.anlegen("Brüche addieren")
    topic = topics.get(topic_id)
    with app_env.db.tx() as c:
        exam_id = c.execute(
            "INSERT INTO exam(subject,exam_date,themen,created_at) VALUES(?,?,?,?)",
            ("Mathematik", "2026-10-02", json.dumps(["Brüche addieren"]), app_env.db.now()),
        ).lastrowid
        c.execute(
            """INSERT INTO exam_plan(exam_id,state,tagesplan,created_at)
               VALUES(?,'bereit',?,?)""",
            (exam_id, json.dumps([
                {"tag": "28.09.2026", "inhalt": "Brüche addieren",
                 "minuten": 20, "topic_code": topic["code"]},
            ]), app_env.db.now()),
        )
    return exam_id, topic_id


def test_exam_calendar_saves_different_minutes_for_each_day(app_env, monkeypatch):
    from app.services import exam_calendar

    exam_id, topic_id = _exam_with_topic(app_env)
    monkeypatch.setattr("app.db.today", lambda: "2026-09-27")

    exam_calendar.save_days(exam_id, {
        "2026-09-28": 23,
        "2026-09-29": 0,
        "2026-09-30": 29,
        "2026-10-01": 10,
    })

    saved = exam_calendar.get_days(exam_id)
    assert saved["2026-09-28"] == 23
    assert saved["2026-09-29"] == 0
    assert saved["2026-09-30"] == 29
    assert saved["2026-10-01"] == 10

    days = exam_calendar.calendar(exam_id)
    assert [item["date"] for item in days] == [
        "2026-09-27", "2026-09-28", "2026-09-29",
        "2026-09-30", "2026-10-01", "2026-10-02",
    ]
    assert next(item for item in days if item["date"] == "2026-09-28")["minutes"] == 23
    assert next(item for item in days if item["date"] == "2026-09-30")["minutes"] == 29
    assert next(item for item in days if item["date"] == "2026-10-02")["is_exam"]
    assert next(item for item in days if item["date"] == "2026-09-28")["topic_id"] == topic_id


def test_only_due_exam_session_appears_on_today(app_env, monkeypatch):
    from app.services import exam_calendar

    exam_id, topic_id = _exam_with_topic(app_env)
    monkeypatch.setattr("app.db.today", lambda: "2026-09-28")
    exam_calendar.save_days(exam_id, {
        "2026-09-28": 23,
        "2026-09-29": 0,
        "2026-09-30": 29,
        "2026-10-01": 0,
    })

    task = exam_calendar.today_task()
    assert task is not None
    assert task["exam_id"] == exam_id
    assert task["topic_id"] == topic_id
    assert task["minutes"] == 23
    assert task["thema"] == "Brüche addieren"

    monkeypatch.setattr("app.db.today", lambda: "2026-09-29")
    assert exam_calendar.today_task() is None


def test_child_can_save_calendar_and_today_starts_adaptive_topic(
        client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.services import exam_calendar

    einrichten(client, fake_llm)
    app_env.config.update(klassenarbeit_kind=True, adaptive_learning_enabled=True)
    exam_id, topic_id = _exam_with_topic(app_env)
    monkeypatch.setattr("app.db.today", lambda: "2026-09-28")

    kind_modus_aktivieren(client)
    exam_page = client.get("/klassenarbeit")
    response = client.post(
        f"/klassenarbeit/{exam_id}/kalender",
        data={
            "_csrf": csrf_from(exam_page.text),
            "minutes_2026-09-28": "23",
            "minutes_2026-09-29": "0",
            "minutes_2026-09-30": "29",
            "minutes_2026-10-01": "0",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert exam_calendar.get_days(exam_id)["2026-09-28"] == 23
    assert exam_calendar.get_days(exam_id)["2026-09-30"] == 29

    today = client.get("/")
    assert "HEUTE · KLASSENARBEIT" in today.text
    assert "Brüche addieren" in today.text
    assert "23 Minuten" in today.text
    assert 'action="/lernen/adaptiv/start"' in today.text
    assert f'name="topic_id" value="{topic_id}"' in today.text


def test_last_planned_day_is_simulation_and_can_move_one_day_earlier(app_env, monkeypatch):
    from app.services import exam_calendar

    exam_id, _ = _exam_with_topic(app_env)
    monkeypatch.setattr("app.db.today", lambda: "2026-09-27")
    exam_calendar.save_days(exam_id, {
        "2026-09-28": 20,
        "2026-09-29": 0,
        "2026-09-30": 25,
        "2026-10-01": 30,
    })

    days = exam_calendar.calendar(exam_id)
    assert next(item for item in days if item["date"] == "2026-10-01")["is_simulation"]
    assert not next(item for item in days if item["date"] == "2026-09-30")["is_simulation"]

    exam_calendar.set_simulation_early(exam_id, True)
    days = exam_calendar.calendar(exam_id)
    assert next(item for item in days if item["date"] == "2026-09-30")["is_simulation"]
    assert not next(item for item in days if item["date"] == "2026-10-01")["is_simulation"]


def test_simulation_questions_are_gated_until_simulation_day(
        client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.services import exam_calendar

    einrichten(client, fake_llm)
    app_env.config.update(klassenarbeit_kind=True, adaptive_learning_enabled=True)
    exam_id, topic_id = _exam_with_topic(app_env)
    exam_calendar.save_days(exam_id, {
        "2026-09-28": 20,
        "2026-09-30": 25,
        "2026-10-01": 30,
    })

    kind_modus_aktivieren(client)

    monkeypatch.setattr("app.db.today", lambda: "2026-09-30")
    assert client.get(f"/klassenarbeit/{exam_id}/simulation").status_code == 403

    monkeypatch.setattr("app.db.today", lambda: "2026-10-01")
    page = client.get(f"/klassenarbeit/{exam_id}/simulation")
    assert page.status_code == 200
    assert "Wiederholung + Prüfungssimulation" in page.text
    assert "Brüche addieren" in page.text

    response = client.post(
        f"/klassenarbeit/{exam_id}/simulation/{topic_id}",
        data={"_csrf": csrf_from(page.text)},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/quiz/")
