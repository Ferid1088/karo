"""Stored evidence only, timezone-safe drilldown, ownership and privacy."""
from datetime import date
from urllib.parse import urlsplit

import pytest

from .test_app import einrichten, kind_modus_aktivieren


def seed(app_env, monkeypatch):
    from app.services import parent_report
    from app.woche import plaene_store
    monkeypatch.setattr(parent_report.plaene, 'today', lambda: date(2026, 9, 28))
    plaene_store.init()
    db = app_env.db
    with db.tx() as c:
        for tid, subject, visible, label in [
            (1,'mathematik',1,'Brüche'),(2,'mathematik',0,'Brüche'),
            (3,'deutsch',1,'Satzglieder'),(4,'englisch',1,'Simple past'),
            (5,'mathematik',1,'Gelöscht'),(6,'biologie',1,'Nicht erlaubt'),
            (7,'mathematik',1,'Mehrdeutig'),(8,'mathematik',0,'Andere Prüfung')]:
            c.execute('''INSERT INTO topic(id,subject,code,label,state,learning_visible,created_at)
                VALUES(?,?,?,?,'aktiv',?,'2026-09-01T00:00:00+00:00')''', (tid,subject,f'report.{tid}',label,visible))
        c.execute("UPDATE topic SET deleted_at='2026-09-20' WHERE id=5")
        for eid in (1,2):
            c.execute("INSERT INTO exam(id,subject,exam_date,created_at) VALUES(?,'mathematik','2026-10-04','2026-09-01T00:00:00+00:00')",(eid,))
        c.executemany('INSERT INTO exam_topic VALUES(?,?,?)',[(1,2,0),(2,8,0),(1,7,1)])
        for sid,tid in enumerate([1,2,3,5,6,7,8],1):
            c.execute("INSERT INTO lern_eingabe(id,art,topic_id,created_at) VALUES(?,'thema',?,'2026-09-01T00:00:00+00:00')",(sid,tid))
            c.execute("""INSERT INTO lern_sitzung(id,eingabe_id,zustand,created_at,updated_at)
                VALUES(?,?,'MASTERED','2026-09-01T00:00:00+00:00','2026-09-23T10:00:00+00:00')""",(sid,sid))
        def event(sid,stamp,reason,state=None):
            c.execute('INSERT INTO lern_ereignis(sitzung_id,created_at,anlass,nach_zustand) VALUES(?,?,?,?)',
                      (sid,stamp,reason,state))
        event(1,'2026-09-10T09:00:00+00:00','Beherrschung erreicht','MASTERED')
        event(1,'2026-09-21T22:30:00+00:00','Antwort richtig') # local 22 September
        event(1,'2026-09-22T09:00:00+00:00','Lehrrunde ohne Erfolg')
        event(1,'2026-09-22T09:01:00+00:00','Beherrschung erreicht','MASTERED')
        event(2,'2026-09-22T10:00:00+00:00','Antwort richtig','TEACHING')
        event(2,'2026-09-23T10:00:00+00:00','Beherrschung erreicht','MASTERED')
        event(3,'2026-09-22T12:00:00+00:00','Antwort richtig')
        event(3,'2026-09-22T12:01:00+00:00','Beherrschung erreicht','MASTERED')
        event(3,'2026-09-23T10:00:00+00:00','Beherrschung erreicht','MASTERED')
        for sid in (4,5,6):
            event(sid,'2026-09-22T10:00:00+00:00','Antwort richtig','MASTERED')
        event(7,'2026-09-22T10:00:00+00:00','Anker beantwortet','TEACHING')
        # Different child's events are never included.
        c.execute("INSERT INTO lern_sitzung(id,eingabe_id,child_key,zustand,created_at,updated_at) VALUES(8,1,'other','MASTERED','2026-09-01','2026-09-22')")
        event(8,'2026-09-22T10:00:00+00:00','Antwort richtig','MASTERED')
        # Approved legacy answers: one question, corrected later, not two attempts.
        c.execute("INSERT INTO quiz(id,topic_id,anlass,state,created_at) VALUES(1,4,'evaluation','freigegeben','2026-09-22')")
        c.execute("INSERT INTO question(id,quiz_id,position,frage) VALUES(1,1,1,'Test')")
        c.execute("""INSERT INTO answer_log(id,question_id,topic_id,beantwortet_am,richtig,quelle,created_at)
            VALUES(1,1,4,'2026-09-22T10:00:00+00:00',0,'lernbegleitung','2026-09-22T11:00:00+00:00')""")
        c.execute("""INSERT INTO answer_log(id,question_id,topic_id,beantwortet_am,richtig,quelle,created_at,ersetzt_id)
            VALUES(2,1,4,'2026-09-22T10:00:00+00:00',1,'lernbegleitung','2026-09-25T11:00:00+00:00',1)""")
        # Goal records: two segments of a makeup on actual local day, not planned date.
        c.execute("""INSERT INTO plan_goal(id,statement,start_date,end_date,planned_minutes,weekdays,created_at,updated_at)
            VALUES(1,'Lesen','2026-09-01','2026-09-30',15,'1,2,3','2026-09-01','2026-09-01')""")
        for sid,day in [(1,'2026-09-20'),(2,'2026-09-22'),(3,'2026-09-30')]:
            c.execute("INSERT INTO plan_session(id,goal_id,scheduled_date,planned_minutes,created_at) VALUES(?,1,?,15,'2026-09-01')",(sid,day))
        for stamp,minutes in [('2026-09-21T22:30:00+00:00',12),('2026-09-22T12:00:00+00:00',8),('2026-09-23T01:00:00+00:00',5)]:
            c.execute('INSERT INTO plan_completion(planned_session_id,actual_minutes,focus_percent,completed_at,is_makeup) VALUES(1,?,37,?,1)',(minutes,stamp))
        c.execute("INSERT INTO exam_schedule_day VALUES(1,'2026-09-22',30,'2026-09-01')")
    return parent_report


