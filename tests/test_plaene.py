from datetime import date, datetime, timezone

import pytest

from app.woche import plaene


def test_time_formulas_accept_less_equal_more_and_limits():
    rows = [
        {"scheduled_date": "2026-09-01", "planned_minutes": 20, "status": "completed", "actual_minutes": 10, "focus_percent": 0},
        {"scheduled_date": "2026-09-02", "planned_minutes": 20, "status": "completed", "actual_minutes": 20, "focus_percent": 100},
        {"scheduled_date": "2026-09-03", "planned_minutes": 20, "status": "completed", "actual_minutes": 24, "focus_percent": 50},
        {"scheduled_date": "2026-09-04", "planned_minutes": 20, "status": "completed", "actual_minutes": 0, "focus_percent": 100},
        {"scheduled_date": "2026-09-05", "planned_minutes": 20, "status": "completed", "actual_minutes": 60, "focus_percent": 100},
    ]
    result = plaene.aggregate(rows)
    assert result == {"planned": 100, "actual": 114, "focused": 92, "focus": 81, "percent": 114}


def test_canonical_acceptance_calculation():
    values = [(24, 95), (18, 80), (23, 90), (20, 85)]
    rows = [{"scheduled_date": f"2026-09-{day:02d}", "planned_minutes": 20,
             "status": "completed", "actual_minutes": actual, "focus_percent": focus}
            for day, (actual, focus) in enumerate(values, 1)]
    rows += [{"scheduled_date": f"2026-09-{day:02d}", "planned_minutes": 20,
              "status": "planned", "actual_minutes": None, "focus_percent": None}
             for day in range(5, 13)]
    result = plaene.goal_statistics(rows, date(2026, 9, 4))
    assert result["due_actual"] == 85
    assert result["adherence"] == 106
    assert result["progress"] == 35
    assert result["focus"] == 88


def test_motivation_is_honest_about_progress():
    waiting = plaene.motivation({"planned": 100, "actual": 0, "percent": 0})
    assert waiting["title"] == "Heute kannst du anfangen!"
    assert "voraus" not in waiting["title"] + waiting["text"]

    behind = plaene.motivation({"planned": 100, "actual": 40, "percent": 40})
    assert behind["title"] == "Jeder Schritt zählt!"
    assert "40 %" in behind["text"]

    ahead = plaene.motivation({"planned": 100, "actual": 112, "percent": 112})
    assert ahead["title"] == "Du bist deinem Plan voraus!"
    assert "12 %" in ahead["text"]


def test_store_creates_completes_makes_up_and_keeps_history(app_env, monkeypatch):
    from app.woche import plaene_store as store
    monkeypatch.setattr(plaene, "today", lambda now=None: date(2026, 9, 10))
    goal_id = store.create_goal("Ich möchte besser in Englisch werden.", date(2026, 9, 1), date(2026, 9, 28), 20, [1, 3, 5])
    items = store.sessions(goal_id)
    assert len(items) == 12
    assert sum(row["planned_minutes"] for row in items) == 240
    store.mark_missed(date(2026, 9, 10))
    first = store.sessions(goal_id)[0]
    assert first["status"] == "missed"
    store.complete(first["id"], 24, 95, datetime(2026, 9, 10, 12, tzinfo=timezone.utc))
    assert store.sessions(goal_id)[0]["status"] == "made_up"
    assert len(app_env.db.q("SELECT * FROM plan_completion")) == 1
    store.complete(first["id"], 24, 95, datetime(2026, 9, 10, 12, tzinfo=timezone.utc))
    assert len(app_env.db.q("SELECT * FROM plan_completion")) == 1
    old_dates = [(row["scheduled_date"], row["planned_minutes"]) for row in store.sessions(goal_id) if row["scheduled_date"] < "2026-09-14"]
    store.update_future(goal_id, "Englisch sicher sprechen.", date(2026, 10, 4), 30, [2, 4], date(2026, 9, 14))
    after = store.sessions(goal_id)
    assert [(row["scheduled_date"], row["planned_minutes"]) for row in after if row["scheduled_date"] < "2026-09-14"] == old_dates
    assert all(row["planned_minutes"] == 30 for row in after if row["scheduled_date"] >= "2026-09-14")


