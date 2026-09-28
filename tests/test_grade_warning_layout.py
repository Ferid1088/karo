"""Optional browser QA against isolated TestClient data, never the live app."""
from urllib.parse import urlsplit

import pytest

from .test_grade_guidance import setup


def test_warning_is_readable_on_phone_and_desktop(client, fake_llm, fake_cli, app_env, tmp_path):
    pw = pytest.importorskip('playwright.sync_api')
    tid, token = setup(client, fake_llm, app_env)
    warning = client.post('/lernen/adaptiv/start', data={'_csrf': token, 'topic_id': tid}).text
    with pw.sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel='chrome', headless=True)
        except pw.Error as exc:
            pytest.skip(f'Chrome für Layoutprüfung nicht verfügbar: {exc}')
        page = browser.new_page()

        def serve(route):
            path = urlsplit(route.request.url).path
            if path == '/preview':
                route.fulfill(status=200, content_type='text/html', body=warning)
            elif path.startswith('/static/'):
                response = client.get(path)
                route.fulfill(status=response.status_code,
                              content_type=response.headers.get('content-type', 'text/plain'), body=response.content)
            else:
                route.abort()

        page.route('**/*', serve)
        for width in [375, 768, 1440]:
            page.set_viewport_size({'width': width, 'height': 900})
            page.goto('http://karo.test/preview')
            page.get_by_role('heading', name='Möchtest du dieses Thema ausprobieren?').wait_for()
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            button = page.get_by_role('button', name='Ja, trotzdem lernen')
            assert button.is_visible()
            button.focus()
            assert button.evaluate('(element) => document.activeElement === element')
            assert page.get_by_role('link', name='Zurück').is_visible()
            page.screenshot(path=str(tmp_path / f'warning-{width}.png'), full_page=True)
        print(f'Layout-Screenshots: {tmp_path}')
        browser.close()
