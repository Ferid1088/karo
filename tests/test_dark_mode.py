"""Hell / Dunkel / Automatisch im Elternbereich: nur im Browser gespeichert, vor dem ersten Zeichnen."""
from urllib.parse import urlsplit

import pytest

from .test_app import einrichten, kind_modus_aktivieren


def test_switch_only_in_parent_area(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    html = client.get('/eltern').text
    for mode in ('hell', 'auto', 'dunkel'):
        assert f'data-modus="{mode}"' in html
    assert 'id="eltern-modus"' not in html  # one switch only: the header
    assert html.index('/static/themes.js') < html.index('/static/karo.css')  # applied before first paint
    kind_modus_aktivieren(client)
    assert 'data-modus=' not in client.get('/').text


def test_browser_mode_switch_follows_device_and_persists(client, fake_llm, fake_cli, app_env, tmp_path):
    pw = pytest.importorskip('playwright.sync_api')
    einrichten(client, fake_llm)
    with pw.sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel='chrome', headless=True)
        except pw.Error as exc:
            pytest.skip(f'Chrome nicht verfügbar: {exc}')
        errors = []

        def serve(route):
            req = route.request
            url = urlsplit(req.url)
            if url.hostname != 'karo.test':
                return route.abort()
            response = client.request(req.method, url.path + ('?' + url.query if url.query else ''),
                                      content=req.post_data_buffer,
                                      headers={'Content-Type': req.headers.get('content-type', '')})
            route.fulfill(status=response.status_code, body=response.content,
                          content_type=response.headers.get('content-type', 'text/plain'))

        context = browser.new_context(color_scheme='light')
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('**/*', serve)
        html = page.locator('html')
        page.goto('http://karo.test/eltern')
        assert html.get_attribute('data-theme-mode') == 'auto' and html.get_attribute('data-theme-color') == 'karo'
        assert page.locator('[data-modus="auto"]').get_attribute('aria-pressed') == 'true'
        page.emulate_media(color_scheme='dark')  # "Automatisch" follows the device live
        page.wait_for_function("document.documentElement.dataset.themeColor === 'nacht'")
        page.emulate_media(color_scheme='light')
        page.wait_for_function("document.documentElement.dataset.themeColor === 'karo'")
        page.get_by_role('button', name='Dunkel').click()
        assert html.get_attribute('data-theme-color') == 'nacht'
        assert page.locator('[data-modus="dunkel"]').get_attribute('aria-pressed') == 'true'
        assert page.evaluate("getComputedStyle(document.documentElement).colorScheme") == 'dark'
        page.screenshot(path=str(tmp_path / 'eltern-dunkel.png'), full_page=True)
        page.reload()  # the choice survives a reload and wins over the device setting
        assert html.get_attribute('data-theme-color') == 'nacht'
        page.locator('.parent-management > summary').click()
        page.locator('.parent-details').last.locator('summary').click()
        assert page.locator('#eltern-farbwelt').input_value() == 'karo'  # light palette stays listed
        page.locator('#eltern-farbwelt').select_option('sand')  # a light palette is an explicit "Hell"
        assert html.get_attribute('data-theme-color') == 'sand' and html.get_attribute('data-theme-mode') == 'hell'
        page.emulate_media(color_scheme='dark')
        assert html.get_attribute('data-theme-color') == 'sand'
        page.get_by_role('button', name='Automatisch wie das Gerät').click()
        page.wait_for_function("document.documentElement.dataset.themeColor === 'nacht'")
        page.emulate_media(color_scheme='light')
        page.wait_for_function("document.documentElement.dataset.themeColor === 'sand'")  # own light palette kept
        page.get_by_role('button', name='Hell').click()
        assert page.locator('[data-modus="hell"]').get_attribute('aria-pressed') == 'true'
        for width in (375, 768, 1280):
            page.set_viewport_size({'width': width, 'height': 900})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        # Older installs saved "schiefer" (now karo) or "Nachtblau" (stays dark).
        older = browser.new_context(color_scheme='light')
        was = older.new_page()
        was.route('**/*', serve)
        was.add_init_script("localStorage.setItem('karo-farbwelt-parent','schiefer')")
        was.goto('http://karo.test/eltern')
        assert was.locator('html').get_attribute('data-theme-color') == 'karo'
        legacy = browser.new_context(color_scheme='light')
        old = legacy.new_page()
        old.route('**/*', serve)
        old.add_init_script("localStorage.setItem('karo-farbwelt-parent','nacht')")
        old.goto('http://karo.test/eltern')
        assert old.locator('html').get_attribute('data-theme-color') == 'nacht'
        assert old.locator('html').get_attribute('data-theme-mode') == 'dunkel'
        assert not errors
        browser.close()
