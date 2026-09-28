"""Historische Prüfungsmaterialien bleiben lesbar; neue Runden bleiben getrennt."""
import json
from pathlib import Path

import pytest

from .conftest import csrf_from, run_jobs
from .test_app import _bis_rot


def plan_anlegen(app_env, topic_id):
    from app import exam_plan
    db = app_env.db
    topic = db.q1("SELECT * FROM topic WHERE id=?", topic_id)
    with db.tx() as c:
        exam_id = c.execute("INSERT INTO exam(subject, exam_date, themen, created_at) VALUES (?, ?, ?, ?)",
                            ("mathematik", "2026-10-01", json.dumps([topic["label"]]), db.now())).lastrowid
        c.execute("INSERT INTO exam_plan(exam_id, state, tagesplan, created_at) VALUES (?, 'bereit', ?, ?)",
                  (exam_id, json.dumps([
                      {"tag": "Montag", "inhalt": "Brüche addieren", "topic_code": topic["code"], "minuten": 15},
                      {"tag": "Dienstag", "inhalt": "Brüche in Textaufgaben", "topic_code": topic["code"], "minuten": 20},
                  ]), db.now()))
    return exam_id, exam_plan.holen_plan(exam_id)["tagesplan_liste"]


def historisches_material(exam_id, tag, ausgabe='html'):
    """Den früheren Datenbestand nachbilden, nicht den stillgelegten HTTP-Weg öffnen."""
    from app import exam_learning
    return exam_learning.status(exam_learning.starten(exam_id, tag['row_key'], ausgabe))


def test_material_in_zeile_archiviert_und_in_eigenem_tab(client, fake_llm, fake_cli, app_env, alter_generator):
    from app import materials, exam_plan
    topic_id = _bis_rot(client, fake_llm, app_env)
    exam_id, tage = plan_anlegen(app_env, topic_id)
    m = historisches_material(exam_id, tage[0])
    assert m["state"] == "offen"
    assert historisches_material(exam_id, tage[0])["id"] == m["id"]
    waiting = client.get(m["url"])
    assert 'Material ist nicht verfügbar' in waiting.text
    assert f'href="/klassenarbeit/{exam_id}"' in waiting.text
    run_jobs(app_env, fake_llm)
    m = client.get(m["url"] + "/status").json()
    assert m["state"] == "bereit"
    page = client.get(m["url"])
    assert '<iframe' in page.text
    assert 'Verständnis prüfen' not in page.text
    assert 'früheren Prüfungsvorbereitung' in page.text
    plan = client.get(f"/klassenarbeit/{exam_id}")
    assert f'href="{m["url"]}"' in plan.text
    assert exam_plan.holen_plan(exam_id)["tagesplan_liste"][0]["materialien"][0]["id"] == m["id"]
    archive = materials.holen("runde", m["round_id"])
    assert "Brüche" in archive["titel"]
    assert "Runde 1" in archive["titel"]
    assert len(archive["dateiname"]) < 120
    assert archive["inhalt"]
    path = app_env.db.q1("SELECT material_pfad FROM lesson_round WHERE id=?", m["round_id"])["material_pfad"]
    Path(path).unlink()
    restored = client.get(m['url'] + '/inhalt')
    assert restored.status_code == 200
    assert restored.content == archive["inhalt"]


def test_zeilen_und_neues_material_bleiben_getrennt(client, fake_llm, fake_cli, app_env, alter_generator):
    from app import teaching
    topic_id = _bis_rot(client, fake_llm, app_env)
    existing = teaching.starten(topic_id, "html", "Eine andere Lernrunde")
    exam_id, tage = plan_anlegen(app_env, topic_id)
    first = historisches_material(exam_id, tage[0])
    second = historisches_material(exam_id, tage[1])
    assert len({existing, first["lesson_id"], second["lesson_id"]}) == 3
    run_jobs(app_env, fake_llm)
    third = historisches_material(exam_id, tage[0])
    assert third["id"] != first["id"]
    assert app_env.db.q1("SELECT prompt_wunsch FROM lesson WHERE id=?", second["lesson_id"])[0] == tage[1]["inhalt"]
    paths = app_env.db.q("SELECT material_pfad FROM lesson_round WHERE material_pfad IS NOT NULL")
    assert len({r[0] for r in paths}) == 2


