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


def test_goal_calendar_builds_month_grid_and_achievement_states():
    rows = [
        {"scheduled_date": "2026-09-02", "planned_minutes": 20,
         "status": "completed", "actual_minutes": 20},
        {"scheduled_date": "2026-09-08", "planned_minutes": 20,
         "status": "completed", "actual_minutes": 10},
        {"scheduled_date": "2026-09-15", "planned_minutes": 20,
         "status": "completed", "actual_minutes": 5},
        {"scheduled_date": "2026-09-22", "planned_minutes": 20,
         "status": "planned", "actual_minutes": None},
    ]
    result = plaene.goal_calendar(rows, date(2026, 9, 1))
    states = {cell["date"]: cell["state"] for cell in result["cells"]}

    assert result["label"] == "September 2026"
    assert result["previous"] == "2026-08"
    assert result["following"] == "2026-10"
    assert len(result["cells"]) == 35
    assert states["2026-09-02"] == "reached"
    assert states["2026-09-08"] == "partial"
    assert states["2026-09-15"] == "not-reached"
    assert states["2026-09-22"] == "open"


def test_goal_calendar_defaults_to_month_inside_goal_range():
    assert plaene.selected_goal_month(
        date(2026, 9, 22), date(2026, 10, 19), date(2026, 8, 4)) == date(2026, 9, 1)
    assert plaene.selected_goal_month(
        date(2026, 9, 22), date(2026, 10, 19), date(2026, 11, 4)) == date(2026, 10, 1)
    assert plaene.selected_goal_month(
        date(2026, 9, 22), date(2026, 10, 19), date(2026, 9, 25), "2027-02") == date(2027, 2, 1)


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
    # Ein zweiter Lernabschnitt am selben Tag kommt dazu, er ersetzt den ersten nicht.
    store.complete(first["id"], 6, 50, datetime(2026, 9, 10, 17, tzinfo=timezone.utc))
    assert len(app_env.db.q("SELECT * FROM plan_completion")) == 2
    again = store.sessions(goal_id)[0]
    assert again["actual_minutes"] == 30
    assert again["focus_percent"] == 86
    assert again["entry_count"] == 2
    old_dates = [(row["scheduled_date"], row["planned_minutes"]) for row in store.sessions(goal_id) if row["scheduled_date"] < "2026-09-14"]
    store.update_future(goal_id, "Englisch sicher sprechen.", date(2026, 10, 4), 30, [2, 4], date(2026, 9, 14))
    after = store.sessions(goal_id)
    assert [(row["scheduled_date"], row["planned_minutes"]) for row in after if row["scheduled_date"] < "2026-09-14"] == old_dates
    assert all(row["planned_minutes"] == 30 for row in after if row["scheduled_date"] >= "2026-09-14")


