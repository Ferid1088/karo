"""Klassenarbeit + persönlicher Lernkalender + Heute-Einstieg."""
import json
from datetime import date

from .conftest import csrf_from
from .test_app import einrichten, kind_modus_aktivieren


def _exam_with_topic(app_env):
    from app import topics
    app_env.config.update(learner_grade=6)
    app_env.db.init()
    topic_id = topics.anlegen("Brüche addieren", subject="mathematik")
    topic = topics.get(topic_id)
    with app_env.db.tx() as c:
        exam_id = c.execute(
            "INSERT INTO exam(subject,exam_date,themen,created_at) VALUES(?,?,?,?)",
            ("mathematik", "2026-10-02", json.dumps(["Brüche addieren"]), app_env.db.now()),
        ).lastrowid
        c.execute(
            """INSERT INTO exam_plan(exam_id,state,tagesplan,created_at)
               VALUES(?,'bereit',?,?)""",
            (exam_id, json.dumps([
                {"tag": "28.09.2026", "inhalt": "Brüche addieren",
                 "minuten": 20, "topic_code": topic["code"]},
            ]), app_env.db.now()),
        )
    from app.services import learning_hub
    learning_hub.link_exam(exam_id, [topic['label']], 'Mathematik')
    owned = learning_hub.exam_topics(exam_id)
    assert owned[0]['id'] != topic_id
    return exam_id, owned[0]['id']


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
    assert "Klassenarbeit" in today.text
    assert "Brüche addieren" in today.text
    assert "23 Minuten" in today.text
    assert f'action="/klassenarbeit/{exam_id}/lernen/start"' in today.text
    assert 'action="/lernen/adaptiv/start"' not in today.text
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
    assert "Deine Generalprobe" in page.text
    assert "Brüche addieren" in page.text

    response = client.post(
        f"/klassenarbeit/{exam_id}/simulation/{topic_id}",
        data={"_csrf": csrf_from(page.text)},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == f"/klassenarbeit/{exam_id}/simulation/{topic_id}"
    assert client.get(response.headers['location']).status_code == 200
    assert not app_env.db.q('SELECT id FROM quiz')


def test_exam_plan_stays_on_topic_until_adaptive_mastery(app_env, monkeypatch):
    from app import topics
    from app.adaptiv import store as adaptiv_store
    from app.services import exam_calendar

    app_env.db.init()
    first_id = topics.anlegen("Brüche addieren", subject="mathematik")
    second_id = topics.anlegen("Brüche kürzen", subject="mathematik")
    first = topics.get(first_id)
    second = topics.get(second_id)

    with app_env.db.tx() as c:
        exam_id = c.execute(
            "INSERT INTO exam(subject,exam_date,themen,created_at) VALUES(?,?,?,?)",
            ("mathematik", "2026-10-05",
             json.dumps(["Brüche addieren", "Brüche kürzen"]), app_env.db.now()),
        ).lastrowid
        c.execute(
            """INSERT INTO exam_plan(exam_id,state,tagesplan,created_at)
               VALUES(?,'bereit',?,?)""",
            (exam_id, json.dumps([
                {"tag": "28.09.2026", "inhalt": "Brüche addieren",
                 "minuten": 20, "topic_code": first["code"]},
                {"tag": "29.09.2026", "inhalt": "Brüche kürzen",
                 "minuten": 20, "topic_code": second["code"]},
            ]), app_env.db.now()),
        )

    from app.services import learning_hub
    learning_hub.link_exam(exam_id, [first['label'], second['label']], 'Mathematik')
    owned = learning_hub.exam_topics(exam_id)
    assert not {first_id, second_id} & {t['id'] for t in owned}
    first_id, second_id = [t['id'] for t in owned]
    monkeypatch.setattr("app.db.today", lambda: "2026-09-27")
    exam_calendar.save_days(exam_id, {
        "2026-09-28": 20,
        "2026-09-29": 20,
        "2026-09-30": 20,
    })

    def reihenfolge(kalender):
        """Themen in der Reihenfolge, in der die Lerntage sie tragen."""
        gesehen = []
        for item in kalender:
            if not item["is_learning_day"] or item["is_simulation"]:
                continue
            for z in item["themen"]:
                if z["topic_id"] not in gesehen:
                    gesehen.append(z["topic_id"])
        return gesehen

    # Karo verteilt die Themen der Reihe nach auf die gewaehlten Lerntage —
    # die angekuendigte Reihenfolge traegt die Voraussetzungen.
    before = exam_calendar.calendar(exam_id)
    normal = [item for item in before if item["is_learning_day"] and not item["is_simulation"]]
    assert normal and normal[0]["topic_id"] == first_id
    assert reihenfolge(before) == [first_id, second_id]

    input_id = adaptiv_store.eingabe_anlegen(
        "manuell", fach="Mathematik", thema_text="Brüche addieren",
        topic_id=first_id)
    session_id = adaptiv_store.sitzung_anlegen(
        "INPUT_RECEIVED", eingabe_id=input_id)
    adaptiv_store.sitzung_aktualisieren(session_id, zustand="MASTERED")

    # Verstanden ist noch nicht sicher (Z7): der Kalender bleibt beim Thema,
    # bis die Wiederholung es bestaetigt hat.
    zwischen = exam_calendar.calendar(exam_id)
    normal = [item for item in zwischen if item["is_learning_day"] and not item["is_simulation"]]
    assert normal and normal[0]["topic_id"] == first_id

    adaptiv_store.init()
    from app.adaptiv import lektionen, wiederholung
    konzept_id = lektionen.fuer_thema("Brüche addieren", "mathematik")["konzept_id"]
    termin = wiederholung.planen(konzept_id, 2)
    wiederholung.abschliessen(termin["id"], bestanden_=True)

    # Ein sicheres Thema faellt aus der Planung heraus, das naechste rueckt vor.
    after = exam_calendar.calendar(exam_id)
    normal = [item for item in after if item["is_learning_day"] and not item["is_simulation"]]
    assert normal and normal[0]["topic_id"] == second_id
    assert reihenfolge(after) == [second_id]


def test_empty_calendar_days_are_valid_and_mean_no_study(app_env, monkeypatch):
    from app.services import exam_calendar

    exam_id, _ = _exam_with_topic(app_env)
    monkeypatch.setattr("app.db.today", lambda: "2026-09-27")

    exam_calendar.save_days(exam_id, {
        "2026-09-27": "",
        "2026-09-28": "23",
        "2026-09-29": "",
        "2026-09-30": "29",
        "2026-10-01": "",
    })

    saved = exam_calendar.get_days(exam_id)
    assert saved["2026-09-27"] == 0
    assert saved["2026-09-28"] == 23
    assert saved["2026-09-29"] == 0
    assert saved["2026-09-30"] == 29
    assert saved["2026-10-01"] == 0


def test_child_exam_page_hides_legacy_plan_and_shows_guided_flow(
        client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.services import exam_calendar

    einrichten(client, fake_llm)
    app_env.config.update(klassenarbeit_kind=True, adaptive_learning_enabled=True)
    exam_id, _ = _exam_with_topic(app_env)
    monkeypatch.setattr("app.db.today", lambda: "2026-09-28")
    exam_calendar.save_days(exam_id, {
        "2026-09-28": 20,
        "2026-09-29": 0,
        "2026-09-30": 25,
        "2026-10-01": 30,
    })

    kind_modus_aktivieren(client)
    page = client.get(f"/klassenarbeit/{exam_id}")
    assert page.status_code == 200
    assert "SO LERNST DU HIER" in page.text
    for step in ('Prüfen', 'Verstehen', 'Üben', 'Sicher werden'):
        assert f'<strong>{step}</strong>' in page.text
    assert f'action="/klassenarbeit/{exam_id}/lernen/start"' in page.text
    assert 'action="/lernen/adaptiv/start"' not in page.text
    assert "<th>Tag</th><th>Thema und Lernreihe</th>" not in page.text
