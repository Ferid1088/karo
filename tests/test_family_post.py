"""Post von zu Hause: Eltern schreiben aus dem Bericht, das Kind liest und antwortet.

Leitplanken: nur freundliche Emojis, Vorschläge ohne Fehlerzahlen, Feiern nur am
eigenen Ziel des Kindes (nie an Ampel oder Trefferquote), Rückzug nur ungelesen.
"""
from datetime import date, datetime, timezone

import pytest

from .conftest import csrf_from
from .test_app import einrichten, kind_modus_aktivieren, session_cookie_faelschen


def eltern_login(client, passwort='geheim123'):
    seite = client.get('/login')
    client.post('/login', data={'_csrf': csrf_from(seite.text), 'password': passwort})


def test_service_guardrails_and_suggestions(client, fake_llm, app_env):
    einrichten(client, fake_llm)
    from app.services import family_post as post
    for text, emoji in [('', None), ('Hallo', '👎'), ('x' * 201, None), ('', '😞'), ('Hallo', '<script>')]:
        with pytest.raises(post.PostError):
            post.send(text, emoji)
    with pytest.raises(post.PostError):
        post.send('Hallo', None, 'geschenk')
    first = post.send('  Du hast   drangeblieben!  ', '💪')
    only_emoji = post.send('', '❤️')
    assert post.recent()[0]['id'] == only_emoji and post.recent()[1]['text'] == 'Du hast drangeblieben!'
    post.withdraw(only_emoji)
    assert [m['id'] for m in post.inbox()] == [first]
    with pytest.raises(post.PostError):
        post.react(first, '👎')
    post.react(first, 'danke')
    with pytest.raises(post.PostError):
        post.withdraw(first)  # gelesen und beantwortet: bleibt stehen
    report = {'mode': 'woche', 'check_rows': [{'label': 'Brüche'}], 'active_days': 4, 'goal_done': 2,
              'subjects': [{'topics': [{'label': 'Prisma: Volumen'}]}], 'upcoming': [{'days': 5, 'date_label': '08.10.'}],
              'retry': 7, 'answer_ten': 3}
    ideas = post.suggestions(report, 'Milena')
    assert 1 <= len(ideas) <= 3 and all(i['emoji'] in post.PARENT_EMOJIS for i in ideas)
    for idea in ideas:  # Einsatz loben, nie Fehler zählen oder Bedingungen stellen
        low = idea['text'].lower()
        assert not any(w in low for w in ('richtig', 'falsch', 'fehler', 'von 10', 'wenn du'))
    assert ideas[0]['text'].startswith('„Brüche“ sitzt jetzt')
    assert post.suggestions({'mode': 'monat'}, 'Milena')[0]['emoji'] == '❤️'


def test_parent_sends_child_reads_and_answers(client, fake_llm, app_env):
    einrichten(client, fake_llm)
    seite = client.get('/eltern?ansicht=woche&datum=2026-09-22')
    assert 'id="pr-d-post"' in seite.text and 'Nachricht an Milena' in seite.text
    token = csrf_from(seite.text)
    here = '/eltern?ansicht=woche&datum=2026-09-22'
    r = client.post('/eltern/post', data={'_csrf': token, 'text': 'Du hast toll geübt!', 'emoji': '💪',
                                          'art': 'nachricht', 'zurueck_zu': here}, follow_redirects=False)
    assert r.status_code == 303 and r.headers['location'] == here
    # Ohne eigenen Text zählt der gewählte Vorschlag; fremde Rücksprünge werden ignoriert.
    r = client.post('/eltern/post', data={'_csrf': token, 'vorschlag': 'Samstag gehen wir Eis essen.', 'emoji': '🎉',
                                          'art': 'ueberraschung', 'zurueck_zu': 'https://fremd.example/eltern'},
                    follow_redirects=False)
    assert r.headers['location'] == '/eltern'
    bad = client.post('/eltern/post', data={'_csrf': token, 'text': 'Hm', 'emoji': '👎', 'art': 'nachricht'})
    assert 'freundlichen Emojis' in bad.text
    assert app_env.db.q1('SELECT COUNT(*) AS n FROM family_message')['n'] == 2
    page = client.get('/eltern').text
    assert 'noch ungelesen' in page and 'Zurückziehen' in page
    # Eltern, die den Kinderbereich ansehen, lösen kein "gelesen" aus.
    client.get('/post')
    assert app_env.db.q1('SELECT COUNT(*) AS n FROM family_message WHERE read_at IS NULL')['n'] == 2

    kind_modus_aktivieren(client)
    heute = client.get('/')
    assert '2 neue Nachrichten von zu Hause' in heute.text
    assert 'Eine Überraschung wartet auf dich!' in heute.text  # Überraschung wird nicht vorab verraten
    assert 'kopf-post-zahl">2<' in heute.text
    assert 'pr-d-post' not in heute.text and 'Lagebild' not in heute.text  # nie der Bericht
    box = client.get('/post')
    assert 'Du hast toll geübt!' in box.text and '🎁 Überraschung' in box.text and box.text.count('>Neu<') == 2
    assert app_env.db.q1('SELECT COUNT(*) AS n FROM family_message WHERE read_at IS NULL')['n'] == 0
    assert 'kopf-post-zahl' not in client.get('/').text
    msg = app_env.db.q1("SELECT id FROM family_message WHERE text='Du hast toll geübt!'")['id']
    r = client.post(f'/post/{msg}/antwort', data={'_csrf': csrf_from(box.text), 'antwort': '❤️'}, follow_redirects=False)
    assert r.status_code == 303
    assert app_env.db.q1('SELECT reaction FROM family_message WHERE id=?', msg)['reaction'] == '❤️'
    assert 'Deine Antwort: <b>❤️</b>' in client.get('/post').text
    # Das Kind kann keine Elternpost schicken und nichts zurückziehen.
    for path in ('/eltern/post', f'/eltern/post/{msg}/zurueckziehen'):
        assert client.post(path, data={'_csrf': csrf_from(box.text), 'text': 'x'},
                           follow_redirects=False).status_code == 403
    eltern_login(client)
    page = client.get('/eltern').text
    assert 'Milena: ❤️' in page and 'gelesen ✓' in page and 'Letzte Antwort: ❤️' in page


