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


def test_erfolge_tabs_stay_in_the_area_they_were_opened_from(client, fake_llm, fake_cli):
    """Die Erfolge-Seite liegt unter zwei Adressen. Ein Reiterklick darf den
    Bereich nicht wechseln — in den Kinderbereich kommt man nur ueber
    "Zum Kinderbereich"."""
    einrichten(client, fake_llm)

    eltern = client.get('/messung/fortschritt')
    assert eltern.status_code == 200
    assert 'data-ui-area="parent"' in eltern.text
    assert 'href="/messung/fortschritt?tab=arbeiten"' in eltern.text
    assert 'href="/lernstand?tab=arbeiten"' not in eltern.text

    arbeiten = client.get('/messung/fortschritt?tab=arbeiten')
    assert arbeiten.status_code == 200
    assert 'data-ui-area="parent"' in arbeiten.text

    kind = client.get('/lernstand')
    assert 'data-ui-area="child"' in kind.text
    assert 'href="/lernstand?tab=arbeiten"' in kind.text
    assert '/messung/fortschritt?tab=arbeiten' not in kind.text


def test_erfolge_actions_return_to_their_own_area(client, fake_llm, fake_cli, app_env):
    from app import db
    from app.routers.shared import erfolge_ziel
    from .conftest import csrf_from
    from .test_app import als_kind

    assert erfolge_ziel('/messung/fortschritt') == '/messung/fortschritt'
    assert erfolge_ziel('/messung') == '/messung/fortschritt'
    assert erfolge_ziel('/lernstand') == '/lernstand'
    assert erfolge_ziel('', 'arbeiten') == '/lernstand?tab=arbeiten'
    # Ein Formularfeld darf kein freies Umleitungsziel sein.
    assert erfolge_ziel('https://fremd.example/') == '/lernstand'

    einrichten(client, fake_llm)
    with db.tx() as c:
        topic_id = c.execute(
            "INSERT INTO topic (subject, code, label, state, created_at)"
            " VALUES ('mathematik', 'M-TEST-1', 'Testthema', 'aktiv', ?)",
            (db.today(),)).lastrowid

    # Das Archiv gehoert dem Kind: Eltern sehen es, raeumen es aber nicht auf.
    seite = client.get('/messung/fortschritt')
    assert seite.status_code == 200
    abgewiesen = client.post(f"/lernstand/thema/{topic_id}/zurueck",
                             data={"_csrf": csrf_from(seite.text),
                                   "ziel": "/messung/fortschritt"},
                             follow_redirects=False)
    assert abgewiesen.status_code == 403

    # Das Kind raeumt auf und landet wieder auf seiner eigenen Adresse.
    with als_kind(client, app_env):
        seite = client.get('/lernstand')
        antwort = client.post(f"/lernstand/thema/{topic_id}/zurueck",
                              data={"_csrf": csrf_from(seite.text),
                                    "ziel": "/lernstand"},
                              follow_redirects=False)
        assert antwort.headers["location"] == "/lernstand"
