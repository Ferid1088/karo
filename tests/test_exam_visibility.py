"""Klassenarbeitsplan: Sichtbarkeit, Berechtigungen und kompletter Kind-Ablauf."""
from datetime import date, timedelta

from .conftest import csrf_from, make_jpeg, run_jobs
from .test_app import einrichten, kind_modus_aktivieren, _bis_rot


def test_exam_plan_moves_between_parent_and_child_sections(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    for enabled in (False, True, False):
        app_env.config.update(klassenarbeit_kind=enabled)
        assert ('href="/klassenarbeit"' in client.get('/eltern').text) is not enabled
        for path in ('/', '/lernen', '/lernzyklus'):
            assert ('href="/klassenarbeit"' in client.get(path).text) is enabled
    kind_modus_aktivieren(client)
    for enabled in (False, True, False):
        app_env.config.update(klassenarbeit_kind=enabled)
        for path in ('/', '/lernen', '/lernzyklus'):
            assert ('href="/klassenarbeit"' in client.get(path).text) is enabled
        for path in ('/klassenarbeit', '/messung/examen'):
            page = client.get(path)
            assert page.status_code == (200 if enabled else 403)
            if enabled:
                assert 'href="/eltern"' not in page.text
                assert 'Für Eltern:' not in page.text
                assert 'href="/lernen"' in page.text


def test_child_can_create_use_and_update_exam_with_setting(
        client, fake_llm, fake_cli, app_env, tmp_path):
    from app import exam_plan
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
    posts = ('/klassenarbeit', '/klassenarbeit/themenblatt',
             '/klassenarbeit/1/plan/neu', '/klassenarbeit/1/lerntag',
             '/klassenarbeit/1/ergebnis')
    for path in posts:
        assert client.post(path, data={'_csrf': token}).status_code == 403
    for path in ('/klassenarbeit/1/plan/status', '/klassenarbeit/themenblatt/status?scan_id=1'):
        assert client.get(path).status_code == 403

    app_env.config.update(klassenarbeit_kind=True)
    for path in posts:
        assert client.post(path, data={'_csrf': 'invalid'}).status_code == 403
    jpeg = make_jpeg(tmp_path / 'themenblatt.jpg', size=(1000, 1300))
    assert client.post('/klassenarbeit/themenblatt', data={'_csrf': token}, files={
        'datei': ('themenblatt.jpg', jpeg.read_bytes(), 'image/jpeg')}).status_code == 200
    run_jobs(app_env, fake_llm)
    scan = app_env.db.q1('SELECT * FROM exam_scan ORDER BY id DESC LIMIT 1')
    assert client.get(f"/klassenarbeit/themenblatt/status?scan_id={scan['id']}").json()['signatur'] == 'gelesen'
    assert client.post('/klassenarbeit', data={
        '_csrf': token, 'exam_date': exam_date, 'scan_id': scan['id']}).status_code == 200
    run_jobs(app_env, fake_llm)
    exam = app_env.db.q1('SELECT * FROM exam ORDER BY id DESC LIMIT 1')
    exam_id = exam['id']
    assert client.get(f'/klassenarbeit/{exam_id}/plan/status').json()['signatur'] == 'bereit'
    page = client.get('/messung/examen')
    assert 'Ergebnis der Klassenarbeit eintragen' in page.text
    assert 'Für Eltern:' not in page.text
    tag = exam_plan.holen_plan(exam_id)['tagesplan_liste'][0]
    material = client.post(f'/klassenarbeit/{exam_id}/lerntag', data={
        '_csrf': token, 'row_key': tag['row_key'], 'ausgabe': 'html',
    }, headers={'accept': 'application/json'})
    assert material.status_code == 200
    run_jobs(app_env, fake_llm)
    material_url = material.json()['url']
    assert client.get(material_url + '/status').json()['state'] == 'bereit'
    assert '<iframe' in client.get(material_url).text
    assert 'href="/eltern"' not in client.get(material_url).text
    assert client.post(material_url + '/fragen', data={'_csrf': token}).status_code == 200
    assert client.post(f'/klassenarbeit/{exam_id}/ergebnis', data={
        '_csrf': token, f'ist_{topic_id}': 'gruen'}).status_code == 200
    assert app_env.db.q1('SELECT tatsaechlich FROM prediction WHERE exam_id=? AND topic_id=?',
                        exam_id, topic_id)['tatsaechlich'] == 'gruen'
    assert client.post(f'/klassenarbeit/{exam_id}/plan/neu', data={'_csrf': token}).status_code == 200
    assert client.get(f'/klassenarbeit/{exam_id}/plan/status').json()['signatur'] == 'offen'
    for path in ('/setup', '/eltern', '/wissen', '/themen', '/messung/fortschritt', '/protokoll'):
        assert client.get(path).status_code == 403
    assert client.post('/setup/finish', data={'_csrf': token, 'klassenarbeit_kind': 'ja'}).status_code == 403
    assert client.post('/quiz/1/freigabe', data={'_csrf': token}).status_code == 403
    app_env.config.update(klassenarbeit_kind=False)
    for path in posts:
        assert client.post(path, data={'_csrf': token}).status_code == 403
