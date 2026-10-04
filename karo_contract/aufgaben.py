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
    """Nur Rechnen und Vergleichen. Kein Punkt, keine Klammeraffen, kein Import.

    `**` faellt aus, obwohl es die Zeichenliste erlaubt: Potenzen braucht
    keine Schulbedingung, und `a ** 999999` rechnet in jedem einzelnen
    Wurf eine Zahl, die niemand mehr lesen kann.
    """
    if not _BEDINGUNG_OK.match(text or ""):
        raise VorlageUnbrauchbar(f"Bedingung enthält Unerlaubtes: {text!r}")
    if "__" in text or "**" in text or "lambda" in text:
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


#: Groessenordnung, bis zu der eine Vorlage noch wuerfeln darf. Zahlen
#: jenseits davon ergeben Aufgaben, die kein Kind mehr lesen kann — und
#: Bedingungen wie `kgv` rechnen auf absurden Werten.
MAX_BEREICH = 100_000


def _bereich_pruefen(roh, vorlage: str) -> tuple[int, int]:
    """`bereich` ist [unten, oben] ganzer Zahlen — oder Vorgabe 1–12."""
    if roh is None:
        return (1, 12)
    try:
        unten, oben = roh
    except (TypeError, ValueError):
        raise VorlageUnbrauchbar(
            f"bereich ist kein Zahlenpaar: {roh!r} (in {vorlage!r})") from None
    if type(unten) is not int or type(oben) is not int or unten > oben:
        raise VorlageUnbrauchbar(
            f"bereich ist ungültig: {roh!r} (in {vorlage!r})")
    if max(abs(unten), abs(oben)) > MAX_BEREICH:
        raise VorlageUnbrauchbar(
            f"bereich ist absurd groß: {roh!r} (in {vorlage!r})")
    return (unten, oben)


def bauen(vorlage: dict, *, seed: int | str = 0, fehler_key: str = "") -> dict:
    """Aus Vorlage und Bedingungen eine fertige Aufgabe machen.

    Erwartet `{"vorlage": "...", "bedingungen": [...], "frage": "Rechne {aufgabe}."}`.
    Gibt Frage, Loesung und — wo bekannt — den typischen Fehler zurueck.
    """
    muster = str(vorlage.get("vorlage") or "").strip()
    if not muster:
        raise VorlageUnbrauchbar("Die Vorlage hat kein Muster.")
    roh_bedingungen = vorlage.get("bedingungen") or []
    if not isinstance(roh_bedingungen, list):
        raise VorlageUnbrauchbar(
            f"bedingungen ist keine Liste: {roh_bedingungen!r}")
    bedingungen = [str(b) for b in roh_bedingungen]
    bereich = _bereich_pruefen(vorlage.get("bereich"), muster)
    belegung = belegen(muster, bedingungen, seed=seed, bereich=bereich)
    aufgabe = einsetzen(muster, belegung)
    # Erst fragen, ob eine Unbekannte gesucht ist: „4x − 3 = 9" laesst sich
    # nicht ausrechnen, nur loesen. Genau an dieser Vorlagenart haengt das
    # Thema, das den ganzen Generator ausgeloest hat.
    geloest = loesen(aufgabe)
    if geloest:
        variable, wert_ = geloest
        loesung = f"{variable} = {wert_}"
    else:
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


# --------------------------------------------------------------------------
# Gleichungen mit einer Unbekannten
# --------------------------------------------------------------------------
#
# „{a}x − {b} = {c}x + {d}" ist die haeufigste Vorlage ueberhaupt, und sie
# laesst sich nicht „ausrechnen": gesucht ist x, nicht ein Zahlenwert. Ohne
# das hier waere der Generator ausgerechnet fuer das Thema unbrauchbar, das
# ihn ausgeloest hat — „Lineare Gleichungen loesen".
#
# Geloest wird nur, was wirklich linear ist: beide Seiten der Form
# „Zahl·x + Zahl". Alles andere bleibt ungeloest und sagt das auch.

_VARIABLE = re.compile(r"(?<![a-zA-Z])([a-z])(?![a-zA-Z])")


def _linear_teilen(seite: str, variable: str) -> tuple[Fraction, Fraction]:
    """Eine Seite in (Faktor vor der Variablen, Konstante) zerlegen."""
    text = (seite.replace("−", "-").replace("–", "-").replace("·", "*")
                 .replace("×", "*").replace(" ", ""))
    faktor = Fraction(0)
    konstante = Fraction(0)
    # In Summanden zerlegen, Vorzeichen behalten.
    for teil in re.findall(r"[+-]?[^+-]+", text):
        if not teil:
            continue
        vorzeichen = -1 if teil.startswith("-") else 1
        rumpf = teil.lstrip("+-")
        if variable in rumpf:
            zahl = rumpf.replace(variable, "").replace("*", "").strip()
            faktor += vorzeichen * (Fraction(zahl) if zahl else Fraction(1))
        else:
            try:
                konstante += vorzeichen * Fraction(rumpf)
            except (ValueError, ZeroDivisionError):
                raise VorlageUnbrauchbar(f"„{seite}“ ist nicht linear.") from None
    return faktor, konstante


def loesen(gleichung: str) -> tuple[str, str] | None:
    """Loest „a·x + b = c·x + d" nach x. Gibt (variable, loesung) zurueck.

    None, wenn es keine Gleichung mit genau einer Unbekannten ist — dann
    ist dieser Weg nicht zustaendig.
    """
    if "=" not in gleichung:
        return None
    variablen = set(_VARIABLE.findall(gleichung))
    if len(variablen) != 1:
        return None
    variable = variablen.pop()
    links, _, rechts = gleichung.partition("=")
    fl, kl = _linear_teilen(links, variable)
    fr, kr = _linear_teilen(rechts, variable)
    faktor, konstante = fl - fr, kr - kl
    if faktor == 0:
        raise VorlageUnbrauchbar(
            f"„{gleichung}“ hat keine eindeutige Lösung — die Unbekannte fällt weg.")
    return variable, _als_text(konstante / faktor)
