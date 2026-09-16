"""Acceptance tests for the replacement pilot (the old prototype contract is retired)."""
from datetime import date, datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor

import pytest
from .conftest import csrf_from
from .test_app import einrichten, session_cookie_faelschen


@pytest.fixture
def family(client, app_env, fake_llm, fake_cli, monkeypatch):
    password = einrichten(client, fake_llm)
    from app.woche import pilot, pilot_store
    monkeypatch.setattr(pilot, 'today', lambda now=None: date(2026, 9, 15))
    return client, app_env, pilot, pilot_store, password


def role(family, value='child'):
    client, env, *_ = family
    session = {'auth': True, 'csrf': 'test-token'}
    if value is not None:
        session['role'] = value
    cookie = session_cookie_faelschen(env, **session)
    client.cookies.clear()
    client.cookies.set('karo_session', cookie)


def post(family, path, data=None, expected=303):
    client = family[0]
    token = csrf_from(client.get('/woche').text)
    response = client.post(path, data={'_csrf': token, **(data or {})}, follow_redirects=False)
    assert response.status_code == expected, response.text[:1200]
    return response


def create(family, **changes):
    store = family[3]
    role(family, 'parent')
    existing = store.get()
    values = {'week': '2026-09-14', 'version': existing['version'] if existing else 0,
              'goal': 'Meinen Referatseinstieg sicher erzählen.', 'step': 'Öffne deine Notizen und lies den ersten Satz laut.',
              'routine': '', 'promise': 'Ich höre dir zehn Minuten zu.', 'discussed': 'ja'}
    values.update(changes)
    post(family, '/woche/eltern/plan', values)
    role(family)
    return store.get()


def activity(family, action, selected='goal', expected=303, **extra):
    p = family[3].get()
    return post(family, '/woche/aktivitaet', {'plan_id': p['id'], 'revision': p['revision'],
                'day': str(family[2].today()), 'activity': selected, 'action': action, **extra}, expected)


def status(family, action, expected=303, **extra):
    p = family[3].get()
    return post(family, '/woche/status', {'plan_id': p['id'], 'version': p['version'], 'action': action, **extra}, expected)


def test_parent_agreement_child_and_dashboard(family):
    create(family)
    assert 'Meinen Referatseinstieg' in family[0].get('/woche').text
    status(family, 'change')
    role(family, 'parent')
    html = family[0].get('/eltern').text
    assert 'Ihr Kind bittet um eine Änderung' in html and 'Noch keine Rückmeldung' in html
    assert 'Meine Woche' in family[0].get('/').text
    assert 'data-ui-area="parent"' in family[0].get('/woche/eltern').text


@pytest.mark.parametrize('values', [dict(step='', promise=''), dict(goal='', step='', routine='An meinem Projekt arbeiten', days=['2','4'], promise=''), dict(goal='', step='')])
def test_optional_components(family, values):
    create(family, **values)
    assert family[0].get('/woche').status_code == 200


@pytest.mark.parametrize('changes', [dict(goal='',step='',promise=''), dict(discussed=''), dict(goal='x'*161), dict(routine='Routine',days=['8']), dict(routine='Routine'), dict(promise_day='2',promise_time='25:01'),dict(step='Einstieg',goal='')])
def test_invalid_agreements_are_not_saved(family, changes):
    role(family, 'parent')
    post(family, '/woche/eltern/plan', {'week':'2026-09-14','version':0,'goal':'Ziel','step':'Schritt','promise':'Zusage','discussed':'ja',**changes}, 400)
    assert family[3].get() is None


def test_get_does_not_create_plan_or_business_events(family):
    tables = ('woche_plan', 'woche_feedback', 'woche_help')
    before = {t: family[1].db.q(f'SELECT * FROM {t}') for t in tables}
    for path in ('/woche','/woche/eltern','/eltern'):
        assert family[0].get(path).status_code == 200
    assert family[3].get() is None
    assert {t: family[1].db.q(f'SELECT * FROM {t}') for t in tables} == before


def test_no_login_and_invalid_roles(family):
    client = family[0]
    client.cookies.clear()
    for path in ('/woche','/woche/eltern'):
        assert client.get(path, follow_redirects=False).headers['location'] == '/login'
    for value in (None, '', 'unknown'):
        role(family, value)
        assert client.get('/woche/eltern', follow_redirects=False).headers['location'] == '/login'
        role(family, value)
        assert client.post('/woche/eltern/plan', data={'_csrf':'test-token'}, follow_redirects=False).headers['location'] == '/login'


