"""Wie viele neue Themen Karo an einem Tag bestellt — und dass es das sagt.

Siebzehn Prüfungsthemen auf einmal eingetragen: der Lehrplan-Dienst nahm sie
alle an und hatte sein Tageskontingent an Modellaufrufen an einem Nachmittag
verbraucht. Danach bekam niemand mehr etwas — auch nicht die Familien, die nur
ein einziges Thema wollten.

Die Grenze steht in Karo, nicht im Dienst: der bekommt keine Familienkennung
und könnte gar nicht wissen, wer wie viel bestellt.
"""
from __future__ import annotations

import time

import pytest


@pytest.fixture
def dienst(app_env, monkeypatch):
    """Karo mit einem gefälschten Lehrplan-Dienst, der mitzählt."""
    from app.adaptiv import curriculum_dienst as cd, store
    app_env.db.init()
    store.init()
    app_env.config.update(curriculum_url="http://127.0.0.1:8088", curriculum_key="kc_test_secret")
    bestellt = []

    def antworten(cfg, method, path, body=None):
        if path == "/v1/meta":
            return {"contract_version": cd.CONTRACT_VERSION, "git_sha": "test", "formats": []}
        bestellt.append(body["topic"])
        return {"status": "pending", "export_id": 100 + len(bestellt), "retry_after": 15}

    monkeypatch.setattr(cd, "request", antworten)
    return cd, bestellt


def _bestellen(cd, thema, payload=None):
    from app import config, jobs
    with pytest.raises(jobs.Deferred) as warten:
        cd.prepare(config.load(), dict(payload or {}, curriculum_started=time.time()),
                   thema, "Mathematik", 6)
    return warten.value.payload


def test_mehr_als_das_tagespensum_geht_nicht_raus(dienst, monkeypatch):
    monkeypatch.setenv("KARO_FAMILY_DAILY_TOPICS", "3")
    cd, bestellt = dienst
    for i in range(5):
        _bestellen(cd, f"Thema {i}")
    assert bestellt == ["Thema 0", "Thema 1", "Thema 2"]


def test_das_vierte_thema_wartet_auf_morgen_statt_zu_haengen(dienst, monkeypatch):
    """„Wird erstellt" waere eine Luege, wenn heute nichts mehr passiert."""
    monkeypatch.setenv("KARO_FAMILY_DAILY_TOPICS", "1")
    cd, bestellt = dienst
    _bestellen(cd, "Erstes Thema")
    payload = _bestellen(cd, "Zweites Thema")
    assert bestellt == ["Erstes Thema"]
    assert payload["budget_wartet"] is True


def test_derselbe_auftrag_verbraucht_nicht_jedes_mal_einen_platz(dienst, monkeypatch):
    """Sonst frisst ein einziges haengendes Thema das ganze Budget."""
    from app.services import topic_budget
    monkeypatch.setenv("KARO_FAMILY_DAILY_TOPICS", "2")
    cd, _ = dienst
    payload = {}
    for _ in range(5):
        payload = _bestellen(cd, "Immer dasselbe", payload)
        payload.pop("curriculum_export", None)      # so, als haette der Dienst neu angefangen
    assert topic_budget.verbraucht() == 1
    assert topic_budget.rest() == 1


def test_was_der_dienst_schon_fertig_hat_zaehlt_nicht(app_env, monkeypatch):
    """Eine fertige Lektion kostet den Dienst nichts — dafuer eine Grenze waere Schikane."""
    from app import config
    from app.adaptiv import curriculum_dienst as cd, store
    from app.services import topic_budget
    app_env.db.init()
    store.init()
    app_env.config.update(curriculum_url="http://127.0.0.1:8088", curriculum_key="kc_test_secret")
    monkeypatch.setenv("KARO_FAMILY_DAILY_TOPICS", "2")

    from .test_lektion_erzeugung import _lektion
    fertig = {"status": "ready", "export_id": 7, "format": "karo-adaptiv-v1",
              "concept_id": "MA.GEO.WUERFEL", "concept_version": 1, "subject": "Mathematik",
              "classification": {"source": "approved_curriculum",
                                 "first_contact_grade": 5, "target_grade": 7},
              "lesson": _lektion()}

    def antworten(cfg, method, path, body=None):
        if path == "/v1/meta":
            return {"contract_version": cd.CONTRACT_VERSION, "git_sha": "test", "formats": []}
        return fertig

    monkeypatch.setattr(cd, "request", antworten)
    for i in range(4):
        ergebnis = cd.prepare(config.load(), {"curriculum_started": time.time()},
                              "Würfel: Volumen", "Mathematik", 6)
        assert ergebnis["quelle"] == "curriculum"
    assert topic_budget.verbraucht() == 0
    assert topic_budget.rest() == 2


def test_ohne_grenze_geht_alles_raus(dienst, monkeypatch):
    from app.services import topic_budget
    monkeypatch.setenv("KARO_FAMILY_DAILY_TOPICS", "0")
    cd, bestellt = dienst
    for i in range(7):
        _bestellen(cd, f"Thema {i}")
    assert len(bestellt) == 7 and topic_budget.rest() is None


def test_der_standard_ist_fuenf(app_env, monkeypatch):
    from app.services import topic_budget
    app_env.db.init()
    monkeypatch.delenv("KARO_FAMILY_DAILY_TOPICS", raising=False)
    assert topic_budget.grenze() == topic_budget.STANDARD == 5
    monkeypatch.setenv("KARO_FAMILY_DAILY_TOPICS", "unsinn")
    assert topic_budget.grenze() == 5          # kaputte Angabe aendert nichts


def test_eltern_sehen_morgen_statt_wird_erstellt(client, fake_llm, app_env, monkeypatch):
    from app import db
    from app.services import exam_effort, exam
    from .test_app import einrichten
    einrichten(client, fake_llm)
    monkeypatch.setenv("KARO_FAMILY_DAILY_TOPICS", "2")
    app_env.config.update(adaptive_learning_enabled=True, learner_grade=6)
    monkeypatch.setattr("app.adaptiv.lektionen.fuer_thema", lambda *a, **k: None)
    exam_id = exam.create_exam("2099-05-05", manual_topics="Satz des Thales",
                               subject="mathematik").exam_id
    exam_effort.inhalte_anfordern(exam_id)
    import json
    auftrag = db.q1("SELECT id, payload FROM job WHERE type='lektion_erzeugen' ORDER BY id LIMIT 1")
    nutzlast = json.loads(auftrag["payload"]) | {"budget_wartet": True}
    with db.tx() as c:
        c.execute("UPDATE job SET payload=? WHERE id=?", (json.dumps(nutzlast), auftrag["id"]))

    stand = exam_effort.inhalte_stand(exam_id)
    assert stand["morgen"] == 1 and stand["offen"] == 1
    seite = client.get("/eltern/lernfortschritt")
    assert "morgen vorbereitet" in seite.text
    assert "höchstens 2 neue Themen am Tag" in seite.text
