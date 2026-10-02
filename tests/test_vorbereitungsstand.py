"""Was Karo vorbereitet, und in welcher Reihenfolge — sichtbar für Eltern.

Zwei Dinge, die gefehlt haben: der Lehrplan-Dienst arbeitete die Themen nach
Eingang ab (die Arbeit am Freitag wartete hinter der in drei Wochen), und
Eltern sahen nur „wird vorbereitet" — ununterscheidbar von „hängt".
"""
from __future__ import annotations

import json

import pytest


def _arbeit(app_env, datum: str, themen: list[str], fach: str = "mathematik") -> int:
    from app.services import exam
    app_env.config.update(learner_grade=6)
    return exam.create_exam(datum, manual_topics="\n".join(themen), subject=fach).exam_id


def test_das_pruefungsdatum_geht_an_den_dienst(app_env, monkeypatch):
    """Ohne Datum sortiert der Dienst nach Eingang — und das ist die falsche Ordnung."""
    from app import jobs
    from app.adaptiv import curriculum_dienst as cd
    app_env.db.init()
    app_env.config.update(curriculum_url="http://127.0.0.1:8088", curriculum_key="kc_test_secret")
    gesendet = []

    def dienst(cfg, method, path, body=None):
        if path == "/v1/meta":
            return {"contract_version": cd.CONTRACT_VERSION, "git_sha": "test", "formats": []}
        gesendet.append(body)
        return {"status": "pending", "export_id": 5, "retry_after": 15,
                "position": 2, "waiting": 7, "seconds": 420}

    monkeypatch.setattr(cd, "request", dienst)
    with pytest.raises(jobs.Deferred) as warten:
        cd.prepare(app_env.config.load(), {"gebraucht_am": "2027-05-05"},
                   "Satz des Thales", "Mathematik", 8)
    assert gesendet[0]["needed_by"] == "2027-05-05"
    # Der Wartestand kommt mit zurueck, sonst kann die Oberflaeche nichts sagen.
    assert warten.value.payload["curriculum_position"] == 2
    assert warten.value.payload["curriculum_waiting"] == 7
    assert warten.value.payload["curriculum_seconds"] == 420


def test_ohne_datum_wird_nichts_erfunden(app_env, monkeypatch):
    """Ein persoenliches Thema hat kein Pruefungsdatum — dann geht auch keines raus."""
    from app import jobs
    from app.adaptiv import curriculum_dienst as cd
    app_env.db.init()
    app_env.config.update(curriculum_url="http://127.0.0.1:8088", curriculum_key="kc_test_secret")
    gesendet = []

    def dienst(cfg, method, path, body=None):
        if path == "/v1/meta":
            return {"contract_version": cd.CONTRACT_VERSION, "git_sha": "test", "formats": []}
        gesendet.append(body)
        return {"status": "pending", "export_id": 5}

    monkeypatch.setattr(cd, "request", dienst)
    with pytest.raises(jobs.Deferred):
        cd.prepare(app_env.config.load(), {}, "Satz des Thales", "Mathematik", 8)
    assert "needed_by" not in gesendet[0]


def test_eltern_sehen_jedes_thema_einzeln_mit_schaetzung(client, fake_llm, app_env, monkeypatch):
    """„Wird vorbereitet" ohne Zahl ist nicht von „haengt" zu unterscheiden."""
    from app import db, jobs
    from app.adaptiv import erzeugung
    from app.services import exam_effort
    from .test_app import einrichten
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True)
    monkeypatch.setattr("app.adaptiv.lektionen.fuer_thema", lambda *a, **k: None)
    exam_id = _arbeit(app_env, "2099-05-05", ["Satz des Thales", "Kreisumfang berechnen"])
    assert exam_effort.inhalte_anfordern(exam_id) >= 1

    # So, als haette der Dienst zu einem Thema einen Platz genannt.
    auftrag = db.q1("SELECT id, payload FROM job WHERE type='lektion_erzeugen' ORDER BY id LIMIT 1")
    nutzlast = json.loads(auftrag["payload"])
    nutzlast.update(curriculum_position=3, curriculum_waiting=11, curriculum_seconds=600)
    with db.tx() as c:
        c.execute("UPDATE job SET payload=? WHERE id=?", (json.dumps(nutzlast), auftrag["id"]))

    stand = exam_effort.inhalte_stand(exam_id)
    laufend = [t for t in stand["themen"] if t["stand"] == "laeuft"]
    assert laufend and stand["gesamt"] == 2
    mit_platz = [t for t in laufend if t.get("platz")]
    assert mit_platz and mit_platz[0]["warten"] == 11 and mit_platz[0]["sekunden"] == 600
    assert stand["sekunden"] == 600        # die laengste Schaetzung zaehlt

    uebersicht = exam_effort.vorbereitung_uebersicht()
    assert uebersicht and uebersicht[0]["exam_id"] == exam_id
    assert uebersicht[0]["fach"] == "Mathematik" and uebersicht[0]["datum"] == "2099-05-05"

    seite = client.get("/eltern/lernfortschritt")
    assert seite.status_code == 200
    assert "Was Karo gerade vorbereitet" in seite.text
    assert "Platz 3 von 11" in seite.text and "10 Minuten" in seite.text
    assert nutzlast["thema"] in seite.text


