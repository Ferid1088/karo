"""Der Sitzungs-Zustandsautomat (§7), Eskalation (A5) und Beherrschung (A8).

Der Lernzustand liegt in der Datenbank, nicht in Routenlogik und nicht in der
Cookie-Session: A6 verlangt, dass eine Sitzung auch ein Neu-Login übersteht.
Jeder Übergang wird geschrieben, damit er prüfbar ist.
"""

from __future__ import annotations

from .. import config
from . import store

# §7 — Sitzungszustände
INPUT_RECEIVED = "INPUT_RECEIVED"
MATERIAL_ANALYZED = "MATERIAL_ANALYZED"
DIAGNOSING = "DIAGNOSING"
ERROR_IDENTIFIED = "ERROR_IDENTIFIED"
TEACHING = "TEACHING"
MASTERED = "MASTERED"
ESCALATED = "ESCALATED"

ZUSTAENDE = (INPUT_RECEIVED, MATERIAL_ANALYZED, DIAGNOSING, ERROR_IDENTIFIED,
             TEACHING, MASTERED, ESCALATED)

#: Endzustände — hier wird nichts mehr ausgeliefert.
ENDZUSTAENDE = (MASTERED, ESCALATED)

UEBERGAENGE: dict[str, tuple[str, ...]] = {
    INPUT_RECEIVED: (MATERIAL_ANALYZED,),
    MATERIAL_ANALYZED: (DIAGNOSING,),
    DIAGNOSING: (ERROR_IDENTIFIED, MASTERED, ESCALATED),
    ERROR_IDENTIFIED: (TEACHING,),
    TEACHING: (DIAGNOSING, MASTERED, ESCALATED),
    MASTERED: (),
    ESCALATED: (),
}

# §7 — Lernphasen innerhalb von TEACHING
HOOK = "HOOK"
RULE = "RULE"
WORKED_EXAMPLE = "WORKED_EXAMPLE"
GUIDED_TASK = "GUIDED_TASK"
INDEPENDENT_TASK = "INDEPENDENT_TASK"
ADAPTATION = "ADAPTATION"
COMPLETE = "COMPLETE"

PHASEN = (HOOK, RULE, WORKED_EXAMPLE, GUIDED_TASK, INDEPENDENT_TASK,
          ADAPTATION, COMPLETE)

PHASEN_UEBERGAENGE: dict[str, tuple[str, ...]] = {
    HOOK: (RULE,),
    RULE: (WORKED_EXAMPLE,),
    WORKED_EXAMPLE: (GUIDED_TASK,),
    GUIDED_TASK: (INDEPENDENT_TASK, ADAPTATION),
    INDEPENDENT_TASK: (COMPLETE, ADAPTATION),
    ADAPTATION: (GUIDED_TASK, INDEPENDENT_TASK),
    COMPLETE: (),
}


class UebergangVerboten(RuntimeError):
    """Ein nicht vorgesehener Übergang — Hinweis auf einen Fehler im Aufrufer."""


def _cfg(cfg=None):
    return cfg or config.load_safe()


def max_runden(cfg=None) -> int:
    """A5: endlich. Die Zahl steht in der Konfiguration, nicht im Code."""
    return max(1, int(getattr(_cfg(cfg), "adaptiv_max_lehrrunden", 3)))


def mastery_treffer(cfg=None) -> int:
    """A8: eine richtige Antwort ist nie Beherrschung."""
    return max(2, int(getattr(_cfg(cfg), "adaptiv_mastery_treffer", 2)))


def unbekannte_antworten(cfg=None) -> int:
    """Wie oft eine Antwort unerkannt bleiben darf (Z8).

    Stand als 3 im Code. Jede andere Schwelle des adaptiven Wegs war
    einstellbar, diese nicht — ohne Grund.
    """
    return max(1, int(getattr(_cfg(cfg), "adaptiv_unbekannte_antworten", 3)))


def beherrscht(erfolge: int, cfg=None) -> bool:
    return erfolge >= mastery_treffer(cfg)


# --------------------------------------------------------------------------
# Sitzung führen
# --------------------------------------------------------------------------

