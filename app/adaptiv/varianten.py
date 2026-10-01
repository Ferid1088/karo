"""Neue Aufgaben aus einer bekannten Aufgabe (Schritt 4a).

Eine Wiederholung, die dieselbe Aufgabe noch einmal stellt, misst
Erinnerung an eine Zahl, nicht Koennen. Fuer Mathematik laesst sich das
loesen: wo Karo die Struktur einer Aufgabe wirklich versteht, rechnet sie
eine neue mit anderen Zahlen aus.

**Nur wo sie es sicher kann.** Erkennt der Generator das Muster nicht oder
geht die Rechnung nicht glatt auf, liefert er nichts. Eine erfundene Aufgabe
mit falscher Loesung waere schlimmer als eine wiederholte.
"""

from __future__ import annotations

import random
import re
from fractions import Fraction

#: „1/2 + 1/3", auch mit Leerzeichen, auch mit Minus. Mehr nicht: was hier
#: steht, muss Karo selbst nachrechnen koennen.
_MUSTER = re.compile(
    r"(?P<a>\d{1,3})\s*/\s*(?P<b>\d{1,3})\s*(?P<op>[+\-])\s*(?P<c>\d{1,3})\s*/\s*(?P<d>\d{1,3})")

#: Nenner, die ein Kind der Mittelstufe im Kopf behaelt.
_NENNER = (2, 3, 4, 5, 6, 8, 9, 10, 12)


def _text(wert: Fraction) -> str:
    return f"{wert.numerator}/{wert.denominator}" if wert.denominator != 1 \
        else str(wert.numerator)


def varianten(aufgabe: dict, anzahl: int = 3, *, zufall=None) -> list[dict]:
    """Neue Aufgaben derselben Bauart, mit nachgerechneter Loesung.

    `zufall` nimmt ein eigenes `random.Random` — damit ein Test dieselbe
    Aufgabe zweimal bekommt und die Wiederholung trotzdem wuerfelt.
    """
    treffer = _MUSTER.search(str(aufgabe.get("frage") or ""))
    if treffer is None:
        return []
    wuerfel = zufall or random.Random()
    vorlage = aufgabe.get("frage")
    gesehen = {treffer.group(0)}
    neue: list[dict] = []
    for _ in range(60):
        if len(neue) >= anzahl:
            break
        b, d = wuerfel.choice(_NENNER), wuerfel.choice(_NENNER)
        a, c = wuerfel.randint(1, b - 1), wuerfel.randint(1, d - 1)
        if b == d:
            continue                      # gleichnamig ist eine andere Aufgabe
        links, rechts = Fraction(a, b), Fraction(c, d)
        ergebnis = links + rechts if treffer.group("op") == "+" else links - rechts
        if ergebnis <= 0 or ergebnis > 2 or ergebnis.denominator > 60:
            continue
        rechnung = f"{a}/{b} {treffer.group('op')} {c}/{d}"
        if rechnung in gesehen:
            continue
        gesehen.add(rechnung)
        neue.append({
            "id": None,
            "frage": vorlage[:treffer.start()] + rechnung + vorlage[treffer.end():],
            "loesung": _text(ergebnis),
            "antwort_art": aufgabe.get("antwort_art") or "bruch",
            "optionen": [],
            "tipps": [],
            "quelle": "variante",
            "erwartete_sekunden": aufgabe.get("erwartete_sekunden"),
        })
    return neue


def moeglich(aufgabe: dict) -> bool:
    return _MUSTER.search(str(aufgabe.get("frage") or "")) is not None
