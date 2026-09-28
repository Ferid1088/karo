"""Heute als Tag des Kindes: Plan, Stand und kleine Erfolge."""
from datetime import date


def test_streak_counts_until_yesterday_when_today_is_still_open():
    from app.services.today import streak
    days = {"2026-09-25", "2026-09-26", "2026-09-27"}
    assert streak(days, date(2026, 9, 28)) == 3
    assert streak(days | {"2026-09-28"}, date(2026, 9, 28)) == 4
    assert streak(days, date(2026, 9, 29)) == 0


def test_relative_day_labels():
    from app.services.today import relative_day, date_label
    today = date(2026, 9, 28)
    assert relative_day("2026-09-28T08:00:00+00:00", today) == "heute"
    assert relative_day("2026-09-27", today) == "gestern"
    assert relative_day("2026-09-24", today) == "vor 4 Tagen"
    assert relative_day("2026-09-01", today) == "am 1. September"
    assert date_label(today) == "Montag, 28. September"


def test_empty_day_offers_a_choice_without_plan(client, fake_llm, fake_cli):
    from .test_app import einrichten
    einrichten(client, fake_llm)
    page = client.get("/").text
    assert "Heute ist nichts geplant" in page
    assert "Heute auf deinem Plan" not in page
    assert "Tage</b> in Folge" not in page