def test_archive_keeps_history_and_removes_from_active(app_env):
    from app.woche import plaene_store as store
    goal_id = store.create_goal("Jeden Tag ein bisschen lesen.", date(2026, 9, 1), date(2026, 9, 7), 10, [1])
    store.set_status(goal_id, "completed")
    store.set_status(goal_id, "archived")
    assert not store.goals()
    assert store.goal(goal_id)["archived_at"]
    assert len(store.goals(("archived",))) == 1


def test_pause_cancels_future_and_resume_rebuilds_only_future(app_env, monkeypatch):
    from app.woche import plaene as current_rules, plaene_store as store
    monkeypatch.setattr(current_rules, "today", lambda now=None: date(2026, 9, 3))
    goal_id = store.create_goal("Regelmäßig lesen.", date(2026, 9, 1), date(2026, 9, 14), 15, [1, 3, 5])
    before = store.sessions(goal_id)
    store.set_status(goal_id, "paused")
    paused = store.sessions(goal_id)
    assert all(row["status"] == "cancelled" for row in paused if row["scheduled_date"] >= "2026-09-03")
    store.set_status(goal_id, "active")
    resumed = store.sessions(goal_id)
    assert [(r["scheduled_date"], r["planned_minutes"]) for r in resumed] == [(r["scheduled_date"], r["planned_minutes"]) for r in before]


@pytest.mark.parametrize("actual,focus", [(-1, 80), (61, 80), (20, -1), (20, 101)])
def test_completion_validation(app_env, actual, focus):
    from app.woche import plaene_store as store
    goal_id = store.create_goal("Mathematik üben.", date(2026, 9, 1), date(2026, 9, 1), 20, [2])
    with pytest.raises(ValueError):
        store.complete(store.sessions(goal_id)[0]["id"], actual, focus)


def test_plan_pages_render_and_completion_persists(client, app_env, fake_llm, fake_cli, monkeypatch):
    from app.woche import plaene as current_rules, plaene_store as store
    from .conftest import csrf_from
    from .test_app import einrichten, session_cookie_faelschen

    einrichten(client, fake_llm)
    monkeypatch.setattr(current_rules, "today", lambda now=None: date(2026, 9, 22))
    goal_id = store.create_goal("Ich möchte besser in Englisch werden.", date(2026, 9, 22), date(2026, 10, 19), 20, [1, 2, 3])
    item = store.sessions(goal_id)[0]

    child_cookie = session_cookie_faelschen(app_env, auth=True, role="child", csrf="test-token")
    client.cookies.clear()
    client.cookies.set("karo_session", child_cookie)
    dashboard = client.get("/")
    assert "Ziele planen" in dashboard.text
    assert 'class="plans-entry"' in dashboard.text
    assert '/static/karo-fox-wave.png' in dashboard.text
    for path, text in [
        ("/woche", "Deine Aufgaben heute"), ("/woche/woche", "Wochenfortschritt"),
        ("/woche/monat", "Monatsfortschritt"), ("/woche/ziele", "Alle Ziele"),
        (f"/woche/ziele/{goal_id}", "Bis zum Ziel"), ("/woche/schatzkiste", "Schatzkiste"),
        ("/woche/ziele/neu", "Was möchtest du schaffen?"),
    ]:
        response = client.get(path)
        assert response.status_code == 200, response.text[:1000]
        assert text in response.text

    goals_page = client.get("/woche/ziele")
    assert 'href="/" title="Zurück zu Karo"' in goals_page.text
    assert "Heute kannst du anfangen!" in goals_page.text
    assert f'href="/woche/ziele/{goal_id}"' in goals_page.text

    page = client.get(f"/woche?abschluss={item['id']}")
    assert "Wie lange hast du heute wirklich" in page.text
    assert page.text.count("data-focus-mark=") == 11
    response = client.post(f"/woche/sitzung/{item['id']}/abschluss", data={
        "_csrf": csrf_from(page.text), "actual_minutes": "27", "focus_percent": "80"}, follow_redirects=False)
    assert response.status_code == 303
    completed = store.session(item["id"])
    assert completed["actual_minutes"] == 27 and completed["focus_percent"] == 80