def test_evidence_timezones_separation_corrections_and_no_writes(client, fake_llm, fake_cli, app_env, monkeypatch):
    einrichten(client,fake_llm)
    report=seed(app_env,monkeypatch)
    changes=app_env.db.conn().total_changes
    calls=len(fake_llm.calls)
    day=report.build('tag','2026-09-22')
    assert day['answers']==5 and day['personal_answers']==4 and day['exam_answers']==1
    assert day['active_days']==1 and day['new_secure']==1
    assert day['goal_reports']==2 and day['goal_minutes']==20 and day['goal_planned']==1
    assert day['exam_minutes']==30
    assert day['subjects'][0]['key']=='deutsch' or {s['key'] for s in day['subjects']}=={'mathematik','deutsch','englisch'}
    by_subject={s['key']:s for s in day['subjects']}
    assert (by_subject['mathematik']['right'],by_subject['mathematik']['answers'])==(1,2)
    assert by_subject['englisch']['right']==0  # later correction not projected into past snapshot
    assert day['exams'][0]['safe']==0 and day['exams'][0]['total']==1
    assert report.build('tag','2026-09-23')['exams'][0]['safe']==1
    assert report.build('tag','2026-09-23')['new_secure']==0 # repeated mastery not new
    month=report.build('monat','2026-09-22')
    assert month['new_secure']==2 and month['goal_minutes']==25
    assert month['right']==4 and month['retry']==1 and month['answer_percent']==80
    assert month['all_checks']==3 and month['worked_topics']==5
    assert sum(g['right'] for g in month['groups'])==4
    assert sum(g['checks'] for g in month['groups'])==3
    assert sum(g['goal_minutes'] for g in month['groups'])==25
    assert sum(g['exam_minutes'] for g in month['groups'])==30
    assert sum(v['retry'] for g in month['groups'] for v in g['values'])==1
    assert month['insights'][2]['title']=='Prüfung steht bevor'
    assert '(Prüfung)' in month['insights'][0]['text']
    assert day['answer_percent']==60  # later quiz correction only affects later report snapshots
    assert all(t['scope']=='personal' for s in month['subjects'] for t in s['topics'])
    assert all(t['id']!=2 for s in month['subjects'] for t in s['topics'])
    assert next(s for s in month['subjects'] if s['key']=='englisch')['right']==1
    assert sum(g['total'] for g in month['groups'])==month['answers']
    assert sum(v['value'] for g in month['groups'] for v in g['values'])==month['answers']
    assert app_env.db.conn().total_changes==changes and len(fake_llm.calls)==calls
    assert 'focus_percent' not in str(day) and '37' not in str(day['goals'])
    assert 'Gelöscht' not in str(day) and 'Mehrdeutig' not in str(day)


