"""Die Begriffs-Rubrik bewertet offene Antworten lokal und ehrlich.

Vier Lagen, kein bool mehr: `richtig` bei voller Begriffsabdeckung,
`teilweise` mit den fehlenden Begriffen (Karo unterrichtet nur dieses
Stück), `falsch` mit Misconception-Metadaten bei einer erkannten
Fehlvorstellung — und `unbekannt`, wenn nichts Einordbares dasteht.
Unbekannt ist keine falsche Antwort: die Rubrik liefert eine Klärungs-
aufgabe mit, die deterministisch ausgewertet wird. Nichts davon ruft
ein Modell.
"""
import pytest

from app.adaptiv.antwortvergleich import (
    FALSCH, RICHTIG, TEILWEISE, UNBEKANNT, bewerte, bewerte_klaerung)


# Die Zellatmungs-Rubrik aus dem Brief — Konzeptlisten tragen die
# Schreibweisen mit, die ein Kind realistisch benutzt.
BIO_RUBRIK = {
    "begriffe": [
        ["sauerstoff", "o2", "sauerstoff wird gebraucht",
         "benötigt sauerstoff"],
        ["glucose", "traubenzucker", "glukose"],
        ["energie", "energie wird frei", "atp"],
    ],
    "missverstaendnisse": [
        {"begriffe": ["nur in der lunge", "atmen ist zellatmung",
                      "zellatmung findet in der lunge"],
         "key": "F1",
         "hinweis": "Zellatmung läuft in jeder Zelle, nicht nur in der Lunge."},
    ],
    "klaerung": {
        "frage": "Welche Aussage meinst du?",
        "loesung": "In den Zellen wird Energie frei",
        "optionen": ["In den Zellen wird Energie frei",
                     "Die Lunge atmet für die Zellen",
                     "Zellatmung ist das Einatmen von Luft"],
    },
    "hinweise": {"teilweise": "Ein Teil deiner Erklärung fehlt noch.",
                 "unbekannt": "Das kann ich noch nicht einordnen."},
}


@pytest.mark.parametrize("antwort", [
    "Die Zelle nimmt Sauerstoff auf, baut Glucose ab und Energie wird frei.",
    "Mit O2 wird Traubenzucker abgebaut, dabei wird ATP gewonnen.",
    "Benötigt Sauerstoff, zersetzt Glukose und setzt Energie frei.",
    "sauerstoff + glucose = energie",          # knapp, alle Begriffe
    "Die Zelle benötigt Sauerstoff und Glukose, um Energie freizusetzen.",
])
def test_biologie_vollstaendig_und_paraphrasen_richtig(antwort):
    befund = bewerte(antwort, "", "begriffe", BIO_RUBRIK)
    assert befund["urteil"] == RICHTIG
    assert befund["fehlende"] == []


@pytest.mark.parametrize("antwort,fehlend", [
    ("Zellatmung braucht Sauerstoff.", ["glucose", "energie"]),
    ("Die Zelle braucht Sauerstoff und Glucose.", ["energie"]),
    ("Glucose wird zu Energie abgebaut.", ["sauerstoff"]),
])
def test_biologie_teilantwort_ist_teilweise(antwort, fehlend):
    befund = bewerte(antwort, "", "begriffe", BIO_RUBRIK)
    assert befund["urteil"] == TEILWEISE
    for stueck in fehlend:
        assert stueck in befund["fehlende"]
    assert befund["hinweis"] == "Ein Teil deiner Erklärung fehlt noch."


@pytest.mark.parametrize("antwort", [
    "Zellatmung findet nur in der Lunge statt.",
    "Die Zelle nimmt Sauerstoff auf, baut Glucose ab und Energie wird frei, "
    "aber Zellatmung findet in der Lunge statt.",   # richtiger Kern + falscher Zusatz
])
def test_misconception_schlaegt_vollstaendige_antwort(antwort):
    befund = bewerte(antwort, "", "begriffe", BIO_RUBRIK)
    assert befund["urteil"] == FALSCH
    assert befund["missverstaendnis"] == "F1"