def test_goal_wizard_creates_time_only_plan(client, app_env, fake_llm, fake_cli, monkeypatch):
    from app.woche import plaene as current_rules, plaene_store as store
    from .conftest import csrf_from
    from .test_app import einrichten, session_cookie_faelschen

    einrichten(client, fake_llm)
    monkeypatch.setattr(current_rules, "today", lambda now=None: date(2026, 9, 22))
    cookie = session_cookie_faelschen(app_env, auth=True, role="child", csrf="test-token")
    client.cookies.clear(); client.cookies.set("karo_session", cookie)
    steps = [
        {"step": "1", "statement": "Ich möchte besser in Englisch werden."},
        {"step": "2", "start_date": "2026-09-24", "duration": "28"},
        {"step": "3", "weekdays": ["1", "3", "5"]},
        {"step": "4", "minutes": "20"},
        {"step": "5"},
    ]
    for index, data in enumerate(steps, 1):
        page = client.get(f"/woche/ziele/neu?step={index}")
        response = client.post("/woche/ziele/neu", data={"_csrf": csrf_from(page.text), **data}, follow_redirects=False)
        assert response.status_code == 303, response.text[:1000]
    created = store.goals()
    assert len(created) == 1 and created[0]["planned_minutes"] == 20
    assert created[0]["start_date"] == "2026-09-24"
    assert len(store.sessions(created[0]["id"])) == 12


def test_goal_wizard_rejects_start_date_before_today(client, app_env, fake_llm, fake_cli, monkeypatch):
    from app.woche import plaene as current_rules
    from .conftest import csrf_from
    from .test_app import einrichten, session_cookie_faelschen

    einrichten(client, fake_llm)
    monkeypatch.setattr(current_rules, "today", lambda now=None: date(2026, 9, 22))
    cookie = session_cookie_faelschen(app_env, auth=True, role="child", csrf="test-token")
    client.cookies.clear(); client.cookies.set("karo_session", cookie)
    page = client.get("/woche/ziele/neu?step=2")
    response = client.post("/woche/ziele/neu", data={
        "_csrf": csrf_from(page.text), "step": "2", "start_date": "2026-09-21", "duration": "28",
    })
    assert response.status_code == 400
    assert "darf nicht vor heute liegen" in response.text


def test_goal_detail_actions_work_end_to_end(client, app_env, fake_llm, fake_cli, monkeypatch):
    from app.woche import plaene as current_rules, plaene_store as store
    from .conftest import csrf_from
    from .test_app import einrichten, session_cookie_faelschen

    einrichten(client, fake_llm)
    monkeypatch.setattr(current_rules, "today", lambda now=None: date(2026, 9, 22))
    goal_id = store.create_goal("Englisch üben.", date(2026, 9, 22), date(2026, 10, 19), 20, [1, 3, 5])
    cookie = session_cookie_faelschen(app_env, auth=True, role="child", csrf="test-token")
    client.cookies.clear(); client.cookies.set("karo_session", cookie)

    def post(path, data):
        page = client.get(f"/woche/ziele/{goal_id}")
        return client.post(path, data={"_csrf": csrf_from(page.text), **data}, follow_redirects=False)

    assert post(f"/woche/ziele/{goal_id}/aktion", {"action": "pause"}).status_code == 303
    assert store.goal(goal_id)["status"] == "paused"
    assert "Fortsetzen" in client.get(f"/woche/ziele/{goal_id}").text

    post(f"/woche/ziele/{goal_id}/aktion", {"action": "resume"})
    assert store.goal(goal_id)["status"] == "active"
    post(f"/woche/ziele/{goal_id}/bearbeiten", {
        "statement": "Englisch sicher sprechen.", "end_date": "2026-10-26",
        "minutes": "25", "weekdays": ["2", "4"],
    })
    changed = store.goal(goal_id)
    assert changed["statement"] == "Englisch sicher sprechen."
    assert changed["planned_minutes"] == 25

    post(f"/woche/ziele/{goal_id}/aktion", {"action": "complete"})
    post(f"/woche/ziele/{goal_id}/aktion", {"action": "archive"})
    assert store.goal(goal_id)["status"] == "archived"
    archived_page = client.get(f"/woche/ziele/{goal_id}")
    assert "Bist du sicher?" in archived_page.text
    assert "Zurück zu meinen Plänen" in archived_page.text
    post(f"/woche/ziele/{goal_id}/aktion", {"action": "restore"})
    restored = store.goal(goal_id)
    assert restored["status"] == "active"
    assert restored["archived_at"] is None and restored["completed_at"] is None
    post(f"/woche/ziele/{goal_id}/aktion", {"action": "complete"})
    post(f"/woche/ziele/{goal_id}/aktion", {"action": "archive"})
    response = post(f"/woche/ziele/{goal_id}/aktion", {"action": "repeat"})
    assert response.status_code == 303
    assert len(store.goals(("active",))) == 1
