"""Karos eigene Fachpruefung: welches Fach ein geschriebener Text meint.

Die Schluessel, Namen und Aliase liegen in `karo_contract.faecher` — die
braucht der Lehrplan-Dienst genauso, und zwei fast gleiche Listen sind die
Sorte Unterschied, die erst im Betrieb auffaellt. Was hier steht, ist
dagegen Karos Sache: der Katalog verfasster Lektionen und das Modell.

Fachfremdes erkennt `pruefe()` in zwei Stufen, die billigere zuerst:

    1. ohne Modell: verfasste Lektionen im Katalog und typische Stichworte
    2. nur wenn 1. nichts sagt: das Modell ordnet den Text einem Fach zu

Was nicht passt, wird mit `SUBJECT_MISMATCH` abgewiesen und nie im falschen
Fach gespeichert.
"""
from __future__ import annotations

import logging

from karo_contract.faecher import *                 # noqa: F401,F403
from karo_contract.faecher import _flach            # geteilte Grundform

log = logging.getLogger(__name__)


#: Woran sich ein Fach ohne Modell sicher erkennen laesst. Nur Woerter, die
#: in genau ein Fach gehoeren: „Verben" oder „Zeitformen" gibt es in Deutsch
#: und Englisch und stehen deshalb hier nicht.
_STICHWORTE = {
    "mathematik": (
        "bruch", "brueche", "bruchrechnung", "nenner", "zaehler", "dezimalzahl",
        "prozent", "prozentrechnung", "gleichung", "gleichungen", "term", "terme",
        "geometrie", "dreieck", "viereck", "rechteck", "kreis", "winkel", "flaeche",
        "flaecheninhalt", "umfang", "volumen", "wuerfel", "quader", "prisma",
        "multiplikation", "division", "addition", "subtraktion", "einmaleins",
        "addieren", "subtrahieren", "multiplizieren", "dividieren", "kuerzen",
        "erweitern", "potenz", "potenzen", "wurzel", "funktion", "funktionen",
        "koordinatensystem", "zuordnung", "dreisatz", "statistik", "wahrscheinlichkeit",
        "negative zahlen", "ganze zahlen", "rationale zahlen", "pythagoras",
        "rechnen", "kopfrechnen", "schriftlich", "teilbarkeit", "primzahl", "primzahlen",
    ),
    "englisch": (
        "present", "past", "simple", "progressive", "continuous", "perfect",
        "future", "going to", "will future", "irregular", "vocabulary",
        "grammar", "tense", "tenses", "adverb of frequency", "question tags",
        "if clauses", "if clause", "conditional", "passive voice", "reported speech",
        "some any", "much many", "comparison of adjectives", "englische",
        "english", "englisch", "vokabeln englisch", "unit",
    ),
    "deutsch": (
        "rechtschreibung", "kommasetzung", "komma", "diktat", "aufsatz",
        "eroerterung", "inhaltsangabe", "bericht", "beschreibung", "erzaehlung",
        "gedicht", "gedichte", "lyrik", "ballade", "fabel", "maerchen", "novelle",
        "satzglieder", "satzglied", "subjekt", "praedikat", "objekt", "kasus",
        "faelle", "nominativ", "genitiv", "dativ", "akkusativ", "konjunktiv",
        "wortarten", "nomen", "substantiv", "artikel", "pronomen", "praeposition",
        "konjunktion", "gross und kleinschreibung", "das dass", "s laute",
        "argumentieren", "lesen", "leseverstehen", "deutsche",
    ),
    ANDERE: (
        "biologie", "physik", "chemie", "geschichte", "erdkunde", "geografie",
        "geographie", "franzoesisch", "latein", "spanisch", "kunst", "musik",
        "religion", "ethik", "sport", "informatik", "sachunterricht", "politik",
        "photosynthese", "zelle", "zellen", "atom", "atome", "elektrischer strom",
        "mittelalter", "roemer", "weltkrieg", "vulkane", "kontinente",
    ),
}


def erkenne(text: str | None) -> str | None:
    """Fach eines Textes ohne Modell — oder None, wenn es nicht eindeutig ist.

    Zuerst der Katalog: trifft der Text eine verfasste Lektion, ist deren
    Fach die Antwort. Dann die Stichworte. Ein Gleichstand ist keine Antwort.
    """
    flach = _flach(text)
    if not flach:
        return None
    try:
        from .adaptiv import lektionen
        from .adaptiv.normalisierung import normalisiere_thema
        gesucht = normalisiere_thema(text)
        treffer = {schluessel(l["fach"]) for l in lektionen.verfuegbar()
                   if gesucht and lektionen._trifft(gesucht, l)}
        treffer.discard(None)
        if len(treffer) == 1:
            return treffer.pop()
    except Exception:                       # pragma: no cover - Katalog fehlt
        log.debug("Katalog für die Fachprüfung nicht verfügbar", exc_info=True)
    woerter = f" {flach} "
    punkte = {fach: sum(f" {wort} " in woerter for wort in liste)
              for fach, liste in _STICHWORTE.items()}
    bester = max(punkte, key=punkte.get)
    if punkte[bester] and list(punkte.values()).count(punkte[bester]) == 1:
        return bester
    return None


FACH_SCHEMA = {
    "type": "object",
    "properties": {"fach": {"type": "string", "enum": [*FAECHER, ANDERE]}},
    "required": ["fach"],
}


def _modell(text: str, fach: str) -> str | None:
    """Stufe 2: das Modell entscheidet, wenn Katalog und Stichworte schweigen.

    Kann das Modell nicht antworten, bleibt es bei „unbekannt“: eine
    ausgefallene Prüfung darf das Anlegen nicht blockieren, die erste Stufe
    hat dann schon alles Eindeutige abgefangen.
    """
    from . import config, pii
    cfg = config.load_safe()
    if not getattr(cfg, "has_credentials", False) or not getattr(cfg, "model_text", ""):
        return None
    try:
        from .llm.client import ClaudeClient
        antwort = ClaudeClient.from_config(cfg, 20).complete(
            purpose="fach_pruefen", max_tokens=64, schema=FACH_SCHEMA,
            prompt=("Zu welchem Schulfach gehört dieses Lernthema eines Schulkinds? "
                    "Antworte mit deutsch, mathematik, englisch oder andere.\n"
                    f"Aktives Fach: {NAMEN[fach]}\n"
                    f"Thema: {pii.scrub(text, cfg.learner_name)[:300]}"))
        wert = str((antwort.data or {}).get("fach", "")).strip().lower()
    except Exception:
        log.info("Fachprüfung durch das Modell nicht möglich", exc_info=True)
        return None
    return wert if wert in (*FAECHER, ANDERE) else None


def pruefe(text: str | None, fach: str, *, modell: bool = True) -> str:
    """Gibt den Fach-Schlüssel zurück oder wirft `SubjectMismatch`."""
    fach = pflicht(fach)
    erkannt = erkenne(text)
    if erkannt is None and modell:
        erkannt = _modell(text or "", fach)
    if erkannt and erkannt != fach:
        raise SubjectMismatch(fach, erkannt)
    return fach
