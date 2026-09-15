"""Settings preserve values and keep connection actions separate from saving."""
from html.parser import HTMLParser
import pytest

from .conftest import csrf_from
from .test_app import einrichten
from .test_ui import Forms


class SettingsValues(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.fields = {}
        self.active = False
        self.select = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form':
            self.active = attrs.get('action') == '/setup/finish'
        if not self.active:
            return
        if tag == 'input' and attrs.get('name'):
            if attrs.get('type') == 'checkbox' and 'checked' not in attrs:
                return
            self.fields[attrs['name']] = attrs.get('value', '')
        if tag == 'select':
            self.select = {'name': attrs['name'], 'first': None, 'selected': None}
        if tag == 'option' and self.select:
            if self.select['first'] is None:
                self.select['first'] = attrs.get('value', '')
            if 'selected' in attrs:
                self.select['selected'] = attrs.get('value', '')

    def handle_endtag(self, tag):
        if tag == 'select' and self.select:
            value = self.select['selected']
            self.fields[self.select['name']] = self.select['first'] if value is None else value
            self.select = None
        if tag == 'form':
            self.active = False


def test_settings_has_one_place_for_each_connection(client, fake_llm, fake_cli):
    einrichten(client, fake_llm)
    page = client.get('/setup')
    forms = Forms(page.text).forms
    assert sum(f['action'] == '/setup/notebooklm/anmelden' for f in forms) == 1
    assert sum(f['action'] == '/setup/claude/verbinden' for f in forms) == 1
    assert sum(f['action'] == '/setup/finish' for f in forms) == 1
    assert page.text.count('name="default_ausgabe"') == 1
    assert 'data-settings-form' in page.text
    assert 'Knopf weiter unten' not in page.text


def test_saving_one_setting_preserves_collapsed_controls(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    app_env.config.update(header_crop_percent=17, max_lernrunden=6, recherche_erlaubt=False,
                          antworten_pruefen_kind=True, schulblaetter_kind=True,
                          klassenarbeit_kind=True)
    before = app_env.config.load()
    page = client.get('/setup')
    data = SettingsValues(page.text).fields
    assert data['header_crop'] == '17'
    data['max_lernrunden'] = '5'
    response = client.post('/setup/finish', data=data, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'] == '/setup'
    cfg = app_env.config.load()
    assert cfg.max_lernrunden == 5
    for key in ('header_crop_percent', 'recherche_erlaubt', 'model_text', 'model_vision',
                'default_ausgabe', 'tts_stimme', 'app_password_hash',
                'antworten_pruefen_kind', 'schulblaetter_kind', 'klassenarbeit_kind'):
        assert getattr(cfg, key) == getattr(before, key), key


def test_failed_password_change_keeps_unsaved_preferences(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    page = client.get('/setup')
    data = SettingsValues(page.text).fields
    data.update(max_lernrunden='7', header_crop='12', recherche='nein',
                antworten_pruefen_kind='ja', schulblaetter_kind='ja', klassenarbeit_kind='ja',
                password='neues-passwort', password2='anderes-passwort')
    response = client.post('/setup/finish', data=data)
    assert response.status_code == 400
    returned = SettingsValues(response.text).fields
    assert returned['max_lernrunden'] == '7'
    assert returned['header_crop'] == '12'
    assert returned['recherche'] == 'nein'
    assert returned['antworten_pruefen_kind'] == 'ja'
    assert app_env.config.load().antworten_pruefen_kind is False
    assert returned['schulblaetter_kind'] == 'ja'
    assert app_env.config.load().schulblaetter_kind is False
    assert returned['klassenarbeit_kind'] == 'ja'
    assert app_env.config.load().klassenarbeit_kind is False
    assert returned['password'] == returned['password2'] == ''
    assert app_env.config.load().max_lernrunden != 7
    assert 'data-invalid="true"' in response.text


def test_settings_save_does_not_reopen_google_login(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app.media import notebooklm
    einrichten(client, fake_llm)
    app_env.config.update(default_ausgabe='notebooklm')
    monkeypatch.setattr(notebooklm, 'verfuegbar', lambda: (True, 'Verbunden'))
    def unexpected_login():
        raise AssertionError('Saving preferences must not reopen Google login')
    monkeypatch.setattr(notebooklm, 'login_start', unexpected_login)
    page = client.get('/setup')
    data = SettingsValues(page.text).fields
    data['max_lernrunden'] = '5'
    response = client.post('/setup/finish', data=data, follow_redirects=False)
    assert response.headers['location'] == '/setup'


def test_disconnected_claude_keeps_settings_available(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    app_env.config.update(claude_oauth_token='', anthropic_api_key='')
    page = client.get('/setup')
    assert 'data-settings-form' in page.text
    assert 'action="/setup/credentials"' not in page.text
    assert 'action="/setup/claude/verbinden"' in page.text


CHILD_SETTINGS = ['antworten_pruefen_kind', 'schulblaetter_kind', 'klassenarbeit_kind']


@pytest.mark.parametrize('field', CHILD_SETTINGS)
def test_child_checkbox_can_be_enabled_and_disabled(client, fake_llm, fake_cli, app_env, field):
    einrichten(client, fake_llm)
    others = [key for key in CHILD_SETTINGS if key != field]
    app_env.config.update(**{key: True for key in others})
    assert getattr(app_env.config.load(), field) is False
    data = SettingsValues(client.get('/setup').text).fields
    assert field not in data
    data[field] = 'ja'
    assert client.post('/setup/finish', data=data, follow_redirects=False).status_code == 303
    assert getattr(app_env.config.load(), field) is True
    data = SettingsValues(client.get('/setup').text).fields
    assert data.pop(field) == 'ja'
    assert client.post('/setup/finish', data=data, follow_redirects=False).status_code == 303
    assert getattr(app_env.config.load(), field) is False
    assert all(getattr(app_env.config.load(), key) is True for key in others)
