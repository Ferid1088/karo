"""Zahlen rechnet der Code, Sprache schreibt das Modell.

Ein Sprachmodell formuliert gut und rechnet schlecht. Im Protokoll standen
beide nebeneinander: schöne Aufgabenstellungen und darin Rechnungen, die nicht
aufgingen. Mit einer Vorlage wird die Lösung **gerechnet** statt behauptet —
dann kann sie nicht falsch sein.
"""
from __future__ import annotations

import pytest

from karo_contract import aufgaben, rechnen, schemas

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


# ------------------------------------------ Gleichungen mit Unbekannter

@pytest.mark.parametrize("gleichung,erwartet", [
    ("10x - 4 = 8x + 10", ("x", "7")),
    ("6x − 4 = 2x + 8", ("x", "3")),
    ("x - 6 = 10", ("x", "16")),
    ("3y + 2 = 11", ("y", "3")),
])
def test_lineare_gleichungen_werden_geloest(gleichung, erwartet):
    """Gesucht ist x, nicht ein Zahlenwert — „ausrechnen" reicht hier nicht."""
    assert aufgaben.loesen(gleichung) == erwartet


def test_eine_gleichung_ohne_eindeutige_loesung_wird_gemeldet():
    with pytest.raises(aufgaben.VorlageUnbrauchbar, match="keine eindeutige"):
        aufgaben.loesen("2x + 1 = 2x + 5")


def test_ohne_unbekannte_ist_der_loeser_nicht_zustaendig():
    assert aufgaben.loesen("1/2 + 1/3 = 5/6") is None
    assert aufgaben.loesen("3 + 4") is None


def test_eine_gleichungsvorlage_wird_zur_fertigen_aufgabe():
    """Der Fall, der den Generator ausgelöst hat."""
    vorlage = {"vorlage": "{a}x - {b} = {c}x + {d}", "frage": "Löse: {aufgabe}",
               "bedingungen": ["a > c", "b < 20", "d < 20", "(b + d) % (a - c) == 0"]}
    fertig = aufgaben.bauen(vorlage, seed="MA.GLEICHUNGEN:1",
                            fehler_key="vorzeichen_vergessen")
    assert fertig["loesung"].startswith("x = ")
    # Die Loesung stimmt wirklich: eingesetzt geht die Gleichung auf.
    from fractions import Fraction
    x = Fraction(fertig["loesung"].split("=", 1)[1].strip())
    a, b, c, d = (fertig["belegung"][k] for k in "abcd")
    assert a * x - b == c * x + d


def test_eine_aufloesung_darf_einen_widerspruch_vorrechnen():
    """„Nach Abziehen von 2x steht 4 = 9, und das ist falsch."

    Eine Prüfung, die diesen Satz verbietet, verbietet das Vorrechnen eines
    Widerspruchs — eine der ältesten Beweisformen im Unterricht.
    """
    geprueft = schemas._aufgabe_pruefen(
        {"frage": "Welche Umformung stimmt?", "loesung": "A",
         "optionen": ["A", "B"],
         "aufloesung": "Bei B steht nach dem Abziehen 4 = 9, und das ist falsch."},
        "vorhersage")
    assert "4 = 9" in geprueft["aufloesung"]


def test_eine_regel_darf_weiter_nicht_falsch_rechnen():
    """Der Riegel bleibt dort, wo eine Aussage wahr sein muss."""
    with pytest.raises(schemas.InhaltUngueltig, match="nachgerechnet"):
        schemas._nachrechnen("Rechne so: 2 + 2 = 5.", "fehlertyp[0].erklaerung.regel")
    schemas._nachrechnen("Rechne so: 2 + 2 = 4.", "fehlertyp[0].erklaerung.regel")


# ------------------------------------------------------ Adversarial (DSL)
#
# Alles, was ein Modell an der Vorlage verbiegen kann, muss abgewiesen
# werden — sauber als Befund, nie als Absturz und nie als `ready`.

def _abweisend(vorlage: dict):
    with pytest.raises(schemas.InhaltUngueltig, match="keine Aufgabe"):
        schemas._aufgabe_pruefen(
            {"frage": "x", "loesung": "y", "vorlage": vorlage},
            "beispiel", seed="adv")


