"""Rechnungen nachrechnen, bevor sie ein Kind zu sehen bekommt.

Die Schemaprüfung sieht Struktur, nicht Wahrheit: „2/3 + 1/6 = 4/9" ist
tadellos geformt und trotzdem falsch. Wo sich eine Behauptung lokal
nachrechnen lässt, wird sie nachgerechnet — ohne zweites Modell, ohne Netz,
in Bruchzahlen statt Gleitkomma, damit 1/3 wirklich 1/3 ist.

Drei Antworten, und die dritte ist die wichtigste:

    True   nachgerechnet und richtig
    False  nachgerechnet und falsch
    None   nicht nachrechenbar

`None` ist kein Makel. „Kante 3 cm — wie viele Würfelchen?" ist eine
ehrliche Aufgabe ohne Rechenausdruck; ein zu eifriger Prüfer würde sie
verwerfen. Geprüft wird nur, was sich ohne Deutung prüfen lässt.

Bewusst kein `eval()`: ein winziger Parser ist hier sicherer als eine
Zeichenkette, die irgendwann aus einer Modellausgabe stammt.
"""

from __future__ import annotations

import re
from fractions import Fraction

#: Zeichen, aus denen ein nachrechenbarer Ausdruck bestehen darf.
_ZEICHEN = r"0-9\s+\-*/·×:().,"

#: `A = B`, wo beide Seiten nur aus Rechenzeichen bestehen. Alles mit Worten
#: darin bleibt ungeprüft — lieber nicht nachrechnen als falsch nachrechnen.
#: Die Lookbehind verhindert nur, MITTEN in einer Zahl anzufangen — nicht,
#: dass ein Leerzeichen davorsteht. Sonst bliebe jede Gleichung in einem
#: Satz ungeprüft, und genau dort stehen sie.
_GLEICHUNG = re.compile(
    rf"(?<![0-9.,])([0-9][{_ZEICHEN}]*?)\s*=\s*([0-9][{_ZEICHEN}]*)")


class NichtRechenbar(ValueError):
    """Der Ausdruck enthält etwas, das kein Rechenzeichen ist."""


def _zahlen(text: str):
    """Zerlegt in Zahlen und Operatoren. Wirft, sobald etwas anderes kommt."""
    wert = (text.replace("·", "*").replace("×", "*").replace(":", "/")
                .replace(",", "."))
    marken, i = [], 0
    while i < len(wert):
        zeichen = wert[i]
        if zeichen.isspace():
            i += 1
        elif zeichen.isdigit():
            j = i
            while j < len(wert) and (wert[j].isdigit() or wert[j] == "."):
                j += 1
            zahl = wert[i:j].rstrip(".")
            if not zahl or zahl.count(".") > 1:
                raise NichtRechenbar(wert[i:j])
            marken.append(Fraction(zahl))
            i = j
        elif zeichen in "+-*/()":
            marken.append(zeichen)
            i += 1
        else:
            raise NichtRechenbar(zeichen)
    if not marken:
        raise NichtRechenbar("leer")
    return marken


def _auswerten(marken: list):
    """Ein kleiner Parser: Summe → Produkt → Faktor."""
    pos = 0

    def summe():
        nonlocal pos
        wert = produkt()
        while pos < len(marken) and marken[pos] in ("+", "-"):
            zeichen = marken[pos]
            pos += 1
            rechts = produkt()
            wert = wert + rechts if zeichen == "+" else wert - rechts
        return wert

    def produkt():
        nonlocal pos
        wert = faktor()
        while pos < len(marken) and marken[pos] in ("*", "/"):
            zeichen = marken[pos]
            pos += 1
            rechts = faktor()
            if zeichen == "/":
                if rechts == 0:
                    raise NichtRechenbar("geteilt durch null")
                wert = wert / rechts
            else:
                wert = wert * rechts
        return wert

    def faktor():
        nonlocal pos
        if pos >= len(marken):
            raise NichtRechenbar("unvollständig")
        marke = marken[pos]
        if marke == "-":
            pos += 1
            return -faktor()
        if marke == "(":
            pos += 1
            wert = summe()
            if pos >= len(marken) or marken[pos] != ")":
                raise NichtRechenbar("Klammer offen")
            pos += 1
            return wert
        if isinstance(marke, Fraction):
            pos += 1
            return marke
        raise NichtRechenbar(str(marke))

    wert = summe()
    if pos != len(marken):
        raise NichtRechenbar("Rest")
    return wert


def wert(ausdruck: str) -> Fraction | None:
    """Der Wert eines Ausdrucks, oder None wenn er nicht rechenbar ist."""
    try:
        return _auswerten(_zahlen(ausdruck))
    except (NichtRechenbar, ZeroDivisionError):
        return None


def stimmt(text: str | None) -> bool | None:
    """Prüft jede nachrechenbare Gleichung in einem Text.

    False, sobald eine davon nicht aufgeht. None, wenn keine zu finden war.
    """
    if not text:
        return None
    geprueft = False
    for links, rechts in _GLEICHUNG.findall(str(text)):
        a, b = wert(links), wert(rechts)
        if a is None or b is None:
            continue
        geprueft = True
        if a != b:
            return False
    return True if geprueft else None


def loesung_stimmt(frage: str | None, loesung: str | None) -> bool | None:
    """Prüft eine Aufgabe gegen ihre Lösung: „2/3 + 1/6 = ?" → „5/6"."""
    if not frage or not loesung:
        return None
    aufgabe = re.sub(r"[=?]\s*$", "", str(frage).strip()).strip(" =?")
    a, b = wert(aufgabe), wert(str(loesung))
    if a is None or b is None:
        return None
    return a == b
