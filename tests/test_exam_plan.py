"""Themenblatt hochladen, Klassenarbeit anlegen, Lernplan erzeugen."""
from .conftest import csrf_from, make_jpeg, run_jobs
from .test_app import _bis_rot, einrichten


PLAN_ANTWORT = {
    "einschaetzung": "Brüche sitzen noch nicht sicher.",
    "tagesplan": [
        {"tag": "Montag", "inhalt": "Brüche addieren üben", "minuten": 20,
         "topic_code": None},
        {"tag": "Dienstag", "inhalt": "Pause", "minuten": 0, "topic_code": None},
    ],
}


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
