"""Lerninhalte pro Thema erst nach bestätigter Eingangsprüfung."""
from .conftest import csrf_from, run_jobs
from .test_app import (einrichten, blatt_einlesen, themen_freigeben,
                       quiz_beantworten, quiz_freigeben, kind_modus_aktivieren)
from .test_ui import Forms


def test_content_creation_moves_to_child_topic_after_first_check(
        client, fake_llm, fake_cli, app_env):
    from app import quizzes, teaching
    einrichten(client, fake_llm)
    blatt_einlesen(client, fake_llm, app_env)
    topic_id, other = themen_freigeben(client, app_env)
    action = f'action="/lernzyklus/{topic_id}/start"'
    parent = client.get('/themen')
    assert f'action="/themen/{topic_id}/lernen"' not in parent.text
    app_env.config.update(antworten_pruefen_kind=True)
    kind_modus_aktivieren(client)
    token = csrf_from(client.get('/lernen').text)
    page = client.get(f'/lernzyklus/{topic_id}')
    assert 'Erste Prüfung starten' in page.text
    assert action not in page.text
    assert action not in client.get('/lernen?tab=neu').text
    blocked = client.post(f'/lernzyklus/{topic_id}/start', data={'_csrf': token})
    assert 'Bitte zuerst die Themenprüfung abschließen' in blocked.text
    assert not app_env.db.q('SELECT id FROM lesson')
    response = client.post(f'/lernzyklus/{topic_id}/quiz/starten', data={'_csrf': token})
    assert response.status_code == 200
    run_jobs(app_env, fake_llm)
    quiz = app_env.db.q1('SELECT * FROM quiz ORDER BY id DESC LIMIT 1')
    assert action not in client.get(f'/lernzyklus/{topic_id}').text
    quiz_beantworten(client, app_env, quiz['id'], {1: '3/4', 2: '5/9', 3: '2/9'})
    run_jobs(app_env, fake_llm)
    assert app_env.db.q1('SELECT state FROM quiz WHERE id=?', quiz['id'])['state'] == quizzes.STATE_AUSGEWERTET
    assert action not in client.get('/lernen?tab=bearbeitung').text
    assert action not in client.get(f'/lernzyklus/{topic_id}').text
    quiz_freigeben(client, app_env, quiz['id'])
    page = client.get('/lernen?tab=bearbeitung')
    assert action in page.text
    assert 'Lerninhalte erstellen' in page.text
    assert f'action="/lernzyklus/{other}/start"' not in page.text
    Forms(page.text)
    assert action in client.get(f'/lernzyklus/{topic_id}').text
    # Auch bei grün ist die Funktion verfügbar: entscheidend ist die Prüfung.
    with app_env.db.tx() as c:
        c.execute("UPDATE topic_flag SET flag='gruen' WHERE topic_id=?", (topic_id,))
    assert action in client.get('/lernen?tab=bearbeitung').text
    assert client.post(f'/lernzyklus/{topic_id}/start', data={'_csrf': 'bad'}).status_code == 403
    response = client.post(f'/lernzyklus/{topic_id}/start', data={
        '_csrf': token, 'ausgabe': 'html'}, follow_redirects=False)
    lesson_id = int(response.headers['location'].rsplit('/', 1)[-1])
    assert teaching.holen(lesson_id)['topic_id'] == topic_id
    run_jobs(app_env, fake_llm)
    assert '<iframe' in client.get(response.headers['location']).text


def test_lesson_quiz_does_not_replace_initial_topic_check(client, fake_llm, fake_cli, app_env):
    from app import quizzes, topics
    from app.services import learning_content
    einrichten(client, fake_llm)
    topic_id = topics.anlegen('Neue Geometrie')
    quiz_id = quizzes.anfordern(topic_id, anlass='lernrunde')
    with app_env.db.tx() as c:
        c.execute("UPDATE quiz SET state='freigegeben' WHERE id=?", (quiz_id,))
    assert not learning_content.can_create(topic_id)