def test_empty_future_boundaries_and_routes(client,fake_llm,fake_cli,app_env,monkeypatch):
    einrichten(client,fake_llm)
    from app.services import parent_report as report
    # Reading an unused goal area does not initialize it.
    assert not app_env.db.q1("SELECT 1 FROM sqlite_master WHERE name='plan_session'")
    empty=report.build('monat','2024-02-15')
    assert len(empty['calendar'])==29 and empty['answers']==0
    assert not app_env.db.q1("SELECT 1 FROM sqlite_master WHERE name='plan_session'")
    cross=report.build('woche','2026-01-01')
    assert cross['start']=='2025-12-29' and cross['end']=='2026-01-04'
    assert report.local_day('2026-03-29T22:30:00Z')==date(2026,3,30)
    assert report.local_day('2026-10-25T23:30:00Z')==date(2026,10,26)
    seed(app_env,monkeypatch)
    future=report.build('tag','2026-09-30')
    assert future['answers']==0 and future['goal_minutes']==0 and future['goal_planned']==1
    assert future['active_days']==0 and future['future']
    assert future['answer_percent'] is None and future['worked_topics']==0
    assert future['insights'][0]['title']=='Der Zeitraum liegt vor uns'
    for path in ['/eltern','/eltern/bericht']:
        response=client.get(path+'?ansicht=woche&datum=2026-09-22')
        assert response.status_code==200 and 'Cache-Control' in response.headers
        assert 'Lernwoche' in response.text
        for query in ['ansicht=invalid','datum=2026-02-30','datum=9999-12-31','zurueck=bad','basis=not-a-date']:
            assert client.get(path+'?'+query).status_code==400
    kind_modus_aktivieren(client)
    assert client.get('/eltern/bericht').status_code==403
    client.cookies.clear()
    assert client.get('/eltern/bericht',follow_redirects=False).status_code==303


def test_support_hint_is_evidence_based_not_a_grade(client,fake_llm,fake_cli,app_env,monkeypatch):
    einrichten(client,fake_llm)
    report=seed(app_env,monkeypatch)
    with app_env.db.tx() as c:
        c.execute("INSERT INTO lern_ereignis(sitzung_id,created_at,anlass,nach_zustand) VALUES(1,'2026-09-26T10:00:00Z','Fehlertyp erkannt','TEACHING')")
        c.execute("UPDATE exam SET exam_date='2026-11-01'")
    result=report.build('monat','2026-09-28')
    hint=result['insights'][2]
    assert hint['title']=='Hier lohnt sich ein Blick'
    assert 'Brüche: 2 von 3 Antworten noch nicht richtig' in hint['text']
    assert result['answer_percent']==67 and result['retry']==2
    assert result['all_checks']==3  # a later practice need does not erase first passed checks
    for group in result['groups']:
        assert sum(v['right']+v['retry'] for v in group['values'])==group['total']
        assert all(0<=v['retry_height']<=100 for v in group['values'])