def test_ein_gescheitertes_thema_sieht_nicht_aus_wie_ein_laufendes(app_env, monkeypatch):
    """Bei „läuft" hilft Warten, bei „gescheitert" nie."""
    from app import db
    from app.adaptiv import erzeugung
    from app.services import exam_effort
    app_env.db.init()
    app_env.config.update(adaptive_learning_enabled=True)
    monkeypatch.setattr("app.adaptiv.lektionen.fuer_thema", lambda *a, **k: None)
    exam_id = _arbeit(app_env, "2099-06-06", ["Bruchteile vergleichen"])
    exam_effort.inhalte_anfordern(exam_id)
    with db.tx() as c:
        c.execute("UPDATE job SET state='fehler', last_error=? WHERE type='lektion_erzeugen'",
                  ("Das Kontingent ist aufgebraucht.",))
    themen = exam_effort.inhalte_stand(exam_id)["themen"]
    assert [t["stand"] for t in themen] == ["gescheitert"]
    assert "Kontingent" in themen[0]["grund"]


def test_eltern_sehen_ab_wann_es_weitergeht(client, fake_llm, app_env, monkeypatch):
    """Erschöpftes Kontingent beim Dienst: nicht „gleich fertig", sondern eine Uhrzeit.

    Ohne diese Angabe sieht ein stehender Auftrag aus wie ein laufender, und
    eine Familie sieht alle 15 Sekunden nach.
    """
    import json

    from app import db
    from app.services import exam, exam_effort
    from .test_app import einrichten
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True, learner_grade=6)
    monkeypatch.setattr("app.adaptiv.lektionen.fuer_thema", lambda *a, **k: None)
    exam_id = exam.create_exam("2099-05-05", manual_topics="Satz des Thales",
                               subject="mathematik").exam_id
    exam_effort.inhalte_anfordern(exam_id)
    auftrag = db.q1("SELECT id, payload FROM job WHERE type='lektion_erzeugen' ORDER BY id LIMIT 1")
    nutzlast = json.loads(auftrag["payload"]) | {"curriculum_pausiert_bis": "2026-10-01T14:40:00"}
    with db.tx() as c:
        c.execute("UPDATE job SET payload=? WHERE id=?", (json.dumps(nutzlast), auftrag["id"]))

    themen = exam_effort.inhalte_stand(exam_id)["themen"]
    assert themen[0]["stand"] == "laeuft" and themen[0]["ab"] == "2026-10-01T14:40:00"
    seite = client.get("/eltern/lernfortschritt")
    assert "Tageskontingent aufgebraucht" in seite.text
    assert "ab 14:40 Uhr" in seite.text


def test_der_dienst_meldet_die_pause_an_karo(app_env, monkeypatch):
    """Die Angabe kommt aus der Antwort des Dienstes, nicht aus einer Vermutung."""
    import time

    from app import config, jobs
    from app.adaptiv import curriculum_dienst as cd, store
    app_env.db.init()
    store.init()
    app_env.config.update(curriculum_url="http://127.0.0.1:8088", curriculum_key="kc_test_secret")

    def dienst(cfg, method, path, body=None):
        if path == "/v1/meta":
            return {"contract_version": cd.CONTRACT_VERSION, "git_sha": "test", "formats": []}
        return {"status": "pending", "export_id": 5, "retry_after": 300,
                "paused_until": "2026-10-01T14:40:00+00:00"}

    monkeypatch.setattr(cd, "request", dienst)
    with pytest.raises(jobs.Deferred) as warten:
        cd.prepare(config.load(), {"curriculum_started": time.time()},
                   "Satz des Thales", "Mathematik", 8)
    assert warten.value.payload["curriculum_pausiert_bis"] == "2026-10-01T14:40:00"
