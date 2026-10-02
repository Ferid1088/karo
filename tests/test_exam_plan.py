"""Themenblatt hochladen, Klassenarbeit anlegen, Lernplan erzeugen."""
import pytest

from .conftest import csrf_from, make_jpeg, run_jobs
from .test_app import _bis_rot, einrichten, blatt_einlesen, themen_freigeben


PLAN_ANTWORT = {
    "einschaetzung": "Brüche sitzen noch nicht sicher.",
    "tagesplan": [
        {"tag": "Montag", "inhalt": "Brüche addieren üben", "minuten": 20,
         "topic_code": None},
        {"tag": "Dienstag", "inhalt": "Pause", "minuten": 0, "topic_code": None},
    ],
}


@pytest.fixture(autouse=True)
def exam_test_date(app_env, monkeypatch):
    monkeypatch.setattr('app.db.today', lambda: '2026-09-27')


def test_klassenarbeit_ohne_gelesenes_themenblatt_wird_nicht_angelegt(
        client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    seite = client.get("/klassenarbeit")
    r = client.post("/klassenarbeit", data={"fach": "mathematik", 
        "_csrf": csrf_from(seite.text),
        "exam_date": "2026-10-01",
        "themen": "",
    }, follow_redirects=True)
    assert r.status_code == 200
    assert "zuerst das Themenblatt" in r.text
    assert app_env.db.q("SELECT id FROM exam") == []


def test_themen_und_termin_werden_eingetippt_ohne_modell(
        client, fake_llm, fake_cli, app_env):
    """Das Ankündigungsblatt wird nicht mehr gelesen — es wird abgetippt.

    Ein Foto vom Küchentisch trägt mehr als die Ankündigung: den Namen des
    Kindes, die Klasse, was sonst noch danebenlag. Bestätigen musste ein
    Mensch die erkannten Themen ohnehin immer.
    """
    einrichten(client, fake_llm)
    vorher = len(fake_llm.calls)

    seite = client.get("/klassenarbeit/neu")
    assert 'name="themen"' in seite.text
    # Der Upload ist zurück — das Blatt wird im Browser gelesen, nur Text
    # geht weiter (routers/lernmaterial.py). Ein Foto an ein Modell gibt
    # es weiterhin nicht; das Anlegen hier braucht ohnehin keins.
    assert "Themenblatt" in seite.text

    r = client.post("/klassenarbeit", data={
        "_csrf": csrf_from(seite.text), "fach": "mathematik",
        "exam_date": "2026-10-01",
        "themen": "Brüche addieren\nBrüche kürzen"}, follow_redirects=True)
    assert r.status_code == 200

    exam = app_env.db.q1("SELECT * FROM exam ORDER BY id DESC LIMIT 1")
    assert exam["exam_date"] == "2026-10-01"
    from app.services import learning_hub
    assert {t["label"] for t in learning_hub.exam_topics(exam["id"])} == {
        "Brüche addieren", "Brüche kürzen"}
    # Fuer das Anlegen selbst wurde kein Modell gebraucht.
    assert len(fake_llm.calls) == vorher


def test_klassenarbeit_uebernimmt_scan_und_plant_erst_nach_kalendereingabe(
        client, fake_llm, fake_cli, app_env, tmp_path):
    topic_id = _bis_rot(client, fake_llm, app_env)

    fake_llm.responses["plan"] = PLAN_ANTWORT
    seite = client.get("/klassenarbeit")
    r = client.post("/klassenarbeit", data={"fach": "mathematik",
        "_csrf": csrf_from(seite.text),
        "exam_date": "2026-10-01",
        "themen": "Brüche addieren, Brüche kürzen",
    }, follow_redirects=True)
    assert r.status_code == 200

    exam = app_env.db.q1("SELECT * FROM exam ORDER BY id DESC LIMIT 1")
    plan = app_env.db.q1("SELECT * FROM exam_plan WHERE exam_id=?", exam["id"])
    assert plan is None  # Kein KI-Tagesplan ohne die Lernzeiten des Kindes.
    from app.services import learning_hub, exam_calendar
    owned = learning_hub.exam_topics(exam['id'])
    assert {t['label'] for t in owned} == {'Brüche addieren', 'Brüche kürzen'}
    assert topic_id not in {t['id'] for t in owned}
    assert not exam_calendar.get_days(exam['id'])
    # Vor dem Kalender steht die Einstufung: ohne sie waere jede
    # Minutenangabe geraten. Der Kalender selbst ist trotzdem schon da.
    assert 'Ersteinschätzung' in r.text
    assert 'Lernzeit festlegen' in r.text
    response = client.post(f"/klassenarbeit/{exam['id']}/kalender", data={
        '_csrf': csrf_from(r.text), 'minutes_2026-09-29': '20',
        'minutes_2026-09-30': '15'})
    assert response.status_code == 200
    days = exam_calendar.calendar(exam['id'])
    study = next(d for d in days if d['date'] == '2026-09-29')
    assert study['minutes'] == 20 and study['topic_id'] in {t['id'] for t in owned}
    assert next(d for d in days if d['date'] == '2026-09-30')['is_simulation']
    assert f'action="/klassenarbeit/{exam["id"]}/lernen/start"' in response.text


# ==========================================================================
# Prognose-Korrektheit (change.txt Abschnitt 8): nur passende Themen,
# keine Duplikate, kein Absturz bei unbekannten Themen.
# ==========================================================================

def _arbeit_mit_themen(themen, datum="2026-10-01"):
    """Eine Klassenarbeit mit abgetippten Themen — so, wie sie jetzt entsteht.

    Frueher stand hier ein fotografiertes Themenblatt, das ein Modell las.
    Fuer diese Tests war das immer nur der Weg, Themen in eine Arbeit zu
    bekommen; gelesen wird nichts mehr.
    """
    from app.services import exam as exam_service
    return exam_service.create_exam(datum, manual_topics="\n".join(themen),
                                    subject="mathematik")


def _farbe_geben(app_env, topic_id, flag="gelb"):
    with app_env.db.tx() as c:
        c.execute("INSERT INTO topic_flag (topic_id, flag, computed_at) VALUES (?, ?, ?)",
                  (topic_id, flag, app_env.db.now()))


def test_exam_uebernimmt_keine_persoenlichen_prognosen(
        client, fake_llm, fake_cli, app_env, tmp_path):
    """Ein aktives, farbig geflaggtes Thema, das auf dem Themenblatt gar
    nicht steht, darf nicht in die eingefrorene Prognose aufgenommen
    werden — sonst wuerde jede Klassenarbeit sich mit ALLEN Themen im Fach
    befassen."""
    from app.services import exam as exam_service

    einrichten(client, fake_llm)
    # Zwei eigene Themen mit Farbe: die Pruefung darf davon nichts uebernehmen.
    blatt_einlesen(client, fake_llm, app_env, themenname="Brüche addieren")
    blatt_einlesen(client, fake_llm, app_env, name="blatt2.jpg",
                   themenname="Etwas ganz anderes", size=(800, 1000))
    passend_id, unpassend_id = themen_freigeben(client, app_env)
    for tid in (passend_id, unpassend_id):
        _farbe_geben(app_env, tid)

    ergebnis = _arbeit_mit_themen(["Brüche addieren"])

    vorhergesagt = {r["topic_id"] for r in app_env.db.q(
        "SELECT topic_id FROM prediction WHERE exam_id=?", ergebnis.exam_id)}
    assert vorhergesagt == set()
    assert ergebnis.themen_eingefroren == 0
    from app.services import learning_hub
    owned = learning_hub.exam_topics(ergebnis.exam_id)
    assert [t['label'] for t in owned] == ['Brüche addieren']
    assert owned[0]['id'] not in (passend_id, unpassend_id)
    assert owned[0]['learning_status'] == 'neu'


def test_exam_hat_keine_duplikate_bei_doppelt_genanntem_thema(
        client, fake_llm, fake_cli, app_env, tmp_path):
    from app.services import exam as exam_service

    einrichten(client, fake_llm)
    blatt_einlesen(client, fake_llm, app_env, themenname="Brüche addieren")
    passend_id = themen_freigeben(client, app_env)[0]
    _farbe_geben(app_env, passend_id)

    ergebnis = _arbeit_mit_themen(["Brüche addieren", "Brüche addieren"])

    from app.services import learning_hub
    owned = learning_hub.exam_topics(ergebnis.exam_id)
    assert len(owned) == 1
    assert owned[0]['label'] == 'Brüche addieren'
    assert owned[0]['id'] != passend_id
    assert not app_env.db.q('SELECT * FROM prediction WHERE exam_id=?', ergebnis.exam_id)


def test_unbekanntes_thema_auf_dem_blatt_laesst_die_erstellung_nicht_abstuerzen(
        client, fake_llm, fake_cli, app_env, tmp_path):
    """Unbekannte Prüfungsthemen dürfen keine fremden Lernstände übernehmen."""
    from app.services import exam as exam_service

    einrichten(client, fake_llm)
    # Zwei eigene Themen mit Farbe: die Pruefung darf davon nichts uebernehmen.
    blatt_einlesen(client, fake_llm, app_env, themenname="Brüche addieren")
    blatt_einlesen(client, fake_llm, app_env, name="blatt2.jpg",
                   themenname="Etwas ganz anderes", size=(800, 1000))
    passend_id, unpassend_id = themen_freigeben(client, app_env)
    for tid in (passend_id, unpassend_id):
        _farbe_geben(app_env, tid)

    ergebnis = _arbeit_mit_themen(["Völlig unbekanntes Thema XYZ"])

    vorhergesagt = {r["topic_id"] for r in app_env.db.q(
        "SELECT topic_id FROM prediction WHERE exam_id=?", ergebnis.exam_id)}
    assert vorhergesagt == set()
    from app.services import learning_hub
    owned = learning_hub.exam_topics(ergebnis.exam_id)
    assert [t['label'] for t in owned] == ['Völlig unbekanntes Thema XYZ']
    assert owned[0]['id'] not in (passend_id, unpassend_id)


def test_klassenarbeit_kann_mit_manuellen_themen_angelegt_werden(
        client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    page = client.get('/klassenarbeit/neu')
    response = client.post('/klassenarbeit', data={"fach": "mathematik", 
        '_csrf': csrf_from(page.text), 'exam_date': '2099-01-01',
        'themen': 'Brüche addieren', 'fach': 'Mathematik'}, follow_redirects=False)
    exam = app_env.db.q1('SELECT * FROM exam')
    assert response.status_code == 303
    # Nach dem Anlegen steht die Einstufung an, nicht der Kalender.
    assert response.headers['location'] == f'/klassenarbeit/{exam["id"]}#exam-next-step'
    assert app_env.db.q1('SELECT COUNT(*) AS n FROM exam_topic WHERE exam_id=?', exam['id'])['n'] == 1
    assert not app_env.db.q('SELECT * FROM exam_scan')
