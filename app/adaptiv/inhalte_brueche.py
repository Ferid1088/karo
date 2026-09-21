"""Inhalt der Pilotlektion „ungleichnamige Brüche addieren“.

Umsetzung von 02_LESSON_BRUECHE.md. Diese Datei ist das Autorenwerkzeug im
Sinn von 01_ARCHITECTURE.md §11: der Inhalt entsteht hier einmal, wird geprüft
und in den Katalog geschrieben. Zur Laufzeit wird nur noch nachgeschlagen —
kein Modellaufruf, kein Warten, keine Überraschung.

`saeen()` ist absichtlich idempotent: es darf bei jedem Start laufen.
"""

from __future__ import annotations

from . import inhalt_store, schemas, store
from .katalog import fehlertyp_lernen

FACH = "mathematik"
THEMA = "brueche"
KONZEPT = "ungleichnamig-addieren"
KLASSE = 6

# Zielfehlvorstellung und ihre Nachbarn. Mehrere Fehlertypen sind der Punkt:
# dasselbe Thema, verschiedene Ursachen, verschiedene Erklärungen (A4).
FEHLERTYPEN = (
    {
        "key": "zaehler-und-nenner-addiert",
        "label": "Zähler und Nenner getrennt addiert",
        "beschreibung": "1/2 + 1/3 wird zu 2/5 — oben und unten einzeln addiert.",
        "antworten": ("2/5", "2 / 5", "2:5"),
        "schwierigkeit": 2,
        # Was dieser Fehler bei den Übungsaufgaben ergibt (1+1)/(2+4) bzw.
        # (2+1)/(3+6) — nur so erkennt Karo DIESELBE Fehlvorstellung wieder.
        "fehler_gefuehrt": "2/6",
        "fehler_selbststaendig": "3/9",
    },
    {
        "key": "zaehler-addiert-nenner-behalten",
        "label": "Zähler addiert, einen Nenner einfach übernommen",
        "beschreibung": "1/2 + 1/3 wird zu 2/3 — der größere Nenner bleibt stehen.",
        "antworten": ("2/3",),
        "schwierigkeit": 2,
        "fehler_gefuehrt": "2/4",
        "fehler_selbststaendig": "3/6",
    },
    {
        "key": "nenner-multipliziert-zaehler-addiert",
        "label": "Nenner multipliziert, Zähler addiert",
        "beschreibung": "1/2 + 1/3 wird zu 2/6 — der gemeinsame Nenner stimmt, "
                        "aber die Zähler wurden nicht miterweitert.",
        "antworten": ("2/6", "1/3"),
        "schwierigkeit": 1,
        "fehler_gefuehrt": "2/8",
        "fehler_selbststaendig": "3/18",
    },
)

