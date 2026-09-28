"""Ein Bruchthema ist nicht dasselbe wie *die* Bruchlektion.

Verfasst ist genau eine Lernreihe: `ungleichnamig-addieren`. Die Stichworte
dafür standen aber auf der Themenebene („brueche", „bruch", „nenner"), und
ein Themenwort trifft jedes Unterthema. „Brüche kürzen" bekam damit eine
Lektion über das Addieren — dieselbe stille Ersetzung, die 01_ARCHITECTURE.md
§2 verbietet, nur eine Ebene tiefer als zuvor.

Solange die Zerlegung eines Themas in Konzepte fehlt (Meilenstein 4), ist die
ehrliche Antwort „dazu gibt es noch keine Lernreihe".
"""
from .test_app import einrichten

#: Die echten Themen aus dem Bruchkapitel — sechs davon sind andere Konzepte.
ANDERE_BRUCHTHEMEN = [
    "Brüche vergleichen",
    "Brüche kürzen",
    "Brüche erweitern",
    "Brüche multiplizieren",
    "Brüche dividieren",
    "Zähler und Nenner",
]


def test_andere_bruchthemen_bekommen_keine_additionslektion(
        client, fake_llm, fake_cli, app_env):
    from app.adaptiv import lektionen
    einrichten(client, fake_llm)

    for thema in ANDERE_BRUCHTHEMEN:
        assert lektionen.fuer_thema(thema, "mathematik") is None, thema


def test_das_addieren_selbst_trifft_weiterhin(client, fake_llm, fake_cli,
                                              app_env):
    """Die Gegenprobe: die Lektion, die es gibt, bleibt auffindbar."""
    from app.adaptiv import lektionen
    einrichten(client, fake_llm)

    for thema in ("Brüche addieren und subtrahieren",
                  "Brüche addieren",
                  "ungleichnamige Brüche",
                  "Ungleichnamige Brüche addieren"):
        lektion = lektionen.fuer_thema(thema, "mathematik")
        assert lektion is not None, thema
        assert lektion["konzept_key"] == "ungleichnamig-addieren", thema
