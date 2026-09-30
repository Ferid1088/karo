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
