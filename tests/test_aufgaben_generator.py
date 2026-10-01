"""Zahlen rechnet der Code, Sprache schreibt das Modell.

Ein Sprachmodell formuliert gut und rechnet schlecht. Im Protokoll standen
beide nebeneinander: schöne Aufgabenstellungen und darin Rechnungen, die nicht
aufgingen. Mit einer Vorlage wird die Lösung **gerechnet** statt behauptet —
dann kann sie nicht falsch sein.
"""
from __future__ import annotations

import pytest

from karo_contract import aufgaben, schemas

BRUCH = {"vorlage": "{a}/{b} + {c}/{d}",
         "frage": "Rechne {aufgabe}.",
         "bedingungen": ["b != d", "a < b", "c < d", "b > 1", "d > 1",
                         "kgv(b,d) <= 24"]}


# ------------------------------------------------------------ Bedingungen

def test_der_generator_haelt_alle_bedingungen_ein():
    """Die Bedingungen sind der didaktische Teil — sie sind keine Bitte."""
    for n in range(40):
        b = aufgaben.belegen(BRUCH["vorlage"], BRUCH["bedingungen"], seed=f"L{n}")
        assert b["b"] != b["d"]
        assert b["a"] < b["b"] and b["c"] < b["d"]
        assert b["b"] > 1 and b["d"] > 1
        assert aufgaben.kgv(b["b"], b["d"]) <= 24


def test_unerfuellbare_bedingungen_werden_gemeldet_statt_gebogen():
    with pytest.raises(aufgaben.VorlageUnbrauchbar, match="Bedingungen"):
        aufgaben.belegen("{a}", ["a > 100"], seed="x", bereich=(1, 9))


def test_eine_bedingung_darf_nur_rechnen():
    """Hier wird Text ausgewertet, der aus einem Modell kommt."""
    for boese in ["__import__('os').system('ls')", "open('/etc/passwd')",
                  "a.__class__", "lambda: 1"]:
        with pytest.raises(aufgaben.VorlageUnbrauchbar):
            aufgaben.erfuellt([boese], {"a": 1})


def test_eine_kaputte_bedingung_ist_ein_fehler_keine_stille_wahrheit():
    with pytest.raises(aufgaben.VorlageUnbrauchbar, match="nicht auswertbar"):
        aufgaben.erfuellt(["a > z"], {"a": 1})


# ------------------------------------------------------------ Die Lösung

def test_die_loesung_wird_gerechnet_nicht_behauptet():
    fertig = aufgaben.bauen(BRUCH, seed="MA.BRUECHE:1")
    from fractions import Fraction
    a, b, c, d = (fertig["belegung"][k] for k in "abcd")
    assert fertig["loesung"] == str(Fraction(a, b) + Fraction(c, d)).replace(" ", "")
    # Und sie überlebt den Validator, der sie noch einmal nachrechnet.
    from karo_contract import rechnen
    assert rechnen.stimmt(f"{fertig['ausdruck']} = {fertig['loesung']}") is True


def test_gleicher_seed_gleiche_aufgaben():
    """Sonst stünde in der Datenbank eine andere Aufgabe als im Material."""
    eins = aufgaben.bauen(BRUCH, seed="MA.BRUECHE:1")
    zwei = aufgaben.bauen(BRUCH, seed="MA.BRUECHE:1")
    drei = aufgaben.bauen(BRUCH, seed="MA.BRUECHE:2")
    assert eins == zwei
    assert eins["frage"] != drei["frage"]


def test_die_frage_bleibt_ein_satz():
    fertig = aufgaben.bauen(BRUCH, seed="s")
    assert fertig["frage"].startswith("Rechne ")
    assert fertig["ausdruck"] in fertig["frage"]


# -------------------------------------------------- Der typische Fehler

def test_der_typische_fehler_wird_gerechnet_wo_die_regel_bekannt_ist():
    """„Zähler und Nenner addiert" ist eine Rechenvorschrift, keine Erfindung."""
    fertig = aufgaben.bauen(BRUCH, seed="s", fehler_key="zaehler_und_nenner_addiert")
    a, b, c, d = (fertig["belegung"][k] for k in "abcd")
    assert fertig["typischer_fehler"] == f"{a + c}/{b + d}"
    assert fertig["typischer_fehler"] != fertig["loesung"]


def test_ohne_bekannte_fehlvorstellung_schlaegt_das_modell_vor():
    fertig = aufgaben.bauen(BRUCH, seed="s", fehler_key="etwas_unbekanntes")
    assert "typischer_fehler" not in fertig


