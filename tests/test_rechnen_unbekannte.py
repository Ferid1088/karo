"""Eine Gleichung mit Unbekannter ist keine falsche Rechnung.

Im Betrieb sind 261 von 262 Versuchen zu „Lineare Gleichungen lösen"
gescheitert — mit „«beispiel.frage» enthält eine Rechnung, die nachgerechnet
nicht aufgeht: Löse die Gleichung: x − 6 = 10". Das Modell hatte recht, die
Prüfung nicht: sie fand in dem Satz „6 = 10" und rechnete es nach.
"""
from __future__ import annotations

import pytest

from karo_contract import rechnen


@pytest.mark.parametrize("aufgabe", [
    "Löse die Gleichung: x − 6 = 10",
    "x - 9 = 5",
    "2x + 3 = 11",
    "Bestimme a: a · 5 = 20",
    "Wie groß ist y, wenn y / 4 = 3?",
    "3n − 7 = 14",
])
def test_gleichungen_mit_unbekannter_werden_nicht_nachgerechnet(aufgabe):
    """Ungeprüft ist richtig — falsch geprüft wäre schlimmer."""
    assert rechnen.stimmt(aufgabe) is None, aufgabe


@pytest.mark.parametrize("text,erwartet", [
    ("1/2 + 1/3 = 5/6", True),
    ("Rechne 1/4 + 1/6 = 5/12", True),
    ("Berechne 12 : 4 = 3", True),
    ("Du hast 3 Äpfel. 2 + 2 = 4, oder?", True),
    ("1/2 + 1/3 = 2/5", False),
    ("2 + 2 = 5", False),
    ("Das Ergebnis ist 3 · 4 = 11", False),
])
def test_echte_rechnungen_werden_weiter_geprueft(text, erwartet):
    """Der Riegel bleibt zu: eine falsche Rechnung faellt weiter auf."""
    assert rechnen.stimmt(text) is erwartet, text


def test_ein_satzanfang_ist_keine_unbekannte():
    """„Rechne 2 + 2 = 4" — das e von „Rechne" macht daraus keine Variable."""
    assert rechnen.stimmt("Rechne 2 + 2 = 4") is True
    assert rechnen.stimmt("Rechne 2 + 2 = 5") is False


def test_die_gefundenen_gleichungen_sind_einzeln_abfragbar():
    assert rechnen.gleichungen("x − 6 = 10") == []
    assert rechnen.gleichungen("1/2 + 1/3 = 5/6") == [("1/2 + 1/3", "5/6")]


def test_eine_lektion_zum_gleichungen_loesen_kommt_durch():
    """Der Fall, an dem es 261-mal scheiterte — jetzt von vorn bis hinten."""
    from karo_contract import schemas

    aufgabe = {"frage": "Löse die Gleichung: x − 6 = 10",
               "loesung": "x = 16",
               "typischer_fehler": "x = 4"}
    geprueft = schemas._aufgabe_pruefen(aufgabe, "beispiel")
    assert geprueft["loesung"] == "x = 16"


@pytest.mark.parametrize("text,erwartet", [
    # Der Doppelpunkt ist beides: Geteiltzeichen und Satzzeichen.
    ("Rechne die Kanten mal: 3 * 3 * 3 = 9.", False),     # Satzzeichen, falsche Rechnung
    ("Rechne die Kanten mal: 3 * 3 * 3 = 27.", True),     # Satzzeichen, richtige Rechnung
    ("Berechne 12 : 4 = 3", True),                        # Geteiltzeichen
    ("Berechne 12 : 4 = 5", False),
    ("Verhältnis: 3 : 4 = 6 : 8", True),                  # Verhaeltnis, stimmt
])
def test_der_doppelpunkt_ist_beides(text, erwartet):
    assert rechnen.stimmt(text) is erwartet, text
