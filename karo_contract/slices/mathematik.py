"""Mathematik-Slice: vom Zahlraum bis 100 zum Quader-Volumen.

Level 0 ist hier nicht „Klasse 1", sondern der fachlich elementarste Punkt
der Kette: sicheres Rechnen im Zahlraum bis 100. Wer das nicht kann, kann
weder malnehmen noch Einheiten vergleichen noch Volumen bestimmen.

    MA.GEO.QUADERVOLUMEN   (Ziel, Kl. 5–6)
      ├── MA.GEO.FLAECHE_RECHTECK  (Kl. 4–5)  ── MA.ZAHLEN.EINMALEINS
      └── MA.GROESSEN.EINHEITEN    (Kl. 3–4)  ── MA.ZAHLEN.ZR100   (Level 0)
"""

from __future__ import annotations

from ._bauen import aufgabe, auswahl, choice, item, number, text

_FLAECHEN_EINHEIT_VIS = {
    "component": "AreaModel",
    "parameters": {"spalten": 4, "zeilen": 3, "markiert": 12},
    "animation": "none"}

_SCHRITTE = lambda schritte: {
    "component": "GenericStepFlow",
    "parameters": {"schritte": schritte}, "animation": "none"}

_TABELLE = lambda spalten, zeilen: {
    "component": "DataTable",
    "parameters": {"spalten": spalten, "zeilen": zeilen}, "animation": "none"}


def _hilfe(texte: dict) -> dict:
    return {phase: {"text": t} for phase, t in texte.items()}


