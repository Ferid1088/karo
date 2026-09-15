"""Eltern bestimmen Anzeige und Freigabe von Antworten im Kind-Bereich."""
import pytest

from .conftest import csrf_from, run_jobs
from .test_app import (einrichten, blatt_einlesen, themen_freigeben,
                       kind_modus_aktivieren)


def prepare_review(client, fake_llm, app_env):
    from app import quizzes
    einrichten(client, fake_llm)
    blatt_einlesen(client, fake_llm, app_env)
    topic_id = themen_freigeben(client, app_env)[0]
    quiz_id = quizzes.anfordern(topic_id)
    run_jobs(app_env, fake_llm)
    with app_env.db.tx() as c:
        c.execute("UPDATE quiz SET state='ausgewertet' WHERE id=?", (quiz_id,))
    return topic_id, quiz_id


def test_review_moves_between_parent_and_child_pages(client, fake_llm, fake_cli, app_env):
    _, quiz_id = prepare_review(client, fake_llm, app_env)
    link = f'href="/quiz/{quiz_id}"'
    for enabled in (False, True, False):
        app_env.config.update(antworten_pruefen_kind=enabled)
        assert (link in client.get('/eltern').text) is not enabled
        for path in ('/', '/lernen', '/lernzyklus'):
            page = client.get(path)
            assert (link in page.text) is enabled
        if enabled:
            assert 'Jetzt prüfen' in client.get('/').text
    kind_modus_aktivieren(client)
    assert 'data-review-form' not in client.get(f'/quiz/{quiz_id}').text
    app_env.config.update(antworten_pruefen_kind=True)
    assert 'data-review-form' in client.get(f'/quiz/{quiz_id}').text
    assert link in client.get('/').text
    assert link in client.get('/lernen').text


@pytest.mark.parametrize('alias', [False, True])
def test_child_release_requires_setting_and_csrf(client, fake_llm, fake_cli, app_env, alias):
    topic_id, quiz_id = prepare_review(client, fake_llm, app_env)
    kind_modus_aktivieren(client)
    path = (f'/lernzyklus/{topic_id}/quiz/{quiz_id}' if alias else f'/quiz/{quiz_id}')
    data = {'_csrf': csrf_from(client.get(path).text)}
    questions = app_env.db.q('SELECT id FROM question WHERE quiz_id=?', quiz_id)
    data['frage_id'] = [str(q['id']) for q in questions]
    data.update({f"urteil_{q['id']}": 'ja' for q in questions})
    assert client.post(path + '/freigabe', data=data).status_code == 403
    app_env.config.update(antworten_pruefen_kind=True)
    assert client.post(path + '/freigabe', data={**data, '_csrf': 'invalid'}).status_code == 403
    for restricted in ('/setup', '/eltern', '/themen'):
        assert client.get(restricted).status_code == 403
    assert client.post('/setup/finish', data={**data, 'antworten_pruefen_kind': 'ja'}).status_code == 403
    response = client.post(path + '/freigabe', data=data, follow_redirects=False)
    assert response.status_code == 303
    assert client.get(response.headers['location']).status_code == 200
    assert app_env.db.q1('SELECT state FROM quiz WHERE id=?', quiz_id)['state'] == 'freigegeben'
    count = len(app_env.db.q('SELECT * FROM answer_log'))
    assert count == len(questions)
    repeated = client.post(path + '/freigabe', data=data, follow_redirects=False)
    assert repeated.headers['location'] == '/'
    assert len(app_env.db.q('SELECT * FROM answer_log')) == count
    app_env.config.update(antworten_pruefen_kind=False)
    assert client.post(path + '/freigabe', data=data).status_code == 403


def test_next_action_review_follows_selected_role():
    from app.services.workflow import get_next_action
    reviews = [{'id': 1, 'thema_label': 'Brüche'}]
    for enabled in (False, True):
        for role in ('parent', 'child'):
            action = get_next_action(role, [], [], reviews, antworten_pruefen_kind=enabled)
            assert (action.kind == 'review') is (role == ('child' if enabled else 'parent'))
