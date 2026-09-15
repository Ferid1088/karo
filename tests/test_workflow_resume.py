"""Wiederöffnen, Entwürfe, Mehrfachklicks und verlustfreie Altbestand-Reparatur."""
import json
import pytest
from concurrent.futures import ThreadPoolExecutor

from .conftest import csrf_from, run_jobs
from .test_app import (einrichten, blatt_einlesen, themen_freigeben,
                       kind_modus_aktivieren, quiz_beantworten, quiz_freigeben, _bis_rot)


def prepare(client, fake_llm, app_env):
    from app import quizzes
    einrichten(client, fake_llm)
    blatt_einlesen(client, fake_llm, app_env)
    topic_id = themen_freigeben(client, app_env)[0]
    quiz_id = quizzes.anfordern(topic_id)
    run_jobs(app_env, fake_llm)
    return topic_id, quiz_id


def test_reopening_and_double_click_resume_same_quiz(client, fake_llm, fake_cli, app_env):
    from app import quizzes
    topic_id, quiz_id = prepare(client, fake_llm, app_env)
    app_env.config.update(antworten_pruefen_kind=True)
    kind_modus_aktivieren(client)
    for state in ('bereit', 'beantwortet', 'ausgewertet'):
        with app_env.db.tx() as c:
            c.execute('UPDATE quiz SET state=? WHERE id=?', (state, quiz_id))
        assert quizzes.anfordern(topic_id) == quiz_id
        page = client.get(f'/lernzyklus/{topic_id}', follow_redirects=False)
        assert page.headers['location'] == f'/quiz/{quiz_id}'
        token = csrf_from(client.get('/lernen').text)
        response = client.post(f'/lernzyklus/{topic_id}/quiz/starten', data={'_csrf': token}, follow_redirects=False)
        assert response.headers['location'] == f'/quiz/{quiz_id}'
        assert len(app_env.db.q('SELECT id FROM quiz')) == 1
    quiz_freigeben(client, app_env, quiz_id)
    page = client.get(f'/lernzyklus/{topic_id}')
    assert 'Lerninhalte erstellen' in page.text
    assert 'Deine erste Prüfung ist gespeichert' in page.text
    assert 'Lerninhalte erstellen' in client.get(f'/quiz/{quiz_id}').text
    response = client.post(f'/lernzyklus/{topic_id}/quiz/starten', data={'_csrf': token})
    assert 'Lerninhalte erstellen' in response.text
    assert len(app_env.db.q('SELECT id FROM quiz')) == 1
    client.post(f'/lernzyklus/{topic_id}/quiz/starten', data={'_csrf': token, 'erneut': 'ja'})
    assert len(app_env.db.q('SELECT id FROM quiz')) == 2


def test_answers_persist_across_login_and_reject_stale_tabs(client, fake_llm, fake_cli, app_env):
    topic_id, quiz_id = prepare(client, fake_llm, app_env)
    kind_modus_aktivieren(client)
    question = app_env.db.q1('SELECT id FROM question WHERE quiz_id=? ORDER BY position', quiz_id)['id']
    data = {'_csrf': csrf_from(client.get(f'/quiz/{quiz_id}').text), 'phase': 'answers',
            'revision': '0', 'position': '2', 'values': json.dumps({f'antwort_{question}': '3/4'})}
    response = client.post(f'/quiz/{quiz_id}/entwurf', data=data)
    assert response.json() == {'revision': 1, 'saved': True}
    assert app_env.db.q1('SELECT state FROM quiz WHERE id=?', quiz_id)['state'] == 'bereit'
    assert not app_env.db.q('SELECT * FROM answer_log')
    assert client.post(f'/quiz/{quiz_id}/entwurf', data={**data, 'values': json.dumps({f'antwort_{question}': 'old'})}).status_code == 409
    assert client.post(f'/quiz/{quiz_id}/entwurf', data={**data, '_csrf': 'bad'}).status_code == 403
    app_env.db.init()
    client.cookies.clear()
    token = csrf_from(client.get('/login').text)
    client.post('/login', data={'_csrf': token, 'password': 'geheim123'})
    kind_modus_aktivieren(client)
    page = client.get(f'/lernzyklus/{topic_id}')
    assert 'value="3/4"' in page.text
    assert 'data-draft-position="2"' in page.text
    token = csrf_from(page.text)
    client.post(f'/quiz/{quiz_id}/antworten', data={'_csrf': token, 'draft_revision': '1', f'antwort_{question}': '3/4'})
    assert client.post(f'/quiz/{quiz_id}/entwurf', data={**data, '_csrf': token, 'revision': '2'}).status_code == 409
    client.post(f'/quiz/{quiz_id}/antworten', data={'_csrf': token, f'antwort_{question}': 'overwrite'})
    assert app_env.db.q1('SELECT schueler_antwort FROM question WHERE id=?', question)['schueler_antwort'] == '3/4'