def test_start_session_is_available_for_any_goal_state(app_env, monkeypatch):
    from app.woche import plaene as current_rules, plaene_store as store

    current = date(2026, 9, 22)
    monkeypatch.setattr(current_rules, "today", lambda now=None: current)
    goal_id = store.create_goal("Mathematik üben.", date(2026, 9, 23), date(2026, 9, 30), 20, [3])
    first = store.start_session(goal_id, current)
    assert store.session(first)["scheduled_date"] == str(current)
    assert store.start_session(goal_id, current) == first

    store.complete(first, 20, 80)
    store.set_status(goal_id, "completed")
    store.set_status(goal_id, "archived")
    reopened = store.start_session(goal_id, current)
    assert reopened == first
    assert store.goal(goal_id)["status"] == "active"
    assert store.session(reopened)["actual_minutes"] == 20


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
    today = client.get("/woche")
    assert 'class="quick-edit"' in today.text
    assert 'class="quick-new"' in today.text
    assert 'class="quick-week"' not in today.text
    assert 'class="today-layout"' in today.text
    assert 'class="today-side"' in today.text
    assert 'class="today-main"' in today.text
    assert today.text.index('class="today-side"') < today.text.index('class="today-main"')
    assert today.text.index('class="quick-new"') < today.text.index('class="quick-edit"')
    assert today.text.index('class="quick-edit"') < today.text.index('class="plans-panel"', today.text.index('class="today-main"'))
    for path, text in [
        ("/woche", "Deine Aufgaben heute"), ("/woche/woche", "Wochenfortschritt"),
        ("/woche/monat", "Monatsfortschritt"), ("/woche/ziele", "Alle Ziele"),
        (f"/woche/ziele/{goal_id}", "Bis zum Ziel"), ("/woche/schatzkiste", "Schatzkiste"),
        ("/woche/ziele/neu", "Was möchtest du schaffen?"),
    ]:
        response = client.get(path)
        assert response.status_code == 200, response.text[:1000]
        assert text in response.text

    for path, marker in [
        ("/woche", 'data-progress-set="gesamt"'),
        ("/woche/woche", 'data-progress-set="woche"'),
        ("/woche/monat", 'data-progress-set="monat"'),
        ("/woche/ziele", 'data-progress-set="gesamt"'),
        (f"/woche/ziele/{goal_id}", f'data-progress-set="ziel-{goal_id}"'),
    ]:
        progress_page = client.get(path)
        assert marker in progress_page.text
        assert all(label in progress_page.text
                   for label in ("Fortschritt", "Bis heute", "Konzentration"))

    week_page = client.get("/woche/woche")
    assert 'class="stats-row stats-head"' in week_page.text
    assert 'class="stats-row stats-data"' in week_page.text
    assert 'data-label="Fortschritt"' in week_page.text
    assert "Aktion" in week_page.text
    assert "Heute ansehen" not in week_page.text

    month_page = client.get("/woche/monat")
    assert 'class="plans-panel month-progress"' in month_page.text
    assert 'class="month-layout"' in month_page.text
    assert 'class="month-sidebar-column"' in month_page.text
    assert 'class="month-side"' in month_page.text
    assert 'class="month-period-row"' in month_page.text
    assert "month-motivation" in month_page.text
    assert month_page.text.index('class="month-side"') < month_page.text.index('class="month-main"')
    assert month_page.text.index("month-motivation") < month_page.text.index("month-progress")

    goals_page = client.get("/woche/ziele")
    assert 'href="/" title="Zurück zu Karo"' in goals_page.text
    assert 'data-plans-clock' in goals_page.text
    assert 'data-clock-date>22.09.2026<' in goals_page.text
    assert 'data-clock-time>--:-- Uhr<' in goals_page.text
    assert "Heute kannst du anfangen!" in goals_page.text
    assert f'href="/woche/ziele/{goal_id}"' in goals_page.text
    assert 'class="progress focus"' in goals_page.text
    assert 'class="goal-progress focus-stat"' in goals_page.text
    assert 'class="goal-progress progress-stat"' in goals_page.text
    assert 'class="goal-progress adherence-stat"' in goals_page.text
    detail = client.get(f"/woche/ziele/{goal_id}")
    assert 'aria-label="Lernkalender September 2026"' in detail.text
    assert 'data-calendar-state="open"' in detail.text
    assert f'/woche/ziele/{goal_id}?month=2026-10#calendar' in detail.text
    october = client.get(f"/woche/ziele/{goal_id}?month=2026-10")
    assert 'aria-label="Lernkalender Oktober 2026"' in october.text
    assert client.get(f"/woche/ziele/{goal_id}?month=ungueltig").status_code == 400
    for path in ("/woche", "/woche/woche", "/woche/monat", "/woche/ziele", f"/woche/ziele/{goal_id}"):
        assert f'action="/woche/ziele/{goal_id}/start"' in client.get(path).text

    start_source = client.get("/woche/ziele")
    started = client.post(f"/woche/ziele/{goal_id}/start", data={
        "_csrf": csrf_from(start_source.text),
    }, follow_redirects=False)
    assert started.status_code == 303
    assert started.headers["location"] == f"/woche?abschluss={item['id']}"

    page = client.get(started.headers["location"])
    assert "Wie lange hast du gerade daran gearbeitet" in page.text
    assert page.text.count("data-focus-mark=") == 11
    response = client.post(f"/woche/sitzung/{item['id']}/abschluss", data={
        "_csrf": csrf_from(page.text), "actual_minutes": "27", "focus_percent": "80"}, follow_redirects=False)
    assert response.status_code == 303
    completed = store.session(item["id"])
    assert completed["actual_minutes"] == 27 and completed["focus_percent"] == 80


