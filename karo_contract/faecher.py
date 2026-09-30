"""Die drei Fächer: Deutsch, Mathematik, Englisch — strikt getrennt.

Jedes Thema, jedes Schulblatt, jede Klassenarbeit und jede Lektion gehört zu
genau einem dieser Fächer. Gespeichert wird immer der Schlüssel
(`deutsch`, `mathematik`, `englisch`), angezeigt der Name.

Hier steht die einzige Entscheidung darüber, was ein Fach ist und ob ein
Text in ein Fach gehört. Alle anderen Stellen fragen hier nach, statt eigene
Listen zu führen.

Hier steht nur, was auch der Lehrplan-Dienst braucht: Schluessel, Namen und
die Zuordnung eines geschriebenen Fachnamens dazu. Liefert der Dienst
„Mathematik" und Karo fragt fuer „mathematik", muss beides dasselbe heissen —
sonst wird eine richtige Lieferung verworfen.

Das Erkennen eines Fachs aus einem Text (Katalog, Stichworte, Modell) steht
in `app/faecher.py`: das ist Karos Sache, nicht Sache des Vertrags.
"""
from __future__ import annotations

import logging
import re
import unicodedata

log = logging.getLogger(__name__)

FAECHER = ("deutsch", "mathematik", "englisch")
NAMEN = {"deutsch": "Deutsch", "mathematik": "Mathematik", "englisch": "Englisch"}
#: Fuer SQL: `... WHERE subject IN {SQL_FAECHER}`. Nur feste Schluessel,
#: keine Eingaben — deshalb darf es als Text in die Abfrage.
SQL_FAECHER = "('deutsch','mathematik','englisch')"

SUBJECT_MISMATCH = "SUBJECT_MISMATCH"
ANDERE = "andere"

_ALIASE = {
    "deutsch": "deutsch", "de": "deutsch", "german": "deutsch", "deutschunterricht": "deutsch",
    "mathematik": "mathematik", "mathe": "mathematik", "math": "mathematik",
    "maths": "mathematik", "mathematics": "mathematik", "ma": "mathematik",
    "englisch": "englisch", "english": "englisch", "engl": "englisch", "en": "englisch",
}


class FachFehler(ValueError):
    """Kein gültiges Fach angegeben."""

    code = "SUBJECT_MISSING"


class SubjectMismatch(FachFehler):
    """Der Inhalt gehört in ein anderes Fach als das aktive."""

    code = SUBJECT_MISMATCH

    def __init__(self, aktiv: str, erkannt: str):
        self.aktiv, self.erkannt = aktiv, erkannt
        if erkannt in FAECHER:
            text = (f"Das gehört zu {NAMEN[erkannt]}, nicht zu {NAMEN[aktiv]}. "
                    f"Wechsle oben zum Fach {NAMEN[erkannt]}.")
        else:
            text = ("Das gehört zu keinem deiner Fächer. Karo lernt mit dir "
                    "Deutsch, Mathematik und Englisch.")
        super().__init__(text)


def _flach(text: str | None) -> str:
    text = (text or "").casefold().replace("ß", "ss")
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue")):
        text = text.replace(alt, neu)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(z for z in text if not unicodedata.combining(z))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def schluessel(wert: str | None) -> str | None:
    """`Mathe`, `Mathematik`, `mathematik` → `mathematik`; sonst None."""
    return _ALIASE.get(_flach(wert))


def pflicht(wert: str | None) -> str:
    key = schluessel(wert)
    if key is None:
        raise FachFehler("Bitte wähle ein Fach: Deutsch, Mathematik oder Englisch.")
    return key


def name(wert: str | None) -> str:
    """Anzeigename; Unbekanntes bleibt, wie es ist (Elternordner)."""
    key = schluessel(wert)
    return NAMEN[key] if key else (wert or "Ohne Fach")
