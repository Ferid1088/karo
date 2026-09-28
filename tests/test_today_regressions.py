"""Heute zeigt erreichbare persönliche Aufgaben und hält Prüfungen getrennt."""
import pytest

from .conftest import csrf_from
from .test_app import einrichten


def test_today_start_works_without_adaptive_feature(client, fake_llm, fake_cli, app_env):
    from app import topics
    einrichten(client, fake_llm)
    tid = topics.anlegen('Brüche addieren', subject="mathematik")
    assert not app_env.config.load().adaptive_learning_enabled
    page = client.get('/')
    action = f'/lernzyklus/{tid}/quiz/starten'
    assert f'action="{action}"' in page.text
    response = client.post(action, data={'_csrf': csrf_from(page.text), 'modus': 'bildschirm'},
                           follow_redirects=False)
    assert response.status_code == 303
    quiz = app_env.db.q1('SELECT id,topic_id FROM quiz')
    assert quiz['topic_id'] == tid
    assert client.get(response.headers['location']).status_code == 200
    assert f'href="/quiz/{quiz["id"]}"' in client.get('/').text


@pytest.mark.parametrize('state', ['bereit', 'ausgewertet'])
def test_exam_quizzes_are_not_personal_next_steps(client, fake_llm, fake_cli, app_env, state):
    from app.services import exam, learning_hub, workflow
    einrichten(client, fake_llm)
    app_env.config.update(antworten_pruefen_kind=True)
    eid = exam.create_exam('2099-01-01', manual_topics='Nur in dieser Prüfung', subject='mathematik').exam_id
    tid = learning_hub.exam_topics(eid)[0]['id']
    with app_env.db.tx() as c:
        qid = c.execute("INSERT INTO quiz(topic_id,state,created_at,anlass) VALUES(?,?,?,'evaluation')",
                        (tid, state, app_env.db.now())).lastrowid
    topics, steps, reviews = workflow.offene_schritte()
    assert not topics and not steps and not reviews
    for path in ('/', '/lernen'):
        page = client.get(path).text
        assert f'href="/quiz/{qid}"' not in page
        assert 'Nur in dieser Prüfung' not in page


def test_historical_exam_quiz_does_not_hide_personal_quiz(client, fake_llm, fake_cli, app_env):
    from app import topics
    from app.services import workflow, topic_workflow
    einrichten(client, fake_llm)
    tid = topics.anlegen('Brüche addieren', subject="mathematik")
    with app_env.db.tx() as c:
        eid = c.execute("INSERT INTO exam(subject,exam_date,themen,created_at) VALUES('mathematik','2099-01-01','[]',?)",
                        (app_env.db.now(),)).lastrowid
        lid = c.execute("INSERT INTO lesson(topic_id,state,ausgabe,created_at) VALUES(?,'wartet','html',?)",
                        (tid, app_env.db.now())).lastrowid
        c.execute("INSERT INTO exam_material(exam_id,row_key,lesson_id,created_at,vorher) VALUES(?,'alt',?,?,'null')",
                  (eid, lid, app_env.db.now()))
        old = c.execute("INSERT INTO quiz(topic_id,lesson_id,state,created_at,anlass) VALUES(?,?,'ausgewertet',?,'lernrunde')",
                        (tid, lid, app_env.db.now())).lastrowid
        personal = c.execute("INSERT INTO quiz(topic_id,state,created_at,anlass) VALUES(?,'bereit',?,'evaluation')",
                             (tid, app_env.db.now())).lastrowid
    assert topic_workflow.pending_quiz(tid)['id'] == personal
    _, steps, reviews = workflow.offene_schritte()
    assert [s['url'] for s in steps] == [f'/quiz/{personal}']
    assert not reviews
    page = client.get('/').text
    assert f'href="/quiz/{personal}"' in page
    assert f'href="/quiz/{old}"' not in page
