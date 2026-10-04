"""Die eine Stelle, die entscheidet, was als Nächstes kommt.

Lernen und Klassenarbeit teilen denselben Zustandsautomaten — und damit
dieselbe Frage: welche Aktion trägt das Kind vom jetzigen Stand zum
nächsten sinnvollen Schritt? `fuer` beantwortet sie aus dem Sitzungsstand
allein und ist damit für beide Bereiche identisch; `unterricht` setzt die
gewählte Aktion dann in den konkreten Bildschirm um.

Bewusst kein Aktionstyp `AUFGEBEN`: wer hängen bleibt, bekommt eine
andere Erklärung, eine leichtere Aufgabe, eine Voraussetzung oder die
Begleitung — nie das Verlassen des Themas durch das System.
"""
from __future__ import annotations

from . import sitzung as zustand

#: Semantische Lernaktionen (Master-Auftrag §12). Die Engine kennt kein
#: GIVE_UP — jede Antwort dieser Funktion endet in einem Lernschritt oder
#: in einer Wahl des Kindes.
DIAGNOSE = "DIAGNOSE"
ERKLAEREN = "ERKLAEREN"
ERKLAEREN_ANDERS = "ERKLAEREN_ANDERS"
UEBUNG_GEFUEHRT = "UEBUNG_GEFUEHRT"
UEBUNG_SELBST = "UEBUNG_SELBST"
TRANSFER = "TRANSFER"
VORAUSSETZUNG_PRUEFEN = "VORAUSSETZUNG_PRUEFEN"
VORAUSSETZUNG_LERNEN = "VORAUSSETZUNG_LERNEN"
ZURUECK_ZUM_ZIEL = "ZURUECK_ZUM_ZIEL"
BEGLEITEN = "BEGLEITEN"
GESCHAFFT = "GESCHAFFT"


def _tage_bis_pruefung(daten: dict) -> int | None:
    """Wie viele Tage bis zur Klassenarbeit — None ohne Terminkontext.

    Die Sitzung traegt den Termin in `daten.pruefung` mit, seitdem sie im
    Exam-Bereich begann (§29): der Schirm weiss sonst nichts von der Uhr.
    """
    import datetime as dt
    termin = (daten.get("pruefung") or {}).get("exam_date")
    if not termin:
        return None
    try:
        tag = dt.date.fromisoformat(str(termin)[:10])
    except (TypeError, ValueError):
        return None
    from ..woche import plaene
    return (tag - plaene.today()).days


def fuer(sitzung: dict) -> dict:
    """Welche Lernaktion jetzt dran ist — rein aus dem Sitzungsstand.

    Gibt `{"aktion", "grund"}` zurück. Die Funktion verändert nichts:
    entscheiden und handeln bleiben getrennt, damit dieselbe Entscheidung
    auch geloggt und geprüft werden kann.
    """
    daten = dict(sitzung.get("daten") or {})

    # Eine offene Voraussetzung sticht jede Phase: erst prüfen oder
    # lernen, sonst scheitert dieselbe Stelle noch einmal.
    if daten.get("voraussetzung_offen"):
        if daten.get("voraussetzung_lernen"):
            return {"aktion": VORAUSSETZUNG_LERNEN,
                    "grund": "Voraussetzung fehlt — Umweg steht bereit"}
        tage = _tage_bis_pruefung(daten)
        if tage is not None and tage <= 1:
            # Ist die Arbeit morgen, kostet die kurze Pruefung nur Zeit:
            # die fehlende Voraussetzung wird sie kaum widerlegen. Direkt
            # das fehlende Stueck ueben ist der kuerzere ehrliche Weg —
            # Mastery wird trotzdem erst mit Bestehen vergeben.
            return {"aktion": VORAUSSETZUNG_LERNEN,
                    "grund": "Pruefung nahe — ohne Umweg-Umweg direkt das "
                             "fehlende Stueck lernen"}
        return {"aktion": VORAUSSETZUNG_PRUEFEN,
                "grund": "Voraussetzung fraglich — kurz prüfen"}

    name = sitzung["zustand"]
    phase = sitzung["phase"]

    if name == zustand.MASTERED:
        if daten.get("voraussetzung_detour"):
            return {"aktion": ZURUECK_ZUM_ZIEL,
                    "grund": "Umweg geschafft — zurück an die Stelle, "
                             "an der es hakte"}
        return {"aktion": GESCHAFFT, "grund": "Zielkompetenz erreicht"}

    if name == zustand.ESCALATED:
        # Begleitung ist die Unterstützungsstufe, nicht das Ende: welcher
        # Weg beim Weitermachen sinnvoll ist, entscheidet der Fehlertyp.
        if sitzung.get("fehlertyp_id"):
            return {"aktion": ERKLAEREN_ANDERS,
                    "grund": "Fehlertyp bekannt — andere Darstellung, "
                             "kleinere Schritte"}
        return {"aktion": DIAGNOSE,
                "grund": "Fehlertyp unbekannt — andere geprüfte Aufgabe"}

    if name == zustand.DIAGNOSING:
        return {"aktion": DIAGNOSE, "grund": "Einstieg läuft"}

    if name == zustand.TEACHING:
        if phase in (zustand.HOOK, zustand.RULE, zustand.WORKED_EXAMPLE):
            return {"aktion": ERKLAEREN,
                    "grund": f"Lehrphase {phase}"}
        if phase == zustand.GUIDED_TASK:
            return {"aktion": UEBUNG_GEFUEHRT, "grund": "mit Hilfe üben"}
        if phase == zustand.INDEPENDENT_TASK:
            if daten.get("gerechnet"):
                return {"aktion": TRANSFER,
                        "grund": "Einsicht an anderer Struktur prüfen"}
            return {"aktion": UEBUNG_SELBST, "grund": "allein üben"}
        if phase == zustand.ADAPTATION:
            return {"aktion": ERKLAEREN_ANDERS,
                    "grund": "andere Darstellung nach Fehlschlag"}

    return {"aktion": BEGLEITEN,
            "grund": f"Zustand {name} — Kind wählt den nächsten Schritt"}
