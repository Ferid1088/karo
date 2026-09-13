"""Materialzeile, getrennte Einheiten, Archivumzug und echte Lernkontrolle."""
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
                            ("Mathematik", "2026-10-01", json.dumps([topic["label"]]), db.now())).lastrowid
        c.execute("INSERT INTO exam_plan(exam_id, state, tagesplan, created_at) VALUES (?, 'bereit', ?, ?)",
                  (exam_id, json.dumps([
                      {"tag": "Montag", "inhalt": "Brüche addieren", "topic_code": topic["code"], "minuten": 15},
                      {"tag": "Dienstag", "inhalt": "Brüche in Textaufgaben", "topic_code": topic["code"], "minuten": 20},
                  ]), db.now()))
    return exam_id, exam_plan.holen_plan(exam_id)["tagesplan_liste"]


def erstellen(client, exam_id, tag, **extra):
    return client.post(f"/klassenarbeit/{exam_id}/lerntag", headers={"accept": "application/json"},
                       data={"_csrf": csrf_from(client.get("/klassenarbeit").text),
                             "row_key": tag["row_key"], "ausgabe": "html", **extra})


def test_material_in_zeile_archiviert_und_in_eigenem_tab(client, fake_llm, fake_cli, app_env):
    from app import materials, exam_plan
    topic_id = _bis_rot(client, fake_llm, app_env)
    exam_id, tage = plan_anlegen(app_env, topic_id)
    r = erstellen(client, exam_id, tage[0])
    assert r.status_code == 200
    m = r.json()
    assert m["state"] == "offen"
    assert erstellen(client, exam_id, tage[0]).json()["id"] == m["id"]
    waiting = client.get(m["url"])
    assert "DOMContentLoaded" in waiting.text
    run_jobs(app_env, fake_llm)
    m = client.get(m["url"] + "/status").json()
    assert m["state"] == "bereit"
    page = client.get(m["url"])
    assert '<iframe' in page.text
    assert 'Verständnis prüfen' in page.text
    plan = client.get("/klassenarbeit")
    assert f'href="{m["url"]}" target="_blank" rel="noopener"' in plan.text
    assert exam_plan.holen_plan(exam_id)["tagesplan_liste"][0]["materialien"][0]["id"] == m["id"]
    archive = materials.holen("runde", m["round_id"])
    assert "Brüche" in archive["titel"]
    assert "Runde 1" in archive["titel"]
    assert len(archive["dateiname"]) < 120
    assert archive["inhalt"]
    path = app_env.db.q1("SELECT material_pfad FROM lesson_round WHERE id=?", m["round_id"])["material_pfad"]
    Path(path).unlink()
    restored = client.get(f'/material/{m["round_id"]}')
    assert restored.status_code == 200
    assert restored.content == archive["inhalt"]


def test_zeilen_und_neues_material_bleiben_getrennt(client, fake_llm, fake_cli, app_env):
    from app import teaching
    topic_id = _bis_rot(client, fake_llm, app_env)
    existing = teaching.starten(topic_id, "html", "Eine andere Lernrunde")
    exam_id, tage = plan_anlegen(app_env, topic_id)
    first = erstellen(client, exam_id, tage[0]).json()
    second = erstellen(client, exam_id, tage[1]).json()
    assert len({existing, first["lesson_id"], second["lesson_id"]}) == 3
    run_jobs(app_env, fake_llm)
    third = erstellen(client, exam_id, tage[0]).json()
    assert third["id"] != first["id"]
    assert app_env.db.q1("SELECT prompt_wunsch FROM lesson WHERE id=?", second["lesson_id"])[0] == tage[1]["inhalt"]
    paths = app_env.db.q("SELECT material_pfad FROM lesson_round WHERE material_pfad IS NOT NULL")
    assert len({r[0] for r in paths}) == 2


def test_ungueltige_zeile_und_ausgabe_erzeugen_keine_einheit(client, fake_llm, fake_cli, app_env):
    topic_id = _bis_rot(client, fake_llm, app_env)
    exam_id, tage = plan_anlegen(app_env, topic_id)
    assert erstellen(client, exam_id, {"row_key": "fremde-zeile"}).status_code == 400
    assert erstellen(client, exam_id, tage[0], ausgabe="ungueltig").status_code == 400
    assert not app_env.db.q("SELECT * FROM exam_material")


