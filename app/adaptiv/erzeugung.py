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

#: Eine ganze Lernreihe ist um ein Vielfaches länger als eine Fragerunde:
#: zwei bis vier Fehlvorstellungen mit je fünf Aufgaben, dazu Hilfe für
#: sechs Phasen und die FAQ. Mit der üblichen Vorgabe bricht die Antwort
#: mittendrin ab, und die Prüfung verwirft sie als unvollständig.
MAX_TOKENS = 32000

#: Entsprechend länger darf der Aufruf dauern. Gemessen auf der
#: Testinstallation: 240 bis 300 Sekunden — genau an der üblichen Grenze,
#: weshalb jeder zweite Versuch als Zeitüberschreitung endete.
TIMEOUT_SEKUNDEN = 900

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

    for phase, hilfe in lektion["hilfe"].items():
        inhalt_store.hilfe_sichern(
            konzept_id, inhalt_store.HILFE_PHASE, phase, hilfe["text"],
            visualisierung=hilfe.get("visualisierung"), geprueft=False)
    for i, eintrag in enumerate(lektion["faq"]):
        inhalt_store.hilfe_sichern(
            konzept_id, inhalt_store.HILFE_FAQ, eintrag["frage"],
            eintrag["antwort"], sortierung=i, geprueft=False)

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
    inhalt_store.hilfe_freigeben(konzept_id)
    store.erstkontakt_freigeben(konzept_id)
    store.konzept_freigeben(konzept_id)


# --------------------------------------------------------------------------
# Auf Anfrage erzeugen (§5 Modell A, §6 Tier 3, §15 Latenz)
# --------------------------------------------------------------------------

def auftrag_schluessel(thema: str) -> str:
    """Ein Thema, ein Auftrag. Zweimal klicken erzeugt nicht zweimal."""
    return f"lektion:{normalisiere(thema)}"


def anfordern(thema: str) -> int | None:
    """Reiht die Erzeugung ein. Gibt None zurück, wenn schon eine läuft."""
    from .. import jobs
    return jobs.enqueue("lektion_erzeugen", {"thema": thema},
                        dedup_key=auftrag_schluessel(thema))


def laeuft(thema: str) -> bool:
    from .. import db
    return bool(db.q1(
        "SELECT 1 FROM job WHERE dedup_key=? AND state IN ('wartend','laeuft')",
        auftrag_schluessel(thema)))


def _handler_anmelden():
    """Erst beim Import von `jobs` registrieren — sonst zieht diese Datei
    die halbe Anwendung in die adaptive Schicht, nur um geladen zu werden."""
    from .. import config, jobs, pii, prompts
    from ..llm.client import ClaudeClient

    @jobs.handler("lektion_erzeugen")
    def job_lektion_erzeugen(payload: dict) -> dict:
        """Der erste echte Modellaufruf des adaptiven Lernens.

        Im Hintergrund, nicht im Klick des Kindes: eine Lektion zu schreiben
        dauert, und §15 verlangt, dass niemand vor einem Spinner sitzt.

        Schlägt die Prüfung fehl, wirft `speichern()` — der Auftrag landet
        auf „fehler", und es bleibt nichts Halbes zurück. Lieber keine
        Lektion als eine falsche.
        """
        thema = str(payload.get("thema") or "").strip()
        if not thema:
            return {"uebersprungen": "kein Thema"}
        cfg = config.load()
        # §5: Modell A schreibt Didaktik und ist das starke Modell. Ohne
        # ausdrückliche Wahl nähme `complete()` das kleine Textmodell —
        # das schrieb Komponentenparameter, die die Prüfung verwarf.
        ergebnis = ClaudeClient.from_config(cfg, TIMEOUT_SEKUNDEN).complete(
            purpose="lektion_erzeugen",
            model=cfg.model_vision or None,
            max_tokens=MAX_TOKENS,
            prompt=prompts.lektion_prompt(
                cfg.learner_grade, cfg.subject,
                pii.scrub(thema, cfg.learner_name)),
            schema=prompts.LEKTION_SCHEMA,
            system=prompts.SYSTEM,
        )
        konzept_id = speichern(ergebnis.data)
        return {"konzept_id": konzept_id, "thema": thema}

    return job_lektion_erzeugen


job_lektion_erzeugen = _handler_anmelden()