def test_overview_lamps_strip_exams_and_goal_units(client,fake_llm,fake_cli,app_env,monkeypatch):
    """The at-a-glance layer only re-reads stored evidence and never judges missing data as failure."""
    einrichten(client,fake_llm)
    report=seed(app_env,monkeypatch)
    changes=app_env.db.conn().total_changes
    week=report.build('woche','2026-09-22')
    assert [d['iso'] for d in week['strip']]==[f'2026-09-{d}' for d in range(21,28)]
    by_day={d['iso']:d for d in week['strip']}
    assert by_day['2026-09-22']['active'] and by_day['2026-09-22']['answers']==5
    assert by_day['2026-09-23']['active'] and by_day['2026-09-23']['heat']==1  # activity without answers stays visible
    assert not by_day['2026-09-21']['active'] and by_day['2026-09-21']['heat']==0
    assert week['answer_ten']==8 and week['elapsed_days']==7 and week['period_short']=='KW 39'
    lamps={l['key']:l for l in week['status']['lamps']}
    assert lamps['answers']['level']=='good' and lamps['answers']['value']=='8 von 10 richtig'
    assert lamps['days']['value']=='2 von 7 Tagen' and lamps['days']['level']=='warn'
    assert lamps['exams']['level']=='warn' and lamps['exams']['dialog']=='pr-d-exam-2'
    assert week['status']['level']=='warn' and week['status']['head']=='Gemischte Woche'
    assert all(l['level']!='crit' for k,l in lamps.items() if k!='exams')  # only a close exam may turn red
    exams={e['id']:e for e in week['exams']}
    assert exams[1]['verdict']['text']=='Auf Kurs' and exams[1]['topic_rows']==[{'label':'Brüche','state':'sicher'}]
    assert exams[2]['verdict']['text']=='Knapp' and exams[2]['practicing']==1
    goal=week['goals'][0]
    assert [x['state'] for x in goal['sessions']]==['missed'] and (goal['due'],goal['done'])==(1,0)
    month=report.build('monat','2026-09-22')
    assert [x['state'] for x in month['goals'][0]['sessions']]==['done','missed','planned']  # makeup counts for its session
    assert (month['goal_due'],month['goal_done'],month['goal_due_minutes'])==(2,1,30)
    assert len(month['calendar_rows'])==5 and month['calendar_rows'][0]['days'][:1]==[None]
    assert sum(r['total'] for r in month['calendar_rows'])==month['answers']
    assert [c['date'] for c in month['check_rows']]==['10.09.','22.09.','23.09.']
    subjects={s['key']:s for s in month['subjects']}
    assert subjects['englisch']['mastery']==['uebt']  # quiz practice without adaptive state is "übt noch"
    assert subjects['deutsch']['safe_total']==1 and subjects['mathematik']['ten']==5
    day=report.build('tag','2026-09-22')
    assert [d['iso'] for d in day['strip']][0]=='2026-09-21' and next(d for d in day['strip'] if d['selected'])['iso']=='2026-09-22'
    future=report.build('tag','2026-09-30')
    assert future['status']['head']=='Vorschau' and future['answer_ten'] is None
    assert {l['key']:l['level'] for l in future['status']['lamps']}['days']=='off'
    assert report.exam_verdict(3,0,0,3)=={'level':'crit','text':'Wenig Zeit'}
    assert report.exam_verdict(0,0,0,3)['text']=='Themen fehlen' and report.exam_verdict(4,1,0,30)['text']=='Noch Zeit'
    assert app_env.db.conn().total_changes==changes
    html=client.get('/eltern/bericht?ansicht=woche&datum=2026-09-22').text
    for dialog in ['pr-d-status','pr-d-days','pr-d-answers','pr-d-checks','pr-d-goals','pr-d-goal-1',
                   'pr-d-exam-1','pr-d-exam-2','pr-d-subj-mathematik','pr-d-table','pr-d-help']:
        assert f'id="{dialog}"' in html and f'href="#{dialog}"' in html
    assert html.count('class="pr-chart-group')==7 and 'focus' not in html.lower().replace('focus-visible','')


