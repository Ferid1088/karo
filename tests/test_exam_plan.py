"""Themenblatt hochladen, Klassenarbeit anlegen, Lernplan erzeugen."""
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


def test_klassenarbeit_ohne_gelesenes_themenblatt_wird_nicht_angelegt(
        client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    seite = client.get("/klassenarbeit")
    r = client.post("/klassenarbeit", data={
        "_csrf": csrf_from(seite.text),
        "exam_date": "2026-10-01",
        "themen": "Ein vorhandenes Thema",
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

    seite = client.get("/klassenarbeit")
    assert 'value="2026-10-01"' in seite.text
    assert "Brüche addieren, Brüche kürzen" in seite.text
    assert f'name="scan_id" value="{scan["id"]}"' in seite.text


def test_klassenarbeit_anlegen_erzeugt_lernplan_und_uebernimmt_scan(
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
    r = client.post("/klassenarbeit", data={
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
    assert plan["state"] == "offen"

    run_jobs(app_env, fake_llm)
    plan = app_env.db.q1("SELECT * FROM exam_plan WHERE exam_id=?", exam["id"])
    assert plan["state"] == "bereit"
    assert "Brüche" in plan["einschaetzung"]

    seite = client.get("/klassenarbeit")
    assert "Brüche addieren üben" in seite.text
    assert "Montag" in seite.text


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


def test_exam_prediction_enthaelt_nur_passende_themen(
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

    ergebnis = exam_service.create_exam("2026-10-01", str(scan["id"]))

    vorhergesagt = {r["topic_id"] for r in app_env.db.q(
        "SELECT topic_id FROM prediction WHERE exam_id=?", ergebnis.exam_id)}
    assert passend_id in vorhergesagt
    assert unpassend_id not in vorhergesagt
    assert ergebnis.themen_eingefroren == 1


def test_exam_prediction_hat_keine_duplikate_bei_doppelt_genanntem_thema(
        client, fake_llm, fake_cli, app_env, tmp_path):
    from app.services import exam as exam_service

    einrichten(client, fake_llm)
    blatt_einlesen(client, fake_llm, app_env)
    passend_id, _ = themen_freigeben(client, app_env)
    _farbe_geben(app_env, passend_id)

    scan = _themenblatt_scan(client, fake_llm, app_env, tmp_path,
                             ["Brüche addieren", "Brüche addieren"])

    ergebnis = exam_service.create_exam("2026-10-01", str(scan["id"]))

    anzahl = app_env.db.q1(
        "SELECT COUNT(*) AS n FROM prediction WHERE exam_id=? AND topic_id=?",
        ergebnis.exam_id, passend_id)["n"]
    assert anzahl == 1


def test_unbekanntes_thema_auf_dem_blatt_laesst_die_erstellung_nicht_abstuerzen(
        client, fake_llm, fake_cli, app_env, tmp_path):
    """Kein Treffer fuer keines der Blatt-Themen: topics.passende() faellt
    dann bewusst auf die volle Liste zurueck (siehe deren Docstring) —
    besser eine zu breite Prognose als eine abgestuerzte Erstellung."""
    from app.services import exam as exam_service

    einrichten(client, fake_llm)
    blatt_einlesen(client, fake_llm, app_env)
    passend_id, unpassend_id = themen_freigeben(client, app_env)
    for tid in (passend_id, unpassend_id):
        _farbe_geben(app_env, tid)

    scan = _themenblatt_scan(client, fake_llm, app_env, tmp_path,
                             ["Völlig unbekanntes Thema XYZ"])

    ergebnis = exam_service.create_exam("2026-10-01", str(scan["id"]))

    vorhergesagt = {r["topic_id"] for r in app_env.db.q(
        "SELECT topic_id FROM prediction WHERE exam_id=?", ergebnis.exam_id)}
    assert vorhergesagt == {passend_id, unpassend_id}