def test_parent_completion_stays_on_karo_page_with_role_notice(client, app_env, fake_llm, fake_cli, monkeypatch):
    from app.woche import plaene as current_rules, plaene_store as store
    from .conftest import csrf_from
    from .test_app import einrichten, session_cookie_faelschen

    einrichten(client, fake_llm)
    monkeypatch.setattr(current_rules, "today", lambda now=None: date(2026, 9, 22))
    goal_id = store.create_goal("Mathematik üben.", date(2026, 9, 22), date(2026, 9, 22), 20, [2])
    item = store.sessions(goal_id)[0]
    parent_cookie = session_cookie_faelschen(app_env, auth=True, role="parent", csrf="test-token")
    client.cookies.clear(); client.cookies.set("karo_session", parent_cookie)

    page = client.get(f"/woche?abschluss={item['id']}")
    assert "data-parent-feedback" in page.text
    response = client.post(f"/woche/sitzung/{item['id']}/abschluss", data={
        "_csrf": csrf_from(page.text), "actual_minutes": "20", "focus_percent": "80",
    }, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"/woche?abschluss={item['id']}&hinweis=kind"
    assert store.session(item["id"])["actual_minutes"] is None

    notice = client.get(response.headers["location"])
    assert notice.status_code == 200
    assert "Fast geschafft!" in notice.text
    assert "Kind-Modus starten" in notice.text
    assert "Diese Rückmeldung gehört dem Kind" not in notice.text


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
    treasure = client.get("/woche/schatzkiste")
    assert f'data-progress-set="ziel-{goal_id}"' in treasure.text
    assert all(label in treasure.text
               for label in ("Fortschritt", "Bis heute", "Konzentration"))
    post(f"/woche/ziele/{goal_id}/aktion", {"action": "restore"})
    restored = store.goal(goal_id)
    assert restored["status"] == "active"
    assert restored["archived_at"] is None and restored["completed_at"] is None
    post(f"/woche/ziele/{goal_id}/aktion", {"action": "complete"})
    post(f"/woche/ziele/{goal_id}/aktion", {"action": "archive"})
    response = post(f"/woche/ziele/{goal_id}/aktion", {"action": "repeat"})
    assert response.status_code == 303
    assert len(store.goals(("active",))) == 1


def test_goal_week_grades_each_planned_day_by_what_was_achieved():
    rows = [
        {"scheduled_date": "2026-09-21", "planned_minutes": 20, "status": "completed", "actual_minutes": 20},
        {"scheduled_date": "2026-09-22", "planned_minutes": 20, "status": "completed", "actual_minutes": 25},
        {"scheduled_date": "2026-09-23", "planned_minutes": 20, "status": "made_up", "actual_minutes": 8},
        {"scheduled_date": "2026-09-24", "planned_minutes": 20, "status": "completed", "actual_minutes": 0},
        {"scheduled_date": "2026-09-25", "planned_minutes": 20, "status": "missed", "actual_minutes": None},
    ]
    days = plaene.goal_week(rows, date(2026, 9, 25))
    assert [day["state"] for day in days] == [
        "done", "done", "partial", "missed", "missed", "off", "off"]
    assert [day["percent"] for day in days][:5] == [100, 100, 40, 0, 0]
    assert days[2]["label"] == "Teilweise geschafft (40 %)"


def test_goal_week_keeps_an_untouched_planned_day_green_and_marks_today():
    rows = [
        {"scheduled_date": "2026-09-24", "planned_minutes": 20, "status": "planned", "actual_minutes": None},
        {"scheduled_date": "2026-09-25", "planned_minutes": 20, "status": "planned", "actual_minutes": None},
    ]
    days = plaene.goal_week(rows, date(2026, 9, 24))
    assert days[3]["state"] == "planned" and days[3]["today"] is True
    assert days[4]["state"] == "planned" and days[4]["today"] is False
    assert days[3]["percent"] == 0
    assert days[5]["state"] == "off" and days[5]["percent"] == 0


def test_goal_week_marks_each_weekday_of_the_current_week():
    rows = [
        {"scheduled_date": "2026-09-21", "planned_minutes": 20, "status": "completed", "actual_minutes": 20},
        {"scheduled_date": "2026-09-22", "planned_minutes": 20, "status": "made_up", "actual_minutes": 15},
        {"scheduled_date": "2026-09-23", "planned_minutes": 20, "status": "missed", "actual_minutes": None},
        {"scheduled_date": "2026-09-24", "planned_minutes": 20, "status": "planned", "actual_minutes": None},
        {"scheduled_date": "2026-09-25", "planned_minutes": 20, "status": "cancelled", "actual_minutes": None},
    ]
    days = plaene.goal_week(rows, date(2026, 9, 24))
    assert [day["weekday"] for day in days] == [1, 2, 3, 4, 5, 6, 7]
    assert [day["state"] for day in days] == [
        "done", "partial", "missed", "planned", "off", "off", "off"]
    assert days[0]["date"] == date(2026, 9, 21)
    assert days[3]["label"] == "Heute dran"


def test_date_and_period_labels_use_german_notation():
    assert plaene.date_label("2026-09-22") == "22.09.2026"
    assert plaene.period_label("2026-09-22", "2026-10-30") == "22.09.2026 – 30.10.2026"
    assert plaene.date_label("") == ""
    assert plaene.period_label("2026-09-22", "") == "22.09.2026"


def test_completed_goal_offers_treasure_chest_and_reactivation(client, app_env, fake_llm, fake_cli, monkeypatch):
    from app.woche import plaene as current_rules, plaene_store as store
    from .test_app import einrichten, session_cookie_faelschen

    einrichten(client, fake_llm)
    monkeypatch.setattr(current_rules, "today", lambda now=None: date(2026, 9, 22))
    goal_id = store.create_goal("bio", date(2026, 9, 22), date(2026, 10, 19), 20, [1, 2, 3])
    client.cookies.clear()
    client.cookies.set("karo_session", session_cookie_faelschen(app_env, auth=True, role="child", csrf="test-token"))

    detail = client.get(f"/woche/ziele/{goal_id}")
    assert 'value="restore" disabled' in detail.text
    assert 'value="complete" disabled' not in detail.text
    assert "✓ Abgeschlossen" not in client.get("/woche/ziele").text

    store.set_status(goal_id, "completed")
    detail = client.get(f"/woche/ziele/{goal_id}")
    assert 'value="restore" disabled' not in detail.text
    assert 'value="complete" disabled' in detail.text

    goals_page = client.get("/woche/ziele")
    assert "✓ Abgeschlossen" in goals_page.text
    assert 'value="archive"' in goals_page.text
    assert "Ziel wieder aktivieren" in goals_page.text

    client.post(f"/woche/ziele/{goal_id}/aktion",
                data={"action": "restore", "_csrf": "test-token"},
                headers={"x-csrf-token": "test-token"})
    assert store.goal(goal_id)["status"] == "active"


def test_two_sessions_on_the_same_day_are_both_kept(client, app_env, fake_llm, fake_cli, monkeypatch):
    from app.woche import plaene as current_rules, plaene_store as store
    from .test_app import einrichten

    einrichten(client, fake_llm)
    monkeypatch.setattr(current_rules, "today", lambda now=None: date(2026, 9, 22))
    goal_id = store.create_goal("bio", date(2026, 9, 22), date(2026, 10, 19), 20, [1, 2, 3])

    first = store.start_session(goal_id, date(2026, 9, 22))
    store.complete(first, 20, 80)
    second = store.start_session(goal_id, date(2026, 9, 22))
    store.complete(second, 15, 60)

    entries = [row for row in store.completions(goal_id) if row["scheduled_date"] == "2026-09-22"]
    assert [row["actual_minutes"] for row in entries] == [20, 15]

    day = [row for row in store.sessions(goal_id) if row["scheduled_date"] == "2026-09-22"]
    assert len(day) == 1
    assert day[0]["actual_minutes"] == 35
    assert day[0]["focus_percent"] == 71


def test_all_pages_show_the_same_hand_checked_numbers(client, app_env, fake_llm, fake_cli, monkeypatch):
    """Ein Ziel, von Hand nachgerechnet, auf jeder Seite kontrolliert.

    Mo 20 Min bei 80 %, Di 12+9+6 Min bei 70/90/50 %, Mi 0 Min, Do (heute) offen,
    Fr geplant. Geplant gesamt 5 x 20 = 100 Min, davon bis Do 80 Min faellig.
    Gemacht 20+27 = 47 Min. Fokuszeit 20*0,80 + 27*0,72 = 35,44 -> 35 Min.
    """
    from datetime import datetime, timezone
    from app.woche import plaene as current_rules, plaene_store as store
    from .test_app import einrichten, session_cookie_faelschen

    einrichten(client, fake_llm)
    monkeypatch.setattr(current_rules, "today", lambda now=None: date(2026, 9, 24))
    goal_id = store.create_goal("bio", date(2026, 9, 21), date(2026, 9, 25), 20, [1, 2, 3, 4, 5])
    rows = store.sessions(goal_id)
    assert [row["scheduled_date"] for row in rows] == [
        "2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24", "2026-09-25"]
    store.complete(rows[0]["id"], 20, 80, datetime(2026, 9, 21, 9, tzinfo=timezone.utc))
    store.complete(rows[1]["id"], 12, 70, datetime(2026, 9, 22, 8, tzinfo=timezone.utc))
    store.complete(rows[1]["id"], 9, 90, datetime(2026, 9, 22, 16, tzinfo=timezone.utc))
    store.complete(rows[1]["id"], 6, 50, datetime(2026, 9, 22, 19, tzinfo=timezone.utc))
    store.complete(rows[2]["id"], 0, 0, datetime(2026, 9, 23, 17, tzinfo=timezone.utc))

    # Einheiten: Tagessumme und zeitgewichtete Konzentration.
    day = {row["scheduled_date"]: row for row in store.sessions(goal_id)}
    assert (day["2026-09-21"]["actual_minutes"], day["2026-09-21"]["focus_percent"]) == (20, 80)
    assert (day["2026-09-22"]["actual_minutes"], day["2026-09-22"]["focus_percent"]) == (27, 72)
    assert (day["2026-09-23"]["actual_minutes"], day["2026-09-23"]["focus_percent"]) == (0, 0)
    assert day["2026-09-24"]["actual_minutes"] is None

    stats = current_rules.goal_statistics(store.sessions(goal_id), date(2026, 9, 24))
    assert stats["planned"] == 100 and stats["actual"] == 47
    assert stats["due_planned"] == 80 and stats["due_actual"] == 47
    assert stats["progress"] == 47          # 47 von 100
    assert stats["adherence"] == 59         # 47 von 80
    assert stats["focused"] == 35 and stats["focus"] == 75

    week = current_rules.goal_week(store.sessions(goal_id), date(2026, 9, 24))
    assert [row["state"] for row in week] == [
        "done", "done", "missed", "planned", "planned", "off", "off"]
    assert [row["percent"] for row in week][:3] == [100, 100, 0]

    client.cookies.clear()
    client.cookies.set("karo_session", session_cookie_faelschen(app_env, auth=True, role="child", csrf="test-token"))
    detail = client.get(f"/woche/ziele/{goal_id}").text
    assert "47 von 80 Min bis heute" in detail and "59 %" in detail
    assert "47 von 100 Min insgesamt" in detail and "47 %" in detail
    assert "35 von 47 Min fokussiert" in detail and "75 %" in detail
    assert "27 Min <small>in 3 Abschnitten</small>" in detail
    assert "135 %" in detail                # 27 von 20 Min an diesem Tag

    for path in ("/woche/ziele", "/woche/woche", "/woche/monat"):
        page = client.get(path).text
        assert "47" in page and "59 %" in page, path


def test_every_page_counts_the_same_goals(client, app_env, fake_llm, fake_cli, monkeypatch):
    """Ein laufendes, ein pausiertes und ein abgeschlossenes Ziel: „Bis heute" muss
    auf Heute, Woche, Monat und Ziele dieselbe Zahl sein."""
    import re
    from datetime import datetime, timezone
    from app.woche import plaene as current_rules, plaene_store as store
    from .test_app import einrichten, session_cookie_faelschen

    einrichten(client, fake_llm)
    monkeypatch.setattr(current_rules, "today", lambda now=None: date(2026, 9, 24))
    for name, status in (("bio", "active"), ("kunst", "paused"), ("sport", "completed")):
        goal_id = store.create_goal(name, date(2026, 9, 21), date(2026, 9, 25), 20, [1, 2, 3, 4, 5])
        store.complete(store.sessions(goal_id)[0]["id"], 10, 80,
                       datetime(2026, 9, 21, 9, tzinfo=timezone.utc))
        if status != "active":
            store.set_status(goal_id, status)

    client.cookies.clear()
    client.cookies.set("karo_session", session_cookie_faelschen(app_env, auth=True, role="child", csrf="test-token"))
    seen = {}
    for path in ("/woche", "/woche/ziele"):
        page = client.get(path).text
        block = page[page.index("Bis heute"):]
        seen[path] = re.search(r"(\d+) %", block).group(1)
    assert len(set(seen.values())) == 1, seen
    # Pausieren und Abschliessen stornieren die Einheiten ab heute: sie zaehlen
    # nicht mehr als geplant. Faellig sind 4x20 + 3x20 + 3x20 = 200 Min,
    # geschafft 3x10 = 30 Min -> 15 %.
    assert seen["/woche"] == "15"
