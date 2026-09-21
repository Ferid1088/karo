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


def normalisiere(text: str | None) -> str:
    """Schreibweise vereinheitlichen, Bedeutung nicht verändern."""
    if not text:
        return ""
    wert = unicodedata.normalize("NFKD", str(text)).lower()
    wert = (wert.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
                .replace("ß", "ss"))
    wert = wert.replace(":", "/").replace("÷", "/")
    wert = _ERLAUBT.sub(" ", wert)
    wert = wert.replace(",", ".")
    # "2 / 5" → "2/5", aber "1/2 + 1/3" behält seine Teile.
    wert = re.sub(r"\s*/\s*", "/", wert)
    wert = re.sub(r"\s*([+\-=])\s*", r" \1 ", wert)
    return _MEHRFACH_LEER.sub(" ", wert).strip()


def ist_gleichwertig(a: str | None, b: str | None) -> bool:
    """Gleiche Antwort in anderer Schreibweise?"""
    links, rechts = normalisiere(a), normalisiere(b)
    return bool(links) and links == rechts