def test_withdraw_before_reading(client, fake_llm, app_env):
    einrichten(client, fake_llm)
    from app.services import family_post as post
    msg = post.send('Oh, falsch geschickt', '🤗')
    page = client.get('/eltern')
    r = client.post(f'/eltern/post/{msg}/zurueckziehen', data={'_csrf': csrf_from(page.text)}, follow_redirects=False)
    assert r.status_code == 303
    assert post.inbox() == [] and post.unread() == []


def test_celebration_only_for_childs_own_reached_goal(client, fake_llm, app_env, monkeypatch):
    einrichten(client, fake_llm)
    from app.woche import plaene, plaene_store as store
    from app.services import family_post as post
    monkeypatch.setattr(plaene, 'today', lambda now=None: date(2026, 9, 10))
    # Den Bericht lesen legt keine Zieltabellen an.
    assert post.celebrations_due() == []
    client.get('/eltern')
    assert not app_env.db.q1("SELECT 1 FROM sqlite_master WHERE name='plan_session'")
    day = date(2026, 9, 10)
    with_idea = store.create_goal('Mathe üben.', day, date(2026, 9, 20), 20, [day.isoweekday()], celebration='  Pizza-Abend ')
    without = store.create_goal('Lesen.', day, date(2026, 9, 20), 20, [day.isoweekday()])
    by_minutes = store.create_goal('Vokabeln.', day, day, 15, [day.isoweekday()], celebration='Kino mit Papa')
    assert store.goal(with_idea)['celebration'] == 'Pizza-Abend'
    with pytest.raises(ValueError):
        store.create_goal('Zu lang.', day, day, 10, [day.isoweekday()], celebration='x' * 61)
    assert post.celebrations_due() == []  # noch nicht geschafft
    store.set_status(with_idea, 'completed')
    store.set_status(without, 'completed')
    session = store.sessions(by_minutes)[0]
    store.complete(session['id'], 15, 80, datetime(2026, 9, 10, 15, tzinfo=timezone.utc))
    assert [g['id'] for g in post.celebrations_due()] == [with_idea, by_minutes]  # alle Minuten gelernt zählt auch
    page = client.get('/eltern')
    assert 'Feier-Idee von Milena: Pizza-Abend' in page.text and 'Machen wir!' in page.text
    r = client.post(f'/eltern/post/feier/{with_idea}', data={'_csrf': csrf_from(page.text)}, follow_redirects=False)
    assert r.status_code == 303
    row = app_env.db.q1("SELECT * FROM family_message WHERE kind='feier'")
    assert 'Pizza-Abend' in row['text'] and row['emoji'] == '🎉' and row['goal_id'] == with_idea
    assert [g['id'] for g in post.celebrations_due()] == [by_minutes]
    for goal_id in (with_idea, without):
        with pytest.raises(post.PostError):
            post.celebrate(goal_id)
    # Die Ampel spielt keine Rolle: im Bericht gibt es kein Geschenk-Feld für "grün".
    assert 'grün' not in ' '.join(g['celebration'] for g in post.celebrations_due())


def test_child_sets_celebration_in_wizard_and_detail(client, fake_llm, app_env, monkeypatch):
    from app.woche import plaene, plaene_store as store
    einrichten(client, fake_llm)
    monkeypatch.setattr(plaene, 'today', lambda now=None: date(2026, 9, 22))
    cookie = session_cookie_faelschen(app_env, auth=True, role='child', csrf='test-token')
    client.cookies.clear(); client.cookies.set('karo_session', cookie)
    steps = [{'step': '1', 'statement': 'Ich möchte besser in Mathe werden.'},
             {'step': '2', 'start_date': '2026-09-24', 'duration': '7'},
             {'step': '3', 'weekdays': ['1', '3']}, {'step': '4', 'minutes': '20'},
             {'step': '5', 'celebration': 'Pizza-Abend'}]
    for index, data in enumerate(steps, 1):
        page = client.get(f'/woche/ziele/neu?step={index}')
        if index == 5:
            assert 'Wie möchtest du feiern' in page.text
        r = client.post('/woche/ziele/neu', data={'_csrf': csrf_from(page.text), **data}, follow_redirects=False)
        assert r.status_code == 303, r.text[:500]
    goal = store.goals()[0]
    assert goal['celebration'] == 'Pizza-Abend'
    detail = client.get(f"/woche/ziele/{goal['id']}")
    assert 'Deine Feier-Idee: Pizza-Abend' in detail.text
    r = client.post(f"/woche/ziele/{goal['id']}/feier", data={'_csrf': csrf_from(detail.text), 'celebration': 'Kino'},
                    follow_redirects=False)
    assert r.status_code == 303 and store.goal(goal['id'])['celebration'] == 'Kino'
    client.post(f"/woche/ziele/{goal['id']}/feier", data={'_csrf': csrf_from(detail.text), 'celebration': ''})
    assert store.goal(goal['id'])['celebration'] is None
