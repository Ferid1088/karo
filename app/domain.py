"""Fachlogik.

Hier steht die Regel, die das Produkt ausmacht: welche Flagge ein Thema
bekommt. Sie ist eine reine Funktion — kein Modell, kein Zufall, kein
Zustand — und damit testbar.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# --------------------------------------------------------------------------
# Fehlertypen
# --------------------------------------------------------------------------

class ErrorType(str, Enum):
    KONZEPTFEHLER = "konzeptfehler"
    REGEL_VERGESSEN = "regel_vergessen"
    RECHENFEHLER = "rechenfehler"
    FLUECHTIGKEIT = "fluechtigkeit"
    AUFGABE_MISSVERSTANDEN = "aufgabe_missverstanden"
    NICHT_BEARBEITET = "nicht_bearbeitet"


#: Nur diese Fehler deuten auf fehlendes Verstaendnis hin und loesen Rot aus.
#: Ein Rechenfehler ist kein Wissensproblem.
CONCEPTUAL_ERRORS = frozenset(
    {ErrorType.KONZEPTFEHLER.value, ErrorType.REGEL_VERGESSEN.value})

#: Zaehlt ueberhaupt nicht als Evidenz.
NON_EVIDENCE = frozenset({ErrorType.NICHT_BEARBEITET.value})

ERROR_LABELS = {
    ErrorType.KONZEPTFEHLER.value: "Konzept nicht verstanden",
    ErrorType.REGEL_VERGESSEN.value: "Regel nicht abgerufen",
    ErrorType.RECHENFEHLER.value: "Rechenfehler",
    ErrorType.FLUECHTIGKEIT.value: "Flüchtigkeit",
    ErrorType.AUFGABE_MISSVERSTANDEN.value: "Aufgabe missverstanden",
    ErrorType.NICHT_BEARBEITET.value: "Nicht bearbeitet",
}


# --------------------------------------------------------------------------
# Flaggen
# --------------------------------------------------------------------------

class Flag(str, Enum):
    WEISS = "weiss"      # noch nicht geprüft
    ROT = "rot"          # Verständnislücke
    GELB = "gelb"        # wackelig
    GRUEN = "gruen"      # sitzt


FLAG_LABELS = {
    Flag.WEISS.value: "noch nicht geprüft",
    Flag.ROT.value: "Lücke",
    Flag.GELB.value: "wackelig",
    Flag.GRUEN.value: "sitzt",
}

FLAG_SYMBOLS = {
    Flag.WEISS.value: "○",
    Flag.ROT.value: "●",
    Flag.GELB.value: "●",
    Flag.GRUEN.value: "●",
}

#: Reihenfolge in Listen: was Aufmerksamkeit braucht, steht oben.
FLAG_ORDER = [Flag.ROT.value, Flag.GELB.value, Flag.WEISS.value, Flag.GRUEN.value]

#: Diese Flaggen loesen eine Lerneinheit aus.
NEEDS_TEACHING = frozenset({Flag.ROT.value, Flag.GELB.value})


# --------------------------------------------------------------------------
# Eingabe der Regel
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Answer:
    """Eine ausgewertete Antwort, so wie sie in die Regel eingeht."""

    tag: str                    # ISO-Datum, als String sortierbar
    richtig: bool
    fehlertyp: str | None = None
    created_at: str = ""        # zweites Sortierkriterium
    seq: int = 0                # Datenbank-ID, macht die Reihenfolge eindeutig


@dataclass(frozen=True)
class Rule:
    """Die Schwellen. Startwerte, keine Wahrheit — deshalb konfigurierbar."""

    gruen_richtige: int = 3         # so viele richtige Antworten insgesamt
    gruen_tage: int = 2             # so viele fehlerfreie Übungstage am Ende
    rot_konzeptfehler: int = 2      # so viele Verständnisfehler im Fenster
    fenster: int = 5                # Größe des Fensters
    min_evidenz: int = 2            # weniger heißt: keine Aussage

    @classmethod
    def from_config(cls, cfg) -> "Rule":
        return cls(
            gruen_richtige=cfg.rule_gruen_richtige,
            gruen_tage=cfg.rule_gruen_tage,
            rot_konzeptfehler=cfg.rule_rot_konzeptfehler,
            fenster=cfg.rule_fenster,
            min_evidenz=cfg.rule_min_evidenz,
        )


@dataclass(frozen=True)
class FlagResult:
    flag: str
    antworten: int
    richtig: int
    haupt_fehler: str | None
    letzte_uebung: str | None
    begruendung: str


def _sortiert(antworten: list[Answer]) -> list[Answer]:
    """Sortiert eindeutig.

    Alle Antworten eines Arbeitsblattes teilen Datum und Zeitstempel. Ohne das
    dritte Kriterium haenge das Ergebnis davon ab, in welcher Reihenfolge die
    Datenbank die Zeilen liefert.
    """
    brauchbar = [a for a in antworten if (a.fehlertyp or "") not in NON_EVIDENCE]
    return sorted(brauchbar, key=lambda a: (a.tag, a.created_at, a.seq))


def compute_flag(antworten: list[Answer], rule: Rule | None = None) -> FlagResult:
    """Bestimmt die Flagge eines Themas.

    Die Reihenfolge der Pruefungen ist Absicht:
      1. Zu wenig Evidenz          -> weiss (ehrlicher als eine Vermutung)
      2. Wiederholter Konzeptfehler -> rot
      3. Saubere Übungstage         -> gruen
      4. Sonst                      -> gelb

    Eine einzelne falsche Antwort fuehrt nie zu Rot, eine einzelne richtige
    nie zu Gruen.

    Gruen wird in TAGEN gerechnet, nicht in Zeilen: ein Arbeitsblatt liefert
    fuenf bis zehn Antworten am selben Tag, und eine zeilenbasierte Regel
    waere in der normalen Nutzung nie erreichbar.
    """
    rule = rule or Rule()
    ev = _sortiert(antworten)

    if not ev:
        return FlagResult(Flag.WEISS.value, 0, 0, None, None,
                          "noch keine verwertbare Antwort")

    letzte = ev[-1].tag
    richtig = sum(1 for a in ev if a.richtig)

    falsch = [a for a in ev if not a.richtig]
    zaehler: dict[str, int] = {}
    for a in falsch:
        if a.fehlertyp:
            zaehler[a.fehlertyp] = zaehler.get(a.fehlertyp, 0) + 1
    haupt = max(zaehler, key=lambda k: zaehler[k]) if zaehler else None

    if len(ev) < rule.min_evidenz:
        return FlagResult(Flag.WEISS.value, len(ev), richtig, haupt, letzte,
                          f"weniger als {rule.min_evidenz} Antworten")

    fenster = ev[-rule.fenster:]
    konzept = [a for a in fenster
               if not a.richtig and (a.fehlertyp or "") in CONCEPTUAL_ERRORS]
    if len(konzept) >= rule.rot_konzeptfehler:
        return FlagResult(
            Flag.ROT.value, len(ev), richtig, haupt, letzte,
            f"{len(konzept)} Verständnisfehler in den letzten {len(fenster)} Antworten")

    tage: list[str] = []
    for a in ev:
        if a.tag not in tage:
            tage.append(a.tag)
    letzte_tage = tage[-rule.gruen_tage:]
    sauber = all(a.richtig for a in ev if a.tag in letzte_tage)

    if (len(letzte_tage) >= rule.gruen_tage and sauber
            and richtig >= rule.gruen_richtige):
        return FlagResult(
            Flag.GRUEN.value, len(ev), richtig, haupt, letzte,
            f"{richtig}× richtig, die letzten {len(letzte_tage)} Übungstage "
            "vollständig fehlerfrei")

    return FlagResult(Flag.GELB.value, len(ev), richtig, haupt, letzte,
                      "gemischtes Bild")


# --------------------------------------------------------------------------
# Lernstufen: wie eine Erklaerung nach einem Fehlversuch aussieht
# --------------------------------------------------------------------------

class Stufe(str, Enum):
    NORMAL = "normal"
    EINFACHER = "einfacher"
    GANZ_EINFACH = "ganz_einfach"


STUFE_LABELS = {
    Stufe.NORMAL.value: "normale Erklärung",
    Stufe.EINFACHER.value: "einfacher, mehr Zwischenschritte",
    Stufe.GANZ_EINFACH.value: "ganz von vorn, mit Bildern und Alltagsbeispielen",
}

#: Nach einer nicht bestandenen Runde wird eine Stufe einfacher erklaert.
NEXT_STUFE = {
    Stufe.NORMAL.value: Stufe.EINFACHER.value,
    Stufe.EINFACHER.value: Stufe.GANZ_EINFACH.value,
    Stufe.GANZ_EINFACH.value: Stufe.GANZ_EINFACH.value,
}


# --------------------------------------------------------------------------
# Ausgabemodi fuer das Lernmaterial
# --------------------------------------------------------------------------

class Ausgabe(str, Enum):
    HTML = "html"
    MP4 = "mp4"
    NOTEBOOKLM = "notebooklm"


AUSGABE_LABELS = {
    Ausgabe.HTML.value: "Folien mit Stimme (im Browser)",
    Ausgabe.MP4.value: "Video als MP4-Datei",
    Ausgabe.NOTEBOOKLM.value: "NotebookLM-Video",
}

AUSGABE_HINTS = {
    Ausgabe.HTML.value:
        "Sofort fertig, läuft offline, nutzt die Sprachausgabe des "
        "Betriebssystems. Braucht nichts weiter.",
    Ausgabe.MP4.value:
        "Eine echte Videodatei, überall abspielbar — auch am Fernseher. "
        "Dauert ein bis zwei Minuten und braucht die Sprachdateien im Image.",
    Ausgabe.NOTEBOOKLM.value:
        "Nutzt Ihr NotebookLM-Konto. Am aufwändigsten und am unzuverlässigsten: "
        "die Anmeldung läuft alle paar Wochen ab und bricht bei Google-Updates.",
}


# --------------------------------------------------------------------------
# Dokumentzustaende in verstaendlichem Deutsch
# --------------------------------------------------------------------------

DOC_STATE_LABELS = {
    "neu": "eingelesen",
    "gelesen": "wird ausgewertet",
    "erschlossen": "in der Wissensbasis",
    "diagnostiziert": "zur Freigabe bereit",
    "leer": "nichts erkannt",
    "freigegeben": "freigegeben",
    "verworfen": "verworfen",
}

DOC_STATE_HINTS = {
    "neu": "Karo liest das Blatt gerade ein.",
    "gelesen": "Die Auswertung läuft. Dauert das länger als ein paar Minuten, "
               "steht der Grund im Eingang unter „Fehlgeschlagene Vorgänge“.",
    "leer": "Auf dem Bild war nichts erkennbar — meist liegt es an der "
            "Bildqualität.",
}

DOKUMENT_ROLLEN = {
    "wissen": "Erklärung oder Aufgabenblatt (kommt in die Wissensbasis)",
    "bearbeitet": "vom Kind bearbeitet (wird ausgewertet)",
}
