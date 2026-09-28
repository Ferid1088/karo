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


def test_themenblatt_hochladen_liest_themen_und_datum(client, fake_llm, fake_cli,
                                                       app_env, tmp_path):
    einrichten(client, fake_llm)
    fake_llm.responses["exam_scan"] = {
        "themen": ["Brüche addieren", "Brüche kürzen"],
        "exam_date": "2026-10-01",
    }
    bild = make_jpeg(tmp_path / "themenblatt.jpg")
    seite = client.get("/klassenarbeit")
    with open(bild, "rb") as f:
        r = client.post("/klassenarbeit/themenblatt",
                        data={"_csrf": csrf_from(seite.text)},
                        files={"datei": ("themenblatt.jpg", f, "image/jpeg")},
                        follow_redirects=True)
    assert r.status_code == 200

    scan = app_env.db.q1("SELECT * FROM exam_scan ORDER BY id DESC LIMIT 1")
    assert scan["state"] == "offen"

    run_jobs(app_env, fake_llm)
    scan = app_env.db.q1("SELECT * FROM exam_scan WHERE id=?", scan["id"])
    assert scan["state"] == "gelesen"
    assert scan["exam_date"] == "2026-10-01"
    assert "Brüche addieren" in scan["themen"]

    seite = client.get("/klassenarbeit/neu")
    assert 'value="2026-10-01"' in seite.text
    assert "Brüche addieren\nBrüche kürzen" in seite.text
    assert f'name="scan_id" value="{scan["id"]}"' in seite.text


def test_klassenarbeit_uebernimmt_scan_und_plant_erst_nach_kalendereingabe(
        client, fake_llm, fake_cli, app_env, tmp_path):
    topic_id = _bis_rot(client, fake_llm, app_env)

    fake_llm.responses["exam_scan"] = {"themen": ["Brüche addieren"],
                                       "exam_date": None}
    bild = make_jpeg(tmp_path / "themenblatt.jpg")
    seite = client.get("/klassenarbeit")
    with open(bild, "rb") as f:
        client.post("/klassenarbeit/themenblatt",
                    data={"_csrf": csrf_from(seite.text)},
                    files={"datei": ("themenblatt.jpg", f, "image/jpeg")})
    run_jobs(app_env, fake_llm)
    scan = app_env.db.q1("SELECT * FROM exam_scan ORDER BY id DESC LIMIT 1")
    assert scan["state"] == "gelesen"

    fake_llm.responses["plan"] = PLAN_ANTWORT
    seite = client.get("/klassenarbeit")
    r = client.post("/klassenarbeit", data={"fach": "mathematik", 
        "_csrf": csrf_from(seite.text),
        "exam_date": "2026-10-01",
        "themen": "Brüche addieren, Brüche kürzen",
        "scan_id": str(scan["id"]),
    }, follow_redirects=True)
    assert r.status_code == 200

    scan = app_env.db.q1("SELECT * FROM exam_scan WHERE id=?", scan["id"])
    assert scan["state"] == "uebernommen"

    exam = app_env.db.q1("SELECT * FROM exam ORDER BY id DESC LIMIT 1")
    plan = app_env.db.q1("SELECT * FROM exam_plan WHERE exam_id=?", exam["id"])
    assert plan is None  # Kein KI-Tagesplan ohne die Lernzeiten des Kindes.
    from app.services import learning_hub, exam_calendar
    owned = learning_hub.exam_topics(exam['id'])
    assert {t['label'] for t in owned} == {'Brüche addieren', 'Brüche kürzen'}
    assert topic_id not in {t['id'] for t in owned}
    assert not exam_calendar.get_days(exam['id'])
    assert 'Lernzeiten festlegen' in r.text
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

def _themenblatt_scan(client, fake_llm, app_env, tmp_path, themen):
    fake_llm.responses["exam_scan"] = {"themen": themen, "exam_date": None}
    bild = make_jpeg(tmp_path / "themenblatt.jpg")
    seite = client.get("/klassenarbeit")
    with open(bild, "rb") as f:
        client.post("/klassenarbeit/themenblatt",
                    data={"_csrf": csrf_from(seite.text)},
                    files={"datei": ("themenblatt.jpg", f, "image/jpeg")})
    run_jobs(app_env, fake_llm)
    return app_env.db.q1("SELECT * FROM exam_scan ORDER BY id DESC LIMIT 1")


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
    blatt_einlesen(client, fake_llm, app_env)
    passend_id, unpassend_id = themen_freigeben(client, app_env)
    for tid in (passend_id, unpassend_id):
        _farbe_geben(app_env, tid)

    scan = _themenblatt_scan(client, fake_llm, app_env, tmp_path, ["Brüche addieren"])
    assert scan["state"] == "gelesen"

    ergebnis = exam_service.create_exam("2026-10-01", str(scan["id"]), subject="mathematik")

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
    blatt_einlesen(client, fake_llm, app_env)
    passend_id, _ = themen_freigeben(client, app_env)
    _farbe_geben(app_env, passend_id)

    scan = _themenblatt_scan(client, fake_llm, app_env, tmp_path,
                             ["Brüche addieren", "Brüche addieren"])

    ergebnis = exam_service.create_exam("2026-10-01", str(scan["id"]), subject="mathematik")

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
    blatt_einlesen(client, fake_llm, app_env)
    passend_id, unpassend_id = themen_freigeben(client, app_env)
    for tid in (passend_id, unpassend_id):
        _farbe_geben(app_env, tid)

    scan = _themenblatt_scan(client, fake_llm, app_env, tmp_path,
                             ["Völlig unbekanntes Thema XYZ"])

    ergebnis = exam_service.create_exam("2026-10-01", str(scan["id"]), subject="mathematik")

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
    assert response.headers['location'] == f'/klassenarbeit/{exam["id"]}#exam-calendar-title'
    assert app_env.db.q1('SELECT COUNT(*) AS n FROM exam_topic WHERE exam_id=?', exam['id'])['n'] == 1
    assert not app_env.db.q('SELECT * FROM exam_scan')
