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
