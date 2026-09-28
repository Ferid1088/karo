"""Integration contract: personal learning and each exam are separate journeys."""
import json
import re
from datetime import date

import pytest

from .conftest import csrf_from, run_jobs, make_jpeg
from .test_app import einrichten, kind_modus_aktivieren
from .test_lektion_erzeugung import _lektion


def setup_journeys(client, fake_llm, app_env, monkeypatch):
    from app.services import learning_hub, exam
    einrichten(client, fake_llm)
    monkeypatch.setattr("app.db.today", lambda: "2026-09-27")
    app_env.config.update(adaptive_learning_enabled=True, klassenarbeit_kind=True,
                          llm_error_creation_enabled=True, learner_grade=6)
    personal = learning_hub.create_topic("Brüche addieren", "Mathematik", 6)
    exams = [exam.create_exam("2026-10-15", manual_topics="Brüche addieren",
                              subject="Mathematik").exam_id for _ in range(2)]
    exam_topics = [learning_hub.exam_topics(e)[0]["id"] for e in exams]
    kind_modus_aktivieren(client)
    token = csrf_from(client.get("/lernen").text)
    return personal, exams, exam_topics, token


def start(client, token, topic_id, exam_id=None):
    base = f"/klassenarbeit/{exam_id}/lernen" if exam_id else "/lernen/adaptiv"
    response = client.post(base + "/start", data={"_csrf": token, "topic_id": topic_id})
    assert response.status_code == 200, response.text
    match = re.search(r'action="([^"]+/anker\?sitzung=(\d+))"', response.text)
    assert match, response.text
    return base, int(match[2]), response


def post(client, token, base, session_id, action, answer=""):
    return client.post(f"{base}/{action}?sitzung={session_id}",
                       data={"_csrf": token, "antwort": answer})


