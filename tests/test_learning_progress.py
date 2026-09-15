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
    first = topics.anlegen('Brüche addieren')
    second = topics.anlegen('Längen messen')
    kind_modus_aktivieren(client)
    return first, second


def test_child_topic_lifecycle_and_independent_success(client, fake_llm, fake_cli, app_env):
    first, second = prepare(client, fake_llm, app_env)
    token = csrf_from(client.get('/lernen').text)
    card = f'data-topic-id="{first}"'
    assert card in client.get('/lernen?tab=neu').text
    assert card not in client.get('/lernen?tab=bearbeitung').text
    # Eine Bewertung oder das Ansehen der Übersicht hakt nichts ab.
    assert '<h2>Brüche addieren</h2>' not in client.get('/lernstand').text
    client.post(f'/lernzyklus/{first}/gelernt', data={'_csrf': token})
    assert card in client.get('/lernen?tab=neu').text
    assert client.post(f'/lernzyklus/{first}/beginnen', data={'_csrf': token}).status_code == 200
    assert card not in client.get('/lernen?tab=neu').text
    assert card in client.get('/lernen?tab=bearbeitung').text
    assert f'data-topic-id="{second}"' in client.get('/lernen?tab=neu').text
    page = client.get('/lernen?tab=bearbeitung')
    Forms(page.text)  # Keine verschachtelten Formulare auf Themenkarten.
    response = client.post(f'/lernzyklus/{first}/gelernt', data={'_csrf': token, 'gelernt': 'ja'})
    assert response.status_code == 200
    assert '<h2>Brüche addieren</h2>' in response.text
    assert '<h2>Längen messen</h2>' not in response.text
    assert 'name="gelernt" value="ja" checked' in response.text
    assert 'action="/export"' not in response.text
    assert 'Alle bewerteten Antworten' not in response.text
    for path in ('/lernen?tab=neu', '/lernen?tab=bearbeitung', '/lernzyklus'):
        assert card not in client.get(path).text
    app_env.db.init()
    assert app_env.db.q1('SELECT learned_at FROM topic WHERE id=?', first)['learned_at']
    assert not app_env.db.q('SELECT * FROM answer_log')
    assert not app_env.db.q('SELECT * FROM topic_flag')
    response = client.post(f'/lernzyklus/{first}/gelernt', data={'_csrf': token})
    assert card in response.text
    assert card not in client.get('/lernen?tab=neu').text
    assert '<h2>Brüche addieren</h2>' not in client.get('/lernstand').text
    assert client.get('/messung/fortschritt').status_code == 403
    assert client.post('/export', data={'_csrf': token}).status_code == 403


def test_gelernt_on_new_topic_returns_to_neu_after_uncheck(client, fake_llm, fake_cli, app_env):
    # Ein Häkchen direkt auf einer "Neue Themen"-Karte (ohne "Thema anfangen")
    # darf das Thema nicht dauerhaft nach "In Bearbeitung" verschieben.
    first, _ = prepare(client, fake_llm, app_env)
    token = csrf_from(client.get('/lernen').text)
    card = f'data-topic-id="{first}"'
    assert card in client.get('/lernen?tab=neu').text
    client.post(f'/lernzyklus/{first}/gelernt', data={'_csrf': token, 'gelernt': 'ja'})
    for path in ('/lernen?tab=neu', '/lernen?tab=bearbeitung'):
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
    seite = '/lernen?tab=bearbeitung'
    assert card in client.get(seite).text
    response = client.post(
        f'/lernzyklus/{first}/gelernt', data={'_csrf': token, 'gelernt': 'ja'},
        headers={'referer': f'http://127.0.0.1:8080{seite}'})
    assert response.status_code == 200
    assert response.request.url.path == '/lernen'
    assert 'tab=bearbeitung' in str(response.request.url)
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


def test_exam_topics_use_same_progress_and_hide_completed(client, fake_llm, fake_cli, app_env):
    first, second = prepare(client, fake_llm, app_env)
    app_env.config.update(klassenarbeit_kind=True)
    token = csrf_from(client.get('/lernen').text)
    with app_env.db.tx() as c:
        c.execute('INSERT INTO exam(subject, exam_date, themen, created_at) VALUES (?, ?, ?, ?)',
                  ('Mathematik', (date.today() + timedelta(days=10)).isoformat(),
                   json.dumps(['Brüche addieren']), app_env.db.now()))
    new = '/lernen?tab=klassenarbeit&status=neu'
    active = '/lernen?tab=klassenarbeit&status=bearbeitung'
    assert f'data-topic-id="{first}"' in client.get(new).text
    assert f'data-topic-id="{second}"' not in client.get(new).text
    client.post(f'/lernzyklus/{first}/beginnen', data={'_csrf': token})
    assert f'data-topic-id="{first}"' not in client.get(new).text
    assert f'data-topic-id="{first}"' in client.get(active).text
    client.post(f'/lernzyklus/{first}/gelernt', data={'_csrf': token, 'gelernt': 'ja'})
    for path in (new, active):
        assert f'data-topic-id="{first}"' not in client.get(path).text
        assert 'werden noch vorbereitet' not in client.get(path).text
    app_env.config.update(klassenarbeit_kind=False)
    assert 'aria-label="Themen für die Klassenarbeit"' not in client.get(new).text
    assert 'href="/klassenarbeit' not in client.get(new).text


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
    assert '<h2>Brüche addieren</h2>' not in client.get('/lernstand').text
