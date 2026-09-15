"""Area identity follows content and child access, not just the login role."""
from .test_app import einrichten, kind_modus_aktivieren


def test_parent_can_move_between_distinct_areas(client, fake_llm, fake_cli):
    einrichten(client, fake_llm)
    for path in ('/eltern', '/setup', '/themen', '/wissen', '/klassenarbeit', '/messung/fortschritt'):
        page = client.get(path)
        assert page.status_code == 200
        assert 'data-ui-area="parent"' in page.text, path
        assert 'Zum Kinderbereich' in page.text
    for path in ('/', '/lernen', '/lernstand'):
        page = client.get(path)
        assert 'data-ui-area="child"' in page.text, path
        assert 'Für Eltern' in page.text


def test_shared_pages_keep_child_skin_when_enabled(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    app_env.config.update(schulblaetter_kind=True, klassenarbeit_kind=True)
    for path in ('/wissen', '/klassenarbeit'):
        page = client.get(path)
        assert page.status_code == 200
        assert 'data-ui-area="child"' in page.text, path
    kind_modus_aktivieren(client)
    for path in ('/', '/lernen', '/lernstand', '/wissen', '/klassenarbeit', '/hilfe'):
        page = client.get(path)
        assert page.status_code == 200
        assert 'data-ui-area="child"' in page.text, path
        assert 'class="parent-link' not in page.text
    assert client.get('/eltern').status_code == 403


def test_review_uses_parent_skin_until_review_is_enabled_for_child(client, fake_llm, fake_cli, app_env):
    from .conftest import run_jobs
    from .test_app import blatt_einlesen, themen_freigeben
    from app import quizzes
    einrichten(client, fake_llm)
    blatt_einlesen(client, fake_llm, app_env)
    themen_freigeben(client, app_env)
    topic = app_env.db.q1("SELECT id FROM topic WHERE state='aktiv'")["id"]
    quiz_id = quizzes.anfordern(topic)
    run_jobs(app_env, fake_llm)
    with app_env.db.tx() as connection:
        connection.execute("UPDATE quiz SET state='ausgewertet' WHERE id=?", (quiz_id,))
    assert 'data-ui-area="parent"' in client.get(f'/quiz/{quiz_id}').text
    app_env.config.update(antworten_pruefen_kind=True)
    assert 'data-ui-area="child"' in client.get(f'/quiz/{quiz_id}').text
