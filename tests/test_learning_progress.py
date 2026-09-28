"""Neue Themen, begonnene Themen und ausdrücklich abgehakte Erfolge."""
import json
import sqlite3
from datetime import date, timedelta

from .conftest import csrf_from
from .test_app import einrichten, kind_modus_aktivieren
from .test_ui import Forms


def prepare(client, fake_llm, app_env):
    from app import topics
    einrichten(client, fake_llm)
    first = topics.anlegen('Brüche addieren', subject="mathematik")
    second = topics.anlegen('Längen messen', subject="mathematik")
    kind_modus_aktivieren(client)
    return first, second


def test_child_topic_lifecycle_and_independent_success(client, fake_llm, fake_cli, app_env):
    first, second = prepare(client, fake_llm, app_env)
    token = csrf_from(client.get('/lernen').text)
    card = f'data-topic-id="{first}"'
    assert card in client.get('/lernen?status=neu').text
    assert card not in client.get('/lernen?status=bearbeitung').text
    # Eine Bewertung oder das Ansehen der Übersicht hakt nichts ab.
    assert '<h3>Brüche addieren</h3>' not in client.get('/lernstand').text
    client.post(f'/lernzyklus/{first}/gelernt', data={'_csrf': token})
    assert card in client.get('/lernen?status=neu').text
    assert client.post(f'/lernzyklus/{first}/beginnen', data={'_csrf': token}).status_code == 200
    assert card not in client.get('/lernen?status=neu').text
    assert card in client.get('/lernen?status=bearbeitung').text
    assert f'data-topic-id="{second}"' in client.get('/lernen?status=neu').text
    page = client.get('/lernen?status=bearbeitung')
    Forms(page.text)  # Keine verschachtelten Formulare auf Themenkarten.
    response = client.post(f'/lernzyklus/{first}/gelernt', data={'_csrf': token, 'gelernt': 'ja'})
    assert response.status_code == 200
    assert 'Brüche addieren' in response.text
    assert 'Längen messen' not in response.text
    assert f'action="/lernstand/thema/{first}/zurueck"' in response.text
    assert 'action="/export"' not in response.text
    assert 'Alle bewerteten Antworten' not in response.text
    for path in ('/lernen?status=neu', '/lernen?status=bearbeitung', '/lernzyklus'):
        assert card not in client.get(path).text
    app_env.db.init()
    assert app_env.db.q1('SELECT learned_at FROM topic WHERE id=?', first)['learned_at']
    assert not app_env.db.q('SELECT * FROM answer_log')
    assert not app_env.db.q('SELECT * FROM topic_flag')
    response = client.post(f'/lernzyklus/{first}/gelernt', data={'_csrf': token})
    assert card in response.text
    assert response.request.url.query == b'status=bearbeitung'
    assert card not in client.get('/lernen?status=neu').text
    assert '<h3>Brüche addieren</h3>' not in client.get('/lernstand').text
    assert client.get('/messung/fortschritt').status_code == 403
    assert client.post('/export', data={'_csrf': token}).status_code == 403


def test_gelernt_on_new_topic_returns_to_neu_after_uncheck(client, fake_llm, fake_cli, app_env):
    # Ein Häkchen direkt auf einer "Neue Themen"-Karte (ohne "Thema anfangen")
    # darf das Thema nicht dauerhaft nach "In Bearbeitung" verschieben.
    first, _ = prepare(client, fake_llm, app_env)
    token = csrf_from(client.get('/lernen').text)
    card = f'data-topic-id="{first}"'
    assert card in client.get('/lernen?status=neu').text
    client.post(f'/lernzyklus/{first}/gelernt', data={'_csrf': token, 'gelernt': 'ja'})
    for path in ('/lernen?status=neu', '/lernen?status=bearbeitung'):
        assert card not in client.get(path).text
    response = client.post(f'/lernzyklus/{first}/gelernt', data={'_csrf': token})
    assert response.status_code == 200
    assert card in response.text