def test_child_cannot_manage_or_impersonate_parent(family):
    create(family)
    assert family[0].get('/woche/eltern').status_code == 403
    post(family, '/woche/eltern/plan', {}, 403)
    post(family, '/woche/eltern/hilfe/1', {'status':'erledigt','version':1}, 403)
    assert family[0].get('/woche?child_id=2').status_code == 403
    post(family, '/woche/status', {'child_id':2}, 403)
    post(family, '/woche/status', {'plan_id':999, 'version':1,'action':'pause'}, 404)
    post(family, '/woche/hilfe/999/zuruecknehmen', {'version':1}, 404)
    role(family, 'parent')
    post(family, '/woche/eltern/hilfe/999', {'version':1,'status':'zugesagt'}, 404)
    assert family[0].get('/woche/eltern?copy=999').status_code == 404


def test_start_success_duplicate_and_goal_correction(family):
    create(family)
    activity(family, 'start', expected=200)
    assert not family[1].db.q('SELECT * FROM woche_feedback')
    activity(family, 'done')
    activity(family, 'done')
    assert len(family[1].db.q('SELECT * FROM woche_feedback')) == 1
    assert not family[3].get()['achieved']
    status(family, 'achieved')
    assert family[3].get()['achieved']
    status(family, 'unachieved')
    assert not family[3].get()['achieved']


def test_skip_today_undo_and_no_parent_signal(family, monkeypatch):
    create(family)
    activity(family, 'skip')
    assert 'Für heute ist hier nichts weiter vorgesehen' in family[0].get('/woche').text
    assert 'Doch starten' in family[0].get('/woche').text
    activity(family, 'undo')
    assert 'Loslegen' in family[0].get('/woche').text
    activity(family, 'skip')
    monkeypatch.setattr(family[2], 'today', lambda: date(2026,9,16))
    assert 'Loslegen' in family[0].get('/woche').text
    role(family, 'parent')
    html = family[0].get('/eltern').text
    assert 'Noch keine Rückmeldung' in html and 'Heute nicht' not in html and 'ausgeblendet' not in html


def test_routine_days_priority_and_no_catchup(family, monkeypatch):
    create(family, routine='Zehn Minuten Projekt', days=['2','4'])
    p = family[3].get()
    assert family[2].next_action(p, set(), [])['activity'] == 'routine'
    activity(family, 'done', selected='routine')
    assert family[2].next_action(p, family[3].feedback(p), [])['activity'] == 'goal'
    monkeypatch.setattr(family[2], 'today', lambda: date(2026,9,16))
    activity(family, 'done', selected='routine', expected=400)
    assert family[2].next_action(p, set(), [])['activity'] == 'goal'
    monkeypatch.setattr(family[2], 'today', lambda: date(2026,9,17))
    assert family[2].next_action(p, set(), [])['activity'] == 'routine'


def test_difficulty_private_and_only_one_simplification(family):
    create(family)
    response = activity(family, 'reason', expected=200, reason='schwer', message='PRIVATER GRUND')
    assert 'kleineren Einstieg einmal' in response.text
    response = activity(family, 'reason', expected=200, reason='anfang')
    assert 'kleineren Einstieg einmal' not in response.text
    assert 'PRIVATER GRUND' not in '\n'.join(family[1].db.conn().iterdump())
    role(family, 'parent')
    assert 'PRIVATER GRUND' not in family[0].get('/eltern').text


@pytest.mark.parametrize('reason', ['zeit','anders'])
def test_other_difficulty_choices(family, reason):
    create(family)
    result = activity(family, 'reason', expected=303 if reason == 'zeit' else 200, reason=reason)
    if reason == 'anders':
        assert 'Für heute aufhören' in result.text
    assert not family[1].db.q('SELECT * FROM woche_feedback')


def test_help_lifecycle_and_duplicate(family):
    create(family)
    activity(family, 'help', expected=200)
    assert not family[3].helps()
    for _ in range(2):
        activity(family, 'send_help', kind='zusammen', share='ja', message='Bitte zuhören')
    h = family[3].helps()[0]
    assert len(family[3].helps()) == 1
    assert family[2].next_action(family[3].get(),set(),[h])['kind'] == 'help'
    role(family,'parent')
    post(family, f"/woche/eltern/hilfe/{h['id']}", {'version':1,'status':'erledigt'}, 400)
    post(family, f"/woche/eltern/hilfe/{h['id']}", {'version':1,'status':'zugesagt','reply':'Gern','appointment':'2026-09-17T18:00'})
    assert family[3].helps()[0]['status'] == 'zugesagt'
    role(family)
    html = family[0].get('/woche').text
    assert 'Gern' in html and '18:00' in html
    role(family,'parent')
    post(family, f"/woche/eltern/hilfe/{h['id']}", {'version':2,'status':'erledigt'})
    role(family)
    assert 'Hilfe erledigt' in family[0].get('/woche').text
    activity(family, 'send_help', kind='sprechen', share='ja')
    h = family[3].helps()[0]
    post(family, f"/woche/hilfe/{h['id']}/zuruecknehmen", {'version':1})
    assert family[3].helps()[0]['status'] == 'zurueckgenommen'


