"""Umlaute überleben die Normalisierung.

`normalisiere()` zerlegte den Text zuerst mit NFKD und ersetzte die Umlaute
erst danach. Nach der Zerlegung gibt es aber kein „ü" mehr, sondern „u" plus
ein kombinierendes Trema — die Ersetzungen liefen ins Leere, und das Trema
fiel anschließend als unerlaubtes Zeichen auf ein Leerzeichen zurück:

    „Brüche"  →  „bru che"

Das trifft zwei Stellen: die Lektionssuche (`lektionen.fuer_thema()`) findet
die Bruchlektion nicht mehr, und Tier 1 (`katalog`) vergleicht Aliase mit
Umlauten gegen zerschnittene Wörter — beides ohne Fehlermeldung.
"""
from .conftest import csrf_from
from .test_app import einrichten, kind_modus_aktivieren

PFAD = "/lernen/adaptiv"


def test_umlaute_werden_ausgeschrieben(app_env):
    from app.adaptiv.normalisierung import normalisiere

    assert normalisiere("Brüche") == "brueche"
    assert normalisiere("Brüche addieren und subtrahieren") == \
        "brueche addieren und subtrahieren"
    assert normalisiere("Zähler") == "zaehler"
    assert normalisiere("Größe") == "groesse"
    assert normalisiere("Maß") == "mass"


def test_auch_zerlegt_eingegebene_umlaute(app_env):
    """Manche Tastaturen und Zwischenablagen liefern „u" + Trema getrennt.
    Für das Kind ist das dasselbe Wort."""
    from app.adaptiv.normalisierung import normalisiere

    assert normalisiere("Brüche") == normalisiere("Brüche")


def test_gleichwertig_erkennt_umlaut_schreibweisen(app_env):
    from app.adaptiv.normalisierung import ist_gleichwertig

    assert ist_gleichwertig("Brüche", "BRUECHE")
    assert not ist_gleichwertig("Brüche", "Brote")


def test_brueche_addieren_findet_die_bruchlektion(client, fake_llm, fake_cli,
                                                  app_env):
    """Der Fall, der den Fehler sichtbar gemacht hat.

    „Brüche addieren und subtrahieren" ist genau die vorhandene Lektion.
    Vorher normalisierte das zu „bru che addieren und subtrahieren" — weder
    ein Stichwort noch ein Teil des Labels — und Karo sagte, es gebe dazu
    keine Lernreihe.
    """
    from app.adaptiv import lektionen
    einrichten(client, fake_llm)

    lektion = lektionen.fuer_thema("Brüche addieren und subtrahieren")

    assert lektion is not None
    assert lektion["konzept_key"] == "ungleichnamig-addieren"


def test_das_kind_landet_in_der_lektion_statt_in_der_absage(
        client, fake_llm, fake_cli, app_env):
    """Derselbe Weg, den das Kind wirklich geht."""
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True)
    kind_modus_aktivieren(client)
    token = csrf_from(client.get(PFAD).text)

    seite = client.post(f"{PFAD}/start",
                        data={"_csrf": token,
                              "thema": "Brüche addieren und subtrahieren"})

    assert "noch keine Lernreihe" not in seite.text
    sitzung = app_env.db.q1("SELECT * FROM lern_sitzung ORDER BY id DESC LIMIT 1")
    assert sitzung is not None
    assert sitzung["zustand"] == "DIAGNOSING"


def test_ein_fremdes_thema_trifft_weiterhin_nicht(client, fake_llm, fake_cli,
                                                  app_env):
    """Die Reparatur darf die Ehrlichkeit aus `lektionen.py` nicht aufweichen:
    was es nicht gibt, wird weiter gesagt.

    Welche Bruchthemen die Additionslektion treffen dürfen, entscheidet
    `lektionen.STICHWORTE` — geprüft in `test_lektionen_zuordnung.py`,
    nicht hier. Diese Datei hält nur fest, dass die Normalisierung nichts
    aufweicht.
    """
    from app.adaptiv import lektionen
    einrichten(client, fake_llm)

    assert lektionen.fuer_thema("Photosynthese") is None
    assert lektionen.fuer_thema("Wurzeln ziehen") is None