def test_eine_fehlerfunktion_die_nicht_passt_wirft_die_aufgabe_nicht_weg():
    # „vorzeichen_vergessen“ braucht a und b, die Bruchvorlage hat auch c, d —
    # die Funktion passt, liefert aber Unsinn für diese Vorlage. Entscheidend
    # ist: die Aufgabe entsteht trotzdem.
    fertig = aufgaben.bauen({"vorlage": "{a} + {b}"}, seed="s",
                            fehler_key="mal_statt_geteilt")
    assert fertig["loesung"] and fertig["frage"]


# ----------------------------------------------- Im Zusammenspiel

def test_eine_aufgabe_mit_vorlage_kommt_durch_die_pruefung():
    geprueft = schemas._aufgabe_pruefen(
        {"frage": "egal, wird ersetzt", "loesung": "99",
         "typischer_fehler": "98", "vorlage": BRUCH},
        "gefuehrt", seed="MA.BRUECHE", fehler_key="zaehler_und_nenner_addiert")
    assert geprueft["frage"].startswith("Rechne ")
    assert geprueft["loesung"] != "99", "die behauptete Lösung wurde ersetzt"
    assert geprueft["typischer_fehler"] != "98"


def test_ohne_vorlage_bleibt_alles_wie_bisher():
    geprueft = schemas._aufgabe_pruefen(
        {"frage": "Wie viele Seiten hat ein Würfel?", "loesung": "6"}, "beispiel")
    assert geprueft["loesung"] == "6"


def test_eine_unbrauchbare_vorlage_wird_abgewiesen():
    with pytest.raises(schemas.InhaltUngueltig, match="ergibt keine Aufgabe"):
        schemas._aufgabe_pruefen(
            {"frage": "x", "loesung": "y",
             "vorlage": {"vorlage": "{a}/{b}", "bedingungen": ["b > 999"]}},
            "beispiel", seed="s")


def test_der_validator_faengt_eine_absichtlich_falsche_ausgabe_weiter_ab():
    """Der Riegel bleibt zu — auch wenn jetzt meistens der Code rechnet."""
    with pytest.raises(schemas.InhaltUngueltig, match="nicht zur Frage"):
        schemas._aufgabe_pruefen({"frage": "1/2 + 1/3 = ?", "loesung": "2/5"},
                                 "beispiel")
    # Und eine falsche Rechnung im Fragetext ebenso.
    with pytest.raises(schemas.InhaltUngueltig, match="nachgerechnet"):
        schemas._aufgabe_pruefen({"frage": "Es gilt 1/2 + 1/3 = 2/5.", "loesung": "x"},
                                 "beispiel")


def test_eine_falsche_loesung_im_satz_faellt_dem_validator_nicht_auf():
    """Bekannte Luecke, und der Grund fuer den Generator.

    `loesung_stimmt` kann nur blanke Ausdruecke nachrechnen. Steht die
    Aufgabe in einem Satz („Rechne 1/2 + 1/3."), prueft niemand die Loesung —
    das Modell koennte 2/5 behaupten. Mit Vorlage kann es das nicht, weil
    die Loesung dann gar nicht vom Modell kommt.
    """
    durch = schemas._aufgabe_pruefen({"frage": "Rechne 1/2 + 1/3.", "loesung": "2/5"},
                                     "beispiel")
    assert durch["loesung"] == "2/5", "heute faellt das durch — siehe Generator"


# ------------------------------------------------------- Kleiner-als

@pytest.mark.parametrize("text", [
    "<script>alert(1)</script>", "<div>", "</p>", "<!-- x -->",
    "&lt;script&gt;", "<svg onload=1>", "<img src=x onerror=1>",
    "javascript:alert(1)",
])
def test_markup_wird_weiter_abgewiesen(text):
    """Der Riegel aus A1 bleibt zu."""
    assert schemas.enthaelt_markup(text) is True, text


@pytest.mark.parametrize("text", [
    "a < b", "wenn a < b ist, dann …", "3 < 5", "x <= y",
    "Bedingung: kgv(b,d) <= 24",
])
def test_ein_kleiner_als_ist_kein_markup(text):
    """„a < b" ist eine Bedingung, kein Element.

    Vorher verbot diese Pruefung jedes Kleiner-als in Aufgaben und
    Erklaerungen — ein Browser liest „< b" nicht als Element.
    """
    assert schemas.enthaelt_markup(text) is False, text
