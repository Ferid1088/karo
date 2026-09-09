"""Entfernen personenbezogener Angaben, bevor Text an das Modell geht.

Was hier passiert, ist eine Filterung mit klaren Grenzen — keine Garantie.
Ehrlich gesagt: ein Filter kann nicht wissen, dass "Milena" in einer Textaufgabe
der Name der Schülerin ist und nicht der Name in der Aufgabe. Deshalb gilt:

  * durchgesetzt wird, was hier steht (bekannter Vorname, Kopfzeilenmuster,
    Schul- und Lehrkraftangaben, Geburtsdaten)
  * nicht durchgesetzt werden kann, was im Bild steht und ausserhalb des
    abgeschnittenen Randes liegt

Beide Aussagen stehen so auch in der Oberflaeche. Ein Versprechen, das der
Code nicht halten kann, waere schlimmer als gar keines.
"""

from __future__ import annotations

import re

PLACEHOLDER = "[entfernt]"

_PATTERNS: list[re.Pattern] = [
    # Kopfzeilen deutscher Arbeitsblaetter
    re.compile(r"(?i)\b(name|vorname|nachname|schüler(?:in)?)\s*[:.]\s*\S.{0,40}"),
    re.compile(r"(?i)\bklasse\s*[:.]?\s*\d{1,2}\s*[a-e]\b"),
    # Schule und Lehrkraft
    re.compile(r"(?i)\b(?:bei\s+)?(herr|frau)\s+[A-ZÄÖÜ][a-zäöüß]{2,}"),
    re.compile(r"(?i)\b[A-ZÄÖÜ][\wäöüß-]*(gymnasium|realschule|gesamtschule|"
               r"grundschule|oberschule|schule)\b[\w\s.-]{0,30}"),
    re.compile(r"(?i)\b(lehrer(?:in)?|klassenlehrer(?:in)?)\s*[:.]?\s*\S.{0,30}"),
    # Geburtsdatum
    re.compile(r"(?i)\b(geb(?:oren)?|geburtsdatum)\s*[:.]?\s*\d{1,2}\.\d{1,2}\.\d{2,4}"),
    # E-Mail und Telefon
    re.compile(r"\b[\w.+-]+@[\w-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"(?<!\d)(?:\+49|0)\s?\d{2,5}[\s/-]?\d{3,}(?!\d)"),
]


def scrub(text: str | None, learner_name: str = "") -> str:
    """Entfernt bekannte personenbezogene Muster aus einem Text."""
    if not text:
        return ""
    out = str(text)

    # Der eingetragene Vorname ist das Einzige, was sicher bekannt ist.
    name = (learner_name or "").strip()
    if len(name) >= 3:
        out = re.sub(rf"\b{re.escape(name)}\w*\b", PLACEHOLDER, out, flags=re.IGNORECASE)

    for pattern in _PATTERNS:
        out = pattern.sub(PLACEHOLDER, out)
    return out


def scrub_all(values: list[str], learner_name: str = "") -> list[str]:
    return [scrub(v, learner_name) for v in values]