@pytest.mark.parametrize("antwort", [
    "weiß nicht",
    "weil es wichtig ist",
    "Mitochondrien sind toll.",
    "Sie macht, dass wir leben.",
    "",                                             # leere Antwort
])
def test_uneinordbares_ist_unbekannt_mit_klaerung(antwort):
    befund = bewerte(antwort, "", "begriffe", BIO_RUBRIK)
    assert befund["urteil"] == UNBEKANNT
    assert befund["klaerung"]["frage"] == "Welche Aussage meinst du?"


@pytest.mark.parametrize("antwort", [
    "In den Zellen wird Energie frei",              # Auswahl per Text
    "A",                                            # per Buchstabe
    "1",                                            # per Nummer
])
def test_klaerung_richtige_auswahl(antwort):
    assert bewerte_klaerung(antwort, BIO_RUBRIK["klaerung"])["urteil"] == RICHTIG


@pytest.mark.parametrize("antwort", [
    "B", "3", "Die Lunge atmet für die Zellen", "irgendwas",
])
def test_klaerung_falsche_auswahl(antwort):
    assert bewerte_klaerung(antwort, BIO_RUBRIK["klaerung"])["urteil"] == FALSCH


def test_klaerung_kurzantwort_akzeptiert_varianten():
    kurz = {"frage": "Welcher Stoff wird abgebaut?",
            "loesung": "Glucose",
            "akzeptiert": ["Traubenzucker", "Glukose"]}
    assert bewerte_klaerung("Traubenzucker!", kurz)["urteil"] == RICHTIG
    assert bewerte_klaerung("Wasser", kurz)["urteil"] == FALSCH


def test_klaerung_fehlerhaft_wirft_nie():
    assert bewerte_klaerung("A", None)["urteil"] == FALSCH
    assert bewerte_klaerung("A", {})["urteil"] == FALSCH


# --- Matrix übers Fachgebiet hinweg -------------------------------------

ENGLISCH_RUBRIK = {
    "begriffe": [["have", "has"], ["past participle", "pp", "3. form",
                                  "third form", "partizip"]],
    "missverstaendnisse": [{"begriffe": ["simple past"], "key": "F2"}],
    "klaerung": {"frage": "Welche Zeitform meinst du?",
                 "loesung": "Present Perfect",
                 "optionen": ["Present Perfect", "Simple Past"]},
}


@pytest.mark.parametrize("antwort", [
    "You use have plus the past participle.",
    "has + 3. Form",
    "mit have und dem Partizip",
])
def test_englisch_varianten_richtig(antwort):
    assert bewerte(antwort, "", "begriffe", ENGLISCH_RUBRIK)["urteil"] == RICHTIG


def test_englisch_falsche_zeitform_ist_misconception():
    befund = bewerte("You use the simple past with have.", "", "begriffe",
                     ENGLISCH_RUBRIK)
    assert befund["urteil"] == FALSCH
    assert befund["missverstaendnis"] == "F2"


def test_englisch_teilantwort():
    assert bewerte("You need have.", "", "begriffe",
                   ENGLISCH_RUBRIK)["urteil"] == TEILWEISE


DEUTSCH_RUBRIK = {
    "begriffe": [["hauptsatz"], ["nebensatz"], ["verb", "verb steht am ende"]],
}


@pytest.mark.parametrize("antwort", [
    "Der Hauptsatz hat das Verb normal, im Nebensatz steht das Verb am Ende.",
    "hauptsatz und nebensatz unterscheiden sich im verb",
])
def test_deutsch_paraphrasen(antwort):
    assert bewerte(antwort, "", "begriffe", DEUTSCH_RUBRIK)["urteil"] == RICHTIG