# §4: genau ein Konzept, ein Bild, eine Aufgabe. Der Haken spiegelt den Fehler,
# die Erkenntnis kommt VOR der Regel, und „bleibt_gleich“ trägt die Didaktik.
ERKLAERUNGEN = {
    "zaehler-und-nenner-addiert": {
        "haken": "Du hattest ein halbes Stück Pizza und bekommst noch ein "
                 "Drittel dazu.",
        "erkenntnis": "Dein Ergebnis wäre kleiner als das halbe Stück, mit dem "
                      "du angefangen hast — obwohl etwas dazugekommen ist.",
        "regel": "Teile beide Ganzen zuerst in gleich große Stücke, dann zähle "
                 "die Stücke zusammen.",
        "bild": {
            "zeigt": "Zwei gleich breite Streifen: einer in Halbe geteilt, "
                     "einer in Drittel.",
            "bewegt": "Beide Streifen werden in Sechstel weitergeschnitten.",
            "bleibt_gleich": "Die Menge bleibt gleich, nur die Anzahl der "
                             "Stücke wird größer.",
        },
        "aufgabe": {"frage": "1/2 + 1/4 = ?", "loesung": "3/4",
                    "tipp": "Wie viele Viertel sind eine Hälfte?"},
    },
    "zaehler-addiert-nenner-behalten": {
        "haken": "Du hast die oberen Zahlen zusammengezählt und unten eine "
                 "Zahl stehen lassen.",
        "erkenntnis": "Die stehen gebliebene Zahl gehört nur zu einem der "
                      "beiden Brüche — der andere hatte andere Stücke.",
        "regel": "Erst beide Brüche auf dieselbe Stückgröße bringen, dann die "
                 "Zähler addieren.",
        "bild": {
            "zeigt": "Ein Streifen in Halbe, einer in Drittel, gleich breit.",
            "bewegt": "Der Halbe-Streifen wird in Sechstel nachgeschnitten.",
            "bleibt_gleich": "Die Hälfte bleibt gleich groß, sie heißt nur "
                             "jetzt drei Sechstel.",
        },
        "aufgabe": {"frage": "1/2 + 1/4 = ?", "loesung": "3/4",
                    "tipp": "Passt ein Viertel zweimal in eine Hälfte?"},
    },
    "nenner-multipliziert-zaehler-addiert": {
        "haken": "Du hast unten schon die richtige Stückgröße gefunden.",
        "erkenntnis": "Beim Umrechnen werden aber auch die oberen Zahlen "
                      "größer — aus einem Halben wird nicht ein Sechstel.",
        "regel": "Wenn du die Stücke kleiner schneidest, hast du entsprechend "
                 "mehr davon: rechne den Zähler mit um.",
        "bild": {
            "zeigt": "Ein Halbe-Streifen über einem Sechstel-Streifen.",
            "bewegt": "Die Hälfte wird in drei Sechstel zerschnitten.",
            "bleibt_gleich": "Es ist dieselbe Menge, sie besteht nur aus drei "
                             "kleineren Stücken.",
        },
        "aufgabe": {"frage": "1/2 + 1/4 = ?", "loesung": "3/4",
                    "tipp": "Schreib die Hälfte zuerst als Viertel."},
    },
}

#: §3: Auswahl plus Parameter — mehr darf ein Modell hier nie liefern.
BILD_REGEL = {"component": "FractionStrip",
              "parameters": {"a": [1, 2], "b": [1, 3], "gemeinsam": 6},
              "animation": "cut_then_slide"}

#: B1: Was in der Adaptation gezeigt wird, MUSS eine andere Komponente sein.
#: Denselben Streifen noch einmal zu zeigen wiederholt genau das, was eben
#: nicht geholfen hat.
BILD_ADAPTATION = {"component": "NumberLine",
                   "parameters": {"schritte": 4, "marken": [[2, 4], [1, 4]],
                                  "bis": [3, 4]},
                   "animation": "none"}

# 02 §3: das vorgerechnete Beispiel MUSS andere Zahlen haben als die geführte
# Aufgabe, sonst schreibt das Kind nur ab (B1).
BEISPIEL = {
    "frage": "1/3 + 1/6 = ?",
    "loesung": "1/2",
    "schritte": [
        {"text": "Schritt 1 — gemeinsamen Nenner finden: 3 und 6 passen beide "
                 "in 6.", "bild": None},
        {"text": "Schritt 2 — beide Brüche auf Sechstel bringen: 1/3 sind 2/6.",
         "bild": [2, 6]},
        {"text": "1/6 bleibt 1/6.", "bild": [1, 6]},
        {"text": "Schritt 3 — jetzt sind die Stücke gleich groß, also zählst "
                 "du die Zähler zusammen: 2/6 + 1/6 = 3/6.", "bild": [3, 6]},
        {"text": "3 von 6 Stücken ist genau die Hälfte.", "bild": [3, 6]},
    ],
    "visualisierung": {"component": "FractionStrip",
                       "parameters": {"a": [1, 3], "b": [1, 6], "gemeinsam": 6},
                       "animation": "cut_then_slide"},
}

