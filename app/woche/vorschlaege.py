"""Die Vorschlagstabelle — ein Nachschlagewerk, kein Generator.

Kein Modell, keine Erzeugung, keine laufenden Kosten: Fach x Klassenstufe x
Anlass x Groesse ergibt einen Schritt. Das ist nachlesbar, pruefbar und kann
nichts erfinden.

Zwei Begriffe:

* **titel** — was im Angebot steht („einen Uebungstest machen").
* **einstieg** — die Handlung unter zwei Minuten, die keine Entscheidung
  verlangt („Schlag Mathe auf Seite 42 auf und lies die erste Aufgabe laut
  vor."). Sie ist das eigentliche Produkt: der Widerstand sitzt fast
  vollstaendig im Anfangen.

Der Anker (eine Zeile, die das Kind am Tag des Fachs selbst eingibt, z. B.
„Brueche, S. 42") macht den Einstieg konkret. Fehlt er, greift eine
koerperliche Variante, die ohne Inhaltskenntnis auskommt.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Fachgruppen — damit die Tabelle nicht pro Fach vervielfacht werden muss
# --------------------------------------------------------------------------

GRUPPEN = {
    "mathe": ("mathematik", "mathe"),
    "sprache": ("deutsch", "englisch", "franzoesisch", "französisch", "latein",
                "spanisch"),
    "natur": ("biologie", "chemie", "physik", "nwt", "naturwissenschaften"),
    "gesell": ("geschichte", "erdkunde", "geografie", "politik", "gemeinschaftskunde",
               "religion", "ethik", "wirtschaft"),
}

ANLAESSE = ("arbeit_fern", "arbeit_nah", "morgen", "hausaufgaben",
            "gemieden", "normal")

GROESSEN = ("klein", "mittel", "gross")

# Reihenfolge der Verkleinerung. Tiefer als 'klein' geht es nicht — das ist
# die Untergrenze aus dem Konzept.
KLEINER = {"gross": "mittel", "mittel": "klein", "klein": "klein"}

MINUTEN = {"klein": 2, "mittel": 8, "gross": 15}


def gruppe(fach: str) -> str:
    """Ordnet ein Fach einer Gruppe zu. Unbekanntes landet bei 'gesell'."""
    name = (fach or "").strip().lower()
    for schluessel, namen in GRUPPEN.items():
        if name in namen:
            return schluessel
    return "gesell"


# --------------------------------------------------------------------------
# Die Tabelle
# --------------------------------------------------------------------------
# (gruppe, anlass, groesse) -> titel
# --------------------------------------------------------------------------

_TITEL: dict[tuple[str, str, str], str] = {
    # ---- Mathe -----------------------------------------------------------
    ("mathe", "arbeit_fern", "klein"): "herausfinden, was in der Arbeit drankommt",
    ("mathe", "arbeit_fern", "mittel"): "die letzten drei Hausaufgaben durchsehen",
    ("mathe", "arbeit_fern", "gross"): "eine alte Aufgabe pro Thema rechnen",
    ("mathe", "arbeit_nah", "klein"): "das schwierigste Thema heraussuchen",
    ("mathe", "arbeit_nah", "mittel"): "das schwierigste Thema üben",
    ("mathe", "arbeit_nah", "gross"): "einen Übungstest machen",
    ("mathe", "morgen", "klein"): "die letzten zwei Hausaufgaben anschauen",
    ("mathe", "morgen", "mittel"): "eine Aufgabe pro Thema rechnen",
    ("mathe", "morgen", "gross"): "die Aufgaben vom letzten Blatt nachrechnen",
    ("mathe", "hausaufgaben", "klein"): "die erste Aufgabe lesen",
    ("mathe", "hausaufgaben", "mittel"): "die Hausaufgabe rechnen",
    ("mathe", "hausaufgaben", "gross"): "die Hausaufgabe rechnen und nachprüfen",
    ("mathe", "gemieden", "klein"): "5 Minuten reinschauen, nichts rechnen",
    ("mathe", "gemieden", "mittel"): "eine einzige leichte Aufgabe",
    ("mathe", "gemieden", "gross"): "eine Aufgabe, die du schon kannst",
    ("mathe", "normal", "klein"): "eine Aufgabe von heute ansehen",
    ("mathe", "normal", "mittel"): "drei Aufgaben rechnen",
    ("mathe", "normal", "gross"): "das aktuelle Thema durchrechnen",

    # ---- Sprachen --------------------------------------------------------
    ("sprache", "arbeit_fern", "klein"): "herausfinden, was in der Arbeit drankommt",
    ("sprache", "arbeit_fern", "mittel"): "die neuen Wörter einmal durchgehen",
    ("sprache", "arbeit_fern", "gross"): "den Text aus dem Unterricht noch einmal lesen",
    ("sprache", "arbeit_nah", "klein"): "die Wörter heraussuchen, die noch wackeln",
    ("sprache", "arbeit_nah", "mittel"): "die wackligen Wörter üben",
    ("sprache", "arbeit_nah", "gross"): "einen kurzen Text schreiben oder übersetzen",
    ("sprache", "morgen", "klein"): "die Wörter von den letzten zwei Stunden ansehen",
    ("sprache", "morgen", "mittel"): "die wichtigsten Regeln überfliegen",
    ("sprache", "morgen", "gross"): "die letzten Aufgaben noch einmal machen",
    ("sprache", "hausaufgaben", "klein"): "die Aufgabe einmal lesen",
    ("sprache", "hausaufgaben", "mittel"): "die Hausaufgabe machen",
    ("sprache", "hausaufgaben", "gross"): "die Hausaufgabe machen und laut lesen",
    ("sprache", "gemieden", "klein"): "5 Minuten reinschauen, nichts schreiben",
    ("sprache", "gemieden", "mittel"): "fünf Wörter, mehr nicht",
    ("sprache", "gemieden", "gross"): "einen kurzen Abschnitt lesen",
    ("sprache", "normal", "klein"): "die Wörter von heute einmal durchgehen",
    ("sprache", "normal", "mittel"): "zehn Wörter üben",
    ("sprache", "normal", "gross"): "Wörter üben und einen Satz damit bauen",

    # ---- Naturwissenschaften --------------------------------------------
    ("natur", "arbeit_fern", "klein"): "herausfinden, was in der Arbeit drankommt",
    ("natur", "arbeit_fern", "mittel"): "die Überschriften im Heft durchgehen",
    ("natur", "arbeit_fern", "gross"): "zu jedem Thema einen Satz aufschreiben",
    ("natur", "arbeit_nah", "klein"): "das schwierigste Thema heraussuchen",
    ("natur", "arbeit_nah", "mittel"): "das schwierigste Thema erklären",
    ("natur", "arbeit_nah", "gross"): "die Zeichnungen und Begriffe wiederholen",
    ("natur", "morgen", "klein"): "die letzten zwei Heftseiten ansehen",
    ("natur", "morgen", "mittel"): "die wichtigsten Begriffe durchgehen",
    ("natur", "morgen", "gross"): "das ganze Kapitel überfliegen",
    ("natur", "hausaufgaben", "klein"): "die Aufgabe einmal lesen",
    ("natur", "hausaufgaben", "mittel"): "die Hausaufgabe machen",
    ("natur", "hausaufgaben", "gross"): "die Hausaufgabe machen und ergänzen",
    ("natur", "gemieden", "klein"): "5 Minuten reinschauen, nichts aufschreiben",
    ("natur", "gemieden", "mittel"): "eine Seite im Heft ansehen",
    ("natur", "gemieden", "gross"): "ein Thema, das dich interessiert",
    ("natur", "normal", "klein"): "die Heftseite von heute ansehen",
    ("natur", "normal", "mittel"): "die Begriffe von heute erklären",
    ("natur", "normal", "gross"): "das Thema von heute zusammenfassen",

    # ---- Gesellschaft ----------------------------------------------------
    ("gesell", "arbeit_fern", "klein"): "herausfinden, was in der Arbeit drankommt",
    ("gesell", "arbeit_fern", "mittel"): "die Überschriften im Heft durchgehen",
    ("gesell", "arbeit_fern", "gross"): "zu jedem Thema drei Stichpunkte",
    ("gesell", "arbeit_nah", "klein"): "das schwierigste Thema heraussuchen",
    ("gesell", "arbeit_nah", "mittel"): "das schwierigste Thema erzählen",
    ("gesell", "arbeit_nah", "gross"): "die Zeitleiste oder Übersicht wiederholen",
    ("gesell", "morgen", "klein"): "die letzten zwei Heftseiten ansehen",
    ("gesell", "morgen", "mittel"): "die wichtigsten Namen und Jahre durchgehen",
    ("gesell", "morgen", "gross"): "das ganze Thema überfliegen",
    ("gesell", "hausaufgaben", "klein"): "die Aufgabe einmal lesen",
    ("gesell", "hausaufgaben", "mittel"): "die Hausaufgabe machen",
    ("gesell", "hausaufgaben", "gross"): "die Hausaufgabe machen und ergänzen",
    ("gesell", "gemieden", "klein"): "5 Minuten reinschauen, nichts aufschreiben",
    ("gesell", "gemieden", "mittel"): "eine Seite im Heft ansehen",
    ("gesell", "gemieden", "gross"): "ein Thema, das dich interessiert",
    ("gesell", "normal", "klein"): "die Heftseite von heute ansehen",
    ("gesell", "normal", "mittel"): "das Thema von heute erzählen",
    ("gesell", "normal", "gross"): "das Thema von heute zusammenfassen",
}


# --------------------------------------------------------------------------
# Einstiegshandlungen
# --------------------------------------------------------------------------
# Regeln (aus dem Konzept):
#   unter 2 Minuten * keine Wahl * koerperlich und konkret * keine Leistung
# --------------------------------------------------------------------------

_EINSTIEG_MIT_ANKER = {
    "mathe": "Schlag {fach} bei „{anker}“ auf und lies die erste Aufgabe laut vor.",
    "sprache": "Schlag {fach} bei „{anker}“ auf und lies die ersten drei Wörter laut vor.",
    "natur": "Schlag {fach} bei „{anker}“ auf und lies die Überschrift laut vor.",
    "gesell": "Schlag {fach} bei „{anker}“ auf und lies die Überschrift laut vor.",
}

_EINSTIEG_OHNE_ANKER = {
    "mathe": "Nimm das {fach}-Heft raus und schlag die letzte beschriebene Seite auf.",
    "sprache": "Nimm das {fach}-Heft raus und lies die letzten drei Wörter laut vor.",
    "natur": "Nimm das {fach}-Heft raus und schlag die letzte beschriebene Seite auf.",
    "gesell": "Nimm das {fach}-Heft raus und schlag die letzte beschriebene Seite auf.",
}

# Ein gemiedenes Fach bekommt einen Einstieg, der Leistung ausdruecklich
# verbietet. Das senkt die Schwelle eines angstbesetzten Fachs auf fast null.
_EINSTIEG_GEMIEDEN = ("Schlag {fach} irgendwo auf und schau 30 Sekunden hin. "
                      "Du sollst nichts machen.")


def einstieg(fach: str, anlass: str = "normal", anker: str | None = None) -> str:
    """Die Handlung unter zwei Minuten."""
    g = gruppe(fach)
    if anlass == "gemieden":
        return _EINSTIEG_GEMIEDEN.format(fach=fach)
    anker = (anker or "").strip()
    if anker:
        return _EINSTIEG_MIT_ANKER[g].format(fach=fach, anker=anker)
    return _EINSTIEG_OHNE_ANKER[g].format(fach=fach)


def titel(fach: str, anlass: str = "normal", groesse: str = "klein",
          klasse: int = 6) -> str:
    """Was im Angebot steht."""
    g = gruppe(fach)
    anlass = anlass if anlass in ANLAESSE else "normal"
    groesse = groesse if groesse in GROESSEN else "klein"
    text = _TITEL.get((g, anlass, groesse))
    if text is None:                       # pragma: no cover - Sicherheitsnetz
        text = _TITEL[(g, "normal", "klein")]
    # Klasse 5-6 bekommt mehr Struktur, 7-8 mehr Eigenverantwortung.
    if klasse <= 6 and groesse == "gross":
        text = _TITEL[(g, anlass, "mittel")]
    return text


def vorschlag(fach: str, anlass: str = "normal", groesse: str = "klein",
              klasse: int = 6, anker: str | None = None) -> dict:
    """Ein vollstaendiger Schritt: Titel, Einstieg, Minuten."""
    return {
        "fach": fach,
        "titel": titel(fach, anlass, groesse, klasse),
        "einstieg": einstieg(fach, anlass, anker),
        "groesse": groesse,
        "anlass": anlass,
        "minuten": MINUTEN[groesse],
    }


# --------------------------------------------------------------------------
# Kennenlernfragen — eine pro Zyklus, ueberspringbar, rotierend
# --------------------------------------------------------------------------

FRAGEN = [
    {"schluessel": "ort", "symbol": "🍳",
     "frage": "Wo lernst du am liebsten?",
     "antworten": ["am Schreibtisch", "in der Küche", "auf dem Bett", "woanders"],
     "satz": "Du lernst am liebsten {wert}."},
    {"schluessel": "zeit_tag", "symbol": "📅",
     "frage": "An welchem Tag hast du am meisten Zeit?",
     "antworten": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag",
                   "am Wochenende"],
     "satz": "Am meisten Zeit hast du {wert}."},
    {"schluessel": "anfangen", "symbol": "🚀",
     "frage": "Was hilft dir, wenn du nicht anfangen kannst?",
     "antworten": ["ganz kurz anfangen", "jemand sitzt dabei", "Musik",
                   "erst was essen", "weiß nicht"],
     "satz": "Beim Anfangen hilft dir: {wert}."},
    {"schluessel": "nervt", "symbol": "😤",
     "frage": "Welches Fach nervt dich gerade am meisten?",
     "antworten": [],          # wird aus den Faechern des Kindes gefuellt
     "satz": "Gerade nervt dich {wert} am meisten."},
    {"schluessel": "fertig", "symbol": "🕕",
     "frage": "Wann bist du meistens mit Hausaufgaben fertig?",
     "antworten": ["vor dem Abendessen", "nach dem Abendessen", "sehr spät",
                   "mal so, mal so"],
     "satz": "Mit Hausaufgaben bist du meistens {wert} fertig."},
    {"schluessel": "nachmittag", "symbol": "🧸",
     "frage": "Was machst du nach der Schule am liebsten?",
     "antworten": [],          # Freitext
     "satz": "Nach der Schule machst du am liebsten {wert}."},
]

# Tagesanker fuer „wann faengst du an?" — die App misst nichts, sie fragt nur.
TAGESANKER = ["wenn ich heimkomme", "nach dem Essen", "vor dem Training",
              "nach dem Zocken", "am Abend"]