def test_fehlende_quellen_zeigen_einen_handlungsweg(client, fake_llm, fake_cli, app_env, monkeypatch):
    from app import kb, research
    topic_id = _bis_rot(client, fake_llm, app_env)
    exam_id, tage = plan_anlegen(app_env, topic_id)
    monkeypatch.setattr(kb, "lehrmaterial", lambda *a, **kw: [])
    monkeypatch.setattr(research, "material_fuer", lambda *a, **kw: [])
    m = erstellen(client, exam_id, tage[0]).json()
    assert m["state"] == "wartet"
    assert "Quellen ergänzen und Erstellung starten" in client.get(m["url"]).text
    assert erstellen(client, exam_id, tage[0]).json()["id"] == m["id"]


def test_video_aus_archiv_unterstuetzt_spulen(client, fake_llm, fake_cli, app_env, tmp_path, monkeypatch):
    from app import materials, teaching
    topic_id = _bis_rot(client, fake_llm, app_env)
    exam_id, tage = plan_anlegen(app_env, topic_id)
    video = tmp_path / 'test.mp4'
    video.write_bytes(b'0123456789' * 100)
    monkeypatch.setattr(teaching, '_render_material', lambda *a, **kw: (str(video), '', None))
    m = erstellen(client, exam_id, tage[0], ausgabe='notebooklm').json()
    run_jobs(app_env, fake_llm)
    m = client.get(m['url'] + '/status').json()
    assert m['mime'] == 'video/mp4'
    assert '<video' in client.get(m['url']).text
    video.unlink()
    response = client.get(f'/material/{m["round_id"]}', headers={'Range': 'bytes=10-19'})
    assert response.status_code == 206
    assert response.content == b'0123456789'
    assert 'inline' in response.headers['content-disposition']
    assert 'Material' in materials.holen('runde', m['round_id'])['titel']


def test_materialdatenbank_umziehen_und_vorhandenes_ziel_schuetzen(client, fake_llm, fake_cli, app_env, tmp_path):
    from app import materials
    topic_id = _bis_rot(client, fake_llm, app_env)
    exam_id, tage = plan_anlegen(app_env, topic_id)
    m = erstellen(client, exam_id, tage[0]).json()
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


def test_lernkontrolle_misst_bestaetigte_antworten_und_kehrt_zum_material_zurueck(client, fake_llm, fake_cli, app_env):
    from app import exam_learning
    topic_id = _bis_rot(client, fake_llm, app_env)
    exam_id, tage = plan_anlegen(app_env, topic_id)
    m = erstellen(client, exam_id, tage[0]).json()
    vorher = m["vorher"]
    assert vorher and vorher["gesamt"] > 0
    run_jobs(app_env, fake_llm)
    page = client.get(m["url"])
    r = client.post(m["url"] + "/fragen", data={"_csrf": csrf_from(page.text)}, follow_redirects=False)
    quiz_id = int(r.headers["location"].rsplit("/", 1)[-1])
    assert client.post(m["url"] + "/fragen", data={"_csrf": csrf_from(page.text)}, follow_redirects=False).headers["location"] == f"/quiz/{quiz_id}"
    run_jobs(app_env, fake_llm)
    assert exam_learning.auswertung(exam_learning.status(m["id"]))["nachher"] is None
    questions = app_env.db.q("SELECT * FROM question WHERE quiz_id=?", quiz_id)
    data = {"_csrf": csrf_from(page.text), "frage_id": [str(q["id"]) for q in questions]}
    data.update({f'urteil_{q["id"]}': 'ja' for q in questions})
    result = client.post(f"/quiz/{quiz_id}/freigabe", data=data, follow_redirects=False)
    assert result.headers["location"] == m["url"]
    m = exam_learning.status(m["id"])
    assert m["vorher"] == vorher  # Der Ausgangswert wird nicht nachträglich verändert.
    evaluation = exam_learning.auswertung(m)
    assert evaluation["nachher"]["richtig"] == len(questions)
    assert evaluation["differenz"] > 0
    assert "Lernzuwachs" in client.get(m["url"]).text
    assert "Lernzuwachs" in client.get("/klassenarbeit").text


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
