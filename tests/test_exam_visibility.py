"""Klassenarbeitsplan: Sichtbarkeit, Berechtigungen und kompletter Kind-Ablauf."""
from datetime import date, timedelta

from .conftest import csrf_from, make_jpeg, run_jobs
from .test_app import einrichten, kind_modus_aktivieren, _bis_rot


def test_exam_plan_stays_available_to_parents_and_child_access_is_configurable(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    for enabled in (False, True, False):
        app_env.config.update(klassenarbeit_kind=enabled)
        # The compact parent dashboard keeps management links regardless of
        # whether the same feature is also enabled for the child.
        assert 'href="/klassenarbeit"' in client.get('/eltern').text
        # Eltern dürfen die Prüfungen immer über den Lernbereich öffnen.
        for path in ('/lernen', '/lernzyklus'):
            assert 'href="/klassenarbeit"' in client.get(path).text
        assert client.get('/klassenarbeit').status_code == 200
    kind_modus_aktivieren(client)
    for enabled in (False, True, False):
        app_env.config.update(klassenarbeit_kind=enabled)
        for path in ('/lernen', '/lernzyklus'):
            assert ('href="/klassenarbeit"' in client.get(path).text) is enabled
        # Ohne angelegte Arbeit gibt es auf Heute keinen leeren Prüfungsauftrag;
        # der Weg dorthin steht nur als Reiter in der Hauptnavigation.
        heute = client.get('/').text
        assert 'href="/klassenarbeit"' not in heute[heute.index('<main'):]
        assert ('class="exam-entry" href="/klassenarbeit"' in heute) is enabled
        for path in ('/klassenarbeit', '/messung/examen'):
            page = client.get(path)
            assert page.status_code == (200 if enabled else 403)
            if enabled:
                assert 'href="/eltern"' not in page.text
                assert 'Für Eltern:' not in page.text
                assert 'href="/lernen"' in page.text


def test_child_can_create_use_and_update_exam_with_setting(
        client, fake_llm, fake_cli, app_env, tmp_path):
    from app.services import learning_hub, exam_calendar
    topic_id = _bis_rot(client, fake_llm, app_env)
    topic = app_env.db.q1('SELECT * FROM topic WHERE id=?', topic_id)
    exam_date = (date.today() + timedelta(days=14)).isoformat()
    fake_llm.responses['exam_scan'] = {'themen': [topic['label']], 'exam_date': exam_date}
    fake_llm.responses['plan'] = {
        'einschaetzung': 'Das üben wir.',
        'tagesplan': [{'tag': 'Montag', 'inhalt': topic['label'],
                      'minuten': 15, 'topic_code': topic['code']}],
    }
    kind_modus_aktivieren(client)
    token = csrf_from(client.get('/').text)
    posts = ('/klassenarbeit', '/klassenarbeit/1/plan/neu',
             '/klassenarbeit/1/lerntag', '/klassenarbeit/1/ergebnis')
    for path in posts:
        assert client.post(path, data={'_csrf': token}).status_code == 403
    assert client.get('/klassenarbeit/1/plan/status').status_code == 403

    # Die mitgelieferte, geprüfte Bruchlektion gehört zur 6. Klasse.
    app_env.config.update(klassenarbeit_kind=True, adaptive_learning_enabled=True, learner_grade=6)
    for path in posts:
        assert client.post(path, data={'_csrf': 'invalid'}).status_code == 403
    # Themen tippt das Kind ein; ein Themenblatt wird nicht mehr gelesen.
    assert client.post('/klassenarbeit', data={"fach": "mathematik",
        '_csrf': token, 'exam_date': exam_date,
        'themen': 'Brüche addieren'}).status_code == 200
    run_jobs(app_env, fake_llm)
    exam = app_env.db.q1('SELECT * FROM exam ORDER BY id DESC LIMIT 1')
    exam_id = exam['id']
    own = learning_hub.exam_topics(exam_id)[0]
    assert own['id'] != topic_id
    assert own['learning_status'] == 'neu'
    assert not exam_calendar.get_days(exam_id)
    page = client.get('/messung/examen')
    assert f'href="/klassenarbeit/{exam_id}"' in page.text
    assert 'Für Eltern:' not in page.text
    today = app_env.db.today()
    last_day = (date.fromisoformat(exam_date) - timedelta(days=1)).isoformat()
    calendar = client.post(f'/klassenarbeit/{exam_id}/kalender', data={
        '_csrf': token, f'minutes_{today}': '15', f'minutes_{last_day}': '20'})
    assert calendar.status_code == 200
    assert exam_calendar.get_days(exam_id)[today] == 15
    assert f'action="/klassenarbeit/{exam_id}/lernen/start"' in calendar.text
    start = client.post(f'/klassenarbeit/{exam_id}/lernen/start', data={
        '_csrf': token, 'topic_id': own['id']})
    assert start.status_code == 200
    session = app_env.db.q1('SELECT * FROM lern_sitzung ORDER BY id DESC LIMIT 1')
    entry = app_env.db.q1('SELECT * FROM lern_eingabe WHERE id=?', session['eingabe_id'])
    assert entry['topic_id'] == own['id']
    assert session['zustand'] == 'DIAGNOSING'
    assert '/lernen/adaptiv' not in start.text
    assert client.post('/lernen/adaptiv/start', data={'_csrf': token, 'topic_id': own['id']}).status_code == 404
    # Alte Ergebnisfelder dürfen den persönlichen Lernstand nicht beschreiben.
    assert client.post(f'/klassenarbeit/{exam_id}/ergebnis', data={
        '_csrf': token, f'ist_{topic_id}': 'gruen'}).status_code == 200
    assert not app_env.db.q('SELECT * FROM prediction WHERE exam_id=?', exam_id)
    before = len(app_env.db.q('SELECT * FROM job'))
    plan = client.post(f'/klassenarbeit/{exam_id}/plan/neu', data={'_csrf': token}, follow_redirects=False)
    assert plan.headers['location'] == f'/klassenarbeit/{exam_id}#exam-calendar-title'
    assert len(app_env.db.q('SELECT * FROM job')) == before
    for path in ('/setup', '/eltern', '/wissen', '/themen', '/messung/fortschritt', '/protokoll'):
        assert client.get(path).status_code == 403
    assert client.post('/setup/finish', data={'_csrf': token, 'klassenarbeit_kind': 'ja'}).status_code == 403
    assert client.post('/quiz/1/freigabe', data={'_csrf': token}).status_code == 403
    app_env.config.update(klassenarbeit_kind=False)
    for path in posts:
        assert client.post(path, data={'_csrf': token}).status_code == 403