def test_alte_lerntag_route_erzeugt_auch_mit_legacy_schalter_keine_einheit(client, fake_llm, fake_cli, app_env, alter_generator):
    topic_id = _bis_rot(client, fake_llm, app_env)
    exam_id, tage = plan_anlegen(app_env, topic_id)
    before = len(app_env.db.q('SELECT id FROM job'))
    for row_key, ausgabe in [('fremde-zeile', 'html'), (tage[0]['row_key'], 'ungueltig'),
                             (tage[0]['row_key'], 'html')]:
        response = client.post(f'/klassenarbeit/{exam_id}/lerntag', data={
            '_csrf': csrf_from(client.get('/klassenarbeit').text),
            'row_key': row_key, 'ausgabe': ausgabe}, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers['location'] == f'/klassenarbeit/{exam_id}#exam-next-step'
    assert len(app_env.db.q('SELECT id FROM job')) == before
    assert not app_env.db.q("SELECT * FROM exam_material")


def test_fehlende_quellen_zeigen_einen_handlungsweg(client, fake_llm, fake_cli, app_env, monkeypatch, alter_generator):
    from app import kb, research
    topic_id = _bis_rot(client, fake_llm, app_env)
    exam_id, tage = plan_anlegen(app_env, topic_id)
    monkeypatch.setattr(kb, "lehrmaterial", lambda *a, **kw: [])
    monkeypatch.setattr(research, "material_fuer", lambda *a, **kw: [])
    m = historisches_material(exam_id, tage[0])
    assert m["state"] == "wartet"
    page = client.get(m['url']).text
    assert 'Material ist nicht verfügbar' in page
    assert f'href="/klassenarbeit/{exam_id}"' in page
    assert historisches_material(exam_id, tage[0])["id"] == m["id"]


def test_video_aus_archiv_unterstuetzt_spulen(client, fake_llm, fake_cli, app_env, tmp_path, monkeypatch, alter_generator):
    from app import materials, teaching
    topic_id = _bis_rot(client, fake_llm, app_env)
    exam_id, tage = plan_anlegen(app_env, topic_id)
    video = tmp_path / 'test.mp4'
    video.write_bytes(b'0123456789' * 100)
    monkeypatch.setattr(teaching, '_render_material', lambda *a, **kw: (str(video), '', None))
    m = historisches_material(exam_id, tage[0], ausgabe='notebooklm')
    run_jobs(app_env, fake_llm)
    m = client.get(m['url'] + '/status').json()
    assert m['mime'] == 'video/mp4'
    assert '<video' in client.get(m['url']).text
    video.unlink()
    response = client.get(m['url'] + '/inhalt', headers={'Range': 'bytes=10-19'})
    assert response.status_code == 206
    assert response.content == b'0123456789'
    assert 'inline' in response.headers['content-disposition']
    assert 'Material' in materials.holen('runde', m['round_id'])['titel']


def test_materialdatenbank_umziehen_und_vorhandenes_ziel_schuetzen(client, fake_llm, fake_cli, app_env, tmp_path, alter_generator):
    from app import materials
    topic_id = _bis_rot(client, fake_llm, app_env)
    exam_id, tage = plan_anlegen(app_env, topic_id)
    m = historisches_material(exam_id, tage[0])
    run_jobs(app_env, fake_llm)
    m = client.get(m["url"] + "/status").json()
    vorher = materials.holen("runde", m["round_id"])
    alt = materials.pfad()
    ziel = tmp_path / "anderer-ordner" / "material.sqlite3"
    page = client.get("/setup")
    r = client.post("/setup/finish", data={"_csrf": csrf_from(page.text), "material_db_path": str(ziel)}, follow_redirects=False)
    assert r.status_code == 303
    assert alt.exists() and ziel.exists()
    assert materials.pfad() == ziel
    assert materials.holen("runde", m["round_id"]) == vorher
    blocked = tmp_path / "bestehend.db"
    blocked.write_bytes(b"bestehende wichtige Daten")
    r = client.post("/setup/finish", data={"_csrf": csrf_from(page.text), "material_db_path": str(blocked)})
    assert r.status_code == 400
    assert materials.pfad() == ziel
    assert blocked.read_bytes() == b"bestehende wichtige Daten"
    assert str(blocked) in r.text
    with pytest.raises(ValueError):
        materials.einstellungen_speichern({"material_db_path": "relativ.db"})
    assert materials.pfad() == ziel


def test_historische_lernkontrolle_bleibt_lesbar_ohne_neues_persoenliches_quiz(client, fake_llm, fake_cli, app_env, alter_generator):
    from app import exam_learning
    topic_id = _bis_rot(client, fake_llm, app_env)
    exam_id, tage = plan_anlegen(app_env, topic_id)
    m = historisches_material(exam_id, tage[0])
    vorher = m["vorher"]
    assert vorher and vorher["gesamt"] > 0
    run_jobs(app_env, fake_llm)
    token = csrf_from(client.get(f'/klassenarbeit/{exam_id}').text)
    r = client.post(m["url"] + "/fragen", data={"_csrf": token}, follow_redirects=False)
    assert r.headers['location'] == f'/klassenarbeit/{exam_id}#exam-next-step'
    assert exam_learning.status(m['id'])['quiz'] is None
    # Eine bereits vorhandene alte Lernkontrolle als Datenbestand nachbilden.
    quiz_id = exam_learning.fragen_anfordern(m['id'])
    run_jobs(app_env, fake_llm)
    assert exam_learning.auswertung(exam_learning.status(m["id"]))["nachher"] is None
    questions = app_env.db.q("SELECT * FROM question WHERE quiz_id=?", quiz_id)
    from app import quizzes
    quizzes.freigeben(quiz_id, [{'frage_id': q['id'], 'richtig': True} for q in questions])
    m = exam_learning.status(m["id"])
    assert m["vorher"] == vorher  # Der Ausgangswert wird nicht nachträglich verändert.
    evaluation = exam_learning.auswertung(m)
    assert evaluation["nachher"]["richtig"] == len(questions)
    assert evaluation["differenz"] > 0
    before = len(app_env.db.q('SELECT id FROM quiz'))
    response = client.post(m['url'] + '/fragen', data={'_csrf': token}, follow_redirects=False)
    assert response.headers['location'] == f'/klassenarbeit/{exam_id}#exam-next-step'
    assert len(app_env.db.q('SELECT id FROM quiz')) == before
    assert 'href="/quiz/' not in client.get(m['url']).text


@pytest.mark.parametrize('before,after,expected', [
    (None, (3, 4, 4), 'nicht bestimmbar'),
    ((2, 4, 4), (2, 4, 4), 'Gleicher Anteil'),
    ((3, 4, 4), (1, 4, 4), 'Weniger richtige'),
    ((1, 4, 4), (2, 3, 4), 'nicht vollständig'),
    ((1, 2, 4), (4, 4, 4), 'nicht bestimmbar'),
])
def test_keinen_lernzuwachs_erfinden(app_env, monkeypatch, before, after, expected):
    from app import exam_learning
    def score(values):
        return dict(zip(('richtig', 'bewertet', 'gesamt'), values)) if values else None
    monkeypatch.setattr(exam_learning, 'punktestand', lambda _: score(after))
    assert expected in exam_learning.auswertung({'vorher': score(before), 'quiz': {'id': 1}})['text']
