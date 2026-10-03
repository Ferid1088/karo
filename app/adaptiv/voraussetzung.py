"""Vor der Eskalation: liegt es am Konzept — oder an einer Voraussetzung?

Karo hat bei einem Kind, das dreimal hängenblieb, einen Menschen geholt. Das
ist richtig, wenn das Konzept selbst zu schwer ist. Es ist falsch, wenn in
Wahrheit eine Voraussetzung fehlt: wer Brüche nicht erweitern kann, scheitert
beim Addieren an etwas, das zwei Schritte davor liegt. Eine Erklärung zum
Addieren hilft dort nicht, und ein Mensch zu holen ist zu viel für ein
Problem, das Karo selbst lösen kann.

Also wird vorher kurz nachgesehen. Die Diagnose ist dieselbe wie sonst: zwei
geprüfte Aufgaben zum Voraussetzungskonzept, nicht mehr. Fällt sie aus, lernt
das Kind erst die Voraussetzung und kommt danach zurück. Sitzt sie, war es
nicht die Voraussetzung — dann eskaliert Karo wie bisher.

Was hier NICHT passiert: raten. Steht keine Voraussetzung in der Lieferung,
oder ist sie noch nicht importiert, bleibt es bei der Eskalation. Lieber
einen Menschen holen als ein Kind auf ein Konzept schicken, das Karo gar
nicht unterrichten kann.
"""
from __future__ import annotations

from .. import config
from . import inhalt_store, store

#: So viele geprüfte Aufgaben entscheiden, ob eine Voraussetzung sitzt.
#: Dieselbe Zahl wie bei der Ersteinschätzung: eine Aufgabe belegt nichts.
AUFGABEN = config.ops().voraussetzung_aufgaben


def offene(konzept_id: int, child_key: str = store.CHILD_KEY) -> list[dict]:
    """Voraussetzungen, die Karo unterrichten kann und die noch nicht sitzen.

    Nur solche mit `lokal`: eine Voraussetzung, die Karo nicht hat, kann es
    auch nicht beibringen — die gehört in die Meldung an den Menschen, nicht
    in einen Lernweg ins Leere.
    """
    offen = []
    for v in store.voraussetzungen(konzept_id):
        if not v.get("lokal"):
            continue
        if sitzt(v["lokal"], child_key):
            continue
        offen.append(v)
    return offen


def fehlende_ohne_lektion(konzept_id: int) -> list[dict]:
    """Voraussetzungen, die Karo gar nicht unterrichten kann.

    Die stehen in der Meldung an den Menschen: ohne diese Angabe sucht er
    den Grund beim Kind.
    """
    return [v for v in store.voraussetzungen(konzept_id) if not v.get("lokal")]


def sitzt(konzept_id: int, child_key: str = store.CHILD_KEY) -> bool:
    """Gilt dieses Konzept als verstanden?

    Verstanden heißt: jede Fehlvorstellung des Konzepts steht im Fortschritt
    auf „sicher". Eine davon offen genügt, um es nicht als sicher zu zählen —
    die Fehlvorstellung ist die Einheit, nicht das Konzept.
    """
    fehlertypen = store.fehlertypen(konzept_id)
    if not fehlertypen:
        return False
    for f in fehlertypen:
        stand = store.fortschritt(konzept_id, f["id"], child_key=child_key) or {}
        if stand.get("mastery") != "sicher":
            return False
    return True


def diagnoseaufgaben(konzept_id: int) -> list[dict]:
    """Zwei geprüfte Aufgaben zum Voraussetzungskonzept — keine neuen."""
    gefunden = []
    for fehlertyp in store.fehlertypen(konzept_id):
        for aufgabe in inhalt_store.aufgaben(fehlertyp["id"], inhalt_store.SELBSTSTAENDIG):
            if aufgabe.get("frage") and aufgabe.get("loesung"):
                gefunden.append(aufgabe)
            if len(gefunden) >= AUFGABEN:
                return gefunden
    return gefunden


def pruefen(antworten: list[str], aufgaben: list[dict]) -> bool:
    """Sitzt die Voraussetzung? Nur wenn ALLE Aufgaben stimmen.

    Dieselbe Strenge wie bei der Ersteinschätzung: eine von zwei richtig ist
    ein Anfang, keine Sicherheit — und auf einer halben Voraussetzung baut
    das nächste Konzept nicht.
    """
    from .antwortvergleich import check_answer
    if not aufgaben or len(antworten) < len(aufgaben):
        return False
    return all(check_answer(antworten[i], a["loesung"],
                          a.get("antwort_art"))
               for i, a in enumerate(aufgaben))
