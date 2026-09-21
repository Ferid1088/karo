"""Prüfung jedes Inhalts, bevor er in die Datenbank oder in ein Template geht.

Zwei Invarianten hängen an dieser Datei (03_INVARIANTS.md):

A1  Kein Modell-Erzeugnis wird je ausgeführt. Ein Modell wählt eine Komponente
    und füllt Parameter — es liefert niemals HTML, SVG, JS oder CSS.
A2  Jede Modellausgabe ist schemageprüft. Kaputtes JSON erreicht weder die
    Datenbank noch ein Template; ein Schemafehler führt zu einem definierten
    Rückfall, nicht zu einem 500er.

Bewusst im Stil der bestehenden `prompts.py`-Schemas gehalten (einfache
Strukturen statt einer zweiten Validierungsbibliothek).
"""

from __future__ import annotations

import re
from typing import Any

# §3: Das Register führt die Komponenten, ihre Parameter und den Rückfall.
# Diese Datei prüft nur noch den Lehrinhalt und reicht Darstellungen dorthin
# weiter — es gibt genau eine Stelle, an der eine Auswahl gültig wird.
from . import komponenten

#: Sichere Rückfallkomponente, wenn eine Auswahl verworfen wird (§3, §15).
FALLBACK_VISUALISIERUNG = {"component": komponenten.FALLBACK.id,
                           "parameters": {}, "animation": "none"}

INHALT_FELDER = ("haken", "erkenntnis", "regel")
BILD_FELDER = ("zeigt", "bewegt", "bleibt_gleich")
AUFGABE_FELDER = ("frage", "loesung")

#: Markup, Skript oder Style — nichts davon darf je in einem Inhalt stehen.
_MARKUP = re.compile(
    r"<\s*/?\s*[a-z!]"          # <div, </p, <svg, <!--
    r"|&lt;\s*/?\s*[a-z]"       # maskiertes Markup
    r"|javascript\s*:"
    r"|\bon(?:error|load|click)\s*="
    r"|@import\b|\burl\s*\(",
    re.IGNORECASE)


class InhaltUngueltig(ValueError):
    """Der Inhalt passt nicht zum Schema und wird nicht gespeichert."""


def enthaelt_markup(wert: Any) -> bool:
    """True, wenn irgendwo im Wert Markup/Skript/Style steckt."""
    if isinstance(wert, str):
        return bool(_MARKUP.search(wert))
    if isinstance(wert, dict):
        return any(enthaelt_markup(v) for v in wert.values())
    if isinstance(wert, (list, tuple)):
        return any(enthaelt_markup(v) for v in wert)
    return False


def _text(daten: dict, feld: str, pfad: str = "") -> str:
    wert = daten.get(feld)
    if not isinstance(wert, str) or not wert.strip():
        raise InhaltUngueltig(f"„{pfad or feld}“ fehlt oder ist leer.")
    return wert.strip()


def pruefe_inhalt(daten: Any) -> dict:
    """Prüft das Lehrinhalts-Format aus §4 und gibt es gesäubert zurück.

    Wirft `InhaltUngueltig`, statt Halbfertiges durchzulassen — der Aufrufer
    entscheidet dann über den Rückfall.
    """
    if not isinstance(daten, dict):
        raise InhaltUngueltig("Inhalt ist kein Objekt.")
    if enthaelt_markup(daten):
        raise InhaltUngueltig("Inhalt enthält Markup oder Skript (A1).")

    sauber: dict[str, Any] = {f: _text(daten, f) for f in INHALT_FELDER}

    bild = daten.get("bild")
    if not isinstance(bild, dict):
        raise InhaltUngueltig("„bild“ fehlt.")
    sauber["bild"] = {f: _text(bild, f, f"bild.{f}") for f in BILD_FELDER}

    aufgabe = daten.get("aufgabe")
    if not isinstance(aufgabe, dict):
        raise InhaltUngueltig("„aufgabe“ fehlt.")
    sauber["aufgabe"] = {f: _text(aufgabe, f, f"aufgabe.{f}")
                         for f in AUFGABE_FELDER}
    tipp = aufgabe.get("tipp")
    if isinstance(tipp, str) and tipp.strip():
        sauber["aufgabe"]["tipp"] = tipp.strip()
    return sauber


def schwachstellen(inhalt: dict) -> list[str]:
    """Qualitätssignale aus §4 — nicht jeder Mangel ist ein Schemafehler.

    `erkenntnis` und `bild.bleibt_gleich` tragen die Didaktik. Sind sie dünn,
    ist die Erklärung schwach: melden statt ausliefern.
    """
    mangel = []
    if len((inhalt.get("erkenntnis") or "").split()) < 4:
        mangel.append("erkenntnis ist zu vage")
    bleibt = (inhalt.get("bild") or {}).get("bleibt_gleich") or ""
    if len(bleibt.split()) < 4:
        mangel.append("bild.bleibt_gleich ist zu vage")
    return mangel


def pruefe_visualisierung(daten: Any) -> dict:
    """Prüft eine Komponentenauswahl gegen das Register (§3).

    Erlaubt ist ausschließlich: Komponenten-Id, Parameter, Animationsmodus.
    Unbekannte Id oder unpassende Parameter → `InhaltUngueltig`; der Aufrufer
    nimmt dann `FALLBACK_VISUALISIERUNG`.
    """
    if not isinstance(daten, dict):
        raise InhaltUngueltig("Visualisierung ist kein Objekt.")
    if enthaelt_markup(daten):
        raise InhaltUngueltig("Visualisierung enthält Markup oder Skript (A1).")
    try:
        return komponenten.pruefe_auswahl(daten)
    except komponenten.ParameterUngueltig as exc:
        raise InhaltUngueltig(str(exc)) from None


def visualisierung_oder_fallback(daten: Any) -> tuple[dict, str | None]:
    """Nie werfen, immer etwas Sicheres liefern (§15: degradieren, nicht ausfallen)."""
    try:
        return pruefe_visualisierung(daten), None
    except InhaltUngueltig as exc:
        return dict(FALLBACK_VISUALISIERUNG), str(exc)