def test_review_drafts_survive_without_releasing_answers(client, fake_llm, fake_cli, app_env):
    _, quiz_id = prepare(client, fake_llm, app_env)
    quiz_beantworten(client, app_env, quiz_id, {1: '3/4'})
    run_jobs(app_env, fake_llm)
    question = app_env.db.q1('SELECT id FROM question WHERE quiz_id=? ORDER BY position', quiz_id)['id']
    page = client.get(f'/quiz/{quiz_id}')
    revision = app_env.db.q1('SELECT draft_revision FROM quiz WHERE id=?', quiz_id)['draft_revision']
    data = {'_csrf': csrf_from(page.text), 'phase': 'review', 'revision': revision,
            'values': json.dumps({f'urteil_{question}': 'ja'})}
    assert client.post(f'/quiz/{quiz_id}/entwurf', data=data).status_code == 200
    assert not app_env.db.q('SELECT * FROM answer_log')
    page = client.get(f'/quiz/{quiz_id}')
    assert f'name="urteil_{question}" value="ja"\n              checked' in page.text
    kind_modus_aktivieren(client)
    data['_csrf'] = csrf_from(client.get('/').text)
    data['revision'] = revision + 1
    assert client.post(f'/quiz/{quiz_id}/entwurf', data=data).status_code == 403
    app_env.config.update(antworten_pruefen_kind=True)
    assert client.post(f'/quiz/{quiz_id}/entwurf', data=data).status_code == 200


def test_quiz_requests_are_atomic(client, fake_llm, fake_cli, app_env):
    from app import quizzes, jobs
    einrichten(client, fake_llm)
    blatt_einlesen(client, fake_llm, app_env)
    topic_id = themen_freigeben(client, app_env)[0]
    jobs.stop()
    def request(_):
        try:
            return quizzes.anfordern(topic_id)
        finally:
            app_env.db._discard_connection()
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(request, range(8)))
    assert len(set(ids)) == 1
    assert len(app_env.db.q('SELECT id FROM quiz')) == 1
    assert len(app_env.db.q("SELECT id FROM job WHERE type='quiz_build'")) == 1


def test_legacy_repair_preserves_results_and_redirects_empty_duplicates(client, fake_llm, fake_cli, app_env):
    from app.services.workflow_repair import repair
    from app.services import learning_content, workflow
    topic_id = _bis_rot(client, fake_llm, app_env)
    before = [dict(r) for r in app_env.db.q('SELECT * FROM answer_log')]
    result_id = app_env.db.q1('SELECT id FROM quiz ORDER BY id DESC LIMIT 1')['id']
    with app_env.db.tx() as c:
        c.execute("UPDATE topic SET label='multiplikation' WHERE id=?", (topic_id,))
        c.execute("UPDATE quiz SET state='ausgewertet' WHERE id=?", (result_id,))
        duplicate = c.execute("INSERT INTO topic(subject,code,label,state,created_at) VALUES ('Mathematik','DUPLICATE','multiplication','aktiv',?)", (app_env.db.now(),)).lastrowid
        blank = c.execute("INSERT INTO quiz(topic_id,anlass,state,created_at) VALUES (?,'evaluation','bereit',?)", (duplicate, app_env.db.now())).lastrowid
        repair(c)
        repair(c)
    assert before == [dict(r) for r in app_env.db.q('SELECT * FROM answer_log')]
    assert learning_content.can_create(topic_id)
    assert app_env.db.q1('SELECT merged_into FROM topic WHERE id=?', duplicate)['merged_into'] == topic_id
    assert app_env.db.q1('SELECT superseded_by FROM quiz WHERE id=?', blank)['superseded_by'] == result_id
    assert client.get(f'/quiz/{blank}', follow_redirects=False).headers['location'] == f'/quiz/{result_id}'
    assert client.get(f'/lernzyklus/{duplicate}', follow_redirects=False).headers['location'] == f'/lernzyklus/{topic_id}'
    assert all(s['topic_id'] != duplicate for s in workflow.offene_schritte()[1])