def test_streak_and_success_appear_on_today(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.services import today
    from app import topics
    from .test_app import einrichten
    einrichten(client, fake_llm)
    tid = topics.anlegen("Dezimalzahlen", subject="mathematik")
    with app_env.db.tx() as c:
        c.execute("UPDATE topic SET state='aktiv', learned_at=? WHERE id=?", (app_env.db.now(), tid))
    monkeypatch.setattr(today, "activity_days", lambda: {
        str(date.fromordinal(today.plaene.today().toordinal() - n)) for n in (1, 2, 3)})
    page = client.get("/").text
    assert "<b>3 Tage</b> in Folge gelernt" in page
    assert "heute geht’s weiter" in page
    assert "Heute sicher: <b>Dezimalzahlen</b>" in page


def test_success_line_moved_to_erfolge(client, fake_llm, fake_cli):
    from app import topics
    from .test_app import einrichten
    einrichten(client, fake_llm)
    topics.anlegen("Brüche addieren", subject="mathematik")
    assert "Themen sicher" not in client.get("/").text
    assert "Themen sicher" in client.get("/lernstand").text


def test_activity_days_use_the_family_timezone(app_env):
    from app.services import today
    from app.woche import plaene_store as store
    app_env.db.init()
    goal_id = store.create_goal("Lesen", date(2026, 9, 28), date(2026, 9, 28), 20, [1])
    session_id = store.sessions(goal_id)[0]["id"]
    # 22:30 UTC ist in Berlin schon der naechste Tag.
    from datetime import datetime, timezone
    store.complete(session_id, 20, 80, completed_at=datetime(2026, 9, 27, 22, 30, tzinfo=timezone.utc))
    assert today.activity_days() == {"2026-09-28"}


def test_old_success_and_missed_units_stay_quiet(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app import topics
    from app.woche import plaene, plaene_store as store
    from .test_app import einrichten
    einrichten(client, fake_llm)
    monkeypatch.setattr(plaene, "today", lambda now=None: date(2026, 9, 28))
    tid = topics.anlegen("Dezimalzahlen", subject="mathematik")
    with app_env.db.tx() as c:
        c.execute("UPDATE topic SET state='aktiv', learned_at='2026-09-01T10:00:00+00:00' WHERE id=?", (tid,))
    # Verpasst am Sonntag; heute (Montag) nichts geplant: Nachholen wird angeboten.
    missed = store.create_goal("Vokabeln", date(2026, 9, 27), date(2026, 9, 27), 10, [7])
    page = client.get("/").text
    assert "sicher: <b>Dezimalzahlen</b>" not in page
    assert "Noch offen: Vokabeln" in page
    # Steht heute etwas an, bleibt die alte Lücke still.
    store.create_goal("Lesen", date(2026, 9, 28), date(2026, 9, 28), 10, [1])
    assert "Noch offen: Vokabeln" not in client.get("/").text
    assert store.sessions(missed)[0]["status"] == "missed"


def test_exam_day_and_goal_share_one_plan(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.services import exam_calendar
    from app.woche import plaene, plaene_store as store
    from .test_app import einrichten
    from .test_exam_calendar import _exam_with_topic
    einrichten(client, fake_llm)
    app_env.config.update(klassenarbeit_kind=True, adaptive_learning_enabled=True)
    exam_id, topic_id = _exam_with_topic(app_env)
    monkeypatch.setattr("app.db.today", lambda: "2026-09-28")
    monkeypatch.setattr(plaene, "today", lambda now=None: date(2026, 9, 28))
    exam_calendar.save_days(exam_id, {"2026-09-28": 23, "2026-09-30": 29})
    store.create_goal("Lesen", date(2026, 9, 28), date(2026, 9, 28), 10, [1])
    page = client.get("/").text
    # Die Arbeit ist der naechste Schritt; das Ziel steht mit auf der Liste.
    assert f'action="/klassenarbeit/{exam_id}/lernen/start"' in page
    assert "Heute sind es 2 kleine Dinge, etwa 33 Minuten." in page
    assert "Heute auf deinem Plan" in page and ">0/2<" in page
    assert "Mathematik-Arbeit <b>in 4 Tagen</b>" in page
    monkeypatch.setattr(exam_calendar, "learned_on", lambda exam, day: True)
    page = client.get("/").text
    assert ">1/2<" in page and 'action="/woche/ziele/' in page
    # Ohne Freigabe fuer das Kind bleibt die Arbeit ganz aus "Heute" heraus.
    app_env.config.update(klassenarbeit_kind=False)
    page = client.get("/").text
    assert "Mathematik-Arbeit" not in page and "Heute auf deinem Plan" not in page


def test_rehearsal_counts_as_done_when_finished(app_env):
    from app.services import exam_calendar, exam_rehearsal
    from .test_exam_calendar import _exam_with_topic
    exam_id, topic_id = _exam_with_topic(app_env)
    assert not exam_calendar.rehearsal_done(exam_id)
    exam_rehearsal.init()
    with app_env.db.tx() as c:
        c.execute("INSERT INTO exam_rehearsal(exam_id,topic_id,questions,created_at) VALUES(?,?,'[]',?)",
                  (exam_id, topic_id, app_env.db.now()))
    assert not exam_calendar.rehearsal_done(exam_id)
    with app_env.db.tx() as c:
        c.execute("UPDATE exam_rehearsal SET finished_at=? WHERE exam_id=?", (app_env.db.now(), exam_id))
    assert exam_calendar.rehearsal_done(exam_id)


def test_child_can_pick_which_task_is_now(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.woche import plaene, plaene_store as store
    from .test_app import einrichten
    einrichten(client, fake_llm)
    monkeypatch.setattr(plaene, "today", lambda now=None: date(2026, 9, 28))
    mathe = store.create_goal("Mathe üben", date(2026, 9, 28), date(2026, 9, 28), 20, [1])
    bio = store.create_goal("Bio lesen", date(2026, 9, 28), date(2026, 9, 28), 15, [1])
    page = client.get("/").text
    # Beide offen: die nicht gewaehlte Zeile ist ein Link, der sie zu "Jetzt" macht.
    first = mathe if f'action="/woche/ziele/{mathe}/start"' in page else bio
    other = bio if first == mathe else mathe
    assert f'href="/?jetzt=ziel-{other}#jetzt"' in page
    assert f'href="/?jetzt=ziel-{first}#jetzt"' not in page
    picked = client.get(f"/?jetzt=ziel-{other}").text
    assert f'action="/woche/ziele/{other}/start"' in picked
    assert f'action="/woche/ziele/{first}/start"' not in picked
    assert f'href="/?jetzt=ziel-{first}#jetzt"' in picked
    # Eine unbekannte oder erledigte Wahl faellt auf den ersten offenen Eintrag zurueck.
    assert f'action="/woche/ziele/{first}/start"' in client.get("/?jetzt=ziel-999").text


def test_time_capsule_opening_today_shows_only_a_bee_link(client, fake_llm, fake_cli, app_env):
    from app.welten import store as welt, world_db
    from .test_app import einrichten, session_cookie_faelschen
    einrichten(client, fake_llm)
    client.cookies.clear()
    client.cookies.set("karo_session", session_cookie_faelschen(app_env, auth=True, role="child", csrf="t"))
    with world_db.tx() as c:
        heute = c.execute("INSERT INTO world_capsule(title,text,opens_on,created_at) VALUES(?,?,?,?)",
                          ("Brief an mich", "GEHEIMER INHALT", world_db.today(), world_db.now())).lastrowid
        c.execute("INSERT INTO world_capsule(title,text,opens_on,created_at) VALUES(?,?,?,?)",
                  ("Später", "", "2099-01-01", world_db.now()))
    # Ohne Freigabe von Meine Welt bleibt Heute still.
    assert "Zeitkapsel" not in client.get("/").text
    welt.approve("10-11", True, True)
    page = client.get("/").text
    assert f'href="/welten/zeitkapseln/{heute}"' in page
    assert "/static/welt-biene.svg" in page and "„Brief an mich“" in page
    assert "GEHEIMER INHALT" not in page and "Später" not in page
    # Heute oeffnet nichts: erst der Besuch in Meine Welt oeffnet die Kapsel.
    assert welt.capsule(heute)["opened_at"] is None
    client.get(f"/welten/zeitkapseln/{heute}")
    assert welt.capsule(heute)["opened_at"] is not None
    assert "Zeitkapsel" not in client.get("/").text