def test_pause_overrides_help_keeps_promise(family):
    create(family)
    activity(family, 'send_help',kind='erklaeren',share='ja')
    status(family,'pause')
    assert family[2].next_action(family[3].get(),set(),family[3].helps()) is None
    html = family[0].get('/woche').text
    assert 'Ich höre dir' in html and 'Woche fortsetzen' in html
    activity(family,'done',expected=400)
    role(family,'parent')
    status(family,'resume')
    assert not family[3].get()['paused']


def test_plan_edit_resets_confirmation_and_stale_form_conflicts(family):
    p = create(family)
    status(family,'agree')
    create(family, routine='Projekt', days=['2'])
    assert family[3].get()['child_status'] == 'offen'
    role(family,'parent')
    post(family,'/woche/eltern/plan',{'week':p['week'],'version':p['version'],'goal':'Stale','discussed':'ja'},409)
    assert family[3].get()['goal'] != 'Stale'
    assert len(family[1].db.q('SELECT * FROM woche_plan')) == 1
    role(family)
    post(family,'/woche/aktivitaet',{'plan_id':p['id'],'revision':p['revision'],'day':'2026-09-15','activity':'goal','action':'done'},409)


def test_week_rollover_copy_only_content_and_old_help(family,monkeypatch):
    p = create(family)
    activity(family,'done')
    activity(family,'send_help',kind='erklaeren',share='ja')
    status(family,'agree')
    role(family,'parent')
    url = f"/woche/eltern?week=2026-09-21&copy={p['id']}"
    assert 'Meinen Referatseinstieg' in family[0].get(url).text
    assert family[3].get(date(2026,9,21)) is None  # draft GET does not write
    values = {k:p[k] for k in ('goal','step','routine','promise','promise_day','promise_time')}
    post(family,'/woche/eltern/plan',dict(values,week='2026-09-21',version=0,discussed='ja'))
    future = family[3].get(date(2026,9,21))
    assert future['child_status'] == 'offen' and not future['achieved'] and not family[3].helps(future['id'])
    monkeypatch.setattr(family[2],'today',lambda:date(2026,9,21))
    assert not family[3].feedback(future)
    assert 'Woche ab 2026-09-14' in family[0].get('/eltern').text
    h = family[3].helps()[0]
    post(family,f"/woche/eltern/hilfe/{h['id']}",{'version':1,'status':'zugesagt'})


def test_local_date_and_sunday_monday():
    from app.woche.pilot import today, monday
    assert today(datetime(2026,9,13,22,30,tzinfo=timezone.utc)) == date(2026,9,14)
    assert monday(date(2026,9,13)) == date(2026,9,7)
    assert monday(date(2026,9,14)) == date(2026,9,14)
    assert today(datetime(2026,3,29,22,30,tzinfo=timezone.utc)) == date(2026,3,30)


def test_migration_preserves_legacy_and_is_repeatable(family):
    from app.woche import store as legacy
    legacy.ensure()
    legacy.kind_setzen(name='ALT',klasse=8)
    c = family[1].db.conn()
    before = c.execute('SELECT * FROM woche_kind').fetchall()
    family[1].db.init(); family[1].db.init()
    assert c.execute('SELECT * FROM woche_kind').fetchall() == before
    assert family[3].get() is None
    p = create(family)
    family[1].db.init()
    assert family[3].get()['id'] == p['id']


def test_csrf_and_escaped_text_real_requests(family):
    create(family,goal='<script>alert(1)</script>')
    html = family[0].get('/woche').text
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html
    assert '<script>alert(1)</script>' not in html
    assert family[0].post('/woche/status',data={'action':'pause'}).status_code == 403
    token = csrf_from(html)
    assert family[0].post('/woche/status',data={'_csrf':token},headers={'origin':'https://evil.example','sec-fetch-site':'cross-site'}).status_code == 403
    assert not family[3].get()['paused']