def test_deutsch_falscher_fachbegriff_teilweise():
    # „Subjekt“ statt Nebensatz: ein Begriff trifft, der Rest fehlt.
    befund = bewerte("Der Hauptsatz hat ein Subjekt und das Verb.", "",
                     "begriffe", DEUTSCH_RUBRIK)
    assert befund["urteil"] == TEILWEISE


PHYSIK_RUBRIK = {
    "begriffe": [["weg", "strecke", "distanz"], ["zeit", "zeitdauer"],
                 ["geteilt", "dividiert", "durch"]],
    "missverstaendnisse": [{"begriffe": ["weg mal zeit", "strecke mal zeit"],
                            "key": "F3"}],
    "klaerung": {"frage": "Welche Formel meinst du?",
                 "loesung": "v = s / t",
                 "optionen": ["v = s / t", "v = s * t", "v = t / s"]},
}


@pytest.mark.parametrize("antwort", [
    "Geschwindigkeit ist Weg geteilt durch Zeit.",
    "strecke dividiert durch zeitdauer",
    "Man rechnet die Distanz durch die Zeit.",
])
def test_physik_begruendung_andere_wortwahl(antwort):
    assert bewerte(antwort, "", "begriffe", PHYSIK_RUBRIK)["urteil"] == RICHTIG


def test_physik_falscher_zusammenhang_misconception():
    befund = bewerte("Geschwindigkeit ist Weg mal Zeit.", "", "begriffe",
                     PHYSIK_RUBRIK)
    assert befund["urteil"] == FALSCH
    assert befund["missverstaendnis"] == "F3"


CHEMIE_RUBRIK = {
    "begriffe": [["wasserstoff", "h2"], ["sauerstoff", "o2"],
                 ["wasser", "h2o"]],
    "missverstaendnisse": [{"begriffe": ["wasser aus luft",
                                        "wasser entsteht aus luft"],
                            "key": "F4"}],
}


def test_chemie_teilantwort_und_fehlvorstellung():
    assert bewerte("Wasserstoff reagiert mit Sauerstoff.", "", "begriffe",
                   CHEMIE_RUBRIK)["urteil"] == TEILWEISE
    befund = bewerte("Wasser entsteht aus Luft.", "", "begriffe", CHEMIE_RUBRIK)
    assert befund["urteil"] == FALSCH
    assert befund["missverstaendnis"] == "F4"


# --- Adversarial ---------------------------------------------------------

def test_sehr_lange_richtige_antwort_mit_irrelevantem_zusatz():
    antwort = ("Ich habe gelernt, dass die Zellatmung in den Mitochondrien "
               "stattfindet. Die Zelle nimmt Sauerstoff auf und baut die "
               "Glucose ab. Dabei wird Energie frei, die der Körper nutzt. "
               "Mein Lieblingstier ist übrigens der Dachs.")
    assert bewerte(antwort, "", "begriffe", BIO_RUBRIK)["urteil"] == RICHTIG


def test_reihenfolge_vertauscht():
    antwort = "Energie wird frei, wenn Glucose mit Sauerstoff abgebaut wird."
    assert bewerte(antwort, "", "begriffe", BIO_RUBRIK)["urteil"] == RICHTIG


def test_tippfehler_zaehlt_ehrlich():
    # „Sauerstof" und „Glucos" treffen die geforderten Begriffe nicht —
    # die Rubrik erfindet keine Treffer. Was bleibt, ist „energie": eine
    # ehrliche Teil-Leistung statt eines geratenen „richtig".
    antwort = "Sauerstof und Glucos machen Energie."
    befund = bewerte(antwort, "", "begriffe", BIO_RUBRIK)
    assert befund["urteil"] == TEILWEISE


def test_widerspruch_innerhalb_der_antwort_ist_nie_richtig():
    antwort = ("Pflanzen brauchen Sauerstoff und Glucose für Energie, "
               "aber Zellatmung findet in der Lunge statt.")
    assert bewerte(antwort, "", "begriffe", BIO_RUBRIK)["urteil"] == FALSCH


