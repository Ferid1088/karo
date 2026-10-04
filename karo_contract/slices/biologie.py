"""Biologie-Slice: von der Pflanze als Lebewesen zur Fotosynthese.

Level 0: das Kind weiß, dass Pflanzen Lebewesen sind. Dann: was sie zum
Leben brauchen, wie sie gebaut sind — und erst dann, wie sie mit Licht,
Wasser und Luft ihr eigenes Futter herstellen.

    BI.PFLANZEN.FOTOSYNTHESE   (Ziel, Kl. 5–7)
      ├── BI.PFLANZEN.AUFBAU       (Kl. 3–4)
      └── BI.PFLANZEN.BEDUERFNISSE (Kl. 2–4)
            └── BI.LEBEWESEN.PFLANZE   (Kl. 1–2, Level 0)
"""

from __future__ import annotations

from ._bauen import begriffe, aufgabe, auswahl, choice, item, text

_FLUSS = lambda schritte: {
    "component": "GenericStepFlow",
    "parameters": {"schritte": schritte}, "animation": "none"}

_NETZ = lambda knoten, kanten: {
    "component": "ConceptMap",
    "parameters": {"knoten": knoten, "kanten": kanten}, "animation": "none"}

_TABELLE = lambda spalten, zeilen: {
    "component": "DataTable",
    "parameters": {"spalten": spalten, "zeilen": zeilen}, "animation": "none"}


def _hilfe(texte: dict) -> dict:
    return {phase: {"text": t} for phase, t in texte.items()}