def test_review_shared_not_inferred(family):
    create(family)
    status(family,'review',feeling='mittel',wish='leichter',together='ja')
    role(family,'parent')
    assert 'Gemeinsame Wochenrückmeldung: Ging so · Leichter' in family[0].get('/eltern').text


def test_no_learning_writes_or_ai_calls(family,fake_llm):
    db = family[1].db
    tables = ('topic','quiz','lesson','answer_log','llm_call','job')
    before = {t:[tuple(r) for r in db.q(f'SELECT * FROM {t}')] for t in tables}
    calls = len(fake_llm.calls)
    create(family)
    activity(family,'done')
    activity(family,'send_help',kind='sprechen',share='ja')
    assert {t:[tuple(r) for r in db.q(f'SELECT * FROM {t}')] for t in tables} == before
    assert len(fake_llm.calls) == calls


def test_parallel_completions_and_help_are_unique(family):
    p = create(family)
    def write(_):
        try:
            with family[1].db.tx():
                family[3].complete(p,'goal')
                family[3].request_help(p,'goal','sprechen','')
        finally:
            family[1].db._discard_connection()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(write,range(4)))
    assert len(family[1].db.q('SELECT * FROM woche_feedback')) == 1
    assert len(family[3].helps()) == 1


def test_double_plan_and_concurrent_create(family):
    rules, store = family[2:4]
    values = rules.agreement({'goal':'Ein eigenes Vorhaben','discussed':'ja'},[])
    def save(_):
        try:
            store.save(date(2026,9,14), values, 0)
            return 'saved'
        except store.Conflict:
            return 'conflict'
        finally:
            family[1].db._discard_connection()
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(save,range(2)))
    assert sorted(outcomes) == ['conflict','saved']
    role(family,'parent')
    post(family,'/woche/eltern/plan',dict(goal=values['goal'],week='2026-09-14',version=0,discussed='ja'),409)
    assert len(family[1].db.q('SELECT * FROM woche_plan')) == 1


def test_past_week_no_auto_plan_and_child_can_cancel_old_help(family,monkeypatch):
    p = create(family)
    activity(family,'send_help',kind='sprechen',share='ja')
    h = family[3].helps()[0]
    monkeypatch.setattr(family[2],'today',lambda:date(2026,9,21))
    html = family[0].get('/woche').text
    assert 'Was möchtest du diese Woche angehen?' in html
    assert 'Hilfe aus früheren Wochen' in html
    post(family,f"/woche/hilfe/{h['id']}/zuruecknehmen",{'version':1})
    assert family[3].helps()[0]['status'] == 'zurueckgenommen'
    role(family,'parent')
    html = family[0].get('/woche/eltern').text
    assert 'Vereinbarung der letzten Woche' in html
    assert family[3].get() is None


def test_help_stale_reply_cannot_overwrite(family):
    create(family)
    activity(family,'send_help',kind='sprechen',share='ja')
    h = family[3].helps()[0]
    role(family,'parent')
    path = f"/woche/eltern/hilfe/{h['id']}"
    post(family,path,{'version':1,'status':'zugesagt','reply':'Neue Antwort'})
    post(family,path,{'version':1,'status':'zugesagt','reply':'Veraltet'},409)
    assert family[3].helps()[0]['reply'] == 'Neue Antwort'
    post(family,path,{'version':2,'status':'zugesagt','appointment':'2026-09-99T10:00'},400)


@pytest.mark.parametrize('changes', [dict(kind='falsch',share='ja'),dict(kind='sprechen',share=''),dict(kind='sprechen',share='ja',message='x'*241)])
def test_help_input_validation(family,changes):
    create(family)
    activity(family,'send_help',expected=400,**changes)
    assert not family[3].helps()


def test_retired_routes_are_not_active_and_parent_cannot_report_for_child(family):
    create(family)
    for path in ('/woche/einrichtung','/woche/notfall','/woche/stundenplan'):
        assert family[0].get(path).status_code == 404
    role(family,'parent')
    activity(family,'done',expected=403)
    status(family,'achieved',expected=403)
    status(family,'agree',expected=403)


def test_db_constraints_and_cascade_allow_data_correction(family):
    import sqlite3
    p = create(family)
    with pytest.raises(sqlite3.IntegrityError):
        family[1].db.conn().execute("UPDATE woche_plan SET child_status='invalid' WHERE id=?",(p['id'],))
    activity(family,'done')
    activity(family,'send_help',kind='sprechen',share='ja')
    with family[1].db.tx() as c:
        c.execute('DELETE FROM woche_plan WHERE id=?',(p['id'],))
    assert not family[1].db.q('SELECT * FROM woche_feedback')
    assert not family[3].helps()