def test_gelernt_checkbox_refreshes_current_page_instead_of_opening_erfolge(
        client, fake_llm, fake_cli, app_env):
    first, _ = prepare(client, fake_llm, app_env)
    token = csrf_from(client.get('/lernen').text)
    card = f'data-topic-id="{first}"'
    client.post(f'/lernzyklus/{first}/beginnen', data={'_csrf': token})
    seite = '/lernen?status=bearbeitung'
    assert card in client.get(seite).text
    response = client.post(
        f'/lernzyklus/{first}/gelernt', data={'_csrf': token, 'gelernt': 'ja'},
        headers={'referer': f'http://127.0.0.1:8080{seite}'})
    assert response.status_code == 200
    # /lernen führt ins aktive Fach; der Filter bleibt erhalten.
    assert response.request.url.path == '/lernen/mathematik'
    assert 'status=bearbeitung' in str(response.request.url)
    assert card not in response.text
    # Ohne Referer (z. B. altes Formular) bleibt der bisherige Fallback.
    client.post(f'/lernzyklus/{first}/gelernt', data={'_csrf': token})
    response = client.post(f'/lernzyklus/{first}/gelernt', data={'_csrf': token, 'gelernt': 'ja'})
    assert response.request.url.path == '/lernstand'


def test_progress_requires_csrf_and_active_topic(client, fake_llm, fake_cli, app_env):
    first, _ = prepare(client, fake_llm, app_env)
    token = csrf_from(client.get('/lernen').text)
    for action in ('beginnen', 'gelernt'):
        assert client.post(f'/lernzyklus/{first}/{action}', data={'_csrf': 'bad', 'gelernt': 'ja'}).status_code == 403
        assert client.post(f'/lernzyklus/999999/{action}', data={'_csrf': token}).status_code == 404
    assert app_env.db.q1('SELECT learned_at FROM topic WHERE id=?', first)['learned_at'] is None
    with app_env.db.tx() as c:
        c.execute("UPDATE topic SET state='vorschlag' WHERE id=?", (first,))
    assert client.post(f'/lernzyklus/{first}/gelernt', data={'_csrf': token, 'gelernt': 'ja'}).status_code == 404


def test_exam_topics_keep_separate_progress(client, fake_llm, fake_cli, app_env):
    from app.services import learning_hub, exam
    first, second = prepare(client, fake_llm, app_env)
    app_env.config.update(klassenarbeit_kind=True)
    token = csrf_from(client.get('/lernen').text)
    created = exam.create_exam((date.today() + timedelta(days=10)).isoformat(),
                              manual_topics='Brüche addieren', subject='mathematik')
    owned = learning_hub.exam_topics(created.exam_id)[0]
    assert owned['id'] not in (first, second)
    assert owned['learning_status'] == 'neu'
    client.post(f'/lernzyklus/{first}/beginnen', data={'_csrf': token})
    client.post(f'/lernzyklus/{first}/gelernt', data={'_csrf': token, 'gelernt': 'ja'})
    assert learning_hub.exam_topics(created.exam_id)[0]['learning_status'] == 'neu'
    detail = client.get(f'/klassenarbeit/{created.exam_id}').text
    assert f'name="topic_id" value="{owned["id"]}"' in detail
    assert f'name="topic_id" value="{first}"' not in detail
    for path in ('/lernen', '/lernen?status=neu', '/lernen?status=bearbeitung'):
        assert f'data-topic-id="{owned["id"]}"' not in client.get(path).text
    assert app_env.db.q1('SELECT learned_at FROM topic WHERE id=?', owned['id'])['learned_at'] is None
    app_env.config.update(klassenarbeit_kind=False)
    assert 'href="/klassenarbeit' not in client.get('/lernen').text
    assert client.get(f'/klassenarbeit/{created.exam_id}').status_code == 403


def test_existing_topic_schema_gets_nullable_progress_columns(app_env):
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE topic (id INTEGER PRIMARY KEY, label TEXT)')
    conn.execute("INSERT INTO topic VALUES (1, 'Vorhandenes Thema')")
    app_env.db._migrate(conn)
    app_env.db._migrate(conn)
    row = conn.execute('SELECT * FROM topic').fetchone()
    assert row['label'] == 'Vorhandenes Thema'
    assert row['learning_started_at'] is None
    assert row['learned_at'] is None
    conn.close()


def test_prepared_material_is_new_and_auto_completion_is_not_manual_success(
        client, fake_llm, fake_cli, app_env):
    from app import teaching, topics
    from app.services import learning_progress
    first, _ = prepare(client, fake_llm, app_env)
    lesson_id = teaching.starten(first)
    grouped = learning_progress.groups(topics.liste(topics.AKTIV))
    assert first in {t['id'] for t in grouped['neu']}
    with app_env.db.tx() as c:
        c.execute("UPDATE lesson SET state='gelernt' WHERE id=?", (lesson_id,))
    assert '<h3>Brüche addieren</h3>' not in client.get('/lernstand').text