def test_browser_drilldown_history_responsive_and_failure(client,fake_llm,fake_cli,app_env,monkeypatch,tmp_path):
    pw=pytest.importorskip('playwright.sync_api')
    einrichten(client,fake_llm)
    seed(app_env,monkeypatch)
    with pw.sync_playwright() as p:
        try:
            browser=p.chromium.launch(channel='chrome',headless=True)
        except pw.Error as exc:
            pytest.skip(f'Chrome nicht verfügbar: {exc}')
        page=browser.new_page()
        errors=[]; requests=[]; fail=[False]
        page.on('pageerror',lambda e:errors.append(str(e)))
        def serve(route):
            req=route.request;url=urlsplit(req.url)
            if url.hostname!='karo.test':return route.abort()
            requests.append((req.method,url.path))
            if fail[0] and url.path=='/eltern/bericht':return route.fulfill(status=503,body='unavailable')
            response=client.request(req.method,url.path+('?' + url.query if url.query else ''),content=req.post_data_buffer,
                headers={'Content-Type':req.headers.get('content-type','')})
            route.fulfill(status=response.status_code,body=response.content,content_type=response.headers.get('content-type','text/plain'))
        page.route('**/*',serve)
        for width in [375,768,1024,1440]:
            page.set_viewport_size({'width':width,'height':1000})
            page.goto('http://karo.test/eltern?ansicht=monat&datum=2026-09-22')
            root=page.locator('#parent-report')
            assert root.get_attribute('data-mode')=='monat'
            assert page.locator('.pr-overview .pr-tile').count()==5
            assert '8 von 10' in page.locator('.pr-overview .pr-tile').nth(2).inner_text()
            for theme in ['schiefer','sand','nacht']:
                page.locator('html').evaluate('(e,v)=>e.dataset.themeColor=v',theme)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                root.screenshot(path=str(tmp_path/f'report-{width}-{theme}.png'))
            # Overview first, details only on demand: tiles open dialogs, Escape and "Schließen" close them.
            assert not page.locator('#pr-d-status').is_visible()
            page.locator('.pr-status').click()
            page.locator('#pr-d-status').wait_for(state='visible')
            assert page.locator('#pr-d-status .pr-insight').count()==3
            page.screenshot(path=str(tmp_path/f'report-{width}-lagebild.png'))
            page.keyboard.press('Escape')
            page.locator('#pr-d-status').wait_for(state='hidden')
            page.locator('.pr-stile',has_text='Mathematik').click()
            subject=page.locator('#pr-d-subj-mathematik')
            subject.wait_for(state='visible')
            assert subject.locator('.pr-drow').first.is_visible()
            subject.locator('[data-close]').click()
            subject.wait_for(state='hidden')
            page.get_by_role('link',name='Zahlen ansehen').click()
            assert page.locator('#pr-d-table .pr-timeline tbody tr').count()==4
            page.keyboard.press('Escape')
            day=page.locator('.pr-cell[data-day="2026-09-22"]')
            day.focus();day.press('Enter')
            page.wait_for_function("document.querySelector('#parent-report').dataset.mode==='tag'")
            assert page.get_by_role('heading',name='Was an diesem Tag passiert ist').is_visible()
            assert '12 Min. gemeldet' in root.inner_text()
            assert page.locator('.pr-overview .pr-tile').nth(4).locator('.pr-ring-c b').inner_text()=='20'
            assert len([r for r in requests if r==('GET','/eltern/bericht')])>0
            page.go_back()
            page.wait_for_function("document.querySelector('#parent-report').dataset.mode==='monat'")
            page.locator('.pr-switch a').filter(has_text='Woche').click()
            page.wait_for_function("document.querySelector('#parent-report').dataset.mode==='woche'")
            assert page.locator('.pr-chart-group').count()==7
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.get_by_role('link',name='Nächster Zeitraum').click()
            page.wait_for_function("document.querySelector('#parent-report').dataset.date==='2026-09-29'")
            page.locator('.pr-chart-group[data-day="2026-09-30"]').click()
            page.wait_for_function("document.querySelector('#parent-report').dataset.date==='2026-09-30'")
            assert '15 Min. geplant' in root.inner_text()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            fail[0]=True
            page.get_by_role('link',name='Vorheriger Zeitraum').click()
            page.locator('#report-error').wait_for(state='visible')
            assert root.get_attribute('data-date')=='2026-09-30'
            fail[0]=False
            page.get_by_role('link',name='Vorheriger Zeitraum').click()
            page.wait_for_function("document.querySelector('#parent-report').dataset.date==='2026-09-29'")
        assert not errors
        assert all(method=='GET' for method,_ in requests)
        plain=browser.new_context(java_script_enabled=False)
        ppage=plain.new_page();ppage.route('**/*',serve)
        ppage.goto('http://karo.test/eltern?datum=2026-09-22')
        ppage.locator('.pr-status').click()  # without JS the dialog opens via #anchor
        assert ppage.locator('#pr-d-status').is_visible()
        ppage.locator('#pr-d-status [data-close]').click()
        assert not ppage.locator('#pr-d-status').is_visible()
        ppage.locator('.pr-cell[data-day="2026-09-22"]').click()
        assert ppage.locator('#parent-report').get_attribute('data-mode')=='tag'
        print(f'Bericht Screenshots: {tmp_path}')
        browser.close()
