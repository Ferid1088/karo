"""Der Vertrag mit dem Lehrplan-Dienst: ohne Klasseneinordnung kein Import.

Gefunden im Ende-zu-Ende-Lauf: Karo verlangt `classification`, die laufende
Dienst-Version lieferte das Feld nicht, und jede Lieferung wurde abgelehnt.
Nach zwei Ablehnungen gab der Dienst das Thema dauerhaft nicht mehr heraus —
das Thema konnte nie wieder Inhalte bekommen. Ein Versionsunterschied
zwischen zwei Diensten darf nicht still in eine Sackgasse fuehren.
"""
from __future__ import annotations

import pytest


def _antwort(classification, klasse=(7, 8)):
    return {
        "status": "ready", "format": "karo-adaptiv-v1",
        "concept_id": "MA.GEOMETRIE.THALES", "concept_version": 1,
        "classification": classification,
        "lesson": {"konzept": {"klasse_von": klasse[0], "klasse_bis": klasse[1]},
                   "erstkontakt": {"text": "Einstieg"}},
    }


@pytest.mark.parametrize("classification, warum", [
    ({}, "Feld fehlt ganz — genau der gefundene Fall"),
    (None, "Feld ist null"),
    ({"source": "approved_curriculum", "first_contact_grade": 7}, "target_grade fehlt"),
    ({"source": "model_guess", "first_contact_grade": 7, "target_grade": 8}, "nicht aus dem Curriculum"),
    ({"source": "approved_curriculum", "first_contact_grade": 6, "target_grade": 8}, "passt nicht zum Konzept"),
])
def test_ohne_gueltige_klasseneinordnung_wird_abgelehnt(app_env, classification, warum):
    from app import config
    from app.adaptiv import curriculum_dienst as cd, schemas
    app_env.db.init()
    with pytest.raises((schemas.InhaltUngueltig, ValueError, TypeError, KeyError)), \
            pytest.MonkeyPatch.context() as mp:
        mp.setattr(cd.schemas, "pruefe_lektion", lambda l: l)
        cd.import_lesson(config.load_safe(), _antwort(classification), "Satz des Thales",
                         "mathematik", 8)


def test_die_ablehnung_nennt_die_klasseneinordnung_beim_namen(app_env):
    """Der Grund muss im Text stehen, sonst sucht man ihn wie ich stundenlang."""
    from app import config
    from app.adaptiv import curriculum_dienst as cd, schemas
    app_env.db.init()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(cd.schemas, "pruefe_lektion", lambda l: l)
        with pytest.raises(schemas.InhaltUngueltig, match="Klasseneinordnung"):
            cd.import_lesson(config.load_safe(), _antwort({}), "Satz des Thales", "mathematik", 8)


# ---------------- Versionsabgleich statt stiller Sackgasse ----------------
def test_gleiche_vertragsfassung_laesst_durch(app_env, monkeypatch):
    from app import config
    from app.adaptiv import curriculum_dienst as cd
    app_env.db.init()
    monkeypatch.setattr(cd, "request", lambda *a, **k: {
        "contract_version": cd.CONTRACT_VERSION, "git_sha": "abc123",
        "formats": ["karo-adaptiv-v1"]})
    passt, grund = cd.vertrag_passt(config.load_safe())
    assert passt and grund == ""


@pytest.mark.parametrize("fremd", ["karo-adaptiv-v1.0", None, "irgendwas"])
def test_andere_vertragsfassung_stellt_zurueck_statt_abzulehnen(app_env, monkeypatch, fremd):
    """Der Kern: bei Versionsunterschied wird gewartet, nicht abgelehnt.

    Eine Ablehnung zaehlt beim Dienst gegen das Thema. Zwei davon, und es
    wird dauerhaft nicht mehr ausgeliefert — obwohl am Inhalt nichts falsch
    war. Genau so ist im Betrieb jedes Thema unlieferbar geworden.
    """
    import time
    from app import config, jobs
    from app.adaptiv import curriculum_dienst as cd
    app_env.db.init()
    angefragt = []

    def gefaelscht(cfg, method, path, body=None):
        angefragt.append((method, path))
        if path == "/v1/meta":
            return {"contract_version": fremd, "git_sha": "alt", "formats": []}
        raise AssertionError(f"Bei Versionsunterschied darf nichts angefragt werden: {path}")

    monkeypatch.setattr(cd, "request", gefaelscht)
    passt, grund = cd.vertrag_passt(config.load_safe())
    assert not passt and cd.CONTRACT_VERSION in grund

    with pytest.raises(jobs.Deferred):
        cd.prepare(config.load_safe(), {"curriculum_started": time.time()},
                   "Satz des Thales", "Mathematik", 8)
    # Kein /v1/lessons und vor allem kein /reject.
    assert all(p == "/v1/meta" for _, p in angefragt), angefragt
    # Und ein Mensch erfaehrt davon.
    meldung = app_env.db.q1("SELECT text FROM betriebsmeldung WHERE bereich='lehrplan-dienst'")
    assert meldung and cd.CONTRACT_VERSION in meldung["text"]


