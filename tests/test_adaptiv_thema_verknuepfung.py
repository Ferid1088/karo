"""Eine adaptive Sitzung weiß, zu welchem Thema sie gehört.

`app/adaptiv/schema.sql` hält die Lerninhalte bewusst von `topic` getrennt:
Konzepte und Fehlertypen sind für jedes Kind dieselben, lokale Themen-IDs
nicht. Die *Eingabe* ist aber genau der Ort, an dem beides zusammenkommt —
hier hat ein Kind auf eine bestimmte Themenkarte getippt.

Ohne diese Verbindung zeigte „In Bearbeitung" etwas anderes als das, woran
das Kind gerade arbeitete: das Thema mit der laufenden Sitzung stand unter
„Neue Themen", und eines ohne jede adaptive Aktivität stand unter
„In Bearbeitung".
"""
from .conftest import csrf_from
from .test_app import einrichten, kind_modus_aktivieren

LEKTION = "Brüche addieren und subtrahieren"


def _bereit(client, fake_llm, app_env, *labels):
    from app import topics
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True, learner_grade=6)
    ids = {label: topics.anlegen(label, subject="mathematik") for label in labels}
    kind_modus_aktivieren(client)
    return ids


def test_der_knopf_merkt_sich_das_thema(client, fake_llm, app_env):
    ids = _bereit(client, fake_llm, app_env, LEKTION)
    token = csrf_from(client.get("/lernen?status=neu").text)

    client.post("/lernen/adaptiv/start",
                data={"_csrf": token, "thema": LEKTION,
                      "topic_id": str(ids[LEKTION])})

    eingabe = app_env.db.q1("SELECT * FROM lern_eingabe ORDER BY id DESC LIMIT 1")
    assert eingabe["topic_id"] == ids[LEKTION]
    assert eingabe["thema_text"] == LEKTION


def test_ein_getipptes_thema_bleibt_ohne_themen_id(client, fake_llm,
                                                   app_env):
    """Nicht jede Sitzung kommt von einer Karte — das darf nichts brechen."""
    _bereit(client, fake_llm, app_env, LEKTION)
    token = csrf_from(client.get("/lernen?status=neu").text)

    client.post("/lernen/adaptiv/start",
                data={"_csrf": token, "thema": "Brüche addieren"})

    eingabe = app_env.db.q1("SELECT * FROM lern_eingabe ORDER BY id DESC LIMIT 1")
    assert eingabe["topic_id"] is None


def test_laufende_sitzung_setzt_das_thema_auf_in_bearbeitung(
        client, fake_llm, app_env):
    """Der eigentliche Punkt: der Reiter zeigt echten Sitzungszustand."""
    ids = _bereit(client, fake_llm, app_env, LEKTION, "Brüche kürzen")
    token = csrf_from(client.get("/lernen?status=neu").text)
    assert LEKTION in client.get("/lernen?status=neu").text

    client.post("/lernen/adaptiv/start",
                data={"_csrf": token, "thema": LEKTION,
                      "topic_id": str(ids[LEKTION])})

    sitzung = app_env.db.q1("SELECT zustand FROM lern_sitzung ORDER BY id DESC LIMIT 1")
    assert sitzung["zustand"] == "DIAGNOSING"
    assert LEKTION in client.get("/lernen?status=bearbeitung").text
    assert LEKTION not in client.get("/lernen?status=neu").text
    # Ein unberührtes Thema wandert nicht mit.
    assert "Brüche kürzen" in client.get("/lernen?status=neu").text


def test_fremdes_topic_id_wird_nicht_uebernommen(client, fake_llm,
                                                 app_env):
    """Die ID kommt aus dem Formular — sie muss ein echtes aktives Thema sein."""
    _bereit(client, fake_llm, app_env, LEKTION)
    token = csrf_from(client.get("/lernen?status=neu").text)

    response = client.post("/lernen/adaptiv/start",
                           data={"_csrf": token, "thema": LEKTION, "topic_id": "999999"})

    eingabe = app_env.db.q1("SELECT * FROM lern_eingabe ORDER BY id DESC LIMIT 1")
    assert response.status_code == 404
    assert eingabe is None
    assert app_env.db.q("SELECT * FROM lern_sitzung") == []
