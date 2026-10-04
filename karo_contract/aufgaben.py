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

#: Bis zu dieser Kombinatorik zaehlt der Wuerfel vollzaehlig durch — eine
#: erfuellbare Belegung kann dann nicht zufaellig verfehlt werden (Geld in
#: Tausendern mal Prozentsatz in Zehnern ~1e6). Darueber bleibt es beim
#: Zufallswurf mit MAX_VERSUCHE.
MAX_ENUMERATION = 1_000_000

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


#: Was den Wuerfelraum verkleinert, bevor der erste Wurf faellt:
#: „b kleiner 5" schneidet den Bereich zu, „a % 100 == 0" laesst nur
#: Vielfache. Ein geteilter Bereich [1, 9900] mit einer engen Schranke
#: waere sonst ein Zufallstreffer unter 98 Millionen — und das
#: Durchzaehlen greift erst, wenn der Raum ehrlich klein ist.
_OPS = {"<", ">", "<=", ">=", "==", "!="}
_SCHRANKE = re.compile(
    r"^([a-z][a-z0-9_]*)\s*([<>=!]+)\s*(-?\d+)$")
_SCHRANKE_REV = re.compile(
    r"^(-?\d+)\s*([<>=!]+)\s*([a-z][a-z0-9_]*)$")
_TEILER = re.compile(r"^([a-z][a-z0-9_]*)\s*%\s*([1-9]\d*)\s*==\s*0$")


def _raenge(namen: list[str], je: dict[str, tuple[int, int]],
            bedingungen: list[str]) -> list[range]:
    """Wuerfel-Bereiche, schon um das verengt, was eine einfache
    Bedingung vor dem ersten Wurf festlegt."""
    grenzen = {n: [je[n][0], je[n][1], 1] for n in namen}
    for roh in bedingungen or []:
        text = str(roh).strip()
        m = _TEILER.match(text)
        if m and m.group(1) in grenzen:
            grenzen[m.group(1)][2] = math.lcm(
                grenzen[m.group(1)][2], int(m.group(2)))
            continue
        m = _SCHRANKE.match(text)
        if m and m.group(1) in grenzen and m.group(2) in _OPS:
            name, op, w = m.group(1), m.group(2), int(m.group(3))
        else:
            m = _SCHRANKE_REV.match(text)
            if not m or m.group(3) not in grenzen or m.group(2) not in _OPS:
                continue
            name, w = m.group(3), int(m.group(1))
            op = {"<": ">", "<=": ">=", ">": "<", ">=": "<=",
                  "==": "==", "!=": "!="}[m.group(2)]
        if op in ("==", "!="):
            continue
        if op in (">", ">="):
            grenzen[name][0] = max(grenzen[name][0], w + (op == ">"))
        else:
            grenzen[name][1] = min(grenzen[name][1], w - (op == "<"))
    raenge = []
    for n in namen:
        lo, hi, schritt = grenzen[n]
        if schritt > 1:
            lo += (-lo) % schritt
        r = range(lo, hi + 1, schritt)
        if not len(r):
            raise VorlageUnbrauchbar(
                f"Bedingungen lassen für {{{n}}} keinen Wert in "
                f"{tuple(grenzen[n][:2])}.")
        raenge.append(r)
    return raenge


def belegen(vorlage: str, bedingungen: list[str] | None = None, *,
            seed: int | str = 0,
            bereich: tuple[int, int] | dict[str, tuple[int, int]] = (1, 12)) -> dict[str, int]:
    """Zahlen fuer die Platzhalter finden, die alle Bedingungen erfuellen.

    `bereich` gilt als Paar fuer alle Platzhalter oder als
    ``{name: (unten, oben)}`` je Platzhalter — ein Geldwert in Tausendern
    und ein Prozentsatz in Zehnern kommen sonst aus demselben Wuerfel.

    Fester Seed: dieselbe Lektion bekommt immer dieselben Aufgaben. Sonst
    stuende in der Datenbank eine andere Aufgabe als im Lernmaterial, und
    niemand koennte einen Fehlerbericht nachstellen.
    """
    namen = platzhalter(vorlage)
    if not namen:
        return {}
    wuerfel = random.Random(f"{seed}:{vorlage}")
    je = bereich if isinstance(bereich, dict) else {n: bereich for n in namen}
    raenge = _raenge(namen, je, bedingungen or [])
    gesamt = math.prod(len(r) for r in raenge)
    if gesamt <= MAX_ENUMERATION:
        # Kleiner Raum: vollzählig ab einem zufälligen Einstieg — eine
        # erfüllbare Kombination wird sicher gefunden, statt mit
        # Wahrscheinlichkeit ~1/Raum zwischen den Würfen zu verschwinden.
        start = wuerfel.randrange(gesamt)
        for schritt in range(gesamt):
            rest = (start + schritt) % gesamt
            belegung = {}
            for name, r in zip(namen, raenge):
                belegung[name] = r[rest % len(r)]
                rest //= len(r)
            if erfuellt(bedingungen or [], belegung):
                return belegung
    else:
        for _ in range(MAX_VERSUCHE):
            belegung = {n: wuerfel.choice(r) for n, r in zip(namen, raenge)}
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


def _paar_pruefen(roh, vorlage: str) -> tuple[int, int]:
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


def _bereich_pruefen(roh, vorlage: str,
                     namen: list[str]) -> dict[str, tuple[int, int]]:
    """`bereich` ist [unten, oben] für alle Platzhalter — oder
    {"name": [unten, oben]} je Platzhalter (Vorgabe 1–12).

    Die Mapping-Form muss jeden Platzhalter nennen und keine fremden:
    ein Wert, der schweigend im Standard wuerfelt oder gar nicht gilt,
    waere ein unsichtbarer Autorenfehler.
    """
    if roh is None:
        return {n: (1, 12) for n in namen}
    if isinstance(roh, dict):
        fremd = sorted(n for n in roh if n not in namen)
        fehlt = sorted(n for n in namen if n not in roh)
        if fremd or fehlt:
            raise VorlageUnbrauchbar(
                f"bereich passt nicht zu den Platzhaltern {namen}: "
                f"unbekannt {fremd or '—'}, fehlend {fehlt or '—'}")
        return {n: _paar_pruefen(roh[n], vorlage) for n in namen}
    paar = _paar_pruefen(roh, vorlage)
    return {n: paar for n in namen}


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
    bereich = _bereich_pruefen(vorlage.get("bereich"), muster, platzhalter(muster))
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
