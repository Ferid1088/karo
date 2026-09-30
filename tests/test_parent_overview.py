"""Parent overview facts, access, and responsive UI on isolated fixture data."""
from urllib.parse import urlsplit

import pytest

from .test_app import einrichten, kind_modus_aktivieren
from .conftest import csrf_from


def seed(app_env, monkeypatch):
    db = app_env.db
    monkeypatch.setattr(db, 'today', lambda: '2026-09-28')
    with db.tx() as c:
        for i, (subject, state, visible, removed, learned, merged) in enumerate([
            ('mathematik', 'aktiv', 1, None, None, None),
            ('englisch', 'aktiv', 1, None, None, None),
            ('mathematik', 'aktiv', 0, None, None, None),  # exam only
            ('mathematik', 'aktiv', 1, '2026-09-27', None, None),
            ('mathematik', 'aktiv', 1, None, '2026-09-27', None),
            ('biologie', 'aktiv', 1, None, None, None),
            ('mathematik', 'vorschlag', 1, None, None, None),
            ('mathematik', 'aktiv', 1, None, None, 1),
        ], 1):
            c.execute('''INSERT INTO topic
                (id,subject,code,label,state,learning_visible,deleted_at,learned_at,merged_into,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)''',
                (i, subject, f'parent.{i}', f'Thema {i}', state, visible, removed, learned, merged, db.now()))
        for i, subject, date, deleted in [
            (1, 'mathematik', '2026-10-04', None),
            (2, 'englisch', '2026-09-28', None),
            (3, 'mathematik', '2026-09-29', '2026-09-27'),
            (4, 'mathematik', '2026-09-27', None),
            (5, 'biologie', '2026-09-29', None),
        ]:
            c.execute('INSERT INTO exam(id,subject,exam_date,deleted_at,created_at) VALUES(?,?,?,?,?)',
                      (i, subject, date, deleted, db.now()))
        c.execute('INSERT INTO exam_topic(exam_id,topic_id,position) VALUES(1,3,0)')


def test_facts_are_read_only_and_keep_learning_separate(client, fake_llm, fake_cli, app_env, monkeypatch):
    einrichten(client, fake_llm)
    seed(app_env, monkeypatch)
    from app.services.parent_overview import summary
    before = [dict(row) for row in app_env.db.q('SELECT * FROM topic')]
    calls = len(fake_llm.calls)
    facts = summary()
    assert facts['personal_topics'] == 2
    assert facts['upcoming_exams'] == 2
    assert facts['next_exam']['id'] == 2
    assert facts['next_exam']['date_label'] == '28.09.2026'
    assert facts['next_exam']['days'] == 0
    assert [dict(row) for row in app_env.db.q('SELECT * FROM topic')] == before
    assert len(fake_llm.calls) == calls
    assert not app_env.db.q('SELECT * FROM job')
    with app_env.db.tx() as c:
        c.execute('UPDATE topic SET purged_at=? WHERE id=2', (app_env.db.now(),))
        c.execute('UPDATE exam SET purged_at=? WHERE id=2', (app_env.db.now(),))
    assert summary()['personal_topics'] == 1
    assert summary()['upcoming_exams'] == 1
    assert summary()['next_exam']['id'] == 1


