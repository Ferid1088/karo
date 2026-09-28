"""Profile class never labels content; consent is scoped and not implicit."""
import re

import pytest

from .conftest import csrf_from, run_jobs
from .test_app import einrichten, kind_modus_aktivieren
from .test_lektion_erzeugung import _lektion


def setup(client, fake_llm, app_env, grade=1):
    from app.services import learning_hub
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True, learner_grade=grade, klassenarbeit_kind=True)
    tid = learning_hub.create_topic('Brüche addieren', 'mathematik', grade)
    kind_modus_aktivieren(client)
    token = csrf_from(client.get('/lernen').text)
    return tid, token


def proof(response):
    return re.search(r'name="confirmation" value="([^"]+)"', response.text)[1]


def confirm(client, token, response, base='/lernen/adaptiv'):
    return client.post(base + '/klasse-bestaetigen', data={'_csrf': token, 'confirmation': proof(response)})


@pytest.mark.parametrize('grade', [1, 10])
def test_warning_explicit_consent_and_parent_notice(client, fake_llm, fake_cli, app_env, grade):
    tid, token = setup(client, fake_llm, app_env, grade)
    page = client.post('/lernen/adaptiv/start', data={'_csrf': token, 'topic_id': tid, 'klasse': 6})
    assert 'Ja, trotzdem lernen' in page.text
    assert f'Klasse {grade}' in page.text and 'Klassen 5–6' in page.text
    assert not app_env.db.q('SELECT * FROM lern_sitzung')
    assert not app_env.db.q('SELECT * FROM learning_grade_notice')
    assert not app_env.db.q("SELECT * FROM job WHERE type='lektion_erzeugen'")
    assert app_env.db.q1('SELECT grade FROM topic WHERE id=?', tid)['grade'] == 6
    assert 'Ja, trotzdem lernen' not in confirm(client, token, page).text
    confirm(client, token, page)
    assert len(app_env.db.q('SELECT * FROM learning_grade_notice')) == 1
    assert len(app_env.db.q('SELECT * FROM lern_sitzung')) == 1
    notice = app_env.db.q1('SELECT * FROM learning_grade_notice')
    path = f"/eltern/klassenhinweis/{notice['id']}/gelesen"
    assert client.post(path, data={'_csrf': token}).status_code == 403
    login = client.get('/login')
    client.post('/login', data={'_csrf': csrf_from(login.text), 'password': 'geheim123'})
    inbox = client.get('/eltern')
    assert 'Neue Hinweise zum Lernen' in inbox.text and 'Brüche addieren' in inbox.text
    assert client.post(path, data={}).status_code == 403
    client.post(path, data={'_csrf': csrf_from(inbox.text)})
    assert app_env.db.q1('SELECT read_at FROM learning_grade_notice')['read_at']


def test_matching_class_needs_no_notice(client, fake_llm, fake_cli, app_env):
    tid, token = setup(client, fake_llm, app_env, 6)
    page = client.post('/lernen/adaptiv/start', data={'_csrf': token, 'topic_id': tid})
    assert 'confirmation' not in page.text
    assert app_env.db.q('SELECT * FROM lern_sitzung')
    assert not app_env.db.q('SELECT * FROM learning_grade_notice')


def test_alias_resume_does_not_ask_twice(client, fake_llm, fake_cli, app_env):
    _, token = setup(client, fake_llm, app_env)
    page = client.post('/lernen/adaptiv/start', data={'_csrf': token, 'thema': 'Brüche addieren'})
    confirm(client, token, page)
    resumed = client.post('/lernen/adaptiv/start', data={'_csrf': token, 'thema': 'ungleichnamige Brüche'})
    assert 'Ja, trotzdem lernen' not in resumed.text
    assert len(app_env.db.q('SELECT * FROM learning_grade_notice')) == 1
    assert len(app_env.db.q('SELECT * FROM lern_sitzung')) == 1