SLICE = {
    "fach": "biologie",
    "code": "BI",
    "name": "Biologie",
    "blocks": [
        {
            "id": "BI.LEBEWESEN",
            "title": "Lebewesen",
            "description": "Was etwas zum Lebewesen macht — die "
                           "Einstiegsstufe jedes Biologie-Lernens.",
            "grade_min": 1, "grade_max": 3, "typical_grade": 2,
            "concepts": [
                # --------------------------------------------- Level 0
                {
                    "id": "BI.LEBEWESEN.PFLANZE",
                    "title": "Pflanzen sind Lebewesen",
                    "description": "Pflanzen wachsen, brauchen Wasser "
                                   "und vermehren sich — sie sind "
                                   "lebendig, auch ohne Beine.",
                    "first_contact_grade": 1, "target_grade": 2,
                    "prerequisites": [],
                    "levels": {
                        "below": "K1: Pflanzen und Tiere benennen",
                        "target": "K2: Lebenszeichen erkennen und "
                                  "Pflanzen als Lebewesen einordnen",
                        "above": "K3–4: Bedürfnisse und Aufbau der "
                                 "Pflanze"},
                    "can_do": {
                        "below": ["Pflanzen benennen"],
                        "target": ["erklären, warum eine Pflanze "
                                   "lebendig ist"],
                        "above": ["sagen, was eine Pflanze zum Leben "
                                  "braucht"]},
                    "difficulty_parameters": {
                        "beispiele": "Baum, Blume, Gras",
                        "lebenszeichen": "wachsen, Wasser brauchen, "
                                         "sich vermehren"},
                    "anchor_items": [
                        item("Ist eine Blume ein Lebewesen?",
                             "ja", level="target", grade=2,
                             answer=text("ja", "ja, sie wächst")),
                        item("Nenne ein Lebenszeichen einer Pflanze.",
                             "Sie wächst.", level="target", grade=2,
                             answer=text("wachsen", "sie wächst",
                                         "wächst", "braucht wasser"))],
                    "boundary_items": {
                        "below": [item("Nenne eine Pflanze.",
                                       "Baum", level="below", grade=1,
                                       answer=text("baum", "blume",
                                                   "gras", "strauch"))],
                        "within": [item("Was macht eine Pflanze, das "
                                        "ein Stein nicht macht?",
                                        "Sie wächst.", level="target",
                                        grade=2,
                                        answer=text("wachsen",
                                                    "sie wächst"))],
                        "above": [item("Was braucht eine Pflanze zum "
                                       "Leben?", "Wasser und Licht",
                                       level="above", grade=4,
                                       answer=text("wasser und licht",
                                                   "licht und wasser",
                                                   "wasser"))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Lebendig "
                             "heißt für das Kind „bewegt sich“ — "
                             "Dinge ohne Beine gelten als unbelebt.",
                             "remediation_hint": "Lebenszeichen "
                             "suchen statt Bewegung: wachsen, "
                             "brauchen, vermehren.",
                             "diagnostic_item": item(
                                 "Ist eine Blume ein Lebewesen?",
                                 "ja", level="target", grade=2,
                                 answer=choice("ja, sie wächst und "
                                               "braucht Wasser",
                                               ["nein, sie bewegt "
                                                "sich nicht",
                                                "nur wenn Wind "
                                                "sie bewegt"],
                                               ["F1", "F1"]),
                                 distractors=[])}],
                        "diagnostic_items": [
                            item("Nenne eine Pflanze.", "Baum",
                                 level="below", grade=1,
                                 answer=text("baum", "blume", "gras",
                                             "strauch")),
                            item("Warum ist eine Pflanze lebendig?",
                                 "Sie wächst und braucht Wasser.",
                                 level="target", grade=2,
                                 answer=text("sie wächst",
                                             "wächst",
                                             "sie wächst und braucht "
                                             "wasser",
                                             "sie braucht wasser"))],
                        "exit_items": [
                            item("Nenne zwei Lebenszeichen einer "
                                 "Pflanze.", "Wachsen und Wasser "
                                 "brauchen",
                                 level="target", grade=2,
                                 answer=text("wachsen und wasser",
                                             "wachsen wasser",
                                             "sie wächst und braucht "
                                             "wasser")),
                            item("Ist ein Stein ein Lebewesen? "
                                 "Warum nicht?",
                                 "Nein, er wächst nicht und braucht "
                                 "nichts.",
                                 level="target", grade=2,
                                 answer=text("nein",
                                             "nein er wächst nicht"))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "pflanze",
                            "thema_key": "lebewesen",
                            "label": "Pflanzen sind Lebewesen",
                            "klasse_von": 1, "klasse_bis": 3,
                            "stichworte": ["pflanze", "lebewesen",
                                           "ist eine pflanze lebendig",
                                           "lebenszeichen"]},
                        "erstkontakt": {
                            "anker": "Ein Stein und eine Blume — was "
                                     "kann die Blume, das der Stein "
                                     "nicht kann?",
                            "benennung": "Lebewesen",
                            "erste_aufgabe": {"frage": "Ist eine Blume "
                                              "ein Lebewesen? "
                                              "(ja/nein)",
                                              "loesung": "ja"}},
                        "fehlertypen": [
                            {
                                "key": "bewegt_ist_lebendig",
                                "label": "Nur was sich bewegt, lebt",
                                "beschreibung": "Pflanzen gelten als "
                                "unbelebt, weil sie nicht laufen "
                                "können — Leben wird auf Bewegung "
                                "verengt.",
                                "antworten": ["nein", "nicht lebendig",
                                              "sie bewegt sich nicht"],
                                "erklaerung": {
                                    "haken": "Eine Blume läuft nicht "
                                            "— ist sie deshalb tot? "
                                            "Sie wächst jeden Tag ein "
                                            "bisschen weiter.",
                                    "erkenntnis": "Lebendig heißt "
                                    "nicht „bewegt sich“. Es heißt: "
                                    "wächst, braucht etwas zum Leben, "
                                    "vermehrt sich. All das tut die "
                                    "Blume.",
                                    "regel": "Lebewesen erkennt man "
                                    "an Lebenszeichen: wachsen, "
                                    "brauchen, sich vermehren — "
                                    "nicht an Beinen.",
                                    "bild": {"zeigt": "Blume, Stein "
                                             "und Hund mit ihren "
                                             "Lebenszeichen",
                                             "bewegt": "die Zeichen "
                                             "wandern zu dem, der "
                                             "sie erfüllt",
                                             "bleibt_gleich": "die "
                                             "Blume bleibt "
                                             "lebendig"},
                                    "aufgabe": {"frage": "Nenne ein "
                                                "Lebenszeichen der "
                                                "Blume.",
                                                "loesung": "Sie "
                                                           "wächst."}},
                                "visualisierung": _NETZ(
                                    ["Lebewesen", "wachsen",
                                     "brauchen", "vermehren"],
                                    ["Lebewesen → wachsen",
                                     "Lebewesen → brauchen",
                                     "Lebewesen → vermehren",
                                     "Pflanze → Lebewesen"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Ding", "wächst?", "braucht?",
                                     "Lebewesen?"],
                                    ["Blume | ja | Wasser | ja",
                                     "Stein | nein | nein | nein",
                                     "Hund | ja | Futter | ja"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Ist eine Blume ein "
                                        "Lebewesen?",
                                        "ja, sie wächst und braucht "
                                        "Wasser",
                                        ["nein, sie bewegt sich "
                                         "nicht",
                                         "nur wenn Wind sie "
                                         "bewegt"],
                                        "Leben zeigt sich an "
                                        "Wachsen und Brauchen — "
                                        "nicht an Beinen."),
                                    "beispiel": aufgabe(
                                        "Die Blume wächst, trinkt "
                                        "Wasser durch ihre Wurzel "
                                        "und bildet Samen — drei "
                                        "Lebenszeichen.",
                                        "Sie wächst.",
                                        schritte=["wächst",
                                                  "braucht Wasser",
                                                  "bildet Samen"]),
                                    "gefuehrt": aufgabe(
                                        "Warum ist ein Baum ein "
                                        "Lebewesen? Antworte in "
                                        "einem Satz.",
                                        "Er wächst und braucht "
                                        "Wasser.",
                                        fehler="Er ist nicht "
                                               "lebendig.",
                                        art="begriffe",
                                        rubrik={
                                            "begriffe": [["wachs",
                                                          "waechs"],
                                                         "wasser",
                                                         ["vermehr",
                                                          "wucher"]],
                                            "mindestens": 1,
                                            "hinweise": {
                                                "teilweise": "Dein "
                                                "Satz stimmt — nenne "
                                                "noch ein "
                                                "Lebenszeichen."}},
                                        tipps=["Was tut der Baum im "
                                               "Frühjahr?"]),
                                    "selbststaendig": aufgabe(
                                        "Erkläre in einem Satz, "
                                        "warum Gras ein Lebewesen "
                                        "ist.",
                                        "Es wächst und braucht "
                                        "Wasser.",
                                        fehler="Es ist nicht "
                                               "lebendig.",
                                        art="begriffe",
                                        rubrik={
                                            "begriffe": [["wachs",
                                                          "waechs"],
                                                         "wasser",
                                                         ["vermehr",
                                                          "wucher"],
                                                         ["leb",
                                                          "lebt"]],
                                            "mindestens": 2,
                                            "hinweise": {
                                                "teilweise": "Ein "
                                                "Lebenszeichen fehlt "
                                                "noch — was braucht "
                                                "das Gras außerdem?"}},
                                        tipps=["Zwei Lebenszeichen "
                                               "nennen."]),
                                    "transfer": auswahl(
                                        "Ein Pilz bewegt sich "
                                        "nicht und ist grün wie "
                                        "manche Pflanzen — Lebewesen?",
                                        "Ja, wenn er wächst und "
                                        "sich vermehrt",
                                        ["Nein, er bewegt sich "
                                         "nicht",
                                         "Nur Pflanzen sind "
                                         "Lebewesen"],
                                        "Die Lebenszeichen "
                                        "entscheiden — nicht die "
                                        "Art.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Was kann ein Lebewesen, das ein "
                                    "Ding nicht kann?",
                            "RULE": "Lebenszeichen: wachsen, etwas "
                                    "brauchen, sich vermehren.",
                            "WORKED_EXAMPLE": "Prüfe jede Zeile: "
                                    "wächst es? braucht es etwas?",
                            "GUIDED_TASK": "Denk an die drei "
                                    "Lebenszeichen — nenne eines.",
                            "INDEPENDENT_TASK": "Bewegung ist kein "
                                    "Muss — Wachstum reicht.",
                            "ADAPTATION": "Die Tabelle vergleicht "
                                    "Blume, Stein und Hund."}),
                        "faq": [
                            {"frage": "Sind Pflanzen wirklich "
                                      "lebendig?",
                             "antwort": "Ja — sie wachsen, brauchen "
                                        "Wasser und Licht und "
                                        "vermehren sich über Samen."},
                            {"frage": "Muss ein Lebewesen sich "
                                      "bewegen können?",
                             "antwort": "Nein — viele Lebewesen "
                                        "bleiben am Ort. Wachsen und "
                                        "Brauchen sind die Zeichen."}],
                    }},
            ]},
        {
            "id": "BI.PFLANZEN",
            "title": "Pflanzen",
            "description": "Was Pflanzen brauchen, wie sie gebaut "
                           "sind und wie sie ihr Futter herstellen.",
            "grade_min": 2, "grade_max": 7, "typical_grade": 4,
            "concepts": [
                # -------------------------------------- Bedürfnisse
                {
                    "id": "BI.PFLANZEN.BEDUERFNISSE",
                    "title": "Was Pflanzen zum Leben brauchen",
                    "description": "Licht, Wasser, Luft und Wärme — "
                                   "die Bedürfnisse einer Pflanze.",
                    "first_contact_grade": 2, "target_grade": 4,
                    "prerequisites": ["BI.LEBEWESEN.PFLANZE"],
                    "levels": {
                        "below": "K2: Pflanzen sind Lebewesen",
                        "target": "K4: die vier Bedürfnisse nennen "
                                  "und ihre Rolle erklären",
                        "above": "K5–7: Fotosynthese als "
                                 "Futterherstellung"},
                    "can_do": {
                        "below": ["ein Lebenszeichen nennen"],
                        "target": ["Licht, Wasser, Luft und Wärme "
                                   "als Bedürfnisse nennen und "
                                   "jeweils die Folge ihres "
                                   "Fehlens beschreiben"],
                        "above": ["erklären, wozu die Pflanze das "
                                  "Licht nutzt"]},
                    "difficulty_parameters": {
                        "beduerfnisse": "Licht, Wasser, Luft, Wärme",
                        "beobachtung": "Vertrocknen ohne Wasser"},
                    "anchor_items": [
                        item("Nenne zwei Dinge, die eine Pflanze "
                             "zum Leben braucht.",
                             "Wasser und Licht", level="target",
                             grade=4,
                             answer=text("wasser und licht",
                                         "licht und wasser",
                                         "wasser licht")),
                        item("Was passiert mit einer Pflanze ohne "
                             "Wasser?", "Sie vertrocknet.",
                             level="target", grade=4,
                             answer=text("vertrocknet",
                                         "sie vertrocknet",
                                         "sie stirbt"))],
                    "boundary_items": {
                        "below": [item("Ist eine Blume ein "
                                       "Lebewesen? (ja/nein)",
                                       "ja", level="below", grade=2,
                                       answer=text("ja"))],
                        "within": [item("Was braucht die Pflanze aus "
                                        "der Luft?",
                                        "Kohlenstoffdioxid (CO₂)",
                                        level="target", grade=4,
                                        answer=text("co2", "co₂",
                                                    "kohlendioxid",
                                                    "kohlenstoffdioxid"))],
                        "above": [item("Wozu braucht die Pflanze "
                                       "Licht genau?",
                                       "Für die Fotosynthese — "
                                       "ihre Futterherstellung",
                                       level="above", grade=6,
                                       answer=text("fotosynthese",
                                                   "für die "
                                                   "fotosynthese"))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Pflanzen "
                             "„essen“ Erde oder Dünger wie Tiere "
                             "Futter — der Boden wird zum Futter.",
                             "remediation_hint": "Erde gibt Halt "
                             "und Wasser — das Futter baut die "
                             "Pflanze selbst aus Licht und Luft.",
                             "diagnostic_item": item(
                                 "Woher bekommt eine Pflanze ihr "
                                 "Futter?",
                                 "Sie stellt es selbst aus Licht, "
                                 "Wasser und Luft her",
                                 level="target", grade=4,
                                 answer=choice("Sie stellt es "
                                               "selbst her",
                                               ["Aus der Erde",
                                                "Aus dem "
                                                "Gießwasser"],
                                               ["F1", "F1"]),
                                 distractors=[])},
                            {"key": "F2", "description": "Licht "
                             "wird als reine Wärmequelle "
                             "verstanden — die Pflanze braucht es "
                             "„nur zum Wachsen“, nicht als "
                             "Energiequelle.",
                             "remediation_hint": "Licht ist der "
                             "Antrieb, nicht nur Wärme: ohne "
                             "Licht keine Fotosynthese.",
                             "diagnostic_item": item(
                                 "Warum braucht eine Pflanze "
                                 "Licht?",
                                 "Weil sie damit ihr Futter "
                                 "herstellt",
                                 level="target", grade=4,
                                 answer=choice("Zum Futterbau",
                                               ["Nur für Wärme",
                                                "Damit sie "
                                                "schön aussieht"],
                                               ["F2", None]),
                                 distractors=[])}],
                        "diagnostic_items": [
                            item("Nenne ein Lebenszeichen einer "
                                 "Pflanze.", "Sie wächst.",
                                 level="below", grade=2,
                                 answer=text("wachsen", "sie "
                                             "wächst")),
                            item("Welche zwei Stoffe holt sich "
                                 "die Pflanze aus Boden und Luft?",
                                 "Wasser und Kohlenstoffdioxid",
                                 level="target", grade=4,
                                 answer=text("wasser und co2",
                                             "wasser und "
                                             "kohlendioxid",
                                             "wasser co2"))],
                        "exit_items": [
                            item("Nenne die vier Bedürfnisse "
                                 "einer Pflanze.",
                                 "Licht, Wasser, Luft, Wärme",
                                 level="target", grade=4,
                                 answer=text("licht wasser luft "
                                             "wärme",
                                             "wasser licht luft "
                                             "wärme",
                                             "licht wasser luft "
                                             "waerme")),
                            item("Was passiert, wenn eine "
                                 "Pflanze zwei Wochen kein "
                                 "Licht bekommt?",
                                 "Sie wird blass und geht ein.",
                                 level="target", grade=4,
                                 answer=text("sie geht ein",
                                             "sie wird blass",
                                             "sie stirbt"))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "beduerfnisse",
                            "thema_key": "pflanzen",
                            "label": "Was Pflanzen brauchen",
                            "klasse_von": 2, "klasse_bis": 4,
                            "stichworte": ["was brauchen pflanzen",
                                           "pflanzenbedürfnisse",
                                           "licht wasser pflanze",
                                           "pflanze pflegen"]},
                        "erstkontakt": {
                            "anker": "Eine Topfpflanze steht vier "
                                     "Wochen dunkel im Keller — "
                                     "was wird aus ihr?",
                            "benennung": "Pflanzen-Bedürfnisse",
                            "erste_aufgabe": {"frage": "Was passiert "
                                              "ohne Wasser?",
                                              "loesung": "Sie "
                                              "vertrocknet."}},
                        "fehlertypen": [
                            {
                                "key": "erde_ist_futter",
                                "label": "Erde wird zum Pflanzenfutter",
                                "beschreibung": "Die Pflanze „isst“ "
                                "die Erde — Wurzeln werden zu "
                                "Mäulern.",
                                "antworten": ["erde", "aus der erde",
                                              "dünger", "er frisst"],
                                "erklaerung": {
                                    "haken": "Eine Pflanze wird "
                                            "groß, frisst aber die "
                                            "Erde nicht weg — der "
                                            "Topf bleibt voll. "
                                            "Woher kommt ihr "
                                            "Futter?",
                                    "erkenntnis": "Die Erde gibt "
                                    "Halt und Wasser — aber ihr "
                                    "Futter baut die Pflanze "
                                    "selbst: aus Licht, Wasser "
                                    "und einem Gas aus der Luft.",
                                    "regel": "Pflanzen stellen ihr "
                                    "Futter selbst her — sie "
                                    "essen nichts. Erde = Halt "
                                    "und Wasser, nicht Mahlzeit.",
                                    "bild": {"zeigt": "Wurzeln im "
                                             "Boden, Blätter im "
                                             "Licht",
                                             "bewegt": "Wasser "
                                             "wandert hoch, Licht "
                                             "trifft die Blätter",
                                             "bleibt_gleich": "die "
                                             "Erde bleibt im "
                                             "Topf"},
                                    "aufgabe": {"frage": "Wovon "
                                                "lebt die Pflanze "
                                                "hauptsächlich?",
                                                "loesung": "Von "
                                                "Licht, Wasser "
                                                "und Luft"}},
                                "visualisierung": _NETZ(
                                    ["Pflanze", "Wasser aus Erde",
                                     "Licht", "CO₂ aus Luft",
                                     "eigenes Futter"],
                                    ["Wurzel → Wasser aus Erde",
                                     "Blatt → Licht",
                                     "Blatt → CO₂ aus Luft",
                                     "Licht + Wasser + CO₂ → "
                                     "eigenes Futter"]),
                                "visualisierung_alternativ": _FLUSS(
                                    ["Wurzeln holen Wasser",
                                     "Blätter holen Licht und "
                                     "Luft",
                                     "daraus baut die Pflanze "
                                     "ihr Futter"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Woher kommt das Futter "
                                        "der Pflanze?",
                                        "Sie stellt es selbst "
                                        "her",
                                        ["Aus der Erde",
                                         "Aus dem Gießwasser"],
                                        "Der Topf bleibt voll "
                                        "Erde — sie frisst sie "
                                        "nicht."),
                                    "beispiel": aufgabe(
                                        "Wiege eine Pflanze und "
                                        "ihre Erde nach einem "
                                        "Jahr: die Pflanze wird "
                                        "schwerer, die Erde "
                                        "bleibt gleich. Das "
                                        "Futter kommt nicht aus "
                                        "dem Topf.",
                                        "Sie baut es selbst."),
                                    "gefuehrt": aufgabe(
                                        "Woher bekommt die "
                                        "Pflanze ihr Futter? "
                                        "Antworte in einem "
                                        "Satz.",
                                        "Sie stellt es aus "
                                        "Licht, Wasser und Luft "
                                        "selbst her.",
                                        fehler="aus der erde",
                                        art="begriffe",
                                        rubrik={
                                            "begriffe": ["licht",
                                                         "wasser",
                                                         "luft",
                                                         "selbst",
                                                         "herstell"],
                                            "mindestens": 2,
                                            "hinweise": {
                                                "teilweise": "Ein "
                                                "Teil stimmt — "
                                                "woher kommt "
                                                "der Rest?"}},
                                        tipps=["Erde ist nur "
                                               "Halt und Wasser.",
                                               "Das Futter baut "
                                               "sie selbst — "
                                               "woraus?"]),
                                    "selbststaendig": aufgabe(
                                        "Erkläre, warum Dünger "
                                        "nicht das „Essen“ der "
                                        "Pflanze ist.",
                                        "Dünger gibt nur Stoffe "
                                        "— das Futter stellt die "
                                        "Pflanze aus Licht, "
                                        "Wasser und Luft her.",
                                        fehler="dünger ist das "
                                               "essen",
                                        art="begriffe",
                                        rubrik={
                                            "begriffe": ["licht",
                                                         "wasser",
                                                         "luft",
                                                         "selbst",
                                                         "stoff",
                                                         "herstell",
                                                         "futter"],
                                            "mindestens": 2,
                                            "hinweise": {
                                                "teilweise": "Du "
                                                "bist nah dran — "
                                                "was liefert das "
                                                "Futter wirklich?"}},
                                        tipps=["Woraus baut die "
                                               "Pflanze ihr "
                                               "Futter?"]),
                                    "transfer": auswahl(
                                        "Ein Astronaut züchtet "
                                        "Pflanzen ganz ohne Erde "
                                        "(Hydrokultur). Warum "
                                        "funktioniert das?",
                                        "Erde ist nur Halt und "
                                        "Wasser — das Futter "
                                        "kommt aus Licht und "
                                        "Luft",
                                        ["Pflanzen brauchen "
                                         "nichts",
                                         "Das Wasser ersetzt "
                                         "die Erde als Futter"],
                                        "Was die Erde wirklich "
                                        "leistet, kann man "
                                        "ersetzen — was sie "
                                        "nicht ist: Futter.")}},
                            {
                                "key": "licht_ist_waerme",
                                "label": "Licht wird nur als "
                                         "Wärme verstanden",
                                "beschreibung": "Die Pflanze "
                                "braucht Licht angeblich nur zum "
                                "Warmhalten — seine treibende "
                                "Rolle bleibt unsichtbar.",
                                "antworten": ["wärme", "zum warmen",
                                              "damit ihr warm ist"],
                                "erklaerung": {
                                    "haken": "Eine Pflanze am "
                                            "heizungswarmen, "
                                            "dunklen Platz geht "
                                            "ein — Wärme allein "
                                            "reicht offenbar "
                                            "nicht.",
                                    "erkenntnis": "Licht ist für "
                                    "die Pflanze Energie: mit "
                                    "ihm baut sie aus Wasser "
                                    "und Luft ihr Futter. Warm "
                                    "und dunkel = kein Futter.",
                                    "regel": "Licht = Energie "
                                    "zum Futterbau (Fotosynthese). "
                                    "Ohne Licht gibt es kein "
                                    "Futter — egal wie warm.",
                                    "bild": {"zeigt": "Lichtstrahlen "
                                             "treffen das Blatt, "
                                             "die Bausteine "
                                             "entstehen",
                                             "bewegt": "das Blatt "
                                             "verwandelt Licht, "
                                             "Wasser und Luft in "
                                             "Futter",
                                             "bleibt_gleich": "die "
                                             "Wärme bleibt "
                                             "Nebensache"},
                                    "aufgabe": {"frage": "Warum "
                                                "braucht die "
                                                "Pflanze Licht?",
                                                "loesung": "Um "
                                                "Futter "
                                                "herzustellen"}},
                                "visualisierung": _FLUSS(
                                    ["Licht trifft das Blatt",
                                     "Licht liefert Energie",
                                     "Blatt baut Futter aus "
                                     "Wasser und Luft"]),
                                "visualisierung_alternativ": _NETZ(
                                    ["Licht", "Energie",
                                     "Fotosynthese", "Futter"],
                                    ["Licht → Energie",
                                     "Energie → Fotosynthese",
                                     "Fotosynthese → Futter"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Warum braucht eine "
                                        "Pflanze Licht?",
                                        "Um mit seiner Energie "
                                        "Futter herzustellen",
                                        ["Nur für Wärme",
                                         "Damit sie schön "
                                         "aussieht"],
                                        "Licht ist der Antrieb — "
                                        "ohne ihn kein "
                                        "Futterbau."),
                                    "beispiel": aufgabe(
                                        "Eine Pflanze im dunklen "
                                        "Keller verliert ihre "
                                        "grüne Farbe — sie kann "
                                        "kein Futter mehr bauen.",
                                        "Sie braucht Licht "
                                        "als Energie."),
                                    "gefuehrt": aufgabe(
                                        "Warum geht eine "
                                        "Pflanze im dunklen, "
                                        "warmen Keller ein? "
                                        "Antworte in einem Satz.",
                                        "Weil sie ohne Licht "
                                        "kein Futter herstellen "
                                        "kann.",
                                        fehler="weil ihr kalt "
                                               "ist",
                                        art="begriffe",
                                        rubrik={
                                            "begriffe": ["licht",
                                                         "futter",
                                                         "fotosynthese",
                                                         "energie",
                                                         "herstell"],
                                            "mindestens": 2,
                                            "hinweise": {
                                                "teilweise": "Licht "
                                                "hast du — wofür "
                                                "braucht sie es "
                                                "genau?"}},
                                        tipps=["Es ist warm — "
                                               "was fehlt "
                                               "trotzdem?",
                                               "Wozu nutzt sie "
                                               "das Licht?"]),
                                    "selbststaendig": aufgabe(
                                        "Erkläre, warum eine "
                                        "Pflanze Licht braucht.",
                                        "Sie braucht es als "
                                        "Energie für die "
                                        "Fotosynthese — ihren "
                                        "Futterbau.",
                                        fehler="für wärme",
                                        art="begriffe",
                                        rubrik={
                                            "begriffe": ["fotosynthese",
                                                         "energie",
                                                         "futter",
                                                         "herstell"],
                                            "mindestens": 2,
                                            "hinweise": {
                                                "teilweise": "Ein "
                                                "Baustein fehlt — "
                                                "was macht sie "
                                                "mit der "
                                                "Energie?"}},
                                        tipps=["Das Stichwort "
                                               "ist "
                                               "Fotosynthese."]),
                                    "transfer": auswahl(
                                        "Zwei Pflanzen: eine "
                                        "warm+dunkel, eine "
                                        "kühl+hell. Welche "
                                        "überlebt?",
                                        "Die kühle im Licht — "
                                        "Licht ist Energie, "
                                        "Wärme ist nur "
                                        "Nebensache",
                                        ["Die warme im Dunkeln",
                                         "Beide gleich"],
                                        "Der Vergleich zeigt, "
                                        "was wirklich zählt: "
                                        "die Energie für den "
                                        "Futterbau.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Woher kommt das Futter, wenn "
                                    "der Topf voll Erde bleibt?",
                            "RULE": "Pflanzen brauchen Licht, "
                                    "Wasser, Luft und Wärme — "
                                    "und sie stellen ihr Futter "
                                    "selbst her.",
                            "WORKED_EXAMPLE": "Erde gibt Halt und "
                                    "Wasser — das Futter kommt "
                                    "aus Licht und Luft.",
                            "GUIDED_TASK": "Trenne: was gibt der "
                                    "Boden — und was macht die "
                                    "Pflanze selbst?",
                            "INDEPENDENT_TASK": "Licht ist "
                                    "Energie, nicht nur Wärme.",
                            "ADAPTATION": "Das Netz zeigt, woher "
                                    "jeder Baustein kommt."}),
                        "faq": [
                            {"frage": "Frisst die Pflanze die "
                                      "Erde?",
                             "antwort": "Nein — die Erde gibt "
                                        "Halt und Wasser. Ihr "
                                        "Futter stellt sie aus "
                                        "Licht, Wasser und Luft "
                                        "selbst her."},
                            {"frage": "Warum geht eine Pflanze "
                                      "im Dunkeln ein?",
                             "antwort": "Ohne Licht kann sie "
                                        "kein Futter bauen — "
                                        "sie verhungert, auch "
                                        "wenn es warm ist."}],
                    }},
                # ------------------------------------------ Aufbau
                {
                    "id": "BI.PFLANZEN.AUFBAU",
                    "title": "Aufbau der Pflanze",
                    "description": "Wurzel, Stängel, Blatt — die "
                                   "drei Organe und ihre "
                                   "Aufgaben.",
                    "first_contact_grade": 3, "target_grade": 4,
                    "prerequisites": ["BI.PFLANZEN.BEDUERFNISSE"],
                    "levels": {
                        "below": "K2–4: Bedürfnisse der Pflanze",
                        "target": "K4: Wurzel, Stängel und Blatt "
                                  "mit ihren Aufgaben",
                        "above": "K5: die Organe als Baustellen "
                                 "der Fotosynthese"},
                    "can_do": {
                        "below": ["nennen, was die Pflanze "
                                  "braucht"],
                        "target": ["die drei Pflanzenteile "
                                   "benennen und ihre Aufgabe "
                                   "erklären"],
                        "above": ["erklären, wo Fotosynthese "
                                  "stattfindet"]},
                    "difficulty_parameters": {
                        "organe": "Wurzel, Stängel, Blatt",
                        "aufgaben": "Wasser aufnehmen, stützen, "
                                    "Licht fangen"},
                    "anchor_items": [
                        item("Welcher Pflanzenteil nimmt das "
                             "Wasser auf?", "Die Wurzel",
                             level="target", grade=4,
                             answer=text("wurzel", "die wurzel",
                                         "wurzeln")),
                        item("Wo fängt die Pflanze das Licht ein?",
                             "Im Blatt", level="target", grade=4,
                             answer=text("blatt", "im blatt",
                                         "blätter"))],
                    "boundary_items": {
                        "below": [item("Was braucht die Pflanze "
                                       "aus dem Boden?",
                                       "Wasser", level="below",
                                       grade=4,
                                       answer=text("wasser"))],
                        "within": [item("Welcher Teil hält die "
                                        "Pflanze aufrecht?",
                                        "Der Stängel",
                                        level="target", grade=4,
                                        answer=text("stängel",
                                                    "der stängel",
                                                    "stamm"))],
                        "above": [item("In welchem Teil findet "
                                       "die Fotosynthese statt?",
                                       "Im Blatt", level="above",
                                       grade=6,
                                       answer=text("blatt",
                                                   "im blatt"))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Wurzel "
                             "und Stängel werden verwechselt — "
                             "was unten wächst, „hält“ die "
                             "Pflanze.",
                             "remediation_hint": "Die Wurzel "
                             "trinkt und hält fest im Boden — "
                             "der Stängel trägt und leitet "
                             "das Wasser hoch.",
                             "diagnostic_item": item(
                                 "Welcher Teil nimmt das "
                                 "Wasser aus dem Boden auf?",
                                 "Die Wurzel", level="target",
                                 grade=4,
                                 answer=choice("Die Wurzel",
                                               ["Der Stängel",
                                                "Das Blatt"],
                                               ["F1", "F1"]),
                                 distractors=[])},
                            {"key": "F2", "description": "Das "
                             "Blatt wird nur als Deko "
                             "verstanden — seine "
                             "Arbeitsaufgabe bleibt "
                             "unsichtbar.",
                             "remediation_hint": "Das Blatt "
                             "ist die Werkstatt: Licht "
                             "fangen und Luft holen.",
                             "diagnostic_item": item(
                                 "Was ist die Aufgabe des "
                                 "Blattes?",
                                 "Licht fangen und Luft "
                                 "aufnehmen",
                                 level="target", grade=4,
                                 answer=choice("Licht fangen",
                                               ["Nur hübsch "
                                                "aussehen",
                                                "Die Pflanze "
                                                "kühlen"],
                                               ["F2", "F2"]),
                                 distractors=[])}],
                        "diagnostic_items": [
                            item("Was braucht eine Pflanze "
                                 "zum Leben?",
                                 "Wasser und Licht",
                                 level="below", grade=4,
                                 answer=text("wasser und "
                                             "licht",
                                             "licht und "
                                             "wasser")),
                            item("Welcher Teil trägt die "
                                 "Blätter?", "Der Stängel",
                                 level="target", grade=4,
                                 answer=text("stängel",
                                             "der stängel"))],
                        "exit_items": [
                            item("Ordne zu: welcher Teil "
                                 "nimmt Wasser auf — welcher "
                                 "fängt Licht?",
                                 "Wurzel nimmt Wasser, "
                                 "Blatt fängt Licht",
                                 level="target", grade=4,
                                 answer=text("wurzel wasser "
                                             "blatt licht",
                                             "wurzel nimmt "
                                             "wasser blatt "
                                             "fängt licht")),
                            item("Welcher Teil leitet das "
                                 "Wasser von der Wurzel zum "
                                 "Blatt?", "Der Stängel",
                                 level="target", grade=4,
                                 answer=text("stängel",
                                             "der stängel"))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "aufbau",
                            "thema_key": "pflanzen",
                            "label": "Aufbau der Pflanze",
                            "klasse_von": 3, "klasse_bis": 5,
                            "stichworte": ["pflanzenaufbau",
                                           "wurzel stängel blatt",
                                           "teile der pflanze",
                                           "pflanzenteile"]},
                        "erstkontakt": {
                            "anker": "Eine Pflanze hat drei "
                                     "Arbeiter: einen unten, "
                                     "einen in der Mitte, einen "
                                     "oben — wer macht was?",
                            "benennung": "Pflanzenteile",
                            "erste_aufgabe": {"frage": "Welcher "
                                              "Teil nimmt das "
                                              "Wasser auf?",
                                              "loesung": "Die "
                                              "Wurzel"}},
                        "fehlertypen": [
                            {
                                "key": "wurzel_staengel",
                                "label": "Wurzel und Stängel "
                                         "verwechselt",
                                "beschreibung": "Beide Teile "
                                "„halten“ — die unterschiedlichen "
                                "Aufgaben (trinken vs. tragen "
                                "und leiten) bleiben unscharf.",
                                "antworten": ["stängel",
                                              "der stängel",
                                              "der stamm"],
                                "erklaerung": {
                                    "haken": "Wer holt das "
                                            "Wasser aus dem "
                                            "Boden — Wurzel "
                                            "oder Stängel?",
                                    "erkenntnis": "Die Wurzel "
                                    "ist unter der Erde: sie "
                                    "trinkt und hält die "
                                    "Pflanze fest. Der "
                                    "Stängel darüber trägt "
                                    "die Blätter und leitet "
                                    "das Wasser nach oben.",
                                    "regel": "Wurzel = trinken "
                                    "und festhalten (unten). "
                                    "Stängel = tragen und "
                                    "Wasser leiten (Mitte).",
                                    "bild": {"zeigt": "die "
                                             "Pflanze in drei "
                                             "Zonen: unten, "
                                             "Mitte, oben",
                                             "bewegt": "das "
                                             "Wasser steigt "
                                             "vom Boden durch "
                                             "den Stängel zum "
                                             "Blatt",
                                             "bleibt_gleich":
                                             "jeder Teil "
                                             "bleibt an "
                                             "seinem Platz"},
                                    "aufgabe": {"frage": "Was "
                                                "macht die "
                                                "Wurzel?",
                                                "loesung":
                                                "Sie nimmt "
                                                "Wasser auf "
                                                "und hält "
                                                "fest."}},
                                "visualisierung": _FLUSS(
                                    ["Wurzel: trinkt und "
                                     "hält fest",
                                     "Stängel: trägt und "
                                     "leitet Wasser hoch",
                                     "Blatt: fängt Licht "
                                     "und Luft"]),
                                "visualisierung_alternativ":
                                _TABELLE(
                                    ["Teil", "Ort", "Aufgabe"],
                                    ["Wurzel | unten | "
                                     "Wasser + Halt",
                                     "Stängel | Mitte | "
                                     "tragen + leiten",
                                     "Blatt | oben | Licht "
                                     "+ Luft"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Welcher Teil nimmt "
                                        "das Wasser auf?",
                                        "Die Wurzel",
                                        ["Der Stängel",
                                         "Das Blatt"],
                                        "Sie liegt im Boden "
                                        "— dort, wo das "
                                        "Wasser ist."),
                                    "beispiel": aufgabe(
                                        "Wasser wandert: "
                                        "Wurzel trinkt es, "
                                        "Stängel leitet es "
                                        "hoch, Blatt "
                                        "verwendet es.",
                                        "Wurzel trinkt, "
                                        "Stängel leitet."),
                                    "gefuehrt": aufgabe(
                                        "Welcher Teil leitet "
                                        "das Wasser vom "
                                        "Boden zum Blatt?",
                                        "Der Stängel",
                                        fehler="die wurzel",
                                        art="begriffe",
                                        rubrik=begriffe("staengel"),
                                        tipps=["Die Wurzel "
                                               "holt es — "
                                               "wer trägt es "
                                               "hoch?"]),
                                    "selbststaendig": aufgabe(
                                        "Welcher Teil hält "
                                        "die Pflanze im "
                                        "Boden fest?",
                                        "Die Wurzel",
                                        fehler="der stängel",
                                        art="begriffe",
                                        rubrik=begriffe("wurzel"),
                                        tipps=["Wo ist dieser "
                                               "Teil — über "
                                               "oder unter "
                                               "der Erde?"]),
                                    "transfer": auswahl(
                                        "Warum würde eine "
                                        "Pflanze ohne "
                                        "Stängel nicht "
                                        "überleben?",
                                        "Das Wasser käme "
                                        "nie von der Wurzel "
                                        "zum Blatt",
                                        ["Sie sähe "
                                         "hässlich aus",
                                         "Die Wurzel "
                                         "verdurstet"],
                                        "Jeder Teil hat "
                                        "eine Aufgabe — "
                                        "ohne Transport "
                                        "verhungert der "
                                        "Rest.")}},
                            {
                                "key": "blatt_ist_deko",
                                "label": "Blatt wird zur "
                                         "Dekoration",
                                "beschreibung": "Die Blätter "
                                "gelten als schmückendes "
                                "Beiwerk — ihre Arbeitsrolle "
                                "bleibt unsichtbar.",
                                "antworten": ["schön aussehen",
                                              "nur zum "
                                              "aussehen",
                                              "grün machen"],
                                "erklaerung": {
                                    "haken": "Ein Blatt ist "
                                            "breit, flach "
                                            "und nach oben "
                                            "geöffnet — wie "
                                            "eine "
                                            "Solaranlage.",
                                    "erkenntnis": "Das Blatt "
                                    "ist die Werkstatt: es "
                                    "fängt Licht und holt "
                                    "ein Gas aus der Luft. "
                                    "Ohne Blätter kein "
                                    "Futter.",
                                    "regel": "Blatt = die "
                                    "Arbeitsfläche der "
                                    "Pflanze: Licht "
                                    "fangen, Luft holen, "
                                    "Futter bauen.",
                                    "bild": {"zeigt": "das "
                                             "Blatt mit "
                                             "Lichtstrahlen "
                                             "und Luftpfeilen",
                                             "bewegt": "die "
                                             "Bausteine "
                                             "entstehen in "
                                             "seiner "
                                             "Werkstatt",
                                             "bleibt_gleich":
                                             "die Wurzel "
                                             "liefert "
                                             "weiter "
                                             "Wasser"},
                                    "aufgabe": {"frage":
                                                "Was macht "
                                                "das Blatt?",
                                                "loesung":
                                                "Es fängt "
                                                "Licht und "
                                                "holt Luft."}},
                                "visualisierung": _NETZ(
                                    ["Blatt", "Licht fangen",
                                     "Luft holen",
                                     "Futter bauen"],
                                    ["Blatt → Licht fangen",
                                     "Blatt → Luft holen",
                                     "Blatt → Futter bauen"]),
                                "visualisierung_alternativ":
                                _FLUSS(
                                    ["Blatt breitet sich "
                                     "aus",
                                     "fängt Licht",
                                     "holt Gas aus der "
                                     "Luft",
                                     "baut Futter"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was ist die "
                                        "Aufgabe des "
                                        "Blattes?",
                                        "Licht fangen und "
                                        "Luft holen",
                                        ["Nur hübsch "
                                         "aussehen",
                                         "Die Pflanze "
                                         "kühlen"],
                                        "Die breite "
                                        "Fläche hat einen "
                                        "Grund — sie "
                                        "arbeitet."),
                                    "beispiel": aufgabe(
                                        "Das Blatt ist "
                                        "flach und nach "
                                        "oben gerichtet — "
                                        "perfekt, um "
                                        "Licht zu "
                                        "fangen.",
                                        "Es fängt Licht."),
                                    "gefuehrt": aufgabe(
                                        "Welcher Teil "
                                        "arbeitet wie "
                                        "eine "
                                        "Solaranlage?",
                                        "Das Blatt",
                                        fehler="die wurzel",
                                        art="begriffe",
                                        rubrik=begriffe("blatt"),
                                        tipps=["Es liegt "
                                               "dem Licht "
                                               "zugewandt."]),
                                    "selbststaendig": aufgabe(
                                        "Welcher Teil "
                                        "holt das Gas aus "
                                        "der Luft?",
                                        "Das Blatt",
                                        fehler="die wurzel",
                                        art="begriffe",
                                        rubrik=begriffe("blatt"),
                                        tipps=["Woher "
                                               "kommt die "
                                               "Luft — aus "
                                               "Boden oder "
                                               "oben?"]),
                                    "transfer": auswahl(
                                        "Warum sind "
                                        "Blätter so "
                                        "breit und "
                                        "flach?",
                                        "Um möglichst "
                                        "viel Licht zu "
                                        "fangen",
                                        ["Damit Regen "
                                         "abläuft",
                                         "Damit sie "
                                         "schön sind"],
                                        "Die Form dient "
                                        "der Aufgabe — "
                                        "mehr Fläche "
                                        "fängt mehr "
                                        "Licht.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Drei Arbeiter, drei "
                                    "Aufgaben — welcher "
                                    "steht wo?",
                            "RULE": "Wurzel trinkt und "
                                    "hält fest, Stängel "
                                    "trägt und leitet, "
                                    "Blatt fängt Licht "
                                    "und Luft.",
                            "WORKED_EXAMPLE": "Folge dem "
                                    "Wasser: Boden → "
                                    "Wurzel → Stängel → "
                                    "Blatt.",
                            "GUIDED_TASK": "Über der Erde "
                                    "trägt, unter der "
                                    "Erde trinkt.",
                            "INDEPENDENT_TASK": "Jeder "
                                    "Teil hat eine "
                                    "Aufgabe — Form "
                                    "folgt Aufgabe.",
                            "ADAPTATION": "Die Tabelle "
                                    "ordnet jeden Teil "
                                    "seiner Aufgabe zu."}),
                        "faq": [
                            {"frage": "Was macht der "
                                      "Stängel?",
                             "antwort": "Er trägt die "
                                        "Blätter und "
                                        "leitet das "
                                        "Wasser von der "
                                        "Wurzel nach "
                                        "oben."},
                            {"frage": "Warum ist das "
                                      "Blatt so breit?",
                             "antwort": "Um viel Licht "
                                        "zu fangen — es "
                                        "ist die "
                                        "Arbeitsfläche "
                                        "der Pflanze."}],
                    }},
                # ---------------------------------- Fotosynthese
                {
                    "id": "BI.PFLANZEN.FOTOSYNTHESE",
                    "title": "Fotosynthese",
                    "description": "Licht + Wasser + CO₂ → "
                                   "Zucker + Sauerstoff — wie "
                                   "die Pflanze aus Licht ihr "
                                   "Futter baut und dabei "
                                   "unsere Luft macht.",
                    "first_contact_grade": 5, "target_grade": 7,
                    "prerequisites": ["BI.PFLANZEN.BEDUERFNISSE",
                                      "BI.PFLANZEN.AUFBAU"],
                    "levels": {
                        "below": "K4: Pflanzenteile und ihre "
                                 "Aufgaben, Bedürfnisse",
                        "target": "K6–7: Fotosynthese als "
                                  "Stoff- und Energieumwandlung",
                        "above": "K8: Chlorophyll, Zellatmung, "
                                 "Kreisläufe"},
                    "can_do": {
                        "below": ["die Teile der Pflanze und "
                                  "ihre Bedürfnisse nennen"],
                        "target": ["die Fotosynthese als "
                                   "Umbau von Licht, Wasser "
                                   "und CO₂ zu Zucker und O₂ "
                                   "erklären"],
                        "above": ["den Zusammenhang zur "
                                  "Atmung deuten"]},
                    "difficulty_parameters": {
                        "edukte": "Licht, Wasser, CO₂",
                        "produkte": "Zucker (Traubenzucker), O₂",
                        "ort": "Blatt (Chloroplasten)"},
                    "anchor_items": [
                        item("Was stellt die Pflanze bei der "
                             "Fotosynthese her?",
                             "Zucker und Sauerstoff",
                             level="target", grade=7,
                             answer=text("zucker und "
                                         "sauerstoff",
                                         "sauerstoff und "
                                         "zucker",
                                         "zucker sauerstoff")),
                        item("Welches Gas nimmt die Pflanze "
                             "für die Fotosynthese aus der "
                             "Luft auf?",
                             "Kohlenstoffdioxid (CO₂)",
                             level="target", grade=7,
                             answer=text("co2", "co₂",
                                         "kohlendioxid",
                                         "kohlenstoffdioxid"))],
                    "boundary_items": {
                        "below": [item("Welcher Teil nimmt "
                                       "das Wasser auf?",
                                       "Die Wurzel",
                                       level="below", grade=4,
                                       answer=text("wurzel"))],
                        "within": [item("Welches Gas gibt "
                                        "die Pflanze bei "
                                        "der Fotosynthese "
                                        "ab?",
                                        "Sauerstoff (O₂)",
                                        level="target",
                                        grade=7,
                                        answer=text("o2",
                                                    "o₂",
                                                    "sauerstoff"))],
                        "above": [item("Was braucht die "
                                       "Pflanze NACHTS zum "
                                       "Leben? (Hinweis: "
                                       "Atmung)",
                                       "Sauerstoff",
                                       level="above", grade=8,
                                       answer=text("sauerstoff",
                                                   "o2",
                                                   "o₂"))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "O₂ "
                             "und CO₂ werden vertauscht — "
                             "die Pflanze „atmet aus, was "
                             "wir einatmen“ wird auf den "
                             "Kopf gestellt.",
                             "remediation_hint": "Merksatz: "
                             "Pflanze nimmt CO₂, gibt O₂ — "
                             "das Gegenteil von uns.",
                             "diagnostic_item": item(
                                 "Welches Gas nimmt die "
                                 "Pflanze für die "
                                 "Fotosynthese auf?",
                                 "CO₂", level="target",
                                 grade=7,
                                 answer=choice("CO₂",
                                               ["O₂",
                                                "N₂"],
                                               ["F1", None]),
                                 distractors=[])},
                            {"key": "F2", "description": "Fotosynthese "
                             "wird zur Pflanzenatmung — "
                             "der Futterbau wird als "
                             "reines Atmen gelesen.",
                             "remediation_hint": "Atmung "
                             "setzt Energie frei — "
                             "Fotosynthese speichert sie "
                             "im Zucker. Zwei "
                             "verschiedene Vorgänge.",
                             "diagnostic_item": item(
                                 "Was macht die "
                                 "Fotosynthese?",
                                 "Sie baut Futter und "
                                 "speichert Lichtenergie",
                                 level="target", grade=7,
                                 answer=choice(
                                     "Futter bauen und "
                                     "Energie speichern",
                                     ["Die Pflanze "
                                      "atmen lassen",
                                      "Wasser "
                                      "verdunsten"],
                                     ["F2", None]),
                                 distractors=[])},
                            {"key": "F3", "description": "Licht "
                             "wird als Stoff gezählt — die "
                             "Pflanze „isst“ Licht wie "
                             "Wasser.",
                             "remediation_hint": "Licht "
                             "liefert die Energie, nicht "
                             "die Bausteine — Zucker "
                             "entsteht aus CO₂ und "
                             "Wasser.",
                             "diagnostic_item": item(
                                 "Welche Rolle spielt "
                                 "das Licht bei der "
                                 "Fotosynthese?",
                                 "Es liefert die "
                                 "Energie für den "
                                 "Umbau",
                                 level="target", grade=7,
                                 answer=choice("Energie "
                                               "liefern",
                                               ["Ein Stoff "
                                                "sein, aus "
                                                "dem Zucker "
                                                "entsteht",
                                                "Das Blatt "
                                                "wärmen"],
                                               ["F3",
                                                "F3"]),
                                 distractors=[])}],
                        "diagnostic_items": [
                            item("Welcher Teil der Pflanze "
                                 "fängt das Licht ein?",
                                 "Das Blatt", level="below",
                                 grade=4,
                                 answer=text("blatt",
                                             "das blatt")),
                            item("Was entsteht bei der "
                                 "Fotosynthese?",
                                 "Zucker und Sauerstoff",
                                 level="target", grade=7,
                                 answer=text("zucker und "
                                             "sauerstoff",
                                             "sauerstoff "
                                             "und zucker"))],
                        "exit_items": [
                            item("Schreibe die "
                                 "Fotosynthese als "
                                 "Wortgleichung.",
                                 "Licht + Wasser + CO₂ → "
                                 "Zucker + O₂",
                                 level="target", grade=7,
                                 answer=text(
                                     "licht wasser co2 "
                                     "zucker o2",
                                     "wasser und co2 "
                                     "werden zu zucker "
                                     "und sauerstoff")),
                            item("Warum ist die "
                                 "Fotosynthese für uns "
                                 "wichtig?",
                                 "Sie macht den "
                                 "Sauerstoff, den wir "
                                 "atmen.",
                                 level="target", grade=7,
                                 answer=text("sauerstoff",
                                             "sie macht "
                                             "sauerstoff",
                                             "weil sie "
                                             "sauerstoff "
                                             "macht"))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "fotosynthese",
                            "thema_key": "pflanzen",
                            "label": "Fotosynthese",
                            "klasse_von": 5, "klasse_bis": 8,
                            "stichworte": ["fotosynthese",
                                           "photosynthese",
                                           "pflanzen atmen",
                                           "co2 o2 pflanze",
                                           "licht pflanze futter"]},
                        "erstkontakt": {
                            "anker": "Du atmest gerade — "
                                     "woher kommt der "
                                     "Sauerstoff in deiner "
                                     "Luft?",
                            "benennung": "Fotosynthese",
                            "erste_aufgabe": {"frage": "Was "
                                              "stellt die "
                                              "Pflanze bei "
                                              "der "
                                              "Fotosynthese "
                                              "her?",
                                              "loesung":
                                              "Zucker und "
                                              "Sauerstoff"}},
                        "fehlertypen": [
                            {
                                "key": "gase_vertauscht",
                                "label": "CO₂ und O₂ "
                                         "vertauscht",
                                "beschreibung": "Die "
                                "Pflanze nimmt angeblich "
                                "unseren Sauerstoff und "
                                "gibt CO₂ ab — die "
                                "Gasrichtungen sitzen "
                                "falsch herum.",
                                "antworten": ["sauerstoff "
                                              "aufnehmen",
                                              "o2 aufnehmen",
                                              "o2",
                                              "co2 abgeben"],
                                "erklaerung": {
                                    "haken": "Die Pflanze "
                                            "macht mit "
                                            "Gasen genau "
                                            "das "
                                            "Gegenteil "
                                            "von uns — "
                                            "die "
                                            "Richtungen "
                                            "verwechseln "
                                            "sich "
                                            "leicht.",
                                    "erkenntnis": "Wir "
                                    "atmen O₂ ein und "
                                    "CO₂ aus. Die "
                                    "Pflanze dreht es "
                                    "um: sie nimmt CO₂ "
                                    "und gibt O₂ ab — "
                                    "unseren "
                                    "Atemstoff.",
                                    "regel": "Pflanze: "
                                    "CO₂ rein, O₂ "
                                    "raus. Merkhilfe: "
                                    "sie macht, was "
                                    "wir brauchen — "
                                    "und nimmt, was "
                                    "wir abgeben.",
                                    "bild": {"zeigt": "die "
                                             "Pflanze "
                                             "zwischen "
                                             "zwei "
                                             "Gasströmen",
                                             "bewegt":
                                             "CO₂ "
                                             "hinein, "
                                             "O₂ "
                                             "hinaus — "
                                             "in "
                                             "Pfeilen",
                                             "bleibt_gleich":
                                             "die "
                                             "Menge "
                                             "bleibt "
                                             "erhalten"},
                                    "aufgabe": {"frage":
                                                "Welches "
                                                "Gas "
                                                "gibt "
                                                "die "
                                                "Pflanze "
                                                "ab?",
                                                "loesung":
                                                "Sauerstoff "
                                                "(O₂)"}},
                                "visualisierung": _NETZ(
                                    ["Pflanze",
                                     "CO₂ hinein",
                                     "O₂ hinaus",
                                     "Zucker"],
                                    ["CO₂ → Pflanze",
                                     "Pflanze → O₂",
                                     "Pflanze → Zucker"]),
                                "visualisierung_alternativ":
                                _TABELLE(
                                    ["Wer", "nimmt "
                                     "auf", "gibt ab"],
                                    ["Pflanze | CO₂ | O₂",
                                     "Mensch | O₂ | "
                                     "CO₂"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Welches Gas "
                                        "nimmt die "
                                        "Pflanze für "
                                        "die "
                                        "Fotosynthese "
                                        "auf?",
                                        "CO₂",
                                        ["O₂", "N₂"],
                                        "Sie nimmt, "
                                        "was wir "
                                        "ausatmen — "
                                        "und gibt "
                                        "unseren "
                                        "Atemstoff "
                                        "zurück."),
                                    "beispiel": aufgabe(
                                        "Wortgleichung: "
                                        "Licht + "
                                        "Wasser + "
                                        "CO₂ → "
                                        "Zucker + "
                                        "O₂. CO₂ "
                                        "hinein, O₂ "
                                        "hinaus.",
                                        "Zucker + O₂"),
                                    "gefuehrt": aufgabe(
                                        "Welches Gas "
                                        "entsteht bei "
                                        "der "
                                        "Fotosynthese?",
                                        "Sauerstoff "
                                        "(O₂)",
                                        fehler="CO₂",
                                        art="begriffe",
                                        rubrik=begriffe("sauerstoff"),
                                        tipps=["Was "
                                               "brauchen "
                                               "wir zum "
                                               "Atmen?",
                                               "Die "
                                               "Pflanze "
                                               "gibt es "
                                               "ab."]),
                                    "selbststaendig": aufgabe(
                                        "Welches Gas "
                                        "verbraucht "
                                        "die Pflanze "
                                        "bei der "
                                        "Fotosynthese?",
                                        "CO₂",
                                        fehler="O₂",
                                        art="begriffe",
                                        rubrik=begriffe(("co2", "kohlendioxid", "kohlenstoffdioxid"),),
                                        tipps=["Gegenteil "
                                               "von "
                                               "uns."]),
                                    "transfer": auswahl(
                                        "Warum ist es "
                                        "gut für uns, "
                                        "dass die "
                                        "Pflanze "
                                        "„verkehrt "
                                        "herum“ "
                                        "arbeitet?",
                                        "Sie baut "
                                        "unseren "
                                        "Sauerstoff "
                                        "— unsere "
                                        "Kreisläufe "
                                        "passen "
                                        "zusammen",
                                        ["Sie braucht "
                                         "weniger "
                                         "Luft",
                                         "Zufall"],
                                        "Kreislauf: "
                                        "unsere Abgabe "
                                        "ist ihre "
                                        "Zufuhr — und "
                                        "umgekehrt.")}},
                            {
                                "key": "fotosynthese_ist_atmung",
                                "label": "Fotosynthese "
                                         "wird zur "
                                         "Atmung",
                                "beschreibung": "Gas-"
                                "Austausch und Futterbau "
                                "werfen sich auf einen "
                                "Vorgang — die Pflanze "
                                "„atmet“ ihr Futter.",
                                "antworten": ["sie atmet",
                                              "pflanzenatmung",
                                              "atmen"],
                                "erklaerung": {
                                    "haken": "Die Pflanze "
                                            "„atmet“ "
                                            "CO₂ — ist "
                                            "Fotosynthese "
                                            "nur ihr "
                                            "Atmen? "
                                            "Dann "
                                            "würde sie "
                                            "nie "
                                            "wachsen.",
                                    "erkenntnis": "Atmen "
                                    "setzt Energie "
                                    "frei — "
                                    "Fotosynthese "
                                    "speichert sie. "
                                    "Das eine baut "
                                    "Futter, das "
                                    "andere "
                                    "verbraucht "
                                    "es.",
                                    "regel": "Fotosynthese "
                                    "= Bauen: "
                                    "Lichtenergie "
                                    "wird im Zucker "
                                    "gespeichert. "
                                    "Atmung = "
                                    "Verbrennen: "
                                    "Energie wird "
                                    "frei.",
                                    "bild": {"zeigt":
                                             "zwei "
                                             "gegenläufige "
                                             "Pfeile "
                                             "im Blatt",
                                             "bewegt":
                                             "der "
                                             "Aufbau-"
                                             "Pfeil "
                                             "füllt "
                                             "den "
                                             "Speicher, "
                                             "der "
                                             "Atmungs-"
                                             "Pfeil "
                                             "entleert "
                                             "ihn",
                                             "bleibt_gleich":
                                             "die "
                                             "Pflanze "
                                             "bleibt "
                                             "dieselbe"},
                                    "aufgabe": {"frage":
                                                "Speichert "
                                                "die "
                                                "Fotosynthese "
                                                "Energie "
                                                "oder "
                                                "gibt "
                                                "sie sie "
                                                "frei?",
                                                "loesung":
                                                "Sie "
                                                "speichert "
                                                "sie."}},
                                "visualisierung": _FLUSS(
                                    ["Fotosynthese: "
                                     "bauen",
                                     "Lichtenergie → "
                                     "in Zucker "
                                     "gespeichert",
                                     "Atmung: "
                                     "verbrennen",
                                     "Zucker → "
                                     "Energie frei"]),
                                "visualisierung_alternativ":
                                _TABELLE(
                                    ["Vorgang", "was "
                                     "passiert"],
                                    ["Fotosynthese | "
                                     "Futter bauen, "
                                     "Energie "
                                     "speichern",
                                     "Atmung | "
                                     "Futter "
                                     "verbrennen, "
                                     "Energie frei"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Was macht "
                                        "die "
                                        "Fotosynthese?",
                                        "Sie baut "
                                        "Futter und "
                                        "speichert "
                                        "Lichtenergie",
                                        ["Sie lässt "
                                         "die "
                                         "Pflanze "
                                         "atmen",
                                         "Sie "
                                         "verdunstet "
                                         "Wasser"],
                                        "Sie ist ein "
                                        "Aufbau — "
                                        "keine "
                                        "Verbrennung."),
                                    "beispiel": aufgabe(
                                        "Wie ein "
                                        "Sparbuch: "
                                        "die "
                                        "Fotosynthese "
                                        "legt "
                                        "Lichtenergie "
                                        "im Zucker "
                                        "an, die "
                                        "Atmung "
                                        "hebt sie "
                                        "ab.",
                                        "Energie "
                                        "speichern."),
                                    "gefuehrt": aufgabe(
                                        "Speichert "
                                        "die "
                                        "Fotosynthese "
                                        "Energie "
                                        "oder gibt "
                                        "sie sie "
                                        "frei?",
                                        "Sie "
                                        "speichert "
                                        "sie im "
                                        "Zucker.",
                                        fehler="sie "
                                               "gibt "
                                               "sie "
                                               "frei",
                                        art="begriffe",
                                        rubrik=begriffe("zucker"),
                                        tipps=["Aufbau "
                                               "oder "
                                               "Verbrennung?",
                                               "Wohin "
                                               "geht "
                                               "die "
                                               "Lichtenergie?"]),
                                    "selbststaendig": aufgabe(
                                        "Erkläre den "
                                        "Unterschied "
                                        "zwischen "
                                        "Fotosynthese "
                                        "und Atmung "
                                        "in einem "
                                        "Satz.",
                                        "Fotosynthese "
                                        "baut "
                                        "Futter und "
                                        "speichert "
                                        "Energie, "
                                        "Atmung "
                                        "setzt sie "
                                        "frei.",
                                        fehler="beide "
                                               "sind "
                                               "atmen",
                                        art="begriffe",
                                        rubrik={
                                            "begriffe": [
                                                "futter",
                                                "speicher",
                                                "energie",
                                                "frei",
                                                "bau",
                                                "zucker"],
                                            "mindestens": 3,
                                            "hinweise": {
                                                "teilweise":
                                                    "Ein "
                                                    "Teil "
                                                    "stimmt — "
                                                    "beschreibe "
                                                    "auch "
                                                    "den "
                                                    "anderen "
                                                    "Vorgang."}},
                                        tipps=["Eins "
                                               "baut, "
                                               "eins "
                                               "verbrennt."]),
                                    "transfer": auswahl(
                                        "Nachts kann "
                                        "die "
                                        "Pflanze "
                                        "keine "
                                        "Fotosynthese "
                                        "machen — "
                                        "stirbt sie?",
                                        "Nein — sie "
                                        "atmet und "
                                        "lebt vom "
                                        "gespeicherten "
                                        "Zucker",
                                        ["Ja, ohne "
                                         "Licht "
                                         "stirbt sie",
                                         "Sie "
                                         "schläft "
                                         "nur"],
                                        "Tagsüber "
                                        "wird "
                                        "gespeichert, "
                                        "nachts "
                                        "davon "
                                        "gelebt — "
                                        "das "
                                        "Sparbuch-"
                                        "Prinzip.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Die Pflanze arbeitet "
                                    "verkehrt herum — "
                                    "und genau das "
                                    "rettet uns.",
                            "RULE": "CO₂ rein, O₂ "
                                    "raus — Licht "
                                    "liefert die "
                                    "Energie, Zucker "
                                    "speichert sie.",
                            "WORKED_EXAMPLE": "Wortgleichung "
                                    "lesen: links "
                                    "kommt rein, "
                                    "rechts kommt "
                                    "raus.",
                            "GUIDED_TASK": "Wir atmen "
                                    "umgekehrt — die "
                                    "Pflanze dreht "
                                    "das Rad "
                                    "zurück.",
                            "INDEPENDENT_TASK": "Fotosynthese "
                                    "ist Bauen, "
                                    "Atmung ist "
                                    "Verbrennen — "
                                    "nicht "
                                    "dasselbe.",
                            "ADAPTATION": "Das Netz "
                                    "zeigt die "
                                    "Gasströme in "
                                    "beide "
                                    "Richtungen."}),
                        "faq": [
                            {"frage": "Atmen Pflanzen "
                                      "auch?",
                             "antwort": "Ja — aber "
                                        "Atmung ist "
                                        "etwas anderes "
                                        "als "
                                        "Fotosynthese: "
                                        "das eine "
                                        "verbrennt "
                                        "Futter, das "
                                        "andere baut "
                                        "es."},
                            {"frage": "Wo findet die "
                                      "Fotosynthese "
                                      "statt?",
                             "antwort": "Im Blatt — "
                                        "in den "
                                        "Chloroplasten, "
                                        "den "
                                        "Werkstätten "
                                        "mit dem "
                                        "grünen "
                                        "Farbstoff."}],
                    }},
            ]},
    ]}