def test_empty_overview_access_and_existing_tools(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    response = client.get('/eltern')
    assert response.status_code == 200
    # Nothing to do: no attention card at all, the report says what is missing.
    assert 'parent-attention' not in response.text
    assert 'Keine Klassenarbeit eingetragen.' in response.text
    # Header already has Hell/Dunkel and Abmelden; the page does not repeat them.
    assert response.text.count('action="/logout"') == 1
    # "Meine Welt" fuehrt fuer Eltern auf ihre Verwaltungsseite, nicht in
    # den Bereich des Kindes.
    for path in ['/themen', '/wissen', '/klassenarbeit', '/setup', '/woche/eltern',
                 '/welten/eltern', '/recherche', '/messung/fortschritt#ausfuehrlich', '/protokoll']:
        assert f'href="{path}"' in response.text
    # Optional child access must not hide useful parent entry points.
    app_env.config.update(schulblaetter_kind=True, klassenarbeit_kind=True)
    assert 'href="/wissen"' in client.get('/eltern').text
    assert 'href="/klassenarbeit"' in client.get('/eltern').text
    kind_modus_aktivieren(client)
    assert client.get('/eltern').status_code == 403


def test_retry_stays_in_parent_area_and_requires_csrf(client, fake_llm, fake_cli, monkeypatch):
    einrichten(client, fake_llm)
    from app.routers import eltern
    retried = []
    monkeypatch.setattr(eltern.jobs, 'retry', lambda job_id: retried.append(job_id) or True)
    assert client.post('/vorgang/123/erneut', data={}).status_code == 403
    page = client.get('/eltern')
    response = client.post('/vorgang/123/erneut', data={'_csrf': csrf_from(page.text)}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'] == '/eltern#betrieb'
    assert retried == [123]
    kind_modus_aktivieren(client)
    assert client.post('/vorgang/123/erneut', data={'_csrf': csrf_from(client.get('/').text)}).status_code == 403
    assert retried == [123]


def test_mobile_desktop_themes_and_disclosures(client, fake_llm, fake_cli, app_env, monkeypatch, tmp_path):
    pw = pytest.importorskip('playwright.sync_api')
    einrichten(client, fake_llm)
    seed(app_env, monkeypatch)
    from app.routers import dashboard
    monkeypatch.setattr(dashboard.jobs, 'counts', lambda: {'fehler': 1})
    monkeypatch.setattr(dashboard.jobs, 'fehlgeschlagen', lambda: [
        {'id': 999, 'last_error': 'Testfehler', 'type': 'test_job'}])
    from app.services import grade_guidance
    monkeypatch.setattr(grade_guidance, 'unread', lambda: [dict(
        id=999, topic_label='Brüche mit verschiedenen Nennern addieren',
        profile_grade=1, grade_from=5, grade_to=6, area='/lernen/adaptiv',
        created_at='2026-09-28T12:00:00')])
    with pw.sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel='chrome', headless=True)
        except pw.Error as exc:
            pytest.skip(f'Chrome nicht verfügbar: {exc}')
        page = browser.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))

        def serve(route):
            request = route.request
            url = urlsplit(request.url)
            if url.hostname != 'karo.test':
                return route.abort()
            response = client.request(request.method, url.path + ('?' + url.query if url.query else ''),
                content=request.post_data_buffer,
                headers={'Content-Type': request.headers.get('content-type', '')})
            route.fulfill(status=response.status_code, body=response.content,
                          content_type=response.headers.get('content-type', 'text/plain'))

        page.route('**/*', serve)
        for width in [375, 768, 1024, 1440]:
            page.set_viewport_size({'width': width, 'height': 1000})
            page.goto('http://karo.test/eltern')
            assert page.get_by_role('heading', name='Alles Wichtige im Blick').is_visible()
            assert page.get_by_role('heading', name='Neue Hinweise zum Lernen').is_visible()
            assert not page.locator('#familie').evaluate('(el) => el.open')
            page.locator('.parent-management > summary').click()
            for theme in ['karo', 'sand', 'nacht']:
                appearance = page.locator('.parent-details').last
                appearance.locator('summary').click()
                if theme == 'nacht':  # dark is the header switch, not a palette
                    page.get_by_role('button', name='Dunkel').click()
                else:
                    page.locator('#eltern-farbwelt').select_option(theme)
                assert page.locator('html').get_attribute('data-theme-color') == theme
                appearance.locator('summary').click()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=str(tmp_path / f'parent-{width}-{theme}.png'), full_page=True)
            # Native disclosures support keyboard and all secondary actions stay reachable.
            summary = page.locator('#familie > summary')
            summary.focus()
            summary.press('Enter')
            assert page.get_by_role('link', name='Vereinbarung und Hilfe öffnen').is_visible()
            assert page.get_by_role('link', name='Meine Welt verwalten', exact=True).is_visible()
            summary.press('Enter')
            page.locator('.parent-task-list a[href="#betrieb"]').click()
            page.wait_for_function("document.getElementById('betrieb').open")
            assert page.get_by_role('button', name='Erneut versuchen').is_visible()
            assert page.get_by_text('Testfehler', exact=True).is_hidden()
            page.get_by_text('Fehlerdetails ansehen', exact=True).click()
            assert page.get_by_text('Testfehler', exact=True).is_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors
        # Main functions are server-rendered; no JavaScript required for disclosures.
        plain = browser.new_context(java_script_enabled=False, reduced_motion='reduce')
        plain_page = plain.new_page()
        plain_page.route('**/*', serve)
        plain_page.goto('http://karo.test/eltern')
        plain_page.locator('.parent-management > summary').click()
        plain_page.locator('#familie > summary').click()
        assert plain_page.get_by_role('link', name='Vereinbarung und Hilfe öffnen').is_visible()
        print(f'Eltern-Layout: {tmp_path}')
        browser.close()