def test_profile_change_blocks_resume_and_answer(client, fake_llm, fake_cli, app_env):
    tid, token = setup(client, fake_llm, app_env, 6)
    client.post('/lernen/adaptiv/start', data={'_csrf': token, 'topic_id': tid})
    before = dict(app_env.db.q1('SELECT * FROM lern_sitzung'))
    app_env.config.update(learner_grade=1)
    for response in [client.get('/lernen/adaptiv'),
                     client.post('/lernen/adaptiv/anker', data={'_csrf': token, 'antwort': 'Hälfte'})]:
        assert 'Ja, trotzdem lernen' in response.text
    assert dict(app_env.db.q1('SELECT * FROM lern_sitzung')) == before


def test_confirmation_cannot_cross_exam_or_changed_profile(client, fake_llm, fake_cli, app_env):
    from app.services import exam, learning_hub
    tid, token = setup(client, fake_llm, app_env)
    eid = exam.create_exam('2027-01-15', manual_topics='Brüche addieren', subject='mathematik').exam_id
    etid = learning_hub.exam_topics(eid)[0]['id']
    page = client.post('/lernen/adaptiv/start', data={'_csrf': token, 'topic_id': tid})
    base = f'/klassenarbeit/{eid}/lernen'
    assert confirm(client, token, page, base).status_code == 403
    assert client.post('/lernen/adaptiv/klasse-bestaetigen', data={'_csrf': token, 'confirmation': 'forged'}).status_code == 400
    assert client.post('/lernen/adaptiv/klasse-bestaetigen', data={'confirmation': proof(page)}).status_code == 403
    app_env.config.update(learner_grade=2)
    again = confirm(client, token, page)
    assert 'Ja, trotzdem lernen' in again.text and 'Klasse 2' in again.text
    assert not app_env.db.q('SELECT * FROM learning_grade_notice')
    confirm(client, token, again)
    exam_page = client.post(base + '/start', data={'_csrf': token, 'topic_id': etid})
    assert 'Ja, trotzdem lernen' in exam_page.text
    confirmed = confirm(client, token, exam_page, base)
    assert confirmed.status_code == 200, confirmed.text
    assert len(app_env.db.q('SELECT * FROM learning_grade_notice')) == 2


def test_unknown_generation_keeps_content_level_and_then_warns(client, fake_llm, fake_cli, app_env):
    from app.services import learning_hub
    setup(client, fake_llm, app_env)
    app_env.config.update(llm_error_creation_enabled=True)
    tid = learning_hub.create_topic('Würfel: Volumen', 'mathematik', 1, modell=False)
    assert app_env.db.q1('SELECT grade FROM topic WHERE id=?', tid)['grade'] is None
    fake_llm.responses['lektion'] = _lektion()
    token = csrf_from(client.get('/lernen').text)
    waiting = client.post('/lernen/adaptiv/start', data={'_csrf': token, 'topic_id': tid})
    assert 'vorbereitet' in waiting.text
    run_jobs(app_env, fake_llm)
    c = app_env.db.q1("SELECT * FROM lern_konzept WHERE quelle='erzeugt'")
    assert (c['klasse_von'], c['klasse_bis']) == (5, 7)
    page = client.get(f'/lernen/adaptiv/wartet?topic_id={tid}')
    assert 'Ja, trotzdem lernen' in page.text
    assert not app_env.db.q('SELECT * FROM lern_sitzung')
    confirm(client, token, page)
    assert app_env.db.q('SELECT * FROM lern_sitzung')


@pytest.mark.parametrize('sicher,lo,hi', [(False, 5, 7), (True, 1, 1)])
def test_unconfirmed_classification_never_persists(client, fake_llm, fake_cli, app_env, sicher, lo, hi):
    from app.adaptiv import erzeugung
    from app import jobs
    setup(client, fake_llm, app_env)
    fake_llm.responses['lektion'] = _lektion()
    fake_llm.responses['klassenpruefung'] = dict(sicher=sicher, klasse_von=lo, klasse_bis=hi,
                                              begruendung='Die Einordnung ist nicht bestätigt.')
    jid = erzeugung.anfordern('Würfel: Volumen', 'mathematik', 1)
    assert jobs.run_now(jid)[0] == 'failed'
    assert not app_env.db.q("SELECT * FROM lern_konzept WHERE quelle='erzeugt'")
