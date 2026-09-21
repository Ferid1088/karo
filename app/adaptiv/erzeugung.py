"""Eine vorgeschlagene Lektion prüfen, schreiben und freigeben.

Schritt 2 der Erzeugung. Was hier hereinkommt, hat ein Modell vorgeschlagen
(§5 Modell A); was hier hinausgeht, ist ein Katalogeintrag wie jeder andere
und wird beim nächsten Kind ohne Modellaufruf ausgeliefert (§11, A3).

**Die Freigabe kommt zuletzt, und das trägt die Atomarität.** Die
Schreibvorgänge laufen über mehrere Transaktionen; bräche einer davon ab,
stünde eine halbe Lektion in der Datenbank. Weil aber alles ungeprüft
geschrieben und erst am Ende freigegeben wird, ist eine halbe Lektion für
ein Kind unsichtbar — die Sperre aus §11 erledigt das, wofür es sonst eine
umspannende Transaktion bräuchte.

**Freigegeben wird nach bestandener Prüfung, ohne Klick.** Ungeprüft heisst
weiterhin unsichtbar; die Sperre wartet nur nicht mehr auf einen Menschen.
Roher Modelltext erreicht damit nie ein Kind — aber auch kein Elternteil
muss zwischen Frage und Antwort treten.
"""

from __future__ import annotations

from . import inhalt_store, schemas, store
from .normalisierung import normalisiere

#: Herkunft dieser Einträge (§6: „creation source").
QUELLE = "erzeugt"

#: Welche Rolle als Auswahl gestellt wird statt als Rechnung.
_ALS_AUSWAHL = {"vorhersage", "transfer"}


def _aufgabe_schreiben(fehlertyp_id: int, rolle: str, aufgabe: dict) -> None:
    inhalt_store.aufgabe_sichern(
        fehlertyp_id, rolle, aufgabe["frage"], aufgabe["loesung"],
        tipps=aufgabe.get("tipps"), schritte=aufgabe.get("schritte"),
        typischer_fehler=aufgabe.get("typischer_fehler"),
        antwort_art=(inhalt_store.AUSWAHL if rolle in _ALS_AUSWAHL
                     else inhalt_store.BRUCH),
        optionen=aufgabe.get("optionen"),
        aufloesung=aufgabe.get("aufloesung"),
        quelle=QUELLE, geprueft=False)


def speichern(rohdaten: dict, fach: str = "mathematik") -> int:
    """Prüft den Vorschlag und schreibt ihn in den Katalog. Gibt die
    Konzept-Id zurück.

    Wirft `schemas.InhaltUngueltig`, bevor irgendetwas geschrieben wurde —
    ein abgewiesener Vorschlag hinterlässt keinen halben Eintrag.
    """
    lektion = schemas.pruefe_lektion(rohdaten)
    konzept = lektion["konzept"]

    konzept_id = store.konzept_sichern(
        fach, konzept["thema_key"], konzept["konzept_key"], konzept["label"],
        konzept["klasse_von"], konzept["klasse_bis"],
        stichworte=konzept["stichworte"], quelle=QUELLE, geprueft=False)

    fehlertyp_ids = []
    for fehler in lektion["fehlertypen"]:
        fehlertyp_id = store.fehlertyp_sichern(
            konzept_id, fehler["key"], fehler["label"],
            fehler["beschreibung"], quelle=QUELLE, geprueft=False)
        fehlertyp_ids.append(fehlertyp_id)

        for antwort in fehler["antworten"]:
            store.alias_sichern(fehlertyp_id, normalisiere(antwort), QUELLE)

        if not store.beste_erklaerung(fehlertyp_id, konzept["klasse_bis"]):
            store.erklaerung_anlegen(
                fehlertyp_id, konzept["klasse_bis"], fehler["erklaerung"],
                visualisierung=fehler["visualisierung"],
                visualisierung_alternativ=fehler.get(
                    "visualisierung_alternativ"),
                quelle=QUELLE, geprueft=False)

        for rolle, aufgabe in fehler["aufgaben"].items():
            _aufgabe_schreiben(fehlertyp_id, rolle, aufgabe)

    erstkontakt = lektion.get("erstkontakt")
    if erstkontakt and not store.erstkontakt(konzept_id):
        store.erstkontakt_anlegen(
            konzept_id, erstkontakt["anker"], erstkontakt["erste_aufgabe"],
            erstkontakt["benennung"], quelle=QUELLE, geprueft=False)

    _freigeben(konzept_id, fehlertyp_ids)
    return konzept_id


def _freigeben(konzept_id: int, fehlertyp_ids: list) -> None:
    """Erst jetzt wird die Lektion sichtbar — und zwar in einem Zug."""
    for fehlertyp_id in fehlertyp_ids:
        store.fehlertyp_freigeben(fehlertyp_id)
        for erklaerung in store.erklaerungen(fehlertyp_id):
            store.erklaerung_freigeben(erklaerung["id"])
        inhalt_store.aufgaben_freigeben(fehlertyp_id)
    store.erstkontakt_freigeben(konzept_id)
    store.konzept_freigeben(konzept_id)