SLICE = {
    "fach": "mathematik",
    "code": "MA",
    "name": "Mathematik",
    "blocks": [
        {
            "id": "MA.ZAHLEN",
            "title": "Zahlen und Rechnen",
            "description": "Sicherer Umgang mit Zahlen bis 100, kleines "
                           "Einmaleins und geteilte Größen.",
            "grade_min": 1, "grade_max": 4, "typical_grade": 2,
            "concepts": [
                # ------------------------------------------------ Level 0
                {
                    "id": "MA.ZAHLEN.ZR100",
                    "title": "Sicher rechnen im Zahlraum bis 100",
                    "description": "Plus und Minus bis 100 ohne Zählen an den "
                                   "Fingern — die Grundlage jeder späteren Rechnung.",
                    "first_contact_grade": 1, "target_grade": 2,
                    "prerequisites": [],
                    "levels": {
                        "below": "K1: Zahlen bis 20, Mengen vergleichen",
                        "target": "K2: Plus und Minus bis 100, Zehnerübergang",
                        "above": "K3: Einmaleins, Zahlen bis 1000"},
                    "can_do": {
                        "below": ["Zahlen bis 20 lesen und ordnen"],
                        "target": ["Aufgaben wie 47 + 35 oder 82 - 56 im Kopf "
                                   "oder schriftlich lösen"],
                        "above": ["Malaufgaben als wiederholtes Plus verstehen"]},
                    "difficulty_parameters": {
                        "zahlraum": "bis 100", "uebergang": "Zehner erlaubt",
                        "wege": "Kopfrechnen oder schriftlich"},
                    "anchor_items": [
                        item("Rechne: 48 + 37", "85", level="target", grade=2,
                             answer=number(85)),
                        item("Rechne: 93 - 58", "35", level="target", grade=2,
                             answer=number(35))],
                    "boundary_items": {
                        "below": [item("Rechne: 9 + 7", "16", level="below",
                                       grade=1, answer=number(16))],
                        "within": [item("Rechne: 64 - 29", "35", level="target",
                                        grade=2, answer=number(35))],
                        "above": [item("Rechne: 6 * 7", "42", level="above",
                                       grade=3, answer=number(42))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Zehnerübergang wird "
                             "übersehen: 48 + 37 wird zu 75 statt 85 — die "
                             "Einer bilden einen neuen Zehner.",
                             "remediation_hint": "Einer zuerst rechnen und den "
                             "neuen Zehner sichtbar aufschreiben.",
                             "diagnostic_item": item(
                                 "Rechne: 48 + 37", "85", level="target",
                                 grade=2, answer=number(85),
                                 distractors=[{"answer": "75",
                                               "misconception": "F1",
                                               "feedback": "8 + 7 sind 15 — die 1 geht zu den Zehnern."}])},
                            {"key": "F2", "description": "Beim Minusrechnen "
                             "wird die größere Ziffer genommen: 93 - 58 wird "
                             "zu 45 statt 35 — 8 - 3 statt Ergänzen oder "
                             "Entbündeln.",
                             "remediation_hint": "Vom Subtrahend zum Zehner "
                             "auffüllen statt Ziffern zu tauschen.",
                             "diagnostic_item": item(
                                 "Rechne: 93 - 58", "35", level="target",
                                 grade=2, answer=number(35),
                                 distractors=[{"answer": "45",
                                               "misconception": "F2",
                                               "feedback": "3 - 8 geht nicht — bündle einen Zehner um."}])}],
                        "diagnostic_items": [
                            item("Rechne: 26 + 17", "43", level="below",
                                 grade=2, answer=number(43)),
                            item("Rechne: 71 - 46", "25", level="target",
                                 grade=2, answer=number(25))],
                        "exit_items": [
                            item("Rechne: 59 + 34", "93", level="target",
                                 grade=2, answer=number(93)),
                            item("Rechne: 81 - 47", "34", level="target",
                                 grade=2, answer=number(34))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "zr100", "thema_key": "zahlen",
                            "label": "Rechnen bis 100",
                            "klasse_von": 1, "klasse_bis": 3,
                            "stichworte": ["rechnen bis 100", "plus und minus",
                                           "zahlraum 100", "grundrechenarten",
                                           "addieren", "subtrahieren"]},
                        "erstkontakt": {
                            "anker": "An einem Kiosk gibt es 48 Brötchen. Nach "
                                     "dem Verkauf von 37 wie viele bleiben?",
                            "benennung": "Rechnen bis 100",
                            "erste_aufgabe": {"frage": "48 - 37 = ?",
                                              "loesung": "11"}},
                        "fehlertypen": [
                            {
                                "key": "zehner_uebergang",
                                "label": "Zehnerübergang übersehen",
                                "beschreibung": "Die Einer ergeben zusammen "
                                "einen neuen Zehner, der vergessen wird.",
                                "antworten": ["75", "48+37=75"],
                                "erklaerung": {
                                    "haken": "Rechne 48 + 37. Viele sagen "
                                            "sofort 75 — und liegen 10 daneben.",
                                    "erkenntnis": "Die Einer 8 + 7 machen 15: "
                                    "das sind 1 Zehner und 5 Einer. Der neue "
                                    "Zehner gehört zu den 4 + 3 Zehnern dazu.",
                                    "regel": "Rechne Einer und Zehner "
                                    "getrennt. Machen die Einer mehr als 10, "
                                    "wandert der neue Zehner nach links.",
                                    "bild": {"zeigt": "4 Zehner + 3 Zehner "
                                             "und die Einer 8 + 7",
                                             "bewegt": "aus den 15 Einern "
                                             "wandert 1 Zehner zu den Zehnern",
                                             "bleibt_gleich": "die Gesamtzahl "
                                             "ändert sich nicht"},
                                    "aufgabe": {"frage": "56 + 28 = ?",
                                                "loesung": "84",
                                                "tipp": "Erst 6 + 8."}},
                                "visualisierung": _SCHRITTE(
                                    ["Einer rechnen: 8 + 7 = 15",
                                     "15 = 1 Zehner + 5 Einer",
                                     "Zehner rechnen: 40 + 30 + 10 = 80",
                                     "80 + 5 = 85"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Schritt", "Ergebnis"],
                                    ["8 + 7 | 15", "40 + 30 | 70",
                                     "70 + 15 | 85"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist 48 + 37?",
                                        "85",
                                        ["75", "715"],
                                        "8 + 7 = 15 ergibt 5 Einer und 1 neuen "
                                        "Zehner — ohne ihn fehlt genau 10."),
                                    "beispiel": aufgabe(
                                        "Wir rechnen 48 + 37: erst 8 + 7 = 15. "
                                        "Dann 40 + 30 = 70. Zusammen 70 + 15.",
                                        "85",
                                        schritte=["8 + 7 = 15",
                                                  "40 + 30 = 70",
                                                  "70 + 15 = 85"]),
                                    "gefuehrt": aufgabe(
                                        "36 + 47 = ?", "83",
                                        fehler="73",
                                        tipps=["Erst die Einer: 6 + 7.",
                                               "Aus den 13 wird ein Zehner und 3 Einer."],
                                        schritte=["6 + 7 = 13",
                                                  "30 + 40 + 10 = 80",
                                                  "80 + 3 = 83"]),
                                    "selbststaendig": aufgabe(
                                        "59 + 26 = ?", "85",
                                        fehler="75",
                                        tipps=["9 + 6 macht einen neuen Zehner."],
                                        schritte=["9 + 6 = 15",
                                                  "50 + 20 + 10 = 80",
                                                  "80 + 5 = 85"]),
                                    "transfer": auswahl(
                                        "Lisa rechnet 27 plus 56 und "
                                        "bekommt 73 heraus. Was hat sie "
                                        "vergessen?",
                                        "Den neuen Zehner aus den Einern",
                                        ["Die Einer komplett",
                                         "Die Zehner komplett"],
                                        "7 + 6 = 13 — der neue Zehner gehört zu "
                                        "den Zehnern: 70 + 13 = 83.")}},
                            {
                                "key": "minus_umtauschen",
                                "label": "Beim Minusrechnen Ziffern tauschen",
                                "beschreibung": "Unten größer als oben wird "
                                "einfach umgedreht statt umzubündeln.",
                                "antworten": ["45", "93-58=45"],
                                "erklaerung": {
                                    "haken": "93 - 58: Wer nur die Ziffern "
                                            "sieht, nimmt 8 - 3 = 5 — und "
                                            "rechnet falsch herum.",
                                    "erkenntnis": "3 - 8 geht nicht. Statt "
                                    "umzudrehen wandelt man einen Zehner der "
                                    "93 in 10 Einer um: 13 - 8 = 5.",
                                    "regel": "Reicht der obere Einer nicht, "
                                    "bündle einen Zehner um: aus 90 + 3 wird "
                                    "80 + 13. Zehner und Einer bleiben "
                                    "zusammen gleich viel wert.",
                                    "bild": {"zeigt": "9 Zehnerstäbe und "
                                             "3 Einer",
                                             "bewegt": "ein Zehnerstab wird "
                                             "in 10 Einer getauscht",
                                             "bleibt_gleich": "93 bleibt 93 — "
                                             "nur anders gebündelt"},
                                    "aufgabe": {"frage": "72 - 45 = ?",
                                                "loesung": "27",
                                                "tipp": "Mache aus der 72 eine 60 + 12."}},
                                "visualisierung": _SCHRITTE(
                                    ["93 = 90 + 3 — die 3 reicht nicht",
                                     "Umbündeln: 93 = 80 + 13",
                                     "Einer: 13 - 8 = 5",
                                     "Zehner: 80 - 50 = 30", "30 + 5 = 35"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Schritt", "Rechnung"],
                                    ["Umbündeln | 93 = 80 + 13",
                                     "Einer | 13 - 8 = 5",
                                     "Zehner | 80 - 50 = 30",
                                     "Zusammen | 30 + 5 = 35"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist 93 - 58?", "35",
                                        ["45", "38"],
                                        "8 - 3 umdrehen ist verboten — man "
                                        "bündelt einen Zehner um: 80 + 13 - 58."),
                                    "beispiel": aufgabe(
                                        "Wir rechnen 93 - 58: umbündeln "
                                        "93 = 80 + 13, dann 13 - 8 = 5 und "
                                        "80 - 50 = 30.",
                                        "35",
                                        schritte=["93 = 80 + 13",
                                                  "13 - 8 = 5",
                                                  "80 - 50 = 30",
                                                  "30 + 5 = 35"]),
                                    "gefuehrt": aufgabe(
                                        "61 - 36 = ?", "25",
                                        fehler="35",
                                        tipps=["1 - 6 geht nicht — bündle um.",
                                               "61 = 50 + 11."],
                                        schritte=["61 = 50 + 11",
                                                  "11 - 6 = 5",
                                                  "50 - 30 = 20",
                                                  "20 + 5 = 25"]),
                                    "selbststaendig": aufgabe(
                                        "84 - 57 = ?", "27",
                                        fehler="37",
                                        tipps=["84 = 70 + 14."],
                                        schritte=["84 = 70 + 14",
                                                  "14 - 7 = 7",
                                                  "70 - 50 = 20",
                                                  "20 + 7 = 27"]),
                                    "transfer": auswahl(
                                        "Bei 52 - 28 rechnet Ben 8 - 2 = 6. "
                                        "Was ist das eigentliche Problem?",
                                        "Er darf nicht umdrehen, er muss "
                                        "umbündeln",
                                        ["Das Ergebnis ist einfach falsch",
                                         "Er sollte erst die Zehner rechnen"],
                                        "Unten steht die größere Ziffer — "
                                        "umdrehen zählt das Falsche.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Rechne Einer und Zehner getrennt — und "
                                    "schau, ob die Einer einen neuen Zehner bilden.",
                            "RULE": "Mehr als 10 Einer heißt: ein Zehner "
                                    "wandert nach links. Bei Minus bündelst "
                                    "du umgekehrt einen Zehner in Einer um.",
                            "WORKED_EXAMPLE": "Lies jeden Schritt einzeln: "
                                    "zuerst die Bündelung, dann die Rechnung.",
                            "GUIDED_TASK": "Schreib dir den Zwischenschritt "
                                    "auf (z. B. 93 = 80 + 13), bevor du rechnest.",
                            "INDEPENDENT_TASK": "Prüfe am Ende: passt das "
                                    "Ergebnis zur Überschlagsrechnung?",
                            "ADAPTATION": "Dieselbe Rechnung, anders "
                                    "gezeigt — folge den Schritten nacheinander."}),
                        "faq": [
                            {"frage": "Warum ist 48 + 37 nicht 75?",
                             "antwort": "Die Einer 8 + 7 ergeben 15 — das "
                                        "ist ein ganzer Zehner. Er gehört zu "
                                        "den Zehnern dazu: 70 + 15 = 85."},
                            {"frage": "Darf ich bei Minus die größere Ziffer "
                                      "oben hinschreiben?",
                             "antwort": "Nein — das rechnet die falsche "
                                        "Richtung. Stattdessen bündelst du "
                                        "einen Zehner in zehn Einer um."}],
                    }},
                # -------------------------------------------- Einmaleins
                {
                    "id": "MA.ZAHLEN.EINMALEINS",
                    "title": "Kleines Einmaleins sicher",
                    "description": "Malnehmen als Abkürzung für wiederholtes "
                                   "Plusrechnen — jede Reihe zwischen 1 und 10.",
                    "first_contact_grade": 2, "target_grade": 3,
                    "prerequisites": ["MA.ZAHLEN.ZR100"],
                    "levels": {
                        "below": "K2: Plusrechnen bis 100",
                        "target": "K3: kleines Einmaleins auswendig und als "
                                  "Plusreihe verstanden",
                        "above": "K4: schriftliche Multiplikation, "
                                 "Größenbereiche"},
                    "can_do": {
                        "below": ["Reihen wie 7 + 7 + 7 rechnen"],
                        "target": ["Jede Aufgabe des kleinen Einmaleins ohne "
                                   "Nachdenken beantworten und als Reihe "
                                   "deuten können"],
                        "above": ["Zweistellige Zahlen malnehmen"]},
                    "difficulty_parameters": {
                        "faktoren": "1 bis 10", "darstellung": "Reihe, Malpunkt",
                        "zeit": "pro Aufgabe wenige Sekunden"},
                    "anchor_items": [
                        item("Rechne: 7 * 8", "56", level="target", grade=3,
                             answer=number(56)),
                        item("Rechne: 9 * 6", "54", level="target", grade=3,
                             answer=number(54))],
                    "boundary_items": {
                        "below": [item("Rechne: 4 + 4 + 4", "12", level="below",
                                       grade=2, answer=number(12))],
                        "within": [item("Rechne: 8 * 8", "64", level="target",
                                        grade=3, answer=number(64))],
                        "above": [item("Rechne: 14 * 6", "84", level="above",
                                       grade=4, answer=number(84))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Mal als Plus der "
                             "beiden Zahlen: 7 * 8 wird zu 15 — das Zeichen "
                             "wird gelesen, nicht verstanden.",
                             "remediation_hint": "7 * 8 heißt 8-mal die 7: "
                             "die Punktaufgabe als Reihe ausmalen.",
                             "diagnostic_item": item(
                                 "Was ergibt 7 * 8?", "56", level="target",
                                 grade=3, answer=number(56),
                                 distractors=[{"answer": "15",
                                               "misconception": "F1",
                                               "feedback": "7 * 8 ist nicht 7 + 8 — es sind 8 Siebener."}])},
                            {"key": "F2", "description": "Reihen verwechselt: "
                             "6 * 7 = 36 kommt aus der 6er-Reihe, nicht der "
                             "7er — die Nachbaraufgabe wird geraten.",
                             "remediation_hint": "Ankeraufgaben nutzen: "
                             "5 * 7 = 35, also 6 * 7 = 35 + 7.",
                             "diagnostic_item": item(
                                 "Rechne: 6 * 7", "42", level="target",
                                 grade=3, answer=number(42),
                                 distractors=[{"answer": "36",
                                               "misconception": "F2",
                                               "feedback": "36 ist 6 * 6 — bei 6 * 7 kommt noch eine 7 dazu."}])}],
                        "diagnostic_items": [
                            item("Schreibe 5 * 4 als Plusaufgabe.", "4+4+4+4+4=20",
                                 level="below", grade=2, answer=text("20")),
                            item("Rechne: 8 * 7", "56", level="target",
                                 grade=3, answer=number(56))],
                        "exit_items": [
                            item("Rechne: 9 * 7", "63", level="target",
                                 grade=3, answer=number(63)),
                            item("Rechne: 8 * 6", "48", level="target",
                                 grade=3, answer=number(48))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "einmaleins", "thema_key": "zahlen",
                            "label": "Kleines Einmaleins",
                            "klasse_von": 2, "klasse_bis": 4,
                            "stichworte": ["einmaleins", "malnehmen",
                                           "multiplizieren", "mal rechnen",
                                           "malaufgaben"]},
                        "erstkontakt": {
                            "anker": "In einer Packung liegen 6 Reihen mit je "
                                     "8 Keksen. Wie viele Kekse sind es?",
                            "benennung": "Malnehmen",
                            "erste_aufgabe": {"frage": "6 * 8 = ?",
                                              "loesung": "48"}},
                        "fehlertypen": [
                            {
                                "key": "mal_als_plus",
                                "label": "Mal wird zu Plus",
                                "beschreibung": "Das Malzeichen wird wie ein "
                                "Plus gelesen: 7 * 8 ergibt 15.",
                                "antworten": ["15", "7+8"],
                                "erklaerung": {
                                    "haken": "7 * 8: Wer schnell rechnet, "
                                            "addiert 7 + 8 = 15. Das Malzeichen "
                                            "meint aber etwas ganz anderes.",
                                    "erkenntnis": "7 * 8 steht für eine Reihe: "
                                    "8-mal die 7. Das ist viel mehr als 7 + 8 — "
                                    "es sind 7 + 7 + 7 + 7 + 7 + 7 + 7 + 7.",
                                    "regel": "A * B heißt: B-mal die Zahl A "
                                    "aneinanderlegen (oder umgekehrt). Mal "
                                    "ist die Abkürzung für immer dasselbe Plus.",
                                    "bild": {"zeigt": "8 Reihen mit je 7 Punkten",
                                             "bewegt": "die Reihen werden "
                                             "nebeneinander geschoben",
                                             "bleibt_gleich": "die Gesamtzahl "
                                             "der Punkte ändert sich nicht"},
                                    "aufgabe": {"frage": "5 * 6 = ?",
                                                "loesung": "30",
                                                "tipp": "Schreibe es als Plusreihe."}},
                                "visualisierung": _FLAECHEN_EINHEIT_VIS,
                                "visualisierung_alternativ": _SCHRITTE(
                                    ["7 * 8 heißt: 8 Reihen mit je 7",
                                     "7 + 7 = 14, + 7 = 21, …",
                                     "nach 8 Siebenern: 56"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was bedeutet 7 * 8?", "8-mal die 7",
                                        ["7 + 8", "7 Reihen mit 8"],
                                        "Mal ist eine Abkürzung: 8 Reihen "
                                        "mit je 7 — nicht die Summe der beiden Zahlen."),
                                    "beispiel": aufgabe(
                                        "4 * 5 als Reihe: 5 + 5 + 5 + 5. "
                                        "Vier Fünfer machen 20.",
                                        "20",
                                        schritte=["4 * 5 = 5 + 5 + 5 + 5",
                                                  "5 + 5 = 10, 10 + 5 = 15, 15 + 5 = 20"]),
                                    "gefuehrt": aufgabe(
                                        "6 * 4 = ?", "24",
                                        fehler="10",
                                        tipps=["Schreibe sechs Vieren auf.",
                                               "Oder: 3 * 4 = 12, verdoppeln."],
                                        schritte=["4 + 4 + 4 + 4 + 4 + 4",
                                                  "= 24"]),
                                    "selbststaendig": aufgabe(
                                        "9 * 5 = ?", "45",
                                        fehler="14",
                                        tipps=["Neun Fünfer — oder 10 * 5 minus 5."],
                                        schritte=["10 * 5 = 50",
                                                  "50 - 5 = 45"]),
                                    "transfer": auswahl(
                                        "Welche Aufgabe passt zum Bild: "
                                        "4 Reihen mit je 6 Kugeln?",
                                        "4 * 6", ["4 + 6", "6 * 6"],
                                        "Vier gleiche Reihen — mal, nicht plus.")}},
                            {
                                "key": "reihe_verwechselt",
                                "label": "Reihen verwechselt",
                                "beschreibung": "Die richtige Technik, aber "
                                "das Ergebnis der Nachbaraufgabe: 6 * 7 = 36.",
                                "antworten": ["36", "6*7=36", "49"],
                                "erklaerung": {
                                    "haken": "6 * 7 = 36? Fast — 36 gehört "
                                            "zur Nachbaraufgabe 6 * 6.",
                                    "erkenntnis": "Reihen wachsen immer "
                                    "um denselben Schritt: nach 6 * 6 = 36 "
                                    "kommt bei 6 * 7 noch eine 6 dazu — 42.",
                                    "regel": "Such die Aufgabe aus einer "
                                    "Ankeraufgabe: 5 * 7 = 35, also "
                                    "6 * 7 = 35 + 7 = 42.",
                                    "bild": {"zeigt": "die 7er-Reihe "
                                             "35 - 42 - 49",
                                             "bewegt": "der Sprung von 35 "
                                             "nach 42 ist genau eine 7",
                                             "bleibt_gleich": "der Abstand "
                                             "bleibt in der Reihe gleich"},
                                    "aufgabe": {"frage": "8 * 7 = ?",
                                                "loesung": "56",
                                                "tipp": "Von 7 * 7 = 49 aus weiter."}},
                                "visualisierung": _SCHRITTE(
                                    ["Anker: 5 * 7 = 35",
                                     "noch eine 7: 35 + 7 = 42",
                                     "also 6 * 7 = 42"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Aufgabe", "Ergebnis"],
                                    ["5 * 7 | 35", "6 * 7 | 42",
                                     "7 * 7 | 49", "8 * 7 | 56"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist 6 * 7?", "42",
                                        ["36", "49"],
                                        "5 * 7 = 35, dann noch eine 7 dazu — "
                                        "36 wäre schon 6 * 6."),
                                    "beispiel": aufgabe(
                                        "8 * 6 gesucht. Anker: 4 * 6 = 24, "
                                        "verdoppeln gibt 8 * 6.",
                                        "48",
                                        schritte=["4 * 6 = 24",
                                                  "8 * 6 = 24 + 24 = 48"]),
                                    "gefuehrt": aufgabe(
                                        "7 * 9 = ?", "63",
                                        fehler="72",
                                        tipps=["7 * 10 = 70 — und dann?",
                                               "72 wäre 8 * 9."],
                                        schritte=["7 * 10 = 70",
                                                  "70 - 7 = 63"]),
                                    "selbststaendig": aufgabe(
                                        "9 * 8 = ?", "72",
                                        fehler="64",
                                        tipps=["Von 10 * 8 zurück."],
                                        schritte=["10 * 8 = 80",
                                                  "80 - 8 = 72"]),
                                    "transfer": auswahl(
                                        "Mia sagt: sieben mal acht ist 54. "
                                        "Aus welcher Richtung hätte sie "
                                        "das prüfen können?",
                                        "7 * 7 = 49, also muss es größer "
                                        "als 49 sein",
                                        ["54 klingt richtig",
                                         "7 + 8 = 15, also stimmt es"],
                                        "Reihen wachsen schrittweise — ein "
                                        "Anker macht den Fehler sichtbar.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Mal ist eine Abkürzung: 6 * 8 heißt "
                                    "sechs Achter (oder acht Sechser).",
                            "RULE": "Schreibe die Malaufgabe einmal als "
                                    "Plusreihe — dann siehst du, was sie "
                                    "wirklich bedeutet.",
                            "WORKED_EXAMPLE": "Der Trick: erst eine leichte "
                                    "Aufgabe finden, dann schrittweise weiter.",
                            "GUIDED_TASK": "Nutze eine Ankeraufgabe "
                                    "(5 * 7 = 35 oder 10 * 7 = 70) und rechne weiter.",
                            "INDEPENDENT_TASK": "Prüfe: liegt das Ergebnis "
                                    "zwischen zwei benachbarten Reihenwerten?",
                            "ADAPTATION": "Andere Sicht: die Reihe als "
                                    "Tabelle — wo sitzt deine Aufgabe?"}),
                        "faq": [
                            {"frage": "Warum ist 7 * 8 nicht 15?",
                             "antwort": "7 + 8 ist 15. 7 * 8 meint acht "
                                        "Siebener aneinander — das sind 56."},
                            {"frage": "Wie merke ich mir schwierige "
                                      "Malaufgaben?",
                             "antwort": "Über Ankeraufgaben: 7 * 9 ist "
                                        "7 * 10 minus 7 — also 70 - 7 = 63."}],
                    }},
                # ------------------------------------------------ ZR1000
                {
                    "id": "MA.ZAHLEN.ZR1000",
                    "title": "Sicher rechnen im Zahlraum bis 1000",
                    "description": "Plus und Minus bis 1000 — der "
                                   "Hunderterübergang als Erweiterung des "
                                   "Zehnerübergangs.",
                    "first_contact_grade": 2, "target_grade": 3,
                    "prerequisites": ["MA.ZAHLEN.ZR100"],
                    "levels": {
                        "below": "K2: Plus und Minus bis 100",
                        "target": "K3: Hunderterübergänge, dreistellige "
                                  "Zahlen zerlegen",
                        "above": "K4: Zahlen bis 1 Million, schriftliche "
                                 "Verfahren"},
                    "can_do": {
                        "below": ["Plus- und Minusaufgaben bis 100 sicher "
                                  "rechnen"],
                        "target": ["Aufgaben wie 385 + 247 oder 720 - 365 "
                                   "mit Hunderterübergang lösen"],
                        "above": ["Schriftlich addieren und subtrahieren"]},
                    "difficulty_parameters": {
                        "zahlraum": "bis 1000",
                        "uebergang": "Hunderter und Zehner erlaubt",
                        "wege": "schrittweise oder stellenweise"},
                    "anchor_items": [
                        item("Rechne: 385 + 247", "632", level="target",
                             grade=3, answer=number(632)),
                        item("Rechne: 720 - 365", "355", level="target",
                             grade=3, answer=number(355))],
                    "boundary_items": {
                        "below": [item("Rechne: 96 + 28", "124",
                                       level="below", grade=2,
                                       answer=number(124))],
                        "within": [item("Rechne: 456 + 178", "634",
                                        level="target", grade=3,
                                        answer=number(634))],
                        "above": [item("Rechne: 1234 + 567", "1801",
                                       level="above", grade=4,
                                       answer=number(1801))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Der neue Hunderter "
                             "wird übersehen: 385 + 247 wird zu 522 — die "
                             "Zehner ergeben 13 Zehner, also 1 Hunderter und "
                             "3 Zehner.",
                             "remediation_hint": "Zehner und Hunderter "
                             "getrennt zusammenzählen und den neuen "
                             "Hunderter sichtbar markieren.",
                             "diagnostic_item": item(
                                 "Rechne: 385 + 247", "632", level="target",
                                 grade=3, answer=number(632),
                                 distractors=[{"answer": "522",
                                               "misconception": "F1",
                                               "feedback": "8 + 4 Zehner plus der neue Zehner sind 13 Zehner — das ist ein ganzer Hunderter."}])},
                            {"key": "F2", "description": "Stellen werden "
                             "vermischt: die Zehner der einen Zahl werden "
                             "zu den Hundertern der anderen gezählt.",
                             "remediation_hint": "Zahlen untereinander "
                             "schreiben, Stelle über Stelle.",
                             "diagnostic_item": item(
                                 "Rechne: 456 + 178", "634", level="target",
                                 grade=3, answer=number(634),
                                 distractors=[{"answer": "1134",
                                               "misconception": "F2",
                                               "feedback": "Die 7 der 178 sind Zehner, keine Hunderter — stell sie unter die 5."}])}],
                        "diagnostic_items": [
                            item("Rechne: 76 + 38", "114", level="below",
                                 grade=3, answer=number(114)),
                            item("Rechne: 298 + 305", "603", level="target",
                                 grade=3, answer=number(603))],
                        "exit_items": [
                            item("Rechne: 467 + 289", "756", level="target",
                                 grade=3, answer=number(756)),
                            item("Rechne: 810 - 275", "535", level="target",
                                 grade=3, answer=number(535))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "zr1000", "thema_key": "zahlen",
                            "label": "Rechnen bis 1000",
                            "klasse_von": 2, "klasse_bis": 4,
                            "stichworte": ["zahlraum 1000", "hunderter",
                                           "dreistellig", "stellenwert",
                                           "plus bis 1000", "minus bis 1000"]},
                        "erstkontakt": {
                            "anker": "In der Schulbücherei stehen 385 "
                                     "Bücher. 247 kommen dazu. Wie viele "
                                     "sind es jetzt?",
                            "benennung": "Rechnen bis 1000",
                            "erste_aufgabe": {"frage": "385 + 247 = ?",
                                              "loesung": "632"}},
                        "fehlertypen": [
                            {
                                "key": "hunderter_uebergang",
                                "label": "Neuer Hunderter übersehen",
                                "beschreibung": "Die Zehner ergeben mehr "
                                "als 10 — daraus wird ein ganzer Hunderter, "
                                "der vergessen wird.",
                                "antworten": ["522", "385+247=522"],
                                "erklaerung": {
                                    "haken": "Rechne 385 + 247. Wer schnell "
                                            "rechnet, sagt oft 522 — und "
                                            "verliert einen ganzen Hunderter.",
                                    "erkenntnis": "Die Zehner 8 + 4 machen "
                                    "12 Zehner, plus den neuen Zehner aus "
                                    "den Einern sind es 13 Zehner. 13 Zehner "
                                    "sind 1 Hunderter und 3 Zehner.",
                                    "regel": "Rechne Einer, Zehner und "
                                    "Hunderter getrennt. Ergibt eine Stelle "
                                    "mehr als 10, wandert die neue "
                                    "Bündelung eine Stelle nach links.",
                                    "bild": {"zeigt": "3 Hunderter, 12 "
                                             "Zehner und 12 Einer",
                                             "bewegt": "aus 12 Einern wird "
                                             "1 Zehner, aus 13 Zehnern "
                                             "1 Hunderter",
                                             "bleibt_gleich": "die "
                                             "Gesamtzahl ändert sich nicht"},
                                    "aufgabe": {"frage": "276 + 148 = ?",
                                                "loesung": "424",
                                                "tipp": "Zähle die Zehner: 7 + 4 + 1."}},
                                "visualisierung": _SCHRITTE(
                                    ["Einer: 5 + 7 = 12 → 1 Zehner + 2 Einer",
                                     "Zehner: 8 + 4 + 1 = 13 Zehner",
                                     "13 Zehner = 1 Hunderter + 3 Zehner",
                                     "Hunderter: 3 + 2 + 1 = 6",
                                     "Ergebnis: 632"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Stelle", "Rechnung", "Neue Stelle"],
                                    ["Einer | 5 + 7 = 12 | 1 Zehner wandert",
                                     "Zehner | 8 + 4 + 1 = 13 | 1 Hunderter wandert",
                                     "Hunderter | 3 + 2 + 1 = 6 | bleibt"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist 385 + 247?",
                                        "632",
                                        ["522", "612"],
                                        "Die Zehner werden zu 13 Zehnern — "
                                        "ein ganzer Hunderter mehr."),
                                    "beispiel": aufgabe(
                                        "Wir rechnen 385 + 247: Einer "
                                        "5 + 7 = 12, Zehner 8 + 4 + 1 = 13, "
                                        "Hunderter 3 + 2 + 1 = 6.",
                                        "632",
                                        schritte=["5 + 7 = 12",
                                                  "8 + 4 + 1 = 13 Zehner",
                                                  "3 + 2 + 1 = 6 Hunderter",
                                                  "632"]),
                                    "gefuehrt": aufgabe(
                                        "469 + 273 = ?", "742",
                                        fehler="632",
                                        tipps=["Einer zuerst: 9 + 3 = 12.",
                                               "Zehner: 6 + 7 + 1 — das ist ein neuer Hunderter."],
                                        schritte=["9 + 3 = 12",
                                                  "6 + 7 + 1 = 14 Zehner",
                                                  "14 Zehner = 1 Hunderter + 4 Zehner",
                                                  "4 + 2 + 1 = 7 Hunderter"]),
                                    "selbststaendig": aufgabe(
                                        "358 + 374 = ?", "732",
                                        fehler="622",
                                        tipps=["Wie viele Zehner sind es "
                                               "zusammen?"],
                                        schritte=["8 + 4 = 12",
                                                  "5 + 7 + 1 = 13 Zehner",
                                                  "3 + 3 + 1 = 7 Hunderter"]),
                                    "transfer": auswahl(
                                        "Emma rechnet 456 + 178 und "
                                        "bekommt 1134 heraus. Was hat sie "
                                        "verwechselt?",
                                        "Die Stellen: ihre 7 Zehner wurden "
                                        "zu Hundertern",
                                        ["Nur die Einer vergessen",
                                         "Gar nichts, es stimmt"],
                                        "Sie hat die 7 der 178 als "
                                        "Hunderter gezählt: Stelle für "
                                        "Stelle ergibt 634.")}},
                            {
                                "key": "stellen_vermischt",
                                "label": "Stellen vermischt",
                                "beschreibung": "Zehner der einen Zahl "
                                "landen bei den Hundertern der anderen — "
                                "die Stellenwerte rutschen durcheinander.",
                                "antworten": ["1134"],
                                "erklaerung": {
                                    "haken": "456 + 178: Wer die 7 aus der "
                                            "178 zu den Hundertern zählt, "
                                            "bekommt mehr als doppelt so "
                                            "viel.",
                                    "erkenntnis": "Jede Ziffer hat ihren "
                                    "Platz: die 7 der 178 sind 7 Zehner = "
                                    "70, nicht 700.",
                                    "regel": "Schreibe die Zahlen Stelle "
                                    "für Stelle untereinander: Hunderter "
                                    "über Hunderter, Zehner über Zehner, "
                                    "Einer über Einer.",
                                    "bild": {"zeigt": "456 und 178 "
                                             "untereinander geschrieben",
                                             "bewegt": "die 7 rutscht von "
                                             "der Hunderter- in die "
                                             "Zehnerspalte",
                                             "bleibt_gleich": "der Wert der "
                                             "178 bleibt 178"},
                                    "aufgabe": {"frage": "324 + 192 = ?",
                                                "loesung": "516",
                                                "tipp": "Die 9 der 192 sind Zehner."}},
                                "visualisierung": _TABELLE(
                                    ["Stelle", "456", "178"],
                                    ["Hunderter | 4 | 1",
                                     "Zehner | 5 | 7",
                                     "Einer | 6 | 8"]),
                                "visualisierung_alternativ": _SCHRITTE(
                                    ["Hunderter: 400 + 100 = 500",
                                     "Zehner: 50 + 70 = 120",
                                     "Einer: 6 + 8 = 14",
                                     "500 + 120 + 14 = 634"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist 456 + 178?",
                                        "634",
                                        ["1134", "524"],
                                        "Die 7 gehört zu den Zehnern: "
                                        "400 + 100 = 500, 50 + 70 = 120, "
                                        "6 + 8 = 14."),
                                    "beispiel": aufgabe(
                                        "Wir zerlegen: 456 + 178 = "
                                        "400 + 100 + 50 + 70 + 6 + 8.",
                                        "634",
                                        schritte=["400 + 100 = 500",
                                                  "50 + 70 = 120",
                                                  "6 + 8 = 14",
                                                  "500 + 120 + 14 = 634"]),
                                    "gefuehrt": aufgabe(
                                        "235 + 491 = ?", "726",
                                        fehler="816",
                                        tipps=["Untereinander schreiben.",
                                               "Die 9 der 491 steht bei den Zehnern."],
                                        schritte=["200 + 400 = 600",
                                                  "30 + 90 = 120",
                                                  "5 + 1 = 6",
                                                  "600 + 120 + 6 = 726"]),
                                    "selbststaendig": aufgabe(
                                        "562 + 278 = ?", "840",
                                        fehler="1340",
                                        tipps=["Zähle die Hunderter "
                                               "getrennt."],
                                        schritte=["500 + 200 = 700",
                                                  "60 + 70 = 130",
                                                  "2 + 8 = 10",
                                                  "700 + 130 + 10 = 840"]),
                                    "transfer": auswahl(
                                        "Warum ist es gefährlich, 456 + 178 "
                                        "im Kopf „einfach der Reihe nach“ "
                                        "zu lesen?",
                                        "Weil Ziffern in die falsche "
                                        "Stelle rutschen können",
                                        ["Weil Kopfrechnen immer falsch ist",
                                         "Weil die Zahlen zu groß sind"],
                                        "Die 7 der 178 klingt wie 700 — "
                                        "sie ist aber nur 70. Erst die "
                                        "Stelle entscheidet den Wert.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Überlege, aus wie vielen Hundertern, "
                                    "Zehnern und Einern jede Zahl besteht.",
                            "RULE": "Jede Stelle bündelt einzeln. Mehr als "
                                    "10 auf einer Stelle wandert eine "
                                    "Stelle nach links.",
                            "WORKED_EXAMPLE": "Verfolge jede Stelle einzeln: "
                                    "erst Einer, dann Zehner, dann Hunderter.",
                            "GUIDED_TASK": "Schreib die Zerlegung auf "
                                    "(z. B. 400 + 100), bevor du addierst.",
                            "INDEPENDENT_TASK": "Kontrolliere mit dem "
                                    "Überschlag: ungefähr 400 + 250 = 650 — "
                                    "liegt dein Ergebnis in der Nähe?",
                            "ADAPTATION": "Die Tabelle zeigt dieselbe "
                                    "Rechnung noch einmal — Stelle für "
                                    "Stelle."}),
                        "faq": [
                            {"frage": "Warum wird aus 13 Zehnern ein "
                                      "Hunderter?",
                             "antwort": "Weil 10 Zehner zusammen 100 sind — "
                                        "also genau ein Hunderter. 13 "
                                        "Zehner sind 1 Hunderter und 3 "
                                        "Zehner."},
                            {"frage": "Muss ich schriftlich rechnen?",
                             "antwort": "Nein — aber die Zerlegung "
                                        "(Hunderter, Zehner, Einer getrennt) "
                                        "ist der sichere Weg, egal ob im "
                                        "Kopf oder auf dem Papier."}],
                    }},
                # ------------------------------------- halbschriftlich mal
                {
                    "id": "MA.ZAHLEN.MULT_HALBSCHRIFTLICH",
                    "title": "Halbschriftliches Multiplizieren",
                    "description": "Große Zahlen malnehmen durch Zerlegen: "
                                   "6 · 23 wird zu 6 · 20 + 6 · 3.",
                    "first_contact_grade": 3, "target_grade": 4,
                    "prerequisites": ["MA.ZAHLEN.EINMALEINS",
                                      "MA.ZAHLEN.ZR100"],
                    "levels": {
                        "below": "K3: kleines Einmaleins",
                        "target": "K4: einstellig mal zwei- und "
                                  "dreistellig durch Zerlegen",
                        "above": "K4–5: schriftliche Multiplikation, "
                                 "zweistellig mal zweistellig"},
                    "can_do": {
                        "below": ["Malaufgaben bis 10 · 10 auswendig"],
                        "target": ["Aufgaben wie 6 · 23 oder 4 · 152 durch "
                                   "Zerlegen in Teilprodukte lösen"],
                        "above": ["Zweistellige Faktoren und das "
                                  "schriftliche Verfahren"]},
                    "difficulty_parameters": {
                        "faktoren": "einstellig mal zwei-/dreistellig",
                        "zerlegung": "in Zehner und Einer",
                        "wege": "Teilprodukte schriftlich stützen"},
                    "anchor_items": [
                        item("Rechne: 6 · 23", "138", level="target",
                             grade=4, answer=number(138)),
                        item("Rechne: 4 · 152", "608", level="target",
                             grade=4, answer=number(608))],
                    "boundary_items": {
                        "below": [item("Rechne: 8 · 7", "56", level="below",
                                       grade=3, answer=number(56))],
                        "within": [item("Rechne: 7 · 34", "238",
                                        level="target", grade=4,
                                        answer=number(238))],
                        "above": [item("Rechne: 23 · 12", "276",
                                       level="above", grade=4,
                                       answer=number(276))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Nur ein Teil der "
                             "Zahl wird malgenommen: 6 · 23 wird zu 18 "
                             "(nur die 3) oder 66 — die Zerlegung fehlt.",
                             "remediation_hint": "Die große Zahl in "
                             "Zehner und Einer zerlegen und beide Teile "
                             "einzeln malnehmen.",
                             "diagnostic_item": item(
                                 "Rechne: 6 · 23", "138", level="target",
                                 grade=4, answer=number(138),
                                 distractors=[{"answer": "18",
                                               "misconception": "F1",
                                               "feedback": "Du hast nur 6 · 3 gerechnet — die 20 fehlt noch."}])},
                            {"key": "F2", "description": "Die Zehnerstelle "
                             "wird als Einer malgenommen: 6 · 23 wird zu "
                             "6 · 2 + 6 · 3 = 30 — aus den 2 Zehnern "
                             "wurden 2 Einer.",
                             "remediation_hint": "Beim Zerlegen die "
                             "Stellenwerte mitschreiben: 23 = 20 + 3, "
                             "nicht 2 + 3.",
                             "diagnostic_item": item(
                                 "Rechne: 6 · 23", "138", level="target",
                                 grade=4, answer=number(138),
                                 distractors=[{"answer": "30",
                                               "misconception": "F2",
                                               "feedback": "Die 2 in 23 sind 20 — 6 · 20 ist 120, nicht 12."}])}],
                        "diagnostic_items": [
                            item("Rechne: 9 · 8", "72", level="below",
                                 grade=3, answer=number(72)),
                            item("Rechne: 5 · 46", "230", level="target",
                                 grade=4, answer=number(230))],
                        "exit_items": [
                            item("Rechne: 8 · 36", "288", level="target",
                                 grade=4, answer=number(288)),
                            item("Rechne: 3 · 214", "642", level="target",
                                 grade=4, answer=number(642))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "mult_halbschriftlich",
                            "thema_key": "zahlen",
                            "label": "Halbschriftlich malnehmen",
                            "klasse_von": 3, "klasse_bis": 5,
                            "stichworte": ["halbschriftlich multiplizieren",
                                           "malnehmen zerlegen",
                                           "teilprodukte", "grosse zahlen mal"]},
                        "erstkontakt": {
                            "anker": "Ein Kino verkauft an 6 Tagen je 23 "
                                     "Karten. Wie viele Karten sind das "
                                     "zusammen?",
                            "benennung": "Halbschriftlich malnehmen",
                            "erste_aufgabe": {"frage": "6 · 23 = ?",
                                              "loesung": "138"}},
                        "fehlertypen": [
                            {
                                "key": "zerlegung_fehlt",
                                "label": "Nur einen Teil malgenommen",
                                "beschreibung": "Statt 23 in 20 + 3 zu "
                                "zerlegen, wird nur die Einerziffer "
                                "malgenommen — das Ergebnis ist viel zu "
                                "klein.",
                                "antworten": ["18", "66", "6*23=18"],
                                "erklaerung": {
                                    "haken": "6 · 23: Die 23 ist groß — "
                                            "aber sie lässt sich in zwei "
                                            "bequeme Stücke brechen.",
                                    "erkenntnis": "23 ist 20 + 3. Die "
                                    "Aufgabe wird zu zwei kleinen "
                                    "Einmaleins-Aufgaben: 6 · 20 = 120 "
                                    "und 6 · 3 = 18. Zusammen 138.",
                                    "regel": "Zerlege die große Zahl in "
                                    "Zehner und Einer. Rechne jede "
                                    "Teilaufgabe einzeln und zähle die "
                                    "Teilprodukte zusammen.",
                                    "bild": {"zeigt": "ein Streifen von "
                                             "23 Kästchen, geteilt in "
                                             "20 + 3, sechsmal übereinander",
                                             "bewegt": "der lange Teil "
                                             "wird 6 · 20, der kurze 6 · 3",
                                             "bleibt_gleich": "alle "
                                             "Kästchen werden gezählt — "
                                             "keins fehlt"},
                                    "aufgabe": {"frage": "4 · 32 = ?",
                                                "loesung": "128",
                                                "tipp": "4 · 30 und 4 · 2."}},
                                "visualisierung": _SCHRITTE(
                                    ["23 zerlegen: 20 + 3",
                                     "6 · 20 = 120",
                                     "6 · 3 = 18",
                                     "120 + 18 = 138"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Teil", "Rechnung"],
                                    ["20 | 6 · 20 = 120",
                                     "3 | 6 · 3 = 18",
                                     "zusammen | 120 + 18 = 138"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist 6 · 23?",
                                        "138",
                                        ["18", "126"],
                                        "Nur 6 · 3 zu rechnen lässt die "
                                        "20 weg — 6 · 20 ist 120 dazu."),
                                    "beispiel": aufgabe(
                                        "Wir rechnen 6 · 23: die 23 "
                                        "zerlegen in 20 + 3, dann beide "
                                        "Teile malnehmen.",
                                        "138",
                                        schritte=["23 = 20 + 3",
                                                  "6 · 20 = 120",
                                                  "6 · 3 = 18",
                                                  "120 + 18 = 138"]),
                                    "gefuehrt": aufgabe(
                                        "7 · 34 = ?", "238",
                                        fehler="28",
                                        tipps=["Zerlege 34 in 30 + 4.",
                                               "7 · 30 ist mehr als 7 · 3."],
                                        schritte=["34 = 30 + 4",
                                                  "7 · 30 = 210",
                                                  "7 · 4 = 28",
                                                  "210 + 28 = 238"]),
                                    "selbststaendig": aufgabe(
                                        "8 · 45 = ?", "360",
                                        fehler="40",
                                        tipps=["45 = 40 + 5."],
                                        schritte=["8 · 40 = 320",
                                                  "8 · 5 = 40",
                                                  "320 + 40 = 360"]),
                                    "transfer": auswahl(
                                        "Luis rechnet 5 · 26 und schreibt "
                                        "nur 5 · 6 = 30 auf. Welcher Teil "
                                        "seiner Rechnung fehlt?",
                                        "5 · 20 = 100 — der Zehnerteil",
                                        ["Das Einmaleins der 5",
                                         "Nichts, 30 stimmt"],
                                        "Die 26 ist 20 + 6 — ohne die 20 "
                                        "fehlt genau die Hälfte: "
                                        "100 + 30 = 130.")}},
                            {
                                "key": "stellenwert_rutscht",
                                "label": "Zehner als Einer gerechnet",
                                "beschreibung": "Aus den 2 Zehnern der 23 "
                                "werden beim Zerlegen 2 Einer — das "
                                "Teilprodukt fällt um den Faktor 10 zu "
                                "klein aus.",
                                "antworten": ["30"],
                                "erklaerung": {
                                    "haken": "6 · 23 = 30? Das kann nicht "
                                            "sein — 6 · 10 wäre schon 60.",
                                    "erkenntnis": "Wer die 23 in 2 "
                                    "und 3 zerlegt, verkleinert die "
                                    "Zahl. Die 2 steht für 20: sechs "
                                    "mal 20 ist 120, nicht sechs "
                                    "mal 2.",
                                    "regel": "Beim Zerlegen bleibt jede "
                                    "Stelle ihren Wert: Zehner bleiben "
                                    "Zehner. Schreib 23 = 20 + 3, nicht "
                                    "2 + 3.",
                                    "bild": {"zeigt": "23 als 2 Zehner-"
                                             "stangen und 3 Einerwürfel",
                                             "bewegt": "die Zehnerstange "
                                             "wird mit 6 vervielfacht, "
                                             "nicht die Ziffer 2",
                                             "bleibt_gleich": "23 bleibt "
                                             "23 — nur anders aufgeteilt"},
                                    "aufgabe": {"frage": "3 · 42 = ?",
                                                "loesung": "126",
                                                "tipp": "Die 4 sind 40."}},
                                "visualisierung": _TABELLE(
                                    ["Zerlegung", "richtig?", "Rechnung"],
                                    ["23 = 20 + 3 | ja | 6·20 + 6·3",
                                     "23 = 2 + 3 | nein | Wert verloren"]),
                                "visualisierung_alternativ": _SCHRITTE(
                                    ["3 · 42: 42 = 40 + 2",
                                     "3 · 40 = 120",
                                     "3 · 2 = 6",
                                     "120 + 6 = 126"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist 3 · 42?",
                                        "126",
                                        ["18", "45"],
                                        "Die 4 in 42 sind 40: 3 · 40 = "
                                        "120 und 3 · 2 = 6."),
                                    "beispiel": aufgabe(
                                        "Wir rechnen 4 · 52 — die 52 "
                                        "zerlegen in 50 + 2, also "
                                        "4 · 50 und 4 · 2.",
                                        "208",
                                        schritte=["52 = 50 + 2",
                                                  "4 · 50 = 200",
                                                  "4 · 2 = 8",
                                                  "200 + 8 = 208"]),
                                    "gefuehrt": aufgabe(
                                        "5 · 63 = ?", "315",
                                        fehler="45",
                                        tipps=["63 = 60 + 3.",
                                               "5 · 60, nicht 5 · 6."],
                                        schritte=["5 · 60 = 300",
                                                  "5 · 3 = 15",
                                                  "300 + 15 = 315"]),
                                    "selbststaendig": aufgabe(
                                        "6 · 71 = ?", "426",
                                        fehler="72",
                                        tipps=["Was ist die 7 in 71 "
                                               "wert?"],
                                        schritte=["6 · 70 = 420",
                                                  "6 · 1 = 6",
                                                  "420 + 6 = 426"]),
                                    "transfer": auswahl(
                                        "Jana zerlegt 82 als „8 + 2“ und "
                                        "rechnet 5 · 8 + 5 · 2 = 50. "
                                        "Wo liegt der Denkfehler?",
                                        "Die 8 in 82 ist 80, nicht 8",
                                        ["Sie hätte schriftlich rechnen "
                                         "müssen",
                                         "Das Ergebnis stimmt doch"],
                                        "Beim Zerlegen bleibt der "
                                        "Stellenwert: 82 = 80 + 2, also "
                                        "5 · 80 + 5 · 2 = 410.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Große Malaufgaben werden klein, wenn "
                                    "du die große Zahl in Stücke brichst.",
                            "RULE": "Zerlege in Zehner und Einer, rechne "
                                    "beide Teile einzeln, zähle zusammen.",
                            "WORKED_EXAMPLE": "Lies die Zerlegung zuerst: "
                                    "wo werden die 20 und die 3 "
                                    "malgenommen?",
                            "GUIDED_TASK": "Schreib die Zerlegung auf: "
                                    "welche Zahl ist Zehner, welche Einer?",
                            "INDEPENDENT_TASK": "Schätze vorher: das "
                                    "Ergebnis muss größer sein als die "
                                    "Zehner mal den Faktor.",
                            "ADAPTATION": "Die Tabelle zeigt jedes "
                                    "Teilprodukt einzeln — welches fehlt?"}),
                        "faq": [
                            {"frage": "Warum darf ich die Zahl zerlegen?",
                             "antwort": "Weil 6 · 23 dasselbe ist wie "
                                        "6 mal (20 + 3) — Verteilen "
                                        "ändert das Ergebnis nicht, es "
                                        "macht nur leichter rechnen."},
                            {"frage": "Was mache ich mit dreistelligen "
                                      "Zahlen?",
                             "antwort": "Dasselbe mit drei Teilen: "
                                        "4 · 152 = 4 · 100 + 4 · 50 + "
                                        "4 · 2 = 400 + 200 + 8."}],
                    }},
                # ----------------------------------- halbschriftlich geteilt
                {
                    "id": "MA.ZAHLEN.DIV_HALBSCHRIFTLICH",
                    "title": "Halbschriftliches Dividieren",
                    "description": "Große Zahlen teilen durch Zerlegen: "
                                   "192 : 8 wird zu 160 : 8 + 32 : 8.",
                    "first_contact_grade": 3, "target_grade": 4,
                    "prerequisites": ["MA.ZAHLEN.EINMALEINS",
                                      "MA.ZAHLEN.ZR100"],
                    "levels": {
                        "below": "K3: Einmaleins auch rückwärts",
                        "target": "K4: zwei- und dreistellige Zahlen "
                                  "durch einstellige teilen",
                        "above": "K4–5: schriftliche Division, "
                                 "Teilen mit Rest"},
                    "can_do": {
                        "below": ["Geteiltaufgaben des Einmaleins lösen"],
                        "target": ["Aufgaben wie 96 : 4 oder 192 : 8 "
                                   "durch Zerlegen in teilbare Stücke "
                                   "lösen"],
                        "above": ["Division mit Rest und schriftliches "
                                  "Verfahren"]},
                    "difficulty_parameters": {
                        "dividend": "bis 1000", "divisor": "einstellig",
                        "rest": "kein Rest",
                        "wege": "Zerlegung in bequeme Teile"},
                    "anchor_items": [
                        item("Rechne: 96 : 4", "24", level="target",
                             grade=4, answer=number(24)),
                        item("Rechne: 225 : 5", "45", level="target",
                             grade=4, answer=number(225 / 5))],
                    "boundary_items": {
                        "below": [item("Rechne: 36 : 6", "6", level="below",
                                       grade=3, answer=number(6))],
                        "within": [item("Rechne: 168 : 8", "21",
                                        level="target", grade=4,
                                        answer=number(21))],
                        "above": [item("Rechne: 1000 : 8", "125",
                                       level="above", grade=4,
                                       answer=number(125))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Die Zerlegung "
                             "wird abgebrochen: 192 : 8 wird zu 20 — die "
                             "Restlichen 32 werden einfach vergessen.",
                             "remediation_hint": "Nach dem ersten Teil "
                             "fragen: was ist übrig? Das Übrige muss "
                             "auch geteilt werden.",
                             "diagnostic_item": item(
                                 "Rechne: 192 : 8", "24", level="target",
                                 grade=4, answer=number(24),
                                 distractors=[{"answer": "20",
                                               "misconception": "F1",
                                               "feedback": "160 : 8 = 20 stimmt — aber was ist mit den 32 übrig gebliebenen?"}])},
                            {"key": "F2", "description": "Teil-Quotienten "
                             "werden falsch zusammengesetzt: 96 : 4 wird "
                             "zu 204, weil 80 : 4 = 20 und 16 : 4 = 4 "
                             "nebeneinander statt addiert werden.",
                             "remediation_hint": "Teil-Ergebnisse "
                             "addieren, nicht aneinanderhängen.",
                             "diagnostic_item": item(
                                 "Rechne: 96 : 4", "24", level="target",
                                 grade=4, answer=number(24),
                                 distractors=[{"answer": "204",
                                               "misconception": "F2",
                                               "feedback": "20 und 4 werden addiert: 20 + 4 = 24, nicht aneinander geschrieben."}])}],
                        "diagnostic_items": [
                            item("Rechne: 42 : 6", "7", level="below",
                                 grade=3, answer=number(7)),
                            item("Rechne: 144 : 6", "24", level="target",
                                 grade=4, answer=number(24))],
                        "exit_items": [
                            item("Rechne: 171 : 9", "19", level="target",
                                 grade=4, answer=number(19)),
                            item("Rechne: 252 : 6", "42", level="target",
                                 grade=4, answer=number(42))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "div_halbschriftlich",
                            "thema_key": "zahlen",
                            "label": "Halbschriftlich teilen",
                            "klasse_von": 3, "klasse_bis": 5,
                            "stichworte": ["halbschriftlich dividieren",
                                           "teilen zerlegen",
                                           "division", "grosse zahlen teilen"]},
                        "erstkontakt": {
                            "anker": "96 Stifte werden fair auf 4 Klassen "
                                     "verteilt. Wie viele bekommt jede "
                                     "Klasse?",
                            "benennung": "Halbschriftlich teilen",
                            "erste_aufgabe": {"frage": "96 : 4 = ?",
                                              "loesung": "24"}},
                        "fehlertypen": [
                            {
                                "key": "rest_vergessen",
                                "label": "Zerlegung abgebrochen",
                                "beschreibung": "Der erste bequeme Teil "
                                "wird geteilt, das Übrige fällt unter den "
                                "Tisch — 192 : 8 wird zu 20 statt 24.",
                                "antworten": ["20", "192:8=20"],
                                "erklaerung": {
                                    "haken": "192 : 8: Die 160 passt "
                                            "schön — aber was bleibt "
                                            "übrig?",
                                    "erkenntnis": "192 = 160 + 32. Die "
                                    "160 : 8 = 20 deckt nur den ersten "
                                    "Teil ab: die 32 müssen auch durch 8 "
                                    "— das sind noch einmal 4.",
                                    "regel": "Teile die Zahl in bequeme "
                                    "Stücke, die du durch den Teiler "
                                    "rechnen kannst. JEDES Stück muss "
                                    "geteilt werden — dann addieren.",
                                    "bild": {"zeigt": "192 Kästchen, "
                                             "geteilt in 160 + 32",
                                             "bewegt": "beide Haufen "
                                             "werden auf 8 Fächer verteilt",
                                             "bleibt_gleich": "alle 192 "
                                             "Kästchen werden verteilt"},
                                    "aufgabe": {"frage": "144 : 6 = ?",
                                                "loesung": "24",
                                                "tipp": "120 + 24."}},
                                "visualisierung": _SCHRITTE(
                                    ["192 zerlegen: 160 + 32",
                                     "160 : 8 = 20",
                                     "32 : 8 = 4",
                                     "20 + 4 = 24"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Stück", "Geteilt"],
                                    ["160 | : 8 = 20",
                                     "32 | : 8 = 4",
                                     "zusammen | 20 + 4 = 24"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist 192 : 8?",
                                        "24",
                                        ["20", "21"],
                                        "160 : 8 = 20 teilt nur den "
                                        "ersten Teil — die 32 kommen "
                                        "noch dazu."),
                                    "beispiel": aufgabe(
                                        "Wir rechnen 192 : 8: zerlegen "
                                        "in 160 + 32 und jedes Stück "
                                        "einzeln teilen.",
                                        "24",
                                        schritte=["192 = 160 + 32",
                                                  "160 : 8 = 20",
                                                  "32 : 8 = 4",
                                                  "20 + 4 = 24"]),
                                    "gefuehrt": aufgabe(
                                        "225 : 5 = ?", "45",
                                        fehler="40",
                                        tipps=["Zerlege 225 in 200 + 25.",
                                               "Beide Teile durch 5."],
                                        schritte=["225 = 200 + 25",
                                                  "200 : 5 = 40",
                                                  "25 : 5 = 5",
                                                  "40 + 5 = 45"]),
                                    "selbststaendig": aufgabe(
                                        "168 : 8 = ?", "21",
                                        fehler="20",
                                        tipps=["160 : 8 = 20 — und was "
                                               "bleibt?"],
                                        schritte=["168 = 160 + 8",
                                                  "160 : 8 = 20",
                                                  "8 : 8 = 1",
                                                  "20 + 1 = 21"]),
                                    "transfer": auswahl(
                                        "Finn rechnet 96 : 4: „80 : 4 = "
                                        "20, also 20.“ Was hat er "
                                        "übersehen?",
                                        "Die 16 muss auch geteilt werden",
                                        ["80 ist falsch zerlegt",
                                         "4 ist der falsche Teiler"],
                                        "96 ist 80 + 16 — die 16 : 4 = 4 "
                                        "gehört noch dazu: 20 + 4 = 24.")}},
                            {
                                "key": "teile_aneinander",
                                "label": "Teilergebnisse angehängt",
                                "beschreibung": "Die Teil-Quotienten "
                                "werden als Ziffern nebeneinander "
                                "geschrieben statt addiert — aus 20 + 4 "
                                "wird „204“.",
                                "antworten": ["204", "96:4=204"],
                                "erklaerung": {
                                    "haken": "96 : 4: 80 : 4 = 20 und "
                                            "16 : 4 = 4 — aber 204 ist "
                                            "größer als die 96 selbst!",
                                    "erkenntnis": "Die Teil-Ergebnisse "
                                    "sind Anzahlen, keine Ziffern: 20 + "
                                    "4 = 24. Ein Ergebnis größer als "
                                    "der Dividend ist unmöglich.",
                                    "regel": "Teilergebnisse werden "
                                    "addiert. Plausibilitätscheck: das "
                                    "Ergebnis muss kleiner sein als die "
                                    "geteilte Zahl.",
                                    "bild": {"zeigt": "20 Kästchen und "
                                             "4 Kästchen nebeneinander",
                                             "bewegt": "die zwei Haufen "
                                             "werden zusammengeschoben",
                                             "bleibt_gleich": "zusammen "
                                             "sind es 24 Kästchen"},
                                    "aufgabe": {"frage": "85 : 5 = ?",
                                                "loesung": "17",
                                                "tipp": "50 : 5 + 35 : 5."}},
                                "visualisierung": _SCHRITTE(
                                    ["85 = 50 + 35",
                                     "50 : 5 = 10",
                                     "35 : 5 = 7",
                                     "10 + 7 = 17 — addiert, nicht "
                                     "angehängt"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Teil", "Quotient", "was wird damit"],
                                    ["50 | 10 | wird addiert",
                                     "35 | 7 | wird addiert",
                                     "Ergebnis | 17 | nicht „107“"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist 96 : 4?",
                                        "24",
                                        ["204", "26"],
                                        "80 : 4 = 20 und 16 : 4 = 4 — "
                                        "die Teile werden addiert: "
                                        "20 + 4."),
                                    "beispiel": aufgabe(
                                        "Wir rechnen 85 : 5: 50 + 35 "
                                        "zerlegen, teilen, addieren.",
                                        "17",
                                        schritte=["85 = 50 + 35",
                                                  "50 : 5 = 10",
                                                  "35 : 5 = 7",
                                                  "10 + 7 = 17"]),
                                    "gefuehrt": aufgabe(
                                        "78 : 6 = ?", "13",
                                        fehler="103",
                                        tipps=["78 = 60 + 18.",
                                               "10 + 3, nicht anhängen."],
                                        schritte=["60 : 6 = 10",
                                                  "18 : 6 = 3",
                                                  "10 + 3 = 13"]),
                                    "selbststaendig": aufgabe(
                                        "112 : 7 = ?", "16",
                                        fehler="106",
                                        tipps=["70 : 7 = 10, 42 : 7 = ?"],
                                        schritte=["112 = 70 + 42",
                                                  "70 : 7 = 10",
                                                  "42 : 7 = 6",
                                                  "10 + 6 = 16"]),
                                    "transfer": auswahl(
                                        "Warum kann 96 : 4 nicht 204 "
                                        "ergeben?",
                                        "Das Ergebnis wäre größer als "
                                        "die geteilte Zahl",
                                        ["Weil 4 eine gerade Zahl ist",
                                         "Weil man nicht zerlegen darf"],
                                        "Teilen macht die Zahl kleiner — "
                                        "die Teilergebnisse werden "
                                        "addiert und ergeben 24.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Suche Stücke, die du schon teilen "
                                    "kannst — der Rest folgt.",
                            "RULE": "Zerlege in teilbare Stücke, teile "
                                    "jedes Stück, addiere die "
                                    "Teilergebnisse.",
                            "WORKED_EXAMPLE": "Achte auf die Zerlegung: "
                                    "welche zwei Stücke wurden gewählt "
                                    "und warum?",
                            "GUIDED_TASK": "Schreib die Zerlegung hin, "
                                    "bevor du teilst: was plus was gibt "
                                    "deine Zahl?",
                            "INDEPENDENT_TASK": "Mache die Probe: "
                                    "Ergebnis mal Teiler muss die Zahl "
                                    "ergeben.",
                            "ADAPTATION": "Die Tabelle zeigt jedes "
                                    "Teilergebnis — wo wird addiert "
                                    "statt angehängt?"}),
                        "faq": [
                            {"frage": "Welche Zerlegung ist die richtige?",
                             "antwort": "Jede, bei der beide Stücke sich "
                                        "glatt teilen lassen. Bei 96 : 4 "
                                        "geht 80 + 16, aber auch "
                                        "60 + 36 — beides führt zum Ziel."},
                            {"frage": "Woran erkenne ich ein falsches "
                                      "Ergebnis schnell?",
                             "antwort": "Mach die Gegenprobe: Ergebnis "
                                        "mal Teiler. Bei 204 · 4 kommst "
                                        "du auf 816, nicht auf 96."}],
                    }},
                # --------------------------------------- negative Zahlen
                {
                    "id": "MA.ZAHLEN.NEGATIVE_ZAHLEN",
                    "title": "Negative Zahlen und der Zahlenstrahl",
                    "description": "Zahlen unter Null lesen, ordnen und "
                                   "einfach damit rechnen — die Erweiterung "
                                   "des Zahlenstrahls nach links.",
                    "first_contact_grade": 5, "target_grade": 6,
                    "prerequisites": ["MA.ZAHLEN.ZR100"],
                    "levels": {
                        "below": "K2–4: Zahlenstrahl ab 0",
                        "target": "K5–6: negative Zahlen ordnen, "
                                  "Betrag verstehen, einfache Schritte",
                        "above": "K7: Rechnen mit negativen Zahlen, "
                                 "Koordinatensystem"},
                    "can_do": {
                        "below": ["Zahlen auf dem Zahlenstrahl ab 0 "
                                  "finden und ordnen"],
                        "target": ["Negative Zahlen der Größe nach "
                                   "ordnen und Schritte über die Null "
                                   "hinweg nachvollziehen"],
                        "above": ["Mit negativen Zahlen rechnen"]},
                    "difficulty_parameters": {
                        "zahlraum": "-20 bis 20",
                        "aufgaben": "ordnen, ablesen, einfache Schritte",
                        "darstellung": "Zahlenstrahl, Thermometer"},
                    "anchor_items": [
                        item("Welche Zahl liegt 4 Schritte links von -1?",
                             "-5", level="target", grade=6,
                             answer=number(-5)),
                        item("Ordne der Größe nach: -3, 2, -7, 0. "
                             "Welche Zahl ist die kleinste?", "-7",
                             level="target", grade=6,
                             answer=number(-7))],
                    "boundary_items": {
                        "below": [item("Welche Zahl liegt zwischen -2 "
                                       "und 0?", "-1", level="below",
                                       grade=5, answer=number(-1))],
                        "within": [item("Rechne: -5 + 3", "-2",
                                        level="target", grade=6,
                                        answer=number(-2))],
                        "above": [item("Rechne: -4 - 3", "-7",
                                       level="above", grade=6,
                                       answer=number(-7))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Betrag und "
                             "Vorzeichen werden verwechselt: -7 gilt als "
                             "größer als -3, weil 7 mehr ist als 3.",
                             "remediation_hint": "Am Thermometer zeigen: "
                             "je tiefer die Zahl, desto kälter — -7 ist "
                             "weiter unten als -3.",
                             "diagnostic_item": item(
                                 "Was ist größer: -7 oder -3?", "-3",
                                 level="target", grade=6,
                                 answer=number(-3),
                                 distractors=[{"answer": "-7",
                                               "misconception": "F1",
                                               "feedback": "7 ist mehr als 3 — aber -7 liegt weiter UNTER der Null als -3."}])},
                            {"key": "F2", "description": "Die Richtung auf "
                             "dem Zahlenstrahl kippt: -1 minus 4 wird zu "
                             "3 statt -5 — nach dem Minuszeichen geht es "
                             "irrtümlich wieder nach rechts.",
                             "remediation_hint": "Minus heißt immer: "
                             "Schritte nach LINKS — auch links von der "
                             "Null.",
                             "diagnostic_item": item(
                                 "Rechne: -1 - 4", "-5", level="target",
                                 grade=6, answer=number(-5),
                                 distractors=[{"answer": "3",
                                               "misconception": "F2",
                                               "feedback": "Minus geht nach links: von -1 vier Schritte links landet bei -5."}])}],
                        "diagnostic_items": [
                            item("Welche Zahl liegt 3 Schritte links "
                                 "von 0?", "-3", level="below", grade=5,
                                 answer=number(-3)),
                            item("Ordne der Größe nach: -6, -1, -9. "
                                 "Welche ist die kleinste?", "-9",
                                 level="target", grade=6,
                                 answer=number(-9))],
                        "exit_items": [
                            item("Rechne: -6 + 4", "-2", level="target",
                                 grade=6, answer=number(-2)),
                            item("Welche Zahl liegt in der Mitte "
                                 "zwischen -8 und -2?", "-5",
                                 level="target", grade=6,
                                 answer=number(-5))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "negative_zahlen",
                            "thema_key": "zahlen",
                            "label": "Negative Zahlen",
                            "klasse_von": 5, "klasse_bis": 7,
                            "stichworte": ["negative zahlen", "zahlenstrahl",
                                           "minus zahlen", "unter null",
                                           "betrag", "thermometer"]},
                        "erstkontakt": {
                            "anker": "Am Morgen zeigt das Thermometer "
                                     "-4 Grad. Mittags sind es 6 Grad "
                                     "wärmer. Wie viel zeigt es dann?",
                            "benennung": "Negative Zahlen",
                            "erste_aufgabe": {"frage": "-4 + 6 = ?",
                                              "loesung": "2"}},
                        "fehlertypen": [
                            {
                                "key": "betrag_verwechselt",
                                "label": "Mehr Minus für mehr halten",
                                "beschreibung": "Die Zahl hinter dem "
                                "Minus wird verglichen statt der Lage "
                                "auf dem Zahlenstrahl — -7 wirkt "
                                "„mehr“ als -3.",
                                "antworten": ["-7 ist groesser",
                                              "-7 groesser als -3"],
                                "erklaerung": {
                                    "haken": "Was ist größer: -7 oder "
                                            "-3? Wer nur die Zahlen "
                                            "vergleicht, liegt daneben.",
                                    "erkenntnis": "Auf dem Zahlenstrahl "
                                    "ist größer, was weiter RECHTS "
                                    "liegt. -3 liegt näher an der Null "
                                    "und damit rechts von -7.",
                                    "regel": "Bei negativen Zahlen gilt: "
                                    "je kleiner die Zahl hinter dem "
                                    "Minus, desto größer die Zahl. "
                                    "-3 > -7, weil 3 < 7.",
                                    "bild": {"zeigt": "ein Thermometer "
                                             "mit -7 ganz unten und -3 "
                                             "darüber",
                                             "bewegt": "die Flüssigkeit "
                                             "steigt von -7 zu -3",
                                             "bleibt_gleich": "die "
                                             "Reihenfolge auf dem "
                                             "Strahl ändert sich nie"},
                                    "aufgabe": {"frage": "Was ist "
                                                "größer: -8 oder -2?",
                                                "loesung": "-2",
                                                "tipp": "Was liegt näher "
                                                        "an der Null?"}},
                                "visualisierung": _SCHRITTE(
                                    ["Zahlenstrahl: -9 -8 -7 ... -3 -2 -1 0",
                                     "-7 liegt LINKS von -3",
                                     "links = kleiner, rechts = größer",
                                     "also: -7 < -3"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Vergleich", "Lage", "Ergebnis"],
                                    ["-7 vs -3 | -7 weiter links | -3 größer",
                                     "-2 vs -9 | -2 näher an 0 | -2 größer"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist größer: -7 oder -3?",
                                        "-3",
                                        ["-7", "beide gleich"],
                                        "-3 liegt rechts von -7 auf dem "
                                        "Zahlenstrahl — näher an der "
                                        "Null ist größer."),
                                    "beispiel": aufgabe(
                                        "Wir ordnen -6, -1, -9: wer "
                                        "liegt am weitesten links, ist "
                                        "am kleinsten.",
                                        "-9, -6, -1",
                                        schritte=["-9 liegt am weitesten links",
                                                  "dann -6",
                                                  "-1 liegt am nächsten an 0"]),
                                    "gefuehrt": aufgabe(
                                        "Ordne der Größe nach, kleinste "
                                        "zuerst: -4, -10, -2", "-10, -4, -2",
                                        fehler="-2, -4, -10",
                                        tipps=["Nicht die Zahl hinter dem Minus vergleichen.",
                                               "Was liegt am weitesten links?"],
                                        schritte=["-10 am weitesten links",
                                                  "-4 in der Mitte",
                                                  "-2 am nächsten an 0"]),
                                    "selbststaendig": aufgabe(
                                        "Welche Zahl ist größer: -12 "
                                        "oder -5?", "-5",
                                        fehler="-12",
                                        tipps=["Näher an Null heißt "
                                               "größer."]),
                                    "transfer": auswahl(
                                        "Mia sagt: „-10 Euro Schulden "
                                        "ist besser als -5 Euro "
                                        "Schulden.“ Stimmt das?",
                                        "Nein, -5 Euro Schulden ist "
                                        "besser — man schuldet weniger",
                                        ["Ja, 10 ist mehr als 5",
                                         "Beides ist gleich schlecht"],
                                        "Bei Schulden ist weniger Minus "
                                        "besser: -5 liegt näher an null "
                                        "Schulden.")}},
                            {
                                "key": "richtung_kippt",
                                "label": "Richtung auf dem Strahl kippt",
                                "beschreibung": "Links von der Null "
                                "dreht das Kind die Schrittrichtung um: "
                                "-1 - 4 wird zu 3 statt -5.",
                                "antworten": ["3", "-1-4=3"],
                                "erklaerung": {
                                    "haken": "-1 - 4: Das Minus sagt "
                                            "„nach links“ — egal wo du "
                                            "stehst.",
                                    "erkenntnis": "Von -1 vier Schritte "
                                    "nach links: -2, -3, -4, -5. Die "
                                    "Richtung ändert sich nicht, nur "
                                    "weil man links von der Null ist.",
                                    "regel": "Minus heißt immer "
                                    "Schritte nach LINKS, Plus immer "
                                    "nach RECHTS — auf dem ganzen "
                                    "Zahlenstrahl.",
                                    "bild": {"zeigt": "ein Pfeil, der "
                                             "von -1 über -2, -3, -4 "
                                             "zu -5 wandert",
                                             "bewegt": "vier Einzelschritte "
                                             "nach links",
                                             "bleibt_gleich": "die "
                                             "Richtung des Minus bleibt "
                                             "immer links"},
                                    "aufgabe": {"frage": "-2 - 5 = ?",
                                                "loesung": "-7",
                                                "tipp": "Fünf Schritte "
                                                        "nach links."}},
                                "visualisierung": _SCHRITTE(
                                    ["Start: -1 auf dem Zahlenstrahl",
                                     "Minus 4 = 4 Schritte links",
                                     "-2, -3, -4, -5",
                                     "Ergebnis: -5"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Schritt", "Position"],
                                    ["Start | -1",
                                     "1 links | -2",
                                     "2 links | -3",
                                     "3 links | -4",
                                     "4 links | -5"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist -1 - 4?",
                                        "-5",
                                        ["3", "-3"],
                                        "Minus geht nach links: von -1 "
                                        "vier Schritte links endet bei "
                                        "-5, nicht bei 3."),
                                    "beispiel": aufgabe(
                                        "Wir gehen von -1 aus vier "
                                        "Schritte nach links und zählen "
                                        "jeden mit.",
                                        "-5",
                                        schritte=["-1 → -2",
                                                  "-2 → -3",
                                                  "-3 → -4",
                                                  "-4 → -5"]),
                                    "gefuehrt": aufgabe(
                                        "-3 + 7 = ?", "4",
                                        fehler="-4",
                                        tipps=["Plus geht nach rechts — über die Null hinweg.",
                                               "Erst bis 0: das sind 3 Schritte."],
                                        schritte=["-3 + 3 = 0",
                                                  "noch 4 übrig",
                                                  "0 + 4 = 4"]),
                                    "selbststaendig": aufgabe(
                                        "-2 - 6 = ?", "-8",
                                        fehler="4",
                                        tipps=["Minus geht weiter nach links."]),
                                    "transfer": auswahl(
                                        "Das Thermometer zeigt -2 Grad. "
                                        "Über Nacht wird es 5 Grad "
                                        "kälter. Was zeigt es morgens?",
                                        "-7 Grad",
                                        ["3 Grad", "-3 Grad"],
                                        "Kälter heißt Minus — 5 Schritte "
                                        "nach links von -2 landet bei "
                                        "-7.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Stell dir den Zahlenstrahl wie ein "
                                    "Thermometer vor: unter Null wird es "
                                    "kälter.",
                            "RULE": "Rechts ist größer, links ist "
                                    "kleiner — auf dem ganzen Strahl, "
                                    "auch unter Null.",
                            "WORKED_EXAMPLE": "Folge jedem Schritt auf "
                                    "dem Strahl — wo landet der letzte?",
                            "GUIDED_TASK": "Zeichne den Zahlenstrahl und "
                                    "markiere Start und Ziel, bevor du "
                                    "zählst.",
                            "INDEPENDENT_TASK": "Prüfe: liegt dein "
                                    "Ergebnis auf derselben Seite wie "
                                    "dein Start — oder über der Null?",
                            "ADAPTATION": "Die Schritt-Tabelle zeigt "
                                    "jeden Sprung einzeln."}),
                        "faq": [
                            {"frage": "Warum ist -3 größer als -7, obwohl "
                                      "7 mehr ist als 3?",
                             "antwort": "Das Minus dreht alles um: -7 "
                                        "liegt weiter UNTER der Null als "
                                        "-3. Wer näher an der Null ist, "
                                        "ist größer."},
                            {"frage": "Wofür braucht man negative "
                                      "Zahlen?",
                             "antwort": "Für alles unter Null: "
                                        "Temperaturen im Winter, "
                                        "Schulden auf dem Konto, Etagen "
                                        "unter dem Erdgeschoss."}],
                    }},
                # ------------------------------- Dezimalzahlen am Strahl
                {
                    "id": "MA.ZAHLEN.DEZIMALZAHLEN_ZAHLENSTRAHL",
                    "title": "Dezimalzahlen ordnen und einordnen",
                    "description": "Dezimalzahlen am Zahlenstrahl lesen "
                                   "und der Größe nach ordnen — Zehntel "
                                   "und Hundertstel als Stellenwerte.",
                    "first_contact_grade": 4, "target_grade": 5,
                    "prerequisites": ["MA.BRUECHE.BEGRIFF",
                                      "MA.ZAHLEN.ZR100"],
                    "levels": {
                        "below": "K4: Zehnerbrüche, Zahlenstrahl",
                        "target": "K5: Dezimalzahlen vergleichen, "
                                  "am Zahlenstrahl einordnen",
                        "above": "K6: mit Dezimalzahlen rechnen"},
                    "can_do": {
                        "below": ["Zehnerbrüche wie 3/10 als Teil "
                                  "verstehen"],
                        "target": ["Dezimalzahlen der Größe nach ordnen "
                                   "und zwischen zwei Zahlen "
                                   "einordnen"],
                        "above": ["Mit Dezimalzahlen rechnen"]},
                    "difficulty_parameters": {
                        "stellen": "Zehntel und Hundertstel",
                        "zahlraum": "0 bis 10",
                        "aufgaben": "ordnen, einordnen, vergleichen"},
                    "anchor_items": [
                        item("Was ist größer: 0,7 oder 0,65?", "0,7",
                             level="target", grade=5,
                             answer=text("0,7", "0.7")),
                        item("Welche Zahl liegt genau in der Mitte "
                             "zwischen 2 und 3?", "2,5",
                             level="target", grade=5,
                             answer=number(2.5))],
                    "boundary_items": {
                        "below": [item("Was ist größer: 0,5 oder 0,4?",
                                       "0,5", level="below", grade=4,
                                       answer=text("0,5", "0.5"))],
                        "within": [item("Ordne aufsteigend: 0,3, 0,29, "
                                        "0,31. Die kleinste?", "0,29",
                                        level="target", grade=5,
                                        answer=text("0,29", "0.29"))],
                        "above": [item("Rechne: 1,5 + 0,25", "1,75",
                                       level="above", grade=5,
                                       answer=number(1.75))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Nachkommastellen "
                             "werden als ganze Zahl gelesen: 0,65 gilt "
                             "als größer als 0,7, weil 65 mehr ist als 7.",
                             "remediation_hint": "Stellenwerte "
                             "vergleichen: 0,7 ist 7 Zehntel = 70 "
                             "Hundertstel — mehr als 65 Hundertstel.",
                             "diagnostic_item": item(
                                 "Was ist größer: 0,7 oder 0,65?", "0,7",
                                 level="target", grade=5,
                                 answer=text("0,7", "0.7"),
                                 distractors=[{"answer": "0,65",
                                               "misconception": "F1",
                                               "feedback": "65 sieht mehr aus als 7 — aber es sind Hundertstel gegen Zehntel: 0,7 = 0,70."}])},
                            {"key": "F2", "description": "Die Null in "
                             "Nachkommastellen wird ignoriert: 2,05 "
                             "wird mit 2,5 gleichgesetzt.",
                             "remediation_hint": "Jede Stelle zählt: "
                             "2,05 hat 0 Zehntel und 5 Hundertstel — "
                             "das ist viel weniger als 5 Zehntel.",
                             "diagnostic_item": item(
                                 "Was ist größer: 2,05 oder 2,5?", "2,5",
                                 level="target", grade=5,
                                 answer=text("2,5", "2.5"),
                                 distractors=[{"answer": "2,05",
                                               "misconception": "F2",
                                               "feedback": "2,05 hat null Zehntel — 2,5 hat fünf. Die Null rutscht die 5 eine Stelle weiter."}])}],
                        "diagnostic_items": [
                            item("Was ist größer: 0,3 oder 0,8?", "0,8",
                                 level="below", grade=4,
                                 answer=text("0,8", "0.8")),
                            item("Was ist größer: 1,4 oder 1,38?",
                                 "1,4", level="target", grade=5,
                                 answer=text("1,4", "1.4"))],
                        "exit_items": [
                            item("Ordne aufsteigend: 0,9, 0,85, 0,95. "
                                 "Die kleinste?", "0,85",
                                 level="target", grade=5,
                                 answer=text("0,85", "0.85")),
                            item("Nenne eine Zahl zwischen 3,2 "
                                 "und 3,3", "3,25",
                                 level="target", grade=5,
                                 answer=text("3,25", "3.25", "3,2…"))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "dezimal_zahlenstrahl",
                            "thema_key": "zahlen",
                            "label": "Dezimalzahlen ordnen",
                            "klasse_von": 4, "klasse_bis": 6,
                            "stichworte": ["dezimalzahlen", "kommazahlen",
                                           "zehntel", "hundertstel",
                                           "zahlenstrahl", "ordnen"]},
                        "erstkontakt": {
                            "anker": "Beim Weitsprung springt Lena "
                                     "3,45 m und Tom 3,5 m. Wer ist "
                                     "weiter gesprungen?",
                            "benennung": "Dezimalzahlen ordnen",
                            "erste_aufgabe": {"frage": "Was ist größer: "
                                              "3,45 oder 3,5?",
                                              "loesung": "3,5"}},
                        "fehlertypen": [
                            {
                                "key": "nachkomma_als_ganze_zahl",
                                "label": "Nachkommastellen als ganze "
                                         "Zahl gelesen",
                                "beschreibung": "0,65 wirkt größer als "
                                "0,7, weil 65 mehr aussieht als 7 — "
                                "die Stellenwerte werden ignoriert.",
                                "antworten": ["0,65", "0,65 groesser"],
                                "erklaerung": {
                                    "haken": "0,7 oder 0,65 — was ist "
                                            "größer? Die 65 sieht "
                                            "mächtiger aus als die 7.",
                                    "erkenntnis": "Die 7 steht bei den "
                                    "Zehnteln: 0,7 sind 70 Hundertstel. "
                                    "0,65 sind nur 65 Hundertstel. "
                                    "70 > 65.",
                                    "regel": "Vergleiche Stelle für "
                                    "Stelle ab dem Komma: erst Zehntel, "
                                    "dann Hundertstel. Fehlende Stellen "
                                    "mit Null auffüllen: 0,7 = 0,70.",
                                    "bild": {"zeigt": "0,7 als 70 "
                                             "Kästchen von 100 und 0,65 "
                                             "als 65 Kästchen",
                                             "bewegt": "die 70 "
                                             "Kästchen sind mehr",
                                             "bleibt_gleich": "der "
                                             "Stellenwert jeder Ziffer "
                                             "bleibt"},
                                    "aufgabe": {"frage": "Was ist "
                                                "größer: 0,9 oder 0,87?",
                                                "loesung": "0,9",
                                                "tipp": "0,9 = 0,90."}},
                                "visualisierung": _TABELLE(
                                    ["Zahl", "Zehntel", "Hundertstel"],
                                    ["0,7 | 7 | 0",
                                     "0,65 | 6 | 5",
                                     "Vergleich | 7 > 6 | entschieden"]),
                                "visualisierung_alternativ": _SCHRITTE(
                                    ["0,7 = 70/100",
                                     "0,65 = 65/100",
                                     "70 Hundertstel > 65 Hundertstel",
                                     "also: 0,7 > 0,65"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist größer: 0,7 oder "
                                        "0,65?",
                                        "0,7",
                                        ["0,65", "gleich groß"],
                                        "Auf Hundertstel bringen: "
                                        "0,7 = 0,70 und 70 > 65."),
                                    "beispiel": aufgabe(
                                        "Wir vergleichen 1,4 und 1,38: "
                                        "1,4 als 1,40 schreiben, dann "
                                        "Hundertstel vergleichen.",
                                        "1,4",
                                        schritte=["1,4 = 1,40",
                                                  "40 Hundertstel > 38 Hundertstel",
                                                  "1,4 > 1,38"]),
                                    "gefuehrt": aufgabe(
                                        "Ordne aufsteigend, kleinste "
                                        "zuerst: 0,9, 0,85, 0,95",
                                        "0,85, 0,9, 0,95",
                                        fehler="0,9, 0,85, 0,95",
                                        tipps=["0,9 ist 0,90.",
                                               "85 < 90 < 95 Hundertstel."],
                                        schritte=["alle auf Hundertstel: 0,90, 0,85, 0,95",
                                                  "0,85 am kleinsten",
                                                  "0,90 dann 0,95"]),
                                    "selbststaendig": aufgabe(
                                        "Was ist größer: 2,06 "
                                        "oder 2,6?", "2,6",
                                        fehler="2,06",
                                        tipps=["Zehntel zuerst: 0 "
                                               "gegen 6."]),
                                    "transfer": auswahl(
                                        "Lena springt 3,45 m, Tom "
                                        "3,5 m. Warum ist Tom weiter "
                                        "gesprungen?",
                                        "3,5 m sind 3 m 50 cm — mehr "
                                        "als 3 m 45 cm",
                                        ["Weil 5 weniger Stellen hat",
                                         "Weil 45 mehr ist als 5"],
                                        "Die Nachkommastelle ist kein "
                                        "Vergleich zweier Zahlen: 3,50 "
                                        "hat mehr Zehntel als 3,45.")}},
                            {
                                "key": "null_uebergangen",
                                "label": "Null in Nachkommastellen "
                                         "ignoriert",
                                "beschreibung": "2,05 wird wie 2,5 "
                                "gelesen — die Null auf der "
                                "Zehntelstelle wird einfach "
                                "übersprungen.",
                                "antworten": ["2,05 gleich 2,5",
                                              "2,05 groesser"],
                                "erklaerung": {
                                    "haken": "2,05 und 2,5 — sehen fast "
                                            "gleich aus, liegen aber "
                                            "weit auseinander.",
                                    "erkenntnis": "Die Null schiebt die "
                                    "5 eine Stelle weiter: 2,05 hat "
                                    "0 Zehntel und 5 Hundertstel. "
                                    "2,5 hat 5 Zehntel = 50 "
                                    "Hundertstel.",
                                    "regel": "Jede Stelle nach dem "
                                    "Komma zählt: Zehntel, "
                                    "Hundertstel, Tausendstel. Eine "
                                    "Null rutscht alles danach eine "
                                    "Stelle weiter.",
                                    "bild": {"zeigt": "2,05 auf dem "
                                             "Zahlenstrahl knapp über 2 "
                                             "und 2,5 in der Mitte zu 3",
                                             "bewegt": "die 5 wandert "
                                             "von den Zehnteln zu den "
                                             "Hundertsteln",
                                             "bleibt_gleich": "beide "
                                             "Zahlen behalten ihre "
                                             "Stellen"},
                                    "aufgabe": {"frage": "Was ist "
                                                "größer: 4,07 "
                                                "oder 4,7?",
                                                "loesung": "4,7",
                                                "tipp": "0 Zehntel "
                                                        "gegen 7."}},
                                "visualisierung": _SCHRITTE(
                                    ["2,05 = 2 + 0/10 + 5/100",
                                     "2,5 = 2 + 5/10",
                                     "5 Zehntel = 50 Hundertstel",
                                     "50 > 5, also 2,5 > 2,05"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Stelle", "2,05", "2,5"],
                                    ["Zehntel | 0 | 5",
                                     "Hundertstel | 5 | 0",
                                     "Vergleich | verliert | gewinnt"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist größer: 2,05 oder "
                                        "2,5?",
                                        "2,5",
                                        ["2,05", "gleich groß"],
                                        "2,05 hat null Zehntel — "
                                        "2,5 hat fünf Zehntel = 50 "
                                        "Hundertstel."),
                                    "beispiel": aufgabe(
                                        "Wir zerlegen 1,08 und 1,8 in "
                                        "ihre Stellenwerte und "
                                        "vergleichen.",
                                        "1,8",
                                        schritte=["1,08 zerlegt: 1 Ganzes, "
                                                  "0 Zehntel, 8 Hundertstel",
                                                  "1,8 zerlegt: 1 Ganzes, 8 Zehntel",
                                                  "8 Zehntel > 0 Zehntel"]),
                                    "gefuehrt": aufgabe(
                                        "Was ist kleiner: 5,03 "
                                        "oder 5,3?", "5,03",
                                        fehler="5,3",
                                        tipps=["Wie viele Zehntel hat jede?",
                                               "0 Zehntel ist weniger als 3."],
                                        schritte=["5,03: 0 Zehntel",
                                                  "5,3: 3 Zehntel",
                                                  "0 < 3, also 5,03 kleiner"]),
                                    "selbststaendig": aufgabe(
                                        "Ordne aufsteigend: 1,02, "
                                        "1,2, 1,22. Kleinste?", "1,02",
                                        fehler="1,2",
                                        tipps=["Zehntel zuerst "
                                               "vergleichen."]),
                                    "transfer": auswahl(
                                        "Ein Preisschild zeigt "
                                        "2,05 €, ein anderes 2,50 €. "
                                        "Welches ist teurer?",
                                        "2,50 € — das sind 2 Euro "
                                        "50 Cent",
                                        ["2,05 € — 205 ist mehr als 25",
                                         "Beide gleich teuer"],
                                        "2,05 € sind 2 Euro und 5 "
                                        "Cent — die 5 rutscht bei den "
                                        "Cent weit nach hinten.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Denk an Geld: 0,7 Euro sind 70 "
                                    "Cent — und 0,65 Euro nur 65.",
                            "RULE": "Vergleiche Stelle für Stelle ab "
                                    "dem Komma. Fehlende Stellen mit "
                                    "Null auffüllen.",
                            "WORKED_EXAMPLE": "Schau, wie die Stellen "
                                    "untereinander stehen — wo "
                                    "entscheidet der Vergleich?",
                            "GUIDED_TASK": "Schreib beide Zahlen "
                                    "untereinander, Komma über Komma.",
                            "INDEPENDENT_TASK": "Füll beide Zahlen auf "
                                    "dieselbe Stellenzahl auf und lies "
                                    "dann.",
                            "ADAPTATION": "Die Stellentabelle zeigt "
                                    "Zehntel und Hundertstel "
                                    "nebeneinander."}),
                        "faq": [
                            {"frage": "Warum ist 0,7 mehr als 0,65?",
                             "antwort": "0,7 sind 7 Zehntel = 70 "
                                        "Hundertstel. 0,65 sind 65 "
                                        "Hundertstel — weniger, obwohl "
                                        "65 größer aussieht."},
                            {"frage": "Was bedeutet die Null in 2,05?",
                             "antwort": "Sie sagt: null Zehntel. Die "
                                        "5 steht dadurch bei den "
                                        "Hundertsteln — 2,05 ist viel "
                                        "kleiner als 2,5."}],
                    }},
                # --------------------------------------- Dezimaldivision
                {
                    "id": "MA.ZAHLEN.DEZIMAL_DIVISION",
                    "title": "Mit Dezimalzahlen teilen",
                    "description": "Dezimalzahlen durch natürliche Zahlen "
                                   "teilen — das Komma wandert mit, der "
                                   "Rest wird zu Nachkommastellen.",
                    "first_contact_grade": 5, "target_grade": 6,
                    "prerequisites": ["MA.ZAHLEN.DEZIMALZAHLEN_ZAHLENSTRAHL",
                                      "MA.ZAHLEN.DIV_HALBSCHRIFTLICH"],
                    "levels": {
                        "below": "K5: Dezimalzahlen ordnen, Teilen "
                                 "natürlicher Zahlen",
                        "target": "K6: Dezimalzahl durch einstellige "
                                  "Zahl teilen",
                        "above": "K7: Teilen durch Dezimalzahlen, "
                                 "periodische Ergebnisse"},
                    "can_do": {
                        "below": ["Dezimalzahlen lesen und ordnen, "
                                  "natürliche Zahlen teilen"],
                        "target": ["Aufgaben wie 3,6 : 2 oder 7,2 : 3 "
                                   "mit korrektem Komma lösen"],
                        "above": ["Durch Dezimalzahlen teilen"]},
                    "difficulty_parameters": {
                        "dividend": "Dezimalzahlen bis 100",
                        "divisor": "einstellig, natürlich",
                        "rest": "endliche Ergebnisse"},
                    "anchor_items": [
                        item("Rechne: 3,6 : 2", "1,8", level="target",
                             grade=6, answer=number(1.8)),
                        item("Rechne: 7,2 : 3", "2,4", level="target",
                             grade=6, answer=number(2.4))],
                    "boundary_items": {
                        "below": [item("Rechne: 8 : 4", "2",
                                       level="below", grade=4,
                                       answer=number(2))],
                        "within": [item("Rechne: 4,5 : 3", "1,5",
                                        level="target", grade=6,
                                        answer=number(1.5))],
                        "above": [item("Rechne: 3 : 0,5", "6",
                                       level="above", grade=6,
                                       answer=number(6))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Das Komma "
                             "verschwindet: 3,6 : 2 wird zu 18 statt "
                             "1,8 — die Nachkommastelle wird beim "
                             "Teilen einfach verschluckt.",
                             "remediation_hint": "In Cent denken: "
                             "3,60 Euro geteilt durch 2 sind 1,80 Euro "
                             "— das Komma kommt beim Übergang zu den "
                             "Zehnteln mit.",
                             "diagnostic_item": item(
                                 "Rechne: 3,6 : 2", "1,8",
                                 level="target", grade=6,
                                 answer=number(1.8),
                                 distractors=[{"answer": "18",
                                               "misconception": "F1",
                                               "feedback": "3,6 geteilt ergibt etwas Kleineres als 3,6 — 18 ist viel zu groß."}])},
                            {"key": "F2", "description": "Der Rest vor "
                             "dem Komma wird falsch weitergeführt: bei "
                             "4,5 : 3 wird aus der 1 vor dem Komma "
                             "Rest 1, der dann zu 1,5 wird statt "
                             "mit den Zehnteln verrechnet zu werden.",
                             "remediation_hint": "Der Rest gehört zu "
                             "den nächsten Zehnteln: Rest 1 vor dem "
                             "Komma wird zu 10 Zehnteln.",
                             "diagnostic_item": item(
                                 "Rechne: 4,5 : 3", "1,5",
                                 level="target", grade=6,
                                 answer=number(1.5),
                                 distractors=[{"answer": "1,05",
                                               "misconception": "F2",
                                               "feedback": "Rest 1 sind 10 Zehntel — mit den 5 Zehnteln: 15 : 3 = 5."}])}],
                        "diagnostic_items": [
                            item("Rechne: 6,4 : 2", "3,2",
                                 level="below", grade=5,
                                 answer=number(3.2)),
                            item("Rechne: 9,6 : 4", "2,4",
                                 level="target", grade=6,
                                 answer=number(2.4))],
                        "exit_items": [
                            item("Rechne: 5,4 : 3", "1,8",
                                 level="target", grade=6,
                                 answer=number(1.8)),
                            item("Rechne: 8,4 : 6", "1,4",
                                 level="target", grade=6,
                                 answer=number(1.4))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "dezimal_division",
                            "thema_key": "zahlen",
                            "label": "Dezimalzahlen teilen",
                            "klasse_von": 5, "klasse_bis": 7,
                            "stichworte": ["dezimalzahlen teilen",
                                           "komma division",
                                           "dezimal division",
                                           "kommazahlen rechnen"]},
                        "erstkontakt": {
                            "anker": "Drei Freunde teilen 7,2 Meter "
                                     "Stoff fair. Wie viel bekommt "
                                     "jeder?",
                            "benennung": "Dezimalzahlen teilen",
                            "erste_aufgabe": {"frage": "7,2 : 3 = ?",
                                              "loesung": "2,4"}},
                        "fehlertypen": [
                            {
                                "key": "komma_verschwunden",
                                "label": "Komma verschluckt",
                                "beschreibung": "Beim Teilen geht das "
                                "Komma verloren: aus 3,6 : 2 wird 18 — "
                                "das Ergebnis ist größer als die "
                                "Ausgangszahl.",
                                "antworten": ["18", "3,6:2=18"],
                                "erklaerung": {
                                    "haken": "3,6 : 2: Wenn das "
                                            "Ergebnis größer ist als "
                                            "das, was geteilt wird — "
                                            "ist etwas schiefgelaufen.",
                                    "erkenntnis": "3,6 : 2 heißt: "
                                    "36 Zehntel geteilt durch 2 sind "
                                    "18 Zehntel — und 18 Zehntel sind "
                                    "1,8, nicht 18.",
                                    "regel": "Teile zuerst den ganzen "
                                    "Teil. Über dem Komma der "
                                    "Aufgabe steht im Ergebnis das "
                                    "Komma. Zehntel werden zu "
                                    "Zehnteln geteilt.",
                                    "bild": {"zeigt": "3,6 als 3 "
                                             "ganze + 6 Zehntel-"
                                             "Kästchen, auf 2 Haufen "
                                             "verteilt",
                                             "bewegt": "auf jedem "
                                             "Haufen: 1 Ganzes und "
                                             "8 Zehntel",
                                             "bleibt_gleich": "alle "
                                             "Kästchen werden "
                                             "verteilt"},
                                    "aufgabe": {"frage": "4,8 : 4 = ?",
                                                "loesung": "1,2",
                                                "tipp": "48 Zehntel "
                                                        ": 4."}},
                                "visualisierung": _SCHRITTE(
                                    ["3,6 = 36 Zehntel",
                                     "36 Zehntel : 2 = 18 Zehntel",
                                     "18 Zehntel = 1,8",
                                     "Probe: 1,8 · 2 = 3,6"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Schritt", "Rechnung"],
                                    ["Ganze teilen | 3 : 2 = 1 Rest 1",
                                     "Rest zu Zehnteln | 1 Rest = 10 Zehntel + 6",
                                     "Zehntel teilen | 16 : 2 = 8 Zehntel",
                                     "Ergebnis | 1,8"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist 3,6 : 2?",
                                        "1,8",
                                        ["18", "1,3"],
                                        "Geteilt wird kleiner: "
                                        "36 Zehntel : 2 sind 18 "
                                        "Zehntel = 1,8."),
                                    "beispiel": aufgabe(
                                        "Wir rechnen 7,2 : 3: die "
                                        "Ganzen teilen, den Rest zu "
                                        "Zehnteln machen.",
                                        "2,4",
                                        schritte=["7 geteilt durch 3 "
                                                  "gibt 2, Rest 1",
                                                  "Rest 1 sind 10 Zehntel, mit 2 Zehnteln: 12",
                                                  "12 Zehntel geteilt "
                                                  "durch 3 gibt 4 Zehntel",
                                                  "Ergebnis: 2,4"]),
                                    "gefuehrt": aufgabe(
                                        "4,5 : 3 = ?", "1,5",
                                        fehler="15",
                                        tipps=["4 : 3 = 1 Rest 1.",
                                               "Rest 1 plus 5 Zehntel sind 15 Zehntel."],
                                        schritte=["4 geteilt durch 3 "
                                                  "gibt 1, Rest 1",
                                                  "10 + 5 = 15 Zehntel",
                                                  "15 Zehntel geteilt "
                                                  "durch 3 gibt 5",
                                                  "Ergebnis: 1,5"]),
                                    "selbststaendig": aufgabe(
                                        "9,6 : 6 = ?", "1,6",
                                        fehler="16",
                                        tipps=["Das Komma wandert mit — "
                                               "36 Zehntel : 6."]),
                                    "transfer": auswahl(
                                        "Emma rechnet 5,4 : 3 und "
                                        "schreibt 18. Wie widerlegt "
                                        "sie das Ergebnis sofort "
                                        "selbst?",
                                        "Mit der Probe: 18 · 3 ist "
                                        "54, nicht 5,4",
                                        ["Indem sie nochmal teilt",
                                         "18 ist richtig, kein Fehler"],
                                        "Die Gegenprobe entlarvt das "
                                        "fehlende Komma: 18 · 3 = 54 "
                                        "— es muss 1,8 sein.")}},
                            {
                                "key": "rest_falsch_weiter",
                                "label": "Rest falsch umgewandelt",
                                "beschreibung": "Der Rest vor dem "
                                "Komma wird nicht zu Zehnteln "
                                "umgewandelt — die Nachkommastelle "
                                "verrutscht oder fehlt.",
                                "antworten": ["1,05", "1,15"],
                                "erklaerung": {
                                    "haken": "4,5 : 3: 4 : 3 gibt "
                                            "Rest 1 — und der geht "
                                            "weiter ins Komma.",
                                    "erkenntnis": "Rest 1 Ganzes ist "
                                    "dasselbe wie 10 Zehntel. Mit den "
                                    "5 Zehnteln der Aufgabe sind es "
                                    "15 Zehntel — und die teilen "
                                    "sich glatt durch 3.",
                                    "regel": "Ein Rest wird zur "
                                    "nächsten Stelle umgerechnet: "
                                    "1 Ganzes Rest sind 10 Zehntel, "
                                    "die zu den vorhandenen Zehnteln "
                                    "dazukommen.",
                                    "bild": {"zeigt": "1 Ganzes wird "
                                             "in 10 Zehntel-Streifen "
                                             "getauscht",
                                             "bewegt": "10 + 5 Zehntel "
                                             "werden zu 15 — verteilt "
                                             "auf 3",
                                             "bleibt_gleich": "der "
                                             "Gesamtwert bleibt 4,5"},
                                    "aufgabe": {"frage": "5,6 : 4 = ?",
                                                "loesung": "1,4",
                                                "tipp": "Rest 1 sind "
                                                        "16 Zehntel."}},
                                "visualisierung": _SCHRITTE(
                                    ["5 : 4 = 1 Rest 1",
                                     "Rest 1 = 10 Zehntel",
                                     "10 + 6 = 16 Zehntel",
                                     "16 : 4 = 4 Zehntel → 1,4"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Stelle", "Rechnung", "Ergebnis"],
                                    ["Einer | 5 : 4 | 1 Rest 1",
                                     "Zehntel | 16 : 4 | 4",
                                     "zusammen | | 1,4"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist 4,5 : 3?",
                                        "1,5",
                                        ["1,05", "1,3"],
                                        "Rest 1 wird zu 10 Zehnteln — "
                                        "mit 5 sind 15 : 3 = 5."),
                                    "beispiel": aufgabe(
                                        "Wir rechnen 5,6 : 4: erst "
                                        "die Ganzen, dann den Rest "
                                        "als Zehntel weiter.",
                                        "1,4",
                                        schritte=["5 geteilt durch 4 "
                                                  "gibt 1, Rest 1",
                                                  "der Rest sind 10 Zehntel, plus 6: 16",
                                                  "16 geteilt durch 4 gibt 4",
                                                  "Ergebnis: 1,4"]),
                                    "gefuehrt": aufgabe(
                                        "7,5 : 5 = ?", "1,5",
                                        fehler="1,05",
                                        tipps=["7 : 5 = 1 Rest 2.",
                                               "Rest 2 sind 20 Zehntel — plus 5 macht 25."],
                                        schritte=["7 geteilt durch 5 "
                                                  "gibt 1, Rest 2",
                                                  "20 + 5 = 25 Zehntel",
                                                  "25 : 5 = 5",
                                                  "Ergebnis: 1,5"]),
                                    "selbststaendig": aufgabe(
                                        "8,4 : 6 = ?", "1,4",
                                        fehler="1,04",
                                        tipps=["Rest 2 werden 24 "
                                               "Zehntel."]),
                                    "transfer": auswahl(
                                        "Warum werden aus einem Rest "
                                        "von 1 Ganzen beim Komma 10 "
                                        "Zehntel?",
                                        "Weil ein Ganzes aus 10 "
                                        "Zehnteln besteht",
                                        ["Weil das Komma immer 10 "
                                         "bedeutet",
                                         "Damit das Ergebnis größer "
                                         "wird"],
                                        "Der Stellenwert wechselt: "
                                        "1 Ganzes = 10 Zehntel — wie "
                                        "1 Euro = 10 Zehn-Cent-"
                                        "Stücke.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Denk an Geld: 3,60 Euro auf zwei "
                                    "Leute — jeder bekommt 1,80 Euro.",
                            "RULE": "Ganze teilen, Rest wird zu "
                                    "Zehnteln, Komma wandert gerade "
                                    "nach oben.",
                            "WORKED_EXAMPLE": "Verfolge den Rest: wo "
                                    "wird er zu Zehnteln umgewandelt?",
                            "GUIDED_TASK": "Markiere die Stelle, an "
                                    "der das Komma steht — im "
                                    "Ergebnis steht es genau darüber.",
                            "INDEPENDENT_TASK": "Mach die Probe: "
                                    "Ergebnis mal Teiler muss die "
                                    "Ausgangszahl geben.",
                            "ADAPTATION": "Die Schritte zeigen den "
                                    "Rest beim Übergang ins Komma."}),
                        "faq": [
                            {"frage": "Wo steht das Komma im "
                                      "Ergebnis?",
                             "antwort": "Genau über dem Komma der "
                                        "Aufgabe: sobald du beim "
                                        "Teilen die Zehntel erreichst, "
                                        "setzt du im Ergebnis das "
                                        "Komma."},
                            {"frage": "Kann geteilt auch größer "
                                      "werden?",
                             "antwort": "Nur wenn du durch etwas "
                                        "Kleineres als 1 teilst — "
                                        "durch 0,5 geteilt verdoppelt. "
                                        "Durch 2 geteilt wird immer "
                                        "kleiner."}],
                    }},
                # --------------------------------- rationale Multiplikation
                {
                    "id": "MA.ZAHLEN.RATIONALE_MULT",
                    "title": "Rationale Zahlen multiplizieren",
                    "description": "Mit Vorzeichen und Komma malnehmen: "
                                   "(-3) · 4, 2,5 · 0,4 — die Regeln "
                                   "für Vorzeichen und Kommastellen.",
                    "first_contact_grade": 6, "target_grade": 7,
                    "prerequisites": ["MA.ZAHLEN.DEZIMALZAHLEN_ZAHLENSTRAHL",
                                      "MA.ZAHLEN.NEGATIVE_ZAHLEN",
                                      "MA.ZAHLEN.MULT_HALBSCHRIFTLICH"],
                    "levels": {
                        "below": "K5–6: Dezimalzahlen, negative "
                                 "Zahlen, Malnehmen",
                        "target": "K7: Produkte mit Vorzeichen und "
                                  "Dezimalzahlen",
                        "above": "K8: rationale Zahlen in allen "
                                 "Rechenarten, Brüche"},
                    "can_do": {
                        "below": ["Mit Dezimalzahlen und negativen "
                                  "Zahlen umgehen"],
                        "target": ["Produkte wie (-3) · 4 oder "
                                   "2,5 · 0,4 mit korrektem Vorzeichen "
                                   "und Komma berechnen"],
                        "above": ["Brüche und rationale Zahlen in "
                                  "allen Rechenarten"]},
                    "difficulty_parameters": {
                        "zahlen": "Dezimalzahlen und ganze Zahlen",
                        "vorzeichen": "plus und minus",
                        "stellen": "bis zwei Nachkommastellen"},
                    "anchor_items": [
                        item("Rechne: (-3) · 4", "-12", level="target",
                             grade=7, answer=number(-12)),
                        item("Rechne: 2,5 · 0,4", "1", level="target",
                             grade=7, answer=number(1))],
                    "boundary_items": {
                        "below": [item("Rechne: 0,5 · 6", "3",
                                       level="below", grade=6,
                                       answer=number(3))],
                        "within": [item("Rechne: (-1,5) · (-2)", "3",
                                        level="target", grade=7,
                                        answer=number(3))],
                        "above": [item("Rechne: 1/2 · 1/3", "1/6",
                                       level="above", grade=7,
                                       answer=text("1/6"))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Das Vorzeichen "
                             "wird vergessen oder falsch gesetzt: "
                             "(-3) · 4 wird zu 12 oder (-3) · (-2) "
                             "bleibt bei -6.",
                             "remediation_hint": "Vorzeichen zuerst "
                             "bestimmen, dann rechnen: gleiche "
                             "Vorzeichen ergeben plus, verschiedene "
                             "minus.",
                             "diagnostic_item": item(
                                 "Rechne: (-3) · (-2)", "6",
                                 level="target", grade=7,
                                 answer=number(6),
                                 distractors=[{"answer": "-6",
                                               "misconception": "F1",
                                               "feedback": "Minus mal Minus wird Plus — wie zwei Umkehrungen hintereinander."}])},
                            {"key": "F2", "description": "Die "
                             "Kommastellen werden nicht mitgezählt: "
                             "2,5 · 0,4 wird zu 10 statt 1,0 — die "
                             "Nachkommastellen beider Faktoren gehören "
                             "ins Ergebnis.",
                             "remediation_hint": "Erst ohne Komma "
                             "rechnen, dann die Summe der "
                             "Nachkommastellen setzen.",
                             "diagnostic_item": item(
                                 "Rechne: 2,5 · 0,4", "1",
                                 level="target", grade=7,
                                 answer=number(1),
                                 distractors=[{"answer": "10",
                                               "misconception": "F2",
                                               "feedback": "25 · 4 = 100 — aber mit zwei Nachkommastellen: 1,00 = 1."}])}],
                        "diagnostic_items": [
                            item("Rechne: 0,2 · 3", "0,6",
                                 level="below", grade=6,
                                 answer=number(0.6)),
                            item("Rechne: (-4) · (-5)", "20",
                                 level="target", grade=7,
                                 answer=number(20))],
                        "exit_items": [
                            item("Rechne: (-2,5) · 4", "-10",
                                 level="target", grade=7,
                                 answer=number(-10)),
                            item("Rechne: (-0,5) · (-8)", "4",
                                 level="target", grade=7,
                                 answer=number(4))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "rationale_mult",
                            "thema_key": "zahlen",
                            "label": "Rationale Zahlen malnehmen",
                            "klasse_von": 6, "klasse_bis": 8,
                            "stichworte": ["rationale zahlen",
                                           "minus mal minus",
                                           "vorzeichen",
                                           "komma multiplikation",
                                           "negative zahlen malnehmen"]},
                        "erstkontakt": {
                            "anker": "Das Konto steht 4 Tage lang jeden "
                                     "Tag 3 Euro im Minus. Wie ändert "
                                     "sich der Stand insgesamt?",
                            "benennung": "Rationale Zahlen malnehmen",
                            "erste_aufgabe": {"frage": "4 · (-3) = ?",
                                              "loesung": "-12"}},
                        "fehlertypen": [
                            {
                                "key": "vorzeichen_verloren",
                                "label": "Vorzeichen vergessen oder "
                                         "verdreht",
                                "beschreibung": "Minus mal Minus wird "
                                "zu minus, oder das Minus fällt ganz "
                                "weg — die Vorzeichenregel fehlt.",
                                "antworten": ["12", "-6", "(-3)*(-2)=-6"],
                                "erklaerung": {
                                    "haken": "(-3) · (-2): Zwei Minus "
                                            "hintereinander — was kommt "
                                            "heraus?",
                                    "erkenntnis": "Das Minus ist eine "
                                    "Umkehrung. Zweimal umgekehrt ist "
                                    "wieder geradeaus: minus mal "
                                    "minus ergibt plus.",
                                    "regel": "Erst das Vorzeichen: "
                                    "gleiche Vorzeichen ergeben plus, "
                                    "verschiedene minus. Dann die "
                                    "Zahlen normal malnehmen.",
                                    "bild": {"zeigt": "eine "
                                             "Drehscheibe: einmal "
                                             "minus dreht um 180 Grad, "
                                             "zweimal zurück",
                                             "bewegt": "zwei Drehungen "
                                             "landen wieder bei plus",
                                             "bleibt_gleich": "die "
                                             "Betraege bleiben"},
                                    "aufgabe": {"frage": "(-5) · "
                                                "(-3) = ?",
                                                "loesung": "15",
                                                "tipp": "Gleiche "
                                                        "Vorzeichen?"}},
                                "visualisierung": _TABELLE(
                                    ["Vorzeichen", "Ergebnis"],
                                    ["+ · + | +",
                                     "+ · - | -",
                                     "- · + | -",
                                     "- · - | +"]),
                                "visualisierung_alternativ": _SCHRITTE(
                                    ["(-3) · (-2): erst Vorzeichen",
                                     "minus mal minus → plus",
                                     "dann 3 · 2 = 6",
                                     "Ergebnis: +6"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist (-3) · (-2)?",
                                        "6",
                                        ["-6", "-5"],
                                        "Minus mal minus ergibt plus — "
                                        "wie zweimal umdrehen."),
                                    "beispiel": aufgabe(
                                        "Wir rechnen (-4) · 3: erst "
                                        "das Vorzeichen, dann die "
                                        "Zahlen.",
                                        "-12",
                                        schritte=["minus mal plus → minus",
                                                  "4 · 3 = 12",
                                                  "Ergebnis: -12"]),
                                    "gefuehrt": aufgabe(
                                        "(-6) · (-5) = ?", "30",
                                        fehler="-30",
                                        tipps=["Gleiche Vorzeichen ergeben plus.",
                                               "6 · 5 = ?"],
                                        schritte=["minus mal minus → plus",
                                                  "6 · 5 = 30",
                                                  "Ergebnis: +30"]),
                                    "selbststaendig": aufgabe(
                                        "(-7) · 3 = ?", "-21",
                                        fehler="21",
                                        tipps=["Verschiedene Vorzeichen — "
                                               "welches Ergebniszeichen?"]),
                                    "transfer": auswahl(
                                        "Ein Lehrer sagt: „Zweimal "
                                        "umdrehen ist wie gar nicht "
                                        "umdrehen.“ Was meint er für "
                                        "die Rechnung (-2) · (-4)?",
                                        "Minus mal minus wird plus: 8",
                                        ["Das Ergebnis bleibt -8",
                                         "Man darf nicht rechnen"],
                                        "Jedes Minus dreht das "
                                        "Vorzeichen um — zwei "
                                        "Drehungen landen bei plus.")}},
                            {
                                "key": "kommastellen_verloren",
                                "label": "Kommastellen nicht "
                                         "mitgezählt",
                                "beschreibung": "Beim Rechnen ohne "
                                "Komma stimmt die Ziffernfolge, aber "
                                "das Ergebnis trägt die "
                                "Nachkommastellen beider Faktoren "
                                "nicht.",
                                "antworten": ["10", "2,5*0,4=10"],
                                "erklaerung": {
                                    "haken": "2,5 · 0,4: 25 · 4 = 100 "
                                            "— aber stimmt 10 als "
                                            "Ergebnis?",
                                    "erkenntnis": "Der Überschlag "
                                    "verrät es: 2,5 ist etwa 2 und "
                                    "0,4 fast ein halb — 2 mal ein "
                                    "halb ist etwa 1. Das Ergebnis "
                                    "braucht zwei Nachkommastellen.",
                                    "regel": "Rechne ohne Kommas, "
                                    "dann zähle die Nachkommastellen "
                                    "beider Faktoren: 2,5 und 0,4 "
                                    "haben zusammen zwei — aus 100 "
                                    "wird 1,00.",
                                    "bild": {"zeigt": "25 mal 4 "
                                             "ergibt 100, das Komma "
                                             "rutscht zwei Stellen "
                                             "nach links",
                                             "bewegt": "das Komma "
                                             "wandert zwei Plätze",
                                             "bleibt_gleich": "die "
                                             "Ziffernfolge 100 "
                                             "bleibt"},
                                    "aufgabe": {"frage": "1,5 · 0,2 "
                                                "= ?", "loesung": "0,3",
                                                "tipp": "15 · 2 = 30, "
                                                        "dann zwei "
                                                        "Stellen."}},
                                "visualisierung": _SCHRITTE(
                                    ["ohne Komma: 25 · 4 = 100",
                                     "Nachkommastellen zählen: 1 + 1 = 2",
                                     "Komma zwei Stellen von rechts",
                                     "Ergebnis: 1,00 = 1"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Faktor", "Nachkommastellen"],
                                    ["2,5 | 1",
                                     "0,4 | 1",
                                     "Ergebnis | 2 → 1,00"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist 2,5 · 0,4?",
                                        "1",
                                        ["10", "0,1"],
                                        "25 · 4 = 100 — mit zwei "
                                        "Nachkommastellen: 1,00 = 1."),
                                    "beispiel": aufgabe(
                                        "Wir rechnen 1,2 · 0,3: erst "
                                        "ohne Komma, dann die "
                                        "Stellen zählen.",
                                        "0,36",
                                        schritte=["12 · 3 = 36",
                                                  "Nachkommastellen: 1 + 1 = 2",
                                                  "Ergebnis: 0,36"]),
                                    "gefuehrt": aufgabe(
                                        "0,6 · 0,5 = ?", "0,3",
                                        fehler="3",
                                        tipps=["6 · 5 = 30.",
                                               "Zwei Nachkommastellen: 0,30."],
                                        schritte=["6 · 5 = 30",
                                                  "zwei Stellen: 0,30",
                                                  "Ergebnis: 0,3"]),
                                    "selbststaendig": aufgabe(
                                        "3,2 · 0,4 = ?", "1,28",
                                        fehler="12,8",
                                        tipps=["Wie viele "
                                               "Nachkommastellen "
                                               "insgesamt?"]),
                                    "transfer": auswahl(
                                        "Warum ist der Überschlag bei "
                                        "2,5 · 0,4 so hilfreich?",
                                        "2 mal ein halb ist etwa 1 — "
                                        "zeigt sofort, dass 10 "
                                        "falsch ist",
                                        ["Er macht das Ergebnis genauer",
                                         "Er spart das Kommazählen"],
                                        "Der Überschlag verrät die "
                                        "Größenordnung: das Ergebnis "
                                        "muss bei 1 liegen, nicht bei "
                                        "10.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Vorzeichen zuerst: gleiche "
                                    "ergeben plus, verschiedene minus.",
                            "RULE": "Erst das Vorzeichen, dann die "
                                    "Zahlen, dann die "
                                    "Nachkommastellen beider "
                                    "Faktoren zählen.",
                            "WORKED_EXAMPLE": "Trenne die Schritte: "
                                    "wo wird das Vorzeichen "
                                    "entschieden, wo das Komma "
                                    "gesetzt?",
                            "GUIDED_TASK": "Schreib die "
                                    "Vorzeichenentscheidung auf, bevor "
                                    "du rechnest.",
                            "INDEPENDENT_TASK": "Überschlag prüfen: "
                                    "passt die Größenordnung deines "
                                    "Ergebnisses?",
                            "ADAPTATION": "Die Vorzeichentabelle und "
                                    "die Kommaschritte zeigen beide "
                                    "Hürden einzeln."}),
                        "faq": [
                            {"frage": "Warum ist minus mal minus "
                                      "plus?",
                             "antwort": "Ein Minus kehrt die Richtung "
                                        "um. Zweimal umkehren bringt "
                                        "dich zurück — wie ein "
                                        "Wenden und nochmal Wenden."},
                            {"frage": "Wohin kommt das Komma?",
                             "antwort": "Zähle die Nachkommastellen "
                                        "beider Faktoren zusammen — "
                                        "so viele hat das Ergebnis. "
                                        "Bei 2,5 · 0,4 sind es "
                                        "zwei."}],
                    }},
                # --------------------------------------- Fläche Rechteck
                {
                    "id": "MA.GEO.FLAECHE_RECHTECK",
                    "title": "Fläche eines Rechtecks",
                    "description": "Fläche als Anzahl der Kästchen: Länge mal "
                                   "Breite — und warum die Einheit Quadrat ist.",
                    "first_contact_grade": 4, "target_grade": 5,
                    "prerequisites": ["MA.ZAHLEN.EINMALEINS"],
                    "levels": {
                        "below": "K3: Einmaleins, Reihen zählen",
                        "target": "K5: A = a * b mit Quadrateinheit",
                        "above": "K6: zusammengesetzte Flächen, Umfang vs. "
                                 "Fläche sicher trennen"},
                    "can_do": {
                        "below": ["Kästchen in Reihen zählen und malnehmen"],
                        "target": ["Die Fläche eines Rechtecks mit Länge mal "
                                   "Breite berechnen und in cm² angeben"],
                        "above": ["Flächen zerlegen und zusammensetzen"]},
                    "difficulty_parameters": {
                        "seiten": "natürliche Zahlen", "einheit": "cm",
                        "ergebnis": "in cm²"},
                    "anchor_items": [
                        item("Ein Rechteck ist 6 cm lang und 4 cm breit. "
                             "Wie groß ist seine Fläche?",
                             "24 cm²", level="target", grade=5,
                             answer=number(24, unit="cm²")),
                        item("Ein Rechteck ist 7 cm mal 3 cm. Fläche?",
                             "21 cm²", level="target", grade=5,
                             answer=number(21, unit="cm²"))],
                    "boundary_items": {
                        "below": [item("Ein Feld hat 3 Reihen mit je 5 "
                                       "Kästchen. Wie viele Kästchen?",
                                       "15", level="below", grade=3,
                                       answer=number(15))],
                        "within": [item("Fläche: 8 cm mal 2 cm", "16 cm²",
                                        level="target", grade=5,
                                        answer=number(16, unit="cm²"))],
                        "above": [item("Eine L-förmige Fläche aus zwei "
                                       "Rechtecken 4*3 und 2*5 cm — Gesamtfläche?",
                                       "22 cm²", level="above", grade=6,
                                       answer=number(22, unit="cm²"))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Fläche mit Umfang "
                             "verwechselt: a + b oder 2a + 2b statt a * b.",
                             "remediation_hint": "Umfang läuft am Rand "
                             "entlang, Fläche füllt die Mitte — am Bild "
                             "nachzählen.",
                             "diagnostic_item": item(
                                 "Fläche eines Rechtecks 6 cm mal 4 cm?",
                                 "24 cm²", level="target", grade=5,
                                 answer=number(24, unit="cm²"),
                                 distractors=[{"answer": "20 cm²",
                                               "misconception": "F1",
                                               "feedback": "20 ist der Umfang — die Fläche füllt die Mitte."}])},
                            {"key": "F2", "description": "Einheit bleibt cm "
                             "statt cm² — die Fläche wird in Länge gemessen.",
                             "remediation_hint": "Jedes Kästchen ist ein "
                             "Quadratzentimeter — zwei Längen ergeben eine Fläche.",
                             "diagnostic_item": item(
                                 "Ein Rechteck 5 cm mal 3 cm hat die Fläche …",
                                 "15 cm²", level="target", grade=5,
                                 answer=choice("15 cm²", ["15 cm"], ["F2"]),
                                 distractors=[])},
                            {"key": "F3", "description": "Seiten werden "
                             "addiert statt multipliziert — die Mal-Struktur "
                             "der Reihen ist nicht gesehen.",
                             "remediation_hint": "Reihen zählen: 4 Reihen "
                             "mit je 6 Kästchen — das ist Mal, nicht Plus.",
                             "diagnostic_item": item(
                                 "Fläche eines Rechtecks 6 cm mal 4 cm?",
                                 "24 cm²", level="target", grade=5,
                                 answer=number(24, unit="cm²"),
                                 distractors=[{"answer": "10 cm²",
                                               "misconception": "F3",
                                               "feedback": "6 + 4 sind nur zwei Seiten — die Fläche hat 4 Reihen à 6."}])}],
                        "diagnostic_items": [
                            item("Ein Feld: 4 Reihen mit je 5 Kästchen. "
                                 "Wie viele Kästchen?", "20", level="below",
                                 grade=4, answer=number(20)),
                            item("Fläche: 7 cm mal 2 cm", "14 cm²",
                                 level="target", grade=5,
                                 answer=number(14, unit="cm²"))],
                        "exit_items": [
                            item("Fläche: 9 cm mal 4 cm", "36 cm²",
                                 level="target", grade=5,
                                 answer=number(36, unit="cm²")),
                            item("Ein Quadrat hat Seite 6 cm. Fläche?",
                                 "36 cm²", level="target", grade=5,
                                 answer=number(36, unit="cm²"))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "flaeche_rechteck",
                            "thema_key": "geometrie",
                            "label": "Fläche eines Rechtecks",
                            "klasse_von": 4, "klasse_bis": 6,
                            "stichworte": ["fläche", "rechteck fläche",
                                           "flächeninhalt", "länge mal breite",
                                           "quadratzentimeter", "cm²"]},
                        "erstkontakt": {
                            "anker": "Ein Blumenbeet ist 6 m lang und 4 m "
                                     "breit. Für wie viel Erde muss gesorgt "
                                     "werden?",
                            "benennung": "Fläche",
                            "erste_aufgabe": {"frage": "Ein Rechteck ist "
                                              "5 cm lang und 3 cm breit. "
                                              "Fläche?", "loesung": "15 cm²"}},
                        "fehlertypen": [
                            {
                                "key": "flaeche_umfang",
                                "label": "Fläche und Umfang verwechselt",
                                "beschreibung": "Statt die Mitte zu füllen "
                                "wird der Rand vermessen: a + b + a + b.",
                                "antworten": ["20", "20 cm²", "10"],
                                "erklaerung": {
                                    "haken": "6 mal 4 cm — wer 20 sagt, hat "
                                            "den Rand gemessen, nicht die Fläche.",
                                    "erkenntnis": "Der Umfang läuft einmal "
                                    "außen herum: 6 + 4 + 6 + 4 = 20 cm. Die "
                                    "Fläche füllt die ganze Mitte: 4 Reihen "
                                    "mit je 6 Kästchen — 24.",
                                    "regel": "Umfang: alle Seiten addieren "
                                    "(weg drumherum). Fläche: Länge mal "
                                    "Breite (die Mitte füllen).",
                                    "bild": {"zeigt": "ein Rechteck aus "
                                             "6 mal 4 Kästchen",
                                             "bewegt": "die Kästchen der "
                                             "Mitte färben sich reihenweise",
                                             "bleibt_gleich": "der Rand bleibt "
                                             "ungefüllt — er ist nicht die Fläche"},
                                    "aufgabe": {"frage": "Rechteck 7 cm mal "
                                                "3 cm — Fläche?",
                                                "loesung": "21 cm²"}},
                                "visualisierung": _FLAECHEN_EINHEIT_VIS,
                                "visualisierung_alternativ": _SCHRITTE(
                                    ["Fläche = Kästchen in der Mitte",
                                     "4 Reihen mit je 6 Kästchen",
                                     "4 * 6 = 24 — die Einheit ist cm²"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Rechteck 6 cm mal 4 cm — was "
                                        "beschreibt die Fläche?",
                                        "24 cm²", ["20 cm²", "10 cm²"],
                                        "Die Fläche füllt die Mitte: 4 Reihen "
                                        "à 6 Kästchen. 20 wäre der Weg am Rand."),
                                    "beispiel": aufgabe(
                                        "Wir legen das Rechteck 5 mal 3 aus: "
                                        "3 Reihen mit je 5 Quadratzentimetern. "
                                        "3 * 5 = 15 Kästchen.",
                                        "15 cm²",
                                        schritte=["3 Reihen à 5 cm²",
                                                  "3 * 5 = 15", "Einheit: cm²"]),
                                    "gefuehrt": aufgabe(
                                        "Rechteck 8 cm mal 3 cm — Fläche?",
                                        "24 cm²",
                                        fehler="22 cm²",
                                        tipps=["Wie viele Reihen mit je "
                                               "wie vielen Kästchen?",
                                               "22 wäre der Umfang."],
                                        schritte=["3 Reihen à 8 cm²",
                                                  "3 * 8 = 24 cm²"]),
                                    "selbststaendig": aufgabe(
                                        "Rechteck 9 cm mal 5 cm — Fläche?",
                                        "45 cm²",
                                        fehler="28 cm²",
                                        tipps=["Länge mal Breite."],
                                        schritte=["9 * 5 = 45", "Einheit cm²"]),
                                    "transfer": auswahl(
                                        "Für einen Zaun um das Beet braucht "
                                        "man den Umfang, für Erde die Fläche. "
                                        "Warum liefert 2*(6+4) keine Fläche?",
                                        "Es misst nur den Weg am Rand — die "
                                        "Mitte bleibt ungezählt",
                                        ["Es rechnet mit falschen Zahlen",
                                         "Die Formel gilt nur für Quadrate"],
                                        "Am Rand entlang ist eine Länge, "
                                        "die Fläche liegt in der Mitte.")}},
                            {
                                "key": "einheit_flach",
                                "label": "Einheit bleibt cm statt cm²",
                                "beschreibung": "Die Fläche wird als Länge "
                                "angegeben — das Quadrat in der Einheit fehlt.",
                                "antworten": ["24 cm", "15 cm"],
                                "erklaerung": {
                                    "haken": "24 — richtig gerechnet, aber "
                                            "die Einheit verrät ein Missverständnis.",
                                    "erkenntnis": "Jedes Kästchen ist ein "
                                    "Quadrat aus 1 cm mal 1 cm — ein "
                                    "Quadratzentimeter. Zwei Längen ergeben "
                                    "eine Fläche, darum cm².",
                                    "regel": "Länge mal Länge gibt Fläche: "
                                    "cm mal cm wird cm². Eine Zahl ohne "
                                    "die richtige Einheit ist halb falsch.",
                                    "bild": {"zeigt": "ein Kästchen mit "
                                             "Kanten 1 cm und 1 cm",
                                             "bewegt": "das Kästchen wird "
                                             "vervielfacht und füllt das Rechteck",
                                             "bleibt_gleich": "jedes Kästchen "
                                             "bleibt ein Quadratzentimeter"},
                                    "aufgabe": {"frage": "4 cm mal 2 cm — "
                                                "Fläche mit Einheit?",
                                                "loesung": "8 cm²"}},
                                "visualisierung": _TABELLE(
                                    ["Größe", "Einheit"],
                                    ["Länge | cm", "Fläche | cm²",
                                     "Volumen | cm³"]),
                                "visualisierung_alternativ": _SCHRITTE(
                                    ["1 Kästchen = 1 cm * 1 cm = 1 cm²",
                                     "24 Kästchen = 24 cm²",
                                     "cm beschreibt eine Strecke — keine Fläche"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Ein Rechteck 5 cm mal 3 cm hat "
                                        "die Fläche …", "15 cm²",
                                        ["15 cm", "8 cm²"],
                                        "Flächen misst man in Quadraten — "
                                        "die Einheit heißt Quadratzentimeter."),
                                    "beispiel": aufgabe(
                                        "Ein Kästchen: 1 cm hoch und 1 cm "
                                        "breit = 1 cm². 12 Kästchen sind "
                                        "12 cm².",
                                        "12 cm²"),
                                    "gefuehrt": aufgabe(
                                        "Rechteck 6 cm mal 2 cm — Fläche "
                                        "mit Einheit?", "12 cm²",
                                        fehler="12 cm",
                                        tipps=["Jedes Kästchen ist ein "
                                               "Quadrat — wie heißt seine Größe?",
                                               "cm ist eine Länge."],
                                        schritte=["6 * 2 = 12",
                                                  "cm * cm = cm²"]),
                                    "selbststaendig": aufgabe(
                                        "Rechteck 7 cm mal 4 cm — Fläche "
                                        "mit Einheit?", "28 cm²",
                                        fehler="28 cm",
                                        tipps=["cm mal cm ergibt …?"],
                                        schritte=["7 * 4 = 28 cm²"]),
                                    "transfer": auswahl(
                                        "Warum schreibt man hinter die "
                                        "Fläche cm² und nicht cm?",
                                        "Weil zwei Längen ein Quadrat "
                                        "bilden — die Fläche besteht aus "
                                        "Quadratzentimetern",
                                        ["Es ist nur eine Konvention",
                                         "cm² ist eine größere Länge"],
                                        "Die Einheit beschreibt, WAS "
                                        "gezählt wird: Quadrate, nicht Strecken.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Fläche füllt die Mitte — Umfang läuft "
                                    "nur am Rand entlang.",
                            "RULE": "Fläche = Länge mal Breite. Zwei Längen "
                                    "ergeben eine Fläche: cm mal cm = cm².",
                            "WORKED_EXAMPLE": "Zähle die Kästchen in einer "
                                    "Reihe, dann die Reihen.",
                            "GUIDED_TASK": "Denk in Reihen: wie viele "
                                    "Kästchen pro Reihe, wie viele Reihen?",
                            "INDEPENDENT_TASK": "Vergiss die Einheit nicht — "
                                    "sie gehört zum Ergebnis.",
                            "ADAPTATION": "Schau dir an, was ein Kästchen "
                                    "ist — dann wird die Einheit klar."}),
                        "faq": [
                            {"frage": "Was ist der Unterschied zwischen "
                                      "Fläche und Umfang?",
                             "antwort": "Der Umfang ist der Weg am Rand "
                                        "entlang (eine Länge). Die Fläche "
                                        "ist alles in der Mitte, gezählt in "
                                        "Quadratzentimetern."},
                            {"frage": "Warum cm² und nicht cm?",
                             "antwort": "Weil die Fläche aus kleinen "
                                        "Quadraten von 1 cm mal 1 cm besteht — "
                                        "jedes ist ein Quadratzentimeter."}],
                    }},
                # ------------------------------------------- Einheiten
                {
                    "id": "MA.GROESSEN.EINHEITEN",
                    "title": "Längen- und Raumeinheiten",
                    "description": "mm, cm, m, km und was das ³ bei cm³ "
                                   "bedeutet — Einheiten als Größenfamilie.",
                    "first_contact_grade": 3, "target_grade": 4,
                    "prerequisites": ["MA.ZAHLEN.ZR100"],
                    "levels": {
                        "below": "K2–3: cm und m abschätzen und messen",
                        "target": "K4: Einheiten umwandeln und die Stufen "
                                  "verstehen (10, 100, 1000)",
                        "above": "K5–6: Flächen- und Volumeneinheiten, "
                                 "Zusammenhang zu Rechteck/Quader"},
                    "can_do": {
                        "below": ["Gegenstände in cm oder m messen"],
                        "target": ["Zwischen mm, cm, m und km umrechnen und "
                                   "wissen, dass 1 cm³ ein Würfelchen ist"],
                        "above": ["Flächen- und Volumeneinheiten deuten"]},
                    "difficulty_parameters": {
                        "einheiten": "mm, cm, m, km", "umwandlung": "Stufen 10/100/1000"},
                    "anchor_items": [
                        item("Wie viele cm sind 3 m?", "300 cm",
                             level="target", grade=4,
                             answer=number(300, unit="cm")),
                        item("Wie viele mm sind 5 cm?", "50 mm",
                             level="target", grade=4,
                             answer=number(50, unit="mm"))],
                    "boundary_items": {
                        "below": [item("Was ist länger: 1 m oder 90 cm?",
                                       "1 m", level="below", grade=3,
                                       answer=text("1 m", "1m", "meter"))],
                        "within": [item("2 km in m?", "2000 m",
                                        level="target", grade=4,
                                        answer=number(2000, unit="m"))],
                        "above": [item("Ein Würfel mit Kante 2 cm hat ein "
                                       "Volumen von …", "8 cm³",
                                       level="above", grade=6,
                                       answer=number(8, unit="cm³"))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Umrechnungszahl "
                             "verwechselt: 1 m wird zu 10 cm oder 1000 cm — "
                             "die Stufen laufen durcheinander.",
                             "remediation_hint": "Die Leiter lernen: "
                             "mm→cm→dm→m immer *10, m→km *1000.",
                             "diagnostic_item": item(
                                 "Wie viele cm sind 1 m?", "100 cm",
                                 level="target", grade=4,
                                 answer=choice("100 cm", ["10 cm", "1000 cm"],
                                               ["F1", "F1"]),
                                 distractors=[])},
                            {"key": "F2", "description": "cm³ wird als "
                             "falsche Schreibweise von cm oder als dritte "
                             "Dimension ohne Bedeutung gelesen.",
                             "remediation_hint": "1 cm³ ist ein Würfelchen "
                             "mit Kante 1 cm — drei Male cm.",
                             "diagnostic_item": item(
                                 "Was bedeutet 1 cm³?", "Ein Würfel mit "
                                 "Kantenlänge 1 cm", level="target", grade=4,
                                 answer=choice("Ein Würfel mit Kantenlänge "
                                               "1 cm",
                                               ["3 cm Länge",
                                                "ein Quadrat von 1 cm Seite"],
                                               ["F2", "F2"]),
                                 distractors=[])}],
                        "diagnostic_items": [
                            item("Miss dein Heft: ungefähr wie lang ist es "
                                 "in cm?", "30 cm", level="below", grade=3,
                                 answer=number(30, tolerance=15, unit="cm")),
                            item("Wie viele m sind 2 km?", "2000 m",
                                 level="target", grade=4,
                                 answer=number(2000, unit="m"))],
                        "exit_items": [
                            item("Wie viele cm sind 2,5 m?", "250 cm",
                                 level="target", grade=4,
                                 answer=number(250, unit="cm")),
                            item("Was ist mehr: 400 cm oder 5 m?", "5 m",
                                 level="target", grade=4,
                                 answer=text("5 m", "5m", "fünf meter"))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "einheiten",
                            "thema_key": "groessen",
                            "label": "Längen- und Raumeinheiten",
                            "klasse_von": 3, "klasse_bis": 5,
                            "stichworte": ["einheiten", "cm", "mm", "meter",
                                           "kilometer", "cm³", "umrechnen",
                                           "maßeinheiten"]},
                        "erstkontakt": {
                            "anker": "Ein Klassenzimmer ist etwa 8 m lang — "
                                     "wie viele cm sind das?",
                            "benennung": "Einheiten",
                            "erste_aufgabe": {"frage": "1 m = ? cm",
                                              "loesung": "100 cm"}},
                        "fehlertypen": [
                            {
                                "key": "stufe_verwechselt",
                                "label": "Umrechnungsstufe verwechselt",
                                "beschreibung": "1 m wird zu 10 cm — die "
                                "Einheitenleiter wird an der falschen Stelle "
                                "betreten.",
                                "antworten": ["10 cm", "10", "1000 cm"],
                                "erklaerung": {
                                    "haken": "Wie viele cm sind 1 m? Wer "
                                            "10 sagt, ist eine Stufe der "
                                            "Einheitenleiter verrutscht.",
                                    "erkenntnis": "Zwischen mm, cm, dm und m "
                                    "liegt immer dieselbe Stufe: mal 10. "
                                    "1 m = 10 dm = 100 cm = 1000 mm.",
                                    "regel": "Die Längenleiter: mm - cm - dm "
                                    "- m, jede Stufe mal 10. Erst zum km "
                                    "springt sie auf mal 1000.",
                                    "bild": {"zeigt": "die Leiter mm - cm - "
                                             "dm - m - km",
                                             "bewegt": "jede Sprosse nach "
                                             "unten mal 10",
                                             "bleibt_gleich": "die Länge "
                                             "ändert sich nicht — nur ihr Name"},
                                    "aufgabe": {"frage": "4 cm = ? mm",
                                                "loesung": "40 mm"}},
                                "visualisierung": _SCHRITTE(
                                    ["1 m = 10 dm", "1 dm = 10 cm",
                                     "also 1 m = 10 * 10 cm = 100 cm"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Einheit", "in der nächstkleineren"],
                                    ["1 m | 10 dm", "1 dm | 10 cm",
                                     "1 cm | 10 mm"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Wie viele cm sind 1 m?", "100 cm",
                                        ["10 cm", "1000 cm"],
                                        "Erst m→dm (mal 10), dann dm→cm (mal 10) — zusammen mal 100."),
                                    "beispiel": aufgabe(
                                        "3 m in cm: 1 m = 100 cm, also "
                                        "3 * 100.",
                                        "300 cm",
                                        schritte=["1 m = 100 cm",
                                                  "3 * 100 = 300 cm"]),
                                    "gefuehrt": aufgabe(
                                        "6 cm = ? mm", "60 mm",
                                        fehler="600 mm",
                                        tipps=["Eine Stufe von cm zu mm — "
                                               "wie groß ist sie?",
                                               "600 wären zwei Stufen."],
                                        schritte=["1 cm = 10 mm",
                                                  "6 * 10 = 60 mm"]),
                                    "selbststaendig": aufgabe(
                                        "7 m = ? cm", "700 cm",
                                        fehler="70 cm",
                                        tipps=["m zu cm sind zwei Stufen."],
                                        schritte=["1 m = 100 cm",
                                                  "7 * 100 = 700 cm"]),
                                    "transfer": auswahl(
                                        "Warum ist 1 m nicht 10 cm?",
                                        "Zwischen m und cm liegt noch dm — "
                                        "es sind zwei Stufen à mal 10",
                                        ["Die Stufe ist immer 100",
                                         "cm ist einfach eine kleinere Zahl"],
                                        "Die Leiter hat Sprossen — "
                                        "überspringt man eine, fehlt ein Faktor 10.")}},
                            {
                                "key": "kubik_als_laenge",
                                "label": "cm³ wird als Länge gelesen",
                                "beschreibung": "Das hochgestellte 3 wird "
                                "ignoriert oder als Dreifaches gelesen.",
                                "antworten": ["3 cm", "ein drittel cm"],
                                "erklaerung": {
                                    "haken": "Was ist 1 cm³? Wer „drei cm“ "
                                            "sagt, liest die 3 als Zahl — "
                                            "sie ist eine Dimension.",
                                    "erkenntnis": "Die kleine 3 sagt: drei "
                                    "Richtungen. 1 cm³ ist ein Würfelchen "
                                    "mit 1 cm Kante — Länge mal Breite mal "
                                    "Höhe.",
                                    "regel": "cm² zählt Flächenkästchen "
                                    "(zwei Richtungen), cm³ zählt "
                                    "Würfelchen (drei Richtungen).",
                                    "bild": {"zeigt": "ein Würfelchen aus "
                                             "1 cm Kante in alle drei "
                                             "Richtungen",
                                             "bewegt": "acht solcher "
                                             "Würfelchen bauen einen "
                                             "2-cm-Würfel",
                                             "bleibt_gleich": "jedes "
                                             "Würfelchen bleibt 1 cm³"},
                                    "aufgabe": {"frage": "Ein Würfel hat "
                                                "Kante 2 cm — wie viele "
                                                "cm³-Würfelchen passen hinein?",
                                                "loesung": "8"}},
                                "visualisierung": _TABELLE(
                                    ["Zeichen", "Bedeutung"],
                                    ["cm | eine Strecke",
                                     "cm² | eine Fläche aus Kästchen",
                                     "cm³ | ein Raum aus Würfelchen"]),
                                "visualisierung_alternativ": _SCHRITTE(
                                    ["1 cm³ = 1 Würfelchen, Kante 1 cm",
                                     "2 cm Kante: 2*2*2 = 8 Würfelchen",
                                     "die 3 zählt die Richtungen, nicht die cm"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist 1 cm³?",
                                        "Ein Würfelchen mit 1 cm Kante",
                                        ["3 cm Länge", "ein Drittel cm"],
                                        "Das ³ zählt die Richtungen: Länge, "
                                        "Breite, Höhe."),
                                    "beispiel": aufgabe(
                                        "Ein Würfelchen von 1 cm Kante "
                                        "füllt 1 cm³. Acht davon bauen "
                                        "einen 2-cm-Würfel: 2 * 2 * 2 = 8 cm³.",
                                        "8 cm³"),
                                    "gefuehrt": aufgabe(
                                        "Wie viele 1-cm³-Würfelchen füllen "
                                        "eine Schachtel von 3 cm Länge, "
                                        "2 cm Breite und 1 cm Höhe?", "6",
                                        fehler="6 cm",
                                        tipps=["Leg eine Schicht: wie "
                                               "viele Würfelchen?",
                                               "Würfelchen zählt man in cm³."],
                                        schritte=["3 * 2 * 1 = 6 Würfelchen",
                                                  "= 6 cm³"]),
                                    "selbststaendig": aufgabe(
                                        "Ein Würfel mit Kante 3 cm — wie "
                                        "viele cm³?", "27",
                                        fehler="9",
                                        tipps=["Drei Richtungen, je 3 cm."],
                                        schritte=["3 * 3 * 3 = 27 cm³"]),
                                    "transfer": auswahl(
                                        "Ein Blatt Papier und ein Quader "
                                        "unterscheiden sich in der Einheit. "
                                        "Warum passt cm² beim Papier, aber "
                                        "nicht beim Quader?",
                                        "Das Blatt hat nur Fläche, der "
                                        "Quader füllt Raum — er braucht die "
                                        "dritte Richtung",
                                        ["cm² ist zu klein",
                                         "Der Quader ist schwerer"],
                                        "Die Zahl hinter der Einheit zählt "
                                        "die Richtungen, die gefüllt werden.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Einheiten sind eine Leiter — jede "
                                    "Sprosse hat ihren eigenen Faktor.",
                            "RULE": "mm-cm-dm-m: jede Stufe mal 10. Das ³ "
                                    "bei cm³ zählt drei Richtungen.",
                            "WORKED_EXAMPLE": "Folge den Sprossen einzeln — "
                                    "jede ist ein eigener Schritt.",
                            "GUIDED_TASK": "Schreib die Leiter hin und "
                                    "zähle die Stufen, die du gehst.",
                            "INDEPENDENT_TASK": "Prüfe die Einheit: passt "
                                    "sie zu dem, was du gemessen hast?",
                            "ADAPTATION": "Schau dir das Würfelchen an — "
                                    "die 3 meint Richtungen, nicht Zahlen."}),
                        "faq": [
                            {"frage": "Warum ist 1 m 100 cm und nicht 10?",
                             "antwort": "Weil zwischen Meter und "
                                        "Zentimeter noch das Dezimeter "
                                        "liegt: 1 m = 10 dm = 100 cm."},
                            {"frage": "Was bedeutet die 3 bei cm³?",
                             "antwort": "Sie steht für drei Richtungen: "
                                        "ein Würfelchen mit 1 cm Länge, "
                                        "Breite und Höhe."}],
                    }},
            ]},
        {
            "id": "MA.BRUECHE",
            "title": "Brüche verstehen und rechnen",
            "description": "Vom Anteil über Erweitern und Kürzen bis zur "
                           "Addition ungleichnamiger Brüche.",
            "grade_min": 5, "grade_max": 7, "typical_grade": 6,
            "concepts": [
                # ------------------------------------------ Bruch-Begriff
                {
                    "id": "MA.BRUECHE.BEGRIFF",
                    "title": "Brüche verstehen und darstellen",
                    "description": "Ein Bruch ist ein Anteil: Zähler "
                                   "zählt die Teile, Nenner sagt, in "
                                   "wie viele das Ganze geteilt ist.",
                    "first_contact_grade": 4, "target_grade": 5,
                    "prerequisites": ["MA.ZAHLEN.EINMALEINS"],
                    "levels": {
                        "below": "K3–4: Hälfte, Viertel, Drittel "
                                 "erkennen",
                        "target": "K5: Brüche lesen, darstellen, "
                                  "Anteile von Mengen bestimmen",
                        "above": "K6: erweitern, kürzen, vergleichen"},
                    "can_do": {
                        "below": ["Ein halb und ein viertel von etwas "
                                  "finden"],
                        "target": ["Einen Bruch als Anteil deuten, am "
                                   "Bild darstellen und Anteile von "
                                   "Mengen berechnen"],
                        "above": ["Brüche in andere Schreibweisen "
                                  "bringen"]},
                    "difficulty_parameters": {
                        "nenner": "bis 12", "darstellung": "Kreis, "
                        "Rechteck, Menge",
                        "zahlen": "Zähler kleiner Nenner"},
                    "anchor_items": [
                        item("Ein Kuchen ist in 8 Stücke geteilt, 3 "
                             "sind gegessen. Welcher Bruchteil bleibt?",
                             "5/8", level="target", grade=5,
                             answer=text("5/8")),
                        item("Wie viel sind 3/4 von 20?", "15",
                             level="target", grade=5,
                             answer=number(15))],
                    "boundary_items": {
                        "below": [item("Was ist die Hälfte von 12?",
                                       "6", level="below", grade=4,
                                       answer=number(6))],
                        "within": [item("Welcher Bruchteil ist "
                                        "markiert: 2 von 5 Kästchen?",
                                        "2/5", level="target", grade=5,
                                        answer=text("2/5"))],
                        "above": [item("Erweitere 2/3 auf Neuntel",
                                       "6/9", level="above", grade=6,
                                       answer=text("6/9"))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Zähler und "
                             "Nenner werden vertauscht: 3/8 wird als "
                             "„8 von 3“ gelesen oder als 8/3 "
                             "geschrieben.",
                             "remediation_hint": "Unten steht, in wie "
                             "viele Teile geteilt wurde; oben, wie "
                             "viele gemeint sind. „U wie unten = "
                             "Ufteilung“.",
                             "diagnostic_item": item(
                                 "Von 8 Kästchen sind 3 markiert. "
                                 "Welcher Bruch?",
                                 "3/8", level="target", grade=5,
                                 answer=text("3/8"),
                                 distractors=[{"answer": "8/3",
                                               "misconception": "F1",
                                               "feedback": "Unten steht die Zahl aller Teile: 8. Oben die markierten: 3."}])},
                            {"key": "F2", "description": "Ein größerer "
                             "Nenner wird als größerer Anteil gelesen: "
                             "1/8 gilt als mehr als 1/4, weil 8 "
                             "größer ist als 4.",
                             "remediation_hint": "Mehr Teile heißt "
                             "kleinere Stücke: ein Achtel Kuchen ist "
                             "kleiner als ein Viertel.",
                             "diagnostic_item": item(
                                 "Was ist größer: 1/4 oder 1/8?",
                                 "1/4", level="target", grade=5,
                                 answer=text("1/4", "ein viertel"),
                                 distractors=[{"answer": "1/8",
                                               "misconception": "F2",
                                               "feedback": "In 8 Teile geteilt sind die Stücke kleiner — ein Achtel ist weniger als ein Viertel."}])}],
                        "diagnostic_items": [
                            item("Was ist ein Drittel von 9?", "3",
                                 level="below", grade=4,
                                 answer=number(3)),
                            item("4/6 von 12 Aufklebern sind wie "
                                 "viele?", "8", level="target",
                                 grade=5, answer=number(8))],
                        "exit_items": [
                            item("Welcher Bruchteil ist weiß: 7 "
                                 "Kästchen, 4 grau?", "3/7",
                                 level="target", grade=5,
                                 answer=text("3/7")),
                            item("2/5 von 15 Euro sind wie viel?",
                                 "6", level="target", grade=5,
                                 answer=number(6))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "bruch_begriff",
                            "thema_key": "brueche",
                            "label": "Brüche verstehen",
                            "klasse_von": 4, "klasse_bis": 6,
                            "stichworte": ["bruch", "brüche", "zaehler",
                                           "nenner", "anteil",
                                           "bruchteil"]},
                        "erstkontakt": {
                            "anker": "Eine Pizza wird in 8 Stücke "
                                     "geschnitten. Du bekommst 3. "
                                     "Welcher Teil der Pizza ist das?",
                            "benennung": "Brüche",
                            "erste_aufgabe": {"frage": "3 von 8 Teilen "
                                              "= welcher Bruch?",
                                              "loesung": "3/8"}},
                        "fehlertypen": [
                            {
                                "key": "zaehler_nenner_dreher",
                                "label": "Zähler und Nenner vertauscht",
                                "beschreibung": "Oben und unten werden "
                                "verwechselt — aus 3 von 8 wird 8/3 "
                                "statt 3/8.",
                                "antworten": ["8/3", "8/5"],
                                "erklaerung": {
                                    "haken": "Beim Bruch stehen zwei "
                                            "Zahlen — aber welche "
                                            "gehört wohin?",
                                    "erkenntnis": "Unten steht die "
                                    "Teilung: in wie viele gleiche "
                                    "Stücke das Ganze zerlegt ist. "
                                    "Oben steht, wie viele davon "
                                    "gemeint sind.",
                                    "regel": "Nenner unten = wie oft "
                                    "geteilt. Zähler oben = wie viele "
                                    "Teile zählen. 3 von 8 Stücken "
                                    "ist 3/8.",
                                    "bild": {"zeigt": "eine Pizza in "
                                             "8 Teilen, 3 davon "
                                             "markiert",
                                             "bewegt": "die 8 wandert "
                                             "nach unten, die 3 nach "
                                             "oben",
                                             "bleibt_gleich": "der "
                                             "Anteil ändert sich "
                                             "nicht"},
                                    "aufgabe": {"frage": "5 von 6 "
                                                "Kästchen sind rot — "
                                                "welcher Bruch?",
                                                "loesung": "5/6",
                                                "tipp": "Alle Teile "
                                                        "nach unten."}},
                                "visualisierung": _SCHRITTE(
                                    ["Pizza in 8 Teile geschnitten",
                                     "8 Teile insgesamt → Nenner unten",
                                     "3 markiert → Zähler oben",
                                     "Bruch: 3/8"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Position", "Bedeutung", "Wert"],
                                    ["oben (Zähler) | markierte Teile | 3",
                                     "unten (Nenner) | alle Teile | 8"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "4 von 9 Kästchen sind grau — "
                                        "welcher Bruch?",
                                        "4/9",
                                        ["9/4", "9/5"],
                                        "Alle Teile (9) stehen unten, "
                                        "die grauen (4) oben."),
                                    "beispiel": aufgabe(
                                        "Von 10 Kindern tragen 7 eine "
                                        "Mütze — als Bruch.",
                                        "7/10",
                                        schritte=["alle Kinder: 10 → Nenner",
                                                  "mit Mütze: 7 → Zähler",
                                                  "Bruch: 7/10"]),
                                    "gefuehrt": aufgabe(
                                        "Von 6 Blumen sind 5 gelb — "
                                        "als Bruch.", "5/6",
                                        fehler="6/5",
                                        tipps=["Wie viele Blumen insgesamt?",
                                               "Die Gesamtzahl steht unten."],
                                        schritte=["6 Blumen → Nenner 6",
                                                  "5 gelbe → Zähler 5",
                                                  "5/6"]),
                                    "selbststaendig": aufgabe(
                                        "3 von 12 Bonbons sind "
                                        "Schoko — als Bruch.", "3/12",
                                        fehler="12/3",
                                        tipps=["Was kommt nach "
                                               "unten?"]),
                                    "transfer": auswahl(
                                        "Warum kann „5 von 3 Teilen“ "
                                        "kein normaler Anteil sein?",
                                        "Man kann nicht mehr Teile "
                                        "nehmen, als das Ganze hat",
                                        ["Weil 5 zu groß ist",
                                         "Weil unten immer die "
                                         "kleinere Zahl steht"],
                                        "Der Nenner ist das Ganze — "
                                        "der Zähler kann es nicht "
                                        "übersteigen (bei echten "
                                        "Anteilen).")}},
                            {
                                "key": "grosser_nenner_irrtum",
                                "label": "Großer Nenner wirkt groß",
                                "beschreibung": "1/8 wirkt größer "
                                "als 1/4, weil 8 mehr ist als 4 — "
                                "die Stückgröße wird übersehen.",
                                "antworten": ["1/8 groesser",
                                              "1/8 > 1/4"],
                                "erklaerung": {
                                    "haken": "1/4 oder 1/8 — die 8 "
                                            "sieht größer aus als die "
                                            "4.",
                                    "erkenntnis": "Der Nenner sagt, "
                                    "in wie viele Stücke geteilt "
                                    "wird. In 8 Stücke geteilt ist "
                                    "jedes Stück KLEINER — du teilst "
                                    "durch mehr Leute.",
                                    "regel": "Gleicher Zähler: je "
                                    "größer der Nenner, desto "
                                    "kleiner der Bruch. 1/8 < 1/4.",
                                    "bild": {"zeigt": "zwei Kuchen: "
                                             "einer in 4, einer in "
                                             "8 Stücke — je ein "
                                             "Stück angemalt",
                                             "bewegt": "das "
                                             "Viertelstück ist "
                                             "doppelt so groß",
                                             "bleibt_gleich": "beide "
                                             "Kuchen sind gleich "
                                             "groß"},
                                    "aufgabe": {"frage": "Was ist "
                                                "größer: 1/3 "
                                                "oder 1/6?",
                                                "loesung": "1/3",
                                                "tipp": "Kleinere "
                                                        "Stücke "
                                                        "oder "
                                                        "größere?"}},
                                "visualisierung": _TABELLE(
                                    ["Bruch", "Stücke", "Stückgröße"],
                                    ["1/4 | 4 | groß",
                                     "1/8 | 8 | halb so groß",
                                     "Ergebnis | | 1/4 gewinnt"]),
                                "visualisierung_alternativ": _SCHRITTE(
                                    ["Ein Kuchen in 4 Teile → "
                                     "große Stücke",
                                     "Derselbe in 8 → halb so groß",
                                     "1/4 = 2/8",
                                     "also 1/4 > 1/8"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist größer: 1/3 "
                                        "oder 1/5?",
                                        "1/3",
                                        ["1/5", "gleich"],
                                        "Drei Stücke sind größer "
                                        "als fünf Stücke desselben "
                                        "Kuchens — 1/3 > 1/5."),
                                    "beispiel": aufgabe(
                                        "Wir vergleichen 1/2 und "
                                        "1/4 am Kuchenbild.",
                                        "1/2",
                                        schritte=["1/2: Kuchen halbiert",
                                                  "1/4: geviertelt",
                                                  "das halbe Stück ist doppelt so groß"]),
                                    "gefuehrt": aufgabe(
                                        "Was ist größer: 1/6 "
                                        "oder 1/10?", "1/6",
                                        fehler="1/10",
                                        tipps=["In wie viele Stücke wird jeweils geteilt?",
                                               "Mehr Stücke = kleinere Stücke."],
                                        schritte=["1/6: sechs Teile",
                                                  "1/10: zehn Teile",
                                                  "sechstel-Stücke sind größer"]),
                                    "selbststaendig": aufgabe(
                                        "Ordne aufsteigend: 1/8, "
                                        "1/3, 1/5", "1/8, 1/5, 1/3",
                                        fehler="1/3, 1/5, 1/8",
                                        tipps=["Größter Nenner = "
                                               "kleinstes Stück."]),
                                    "transfer": auswahl(
                                        "Zwei Kinder teilen sich "
                                        "Pizzen: eins bekommt 1/4, "
                                        "das andere 1/6. Welches "
                                        "bekommt mehr?",
                                        "Das mit 1/4 — weniger "
                                        "Teile heißt größere Stücke",
                                        ["Das mit 1/6 — 6 ist mehr",
                                         "Beide gleich viel"],
                                        "Bei gleichem Kuchen ist das "
                                        "Viertel größer als das "
                                        "Sechstel.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Unten steht das Teilen, oben "
                                    "das Nehmen: 3/8 heißt 3 von 8 "
                                    "Stücken.",
                            "RULE": "Gleicher Zähler? Dann gewinnt "
                                    "der kleinere Nenner — größere "
                                    "Stücke.",
                            "WORKED_EXAMPLE": "Zähle erst die "
                                    "Teile insgesamt, dann die "
                                    "markierten.",
                            "GUIDED_TASK": "Male den Bruch auf, "
                                    "bevor du ihn hinschreibst.",
                            "INDEPENDENT_TASK": "Frag dich: ist "
                                    "mein Bruch kleiner als 1? "
                                    "Dann muss oben weniger stehen "
                                    "als unten.",
                            "ADAPTATION": "Das Kuchenbild zeigt "
                                    "den Unterschied zwischen "
                                    "Teilen und Nehmen."}),
                        "faq": [
                            {"frage": "Was heißt der Strich im "
                                      "Bruch?",
                             "antwort": "Er bedeutet „geteilt“: "
                                        "3/8 ist 3 geteilt durch 8 "
                                        "— das Ganze auf 8, davon "
                                        "3 Teile."},
                            {"frage": "Kann oben mehr stehen als "
                                      "unten?",
                             "antwort": "Dann ist der „Anteil“ "
                                        "größer als ein Ganzes — das "
                                        "gibt es, aber bei "
                                        "Kuchenstücken ist es meist "
                                        "ein Schreibfehler."}],
                    }},
                # --------------------------------- Erweitern und Kürzen
                {
                    "id": "MA.BRUECHE.ERWEITERN_KUERZEN",
                    "title": "Brüche erweitern und kürzen",
                    "description": "Derselbe Anteil in anderer Form: "
                                   "Zähler und Nenner mit derselben "
                                   "Zahl malnehmen oder teilen.",
                    "first_contact_grade": 5, "target_grade": 6,
                    "prerequisites": ["MA.BRUECHE.BEGRIFF",
                                      "MA.ZAHLEN.EINMALEINS"],
                    "levels": {
                        "below": "K5: Bruch als Anteil verstehen",
                        "target": "K6: erweitern und kürzen, "
                                  "gleichwertige Brüche finden",
                        "above": "K6–7: Hauptnenner, vergleichen, "
                                 "rechnen"},
                    "can_do": {
                        "below": ["Einen Bruch als Anteil lesen"],
                        "target": ["Einen Bruch mit einer Zahl "
                                   "erweitern, vollständig kürzen "
                                   "und gleichwertige Brüche "
                                   "erkennen"],
                        "above": ["Brüche auf einen gemeinsamen "
                                  "Nenner bringen"]},
                    "difficulty_parameters": {
                        "faktoren": "2 bis 10", "nenner": "bis 60",
                        "ziel": "vollständig gekürzt"},
                    "anchor_items": [
                        item("Erweitere 2/3 mit 4.", "8/12",
                             level="target", grade=6,
                             answer=text("8/12")),
                        item("Kürze 6/8 vollständig.", "3/4",
                             level="target", grade=6,
                             answer=text("3/4"))],
                    "boundary_items": {
                        "below": [item("Welcher Bruch ist markiert: "
                                       "2 von 4 Kästchen?", "2/4",
                                       level="below", grade=5,
                                       answer=text("2/4"))],
                        "within": [item("Kürze 12/18 vollständig.",
                                        "2/3", level="target",
                                        grade=6, answer=text("2/3"))],
                        "above": [item("Was ist größer: 3/5 oder "
                                       "7/10?", "7/10",
                                       level="above", grade=6,
                                       answer=text("7/10"))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Statt "
                             "malzunehmen wird addiert: 2/3 "
                             "erweitert mit 4 wird zu 6/7 — oben "
                             "und unten plus 4.",
                             "remediation_hint": "Erweitern "
                             "vervielfacht die Stückzahl: Zähler "
                             "UND Nenner werden MAL derselben "
                             "Zahl genommen.",
                             "diagnostic_item": item(
                                 "Erweitere 2/3 mit 4.", "8/12",
                                 level="target", grade=6,
                                 answer=text("8/12"),
                                 distractors=[{"answer": "6/7",
                                               "misconception": "F1",
                                               "feedback": "Addieren verändert den Anteil — erweitern heißt mal 4, oben und unten."}])},
                            {"key": "F2", "description": "Es wird nur "
                             "eine Seite gekürzt: 6/8 wird zu 3/8 — "
                             "nur der Zähler wurde geteilt.",
                             "remediation_hint": "Kürzen teilt "
                             "beide Seiten durch denselben "
                             "Teiler — der Wert darf sich nicht "
                             "ändern.",
                             "diagnostic_item": item(
                                 "Kürze 6/8 vollständig.", "3/4",
                                 level="target", grade=6,
                                 answer=text("3/4"),
                                 distractors=[{"answer": "3/8",
                                               "misconception": "F2",
                                               "feedback": "Nur der Zähler wurde geteilt — der Nenner muss denselben Schritt mitmachen."}])}],
                        "diagnostic_items": [
                            item("1/2 = ?/4", "2/4", level="below",
                                 grade=5, answer=text("2/4")),
                            item("Erweitere 3/5 mit 3.", "9/15",
                                 level="target", grade=6,
                                 answer=text("9/15"))],
                        "exit_items": [
                            item("Kürze 20/30 vollständig.", "2/3",
                                 level="target", grade=6,
                                 answer=text("2/3")),
                            item("Erweitere 5/6 auf 24er-Nenner.",
                                 "20/24", level="target", grade=6,
                                 answer=text("20/24"))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "erweitern_kuerzen",
                            "thema_key": "brueche",
                            "label": "Erweitern und Kürzen",
                            "klasse_von": 5, "klasse_bis": 7,
                            "stichworte": ["erweitern", "kürzen",
                                           "brüche erweitern",
                                           "gleichwertige brüche",
                                           "brüche kürzen"]},
                        "erstkontakt": {
                            "anker": "Eine Pizza in 4 Stücke, du "
                                     "bekommst 2. Dieselbe Pizza in "
                                     "8 Stücke — wie viele "
                                     "bekommst du für denselben "
                                     "Anteil?",
                            "benennung": "Erweitern und Kürzen",
                            "erste_aufgabe": {"frage": "2/4 = ?/8",
                                              "loesung": "4/8"}},
                        "fehlertypen": [
                            {
                                "key": "addiert_statt_mal",
                                "label": "Addiert statt multipliziert",
                                "beschreibung": "Beim Erweitern wird "
                                "die Zahl oben und unten addiert — "
                                "der Anteil verändert sich dabei.",
                                "antworten": ["6/7", "5/6"],
                                "erklaerung": {
                                    "haken": "2/3 erweitern mit 4: "
                                            "2 + 4 und 3 + 4 gibt "
                                            "6/7 — aber ist das "
                                            "noch derselbe Anteil?",
                                    "erkenntnis": "Erweitern "
                                    "verfeinert die Stücke: jedes "
                                    "Stück wird in 4 kleinere "
                                    "geschnitten. Aus 2 Teilen "
                                    "werden 8, aus 3 werden 12 — "
                                    "beides mal 4.",
                                    "regel": "Erweitern = Zähler "
                                    "und Nenner MAL dieselbe Zahl. "
                                    "Der Wert bleibt gleich, die "
                                    "Stücke werden kleiner und "
                                    "mehr.",
                                    "bild": {"zeigt": "ein "
                                             "Drittel-Kuchen, dessen "
                                             "Stücke geviertelt "
                                             "werden",
                                             "bewegt": "jedes "
                                             "Stück zerfällt in 4 — "
                                             "Stückzahl mal 4",
                                             "bleibt_gleich": "der "
                                             "Anteil am Ganzen "
                                             "bleibt gleich"},
                                    "aufgabe": {"frage": "Erweitere "
                                                "1/2 mit 5.",
                                                "loesung": "5/10",
                                                "tipp": "Oben mal 5, "
                                                        "unten mal 5."}},
                                "visualisierung": _SCHRITTE(
                                    ["2/3: 2 von 3 Stücken",
                                     "jedes Stück in 4 schneiden",
                                     "2 · 4 = 8 Teile markiert",
                                     "3 · 4 = 12 Teile gesamt",
                                     "2/3 = 8/12"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Operation", "Zähler", "Nenner",
                                     "Ergebnis"],
                                    ["mal 4 | 2·4=8 | 3·4=12 | 8/12",
                                     "plus 4 | 2+4=6 | 3+4=7 | 6/7 ✗"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Erweitere 2/3 mit 4.",
                                        "8/12",
                                        ["6/7", "8/9"],
                                        "Oben und unten mal 4: "
                                        "2·4=8, 3·4=12 — der Anteil "
                                        "bleibt gleich."),
                                    "beispiel": aufgabe(
                                        "Wir erweitern 3/4 mit 2: "
                                        "beide Seiten malnehmen.",
                                        "6/8",
                                        schritte=["3 · 2 = 6",
                                                  "4 · 2 = 8",
                                                  "3/4 = 6/8"]),
                                    "gefuehrt": aufgabe(
                                        "Erweitere 2/5 mit 3.",
                                        "6/15",
                                        fehler="5/8",
                                        tipps=["Nicht addieren — malnehmen.",
                                               "2 · 3 und 5 · 3."],
                                        schritte=["2 · 3 = 6",
                                                  "5 · 3 = 15",
                                                  "6/15"]),
                                    "selbststaendig": aufgabe(
                                        "Erweitere 4/7 mit 2.",
                                        "8/14",
                                        fehler="6/9",
                                        tipps=["Beide Seiten mal 2."]),
                                    "transfer": auswahl(
                                        "Warum bleibt beim "
                                        "Erweitern der Wert gleich?",
                                        "Stücke werden kleiner UND "
                                        "mehr — das gleicht sich "
                                        "aus",
                                        ["Weil man addiert",
                                         "Der Wert ändert sich "
                                         "eben doch"],
                                        "4 mal so kleine Stücke, "
                                        "aber 4 mal so viele — der "
                                        "Anteil ändert sich "
                                        "nicht.")}},
                            {
                                "key": "einseitig_gekuerzt",
                                "label": "Nur eine Seite gekürzt",
                                "beschreibung": "Beim Kürzen wird "
                                "nur Zähler ODER Nenner geteilt — "
                                "der Bruch verändert seinen Wert.",
                                "antworten": ["3/8", "6/4"],
                                "erklaerung": {
                                    "haken": "6/8 kürzen: die 6 "
                                            "durch 2 teilen gibt "
                                            "3/8 — aber stimmt der "
                                            "Anteil noch?",
                                    "erkenntnis": "Kürzen packt "
                                    "Stücke zusammen: immer 2 zu "
                                    "einem. Aus 6 markierten "
                                    "werden 3, aus 8 gesamten "
                                    "werden 4 — beides geteilt "
                                    "durch 2.",
                                    "regel": "Kürzen = Zähler und "
                                    "Nenner DURCH dieselbe Zahl "
                                    "teilen. Nur gemeinsame "
                                    "Teiler kürzen den Bruch, "
                                    "nicht den Wert.",
                                    "bild": {"zeigt": "6 von 8 "
                                             "Kästchen, paarweise "
                                             "zusammengefasst",
                                             "bewegt": "6 Kästchen "
                                             "werden 3 Gruppen, 8 "
                                             "werden 4 Gruppen",
                                             "bleibt_gleich": "der "
                                             "markierte Anteil "
                                             "bleibt"},
                                    "aufgabe": {"frage": "Kürze "
                                                "10/15 "
                                                "vollständig.",
                                                "loesung": "2/3",
                                                "tipp": "Beide "
                                                        "durch 5."}},
                                "visualisierung": _SCHRITTE(
                                    ["6/8: 6 markiert, 8 gesamt",
                                     "gemeinsamer Teiler: 2",
                                     "6 : 2 = 3",
                                     "8 : 2 = 4",
                                     "6/8 = 3/4"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Versuch", "Zähler", "Nenner",
                                     "Wert gleich?"],
                                    [":2 nur oben | 3 | 8 | nein",
                                     ":2 beide | 3 | 4 | ja"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Kürze 6/8 vollständig.",
                                        "3/4",
                                        ["3/8", "6/4"],
                                        "Beide Seiten durch 2: "
                                        "3 und 4 — nur eine Seite "
                                        "zu teilen verändert den "
                                        "Bruch."),
                                    "beispiel": aufgabe(
                                        "Wir kürzen 10/15: "
                                        "gemeinsamer Teiler ist 5.",
                                        "2/3",
                                        schritte=["10 : 5 = 2",
                                                  "15 : 5 = 3",
                                                  "10/15 = 2/3"]),
                                    "gefuehrt": aufgabe(
                                        "Kürze 12/16 "
                                        "vollständig.", "3/4",
                                        fehler="12/8",
                                        tipps=["Welcher Teiler passt in 12 UND 16?",
                                               "Beide durch 4."],
                                        schritte=["12 : 4 = 3",
                                                  "16 : 4 = 4",
                                                  "3/4"]),
                                    "selbststaendig": aufgabe(
                                        "Kürze 14/21 "
                                        "vollständig.", "2/3",
                                        fehler="14/3",
                                        tipps=["Welche Zahl teilt "
                                               "14 und 21?"]),
                                    "transfer": auswahl(
                                        "Warum kann man 5/8 nicht "
                                        "durch 2 kürzen?",
                                        "Die 5 ist nicht durch 2 "
                                        "teilbar — es fehlt der "
                                        "gemeinsame Teiler",
                                        ["Weil 8 zu groß ist",
                                         "Kürzen geht immer"],
                                        "Kürzen braucht einen "
                                        "Teiler, der in BEIDE "
                                        "Zahlen passt — sonst "
                                        "verändert sich der "
                                        "Wert.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Stell dir vor, du schneidest "
                                    "jedes Stück nochmal kleiner — "
                                    "mehr Stücke, gleicher "
                                    "Anteil.",
                            "RULE": "Erweitern: oben und unten "
                                    "mal dieselbe Zahl. Kürzen: "
                                    "durch dieselbe Zahl teilen.",
                            "WORKED_EXAMPLE": "Schau, was mit "
                                    "Zähler UND Nenner passiert — "
                                    "beide machen denselben "
                                    "Schritt.",
                            "GUIDED_TASK": "Such erst den "
                                    "gemeinsamen Teiler, bevor du "
                                    "kürzt.",
                            "INDEPENDENT_TASK": "Prüfe: hat sich "
                                    "der Wert geändert? Zur Probe "
                                    "kannst du zurückrechnen.",
                            "ADAPTATION": "Die Tabelle zeigt, "
                                    "warum addieren den Anteil "
                                    "verändert und malnehmen "
                                    "nicht."}),
                        "faq": [
                            {"frage": "Wann ist ein Bruch "
                                      "vollständig gekürzt?",
                             "antwort": "Wenn Zähler und Nenner "
                                        "keinen gemeinsamen "
                                        "Teiler mehr haben — bei "
                                        "3/4 geht nichts mehr."},
                            {"frage": "Warum darf ich kürzen?",
                             "antwort": "Kürzen packt Stücke "
                                        "zusammen: aus 6/8 kleinen "
                                        "werden 3/4 größere — "
                                        "derselbe Anteil in "
                                        "gröberer Teilung."}],
                    }},
                # ------------------------------- gleichnamige Addition
                {
                    "id": "MA.BRUECHE.GLEICHN_ADD",
                    "title": "Gleichnamige Brüche addieren",
                    "description": "Brüche mit gleichem Nenner "
                                   "addieren und subtrahieren: die "
                                   "Zähler rechnen, der Nenner "
                                   "bleibt.",
                    "first_contact_grade": 5, "target_grade": 6,
                    "prerequisites": ["MA.BRUECHE.BEGRIFF"],
                    "levels": {
                        "below": "K5: Bruch als Anteil",
                        "target": "K6: gleichnamige Brüche "
                                  "addieren und subtrahieren",
                        "above": "K6: ungleichnamige Brüche, "
                                 "gemischte Zahlen"},
                    "can_do": {
                        "below": ["Einen Bruch als Anteil "
                                  "darstellen"],
                        "target": ["3/8 + 2/8 oder 7/10 - 3/10 "
                                   "sicher rechnen und das "
                                   "Ergebnis als Bruch "
                                   "angeben"],
                        "above": ["Ungleichnamige Brüche "
                                  "addieren"]},
                    "difficulty_parameters": {
                        "nenner": "bis 12, gleich",
                        "ergebnis": "auch größer als 1",
                        "kuerzen": "Ergebnis darf gekürzt "
                                   "werden"},
                    "anchor_items": [
                        item("Rechne: 3/8 + 2/8", "5/8",
                             level="target", grade=6,
                             answer=text("5/8")),
                        item("Rechne: 7/10 - 3/10", "4/10",
                             level="target", grade=6,
                             answer=text("4/10", "2/5"))],
                    "boundary_items": {
                        "below": [item("Welcher Bruch: 2 von "
                                       "4 Kästchen?", "2/4",
                                       level="below", grade=5,
                                       answer=text("2/4"))],
                        "within": [item("Rechne: 5/6 - 1/6",
                                        "4/6", level="target",
                                        grade=6,
                                        answer=text("4/6", "2/3"))],
                        "above": [item("Rechne: 1/2 + 1/4",
                                       "3/4", level="above",
                                       grade=6,
                                       answer=text("3/4"))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Der Nenner "
                             "wird mitaddiert: 3/8 + 2/8 wird zu "
                             "5/16 — die Stückgröße wird "
                             "verändert.",
                             "remediation_hint": "Der Nenner "
                             "benennt die Stückgröße — er bleibt. "
                             "Nur die Zähler zählen die Stücke "
                             "zusammen.",
                             "diagnostic_item": item(
                                 "Rechne: 3/8 + 2/8", "5/8",
                                 level="target", grade=6,
                                 answer=text("5/8"),
                                 distractors=[{"answer": "5/16",
                                               "misconception": "F1",
                                               "feedback": "Die Stücke bleiben Achtel — nur ihre Anzahl wächst: 5/8."}])},
                            {"key": "F2", "description": "Ein "
                             "Ergebnis über 1 wirkt falsch: "
                             "7/8 + 3/8 = 10/8 wird nicht "
                             "getraut, weil „oben mehr als unten "
                             "nicht geht“.",
                             "remediation_hint": "10/8 sind 8 "
                             "Achtel (= 1 Ganzes) plus 2 Achtel — "
                             "das darf sein.",
                             "diagnostic_item": item(
                                 "Rechne: 5/8 + 4/8", "9/8",
                                 level="target", grade=6,
                                 answer=text("9/8", "1 1/8"),
                                 distractors=[{"answer": "9/16",
                                               "misconception": "F2",
                                               "feedback": "9 Achtel sind mehr als ein Ganzes — das ist erlaubt: 9/8."}])}],
                        "diagnostic_items": [
                            item("Rechne: 1/4 + 2/4", "3/4",
                                 level="below", grade=5,
                                 answer=text("3/4")),
                            item("Rechne: 4/9 + 3/9", "7/9",
                                 level="target", grade=6,
                                 answer=text("7/9"))],
                        "exit_items": [
                            item("Rechne: 5/12 + 4/12", "9/12",
                                 level="target", grade=6,
                                 answer=text("9/12", "3/4")),
                            item("Rechne: 1 - 3/7", "4/7",
                                 level="target", grade=6,
                                 answer=text("4/7"))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "gleichnamig_add",
                            "thema_key": "brueche",
                            "label": "Gleichnamige Brüche "
                                     "addieren",
                            "klasse_von": 5, "klasse_bis": 7,
                            "stichworte": ["brüche addieren",
                                           "gleichnamig",
                                           "bruchrechnen",
                                           "brüche subtrahieren"]},
                        "erstkontakt": {
                            "anker": "Du isst 3/8 einer Pizza, "
                                     "dein Bruder 2/8. Wie viel "
                                     "Pizza ist zusammen weg?",
                            "benennung": "Gleichnamige "
                                         "Brüche addieren",
                            "erste_aufgabe": {"frage": "3/8 + "
                                              "2/8 = ?",
                                              "loesung": "5/8"}},
                        "fehlertypen": [
                            {
                                "key": "nenner_mitgerechnet",
                                "label": "Nenner mitaddiert",
                                "beschreibung": "Oben plus oben "
                                "und unten plus unten — aus "
                                "Achteln werden Sechzehntel, die "
                                "Stücke schrumpfen mitten in "
                                "der Rechnung.",
                                "antworten": ["5/16", "6/16"],
                                "erklaerung": {
                                    "haken": "3/8 + 2/8: Wer "
                                            "oben UND unten "
                                            "addiert, bekommt "
                                            "5/16 — und die "
                                            "Stücke werden "
                                            "heimlich kleiner.",
                                    "erkenntnis": "Der Nenner "
                                    "sagt nur, WIE GROSS die "
                                    "Stücke sind: Achtel bleiben "
                                    "Achtel. Was sich ändert, "
                                    "ist die ANZAHL — und die "
                                    "steht oben.",
                                    "regel": "Bei gleichem "
                                    "Nenner: Zähler addieren, "
                                    "Nenner behalten. "
                                    "3/8 + 2/8 = 5/8.",
                                    "bild": {"zeigt": "3 "
                                             "Achtel-Stücke und "
                                             "2 Achtel-Stücke "
                                             "werden "
                                             "zusammengelegt",
                                             "bewegt": "5 "
                                             "gleich große "
                                             "Achtel liegen "
                                             "zusammen",
                                             "bleibt_gleich": "die "
                                             "Stückgröße — "
                                             "Achtel bleibt "
                                             "Achtel"},
                                    "aufgabe": {"frage": "4/9 "
                                                "+ 3/9 = ?",
                                                "loesung": "7/9",
                                                "tipp": "Nur "
                                                        "oben "
                                                        "rechnen."}},
                                "visualisierung": _SCHRITTE(
                                    ["3 Achtel + 2 Achtel",
                                     "gleiche Stückgröße",
                                     "3 + 2 = 5 Stücke",
                                     "Ergebnis: 5/8 — Nenner "
                                     "bleibt 8"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Rechnung", "Zähler", "Nenner"],
                                    ["3/8 + 2/8 | 3+2=5 | bleibt 8",
                                     "falsch: 5/16 | 5 ✓ | 8+8=16 ✗"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist 3/8 + 2/8?",
                                        "5/8",
                                        ["5/16", "6/8"],
                                        "Achtel bleiben Achtel: "
                                        "nur die Anzahl wächst "
                                        "auf 5."),
                                    "beispiel": aufgabe(
                                        "Wir rechnen 2/7 + 4/7: "
                                        "die Stücke zusammenzählen, "
                                        "die Größe behalten.",
                                        "6/7",
                                        schritte=["2 + 4 = 6 Stücke",
                                                  "Siebtel bleiben Siebtel",
                                                  "Ergebnis: 6/7"]),
                                    "gefuehrt": aufgabe(
                                        "5/12 + 4/12 = ?", "9/12",
                                        fehler="9/24",
                                        tipps=["Was macht der Nenner beim Addieren?",
                                               "Zwölftel bleiben Zwölftel."],
                                        schritte=["5 + 4 = 9",
                                                  "Nenner bleibt 12",
                                                  "9/12"]),
                                    "selbststaendig": aufgabe(
                                        "7/15 + 4/15 = ?", "11/15",
                                        fehler="11/30",
                                        tipps=["Der Nenner zählt "
                                               "nicht mit."]),
                                    "transfer": auswahl(
                                        "Warum wird der Nenner "
                                        "beim Addieren nicht "
                                        "mitaddiert?",
                                        "Weil er nur die "
                                        "Stückgröße nennt — "
                                        "Achtel bleiben Achtel",
                                        ["Weil unten immer die "
                                         "gleiche Zahl stehen muss",
                                         "Das ist einfach die Regel"],
                                        "Der Nenner ist ein "
                                        "Einheitsname wie „cm“: "
                                        "3 cm + 2 cm sind 5 cm, "
                                        "nicht 5 „cmcm“.")}},
                            {
                                "key": "ueber_eins_scheu",
                                "label": "Angst vor Ergebnissen "
                                         "über 1",
                                "beschreibung": "Oben größer als "
                                "unten wirkt verboten — Ergebnisse "
                                "wie 9/8 werden „korrigiert“ oder "
                                "abgelehnt.",
                                "antworten": ["geht nicht",
                                              "9/16"],
                                "erklaerung": {
                                    "haken": "5/8 + 4/8 = 9/8 — "
                                            "oben mehr als unten, "
                                            "darf das sein?",
                                    "erkenntnis": "9 Achtel sind "
                                    "8 Achtel (= 1 Ganzes) plus 1 "
                                    "Achtel. Mehr als ein Ganzes "
                                    "ist kein Fehler — die Pizza "
                                    "reicht einfach nicht.",
                                    "regel": "Übersteigt der "
                                    "Zähler den Nenner, enthält "
                                    "das Ergebnis ein Ganzes "
                                    "oder mehr — schreib es als "
                                    "unechten Bruch oder "
                                    "gemischte Zahl.",
                                    "bild": {"zeigt": "9 "
                                             "Achtelstücke: ein "
                                             "voller Kuchen plus "
                                             "1 Stück",
                                             "bewegt": "8 Stücke "
                                             "schließen sich zum "
                                             "Ganzen, 1 bleibt "
                                             "über",
                                             "bleibt_gleich": "9 "
                                             "Achtel bleiben "
                                             "9/8 = 1 1/8"},
                                    "aufgabe": {"frage": "6/8 + "
                                                "5/8 = ?",
                                                "loesung": "11/8",
                                                "tipp": "11 "
                                                        "Achtel — "
                                                        "ein "
                                                        "Ganzes "
                                                        "ist "
                                                        "dabei."}},
                                "visualisierung": _SCHRITTE(
                                    ["5/8 + 4/8",
                                     "5 + 4 = 9 Achtel",
                                     "8 Achtel = 1 Ganzes",
                                     "9/8 = 1 1/8"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Achtel", "Bedeutung"],
                                    ["8/8 | ein Ganzes",
                                     "9/8 | ein Ganzes + 1 Stück",
                                     "Ergebnis | 9/8 = 1 1/8"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist 5/8 + 4/8?",
                                        "9/8",
                                        ["9/16", "geht nicht"],
                                        "9 Achtel sind ein "
                                        "Ganzes plus ein Achtel "
                                        "— das darf sein."),
                                    "beispiel": aufgabe(
                                        "Wir rechnen 7/8 + 3/8 "
                                        "und zerlegen das "
                                        "Ergebnis.",
                                        "10/8",
                                        schritte=["7 + 3 = 10 Achtel",
                                                  "10/8 = 8/8 + 2/8",
                                                  "= 1 2/8"]),
                                    "gefuehrt": aufgabe(
                                        "6/8 + 5/8 = ?", "11/8",
                                        fehler="geht nicht",
                                        tipps=["11 Achtel — mehr als ein Ganzes ist erlaubt.",
                                               "8 davon bilden eine ganze Pizza."],
                                        schritte=["6 + 5 = 11",
                                                  "11/8",
                                                  "= 1 3/8"]),
                                    "selbststaendig": aufgabe(
                                        "9/10 + 4/10 = ?", "13/10",
                                        fehler="13/20",
                                        tipps=["Zähler addieren, "
                                               "Nenner behalten."]),
                                    "transfer": auswahl(
                                        "Zwei Pizzen wurden "
                                        "angebissen: vom ersten "
                                        "fehlt 5/8, vom zweiten "
                                        "fehlt 7/8. Wie viel "
                                        "Pizza fehlt insgesamt?",
                                        "12/8 — das ist "
                                        "anderthalb Pizzen",
                                        ["12/16", "Das geht nicht, nur eine Pizza"],
                                        "Beide fehlenden Teile "
                                        "zusammen sind 12 "
                                        "Achtel — mehr als eine "
                                        "ganze Pizza.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Achtel plus Achtel bleibt "
                                    "Achtel — nur die Anzahl "
                                    "wächst.",
                            "RULE": "Gleicher Nenner: Zähler "
                                    "addieren (oder "
                                    "subtrahieren), Nenner "
                                    "stehen lassen.",
                            "WORKED_EXAMPLE": "Achte auf den "
                                    "Nenner: verändert er sich "
                                    "in den Beispielen?",
                            "GUIDED_TASK": "Schreib den Nenner "
                                    "zuerst ins Ergebnis — dann "
                                    "rechne oben.",
                            "INDEPENDENT_TASK": "Über 1 ist "
                                    "erlaubt: prüfe nur, ob "
                                    "oben und unten richtig "
                                    "stehen.",
                            "ADAPTATION": "Die Tabelle zeigt "
                                    "den falsch mitaddierten "
                                    "Nenner im Vergleich."}),
                        "faq": [
                            {"frage": "Warum bleibt der Nenner "
                                      "gleich?",
                             "antwort": "Der Nenner ist wie eine "
                                        "Einheit: 3 Achtel + 2 "
                                        "Achtel sind 5 Achtel — "
                                        "wie 3 cm + 2 cm = 5 cm."},
                            {"frage": "Darf oben mehr stehen "
                                      "als unten?",
                             "antwort": "Ja — dann enthält das "
                                        "Ergebnis mindestens ein "
                                        "Ganzes. 10/8 sind 1 "
                                        "Ganze und 2 Achtel."}],
                    }},
                # ----------------------------- ungleichnamige Addition
                {
                    "id": "MA.BRUECHE.ADD_UNGL",
                    "title": "Ungleichnamige Brüche addieren",
                    "description": "Brüche mit verschiedenen "
                                   "Nennern addieren: erst "
                                   "gleichnamig machen, dann die "
                                   "Zähler rechnen.",
                    "first_contact_grade": 5, "target_grade": 6,
                    "prerequisites": ["MA.BRUECHE.ERWEITERN_KUERZEN",
                                      "MA.BRUECHE.GLEICHN_ADD"],
                    "levels": {
                        "below": "K6: gleichnamige Brüche, "
                                 "erweitern",
                        "target": "K6: ungleichnamige Brüche "
                                  "addieren und subtrahieren",
                        "above": "K7: Brüche multiplizieren und "
                                 "dividieren"},
                    "can_do": {
                        "below": ["Brüche erweitern und "
                                  "gleichnamige addieren"],
                        "target": ["1/2 + 1/3 über den "
                                   "Hauptnenner rechnen und "
                                   "das Ergebnis kürzen"],
                        "above": ["Brüche malnehmen und "
                                  "teilen"]},
                    "difficulty_parameters": {
                        "nenner": "bis 12, Hauptnenner direkt "
                                  "oder einfach",
                        "kuerzen": "Ergebnis soll gekürzt "
                                   "werden"},
                    "anchor_items": [
                        item("Rechne: 1/2 + 1/4", "3/4",
                             level="target", grade=6,
                             answer=text("3/4")),
                        item("Rechne: 1/2 + 1/3", "5/6",
                             level="target", grade=6,
                             answer=text("5/6"))],
                    "boundary_items": {
                        "below": [item("Rechne: 2/6 + 3/6", "5/6",
                                       level="below", grade=6,
                                       answer=text("5/6"))],
                        "within": [item("Rechne: 1/3 + 1/6",
                                        "3/6", level="target",
                                        grade=6,
                                        answer=text("3/6", "1/2"))],
                        "above": [item("Rechne: 2/3 + 3/4",
                                       "17/12", level="above",
                                       grade=7,
                                       answer=text("17/12", "1 5/12"))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Der "
                             "Quer-Additions-Fehler: 1/2 + 1/3 "
                             "wird zu 2/5 — Zähler plus Zähler, "
                             "Nenner plus Nenner, ohne die "
                             "Stückgrößen anzugleichen.",
                             "remediation_hint": "Verschiedene "
                             "Stückgrößen kann man nicht "
                             "zählen — erst auf den "
                             "gemeinsamen Nenner bringen.",
                             "diagnostic_item": item(
                                 "Rechne: 1/2 + 1/3", "5/6",
                                 level="target", grade=6,
                                 answer=text("5/6"),
                                 distractors=[{"answer": "2/5",
                                               "misconception": "F1",
                                               "feedback": "Hälften und Drittel sind verschiedene Stücke — erst auf Sechstel bringen."}])},
                            {"key": "F2", "description": "Nur ein "
                             "Bruch wird erweitert oder der "
                             "Hauptnenner falsch gewählt: "
                             "1/2 + 1/4 wird zu 2/6 statt "
                             "2/4 + 1/4.",
                             "remediation_hint": "Der "
                             "gemeinsame Nenner muss ein "
                             "Vielfaches beider Nenner sein — "
                             "und beide Brüche werden "
                             "umgewandelt.",
                             "diagnostic_item": item(
                                 "Rechne: 1/3 + 1/6", "3/6",
                                 level="target", grade=6,
                                 answer=text("3/6", "1/2"),
                                 distractors=[{"answer": "2/6",
                                               "misconception": "F2",
                                               "feedback": "Die 1/3 muss auch umgewandelt werden: 1/3 = 2/6, dann 2/6 + 1/6."}])}],
                        "diagnostic_items": [
                            item("Rechne: 1/4 + 2/4", "3/4",
                                 level="below", grade=6,
                                 answer=text("3/4")),
                            item("Rechne: 1/2 + 1/6", "4/6",
                                 level="target", grade=6,
                                 answer=text("4/6", "2/3"))],
                        "exit_items": [
                            item("Rechne: 2/5 + 1/10", "5/10",
                                 level="target", grade=6,
                                 answer=text("5/10", "1/2")),
                            item("Rechne: 3/4 - 1/8", "5/8",
                                 level="target", grade=6,
                                 answer=text("5/8"))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "add_ungleichnamig",
                            "thema_key": "brueche",
                            "label": "Ungleichnamige Brüche "
                                     "addieren",
                            "klasse_von": 5, "klasse_bis": 7,
                            "stichworte": ["ungleichnamige "
                                           "brüche",
                                           "brüche addieren",
                                           "hauptnenner",
                                           "gleichnamig "
                                           "machen"]},
                        "erstkontakt": {
                            "anker": "Du isst 1/2 einer Pizza, "
                                     "deine Schwester 1/4. "
                                     "Wie viel Pizza ist "
                                     "zusammen weg?",
                            "benennung": "Ungleichnamige "
                                         "Brüche addieren",
                            "erste_aufgabe": {"frage": "1/2 + "
                                              "1/4 = ?",
                                              "loesung": "3/4"}},
                        "fehlertypen": [
                            {
                                "key": "quer_addiert",
                                "label": "Zähler und Nenner "
                                         "„quer“ addiert",
                                "beschreibung": "Oben plus oben, "
                                "unten plus unten: 1/2 + 1/3 "
                                "wird zu 2/5 — die "
                                "Stückgrößen werden "
                                "ignoriert.",
                                "antworten": ["2/5", "2/6"],
                                "erklaerung": {
                                    "haken": "1/2 + 1/3 = 2/5? "
                                            "Das Ergebnis ist "
                                            "kleiner als jede "
                                            "der beiden "
                                            "Portionen!",
                                    "erkenntnis": "Hälften und "
                                    "Drittel sind "
                                    "verschiedene "
                                    "Stückgrößen — die kann "
                                    "man nicht zählen wie "
                                    "Äpfel und Birnen "
                                    "durcheinander. Erst "
                                    "umwandeln: 1/2 = 3/6 "
                                    "und 1/3 = 2/6.",
                                    "regel": "Bei "
                                    "ungleichnamigen "
                                    "Brüchen: erst auf den "
                                    "gemeinsamen Nenner "
                                    "erweitern, dann die "
                                    "Zähler addieren, "
                                    "Nenner behalten.",
                                    "bild": {"zeigt": "eine "
                                             "halbe und eine "
                                             "drittel "
                                             "Pizza, "
                                             "beide in "
                                             "Sechstel "
                                             "zerschnitten",
                                             "bewegt": "3 "
                                             "Sechstel + 2 "
                                             "Sechstel "
                                             "werden 5 "
                                             "Sechstel",
                                             "bleibt_gleich": "die "
                                             "Portionen "
                                             "ändern nur "
                                             "ihre Form"},
                                    "aufgabe": {"frage": "1/2 "
                                                "+ 1/6 = ?",
                                                "loesung": "4/6",
                                                "tipp": "Auf "
                                                        "Sechstel "
                                                        "bringen."}},
                                "visualisierung": _SCHRITTE(
                                    ["1/2 und 1/3 — "
                                     "verschiedene Stücke",
                                     "1/2 = 3/6",
                                     "1/3 = 2/6",
                                     "3/6 + 2/6 = 5/6"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Bruch", "auf Sechstel",
                                     "Zähler"],
                                    ["1/2 | ·3 | 3/6",
                                     "1/3 | ·2 | 2/6",
                                     "Summe | | 5/6"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist 1/2 + 1/3?",
                                        "5/6",
                                        ["2/5", "2/6"],
                                        "Erst Sechstel: "
                                        "3/6 + 2/6 = 5/6 — "
                                        "2/5 wäre kleiner "
                                        "als beide Teile!"),
                                    "beispiel": aufgabe(
                                        "Wir rechnen 1/2 + "
                                        "1/4: auf Viertel "
                                        "bringen, dann "
                                        "addieren.",
                                        "3/4",
                                        schritte=["1/2 = 2/4",
                                                  "2/4 + 1/4",
                                                  "= 3/4"]),
                                    "gefuehrt": aufgabe(
                                        "1/3 + 1/6 = ?", "3/6",
                                        fehler="2/9",
                                        tipps=["Sechstel ist der gemeinsame Nenner.",
                                               "1/3 wird zu wie viel Sechsteln?"],
                                        schritte=["1/3 = 2/6",
                                                  "2/6 + 1/6",
                                                  "= 3/6 = 1/2"]),
                                    "selbststaendig": aufgabe(
                                        "2/5 + 1/10 = ?", "5/10",
                                        fehler="3/15",
                                        tipps=["Zehntel als "
                                               "gemeinsamen "
                                               "Nenner."]),
                                    "transfer": auswahl(
                                        "Warum ist 2/5 als "
                                        "Ergebnis von "
                                        "1/2 + 1/3 sofort "
                                        "verdächtig?",
                                        "Es ist kleiner als "
                                        "die 1/2, die "
                                        "hineingesteckt "
                                        "wurde",
                                        ["Weil 5 ungerade ist",
                                         "Es ist doch richtig"],
                                        "Eine Halbe plus "
                                        "irgendwas muss "
                                        "größer sein als "
                                        "eine Halbe — 2/5 "
                                        "ist kleiner.")}},
                            {
                                "key": "hauptnenner_fehlt",
                                "label": "Nur einen Bruch "
                                         "umgewandelt",
                                "beschreibung": "Beim "
                                "Gleichnamig-Machen wird ein "
                                "Bruch vergessen oder ein "
                                "falscher gemeinsamer Nenner "
                                "gewählt — die Bilanz stimmt "
                                "nicht.",
                                "antworten": ["2/6", "1/9"],
                                "erklaerung": {
                                    "haken": "1/3 + 1/6: die "
                                            "1/6 passt schon "
                                            "— aber was ist "
                                            "mit der 1/3?",
                                    "erkenntnis": "Beide "
                                    "Brüche brauchen den "
                                    "gemeinsamen Nenner. Die "
                                    "1/6 hat ihn schon, die "
                                    "1/3 muss erweitert "
                                    "werden: 1/3 = 2/6.",
                                    "regel": "Der gemeinsame "
                                    "Nenner ist ein "
                                    "Vielfaches beider "
                                    "Nenner. JEDER Bruch "
                                    "wird auf ihn gebracht "
                                    "— dann erst "
                                    "addieren.",
                                    "bild": {"zeigt": "1/3 "
                                             "wird in zwei "
                                             "Sechstel "
                                             "zerschnitten, "
                                             "die 1/6 bleibt",
                                             "bewegt": "beide "
                                             "Portionen "
                                             "liegen als "
                                             "Sechstel "
                                             "vor",
                                             "bleibt_gleich": "die "
                                             "Anteile "
                                             "bleiben, nur "
                                             "die Form "
                                             "ändert sich"},
                                    "aufgabe": {"frage": "1/4 "
                                                "+ 1/8 = ?",
                                                "loesung": "3/8",
                                                "tipp": "Achtel "
                                                        "für "
                                                        "beide."}},
                                "visualisierung": _SCHRITTE(
                                    ["1/3 + 1/6: gemeinsamer "
                                     "Nenner 6",
                                     "1/3 = 2/6 (erweitern)",
                                     "1/6 = 1/6 (bleibt)",
                                     "2/6 + 1/6 = 3/6 = 1/2"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Schritt", "1/3", "1/6"],
                                    ["Nenner finden | →6 | →6",
                                     "umwandeln | 2/6 | 1/6",
                                     "addieren | 3/6 | = 1/2"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist 1/3 + 1/6?",
                                        "3/6",
                                        ["2/6", "2/9"],
                                        "Die 1/3 wird zu 2/6 "
                                        "— erst dann: 2/6 + "
                                        "1/6 = 3/6."),
                                    "beispiel": aufgabe(
                                        "Wir rechnen 1/4 + "
                                        "1/8: Achtel ist der "
                                        "gemeinsame Nenner.",
                                        "3/8",
                                        schritte=["1/4 = 2/8",
                                                  "1/8 bleibt 1/8",
                                                  "2/8 + 1/8 = 3/8"]),
                                    "gefuehrt": aufgabe(
                                        "3/4 - 1/8 = ?", "5/8",
                                        fehler="3/8",
                                        tipps=["Achtel für beide — die 3/4 auch umwandeln.",
                                               "3/4 = ?/8."],
                                        schritte=["3/4 = 6/8",
                                                  "6/8 - 1/8",
                                                  "= 5/8"]),
                                    "selbststaendig": aufgabe(
                                        "1/2 + 1/8 = ?", "5/8",
                                        fehler="2/8",
                                        tipps=["Welche Zahl "
                                               "teilt 2 "
                                               "und 8?"]),
                                    "transfer": auswahl(
                                        "Warum muss beim "
                                        "Gleichnamig-Machen "
                                        "auch der Bruch "
                                        "umgewandelt werden, "
                                        "der „schon passt“?",
                                        "Er muss nicht — "
                                        "aber der andere "
                                        "muss auf denselben "
                                        "Nenner",
                                        ["Weil sonst das "
                                         "Ergebnis falsch "
                                         "wird",
                                         "Beide müssen "
                                         "immer verändert "
                                         "werden"],
                                        "Der eine Bruch "
                                        "darf stehen "
                                        "bleiben, wenn "
                                        "sein Nenner "
                                        "passt — wichtig "
                                        "ist nur: beide "
                                        "teilen denselben "
                                        "Nenner.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Äpfel und Birnen zählt "
                                    "man nicht durcheinander — "
                                    "Hälften und Drittel "
                                    "auch nicht.",
                            "RULE": "Erst gleichnamig machen "
                                    "(gemeinsamer Nenner), "
                                    "dann Zähler addieren, "
                                    "Nenner behalten.",
                            "WORKED_EXAMPLE": "Schau, auf "
                                    "welchen Nenner beide "
                                    "Brüche gebracht werden "
                                    "— warum gerade "
                                    "diesen?",
                            "GUIDED_TASK": "Schreib erst die "
                                    "umgewandelten Brüche "
                                    "hin, dann rechne.",
                            "INDEPENDENT_TASK": "Plausibilität: "
                                    "ist dein Ergebnis "
                                    "größer als jeder "
                                    "einzelne Bruch?",
                            "ADAPTATION": "Die Tabelle "
                                    "zeigt für jeden Bruch "
                                    "die Umwandlung."}),
                        "faq": [
                            {"frage": "Wie finde ich den "
                                      "gemeinsamen Nenner?",
                             "antwort": "Ein Vielfaches beider "
                                        "Nenner — oft reicht "
                                        "das Produkt. Bei 2 "
                                        "und 3 sind es 6, bei "
                                        "4 und 8 reicht 8."},
                            {"frage": "Warum darf ich nicht "
                                      "einfach quer "
                                      "addieren?",
                             "antwort": "Weil die Stücke "
                                        "verschieden groß "
                                        "sind: 1/2 + 1/3 "
                                        "sind keine 2 "
                                        "Fünftel — Fünftel "
                                        "gäbe es nur, wenn "
                                        "beide durch 5 "
                                        "teilbar wären."}],
                    }},
            ]},
        {
            "id": "MA.GEO",
            "title": "Geometrie und Größen",
            "description": "Vom Rechteck zum Quader — Fläche und Raummaß.",
            "grade_min": 4, "grade_max": 7, "typical_grade": 5,
            "concepts": [
                # ------------------------------------------- Quader-Volumen
                {
                    "id": "MA.GEO.QUADERVOLUMEN",
                    "title": "Volumen eines Quaders",
                    "description": "V = a * b * c — der Raum, den ein "
                                   "Quader füllt, in Kubikeinheiten.",
                    "first_contact_grade": 5, "target_grade": 6,
                    "prerequisites": ["MA.GEO.FLAECHE_RECHTECK",
                                      "MA.GROESSEN.EINHEITEN"],
                    "levels": {
                        "below": "K4–5: Fläche Rechteck, Einheiten",
                        "target": "K6: V = a*b*c in cm³, Schichtdenken",
                        "above": "K7–8: Prisma, Dichte, Liter-Umrechnung"},
                    "can_do": {
                        "below": ["Flächen berechnen und Einheiten "
                                  "umwandeln"],
                        "target": ["Das Volumen eines Quaders als Produkt "
                                   "der drei Kanten berechnen und in cm³ "
                                   "angeben"],
                        "above": ["Volumen beliebiger Prismen und den "
                                  "Zusammenhang zu Litern deuten"]},
                    "difficulty_parameters": {
                        "kanten": "natürliche Zahlen bis 20",
                        "einheiten": "cm³, dm³", "darstellung": "Schichten"},
                    "anchor_items": [
                        item("Ein Quader ist 5 cm lang, 3 cm breit und "
                             "2 cm hoch. Volumen?", "30 cm³",
                             level="target", grade=6,
                             answer=number(30, unit="cm³")),
                        item("Ein Quader 4 cm mal 3 cm mal 5 cm — Volumen?",
                             "60 cm³", level="target", grade=6,
                             answer=number(60, unit="cm³"))],
                    "boundary_items": {
                        "below": [item("Rechteck 5 cm mal 3 cm — Fläche?",
                                       "15 cm²", level="below", grade=5,
                                       answer=number(15, unit="cm²"))],
                        "within": [item("Quader 4 * 4 * 2 cm — Volumen?",
                                        "32 cm³", level="target", grade=6,
                                        answer=number(32, unit="cm³"))],
                        "above": [item("Ein Quader fasst 240 cm³. Wie "
                                       "viele Liter Wasser sind das "
                                       "(1 dm³ = 1 l)?", "0,24 l",
                                       level="above", grade=7,
                                       answer=number(0.24, tolerance=0.001,
                                                     unit="l"))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Nur zwei Kanten "
                             "multipliziert: 5*3 statt 5*3*2 — die dritte "
                             "Dimension fehlt.",
                             "remediation_hint": "In Schichten denken: "
                             "Fläche mal Anzahl der Schichten (= Höhe).",
                             "diagnostic_item": item(
                                 "Quader 5 * 3 * 2 cm — Volumen?", "30 cm³",
                                 level="target", grade=6,
                                 answer=number(30, unit="cm³"),
                                 distractors=[{"answer": "15 cm³",
                                               "misconception": "F1",
                                               "feedback": "15 ist nur die Bodenfläche — es gibt noch die Höhe."}])},
                            {"key": "F2", "description": "Kanten werden "
                             "addiert statt multipliziert: 5+3+2 = 10.",
                             "remediation_hint": "Würfelchen zählen: eine "
                             "Schicht mal die Anzahl der Schichten.",
                             "diagnostic_item": item(
                                 "Quader 5 * 3 * 2 cm — Volumen?", "30 cm³",
                                 level="target", grade=6,
                                 answer=number(30, unit="cm³"),
                                 distractors=[{"answer": "10 cm³",
                                               "misconception": "F2",
                                               "feedback": "Die Kanten bilden Schichten — mal, nicht plus."}])},
                            {"key": "F3", "description": "Einheit bleibt "
                             "cm² oder cm — das Raummaß wird nicht als "
                             "Kubik verstanden.",
                             "remediation_hint": "Drei Richtungen brauchen "
                             "drei cm — die Einheit würfelt mit.",
                             "diagnostic_item": item(
                                 "Ein Quader 4 * 3 * 2 cm hat das Volumen …",
                                 "24 cm³", level="target", grade=6,
                                 answer=choice("24 cm³",
                                               ["24 cm²", "24 cm"],
                                               ["F3", "F3"]),
                                 distractors=[])}],
                        "diagnostic_items": [
                            item("Eine Schachtel hat eine Schicht aus "
                                 "4 mal 3 Würfelchen und ist 2 Schichten "
                                 "hoch. Wie viele Würfelchen?", "24",
                                 level="below", grade=5,
                                 answer=number(24)),
                            item("Quader 6 * 4 * 2 cm — Volumen?", "48 cm³",
                                 level="target", grade=6,
                                 answer=number(48, unit="cm³"))],
                        "exit_items": [
                            item("Quader 8 * 5 * 3 cm — Volumen?",
                                 "120 cm³", level="target", grade=6,
                                 answer=number(120, unit="cm³")),
                            item("Ein Würfel hat Kante 5 cm. Volumen?",
                                 "125 cm³", level="target", grade=6,
                                 answer=number(125, unit="cm³"))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "quadervolumen",
                            "thema_key": "geometrie",
                            "label": "Volumen eines Quaders",
                            "klasse_von": 5, "klasse_bis": 7,
                            "stichworte": ["volumen", "quader volumen",
                                           "quader", "raummaß", "cm³",
                                           "würfel volumen", "v=a*b*c"]},
                        "erstkontakt": {
                            "anker": "Eine Kiste ist 5 cm lang, 3 cm breit "
                                     "und 2 cm hoch. Wie viele kleine "
                                     "Würfelchen von 1 cm³ passen hinein?",
                            "benennung": "Volumen",
                            "erste_aufgabe": {"frage": "Ein Quader ist "
                                              "4 cm mal 3 cm mal 2 cm groß. "
                                              "Volumen?", "loesung": "24 cm³"}},
                        "fehlertypen": [
                            {
                                "key": "schicht_fehlt",
                                "label": "Dritte Dimension vergessen",
                                "beschreibung": "Nur Bodenfläche gerechnet: "
                                "Länge mal Breite, die Höhe fehlt.",
                                "antworten": ["15", "15 cm³", "20"],
                                "erklaerung": {
                                    "haken": "5 * 3 * 2: Wer 15 sagt, hat "
                                            "nur den Boden gelegt — die "
                                            "Kiste ist aber 2 Schichten hoch.",
                                    "erkenntnis": "Die Bodenfläche 5 * 3 "
                                    "füllt eine Schicht mit 15 Würfelchen. "
                                    "Der Quader stapelt 2 solcher Schichten: "
                                    "15 * 2 = 30.",
                                    "regel": "Volumen = Bodenfläche mal "
                                    "Höhe = Länge mal Breite mal Höhe. "
                                    "Jede Schicht enthält gleich viele "
                                    "Würfelchen.",
                                    "bild": {"zeigt": "eine Schicht aus "
                                             "5 mal 3 Würfelchen und eine "
                                             "zweite darüber",
                                             "bewegt": "die Schichten "
                                             "stapeln sich zum Quader",
                                             "bleibt_gleich": "jede Schicht "
                                             "hat dieselben 15 Würfelchen"},
                                    "aufgabe": {"frage": "Quader 4 mal 3 mal "
                                                "2 cm — Volumen?",
                                                "loesung": "24 cm³"}},
                                "visualisierung": _SCHRITTE(
                                    ["Bodenschicht: 5 * 3 = 15 Würfelchen",
                                     "Höhe 2 cm: zwei Schichten",
                                     "15 * 2 = 30 cm³"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Schicht", "Würfelchen"],
                                    ["unten | 15", "oben | 15",
                                     "gesamt | 30"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Quader 5 * 3 * 2 cm — Volumen?",
                                        "30 cm³", ["15 cm³", "10 cm³"],
                                        "15 ist nur der Boden — die Höhe "
                                        "stapelt noch eine Schicht."),
                                    "beispiel": aufgabe(
                                        "Wir füllen den Quader 4 * 3 * 2: "
                                        "eine Schicht 4 * 3 = 12 Würfelchen, "
                                        "zwei Schichten hoch.",
                                        "24 cm³",
                                        schritte=["4 * 3 = 12 pro Schicht",
                                                  "12 * 2 = 24",
                                                  "Einheit cm³"]),
                                    "gefuehrt": aufgabe(
                                        "Quader 6 * 4 * 2 cm — Volumen?",
                                        "48 cm³",
                                        fehler="24 cm³",
                                        tipps=["Wie viele Würfelchen liegen "
                                               "in einer Schicht?",
                                               "Wie viele Schichten hoch "
                                               "ist der Quader?"],
                                        schritte=["6 * 4 = 24 pro Schicht",
                                                  "24 * 2 = 48 cm³"]),
                                    "selbststaendig": aufgabe(
                                        "Quader 7 * 5 * 2 cm — Volumen?",
                                        "70 cm³",
                                        fehler="35 cm³",
                                        tipps=["Erst Boden, dann mal Höhe."],
                                        schritte=["7 * 5 = 35",
                                                  "35 * 2 = 70 cm³"]),
                                    "transfer": auswahl(
                                        "Warum heißt die Einheit cm³ und "
                                        "nicht cm², obwohl man doch "
                                        "multipliziert?",
                                        "Weil drei Richtungen gefüllt "
                                        "werden — das ³ zählt die "
                                        "Dimensionen",
                                        ["Es ist nur eine andere Schreibart",
                                         "cm³ ist größer"],
                                        "Fläche füllt zwei Richtungen, "
                                        "Raum drei — die Einheit zählt mit.")}},
                            {
                                "key": "kanten_addiert",
                                "label": "Kanten addiert statt multipliziert",
                                "beschreibung": "5+3+2 = 10 — die Summe der "
                                "Kanten verwechselt das Volumen mit einem "
                                "Rahmenmaß.",
                                "antworten": ["10", "10 cm³", "9"],
                                "erklaerung": {
                                    "haken": "5+3+2 = 10? Das ist die Länge "
                                            "der Kanten zusammen — nicht "
                                            "der Raum, den der Quader füllt.",
                                    "erkenntnis": "Würfelchen füllen den "
                                    "Raum: jede Schicht hat Länge mal "
                                    "Breite Stück, und die Höhe stapelt die "
                                    "Schichten. 5*3*2 = 30.",
                                    "regel": "Volumen zählt Würfelchen: "
                                    "Schicht = a*b, Stapel = mal Höhe. "
                                    "Addieren würde nur den Rahmen messen.",
                                    "bild": {"zeigt": "drei Kantenfarben "
                                             "und den Raum dazwischen",
                                             "bewegt": "Würfelchen füllen "
                                             "den Innenraum reihenweise",
                                             "bleibt_gleich": "die Kanten "
                                             "bleiben der Rahmen — sie "
                                             "füllen nichts"},
                                    "aufgabe": {"frage": "Quader 3 mal 2 mal "
                                                "4 cm — Volumen?",
                                                "loesung": "24 cm³"}},
                                "visualisierung": _SCHRITTE(
                                    ["Eine Schicht: 5 * 3 = 15",
                                     "zwei Schichten: 15 * 2 = 30",
                                     "5+3+2 zählt nur die Kanten"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Was", "Rechnung"],
                                    ["Kanten zusammen | 5+3+2 = 10",
                                     "Würfelchen | 5*3*2 = 30"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Quader 5 * 3 * 2 cm — Volumen?",
                                        "30 cm³", ["10 cm³", "25 cm³"],
                                        "Die Kanten bilden Schichten voller "
                                        "Würfelchen — mal, nicht plus."),
                                    "beispiel": aufgabe(
                                        "Kiste 3 * 2 * 2: Schicht 3 * 2 = 6, "
                                        "zwei Schichten.",
                                        "12 cm³",
                                        schritte=["3 * 2 = 6", "6 * 2 = 12"]),
                                    "gefuehrt": aufgabe(
                                        "Quader 4 * 3 * 3 cm — Volumen?",
                                        "36 cm³",
                                        fehler="10 cm³",
                                        tipps=["Schicht zuerst: 4 * 3.",
                                               "10 wären die Kanten zusammen."],
                                        schritte=["4 * 3 = 12",
                                                  "12 * 3 = 36 cm³"]),
                                    "selbststaendig": aufgabe(
                                        "Quader 5 * 5 * 2 cm — Volumen?",
                                        "50 cm³",
                                        fehler="12 cm³",
                                        tipps=["Erst die Schicht, dann die Höhe."],
                                        schritte=["5 * 5 = 25",
                                                  "25 * 2 = 50 cm³"]),
                                    "transfer": auswahl(
                                        "Für eine Kante aus Draht wäre "
                                        "5+3+2 richtig. Warum nicht für "
                                        "das Volumen?",
                                        "Der Draht misst nur den Rahmen — "
                                        "das Volumen füllt den Innenraum "
                                        "mit Würfelchen",
                                        ["Die Zahlen sind zu klein",
                                         "Weil cm³ eine andere Einheit ist"],
                                        "Verschiedene Fragen, verschiedene "
                                        "Rechnungen: Rahmen addieren, "
                                        "Raum multiplizieren.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Denk in Schichten: erst die "
                                    "Bodenfläche, dann mal die Höhe.",
                            "RULE": "V = a*b*c: Länge mal Breite mal Höhe, "
                                    "in cm³ — drei Richtungen, drei cm.",
                            "WORKED_EXAMPLE": "Jede Schicht hat gleich "
                                    "viele Würfelchen — zähle eine, dann "
                                    "die Schichten.",
                            "GUIDED_TASK": "Wie viele Würfelchen hat eine "
                                    "Schicht? Wie viele Schichten?",
                            "INDEPENDENT_TASK": "Einheit prüfen: Raum heißt "
                                    "cm³, nicht cm².",
                            "ADAPTATION": "Die Tabelle zeigt die Schichten "
                                    "einzeln — summiere sie."}),
                        "faq": [
                            {"frage": "Warum multipliziert man drei Zahlen?",
                             "antwort": "Weil der Raum drei Richtungen "
                                        "hat: eine Schicht füllt Länge mal "
                                        "Breite, und die Höhe stapelt die "
                                        "Schichten."},
                            {"frage": "Ist 5*3*2 dasselbe wie 2*3*5?",
                             "antwort": "Ja — dieselben Würfelchen, nur "
                                        "andere Reihenfolge beim "
                                        "Multiplizieren. 30 cm³ bleibt "
                                        "30 cm³."}],
                    }},
            ]},
    ]}