def starten(eingabe_id: int | None = None, konzept_id: int | None = None,
            child_key: str = store.CHILD_KEY) -> dict:
    sitzung_id = store.sitzung_anlegen(INPUT_RECEIVED, eingabe_id, konzept_id,
                                       child_key)
    store.ereignis_schreiben(sitzung_id, "sitzung gestartet",
                             nach_zustand=INPUT_RECEIVED)
    return store.sitzung(sitzung_id)


def laufende(child_key: str = store.CHILD_KEY) -> dict | None:
    """A6: dieselbe Phase nach Neuladen UND nach erneutem Login."""
    return store.offene_sitzung(child_key, abgeschlossen=ENDZUSTAENDE)


def wechsle(sitzung_id: int, nach_zustand: str, anlass: str = "",
            **felder) -> dict:
    aktuell = store.sitzung(sitzung_id)
    if aktuell is None:
        raise UebergangVerboten(f"Sitzung {sitzung_id} gibt es nicht.")
    von = aktuell["zustand"]
    if nach_zustand not in UEBERGAENGE.get(von, ()):
        raise UebergangVerboten(f"{von} → {nach_zustand} ist nicht vorgesehen.")
    store.sitzung_aktualisieren(sitzung_id, zustand=nach_zustand, **felder)
    store.ereignis_schreiben(sitzung_id, anlass or f"{von} → {nach_zustand}",
                             von_zustand=von, nach_zustand=nach_zustand)
    return store.sitzung(sitzung_id)


def wechsle_phase(sitzung_id: int, nach_phase: str, anlass: str = "") -> dict:
    aktuell = store.sitzung(sitzung_id)
    if aktuell is None:
        raise UebergangVerboten(f"Sitzung {sitzung_id} gibt es nicht.")
    if aktuell["zustand"] != TEACHING:
        raise UebergangVerboten("Lernphasen gibt es nur innerhalb von TEACHING.")
    von = aktuell["phase"]
    if von is not None and nach_phase not in PHASEN_UEBERGAENGE.get(von, ()):
        raise UebergangVerboten(f"Phase {von} → {nach_phase} ist nicht vorgesehen.")
    store.sitzung_aktualisieren(sitzung_id, phase=nach_phase)
    store.ereignis_schreiben(sitzung_id, anlass or f"Phase {von} → {nach_phase}",
                             von_phase=von, nach_phase=nach_phase)
    return store.sitzung(sitzung_id)


def fehler_erkannt(sitzung_id: int, fehlertyp_id: int,
                   antwort: str | None = None) -> dict:
    return wechsle(sitzung_id, ERROR_IDENTIFIED, "Fehlertyp erkannt",
                   fehlertyp_id=fehlertyp_id, letzte_antwort=antwort)


def unterricht_beginnen(sitzung_id: int, erklaerung_id: int | None = None,
                        phase: str = HOOK) -> dict:
    sitzung = wechsle(sitzung_id, TEACHING, "Unterricht beginnt",
                      erklaerung_id=erklaerung_id)
    store.sitzung_aktualisieren(sitzung_id, phase=phase)
    store.ereignis_schreiben(sitzung_id, "Phase gesetzt", nach_phase=phase)
    return store.sitzung(sitzung_id)


def runde_gescheitert(sitzung_id: int, antwort: str | None = None,
                      cfg=None) -> dict:
    """Eine erfolglose Lehrrunde zählen — und bei Bedarf eskalieren (A5).

    Es gibt keinen Weg, der diese Zählung umgeht: TEACHING kann nur über
    diese Funktion weiterlaufen, und sie eskaliert selbst.
    """
    sitzung = store.sitzung(sitzung_id)
    if sitzung is None:
        raise UebergangVerboten(f"Sitzung {sitzung_id} gibt es nicht.")
    if sitzung["zustand"] in ENDZUSTAENDE:
        return sitzung

    runden = (sitzung["runden"] or 0) + 1
    store.sitzung_aktualisieren(
        sitzung_id, runden=runden, versuche=(sitzung["versuche"] or 0) + 1,
        letzte_antwort=antwort)
    store.ereignis_schreiben(sitzung_id, "Lehrrunde ohne Erfolg",
                             nutzdaten={"runde": runden})
    if sitzung["konzept_id"]:
        store.fortschritt_buchen(sitzung["konzept_id"], sitzung["fehlertyp_id"],
                                 versuch=True, wiederholung=True,
                                 child_key=store.fortschritt_scope(sitzung))

    if runden >= max_runden(cfg):
        return eskalieren(sitzung_id)
    return store.sitzung(sitzung_id)