def test_failed_enqueue_rolls_back_quiz_and_answers(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app import quizzes, jobs
    topic_id, quiz_id = prepare(client, fake_llm, app_env)
    def unavailable(*args, **kwargs):
        raise RuntimeError('queue unavailable')
    monkeypatch.setattr(jobs, 'enqueue_in_transaction', unavailable)
    question_id = app_env.db.q1('SELECT id FROM question WHERE quiz_id=?', quiz_id)['id']
    with pytest.raises(RuntimeError):
        quizzes.antworten_speichern(quiz_id, {question_id: 'not committed'})
    assert app_env.db.q1('SELECT state FROM quiz WHERE id=?', quiz_id)['state'] == 'bereit'
    assert app_env.db.q1('SELECT schueler_antwort FROM question WHERE id=?', question_id)['schueler_antwort'] is None
    with pytest.raises(RuntimeError):
        quizzes.anfordern(topic_id, anlass='lernrunde', round_nr=1)
    assert len(app_env.db.q('SELECT id FROM quiz')) == 1


def test_material_creation_resumes_after_restart_and_double_click(client, fake_llm, fake_cli, app_env):
    from app import teaching, jobs
    topic_id, _ = prepare(client, fake_llm, app_env)
    jobs.stop()
    def start(_):
        try:
            lesson_id = teaching.starten(topic_id, 'html')
            teaching.runde_starten(lesson_id)
            return lesson_id
        finally:
            app_env.db._discard_connection()
    with ThreadPoolExecutor(max_workers=4) as pool:
        lesson_ids = list(pool.map(start, range(8)))
    assert len(set(lesson_ids)) == 1
    assert len(app_env.db.q('SELECT id FROM lesson_round')) == 1
    assert len(app_env.db.q("SELECT id FROM job WHERE type='lesson_build'")) == 1
    app_env.db._discard_connection()
    app_env.db.init()
    run_jobs(app_env, fake_llm)
    lesson_id = lesson_ids[0]
    assert teaching.holen(lesson_id)['state'] == 'bereit'
    assert '<iframe' in client.get(f'/lernen/{lesson_id}').text


def test_abandoned_round_quizzes_do_not_block_current_material(client, fake_llm, fake_cli, app_env):
    from app import teaching, quizzes
    from app.services import topic_workflow, workflow
    topic_id = _bis_rot(client, fake_llm, app_env)
    old_id = teaching.starten(topic_id, 'html')
    old_quiz = quizzes.anfordern(topic_id, anlass='lernrunde', lesson_id=old_id, round_nr=1)
    teaching.abbrechen(old_id, 'Neue Erklärung')
    active = teaching.starten(topic_id, 'html')
    # Ein jüngerer beendeter Altbestand darf die laufende Einheit nicht verdecken.
    finished = teaching.starten(topic_id, 'html', neue_einheit=True)
    teaching.abbrechen(finished, 'Altbestand')
    assert topic_workflow.pending_quiz(topic_id) is None
    assert all(q['id'] != old_quiz for q in quizzes.offene())
    assert [s['url'] for s in workflow.offene_schritte()[1]] == [f'/lernen/{active}']
    page = client.get(f'/lernzyklus/{topic_id}')
    assert 'Lerninhalte erstellen' in page.text
    assert 'Diese Runde ist zu Ende' not in page.text
    assert app_env.db.q1('SELECT id FROM quiz WHERE id=?', old_quiz)


def test_completed_lesson_round_is_not_tested_twice(client, fake_llm, fake_cli, app_env):
    from app import teaching, quizzes
    topic_id = _bis_rot(client, fake_llm, app_env)
    lesson_id = teaching.starten(topic_id, 'html')
    quiz_id = quizzes.anfordern(topic_id, anlass='lernrunde', lesson_id=lesson_id, round_nr=1)
    with app_env.db.tx() as c:
        c.execute("UPDATE quiz SET state='freigegeben', finished_at=? WHERE id=?", (app_env.db.now(), quiz_id))
    assert quizzes.anfordern(topic_id, anlass='lernrunde', lesson_id=lesson_id, round_nr=1) == quiz_id


def test_schema_upgrade_recognizes_old_finished_quizzes_once(client, fake_llm, fake_cli, app_env):
    topic_id = _bis_rot(client, fake_llm, app_env)
    before = [dict(r) for r in app_env.db.q('SELECT * FROM answer_log')]
    with app_env.db.tx() as c:
        c.execute('DELETE FROM schema_version WHERE version>=6')
        c.execute("UPDATE quiz SET state='ausgewertet' WHERE finished_at IS NOT NULL")
    app_env.db.init()
    assert not app_env.db.q("SELECT id FROM quiz WHERE finished_at IS NOT NULL AND state!='freigegeben'")
    assert before == [dict(r) for r in app_env.db.q('SELECT * FROM answer_log')]
    from app import quizzes
    fresh_id = quizzes.anfordern(topic_id)
    app_env.db.init()
    assert app_env.db.q1('SELECT superseded_by FROM quiz WHERE id=?', fresh_id)['superseded_by'] is None
