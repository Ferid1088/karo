"""Zahlen rechnet der Code, Sprache schreibt das Modell.

Ein Sprachmodell ist gut darin, eine Aufgabe zu *formulieren*, und schlecht
darin, sie zu *rechnen*. Im Protokoll sah man beides nebeneinander: schoene
Aufgabenstellungen, und darin Rechnungen, die nicht aufgingen.

Also die Arbeit teilen. Das Modell liefert eine **Vorlage** mit Platzhaltern
und **Bedingungen**:

    {"vorlage": "{a}/{b} + {c}/{d}", "bedingungen": ["b != d", "kgv(b,d) <= 24"]}

Die Zahlen wuerfelt dieser Code — mit festem Seed je Lektion, damit dieselbe
Lektion immer dieselben Aufgaben hat — und rechnet die Loesung selbst aus.
Dann kann sie nicht falsch sein: sie ist nicht behauptet, sondern gerechnet.

Den typischen Fehler rechnet der Code ebenfalls, wo die Fehlvorstellung
bekannt ist (`FEHLERFUNKTIONEN`). „Zaehler und Nenner addieren" ist eine
Rechenvorschrift, keine Erfindung. Wo sie nicht bekannt ist, darf das Modell
ihn vorschlagen — und der Validator prueft ihn wie bisher.
"""
from __future__ import annotations

import math
import random
import re
from fractions import Fraction
from typing import Callable

from .rechnen import NichtRechenbar, wert

#: So viele Versuche, bis eine Belegung alle Bedingungen erfuellt. Danach
#: lieber ehrlich aufgeben als eine Aufgabe ausliefern, die eine Bedingung
#: verletzt — die Bedingungen sind der didaktische Teil.
MAX_VERSUCHE = 400

_PLATZHALTER = re.compile(r"\{([a-z][a-z0-9_]*)\}")


class VorlageUnbrauchbar(ValueError):
    """Die Vorlage oder ihre Bedingungen ergeben keine Aufgabe."""


# --------------------------------------------------------------------------
# Bedingungen
# --------------------------------------------------------------------------

def kgv(a: int, b: int) -> int:
    return abs(a * b) // math.gcd(a, b) if a and b else 0


def ggt(a: int, b: int) -> int:
    return math.gcd(int(a), int(b))


#: Was in einer Bedingung vorkommen darf. Bewusst eine kurze Liste: hier wird
#: Text ausgewertet, der aus einem Modell kommt.
_ERLAUBT: dict[str, Callable] = {
    "kgv": kgv, "ggt": ggt, "abs": abs, "min": min, "max": max,
    "int": int, "len": len, "sum": sum, "round": round,
}
_BEDINGUNG_OK = re.compile(r"^[a-z0-9_\s+\-*/%().,<>=!&|]+$")


def _pruefe_bedingung(text: str) -> str:
    """Nur Rechnen und Vergleichen. Kein Punkt, keine Klammeraffen, kein Import."""
    if not _BEDINGUNG_OK.match(text or ""):
        raise VorlageUnbrauchbar(f"Bedingung enthält Unerlaubtes: {text!r}")
    if "__" in text or "lambda" in text:
        raise VorlageUnbrauchbar(f"Bedingung enthält Unerlaubtes: {text!r}")
    return text


def erfuellt(bedingungen: list[str], belegung: dict[str, int]) -> bool:
    for roh in bedingungen:
        ausdruck = _pruefe_bedingung(str(roh))
        try:
            if not eval(ausdruck, {"__builtins__": {}}, {**_ERLAUBT, **belegung}):  # noqa: S307
                return False
        except ZeroDivisionError:
            return False
        except (NameError, TypeError, SyntaxError) as fehler:
            raise VorlageUnbrauchbar(f"Bedingung {roh!r} ist nicht auswertbar: {fehler}") from None
    return True


# --------------------------------------------------------------------------
# Belegen und rechnen
# --------------------------------------------------------------------------

def platzhalter(vorlage: str) -> list[str]:
    """Die Namen in der Vorlage, in der Reihenfolge ihres ersten Auftretens."""
    gesehen: list[str] = []
    for name in _PLATZHALTER.findall(vorlage or ""):
        if name not in gesehen:
            gesehen.append(name)
    return gesehen


def belegen(vorlage: str, bedingungen: list[str] | None = None, *,
            seed: int | str = 0, bereich: tuple[int, int] = (1, 12)) -> dict[str, int]:
    """Zahlen fuer die Platzhalter finden, die alle Bedingungen erfuellen.

    Fester Seed: dieselbe Lektion bekommt immer dieselben Aufgaben. Sonst
    stuende in der Datenbank eine andere Aufgabe als im Lernmaterial, und
    niemand koennte einen Fehlerbericht nachstellen.
    """
    namen = platzhalter(vorlage)
    if not namen:
        return {}
    wuerfel = random.Random(f"{seed}:{vorlage}")
    unten, oben = bereich
    for _ in range(MAX_VERSUCHE):
        belegung = {n: wuerfel.randint(unten, oben) for n in namen}
        if erfuellt(bedingungen or [], belegung):
            return belegung
    raise VorlageUnbrauchbar(
        f"Keine Zahlen gefunden, die alle Bedingungen erfüllen: {vorlage} "
        f"mit {bedingungen}")


