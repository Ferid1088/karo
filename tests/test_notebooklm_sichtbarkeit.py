"""NotebookLM verschwindet mit dem Weg, zu dem es gehört.

NotebookLM ist eine Ausgabeart des alten Erzeugungswegs — es macht aus
einer Lektion ein Video. Mit `legacy_lesson_generation_enabled=false` führt
keine Schaltfläche mehr dorthin, aber die Einstellungen boten weiterhin
„Bevorzugtes Format" und eine NotebookLM-Anmeldung an.

Das ist schlimmer als überflüssig: es verspricht eine Funktion, die
abgeschaltet ist. Wer sich dort anmeldet, wartet anschliessend vergeblich
darauf, dass etwas passiert.

Gelöscht wird nichts — wer den Schalter umlegt, bekommt beides zurück.
"""
from .test_app import einrichten


def test_ohne_den_alten_weg_kein_notebooklm_in_den_einstellungen(
        client, fake_llm, app_env):
    einrichten(client, fake_llm)

    seite = client.get("/setup").text

    assert "NotebookLM" not in seite
    assert 'id="default_ausgabe"' not in seite
    assert "Bevorzugtes Format" not in seite


def test_die_uebrigen_einstellungen_bleiben(client, fake_llm,
                                            app_env):
    """Der Abschnitt trägt mehr als das Format — Lernrunden, Quellen, Ablage."""
    einrichten(client, fake_llm)

    seite = client.get("/setup").text

    assert "Lernmaterial und Lernen" in seite
    assert "Devin-Verbindung" in seite
    assert "max_lernrunden" in seite


def test_kein_notebooklm_zeiger_im_elternbereich(client, fake_llm,
                                                 app_env):
    einrichten(client, fake_llm)

    seite = client.get("/eltern").text

    assert "NotebookLM" not in seite
    assert "status-notebooklm" not in seite


def test_mit_dem_schalter_ist_alles_wieder_da(client, fake_llm,
                                              app_env, alter_generator):
    einrichten(client, fake_llm)

    setup = client.get("/setup").text
    eltern = client.get("/eltern").text

    assert 'id="notebooklm-verbindung"' in setup
    assert 'id="default_ausgabe"' in setup
    assert "status-notebooklm" in eltern