def test_stummer_dienst_gilt_als_unpassend(app_env, monkeypatch):
    """Antwortet /v1/meta nicht, weiss Karo nichts — und wartet lieber."""
    from app import config
    from app.adaptiv import curriculum_dienst as cd
    app_env.db.init()
    def kaputt(*a, **k):
        raise OSError("Verbindung abgelehnt")
    monkeypatch.setattr(cd, "request", kaputt)
    passt, grund = cd.vertrag_passt(config.load_safe())
    assert not passt and "meldet seine Vertragsfassung nicht" in grund


# ------------- Vertragsverstoss oder Inhaltsmangel: zwei Meldungen -------------
def _lieferung(**aenderung):
    from .test_lektion_erzeugung import _lektion
    antwort = {"status": "ready", "export_id": 17, "format": "karo-adaptiv-v1",
               "concept_id": "MA.GEO.WUERFEL", "concept_version": 1,
               "classification": {"source": "approved_curriculum",
                                  "first_contact_grade": 5, "target_grade": 7},
               "lesson": _lektion()}
    antwort.update(aenderung)
    return antwort


def _lauf(app_env, monkeypatch, antwort):
    """Ein Vorbereitungslauf gegen eine gefälschte Dienst-Antwort."""
    import time
    from app import config, jobs
    from app.adaptiv import curriculum_dienst as cd, store
    app_env.db.init()
    store.init()
    app_env.config.update(curriculum_url="http://127.0.0.1:8088", curriculum_key="kc_test_secret")
    gesendet = []

    def dienst(cfg, method, path, body=None):
        gesendet.append((path, body))
        if path == "/v1/meta":
            return {"contract_version": cd.CONTRACT_VERSION, "git_sha": "test", "formats": []}
        if path.endswith("/reject"):
            return {"status": "pending", "export_id": 18}
        return antwort

    monkeypatch.setattr(cd, "request", dienst)
    payload = {"curriculum_started": time.time()}
    with pytest.raises(jobs.Deferred) as warten:
        cd.prepare(config.load(), payload, "Würfel: Volumen", "Mathematik", 6)
    return cd, gesendet, warten.value


def test_kaputte_huelle_geht_als_vertragsverstoss_und_zaehlt_nicht(app_env, monkeypatch):
    """Fehlt die Klasseneinordnung, ist nicht die Lektion schuld.

    Genau hier lag die Sackgasse: Karo meldete es als Inhaltsmangel, der
    Dienst zählte mit, und nach zwei Meldungen war das Thema für Karo tot.
    """
    cd, gesendet, deferred = _lauf(app_env, monkeypatch, _lieferung(classification={}))
    ablehnung = [b for p, b in gesendet if p.endswith("/reject")]
    assert len(ablehnung) == 1 and ablehnung[0]["reason_code"] == "contract"
    assert cd.CONTRACT_VERSION in ablehnung[0]["reason"]
    # kein verbrauchter Versuch gegen das Thema, kein Weiterreichen an eine Neufassung
    assert "curriculum_rejections" not in deferred.payload
    assert deferred.payload.get("curriculum_export") == 17
    assert deferred.seconds >= 60
    meldung = app_env.db.q1("SELECT text FROM betriebsmeldung WHERE bereich='lehrplan-dienst'")
    assert meldung and "nicht zum Vertrag" in meldung["text"]


def test_fachlich_falsches_material_bleibt_ein_inhaltsmangel(app_env, monkeypatch):
    """Die Hülle stimmt, die Lektion nicht: das zählt weiterhin mit."""
    kaputt = _lieferung()
    kaputt["lesson"]["konzept"].update(label="Englische Zeiten", stichworte=["past tense"])
    cd, gesendet, deferred = _lauf(app_env, monkeypatch, kaputt)
    ablehnung = [b for p, b in gesendet if p.endswith("/reject")]
    assert len(ablehnung) == 1 and ablehnung[0]["reason_code"] == "content"
    assert deferred.payload["curriculum_rejections"] == 1
    assert deferred.payload["curriculum_export"] == 18
    # nichts fuer den Betrieb: ein Inhaltsmangel ist Tagesgeschaeft, keine Stoerung
    assert not app_env.db.q("SELECT name FROM sqlite_master WHERE name='betriebsmeldung'")
