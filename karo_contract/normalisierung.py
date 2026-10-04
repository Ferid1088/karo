"""Antworten vergleichbar machen, damit Tier 1 ohne Modell trifft.

„2/5“, „2 / 5“ und „2:5“ sind dieselbe Fehlvorstellung. Ohne Normalisierung
braucht man dafür ein Modell — mit Normalisierung reicht ein Index-Zugriff.
Das ist der Unterschied zwischen einem Katalogtreffer und einem Modellaufruf,
und damit das ganze Kostenargument (01_ARCHITECTURE.md §1).
"""

from __future__ import annotations

import re
import unicodedata

_MEHRFACH_LEER = re.compile(r"\s+")
_ERLAUBT = re.compile(r"[^a-z0-9/.,+\-= ]")
_ERLAUBT_THEMA = re.compile(r"[^a-z0-9 ]")


def normalisiere(text: str | None) -> str:
    """Schreibweise vereinheitlichen, Bedeutung nicht verändern."""
    if not text:
        return ""
    wert = _grundform(text)
    wert = wert.replace(":", "/").replace("÷", "/")
    wert = _ERLAUBT.sub(" ", wert)
    wert = wert.replace(",", ".")
    # Ein Satzpunkt ist keine Dezimalstelle: „…20 s." == „…20 s".
    wert = re.sub(r"\.(?![0-9])", " ", wert)
    # "2 / 5" → "2/5", aber "1/2 + 1/3" behält seine Teile.
    wert = re.sub(r"\s*/\s*", "/", wert)
    wert = re.sub(r"\s*([+\-=])\s*", r" \1 ", wert)
    return _MEHRFACH_LEER.sub(" ", wert).strip()


def _grundform(text: str) -> str:
    """Kleinschreibung und ausgeschriebene Umlaute — die Stufe, die beide
    Normalisierungen teilen."""
    wert = unicodedata.normalize("NFC", str(text)).lower()
    wert = (wert.replace("\u00e4", "ae").replace("\u00f6", "oe")
                .replace("\u00fc", "ue").replace("\u00df", "ss"))
    return "".join(z for z in unicodedata.normalize("NFKD", wert)
                   if not unicodedata.combining(z))


def normalisiere_thema(text: str | None) -> str:
    """Themennamen vergleichbar machen — nicht dasselbe wie eine Antwort.

    `normalisiere()` ist auf Brueche geeicht: dort ist „2:5" dieselbe Zahl
    wie „2/5", und der Doppelpunkt wird zum Bruchstrich. Ein Themenname ist
    keine Rechnung. „Wuerfel: Volumen" wuerde sonst zu „wuerfel/volumen"
    und traefe kein Stichwort mehr.

    Hier zaehlen nur Buchstaben, Ziffern und Wortgrenzen.
    """
    if not text:
        return ""
    wert = _ERLAUBT_THEMA.sub(" ", _grundform(text))
    return _MEHRFACH_LEER.sub(" ", wert).strip()


def ist_gleichwertig(a: str | None, b: str | None) -> bool:
    """Gleiche Antwort in anderer Schreibweise?"""
    links, rechts = normalisiere(a), normalisiere(b)
    return bool(links) and links == rechts