def test_mindestens_schwelle():
    rubrik = {"begriffe": ["a", "b", "c", "d"], "mindestens": 3}
    assert bewerte("a b c", "", "begriffe", rubrik)["urteil"] == RICHTIG
    assert bewerte("a b", "", "begriffe", rubrik)["urteil"] == TEILWEISE


def test_unbekannt_nicht_als_falsch_verwischt():
    befund = bewerte("keine Ahnung", "", "begriffe", BIO_RUBRIK)
    assert befund["urteil"] == UNBEKANNT
    assert befund["urteil"] != FALSCH


def test_rubrik_ohne_begriffe_ist_falsch_kein_absturz():
    assert bewerte("irgendwas", "", "begriffe", {})["urteil"] == FALSCH
    assert bewerte("irgendwas", "", "begriffe",
                   {"begriffe": []})["urteil"] == FALSCH


def test_bewerte_wirft_nie():
    for rubrik in (None, {}, {"begriffe": "kaputt"},
                   {"begriffe": [None, 42]}, {"begriffe": [["a"]]}):
        urteil = bewerte("x", "", "begriffe", rubrik)["urteil"]
        assert urteil in (RICHTIG, TEILWEISE, FALSCH, UNBEKANNT)


# --------------------------------------------------------------------------
# Negation und Teilwort-Kollisionen — begriff genannt heisst nicht
# begriff gemeint.
# --------------------------------------------------------------------------

def test_negierter_begriff_zaehlt_nicht():
    """„braucht keinen Sauerstoff" nennt den Begriff, meint das
    Gegenteil — und darf nicht als Abdeckung zählen."""
    befund = bewerte(
        "Die Zelle braucht keinen Sauerstoff, baut aber Glucose ab "
        "und setzt Energie frei.",
        "", "begriffe", BIO_RUBRIK)
    assert befund["urteil"] == TEILWEISE
    assert any("sauerstoff" in f for f in befund["fehlende"])


def test_negierte_misconception_ist_kein_treffer():
    """„findet nicht nur in der Lunge statt" ist richtiges Wissen —
    die Negation darf den Misconception-Schutz nicht auslösen."""
    befund = bewerte("Zellatmung findet nicht nur in der Lunge statt, "
                     "sondern in jeder Zelle.",
                     "", "begriffe",
                     {"begriffe": [["zellatmung"]],
                      "missverstaendnisse": BIO_RUBRIK["missverstaendnisse"]})
    assert befund.get("missverstaendnis") is None


def test_alles_negiert_ist_unbekannt_statt_richtig():
    befund = bewerte("Ohne Sauerstoff, ohne Glucose, ohne Energie.",
                     "", "begriffe", BIO_RUBRIK)
    assert befund["urteil"] == UNBEKANNT


@pytest.mark.parametrize("antwort", [
    "Der Kraftstoff ist wichtig.",          # „kraftstoff" ≠ „kraft"
    "Das Atommodell hilft beim Denken.",    # „atommodell" ≠ „atom"
    "Ein Lichtjahr ist sehr weit.",         # „lichtjahr" ≠ „licht"
    "Wasserstoff ist ein Gas.",             # „wasserstoff" ≠ „wasser"
])
def test_teilwort_kollisionen_treffen_nicht(antwort):
    rubrik = {"begriffe": ["kraft", "atom", "licht", "wasser"]}
    befund = bewerte(antwort, "", "begriffe", rubrik)
    assert befund["urteil"] != RICHTIG


def test_flexion_bleibt_treffer():
    """Kurze Endung ist Flexion, keine Kollision."""
    rubrik = {"begriffe": ["sauerstoff", "energie"]}
    assert bewerte("Sauerstoffe sind Energien pur.", "", "begriffe",
                   rubrik)["urteil"] == RICHTIG
