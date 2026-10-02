"""Prepared-topic search: real browser, isolated app data, no live app writes."""
from urllib.parse import urlsplit

import pytest

from .conftest import csrf_from
from .test_app import einrichten

FRACTIONS = 'Brüche mit verschiedenen Nennern addieren'


def prepare(client, fake_llm):
    einrichten(client, fake_llm)
    from app.adaptiv import store
    store.konzept_sichern('mathematik', 'geometrie', 'quader', 'Quader: Volumen berechnen',
                         5, 7, geprueft=True)
    store.konzept_sichern('englisch', 'grammar', 'present', 'Simple present', 5, 7, geprueft=True)
    return client.get('/lernen/neu?fach=mathematik')


def test_native_dropdown_uses_scoped_catalog_and_existing_post(client, fake_llm, app_env):
    response = prepare(client, fake_llm)
    assert '<select id="catalog-topic" name="thema" required' in response.text
    assert FRACTIONS in response.text and 'Quader: Volumen berechnen' in response.text
    assert 'Simple present' not in response.text
    assert 'catalog-button' not in response.text
    assert 'Diese Lernreihen sind schon vorbereitet.' not in response.text
    result = client.post('/lernen/neu', data={'_csrf': csrf_from(response.text),
                         'thema': FRACTIONS, 'fach': 'mathematik'})
    assert result.status_code == 200 and 'Deine Profilklasse' in result.text
    assert app_env.db.q1('SELECT label FROM topic WHERE label=?', FRACTIONS)


def test_empty_catalog_keeps_custom_topic_form(client, fake_llm, app_env):
    einrichten(client, fake_llm)
    response = client.get('/lernen/neu?fach=deutsch')
    assert 'Noch kein vorbereitetes Thema' in response.text
    assert 'id="new-topic"' in response.text
    assert 'id="catalog-topic"' not in response.text


def test_search_keyboard_mobile_and_submit(client, fake_llm, app_env, tmp_path):
    pw = pytest.importorskip('playwright.sync_api')
    prepare(client, fake_llm)
    with pw.sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel='chrome', headless=True)
        except pw.Error as exc:
            pytest.skip(f'Chrome für Layoutprüfung nicht verfügbar: {exc}')
        page = browser.new_page()
        posted = []
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))

        def serve(route):
            request = route.request
            url = urlsplit(request.url)
            if url.hostname != 'karo.test':
                return route.abort()
            # Der Lernzeit-Herzschlag laeuft auf jeder Lernseite und ist keine
            # Formularabsendung — dieser Test schaut nur auf Absendungen.
            if request.method == 'POST' and url.path != '/lernen/zeit':
                posted.append(request.post_data)
            response = client.request(request.method, url.path + ('?' + url.query if url.query else ''),
                content=request.post_data_buffer,
                headers={'Content-Type': request.headers.get('content-type', '')})
            route.fulfill(status=response.status_code, body=response.content,
                          content_type=response.headers.get('content-type', 'text/plain'))

        page.route('**/*', serve)
        for width in [375, 768, 1024, 1440]:
            page.set_viewport_size({'width': width, 'height': 960})
            page.goto('http://karo.test/lernen/neu?fach=mathematik')
            search = page.get_by_role('combobox', name='Thema suchen')
            trigger = page.locator('.topic-dropdown-trigger')
            select = page.locator('#catalog-topic')
            button = page.get_by_role('button', name='Ausgewähltes Thema hinzufügen')
            trigger.wait_for(state='visible')
            assert button.is_disabled()
            assert search.is_hidden()
            # Disabled text must remain readable, not inherit faded opacity.
            contrast = button.evaluate('''element => {
                const style = getComputedStyle(element);
                const luminance = color => {
                    const rgb = color.match(/[0-9.]+/g).slice(0,3).map(Number).map(v => {
                        v /= 255; return v <= .04045 ? v/12.92 : ((v+.055)/1.055)**2.4;
                    });
                    return .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2];
                };
                const a=luminance(style.color), b=luminance(style.backgroundColor);
                return {opacity:style.opacity, color:style.color, background:style.backgroundColor,
                        ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
            }''')
            assert contrast['opacity'] == '1' and contrast['ratio'] >= 4.5, contrast
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            page.locator('.topic-catalog').screenshot(path=str(tmp_path / f'picker-closed-{width}.png'))
            trigger.click()
            assert search.is_visible()
            assert page.get_by_role('option').count() == 2
            assert search.evaluate('(element) => document.activeElement === element')
            page.locator('.topic-catalog').screenshot(path=str(tmp_path / f'picker-open-{width}.png'))
            # Direct selection without searching.
            page.get_by_role('option', name='Quader: Volumen berechnen', exact=True).click()
            assert select.input_value() == 'Quader: Volumen berechnen'
            assert search.is_hidden() and button.is_enabled()
            trigger.click()
            search.fill('BRUECHE nennern')
            assert page.get_by_role('option').count() == 1
            assert '1 Thema zur Auswahl' in page.locator('#catalog-results').inner_text()
            search.press('ArrowDown')
            assert search.get_attribute('aria-activedescendant')
            search.press('Enter')
            assert trigger.evaluate('(element) => document.activeElement === element')
            assert select.input_value() == FRACTIONS and search.is_hidden()
            assert button.is_enabled()
            assert FRACTIONS in trigger.inner_text()
            assert button.evaluate('(element) => getComputedStyle(element).color') == 'rgb(255, 255, 255)'
            trigger.click()
            search.fill('kein-passendes-thema-xyz')
            assert page.get_by_role('option').count() == 0
            assert 'Kein Thema gefunden' in page.locator('#catalog-results').inner_text()
            search.press('Enter')
            assert search.is_visible() and select.input_value() == FRACTIONS
            search.fill('')
            assert page.get_by_role('option').count() == 2
            search.press('Escape')
            assert search.is_hidden()
            trigger.click()
            search.press('Tab')
            assert search.is_hidden()
            trigger.click()
            page.get_by_role('heading', name='Ein Thema aussuchen').click()
            assert search.is_hidden()
        assert posted == []  # Choosing a topic does not automatically submit it.
        button.click()
        page.get_by_role('heading', name=FRACTIONS, exact=True).wait_for()
        assert len(posted) == 1 and 'fach=mathematik' in posted[0]
        assert not errors
        # Without JavaScript the complete native dropdown remains usable.
        plain = browser.new_context(java_script_enabled=False)
        plain_page = plain.new_page()
        plain_page.route('**/*', serve)
        plain_page.goto('http://karo.test/lernen/neu?fach=mathematik')
        assert plain_page.locator('#catalog-topic').is_visible()
        assert plain_page.locator('#catalog-toggle').is_hidden()
        assert plain_page.locator('#catalog-search').is_hidden()
        print(f'Layout-Screenshots: {tmp_path}')
        browser.close()
