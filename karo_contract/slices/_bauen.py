"""Bausteine für die Slice-Dateien — kurze Formen für die
wiederkehrenden Strukturen (Aufgabe, Auswahl, Dienst-Item, Antworttypen).

Nur Schreibhilfen, kein Inhalt: jedes Wort steht weiter in den
Slice-Dateien selbst.
"""

from __future__ import annotations

from typing import Any


def aufgabe(frage: str, loesung: str, *, fehler: str | None = None,
            tipps: list[str] | None = None, schritte: list[str] | None = None,
            art: str | None = None, rubrik: dict | None = None,
            sekunden: int | None = None) -> dict[str, Any]:
    """Eine gerechnete/überprüfte Aufgabe — kurze Form für die Slice-Autoren.

    `art` ist der Auswertungstyp (z. B. ``begriffe``, ``zahl_einheit``);
    `rubrik` trägt die Bewertungsregeln (benötigte Begriffe, Einheiten).
    """
    a: dict[str, Any] = {"frage": frage, "loesung": loesung}
    if fehler:
        a["typischer_fehler"] = fehler
    if tipps:
        a["tipps"] = tipps
    if schritte:
        a["schritte"] = schritte
    if art:
        a["antwort_art"] = art
    if rubrik:
        a["rubrik"] = rubrik
    if sekunden:
        a["erwartete_sekunden"] = sekunden
    return a


def begriffe(*woerter: str, mindestens: int | None = None,
             teilweise: str | None = None) -> dict:
    """Rubrik für Freitext-Antworten: welche Begriffe eine vollständige
    Antwort nennen muss. Deckt die Schreibvarianten ab, die ein
    Zeichenkettenvergleich bestraft („Fuchs" vs. „ein Fuchs", „Dativ" vs.
    „Dativobjekt") — das Kind bekommt Anerkennung für das, was es weiss,
    und Karo sieht genau, welcher Begriff noch fehlt."""
    rubrik: dict[str, Any] = {"begriffe": list(woerter),
                              "mindestens": mindestens or len(woerter)}
    if teilweise:
        rubrik["hinweise"] = {"teilweise": teilweise}
    return rubrik


def auswahl(frage: str, loesung: str, falsch: list[str],
            aufloesung: str) -> dict[str, Any]:
    """Eine Auswahlaufgabe (vorhersage/transfer): Lösung steht unter den
    Optionen, die übrigen sind plausible Fehlvorstellungen."""
    return {"frage": frage, "loesung": loesung,
            "optionen": [loesung, *falsch], "aufloesung": aufloesung}


def item(prompt: str, solution: str, *, level: str, grade: int,
         answer: dict | None = None, distractors: list[dict] | None = None,
         representation: str | None = None) -> dict[str, Any]:
    """Eine Dienst-Aufgabe (anchor/boundary/diagnostic/exit).

    `answer` ist die auswertbare Antwort im Dienst-Format
    (``{"type": "number", "value": "42"}``, ``{"type": "choice", …}`` …);
    `distractors` tragen die typischen Fehlantworten mit ihrem
    Misconception-Key.
    """
    it: dict[str, Any] = {"prompt": prompt, "solution": solution,
                          "level": level, "grade": grade,
                          "distractors": distractors or []}
    if answer:
        it["answer"] = answer
    if representation:
        it["representation"] = representation
    return it


def number(value, *, tolerance: float = 0, unit: str | None = None) -> dict:
    try:
        v: float | int = int(str(value))
    except ValueError:
        v = float(str(value))
    a: dict[str, Any] = {"type": "number", "value": v,
                         "tolerance": tolerance}
    if unit:
        a["unit"] = unit
    return a


def text(*accepted: str) -> dict:
    return {"type": "text", "accepted": list(accepted),
            "case_sensitive": False, "ignore_punctuation": True}


def choice(loesung: str, falsche: list[str],
           miscon: list[str | None] | None = None) -> dict:
    """Single-Choice-Antwort: genau eine Option richtig, die übrigen
    verraten optional eine Misconception (`miscon`-Liste parallel zu
    `falsche`, ``None`` für neutrale Distraktoren)."""
    options = [{"text": loesung, "correct": True}]
    for i, f in enumerate(falsche):
        o: dict[str, Any] = {"text": f, "correct": False}
        if miscon and miscon[i]:
            o["misconception"] = miscon[i]
        options.append(o)
    return {"type": "choice", "options": options, "multiple": False}