GEFUEHRT = {
    "frage": "1/2 + 1/4 = ?",
    "loesung": "3/4",
    "tipps": [
        "Schau zuerst auf die Größe der Stücke.",
        "Kannst du Halbe und Viertel direkt zusammenzählen?",
        "Wie viele Viertel sind eine Hälfte?",
        "1/2 = 2/4 — also: 2/4 + 1/4 = 3/4.",
    ],
    # B1: die geführte Aufgabe zeigt ihre eigenen Brüche von Anfang an.
    "visualisierung": {"component": "FractionStrip",
                       "parameters": {"a": [1, 2], "b": [1, 4], "gemeinsam": 4},
                       "animation": "none"},
}

# HOOK: das Kind sagt ZUERST voraus, wie sich sein eigenes Ergebnis zu 1/2
# verhält, und sieht danach, dass die Voraussage nicht aufgehen kann. Die
# Einsicht entsteht damit im Kind, statt ihm mitgeteilt zu werden (§19:
# „The child discovers the contradiction before receiving the rule“).
VORHERSAGE = {
    "frage": "Bevor wir rechnen: Du hattest schon 1/2 und bekommst noch 1/3 "
             "dazu. Muss das Ergebnis größer oder kleiner sein als 1/2?",
    "optionen": [["groesser", "Größer als 1/2"], ["kleiner", "Kleiner als 1/2"],
                 ["gleich", "Genau 1/2"]],
    "loesung": "groesser",
    "aufloesung": "Genau — wer etwas dazubekommt, hat danach mehr. Dein "
                  "Ergebnis war aber kleiner als 1/2. Da stimmt also etwas "
                  "noch nicht.",
    "visualisierung": {"component": "FractionStrip",
                       "parameters": {"a": [1, 2], "b": [1, 3]},
                       "animation": "none"},
}

# Transfer: kein Rechnen, sondern dieselbe Einsicht an einer anderen Struktur
# — deshalb gehört er ans Ende der selbstständigen Phase und nicht in den HOOK.
TRANSFER = {
    "frage": "Ohne zu rechnen: Was ist größer?",
    "optionen": [["A", "A: 1/2"], ["B", "B: 1/2 + 1/5"]],
    "loesung": "B",
    "aufloesung": "Richtig — zu 1/2 kommt etwas dazu, also muss B größer sein. "
                  "Das gilt, egal welche Zahlen unten stehen.",
}

# B1: die selbstständige Aufgabe zeigt bewusst KEIN Bild — sie prüft, ob es
# auch ohne geht. 02 §1 nennt das ausdrücklich eine Hypothese, keine Invariante.
SELBSTSTAENDIG = {"frage": "2/3 + 1/6 = ?", "loesung": "5/6",
                  "tipps": ["Mach zuerst beide Stückgrößen gleich."]}

ERSTKONTAKT = {
    "anker": "Stell dir vor: Eine Pizza soll gerecht auf zwei Personen "
             "verteilt werden. Wie viel bekommt jede Person?",
    "erste_aufgabe": {
        "frage": "1/2 + 1/3 = ?",
        "loesung": "5/6",
        "hinweis": "Probier es einmal ohne Erklärung.",
        # Eine richtige Antwort ist keine Beherrschung (A8) — wer die Diagnose
        # löst, bekommt eine zweite Aufgabe, bevor die Lektion endet.
        "bestaetigung": {"frage": "2/3 + 1/6 = ?", "loesung": "5/6"},
    },
    "benennung": "Die Zahl unten nennt man den Nenner, die Zahl oben den "
                 "Zähler. Haben beide Brüche unten dieselbe Zahl, heißt sie "
                 "der gemeinsame Nenner.",
}