def einsetzen(vorlage: str, belegung: dict[str, int]) -> str:
    def ersetze(treffer):
        name = treffer.group(1)
        if name not in belegung:
            raise VorlageUnbrauchbar(f"Platzhalter {{{name}}} hat keinen Wert.")
        return str(belegung[name])
    return _PLATZHALTER.sub(ersetze, vorlage or "")


def _als_text(zahl: Fraction) -> str:
    """Brueche als Bruch, ganze Zahlen als ganze Zahl."""
    if zahl.denominator == 1:
        return str(zahl.numerator)
    return f"{zahl.numerator}/{zahl.denominator}"


def ausrechnen(ausdruck: str) -> str:
    """Die Loesung — gerechnet, nicht behauptet."""
    ergebnis = wert(ausdruck)
    if ergebnis is None:
        raise VorlageUnbrauchbar(f"„{ausdruck}“ lässt sich nicht ausrechnen.")
    return _als_text(ergebnis)


# --------------------------------------------------------------------------
# Typischer Fehler: wo die Fehlvorstellung bekannt ist, rechnet der Code ihn
# --------------------------------------------------------------------------
#
# „Zaehler und Nenner addieren" ist eine Rechenvorschrift, keine Erfindung.
# Wo sie hier steht, muss das Modell sie nicht raten — und kann sie nicht
# falsch raten. Fuer alles andere schlaegt das Modell vor, und der Validator
# prueft (`schemas._aufgabe_pruefen`: der typische Fehler darf nie gleich der
# Loesung sein).

def _zaehler_und_nenner_addiert(belegung: dict[str, int]) -> str:
    """1/2 + 1/3 → 2/5. Die haeufigste Fehlvorstellung beim Bruchaddieren."""
    a, b, c, d = (belegung[k] for k in ("a", "b", "c", "d"))
    return f"{a + c}/{b + d}"


def _nenner_beibehalten(belegung: dict[str, int]) -> str:
    """1/2 + 1/3 → 2/2: Zaehler addiert, Nenner einfach stehen gelassen."""
    a, b, c, _ = (belegung[k] for k in ("a", "b", "c", "d"))
    return f"{a + c}/{b}"


def _vorzeichen_vergessen(belegung: dict[str, int]) -> str:
    """x − a = b → x = b − a statt b + a. Die Umkehrung nicht mitgedacht."""
    a, b = belegung["a"], belegung["b"]
    return f"x = {b - a}"


def _mal_statt_geteilt(belegung: dict[str, int]) -> str:
    a, b = belegung["a"], belegung["b"]
    return _als_text(Fraction(a * b))


#: Schluessel ist der `fehler_key` des Fehlertyps aus dem Katalog.
FEHLERFUNKTIONEN: dict[str, Callable[[dict[str, int]], str]] = {
    "zaehler_und_nenner_addiert": _zaehler_und_nenner_addiert,
    "nenner_addiert": _zaehler_und_nenner_addiert,
    "nenner_beibehalten": _nenner_beibehalten,
    "vorzeichen_vergessen": _vorzeichen_vergessen,
    "mal_statt_geteilt": _mal_statt_geteilt,
}


def typischer_fehler(fehler_key: str, belegung: dict[str, int]) -> str | None:
    """Die typische falsche Antwort — gerechnet, wo die Regel bekannt ist.

    None heisst: fuer diese Fehlvorstellung gibt es keine Rechenvorschrift,
    das Modell darf vorschlagen.
    """
    funktion = FEHLERFUNKTIONEN.get((fehler_key or "").strip().lower())
    if funktion is None:
        return None
    try:
        return funktion(belegung)
    except (KeyError, ZeroDivisionError, ValueError):
        # Die Vorlage passt nicht zu dieser Fehlerfunktion. Kein Grund, die
        # Aufgabe wegzuwerfen — dann schlaegt eben das Modell vor.
        return None


def bauen(vorlage: dict, *, seed: int | str = 0, fehler_key: str = "") -> dict:
    """Aus Vorlage und Bedingungen eine fertige Aufgabe machen.

    Erwartet `{"vorlage": "...", "bedingungen": [...], "frage": "Rechne {aufgabe}."}`.
    Gibt Frage, Loesung und — wo bekannt — den typischen Fehler zurueck.
    """
    muster = str(vorlage.get("vorlage") or "").strip()
    if not muster:
        raise VorlageUnbrauchbar("Die Vorlage hat kein Muster.")
    bedingungen = [str(b) for b in (vorlage.get("bedingungen") or [])]
    bereich = tuple(vorlage.get("bereich") or (1, 12))
    belegung = belegen(muster, bedingungen, seed=seed, bereich=bereich)
    aufgabe = einsetzen(muster, belegung)
    loesung = ausrechnen(aufgabe)

    satz = str(vorlage.get("frage") or "{aufgabe}")
    frage = satz.replace("{aufgabe}", aufgabe)
    frage = einsetzen(frage, belegung) if platzhalter(frage) else frage

    fertig = {"frage": frage, "loesung": loesung, "ausdruck": aufgabe,
              "belegung": belegung}
    fehler = typischer_fehler(fehler_key, belegung)
    if fehler and fehler != loesung:
        fertig["typischer_fehler"] = fehler
    return fertig