def eskalieren(sitzung_id: int) -> dict:
    """§7: Eskalation ist ein normaler Ausgang, kein Fehlerzustand.

    Danach wird keine weitere Erklärung mehr ausgeliefert, und der Fehlertyp
    ist im Profil als „braucht einen Menschen“ markiert.
    """
    sitzung = store.sitzung(sitzung_id)
    if sitzung is None:
        raise UebergangVerboten(f"Sitzung {sitzung_id} gibt es nicht.")
    if sitzung["zustand"] == ESCALATED:
        return sitzung
    ergebnis = wechsle(sitzung_id, ESCALATED, "nach erfolglosen Runden eskaliert")
    if sitzung["konzept_id"]:
        store.fortschritt_buchen(sitzung["konzept_id"], sitzung["fehlertyp_id"],
                                 mastery="braucht_mensch", braucht_mensch=True,
                                 child_key=store.fortschritt_scope(sitzung))
    return ergebnis


def antwort_richtig(sitzung_id: int, antwort: str | None = None, cfg=None,
                    darf_abschliessen: bool = True) -> dict:
    """Richtige Antwort verbuchen — Beherrschung erst ab der Schwelle (A8).

    `darf_abschliessen=False` bucht den Erfolg, beendet die Lektion aber
    nicht: die Rechnung allein schließt die selbstständige Phase noch nicht
    ab, der Transfer danach gehört dazu.
    """
    sitzung = store.sitzung(sitzung_id)
    if sitzung is None:
        raise UebergangVerboten(f"Sitzung {sitzung_id} gibt es nicht.")
    if sitzung["zustand"] in ENDZUSTAENDE:
        return sitzung

    store.sitzung_aktualisieren(
        sitzung_id, versuche=(sitzung["versuche"] or 0) + 1,
        letzte_antwort=antwort)
    store.ereignis_schreiben(sitzung_id, "Antwort richtig")

    if sitzung["erklaerung_id"]:
        # §19: Eine Erklärung wird an der nächsten Antwort gemessen.
        store.erklaerung_wirkte(sitzung["erklaerung_id"])

    erfolge = 0
    if sitzung["konzept_id"]:
        store.fortschritt_buchen(sitzung["konzept_id"], sitzung["fehlertyp_id"],
                                 versuch=True, erfolg=True,
                                 child_key=store.fortschritt_scope(sitzung))
        stand = store.fortschritt(sitzung["konzept_id"], sitzung["fehlertyp_id"],
                                 child_key=store.fortschritt_scope(sitzung))
        erfolge = (stand or {}).get("erfolge", 0)

    if beherrscht(erfolge, cfg) and darf_abschliessen:
        if sitzung["konzept_id"]:
            store.fortschritt_buchen(sitzung["konzept_id"],
                                     sitzung["fehlertyp_id"], mastery="sicher",
                                     child_key=store.fortschritt_scope(sitzung))
        return wechsle(sitzung_id, MASTERED, "Beherrschung erreicht")

    if sitzung["konzept_id"]:
        store.fortschritt_buchen(sitzung["konzept_id"], sitzung["fehlertyp_id"],
                                 mastery="im_aufbau", child_key=store.fortschritt_scope(sitzung))
    return store.sitzung(sitzung_id)


def darf_erklaeren(sitzung: dict) -> bool:
    """A5: Nach der Eskalation wird keine weitere Erklärung ausgeliefert."""
    return bool(sitzung) and sitzung.get("zustand") not in ENDZUSTAENDE