# 02 §5: andere Worte als der Bildschirm, immer mit Bildern, auf Übungsschirmen
# ohne die Lösung. Bilder sind [Beschriftung, gefüllt, gesamt].
ERKLAER_MEHR = {
    "HOOK": {
        "text": "Eine ganze Pizza wird in zwei gleich große Stücke "
                "geschnitten — ein Stück davon ist 1/2. Wird dieselbe Pizza in "
                "drei Stücke geschnitten, ist ein Stück davon 1/3 und damit "
                "kleiner. Beide Streifen unten stehen für dieselbe ganze Pizza.",
        "bilder": [["Eine ganze Pizza", 1, 1], ["Die Hälfte davon", 1, 2],
                   ["Ein Drittel davon", 1, 3]],
    },
    "RULE": {
        "text": "Stell dir vor, beide Streifen sind gleich große Tafeln "
                "Schokolade. Wenn eine Tafel in 2 Stücke und die andere in 3 "
                "Stücke geteilt ist, sind die einzelnen Stücke nicht gleich "
                "groß. Erst wenn beide Tafeln in gleich große Stücke geteilt "
                "sind, können wir zählen, wie viele solcher Stücke wir "
                "zusammen haben.",
        "bilder": [["Eine Hälfte", 1, 2], ["Ein Drittel", 1, 3],
                   ["Drei Sechstel", 3, 6], ["Zwei Sechstel", 2, 6]],
    },
    "WORKED_EXAMPLE": {
        "text": "Langsam nachgerechnet: 1/3 heißt ein Stück von drei, 1/6 ein "
                "Stück von sechs. In ein Drittel passen genau zwei Sechstel. "
                "Deshalb darf man 1/3 als 2/6 schreiben, ohne dass sich die "
                "Menge ändert. Danach haben beide dieselbe Stückgröße.",
        "bilder": [["Ein Drittel", 1, 3], ["Dasselbe als zwei Sechstel", 2, 6],
                   ["Dazu ein Sechstel", 1, 6], ["Zusammen drei Sechstel", 3, 6]],
    },
    "GUIDED_TASK": {
        "text": "In dieser Aufgabe sind die Stücke noch verschieden groß: eine "
                "Hälfte und ein Viertel. Schau im Bild nach, wie oft das "
                "kleinere Stück in das größere passt. Wenn du einen Schritt "
                "mehr Hilfe möchtest, nimm den Tipp.",
        "bilder": [["Eine Hälfte", 1, 2], ["Ein Viertel", 1, 4]],
    },
    "INDEPENDENT_TASK": {
        "text": "Diesmal ohne Bild zur Aufgabe: Überleg zuerst, in welche "
                "Stückgröße beide Brüche passen, schreib beide in dieser "
                "Größe und zähle dann die Stücke zusammen. Fehler sind hier "
                "ausdrücklich erlaubt.",
        "bilder": [["So sah eine Hälfte aus", 1, 2],
                   ["So sehen Sechstel aus", 1, 6]],
    },
    "ADAPTATION": {
        "text": "Dieselbe Aufgabe noch einmal anders gezeigt. Achte darauf, "
                "wie oft das kleinere Stück in das größere hineinpasst — genau "
                "so viele kleine Stücke sind das große wert.",
        "bilder": [["Ein Viertel", 1, 4], ["Zwei Viertel sind eine Hälfte", 2, 4]],
    },
}

# 02 §6
FAQ = (
    ("Was ist der Zähler, was ist der Nenner?",
     "Die Zahl unten sagt, in wie viele gleich große Stücke das Ganze geteilt "
     "wurde. Die Zahl oben sagt, wie viele von diesen Stücken wir haben.",
     [["Ein Stück von vier: 1/4", 1, 4], ["Drei Stücke von vier: 3/4", 3, 4]]),
    ("Was heißt „gemeinsamer Nenner“?",
     "Beide Brüche werden so dargestellt, dass ihre Stücke gleich groß sind. "
     "Dann steht unten bei beiden Brüchen dieselbe Zahl. Diese gemeinsame Zahl "
     "nennen wir den gemeinsamen Nenner.",
     [["Eine Hälfte als Sechstel", 3, 6], ["Ein Drittel als Sechstel", 2, 6]]),
    ("Wie tippe ich meine Antwort?",
     "Schreib den Bruch als Zahl/Zahl, zum Beispiel 3/4. Kommt eine ganze Zahl "
     "heraus, reicht auch einfach 1.", []),
    ("Ich weiß gerade nicht, was ich tun soll.",
     "Schau dir zuerst die beiden Brüche an. Deine Aufgabe ist es jetzt, eine "
     "Antwort einzugeben. Wenn du einen kleinen Hinweis möchtest, nutze den "
     "Tipp.", []),
)


