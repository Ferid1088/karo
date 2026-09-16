"""Der Begleiter (ersetzt "Karo" nur im Kind-Bereich) und das Interessen-Tagebuch."""
import tempfile
from pathlib import Path

import pytest
from .conftest import csrf_from, make_jpeg
from .test_woche import family, role, post


@pytest.fixture
def welt(family):
    from app.welten import store
    return family, store


def set_companion(welt, name='Flafi', farbe='ozean', spass='Fußball spielen', foto=None):
    family, store = welt
    role(family)
    token = csrf_from(family[0].get('/welten').text)
    data = {'_csrf': token, 'name': name, 'farbe': farbe, 'spass_antwort': spass}
    files = {'foto': foto} if foto else None
    response = family[0].post('/welten/begleiter', data=data, files=files, follow_redirects=False)
    assert response.status_code == 303, response.text[:800]
    return next(r for r in store.companion_history() if r['name'] == name)


def test_default_state_shows_karo_everywhere(welt):
    family, store = welt
    role(family)
    assert store.current_companion() is None
    page = family[0].get('/welten').text
    assert 'Meine Welt' in page
    assert 'Noch kein eigener Begleiter' in page
    home = family[0].get('/').text
    assert '>Karo<' in home
    assert '<title>Heute – Karo' in home


def test_child_sets_companion_and_it_replaces_karo_app_wide(welt):
    family, store = welt
    set_companion(welt, name='Flafi')
    home = family[0].get('/').text
    assert '>Flafi<' in home
    assert '<title>Heute – Flafi' in home
    lernen = family[0].get('/lernen').text
    assert 'Flafi' in lernen


def test_companion_changes_are_kept_as_history_not_overwritten(welt):
    family, store = welt
    set_companion(welt, name='Flafi')
    set_companion(welt, name='Mochi')
    history = store.companion_history()
    assert [h['name'] for h in history] == ['Mochi', 'Flafi']
    assert store.current_companion()['name'] == 'Mochi'
    page = family[0].get('/welten').text
    assert 'Mochi' in page
    assert 'Flafi' in page  # in der "Frühere Begleiter"-Liste


def test_companion_never_shown_in_parent_area(welt):
    # Eltern duerfen den Namen als Info sehen (z.B. auf der Eltern-Startseite),
    # aber die App-Marke selbst (Logo/Titel) bleibt fuer sie "Karo".
    family, store = welt
    set_companion(welt, name='Flafi')
    role(family, 'parent')
    eltern = family[0].get('/eltern')
    assert '>Karo<' in eltern.text
    assert 'Flafi' not in eltern.text.split('<title>')[1].split('</title>')[0]
    einstellungen = family[0].get('/setup').text
    assert 'Flafi' not in einstellungen


def test_photo_upload_and_serving(welt):
    family, store = welt
    with tempfile.TemporaryDirectory() as tmp:
        jpeg = make_jpeg(Path(tmp) / 'flafi.jpg')
        item = set_companion(welt, name='Flafi', foto=('flafi.jpg', jpeg.read_bytes(), 'image/jpeg'))
    assert item['foto_pfad']
    role(family)
    home = family[0].get('/').text
    assert f"/welten/foto/{item['foto_pfad']}" in home
    image = family[0].get(f"/welten/foto/{item['foto_pfad']}")
    assert image.status_code == 200
    assert image.headers['content-type'] == 'image/jpeg'


def test_interest_entries_are_kept_as_a_journal(welt):
    family, store = welt
    role(family)
    token = csrf_from(family[0].get('/welten').text)
    r1 = family[0].post('/welten/interesse', data={'_csrf': token, 'text': 'Dinosaurier'}, follow_redirects=False)
    assert r1.status_code == 303
    r2 = family[0].post('/welten/interesse', data={'_csrf': token, 'text': 'Fußball'}, follow_redirects=False)
    assert r2.status_code == 303
    assert store.current_interest()['text'] == 'Fußball'
    history = store.interest_history()
    assert [h['text'] for h in history] == ['Fußball', 'Dinosaurier']
    page = family[0].get('/welten').text
    assert 'Fußball' in page
    assert 'Dinosaurier' in page


def test_interest_requires_text_or_audio(welt):
    family, store = welt
    role(family)
    token = csrf_from(family[0].get('/welten').text)
    response = family[0].post('/welten/interesse', data={'_csrf': token, 'text': ''})
    assert response.status_code == 200
    assert store.current_interest() is None


def test_parent_can_also_set_up_the_companion(welt):
    # Der urspruengliche Wunsch war "das Kind KANN es aendern", nicht "nur
    # das Kind darf es aendern" — Eltern koennen beim Einrichten mithelfen,
    # ohne extra in den Kind-Modus wechseln zu muessen.
    family, store = welt
    role(family, 'parent')
    token = csrf_from(family[0].get('/welten').text)
    response = family[0].post('/welten/begleiter',
                              data={'_csrf': token, 'name': 'Flafi', 'farbe': 'lila'},
                              follow_redirects=False)
    assert response.status_code == 303
    assert store.current_companion()['name'] == 'Flafi'


def test_write_actions_require_csrf(welt):
    family, store = welt
    role(family)
    response = family[0].post('/welten/begleiter', data={'_csrf': 'ungueltig', 'name': 'Flafi', 'farbe': 'lila'})
    assert response.status_code == 403
    assert store.current_companion() is None


def test_old_worlds_missions_routes_are_gone(welt):
    family, store = welt
    role(family)
    assert family[0].get('/welten/interessen').status_code == 404
    assert family[0].get('/welten/album').status_code == 404


def test_parent_can_view_and_edit(welt):
    family, store = welt
    set_companion(welt, name='Flafi')
    role(family, 'parent')
    page = family[0].get('/welten')
    assert page.status_code == 200
    assert 'Begleiter ändern' in page.text
    assert 'Begleiter einrichten' not in page.text