def test_same_name_never_shares_local_topics(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.services import learning_hub
    personal, exams, tids, token = setup_journeys(client, fake_llm, app_env, monkeypatch)
    assert len({personal, *tids}) == 3
    assert [t["id"] for t in learning_hub.personal_topics()] == [personal]
    learning_hub.link_exam(exams[0], ["Brüche addieren"], "Mathematik")
    assert len(learning_hub.exam_topics(exams[0])) == 1
    assert client.get(f"/lernen/thema/{tids[0]}").status_code == 404
    for path, tid in [
        ("/lernen/adaptiv/start", tids[0]),
        (f"/klassenarbeit/{exams[0]}/lernen/start", personal),
        (f"/klassenarbeit/{exams[0]}/lernen/start", tids[1]),
    ]:
        assert client.post(path, data={"_csrf": token, "topic_id": tid}).status_code == 404
    assert not app_env.db.q("SELECT id FROM lern_sitzung")


def test_parallel_tabs_and_progress_stay_separate(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.adaptiv import store
    personal, exams, tids, token = setup_journeys(client, fake_llm, app_env, monkeypatch)
    pbase, psid, _ = start(client, token, personal)
    ebase, esid, exam_page = start(client, token, tids[0], exams[0])
    assert "/lernen/adaptiv" not in exam_page.text
    for base, sid in [(pbase, psid), (ebase, esid)]:
        post(client, token, base, sid, "anker", "die Hälfte")
    assert post(client, token, pbase, esid, "diagnose", "5/6").status_code == 404
    post(client, token, pbase, psid, "diagnose", "5/6")
    # The other tab is still at its first diagnostic task.
    assert not store.sitzung(esid)["daten"].get("zweite_diagnose")
    first = store.erstkontakt(store.sitzung(psid)["konzept_id"])["erste_aufgabe"]
    post(client, token, pbase, psid, "diagnose", first["bestaetigung"]["loesung"])
    assert store.topic_mastery(personal) == "MASTERED"
    assert store.topic_mastery(tids[0]) == "DIAGNOSING"
    post(client, token, ebase, esid, "diagnose", first["loesung"])
    assert store.topic_mastery(tids[0]) != "MASTERED"
    assert store.topic_mastery(tids[1]) is None
    assert client.get(f"{ebase}?sitzung={esid}").status_code == 200


def test_exam_teaches_known_error_through_mastery_without_model(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.adaptiv import store, inhalt_store
    personal, exams, tids, token = setup_journeys(client, fake_llm, app_env, monkeypatch)
    fake_llm.calls.clear()
    base, sid, _ = start(client, token, tids[0], exams[0])
    post(client, token, base, sid, "anker", "die Hälfte")
    post(client, token, base, sid, "diagnose", "2/5")
    session = store.sitzung(sid)
    assert session["phase"] == "HOOK"
    task = inhalt_store.aufgabe(session["fehlertyp_id"], "vorhersage")
    post(client, token, base, sid, "vorhersage", task["loesung"])
    for expected in ["RULE", "WORKED_EXAMPLE", "GUIDED_TASK"]:
        post(client, token, base, sid, "weiter")
        assert store.sitzung(sid)["phase"] == expected
    for role in ["gefuehrt", "selbststaendig"]:
        task = inhalt_store.aufgabe(session["fehlertyp_id"], role)
        post(client, token, base, sid, "aufgabe", task["loesung"])
    assert store.topic_mastery(tids[0]) != "MASTERED"
    task = inhalt_store.aufgabe(session["fehlertyp_id"], "transfer")
    page = post(client, token, base, sid, "transfer", task["loesung"])
    assert store.topic_mastery(tids[0]) == "MASTERED"
    assert store.topic_mastery(personal) is None
    assert store.topic_mastery(tids[1]) is None
    assert "/lernen/adaptiv" not in page.text
    assert fake_llm.calls == []
    # A stale form cannot create extra learning evidence.
    count = len(store.ereignisse(sid))
    post(client, token, base, sid, "aufgabe", "3/4")
    assert len(store.ereignisse(sid)) == count


@pytest.mark.parametrize("exam_scope", [False, True])
def test_generation_wait_resume_and_database_reuse(client, fake_llm, fake_cli, app_env, monkeypatch, exam_scope):
    from app.services import learning_hub
    from app.adaptiv import store
    _, exams, _, token = setup_journeys(client, fake_llm, app_env, monkeypatch)
    fake_llm.responses["lektion"] = _lektion()
    if exam_scope:
        learning_hub.link_exam(exams[0], ["Würfel: Volumen"], "Mathematik")
        tid = learning_hub.exam_topics(exams[0])[-1]["id"]
        base = f"/klassenarbeit/{exams[0]}/lernen"
    else:
        tid = learning_hub.create_topic("Würfel: Volumen", "Mathematik", 7)
        base = "/lernen/adaptiv"
    fake_llm.calls.clear()
    page = client.post(base + "/start", data={"_csrf": token, "topic_id": tid})
    assert "bereitet" in page.text
    assert not app_env.db.q("SELECT id FROM lern_sitzung")
    run_jobs(app_env, fake_llm)
    status = client.get(base + f"/status?topic_id={tid}").json()
    assert status["fertig"]
    page = client.get(base + f"/wartet?topic_id={tid}")
    assert "sitzung=" in page.text
    session = app_env.db.q1("SELECT id FROM lern_sitzung ORDER BY id DESC LIMIT 1")
    entry = store.eingabe(store.sitzung(session["id"])["eingabe_id"])
    assert entry["topic_id"] == tid
    assert len(fake_llm.calls) == 2  # Author and independent class review.
    client.post(base + "/start", data={"_csrf": token, "topic_id": tid})
    assert len(fake_llm.calls) == 2  # Reuse makes no additional model call.
    # Generated lessons without an explicit confirmation use another checked task.
    post(client, token, base, session["id"], "anker", "Würfel")
    post(client, token, base, session["id"], "diagnose", "8")
    assert store.sitzung(session["id"])["daten"].get("zweite_diagnose")


def test_full_calendar_preserves_omitted_days_and_exam_ownership(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.services import exam_calendar
    _, exams, _, token = setup_journeys(client, fake_llm, app_env, monkeypatch)
    first, second = exams
    exam_calendar.save_days(first, {"2026-09-28": 20, "2026-10-13": 35})
    exam_calendar.save_days(second, {"2026-10-13": 15})
    page = client.get(f"/klassenarbeit/{first}").text
    assert 'name="minutes_2026-10-14"' in page
    response = client.post(f"/klassenarbeit/{first}/kalender",
                          data={"_csrf": token, "minutes_2026-09-28": 0})
    assert response.status_code == 200
    assert exam_calendar.get_days(first)["2026-10-13"] == 35
    assert exam_calendar.get_days(second)["2026-10-13"] == 15
    assert exam_calendar.get_days(first)["2026-09-28"] == 0


def test_create_exam_guides_to_own_plan_and_retains_invalid_form(client, fake_llm, fake_cli, app_env, monkeypatch):
    _, _, _, token = setup_journeys(client, fake_llm, app_env, monkeypatch)
    response = client.post("/klassenarbeit", data={"_csrf": token, "exam_date": "2026-11-03",
                           "themen": "Brüche kürzen", "fach": "Mathematik"}, follow_redirects=False)
    assert re.fullmatch(r"/klassenarbeit/\d+#exam-calendar-title", response.headers["location"])
    page = client.post("/klassenarbeit", data={"_csrf": token, "exam_date": "2020-01-01",
                       "themen": "Behaltenes Thema", "fach": "mathematik"})
    assert "Behaltenes Thema" in page.text and 'value="mathematik" selected' in page.text
    # Ein anderes Fach als die drei wird nicht angenommen; die Eingaben bleiben.
    page = client.post("/klassenarbeit", data={"_csrf": token, "exam_date": "2026-11-03",
                       "themen": "Behaltenes Thema", "fach": "Biologie"})
    assert "Behaltenes Thema" in page.text and "Bitte wähle das Fach" in page.text


def test_rehearsal_is_gated_scoped_and_idempotent(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.services import exam_calendar, exam_rehearsal
    from app.adaptiv import store
    personal, exams, tids, token = setup_journeys(client, fake_llm, app_env, monkeypatch)
    eid, tid = exams[0], tids[0]
    base = f"/klassenarbeit/{eid}/simulation"
    exam_calendar.save_days(eid, {"2026-09-28": 20, "2026-10-14": 30})
    assert client.get(base).status_code == 403
    assert client.post(f"{base}/{tid}", data={"_csrf": token}).status_code == 403
    monkeypatch.setattr("app.db.today", lambda: "2026-10-14")
    assert client.post(f"{base}/{personal}", data={"_csrf": token}).status_code == 404
    response = client.post(f"{base}/{tid}", data={"_csrf": token})
    assert response.status_code == 200 and "Generalprobe abgeben" in response.text
    assert "/quiz/" not in response.text and "/lernen/adaptiv" not in response.text
    attempt = exam_rehearsal.get(eid, tid)
    client.post(f"{base}/{tid}", data={"_csrf": token})
    assert exam_rehearsal.get(eid, tid)["id"] == attempt["id"]
    values = {f"answer_{i}": q["loesung"] for i, q in enumerate(attempt["questions"])}
    result = client.post(f"{base}/{tid}/antworten", data={"_csrf": token, **values})
    assert result.status_code == 200 and "richtig" in result.text
    assert all(exam_rehearsal.get(eid, tid)["result"])
    assert store.topic_mastery(personal) is None
    assert store.topic_mastery(tids[1]) is None


def test_deleted_exam_is_not_scheduled_or_accessible(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.services import exam_calendar, learning_hub
    _, exams, tids, token = setup_journeys(client, fake_llm, app_env, monkeypatch)
    exam_calendar.save_days(exams[0], {"2026-09-27": 20})
    learning_hub.arbeit_loeschen(exams[0])
    assert exam_calendar.today_task() is None
    month = exam_calendar.monat("2026-09", date(2026, 9, 27))
    assert not any(a["id"] == exams[0] for a in month["arbeiten"])
    assert client.get(f"/klassenarbeit/{exams[0]}").status_code == 404
    assert client.post(f"/klassenarbeit/{exams[0]}/lernen/start",
                       data={"_csrf": token, "topic_id": tids[0]}).status_code == 404


def test_archive_and_legacy_paths_cannot_take_exam_topics(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.services import learning_hub
    _, exams, tids, token = setup_journeys(client, fake_llm, app_env, monkeypatch)
    tid = tids[0]
    for path in (f'/lernen/{tid}/loeschen', f'/lernstand/thema/{tid}/zurueck',
                 f'/lernstand/thema/{tid}/entfernen', f'/lernzyklus/{tid}/gelernt'):
        assert client.post(path, data={'_csrf': token, 'gelernt': 'ja'}).status_code == 404
    assert client.get(f'/lernzyklus/{tid}').status_code == 404
    assert learning_hub.topic_in_scope(tid, exams[0]) is not None
    response = client.post(f'/klassenarbeit/{exams[0]}/lernen',
                           data={'_csrf': token, 'topic_id': tid})
    assert response.status_code == 200 and 'sitzung=' in response.text


def test_early_rehearsal_is_visible_even_on_unplanned_day(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.services import exam_calendar
    _, exams, _, _ = setup_journeys(client, fake_llm, app_env, monkeypatch)
    exam_calendar.save_days(exams[0], {'2026-10-14': 25})
    exam_calendar.set_simulation_early(exams[0], True)
    month = exam_calendar.monat('2026-10')
    day = next(d for w in month['wochen'] for d in w if d['date'] == '2026-10-13')
    event = next(e for e in day['eintraege'] if e['exam_id'] == exams[0])
    assert event['art'] == 'probe' and event['minutes'] == 0
    assert month['lernminuten'] == 25


def test_scan_ownership_cannot_cross_learning_areas(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.services.exam import create_exam, ExamError
    _, _, _, token = setup_journeys(client, fake_llm, app_env, monkeypatch)
    with app_env.db.tx() as c:
        doc = c.execute('''INSERT INTO document
            (sha256,source_name,stored_path,mime,created_at) VALUES(?,?,?,?,?)''',
            ('scope-test', 'test.pdf', '/tmp/test.pdf', 'application/pdf', app_env.db.now())).lastrowid
        scan = c.execute("INSERT INTO exam_scan (document_id,state,themen,created_at) VALUES (?,'gelesen',?,?)",
                         (doc, json.dumps(['Brüche addieren']), app_env.db.now())).lastrowid
        c.execute('INSERT INTO learning_upload VALUES(?,?,?)', (scan, 'Mathematik', 6))
    assert client.get(f'/klassenarbeit/themenblatt/status?scan_id={scan}').status_code == 404
    assert client.get(f'/lernen/material/status?scan_id={scan}').status_code == 200
    with pytest.raises(ExamError):
        create_exam('2026-10-15', str(scan))
    response = client.post('/lernen/material/uebernehmen',
                           data={'_csrf': token, 'scan_id': scan, 'themen': 'Brüche kürzen'})
    assert response.status_code == 200 and 'Brüche kürzen' in response.text
    assert app_env.db.q1('SELECT state FROM exam_scan WHERE id=?', scan)['state'] == 'uebernommen'


def test_migration_preserves_ambiguous_history_and_is_idempotent(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.services import learning_hub
    from app.adaptiv import store
    personal, exams, tids, token = setup_journeys(client, fake_llm, app_env, monkeypatch)
    _, sid, _ = start(client, token, tids[0], exams[0])
    with app_env.db.tx() as c:
        c.execute('DROP INDEX exam_topic_owner')
        c.execute('UPDATE exam_topic SET topic_id=? WHERE exam_id=?', (tids[0], exams[1]))
    learning_hub.migrate_exams()
    replacements = [learning_hub.exam_topics(e)[0]['id'] for e in exams]
    assert len(set(replacements + [tids[0], personal])) == 4
    assert store.eingabe(store.sitzung(sid)['eingabe_id'])['topic_id'] == tids[0]
    assert len(app_env.db.q('SELECT * FROM exam_topic_legacy')) == 2
    learning_hub.migrate_exams()
    assert replacements == [learning_hub.exam_topics(e)[0]['id'] for e in exams]


def test_unknown_answers_offer_help_instead_of_infinite_retry(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.adaptiv import store
    _, exams, tids, token = setup_journeys(client, fake_llm, app_env, monkeypatch)
    app_env.config.update(llm_error_creation_enabled=False)
    base, sid, _ = start(client, token, tids[0], exams[0])
    post(client, token, base, sid, 'anker', 'Ja')
    for _ in range(3):
        page = post(client, token, base, sid, 'diagnose', '99999')
    assert store.sitzung(sid)['zustand'] == 'ESCALATED'
    assert 'zu zweit' in page.text


def test_generated_grade_variant_remains_findable_without_overwriting_source(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.adaptiv import erzeugung, lektionen, store
    setup_journeys(client, fake_llm, app_env, monkeypatch)
    original = _lektion()
    first = erzeugung.speichern(original, 'Mathematik')
    variant = _lektion()
    variant['konzept']['klasse_von'] = 9
    variant['konzept']['klasse_bis'] = 10
    second = erzeugung.speichern(variant, 'Mathematik')
    assert first != second
    assert store.konzept(first)['klasse_bis'] == original['konzept']['klasse_bis']
    assert lektionen.fuer_thema('Würfel: Volumen', 'Mathematik', 9)['konzept_id'] == second
    assert erzeugung.speichern(variant, 'Mathematik') == second


def test_exam_upload_to_confirmed_exam_stays_separate(client, fake_llm, fake_cli, app_env, monkeypatch, tmp_path):
    from app.services import learning_hub
    personal, _, _, token = setup_journeys(client, fake_llm, app_env, monkeypatch)
    fake_llm.responses['exam_scan'] = {'themen': ['Brüche addieren'], 'exam_date': '2026-10-15'}
    picture = make_jpeg(tmp_path / 'pruefung.jpg')
    with picture.open('rb') as source:
        response = client.post('/klassenarbeit/themenblatt', data={'_csrf': token},
                               files={'datei': ('pruefung.jpg', source, 'image/jpeg')})
    assert response.url.path == '/klassenarbeit/neu'
    run_jobs(app_env, fake_llm)
    scan = app_env.db.q1('SELECT id FROM exam_scan ORDER BY id DESC LIMIT 1')['id']
    page = client.get('/klassenarbeit/neu')
    assert 'value="2026-10-15"' in page.text and 'Brüche addieren' in page.text
    assert client.get(f'/lernen/material/status?scan_id={scan}').status_code == 404
    response = client.post('/klassenarbeit', data={"fach": "mathematik", '_csrf': token, 'scan_id': scan,
        'exam_date': '2026-10-15', 'themen': 'Brüche addieren', 'fach': 'Mathematik'})
    assert 'Wann möchtest du lernen?' in response.text
    eid = app_env.db.q1('SELECT id FROM exam ORDER BY id DESC LIMIT 1')['id']
    assert learning_hub.exam_topics(eid)[0]['id'] != personal
    assert [t['id'] for t in learning_hub.personal_topics()] == [personal]


@pytest.mark.parametrize('video', [False, True])
def test_historical_exam_media_remain_readable_only_in_exam_area(client, fake_llm, fake_cli, app_env, monkeypatch, tmp_path, video):
    _, exams, tids, token = setup_journeys(client, fake_llm, app_env, monkeypatch)
    media = tmp_path / ('archiv.mp4' if video else 'archiv.html')
    content = b'0123456789' * 100 if video else b'<p>Gespeicherte Pruefungserklaerung</p>'
    media.write_bytes(content)
    with app_env.db.tx() as c:
        lid = c.execute("INSERT INTO lesson(topic_id,state,runden,created_at) VALUES(?,'bereit',1,?)",
                        (tids[0], app_env.db.now())).lastrowid
        rid = c.execute("""INSERT INTO lesson_round(lesson_id,nr,state,material_pfad,created_at)
            VALUES(?,1,'erstellt',?,?)""", (lid, str(media), app_env.db.now())).lastrowid
        mid = c.execute("""INSERT INTO exam_material(exam_id,row_key,lesson_id,vorher,created_at)
            VALUES(?,'legacy',?,'null',?)""", (exams[0], lid, app_env.db.now())).lastrowid
    url = f'/klassenarbeit/material/{mid}'
    page = client.get(url)
    assert page.status_code == 200 and url + '/inhalt' in page.text
    assert client.get(f'/material/{rid}').status_code == 404
    assert client.get(f'/lernen/{lid}').status_code == 404
    headers = {'Range': 'bytes=10-19'} if video else {}
    response = client.get(url + '/inhalt', headers=headers)
    assert response.status_code == (206 if video else 200)
    assert response.content == (b'0123456789' if video else content)
    target = client.post(url + '/fragen', data={'_csrf': token}, follow_redirects=False)
    assert target.headers['location'] == f'/klassenarbeit/{exams[0]}#exam-next-step'
