"""Storage selections use real server paths without changing settings prematurely."""
import pytest

from .conftest import csrf_from
from .test_app import einrichten, kind_modus_aktivieren
from .test_settings import SettingsValues


def test_choose_and_save_storage(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    folder = app_env.drive / 'Schule & Lernen' / 'Mathe'
    folder.mkdir(parents=True)
    page = client.get('/setup')
    data = SettingsValues(page.text).fields
    listing = client.get('/setup/speicher/ordner', params={
        'kind': 'material', 'root': 'drive', 'relative': 'Schule & Lernen'}).json()
    assert listing['folders'] == ['Mathe']
    for kind, field in [('material', 'drive_unterordner'), ('database', 'material_db_path')]:
        response = client.post('/setup/speicher/auswaehlen', data={
            '_csrf': csrf_from(page.text), 'kind': kind, 'root': 'drive',
            'relative': 'Schule & Lernen/Mathe', 'filename': 'lernen.sqlite3'})
        assert response.status_code == 200
        data[field] = response.json()['value']
    assert app_env.config.load().drive_subdir == ''
    assert not (folder / 'lernen.sqlite3').exists()
    assert client.post('/setup/finish', data=data, follow_redirects=False).status_code == 303
    assert app_env.config.drive_root() == folder
    assert app_env.config.load().material_db_path == str(folder / 'lernen.sqlite3')
    assert (folder / 'lernen.sqlite3').exists()


@pytest.mark.parametrize('relative', ['../data', '/etc', 'outside'])
def test_folder_escape_rejected(client, fake_llm, fake_cli, app_env, relative):
    einrichten(client, fake_llm)
    (app_env.drive / 'outside').symlink_to(app_env.data, target_is_directory=True)
    response = client.get('/setup/speicher/ordner', params={
        'kind': 'material', 'root': 'drive', 'relative': relative})
    assert response.status_code == 400
    response = client.post('/setup/speicher/auswaehlen', data={
        '_csrf': csrf_from(client.get('/setup').text), 'kind': 'material',
        'root': 'drive', 'relative': relative})
    assert response.status_code == 400


def test_existing_database_and_invalid_filename_rejected(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    (app_env.drive / 'existing.db').write_text('keep')
    token = csrf_from(client.get('/setup').text)
    for filename in ['existing.db', '../outside.db', 'bad.txt']:
        response = client.post('/setup/speicher/auswaehlen', data={
            '_csrf': token, 'kind': 'database', 'root': 'drive', 'filename': filename})
        assert response.status_code == 400
    assert (app_env.drive / 'existing.db').read_text() == 'keep'


def test_storage_requires_parent_and_csrf(client, fake_llm, fake_cli):
    einrichten(client, fake_llm)
    assert client.post('/setup/speicher/auswaehlen', data={
        'kind': 'material', 'root': 'drive'}).status_code == 403
    kind_modus_aktivieren(client)
    assert client.get('/setup/speicher/ordner?kind=material').status_code == 403
    assert client.post('/setup/speicher/auswaehlen', data={
        'kind': 'material', 'root': 'drive'}).status_code == 403