def saeen() -> int:
    """Schreibt die Lektion in den Katalog. Mehrfach aufrufbar.

    Gibt die Konzept-Id zurück. Alles wird als geprüft eingetragen: der Inhalt
    ist von Menschen geschrieben, nicht von einem Modell erzeugt (§11).
    """
    konzept_id = store.konzept_sichern(
        FACH, THEMA, KONZEPT, "Brüche mit verschiedenen Nennern addieren", 5, 6)

    for fehler in FEHLERTYPEN:
        fehlertyp_id = store.fehlertyp_sichern(
            konzept_id, fehler["key"], fehler["label"], fehler["beschreibung"])
        for antwort in fehler["antworten"]:
            fehlertyp_lernen(fehlertyp_id, antwort, quelle="kuratiert")

        # Schemaprüfung vor dem Schreiben — auch bei kuratiertem Inhalt (A2).
        inhalt = schemas.pruefe_inhalt(ERKLAERUNGEN[fehler["key"]])
        bild, _ = schemas.visualisierung_oder_fallback(BILD_REGEL)
        if not store.beste_erklaerung(fehlertyp_id, KLASSE):
            alternativ, _ = schemas.visualisierung_oder_fallback(BILD_ADAPTATION)
            store.erklaerung_anlegen(
                fehlertyp_id, KLASSE, inhalt, visualisierung=bild,
                visualisierung_alternativ=alternativ,
                schwierigkeit=fehler["schwierigkeit"], geprueft=True)

        inhalt_store.aufgabe_sichern(
            fehlertyp_id, inhalt_store.BEISPIEL, BEISPIEL["frage"],
            BEISPIEL["loesung"], schritte=BEISPIEL["schritte"],
            visualisierung=BEISPIEL["visualisierung"])
        inhalt_store.aufgabe_sichern(
            fehlertyp_id, inhalt_store.GEFUEHRT, GEFUEHRT["frage"],
            GEFUEHRT["loesung"], tipps=GEFUEHRT["tipps"],
            visualisierung=GEFUEHRT["visualisierung"],
            typischer_fehler=fehler["fehler_gefuehrt"])
        inhalt_store.aufgabe_sichern(
            fehlertyp_id, inhalt_store.SELBSTSTAENDIG, SELBSTSTAENDIG["frage"],
            SELBSTSTAENDIG["loesung"], tipps=SELBSTSTAENDIG["tipps"],
            typischer_fehler=fehler["fehler_selbststaendig"])
        inhalt_store.aufgabe_sichern(
            fehlertyp_id, inhalt_store.VORHERSAGE, VORHERSAGE["frage"],
            VORHERSAGE["loesung"], antwort_art=inhalt_store.AUSWAHL,
            optionen=VORHERSAGE["optionen"], aufloesung=VORHERSAGE["aufloesung"],
            visualisierung=VORHERSAGE["visualisierung"])
        inhalt_store.aufgabe_sichern(
            fehlertyp_id, inhalt_store.TRANSFER, TRANSFER["frage"],
            TRANSFER["loesung"], antwort_art=inhalt_store.AUSWAHL,
            optionen=TRANSFER["optionen"], aufloesung=TRANSFER["aufloesung"])

    if not store.erstkontakt(konzept_id):
        store.erstkontakt_anlegen(
            konzept_id, ERSTKONTAKT["anker"], ERSTKONTAKT["erste_aufgabe"],
            ERSTKONTAKT["benennung"], geprueft=True)

    for phase, hilfe in ERKLAER_MEHR.items():
        inhalt_store.hilfe_sichern(konzept_id, inhalt_store.HILFE_PHASE, phase,
                                   hilfe["text"], hilfe["bilder"])
    for i, (frage, antwort, bilder) in enumerate(FAQ):
        inhalt_store.hilfe_sichern(konzept_id, inhalt_store.HILFE_FAQ, frage,
                                   antwort, bilder, sortierung=i)
    return konzept_id