def test_bedingungen_muessen_eine_liste_sein():
    _abweisend({"vorlage": "{a} + {b}", "bedingungen": "b != d"})


@pytest.mark.parametrize("bereich", [
    [900, 100],          # umgedreht
    "abc",               # Text statt Zahlenpaar
    [1, 12, 3],          # drei Werte
    [1.5, 12],           # keine ganzen Zahlen
    [1, 10**9],          # absurd groß
    5,                   # kein Paar
])
def test_ein_ungueltiger_bereich_wird_abgewiesen(bereich):
    _abweisend({"vorlage": "{a} + {b}", "bereich": bereich})


def test_ein_gueltiger_bereich_ausserhalb_der_vorgabe_funktioniert():
    """`k % 100 == 0` braucht eben mehr als 1–12 — das ist der Sinn von
    `bereich`, kein Missbrauch."""
    fertig = aufgaben.bauen(
        {"vorlage": "{k} / 100", "bedingungen": ["k % 100 == 0"],
         "bereich": [100, 900]}, seed="s")
    assert fertig["belegung"]["k"] % 100 == 0
    assert 100 <= fertig["belegung"]["k"] <= 900


def test_eine_bedingung_darf_nicht_potenzieren():
    """`a ** 999999` ist gültige Syntax und eine DoS-Falle in jedem Wurf."""
    with pytest.raises(aufgaben.VorlageUnbrauchbar):
        aufgaben.erfuellt(["a ** 999999 > 0"], {"a": 2})


def test_division_durch_null_in_bedingung_und_aufgabe():
    # In der Bedingung: 0 wird als Belegung verworfen, nicht ausgewertet —
    # bleibt nur die 0, erschoepft sich der Wuerfel ehrlich.
    with pytest.raises(aufgaben.VorlageUnbrauchbar, match="Bedingungen"):
        aufgaben.belegen("{b}", ["10/b > 1"], seed="s", bereich=(0, 0))
    # In der Aufgabe selbst: „1/0" ist nicht rechenbar.
    with pytest.raises(aufgaben.VorlageUnbrauchbar):
        aufgaben.bauen({"vorlage": "1/{b}", "bereich": [0, 0]}, seed="s")


def test_eine_vorlage_ohne_rechnung_ist_keine_aufgabe():
    _abweisend({"vorlage": "Hallo {a}", "frage": "Sag: {aufgabe}"})
    _abweisend({"vorlage": "{a} Äpfel und {b} Birnen"})


def test_die_gerechnete_loesung_ersetzt_eine_falsch_behauptete():
    """Die „inkonsistente Lösung" kann im Vorlagenpfad nicht entstehen —
    sie wird gar nicht erst gelesen."""
    geprueft = schemas._aufgabe_pruefen(
        {"frage": "egal", "loesung": "42", "vorlage": BRUCH},
        "beispiel", seed="konsistenz")
    assert rechnen.stimmt(f"{geprueft['loesung']}") is not False


# ------------------------------------------------------ Happy path (DSL)
#
# §12: dieselbe Vorlage muss je Seed andere gültige Aufgaben liefern —
# fachlich äquivalent, rechnerisch richtig, verschieden im Text.

def test_drei_seeds_drei_verschiedene_gueltige_aufgaben():
    gebaut = [aufgaben.bauen(BRUCH, seed=f"variante:{n}") for n in (1, 2, 3)]
    fragen = {g["frage"] for g in gebaut}
    assert len(fragen) == 3, "die Varianten unterscheiden sich nicht"
    for g in gebaut:
        a, b, c, d = (g["belegung"][k] for k in "abcd")
        # Alle Bedingungen gelten — das ist der didaktische Kern.
        assert b != d and a < b and c < d and aufgaben.kgv(b, d) <= 24
        # Die Lösung ist gerechnet, nicht behauptet.
        from fractions import Fraction
        assert Fraction(g["loesung"]) == Fraction(a, b) + Fraction(c, d)
        # Der Kindertext enthält die Aufgabe, keinen Platzhalter.
        assert "{" not in g["frage"] and g["ausdruck"] in g["frage"]
