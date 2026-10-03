"""Der Antwortvergleich wertet fachlich, nicht buchstabengenau.

Früher kannte `ist_richtig` nur denselben Bruchwert oder dieselbe
Zeichenkette: „2/4" auf „1/2" ging durch, „0,5" und „5 = x" waren
falsch — mathematisch dieselbe Antwort, als falsch gewertet. Diese
Faelle decken den Validator je `antwort_art` ab; was nicht sicher
verglichen werden kann, darf nie abstuerzen und nie wahllos richtig sein.
"""
import pytest

from app.adaptiv.antwortvergleich import check_answer


@pytest.mark.parametrize("antwort,loesung,art", [
    ("1/2", "2/4", "bruch"),
    ("2/4", "1/2", "bruch"),
    ("0.5", "1/2", "bruch"),
    ("0,5", "1/2", "bruch"),
    ("1/2", "0,5", "dezimal"),
    ("2/3 + 1/6", "5/6", "bruch"),          # Rechenweg statt Ergebnis
    ("12 : 4", "3", "bruch"),               # Doppelpunkt als Geteilt
    ("-2/4", "-1/2", "bruch"),
    ("x = 5", "5 = x", "gleichung"),
    ("x = 5", "5 = x", None),               # ohne antwort_art: auto
    ("5", "x = 5", "gleichung"),            # nackter Wert als Loesung
    ("x = 5", "5", "gleichung"),            # umgekehrt genauso
    ("y = 5", "x = 5", "gleichung"),        # andere Unbekannte, gleiche Loesung
    ("2(x+3)", "2x+6", "term"),
    ("2x+6", "2(x+3)", "term"),
    ("2(x+3)", "2x+6", None),               # auto mit Unbekannter
    ("3 + 2x", "2x + 3", "term"),           # Kommutativitaet
    ("B", "b", "auswahl"),                  # Gross-/Kleinschreibung egal
    ("ein Viertel", "ein viertel", "text"),
])
def test_mathematisch_aequivalent_ist_richtig(antwort, loesung, art):
    assert check_answer(antwort, loesung, art) is True


@pytest.mark.parametrize("antwort,loesung,art", [
    ("2/5", "1/2", "bruch"),
    ("0,6", "1/2", "bruch"),
    ("x = 6", "x = 5", "gleichung"),
    ("2x + 5", "2x + 6", "term"),
    ("x * x", "x ^ 2", "term"),             # nicht linear → Textvergleich
    ("5 = x", "x = 5", "auswahl"),          # Textart: kein Gleichungsvergleich
    ("7", "x = 5", "gleichung"),
])
def test_nicht_aequivalent_ist_falsch(antwort, loesung, art):
    assert check_answer(antwort, loesung, art) is False


@pytest.mark.parametrize("antwort", [
    "", "   ", "x=foo", "1/0", "beliebiger Text", "=", "((", "5..5",
    "2x+3y", "1/2 + ", "x * * 3",
])
def test_ungueltige_eingabe_stuerzt_nie_ab(antwort):
    for art in (None, "bruch", "term", "gleichung", "auswahl", "text"):
        assert check_answer(antwort, "1/2", art) is False
        assert check_answer(antwort, "x = 5", art) is False


def test_antwort_art_lenkt_den_vergleich():
    """Dieselben Zeichen werden je nach Aufgabentyp verschieden gelesen."""
    # Als Zahl falsch, als Gleichung nicht die Frage — und „5=x" ist unter
    # der Zahlart schlicht der Text.
    assert check_answer("5=x", "5", "bruch") is False
    assert check_answer("5=x", "5", "gleichung") is True
