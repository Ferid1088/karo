"""Zwei Lücken, die eine erzeugte Lektion sonst stillschweigend hätte.

**Hilfe.** „Das habe ich nicht verstanden" ist in jeder Phase ausser
COMPLETE erreichbar (02 §5, B3). Für eine erzeugte Lektion war dafür nichts
vorgesehen: `hilfe_fuer_phase()` hätte `None` geliefert, der Knopf wäre ins
Leere gegangen. Erzeugt wird die Hilfe zusammen mit der Lektion — zur
Laufzeit wird nichts nachgeladen, das wäre ein Modellaufruf im Moment der
Ratlosigkeit (A3).

**Rechnen.** Die Schemaprüfung sieht Struktur, nicht Wahrheit. Ein Modell,
das „2/3 + 1/6 = 4/9" behauptet, käme durch. Wo sich eine Aussage lokal
nachrechnen lässt, wird sie nachgerechnet — ohne zweites Modell.
"""
import copy

import pytest

from .test_lektion_erzeugung import _lektion
from .test_app import einrichten


# --------------------------------------------------------------------------
# Hilfe
# --------------------------------------------------------------------------

def test_eine_lektion_ohne_hilfe_wird_abgewiesen(app_env):
    from app.adaptiv import schemas
    daten = _lektion()
    daten.pop("hilfe", None)

    with pytest.raises(schemas.InhaltUngueltig, match="hilfe"):
        schemas.pruefe_lektion(daten)


def test_jede_phase_ausser_complete_braucht_hilfe(app_env):
    from app.adaptiv import schemas, sitzung
    daten = _lektion()
    del daten["hilfe"]["GUIDED_TASK"]

    with pytest.raises(schemas.InhaltUngueltig, match="GUIDED_TASK"):
        schemas.pruefe_lektion(daten)

    assert "COMPLETE" not in schemas.HILFE_PHASEN
    assert set(schemas.HILFE_PHASEN) == set(sitzung.PHASEN) - {"COMPLETE"}


def test_hilfe_darf_ein_registerbild_tragen(app_env):
    """Bilder der Hilfe gehen denselben Weg wie alle anderen (§3) — nicht
    über die Bruchstreifen, die es nur im Bruchkapitel gibt."""
    from app.adaptiv import schemas
    daten = _lektion()

    sauber = schemas.pruefe_lektion(daten)

    assert sauber["hilfe"]["RULE"]["visualisierung"]["component"] == \
        "GenericStepFlow"


def test_erfundene_komponente_auch_in_der_hilfe_abgewiesen(app_env):
    from app.adaptiv import schemas
    daten = _lektion()
    daten["hilfe"]["RULE"]["visualisierung"] = {
        "component": "CubePainter", "parameters": {}, "animation": "none"}

    with pytest.raises(schemas.InhaltUngueltig):
        schemas.pruefe_lektion(daten)


def test_die_hilfe_erreicht_das_kind(client, fake_llm, fake_cli, app_env):
    from app.adaptiv import erzeugung, inhalt_store, sitzung
    einrichten(client, fake_llm)

    konzept_id = erzeugung.speichern(_lektion())

    for phase in sitzung.PHASEN:
        hilfe = inhalt_store.hilfe_fuer_phase(konzept_id, phase)
        if phase == sitzung.COMPLETE:
            continue
        assert hilfe and hilfe["text"], phase
    assert len(inhalt_store.faq(konzept_id)) >= 2


def test_die_hilfe_ruft_kein_modell(client, fake_llm, fake_cli, app_env):
    """A3: Hilfe ist ein Lookup, kein Aufruf im Moment der Ratlosigkeit."""
    from app.adaptiv import erzeugung, inhalt_store, sitzung
    einrichten(client, fake_llm)
    konzept_id = erzeugung.speichern(_lektion())
    fake_llm.calls.clear()

    inhalt_store.hilfe_fuer_phase(konzept_id, sitzung.RULE)
    inhalt_store.faq(konzept_id)

    assert fake_llm.calls == []


# --------------------------------------------------------------------------
# Nachrechnen
# --------------------------------------------------------------------------

@pytest.mark.parametrize("ausdruck,erwartet", [
    ("2/3 + 1/6", "5/6"),
    ("1/2 + 1/3", "5/6"),
    ("3 * 3 * 3", "27"),
    ("12 - 4", "8"),
    ("2 + 2", "4"),
])
def test_richtige_rechnungen_gehen_durch(app_env, ausdruck, erwartet):
    from app.adaptiv import rechnen

    assert rechnen.stimmt(f"{ausdruck} = {erwartet}") is True


@pytest.mark.parametrize("behauptung", [
    "2/3 + 1/6 = 4/9",
    "3 * 3 * 3 = 9",
    "1/2 + 1/3 = 2/5",
    "12 - 4 = 9",
])
def test_falsche_rechnungen_fallen_auf(app_env, behauptung):
    from app.adaptiv import rechnen

    assert rechnen.stimmt(behauptung) is False


@pytest.mark.parametrize("text", [
    "Kante 3 cm — wie viele Würfelchen?",
    "Nimm die Kantenlänge dreimal mit sich selbst mal.",
    "Klasse 5 bis 6",
    "",
])
def test_was_sich_nicht_nachrechnen_laesst_wird_nicht_verworfen(app_env, text):
    """Nicht prüfbar heisst nicht falsch. Ein zu eifriger Prüfer würde
    ehrliche Aufgaben verwerfen."""
    from app.adaptiv import rechnen

    assert rechnen.stimmt(text) is None


def test_eine_falsche_rechnung_in_der_aufgabe_wird_abgewiesen(app_env):
    from app.adaptiv import schemas
    daten = _lektion()
    daten["fehlertypen"][0]["aufgaben"]["beispiel"] = {
        "frage": "2 * 2 * 2 = ?", "loesung": "9",
        "schritte": ["2 mal 2 ist 4"]}

    with pytest.raises(schemas.InhaltUngueltig, match="nachgerechnet"):
        schemas.pruefe_lektion(daten)


def test_eine_falsche_behauptung_im_erklaertext_wird_abgewiesen(app_env):
    from app.adaptiv import schemas
    daten = _lektion()
    daten["fehlertypen"][0]["erklaerung"]["regel"] = \
        "Rechne die Kanten mal: 3 * 3 * 3 = 9."

    with pytest.raises(schemas.InhaltUngueltig, match="nachgerechnet"):
        schemas.pruefe_lektion(daten)


def test_die_beschreibung_einer_fehlvorstellung_darf_falsch_rechnen(app_env):
    """„1/2 + 1/3 = 2/5" IST die Fehlvorstellung. Als Rechnung ist sie
    falsch — und genau deshalb steht sie da. Der Prüfer darf die Didaktik
    nicht kaputtmachen: Felder, die einen Fehler beschreiben, werden nicht
    nachgerechnet."""
    from app.adaptiv import schemas
    daten = _lektion()
    daten["fehlertypen"][0]["beschreibung"] = "Das Kind rechnet 1/2 + 1/3 = 2/5."

    sauber = schemas.pruefe_lektion(daten)

    assert "2/5" in sauber["fehlertypen"][0]["beschreibung"]
