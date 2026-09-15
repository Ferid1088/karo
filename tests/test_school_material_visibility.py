"""Die Schulblätter lassen sich unabhängig von der Antwortprüfung zuordnen."""
import pytest

from .conftest import csrf_from, make_jpeg, run_jobs
from .test_app import einrichten, kind_modus_aktivieren


def test_school_material_moves_between_sections(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    for enabled in (False, True, False):
        app_env.config.update(schulblaetter_kind=enabled)
        assert ('<h2>Schulblätter</h2>' in client.get('/eltern').text) is not enabled
        for path in ('/', '/lernen?tab=neu', '/lernzyklus?tab=neu'):
            assert ('<h2>Schulblätter</h2>' in client.get(path).text) is enabled
    kind_modus_aktivieren(client)
    assert 'href="/wissen"' not in client.get('/').text
    app_env.config.update(schulblaetter_kind=True)
    for path in ('/', '/lernen?tab=neu', '/lernzyklus?tab=neu'):
        assert 'href="/wissen"' in client.get(path).text


@pytest.mark.parametrize('index,upload,scan,detail', [
    ('/wissen', '/wissen/upload', '/wissen/einlesen', '/wissen/{id}'),
    ('/vorbereitung', '/vorbereitung/schulmaterial/hochladen',
     '/vorbereitung/schulmaterial/einlesen', '/vorbereitung/schulmaterial/{id}'),
])
def test_child_can_use_school_material_only_when_enabled(
        client, fake_llm, fake_cli, app_env, tmp_path, index, upload, scan, detail):
    einrichten(client, fake_llm)
    kind_modus_aktivieren(client)
    token = csrf_from(client.get('/').text)
    for path in (index, detail.format(id=1), '/scan/1.jpg'):
        assert client.get(path, follow_redirects=False).status_code == 403
    for path in (upload, scan):
        assert client.post(path, data={'_csrf': token}).status_code == 403

    app_env.config.update(schulblaetter_kind=True)
    page = client.get(index)
    assert page.status_code == 200
    assert 'Deine Sammlung' in page.text
    assert 'href="/eltern"' not in page.text
    assert 'href="/lernen"' in page.text
    assert client.post(upload, data={'_csrf': 'invalid'}).status_code == 403
    assert client.post(scan, data={'_csrf': 'invalid'}).status_code == 403
    jpeg = make_jpeg(tmp_path / 'bruchrechnung.jpg')
    response = client.post(upload, data={
        '_csrf': token, 'themenname': 'Bruchrechnung', 'rolle': 'bearbeitet',
    }, files={'datei': ('bruchrechnung.jpg', jpeg.read_bytes(), 'image/jpeg')})
    assert response.status_code == 200
    doc = app_env.db.q1('SELECT * FROM document')
    assert doc['rolle'] == 'wissen'
    assert doc['themenname'] == 'Bruchrechnung'
    run_jobs(app_env, fake_llm)
    page = client.get(index)
    assert 'href="/themen' not in page.text
    assert 'Ein Erwachsener bestätigt' in page.text
    assert client.get(detail.format(id=doc['id'])).status_code == 200
    image = client.get(f"/scan/{doc['id']}.jpg")
    assert image.status_code == 200
    assert image.headers['content-type'] == 'image/jpeg'

    inbox = app_env.drive / '01_Eingang'
    inbox.mkdir(parents=True, exist_ok=True)
    make_jpeg(inbox / 'zweites-blatt.jpg', size=(1000, 1300))
    assert client.post(scan, data={'_csrf': token}).status_code == 200
    assert len(app_env.db.q('SELECT id FROM document')) == 2

    for path in ('/setup', '/eltern', '/themen', '/vorbereitung/inhalte',
                 '/vorbereitung/inhalte/sources', '/recherche'):
        assert client.get(path).status_code == 403
    assert client.post('/setup/finish', data={
        '_csrf': token, 'schulblaetter_kind': 'ja'}).status_code == 403
    # Die Schulblatt-Einstellung erlaubt weder Antwortfreigaben noch andere Dokumentrollen.
    assert client.post('/quiz/1/freigabe', data={'_csrf': token}).status_code == 403
    with app_env.db.tx() as c:
        c.execute("UPDATE document SET rolle='bearbeitet' WHERE id=?", (doc['id'],))
    assert client.get(detail.format(id=doc['id']), follow_redirects=False).status_code == 303
    assert client.get(f"/scan/{doc['id']}.jpg").status_code == 404
    app_env.config.update(schulblaetter_kind=False)
    assert client.get(index).status_code == 403
    assert client.get(f"/scan/{doc['id']}.jpg").status_code == 403
    assert client.post(upload, data={'_csrf': token}).status_code == 403
    assert client.post(scan, data={'_csrf': token}).status_code == 403
