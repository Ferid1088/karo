"""Physik-Slice: von Masse und Volumen zur Dichte.

Level 0: das Kind trennt „schwer“ und „groß" — Masse ist, was die Waage
zeigt. Dann Volumen als Platz, dann das „pro“-Denken — und erst dann
ist Dichte mehr als eine Formel.

    PH.GROESSEN.DICHTE        (Ziel, Kl. 6–7)
      └── PH.RECHNEN.PRO          (Kl. 5–6)
            ├── PH.MATERIAL.VOLUMEN   (Kl. 4–5)
            └── PH.MATERIAL.MASSE     (Kl. 2–3, Level 0)
"""

from __future__ import annotations

from ._bauen import begriffe, aufgabe, auswahl, choice, item, number, text

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
    "fach": "physik",
    "code": "PH",
    "name": "Physik",
    "blocks": [{
        "id": "PH.MATERIAL",
        "title": "Körper und ihre Eigenschaften",
        "description": "Masse, Volumen und die Frage, was ein Ding "
                       "„wiegt“ und „ausfüllt“ — bis zur Dichte.",
        "grade_min": 2, "grade_max": 8, "typical_grade": 5,
        "concepts": [
            # ---------------------------------------------- Level 0
            {
                "id": "PH.MATERIAL.MASSE",
                "title": "Masse — wie schwer etwas ist",
                "description": "Masse als das, was die Waage anzeigt — "
                               "gemessen in Gramm und Kilogramm.",
                "first_contact_grade": 2, "target_grade": 3,
                "prerequisites": [],
                "levels": {
                    "below": "K1–2: schwer und leicht fühlen",
                    "target": "K3: Masse mit der Waage messen, g und kg",
                    "above": "K4–5: Volumen getrennt von Masse"},
                "can_do": {
                    "below": ["schwere und leichte Dinge unterscheiden"],
                    "target": ["Masse in g und kg angeben und ein "
                               "Kilogramm richtig einschätzen"],
                    "above": ["Masse und Volumen auseinanderhalten"]},
                "difficulty_parameters": {
                    "einheiten": "g, kg",
                    "geraet": "Waage",
                    "vergleiche": "1 kg Mehl, Feder, Stein"},
                "anchor_items": [
                    item("Was misst die Waage?",
                         "Die Masse", level="target", grade=3,
                         answer=text("masse", "die masse",
                                     "wie schwer", "gewicht")),
                    item("Wie viel Gramm ist ein Kilogramm?",
                         "1000", level="target", grade=3,
                         answer=number("1000"))],
                "boundary_items": {
                    "below": [item("Was ist schwerer: eine Feder oder "
                                   "ein Stein?", "Der Stein",
                                   level="below", grade=2,
                                   answer=text("stein", "der stein"))],
                    "within": [item("In welcher Einheit wiegt man "
                                    "einen Apfel?",
                                    "Gramm", level="target", grade=3,
                                    answer=text("gramm", "g"))],
                    "above": [item("Was ist mehr: 1 kg Federn oder "
                                   "1 kg Stein?",
                                   "Gleich viel", level="above",
                                   grade=5,
                                   answer=text("gleich",
                                               "gleich viel",
                                               "beide gleich"))]},
                "diagnostics": {
                    "misconceptions": [
                        {"key": "F1", "description": "Groß heißt "
                         "schwer: ein großer leichter Gegenstand "
                         "wird für schwerer gehalten als ein "
                         "kleiner schwerer.",
                         "remediation_hint": "Die Waage zählt, nicht "
                         "die Größe — wiegen entscheidet.",
                         "diagnostic_item": item(
                             "Ein großer Luftballon und eine kleine "
                             "Bleikugel — was ist schwerer?",
                             "Die Bleikugel", level="target", grade=3,
                             answer=choice("Die Bleikugel",
                                           ["Der Luftballon",
                                            "Gleich schwer"],
                                           ["F1", "F1"]),
                             distractors=[])},
                        {"key": "F2", "description": "Ein Kilogramm "
                         "wird als viel größer eingeschätzt — 100 g "
                         "gelten schon als „ein Kilo“.",
                         "remediation_hint": "1 kg = 1000 g — ein "
                         "Päckchen Mehl ist das Gefühl dafür.",
                         "diagnostic_item": item(
                             "Was wiegt ungefähr ein Kilogramm?",
                             "Eine Packung Mehl", level="target",
                             grade=3,
                             answer=choice("Eine Packung Mehl",
                                           ["Eine Feder",
                                            "Ein Apfel"],
                                           ["F2", "F2"]),
                             distractors=[])}],
                    "diagnostic_items": [
                        item("Ist ein Fußball schwerer als ein "
                             "Tischtennisball?", "Ja",
                             level="below", grade=2,
                             answer=text("ja")),
                        item("Womit misst man, wie schwer etwas "
                             "ist?", "Mit einer Waage",
                             level="target", grade=3,
                             answer=text("waage", "mit einer waage"))],
                    "exit_items": [
                        item("Wie viel Gramm sind 2 Kilogramm?",
                             "2000", level="target", grade=3,
                             answer=number("2000")),
                        item("Ordne der Masse nach: Feder, Apfel, "
                             "Packung Mehl",
                             "Feder, Apfel, Mehl", level="target",
                             grade=3,
                             answer=text("feder apfel mehl",
                                         "feder, apfel, mehl"))]},
                "lektion": {
                    "konzept": {
                        "konzept_key": "masse",
                        "thema_key": "material",
                        "label": "Masse — wie schwer etwas ist",
                        "klasse_von": 2, "klasse_bis": 4,
                        "stichworte": ["masse", "wie schwer",
                                       "waage", "kilogramm",
                                       "gramm", "wiegen"]},
                    "erstkontakt": {
                        "anker": "Ein riesiger Luftballon und eine "
                                 "winzige Bleikugel — was zeigt die "
                                 "Waage weiter rechts?",
                        "benennung": "Masse",
                        "erste_aufgabe": {"frage": "Womit misst man, "
                                          "wie schwer etwas ist?",
                                          "loesung": "Mit einer "
                                                     "Waage"}},
                    "fehlertypen": [
                        {
                            "key": "gross_ist_schwer",
                            "label": "Groß wird zu schwer",
                            "beschreibung": "Die Größe entscheidet "
                            "über das vermutete Gewicht — der "
                            "Ballon soll schwerer sein als die "
                            "Kugel.",
                            "antworten": ["der ballon",
                                          "der große",
                                          "das große"],
                            "erklaerung": {
                                "haken": "Der Luftballon füllt den "
                                        "Arm — und die Waage "
                                        "interessiert das nicht. "
                                        "Warum?",
                                "erkenntnis": "Die Masse ist, wie "
                                "viel Stoff in etwas steckt — nicht "
                                "wie viel Platz es einnimmt. Blei "
                                "steckt viel Stoff auf kleinem "
                                "Raum.",
                                "regel": "Masse = Stoffmenge, "
                                "gemessen mit der Waage in Gramm "
                                "und Kilogramm. Größe sagt nichts "
                                "über die Masse.",
                                "bild": {"zeigt": "Ballon und "
                                         "Bleikugel auf zwei "
                                         "Waagschalen",
                                         "bewegt": "die Bleikugel "
                                         "senkt ihre Schale",
                                         "bleibt_gleich": "die "
                                         "Größen bleiben "
                                         "verschieden"},
                                "aufgabe": {"frage": "Was ist "
                                            "schwerer: eine Tüte "
                                            "Chips oder ein "
                                            "Apfel?",
                                            "loesung": "Der Apfel"}},
                            "visualisierung": _TABELLE(
                                ["Ding", "vermutet", "Waage"],
                                ["Luftballon | schwer | fast nichts",
                                 "Bleikugel | leicht | viel"]),
                            "visualisierung_alternativ": _FLUSS(
                                ["Vermuten: was ist schwerer?",
                                 "Wiegen: die Waage entscheidet",
                                 "Bleikugel gewinnt trotz "
                                 "Kleinheit"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Was ist schwerer: ein großer "
                                    "Luftballon oder eine kleine "
                                    "Bleikugel?",
                                    "Die Bleikugel",
                                    ["Der Luftballon",
                                     "Gleich schwer"],
                                    "Die Masse steckt im Stoff, "
                                    "nicht in der Größe."),
                                "beispiel": aufgabe(
                                    "Auf der Waage: der Ballon "
                                    "zeigt fast nichts, die "
                                    "Bleikugel drückt die Schale "
                                    "runter.",
                                    "Die Bleikugel ist "
                                    "schwerer."),
                                "gefuehrt": aufgabe(
                                    "Was ist schwerer: ein "
                                    "großer Kissen oder ein "
                                    "kleiner Hammer? Antworte "
                                    "mit dem Wort.",
                                    "Der Hammer",
                                    fehler="das Kissen",
                                    art="begriffe",
                                    rubrik=begriffe("hammer"),
                                    tipps=["Was wiegt eine "
                                           "Waage — Stoff oder "
                                           "Größe?"]),
                                "selbststaendig": aufgabe(
                                    "Was ist schwerer: ein "
                                    "Schaumstoffblock oder ein "
                                    "Handy?",
                                    "Das Handy",
                                    fehler="der Schaumstoff",
                                    art="begriffe",
                                    rubrik=begriffe("handy"),
                                    tipps=["Welcher hat mehr "
                                           "Stoff pro Platz?"]),
                                "transfer": auswahl(
                                    "Warum trügt das Auge beim "
                                    "Vergleich Ballon–Bleikugel?",
                                    "Das Auge misst Platz — die "
                                    "Waage misst Stoffmenge",
                                    ["Blei ist glänzend",
                                     "Der Ballon ist zu rund"],
                                    "Masse und Größe sind zwei "
                                    "verschiedene Dinge.")}},
                        {
                            "key": "kilo_ist_wenig",
                            "label": "Ein Kilogramm wird "
                                     "unterschätzt",
                            "beschreibung": "100 Gramm gelten "
                            "schon als „ein Kilo“ — die "
                            "Größenordnung fehlt.",
                            "antworten": ["100 g", "ein apfel",
                                          "eine tafel"],
                            "erklaerung": {
                                "haken": "„Ein Kilo“ klingt "
                                        "klein — aber ein "
                                        "Päckchen Mehl drückt "
                                        "schon ordentlich in "
                                        "die Hand.",
                                "erkenntnis": "Kilo heißt "
                                "tausend: 1 kg = 1000 g. Ein "
                                "Apfel sind etwa 150 g — ein "
                                "Kilo ist viel mehr.",
                                "regel": "1 kg = 1000 g. "
                                "Anker: eine Packung Mehl "
                                "oder eine Flasche Wasser.",
                                "bild": {"zeigt": "die "
                                         "Waagschale mit "
                                         "einem Kilo-"
                                         "Gewicht und "
                                         "daneben ein "
                                         "Apfel",
                                         "bewegt": "viele "
                                         "Äpfel türmen sich "
                                         "bis die Schale "
                                         "ausgleicht",
                                         "bleibt_gleich":
                                         "das Kilo bleibt "
                                         "das Kilo"},
                                "aufgabe": {"frage": "Wie "
                                            "viele Äpfel à "
                                            "ca. 250 g sind "
                                            "ein Kilogramm?",
                                            "loesung": "4"}},
                            "visualisierung": _TABELLE(
                                ["Ding", "Masse"],
                                ["Feder | wenige Gramm",
                                 "Apfel | ca. 150 g",
                                 "Packung Mehl | 1000 g = "
                                 "1 kg"]),
                            "visualisierung_alternativ":
                            _FLUSS(
                                ["100 g — eine Tafel "
                                 "Schokolade",
                                 "1000 g — eine Packung "
                                 "Mehl",
                                 "1 kg = 1000 g"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Was wiegt ungefähr ein "
                                    "Kilogramm?",
                                    "Eine Packung Mehl",
                                    ["Eine Feder",
                                     "Eine Tafel "
                                     "Schokolade"],
                                    "Ein Kilo = 1000 Gramm "
                                    "— ein Päckchen Mehl "
                                    "ist das Gefühl dafür."),
                                "beispiel": aufgabe(
                                    "10 Tafeln à 100 g = "
                                    "1000 g = 1 kg. Ein "
                                    "Kilo ist zehnmal eine "
                                    "Tafel.",
                                    "1000 g = 1 kg"),
                                "gefuehrt": aufgabe(
                                    "Wie viel Gramm ist ein "
                                    "Kilogramm?",
                                    "1000",
                                    fehler="100",
                                    art="zahl",
                                    tipps=["Kilo heißt "
                                           "tausend."]),
                                "selbststaendig": aufgabe(
                                    "Wie viel Gramm sind "
                                    "3 Kilogramm?",
                                    "3000",
                                    fehler="300",
                                    art="zahl",
                                    tipps=["Pro Kilo "
                                           "1000 g."]),
                                "transfer": auswahl(
                                    "Warum wiegt ein "
                                    "Zentner (100 kg) so "
                                    "viel mehr als ein "
                                    "Kilogramm?",
                                    "Er ist 100 Packungen "
                                    "Mehl — 100-mal das "
                                    "Kilo",
                                    ["Er ist einfach "
                                     "groß",
                                     "Er wiegt doppelt "
                                     "so viel"],
                                    "Einheiten stapeln "
                                    "sich: Kilo = 1000 g, "
                                    "Zentner = 100 kg.")}},
                    ],
                    "hilfe": _hilfe({
                        "HOOK": "Die Waage misst Stoff — "
                                "nicht Platz.",
                        "RULE": "Masse = wie viel Stoff "
                                "steckt drin. Gemessen in "
                                "g und kg: 1 kg = 1000 g.",
                        "WORKED_EXAMPLE": "Erst schätzen, "
                                "dann wiegen — die Waage "
                                "entscheidet.",
                        "GUIDED_TASK": "Denk an die "
                                "Packung Mehl — das ist "
                                "dein Kilo.",
                        "INDEPENDENT_TASK": "Größe "
                                "täuscht — Masse zählt "
                                "Stoff, nicht Platz.",
                        "ADAPTATION": "Die Tabelle "
                                "vergleicht Ding und "
                                "Masse."}),
                    "faq": [
                        {"frage": "Ist Gewicht dasselbe "
                                  "wie Masse?",
                         "antwort": "Im Alltag ja — "
                                    "beides meint, was "
                                    "die Waage zeigt. "
                                    "Genau genommen ist "
                                    "Gewicht die Kraft, "
                                    "Masse die "
                                    "Stoffmenge."},
                        {"frage": "Wie viel ist ein "
                                  "Kilogramm?",
                         "antwort": "1000 Gramm — eine "
                                    "Packung Mehl oder "
                                    "eine volle "
                                    "Wasserflasche."}],
                }},
            # -------------------------------------------- Volumen
            {
                "id": "PH.MATERIAL.VOLUMEN",
                "title": "Volumen — wie viel Platz etwas braucht",
                "description": "Volumen als der Raum, den ein "
                               "Körper einnimmt — gemessen in "
                               "Litern und Kubikzentimetern.",
                "first_contact_grade": 4, "target_grade": 5,
                "prerequisites": ["PH.MATERIAL.MASSE"],
                "levels": {
                    "below": "K3: Masse getrennt von Größe",
                    "target": "K5: Volumen messen und in "
                              "Liter/cm³ angeben",
                    "above": "K6: Verdrängungsmethode und "
                             "Dichte"},
                "can_do": {
                    "below": ["Masse von Größe trennen"],
                    "target": ["das Volumen von Körpern "
                               "vergleichen und in l oder "
                               "cm³ angeben"],
                    "above": ["Volumen durch Wasser-"
                              "Verdrängung messen"]},
                "difficulty_parameters": {
                    "einheiten": "ml, l, cm³",
                    "methode": "Abmessen, Verdrängung"},
                "anchor_items": [
                    item("Was misst ein Messbecher?",
                         "Das Volumen einer Flüssigkeit",
                         level="target", grade=5,
                         answer=text("volumen",
                                     "das volumen",
                                     "wie viel flüssigkeit")),
                    item("Wie viel Milliliter ist ein "
                         "Liter?", "1000",
                         level="target", grade=5,
                         answer=number("1000"))],
                "boundary_items": {
                    "below": [item("Was misst die Waage?",
                                   "Die Masse", level="below",
                                   grade=3,
                                   answer=text("masse",
                                               "die masse"))],
                    "within": [item("Was nimmt mehr Platz "
                                    "ein: ein Fußball oder "
                                    "ein Golfball?",
                                    "Der Fußball",
                                    level="target", grade=5,
                                    answer=text("fußball",
                                                "der "
                                                "fußball"))],
                    "above": [item("Ein Stein verdrängt 50 "
                                   "ml Wasser — wie groß "
                                   "ist sein Volumen?",
                                   "50 cm³", level="above",
                                   grade=6,
                                   answer=text("50 cm3",
                                               "50 cm³",
                                               "50"))]},
                "diagnostics": {
                    "misconceptions": [
                        {"key": "F1", "description": "Volumen "
                         "und Masse werden verwechselt — "
                         "„viel Platz“ heißt „viel Gewicht“.",
                         "remediation_hint": "Platz und "
                         "Stoff sind zwei verschiedene "
                         "Messungen — Ballon versus "
                         "Bleikugel.",
                         "diagnostic_item": item(
                             "Ein großer leichter "
                             "Schaumstoff und eine "
                             "kleine schwere Kugel — "
                             "was hat mehr Volumen?",
                             "Der Schaumstoff",
                             level="target", grade=5,
                             answer=choice("Der Schaumstoff",
                                           ["Die Kugel",
                                            "Gleich"],
                                           ["F1", "F1"]),
                             distractors=[])},
                        {"key": "F2", "description": "Die "
                         "Form täuscht: ausgestreckter "
                         "Ton scheint mehr Volumen zu "
                         "haben als die Kugel daraus.",
                         "remediation_hint": "Verdrängen "
                         "prüft den wahren Platz — Form "
                         "ändert das Volumen nicht.",
                         "diagnostic_item": item(
                             "Ein Tonklumpen wird zur "
                             "Kugel gerollt und dann "
                             "flach gedrückt — was "
                             "passiert mit dem Volumen?",
                             "Es bleibt gleich",
                             level="target", grade=5,
                             answer=choice("Es bleibt "
                                           "gleich",
                                           ["Es wird "
                                            "größer",
                                            "Es wird "
                                            "kleiner"],
                                           ["F2", "F2"]),
                             distractors=[])}],
                    "diagnostic_items": [
                        item("Womit misst man Masse?",
                             "Mit der Waage",
                             level="below", grade=3,
                             answer=text("waage")),
                        item("Welches Gefäß passt am "
                             "besten, um 250 ml "
                             "abzumessen?",
                             "Der Messbecher",
                             level="target", grade=5,
                             answer=text("messbecher",
                                         "der messbecher"))],
                    "exit_items": [
                        item("Wie viel Milliliter sind "
                             "2 Liter?", "2000",
                             level="target", grade=5,
                             answer=number("2000")),
                        item("Ein Körper verdrängt 30 ml "
                             "Wasser — sein Volumen?",
                             "30 cm³", level="target",
                             grade=5,
                             answer=text("30 cm3",
                                         "30 cm³",
                                         "30"))]},
                "lektion": {
                    "konzept": {
                        "konzept_key": "volumen",
                        "thema_key": "material",
                        "label": "Volumen — der Platz eines "
                                 "Körpers",
                        "klasse_von": 4, "klasse_bis": 6,
                        "stichworte": ["volumen",
                                       "wie viel platz",
                                       "messbecher", "liter",
                                       "verdrängung"]},
                    "erstkontakt": {
                        "anker": "Ein Stein fällt ins "
                                 "Glas — das Wasser steigt. "
                                 "Warum?",
                        "benennung": "Volumen",
                        "erste_aufgabe": {"frage": "Was "
                                          "misst ein "
                                          "Messbecher?",
                                          "loesung": "Das "
                                          "Volumen"}},
                    "fehlertypen": [
                        {
                            "key": "volumen_ist_masse",
                            "label": "Volumen wird zu Masse",
                            "beschreibung": "Wer mehr Platz "
                            "einnimmt, soll auch mehr "
                            "wiegen — die zwei Messungen "
                            "fließen zusammen.",
                            "antworten": ["die kugel",
                                          "das schwere",
                                          "schwerer"],
                            "erklaerung": {
                                "haken": "Der Schaumstoff "
                                        "füllt den Arm, "
                                        "die Kugel "
                                        "drückt die Hand "
                                        "— welches hat "
                                        "mehr Volumen?",
                                "erkenntnis": "Volumen ist "
                                "der Platz, den etwas "
                                "einnimmt — Masse ist "
                                "der Stoff darin. Der "
                                "Schaumstoff nimmt mehr "
                                "Platz ein, die Kugel "
                                "hat mehr Stoff.",
                                "regel": "Volumen = Platz, "
                                "gemessen in ml, l, cm³. "
                                "Masse = Stoffmenge, "
                                "gemessen in g, kg. "
                                "Zwei verschiedene "
                                "Größen.",
                                "bild": {"zeigt": "zwei "
                                         "Regale: eines "
                                         "misst Platz, "
                                         "eines Stoff",
                                         "bewegt": "die "
                                         "Dinge wandern "
                                         "auf beide "
                                         "Regale",
                                         "bleibt_gleich":
                                         "die Dinge "
                                         "bleiben "
                                         "dieselben"},
                                "aufgabe": {"frage": "Was "
                                            "hat mehr "
                                            "Volumen: ein "
                                            "Ballon oder "
                                            "eine "
                                            "Murmel?",
                                            "loesung":
                                            "Der Ballon"}},
                            "visualisierung": _NETZ(
                                ["Körper", "Volumen",
                                 "Masse"],
                                ["Körper → Volumen: "
                                 "Platz",
                                 "Körper → Masse: "
                                 "Stoffmenge"]),
                            "visualisierung_alternativ":
                            _TABELLE(
                                ["Größe", "misst",
                                 "Einheit"],
                                ["Volumen | Platz | "
                                 "ml, l, cm³",
                                 "Masse | Stoff | g, kg"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Was hat mehr "
                                    "Volumen: ein "
                                    "Schaumstoffblock "
                                    "oder eine "
                                    "Bleikugel?",
                                    "Der Schaumstoff",
                                    ["Die Bleikugel",
                                     "Gleich"],
                                    "Volumen ist Platz — "
                                    "das Schwere ist "
                                    "eine andere "
                                    "Messung."),
                                "beispiel": aufgabe(
                                    "Der Stein drückt "
                                    "das Wasser hoch: "
                                    "er nimmt dessen "
                                    "Platz ein. Das "
                                    "ist sein Volumen.",
                                    "Der verdrängte "
                                    "Platz."),
                                "gefuehrt": aufgabe(
                                    "Was misst man in "
                                    "Litern: Masse oder "
                                    "Volumen?",
                                    "Volumen",
                                    fehler="masse",
                                    art="begriffe",
                                    rubrik=begriffe("volumen"),
                                    tipps=["Was füllt "
                                           "eine "
                                           "Flasche?"]),
                                "selbststaendig": aufgabe(
                                    "Wie viel Milliliter "
                                    "sind 3 Liter?",
                                    "3000",
                                    fehler="300",
                                    art="zahl",
                                    tipps=["Pro Liter "
                                           "1000 ml."]),
                                "transfer": auswahl(
                                    "Warum zeigt die "
                                    "Waage das Volumen "
                                    "nicht an?",
                                    "Sie misst Stoff — "
                                    "Platz ist eine "
                                    "andere Größe",
                                    ["Sie ist zu "
                                     "ungenau",
                                     "Volumen ist "
                                     "unsichtbar"],
                                    "Jedes Gerät misst "
                                    "seine Größe — "
                                    "Waage: Masse, "
                                    "Messbecher: "
                                    "Volumen.")}},
                        {
                            "key": "form_taeuscht",
                            "label": "Form täuscht über "
                                     "Volumen",
                            "beschreibung": "Ausgerollter "
                            "Ton sieht größer aus — die "
                            "Menge bleibt dieselbe, das "
                            "Auge glaubt es nicht.",
                            "antworten": ["wird größer",
                                          "mehr volumen",
                                          "größer"],
                            "erklaerung": {
                                "haken": "Der Ton wird "
                                        "flach gedrückt "
                                        "und sieht "
                                        "riesig aus — "
                                        "ist er jetzt "
                                        "mehr?",
                                "erkenntnis": "Kein "
                                "Bisschen Ton wurde "
                                "dazugetan oder "
                                "weggenommen — nur "
                                "die Form änderte "
                                "sich. Der Platz "
                                "bleibt derselbe.",
                                "regel": "Umformen ändert "
                                "die Form, nicht das "
                                "Volumen. Die "
                                "Wasserverdrängung "
                                "beweist es.",
                                "bild": {"zeigt": "derselbe "
                                         "Ton als Kugel "
                                         "und als "
                                         "Fladen im "
                                         "Wasser",
                                         "bewegt": "das "
                                         "Wasser steigt "
                                         "beide Male "
                                         "gleich hoch",
                                         "bleibt_gleich":
                                         "die Tonmenge "
                                         "bleibt "
                                         "gleich"},
                                "aufgabe": {"frage": "Ein "
                                            "Würfel Ton "
                                            "wird zur "
                                            "Kugel — "
                                            "sein "
                                            "Volumen?",
                                            "loesung":
                                            "Bleibt "
                                            "gleich"}},
                            "visualisierung": _FLUSS(
                                ["Ton als Kugel: "
                                 "verdrängt 20 ml",
                                 "Ton als Fladen: "
                                 "verdrängt 20 ml",
                                 "gleiches Volumen"]),
                            "visualisierung_alternativ":
                            _TABELLE(
                                ["Form", "verdrängtes "
                                 "Wasser"],
                                ["Kugel | 20 ml",
                                 "Fladen | 20 ml",
                                 "Würfel | 20 ml"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Ein Tonklumpen wird "
                                    "flach gedrückt — "
                                    "sein Volumen?",
                                    "Bleibt gleich",
                                    ["Wird größer",
                                     "Wird kleiner"],
                                    "Kein Ton kam dazu "
                                    "— nur die Form "
                                    "änderte sich."),
                                "beispiel": aufgabe(
                                    "Kugel und Fladen "
                                    "verdrängen "
                                    "dasselbe Wasser — "
                                    "gleicher Platz.",
                                    "Das Volumen "
                                    "bleibt."),
                                "gefuehrt": aufgabe(
                                    "Ein Apfel wird "
                                    "zerschnitten — "
                                    "sein Gesamtvolumen?",
                                    "Bleibt gleich",
                                    fehler="wird größer",
                                    art="begriffe",
                                    rubrik=begriffe("gleich"),
                                    tipps=["Kam Apfel "
                                           "dazu oder "
                                           "weg?"]),
                                "selbststaendig": aufgabe(
                                    "Ein Schwamm wird "
                                    "zusammengedrückt — "
                                    "sein Volumen?",
                                    "Wird kleiner",
                                    fehler="bleibt gleich",
                                    art="begriffe",
                                    rubrik=begriffe("kleiner"),
                                    tipps=["Beim "
                                           "Schwamm "
                                           "entweicht "
                                           "Luft — das "
                                           "ist kein "
                                           "reines "
                                           "Umformen."]),
                                "transfer": auswahl(
                                    "Warum ist der "
                                    "Schwamm eine "
                                    "Ausnahme der "
                                    "Umform-Regel?",
                                    "Er enthält Luft — "
                                    "beim Drücken "
                                    "geht Stoff "
                                    "(Luft) verloren",
                                    ["Er ist zu "
                                     "weich",
                                     "Er hat keine "
                                     "Form"],
                                    "Die Regel gilt "
                                    "nur, wenn keine "
                                    "Menge weggeht.")}},
                    ],
                    "hilfe": _hilfe({
                        "HOOK": "Platz und Stoff sind "
                                "zwei verschiedene "
                                "Messungen.",
                        "RULE": "Volumen = Platz (ml, l, "
                                "cm³). Masse = Stoff (g, "
                                "kg). Umformen ändert "
                                "nur die Form.",
                        "WORKED_EXAMPLE": "Das verdrängte "
                                "Wasser zeigt den wahren "
                                "Platz.",
                        "GUIDED_TASK": "Frag: wurde Stoff "
                                "dazugetan oder weg-"
                                "genommen?",
                        "INDEPENDENT_TASK": "Liter und "
                                "Kubik messen Platz — "
                                "Gramm misst Stoff.",
                        "ADAPTATION": "Die Tabelle "
                                "vergleicht die zwei "
                                "Größen."}),
                    "faq": [
                        {"frage": "Ist ein Liter dasselbe "
                                  "wie ein Kilogramm?",
                         "antwort": "Nein — ein Liter "
                                    "ist Platz, ein "
                                    "Kilogramm ist "
                                    "Stoff. Nur bei "
                                    "Wasser stimmen "
                                    "sie zufällig "
                                    "überein."},
                        {"frage": "Wie misst man das "
                                  "Volumen eines "
                                  "Steins?",
                         "antwort": "Mit Wasser: der "
                                    "Stein verdrängt "
                                    "genau sein "
                                    "Volumen — 50 ml "
                                    "mehr heißt 50 "
                                    "cm³."}],
                }},
            # --------------------------------------- pro-Denken
            {
                "id": "PH.RECHNEN.PRO",
                "title": "„Pro“ — pro Einheit vergleichen",
                "description": "Kilogramm pro Liter, Euro "
                               "pro Stück — die Division "
                               "als Vergleichsmaß.",
                "first_contact_grade": 5, "target_grade": 6,
                "prerequisites": ["PH.MATERIAL.VOLUMEN"],
                "levels": {
                    "below": "K4–5: Volumen und Masse "
                             "messen",
                    "target": "K6: „pro“ als Verteilung auf "
                              "eine Einheit lesen und "
                              "rechnen",
                    "above": "K7: Dichte als Masse pro "
                             "Volumen"},
                "can_do": {
                    "below": ["Volumen und Masse "
                              "getrennt messen"],
                    "target": ["„pro“-Angaben lesen und "
                               "mit Division berechnen"],
                    "above": ["„pro“-Werte zum Vergleich "
                              "nutzen (Dichte)"]},
                "difficulty_parameters": {
                    "beispiele": "Euro pro Stück, Liter "
                                 "pro Stunde, kg pro "
                                 "Liter",
                    "rechenart": "Division"},
                "anchor_items": [
                    item("6 Äpfel kosten 3 € — wie viel "
                         "pro Stück?", "0,50 €",
                         level="target", grade=6,
                         answer=text("0,50", "0,5", "50 "
                                     "cent", "0.50")),
                    item("10 Liter Wasser wiegen 10 kg — "
                         "wie viel pro Liter?", "1 kg",
                         level="target", grade=6,
                         answer=text("1 kg", "1",
                                     "ein kilogramm"))],
                "boundary_items": {
                    "below": [item("Wie viel ml ist ein "
                                   "Liter?", "1000",
                                   level="below", grade=5,
                                   answer=number("1000"))],
                    "within": [item("8 Bonbons kosten "
                                    "4 € — pro Stück?",
                                    "0,50 €", level="target",
                                    grade=6,
                                    answer=text("0,50",
                                                "0,5",
                                                "50 cent"))],
                    "above": [item("Welcher Stoff ist "
                                   "dichter: 3 kg pro "
                                   "Liter oder 1 kg pro "
                                   "Liter?", "3 kg pro "
                                   "Liter", level="above",
                                   grade=7,
                                   answer=text("3 kg pro "
                                               "liter",
                                               "3 kg"))]},
                "diagnostics": {
                    "misconceptions": [
                        {"key": "F1", "description": "Bei "
                         "„pro“ wird falsch herum "
                         "dividiert — Stück durch Euro "
                         "statt Euro durch Stück.",
                         "remediation_hint": "Das Wort "
                         "nach „pro“ ist der Teiler: "
                         "Euro PRO Stück heißt Euro "
                         "geteilt durch Stückzahl.",
                         "diagnostic_item": item(
                             "4 kg Zucker kosten 8 € — "
                             "wie viel pro kg?",
                             "2 €", level="target",
                             grade=6,
                             answer=choice("2 €",
                                           ["0,50 €",
                                            "32 €"],
                                           ["F1", "F1"]),
                             distractors=[])},
                        {"key": "F2", "description": "„Pro“ "
                         "wird als Multiplikation gelesen "
                         "— die Gesamtmenge soll größer "
                         "werden statt verteilt.",
                         "remediation_hint": "„Pro“ "
                         "verteilt — das Ergebnis ist "
                         "kleiner als die Gesamtmenge "
                         "(bei mehr als einer "
                         "Einheit).",
                         "diagnostic_item": item(
                             "6 kg in 3 Kisten — pro "
                             "Kiste?",
                             "2 kg", level="target",
                             grade=6,
                             answer=choice("2 kg",
                                           ["18 kg",
                                            "3 kg"],
                                           ["F2", "F2"]),
                             distractors=[])}],
                    "diagnostic_items": [
                        item("Ein Liter Wasser wiegt "
                             "etwas — wie viel Milliliter "
                             "ist er?", "1000",
                             level="below", grade=5,
                             answer=number("1000")),
                        item("12 € für 4 Stück — pro "
                             "Stück?", "3 €",
                             level="target", grade=6,
                             answer=text("3", "3 €",
                                         "3 euro"))],
                    "exit_items": [
                        item("5 Liter Öl wiegen 4,5 kg — "
                             "pro Liter?", "0,9 kg",
                             level="target", grade=6,
                             answer=text("0,9", "0,9 kg",
                                         "900 g")),
                        item("60 km in 2 Stunden — "
                             "pro Stunde?", "30 km",
                             level="target", grade=6,
                             answer=text("30", "30 km"))]},
                "lektion": {
                    "konzept": {
                        "konzept_key": "pro",
                        "thema_key": "rechnen",
                        "label": "„Pro“ — pro Einheit "
                                 "vergleichen",
                        "klasse_von": 5, "klasse_bis": 7,
                        "stichworte": ["pro", "pro einheit",
                                       "euro pro stück",
                                       "kg pro liter",
                                       "verhältnis"]},
                    "erstkontakt": {
                        "anker": "Zwei Saftpackungen: 1 "
                                 "Liter für 2 €, 2 Liter "
                                 "für 3 € — welche ist "
                                 "günstiger?",
                        "benennung": "Pro-Rechnen",
                        "erste_aufgabe": {"frage": "6 "
                                          "Äpfel für "
                                          "3 € — pro "
                                          "Stück?",
                                          "loesung":
                                          "0,50 €"}},
                    "fehlertypen": [
                        {
                            "key": "falsch_herum_geteilt",
                            "label": "Falsch herum "
                                     "dividiert",
                            "beschreibung": "Stück durch "
                            "Euro statt Euro durch "
                            "Stück — das „pro“-Wort "
                            "bestimmt den Teiler.",
                            "antworten": ["0,5", "0.5",
                                          "halb"],
                            "erklaerung": {
                                "haken": "„2 € pro Liter“ "
                                        "— was wird "
                                        "durch was "
                                        "geteilt? Das "
                                        "Wort nach „pro“ "
                                        "verrät es.",
                                "erkenntnis": "„Euro pro "
                                "Liter“ heißt: Euro "
                                "geteilt durch Liter. "
                                "„Kilogramm pro Kiste“ "
                                "heißt: kg geteilt "
                                "durch Kisten. Das Wort "
                                "nach „pro“ ist der "
                                "Teiler.",
                                "regel": "A pro B = "
                                "A geteilt durch B. "
                                "„Pro“ liest die "
                                "Frage: wie viel A "
                                "auf EIN B?",
                                "bild": {"zeigt": "die "
                                         "Gesamtmenge "
                                         "oben, die "
                                         "Einheiten "
                                         "unten als "
                                         "Teiler",
                                         "bewegt": "die "
                                         "Menge verteilt "
                                         "sich auf die "
                                         "Einheiten",
                                         "bleibt_gleich":
                                         "das „pro“ "
                                         "bleibt das "
                                         "Verteilen"},
                                "aufgabe": {"frage": "10 "
                                            "€ für 5 "
                                            "Stück — "
                                            "pro "
                                            "Stück?",
                                            "loesung":
                                            "2 €"}},
                            "visualisierung": _FLUSS(
                                ["Lies: Euro PRO Stück",
                                 "Euro sind die Menge, "
                                 "Stück der Teiler",
                                 "Euro ÷ Stück = Preis "
                                 "pro Stück"]),
                            "visualisierung_alternativ":
                            _TABELLE(
                                ["Aufgabe", "geteilt",
                                 "durch", "= pro"],
                                ["8 € / 4 kg | 8 € | "
                                 "4 kg | 2 € pro kg",
                                 "6 kg / 3 Kisten | "
                                 "6 kg | 3 Kisten | "
                                 "2 kg pro Kiste"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "4 kg Zucker für "
                                    "8 € — wie viel "
                                    "pro kg?",
                                    "2 €",
                                    ["0,50 €", "32 €"],
                                    "Euro pro kg = "
                                    "Euro geteilt "
                                    "durch kg."),
                                "beispiel": aufgabe(
                                    "„Euro pro Stück“ "
                                    "= Euro ÷ Stück. "
                                    "8 € ÷ 4 Stück = "
                                    "2 € pro Stück.",
                                    "2 € pro Stück"),
                                "gefuehrt": aufgabe(
                                    "10 Liter für "
                                    "20 kg — wie viel "
                                    "kg pro Liter?",
                                    "2",
                                    fehler="0,5",
                                    art="zahl",
                                    tipps=["Das Wort "
                                           "nach „pro“ "
                                           "ist der "
                                           "Teiler.",
                                           "kg ÷ "
                                           "Liter."]),
                                "selbststaendig": aufgabe(
                                    "15 € für 5 m "
                                    "Stoff — pro "
                                    "Meter?",
                                    "3",
                                    fehler="0,33",
                                    art="zahl",
                                    tipps=["€ ÷ m."]),
                                "transfer": auswahl(
                                    "Warum kann man "
                                    "„2 € pro Liter“ "
                                    "nicht umdrehen "
                                    "zu „2 Liter pro "
                                    "€“?",
                                    "Das wäre die "
                                    "Antwort auf "
                                    "eine andere "
                                    "Frage — Menge "
                                    "für Geld statt "
                                    "Preis für Menge",
                                    ["Es klingt "
                                     "falsch",
                                     "Liter sind "
                                     "zu groß"],
                                    "„Pro“ hat eine "
                                    "Richtung — "
                                    "umdrehen "
                                    "wechselt die "
                                    "Frage.")}},
                        {
                            "key": "pro_ist_mal",
                            "label": "„Pro“ wird zu „mal“",
                            "beschreibung": "Die "
                            "Gesamtmenge wird ver-"
                            "vielfacht statt verteilt — "
                            "pro Stück wird größer als "
                            "das Ganze.",
                            "antworten": ["18", "32",
                                          "mal"],
                            "erklaerung": {
                                "haken": "6 kg in 3 "
                                        "Kisten — "
                                        "kann eine "
                                        "Kiste 18 kg "
                                        "haben? Dann "
                                        "wären es ja "
                                        "54 kg.",
                                "erkenntnis": "„Pro“ "
                                "verteilt: die "
                                "Gesamtmenge wird "
                                "auf die Einheiten "
                                "aufgeteilt. Das "
                                "Ergebnis muss "
                                "kleiner sein — "
                                "außer es gibt nur "
                                "eine Einheit.",
                                "regel": "„Pro“ = "
                                "Teilen, nicht "
                                "Malnehmen. "
                                "Kontrolle: das "
                                "Ergebnis mal "
                                "Einheiten muss "
                                "wieder das Ganze "
                                "geben.",
                                "bild": {"zeigt": "6 kg "
                                         "wandern in "
                                         "3 gleiche "
                                         "Kisten",
                                         "bewegt": "die "
                                         "Kilos "
                                         "verteilen "
                                         "sich",
                                         "bleibt_gleich":
                                         "die "
                                         "Gesamtmenge "
                                         "bleibt 6 kg"},
                                "aufgabe": {"frage":
                                            "9 Liter "
                                            "in 3 "
                                            "Flaschen "
                                            "— pro "
                                            "Flasche?",
                                            "loesung":
                                            "3 Liter"}},
                            "visualisierung": _FLUSS(
                                ["Gesamtmenge: 6 kg",
                                 "verteile auf 3 "
                                 "Kisten",
                                 "6 ÷ 3 = 2 kg pro "
                                 "Kiste",
                                 "Kontrolle: 3 · 2 = "
                                 "6"]),
                            "visualisierung_alternativ":
                            _NETZ(
                                ["pro", "teilen",
                                 "Kontrolle"],
                                ["pro → teilen",
                                 "Ergebnis mal "
                                 "Einheiten = "
                                 "Gesamtmenge"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "6 kg in 3 Kisten "
                                    "— pro Kiste?",
                                    "2 kg",
                                    ["18 kg", "3 kg"],
                                    "„Pro“ verteilt — "
                                    "das Ergebnis "
                                    "muss kleiner "
                                    "werden."),
                                "beispiel": aufgabe(
                                    "10 Bonbons auf "
                                    "5 Kinder = 2 "
                                    "pro Kind. "
                                    "Kontrolle: "
                                    "5 · 2 = 10.",
                                    "2 Bonbons"),
                                "gefuehrt": aufgabe(
                                    "8 Liter in 4 "
                                    "Gläser — pro "
                                    "Glas?",
                                    "2",
                                    fehler="32",
                                    art="zahl",
                                    tipps=["Pro ist "
                                           "teilen.",
                                           "Kontrolle: "
                                           "4 mal "
                                           "Ergebnis "
                                           "= 8?"]),
                                "selbststaendig": aufgabe(
                                    "12 € für 3 "
                                    "Stunden — pro "
                                    "Stunde?",
                                    "4",
                                    fehler="36",
                                    art="zahl",
                                    tipps=["Teile "
                                           "die 12 "
                                           "auf 3."]),
                                "transfer": auswahl(
                                    "Woran erkennt "
                                    "man, dass 18 "
                                    "kg pro Kiste "
                                    "unmöglich ist?",
                                    "3 Kisten à 18 "
                                    "kg wären 54 kg "
                                    "— mehr als die "
                                    "6 kg, die es "
                                    "gab",
                                    ["18 ist zu "
                                     "gerade",
                                     "Kisten sind "
                                     "zu klein"],
                                    "Die Rückrechnung "
                                    "verrät jeden "
                                    "Rechenfehler.")}},
                    ],
                    "hilfe": _hilfe({
                        "HOOK": "„Pro“ verteilt — wie "
                                "viel auf EINE Einheit "
                                "kommt.",
                        "RULE": "A pro B = A ÷ B. Das "
                                "Wort nach „pro“ ist "
                                "der Teiler. Kontrolle: "
                                "Ergebnis mal B = A.",
                        "WORKED_EXAMPLE": "Lies laut: "
                                "Euro pro Stück = Euro "
                                "geteilt durch Stück.",
                        "GUIDED_TASK": "Was soll verteilt "
                                "werden — und auf "
                                "wieviele Einheiten?",
                        "INDEPENDENT_TASK": "Pro ist "
                                "teilen, nicht mal — "
                                "die Rückrechnung "
                                "prüft es.",
                        "ADAPTATION": "Die Tabelle "
                                "zeigt jede Aufgabe "
                                "mit ihrem Teiler."}),
                    "faq": [
                        {"frage": "Was heißt „pro“?",
                         "antwort": "„Auf eine Einheit "
                                    "verteilt“ — Euro "
                                    "pro Stück heißt: "
                                    "wieviel Euro auf "
                                    "EIN Stück kommt."},
                        {"frage": "Wie rechne ich „pro“ "
                                  "aus?",
                         "antwort": "Teilen: A pro B = "
                                    "A geteilt durch "
                                    "B. Die Rück-"
                                    "rechnung prüft "
                                    "es."}],
                }},
            # ------------------------------------------- Dichte
            {
                "id": "PH.GROESSEN.DICHTE",
                "title": "Dichte — Masse pro Volumen",
                "description": "Warum Eisen sinkt und Holz "
                               "schwimmt: die Dichte als "
                               "„Masse pro Platz“.",
                "first_contact_grade": 6, "target_grade": 7,
                "prerequisites": ["PH.MATERIAL.MASSE",
                                  "PH.MATERIAL.VOLUMEN",
                                  "PH.RECHNEN.PRO"],
                "levels": {
                    "below": "K5–6: Masse, Volumen und "
                             "„pro“-Denken",
                    "target": "K7: Dichte als Masse pro "
                              "Volumen berechnen und "
                              "Schwimmen/Sinken deuten",
                    "above": "K8: Dichte von "
                             "Flüssigkeiten, Archimedes"},
                "can_do": {
                    "below": ["Masse messen, Volumen "
                              "messen, „pro“ rechnen"],
                    "target": ["Dichte = Masse ÷ Volumen "
                               "rechnen und vorhersagen, "
                               "was schwimmt"],
                    "above": ["die Dichte von Wasser "
                              "nutzen, um Verhalten zu "
                              "erklären"]},
                "difficulty_parameters": {
                    "formel": "Dichte = Masse ÷ Volumen",
                    "einheit": "g/cm³, kg/l",
                    "anker": "Wasser = 1 g/cm³"},
                "anchor_items": [
                    item("Ein Körper hat 20 g Masse und "
                         "10 cm³ Volumen — seine "
                         "Dichte?", "2 g/cm³",
                         level="target", grade=7,
                         answer=text("2 g/cm3", "2",
                                     "2 g/cm³")),
                    item("Schwimmt ein Körper mit "
                         "Dichte 0,8 g/cm³ in Wasser?",
                         "Ja", level="target", grade=7,
                         answer=text("ja", "ja, er "
                                     "schwimmt"))],
                "boundary_items": {
                    "below": [item("Was misst die Waage?",
                                   "Die Masse",
                                   level="below", grade=3,
                                   answer=text("masse")),
                              item("8 € für 4 Stück — "
                                   "pro Stück?", "2 €",
                                   level="below", grade=6,
                                   answer=text("2", "2 €"))],
                    "within": [item("Dichte von 30 g auf "
                                    "10 cm³?", "3 g/cm³",
                                    level="target",
                                    grade=7,
                                    answer=text("3",
                                                "3 g/cm3",
                                                "3 g/cm³"))],
                    "above": [item("Warum schwimmt Öl "
                                   "auf Wasser?",
                                   "Es ist leichter pro "
                                   "Volumen",
                                   level="above", grade=8,
                                   answer=text("es ist "
                                               "leichter",
                                               "geringere "
                                               "dichte",
                                               "leichter "
                                               "pro "
                                               "volumen"))]},
                "diagnostics": {
                    "misconceptions": [
                        {"key": "F1", "description": "Schwer "
                         "sinkt, leicht schwimmt — das "
                         "absolute Gewicht statt der "
                         "Dichte entscheidet.",
                         "remediation_hint": "Ein "
                         "riesiger Eisberg schwimmt, "
                         "eine winzige Nadel sinkt — "
                         "es zählt Masse pro Volumen.",
                         "diagnostic_item": item(
                             "Was schwimmt: ein "
                             "riesiger Eisberg oder "
                             "eine Nähnadel?",
                             "Der Eisberg",
                             level="target", grade=7,
                             answer=choice("Der Eisberg",
                                           ["Die Nadel",
                                            "Beide"],
                                           ["F1", "F1"]),
                             distractors=[])},
                        {"key": "F2", "description": "Die "
                         "Formel wird als Magie "
                         "auswendig gelernt — Masse "
                         "geteilt durch Volumen ohne "
                         "Bedeutung.",
                         "remediation_hint": "Dichte = "
                         "„wie schwer ein cm³ davon "
                         "ist“ — eine Pro-Rechnung.",
                         "diagnostic_item": item(
                             "Was bedeutet „Dichte 3 "
                             "g/cm³“?",
                             "Jeder cm³ wiegt 3 g",
                             level="target", grade=7,
                             answer=choice("Jeder cm³ "
                                           "wiegt 3 g",
                                           ["Der Körper "
                                            "wiegt 3 g",
                                            "3 cm³ "
                                            "wiegen 1 g"],
                                           ["F2", "F2"]),
                             distractors=[])},
                        {"key": "F3", "description": "Holz "
                         "schwimmt „weil es Holz ist“ "
                         "— das Material, nicht das "
                         "Verhältnis, trägt die "
                         "Erklärung.",
                         "remediation_hint": "Gleiches "
                         "Holz kann sinken (nass, "
                         "hart) — der Vergleich mit "
                         "Wasser entscheidet.",
                         "diagnostic_item": item(
                             "Warum schwimmt ein "
                             "Holzstück?",
                             "Weil es pro cm³ weniger "
                             "wiegt als Wasser",
                             level="target", grade=7,
                             answer=choice(
                                 "Weil es pro cm³ "
                                 "weniger wiegt als "
                                 "Wasser",
                                 ["Weil es Holz ist",
                                  "Weil es leicht "
                                  "ist"],
                                 ["F3", "F1"]),
                             distractors=[])}],
                    "diagnostic_items": [
                        item("10 € für 5 Stück — pro "
                             "Stück?", "2 €",
                             level="below", grade=6,
                             answer=text("2", "2 €")),
                        item("Dichte von 40 g auf "
                             "20 cm³?", "2 g/cm³",
                             level="target", grade=7,
                             answer=text("2", "2 g/cm3",
                                         "2 g/cm³"))],
                    "exit_items": [
                        item("Ein Stein hat 50 g und "
                             "20 cm³ — Dichte und "
                             "schwimmt er?",
                             "2,5 g/cm³, er sinkt",
                             level="target", grade=7,
                             answer=text("2,5 sinkt",
                                         "2,5 g/cm3 "
                                         "sinkt",
                                         "2.5 sinkt")),
                        item("Holz mit Dichte 0,6 g/cm³ "
                             "auf Wasser — was "
                             "passiert?",
                             "Es schwimmt",
                             level="target", grade=7,
                             answer=text("es schwimmt",
                                         "schwimmt",
                                         "es schwimmt "
                                         "oben"))]},
                "lektion": {
                    "konzept": {
                        "konzept_key": "dichte",
                        "thema_key": "groessen",
                        "label": "Dichte — Masse pro "
                                 "Volumen",
                        "klasse_von": 6, "klasse_bis": 8,
                        "stichworte": ["dichte",
                                       "masse pro volumen",
                                       "schwimmen sinken",
                                       "g pro cm3",
                                       "spezifisches "
                                       "gewicht"]},
                    "erstkontakt": {
                        "anker": "Ein riesiger Eisberg "
                                 "schwimmt — eine winzige "
                                 "Nähnadel sinkt. Warum "
                                 "umgekehrt als das "
                                 "Gewicht vermutet?",
                        "benennung": "Dichte",
                        "erste_aufgabe": {"frage": "Ein "
                                          "Körper hat "
                                          "20 g und "
                                          "10 cm³ — "
                                          "seine "
                                          "Dichte?",
                                          "loesung":
                                          "2 g/cm³"}},
                    "fehlertypen": [
                        {
                            "key": "schwer_sinkt",
                            "label": "Absolutes Gewicht "
                                     "entscheidet",
                            "beschreibung": "Was schwer "
                            "ist, soll sinken — der "
                            "Eisberg muss untergehen, "
                            "die Nadel schwimmen.",
                            "antworten": ["die nadel "
                                          "schwimmt",
                                          "der eisberg "
                                          "sinkt",
                                          "schwere sinken"],
                            "erklaerung": {
                                "haken": "Der Eisberg "
                                        "wiegt "
                                        "Millionen "
                                        "Kilo und "
                                        "schwimmt — "
                                        "die Nadel "
                                        "wiegt ein "
                                        "Gramm und "
                                        "sinkt. Was "
                                        "zählt "
                                        "wirklich?",
                                "erkenntnis": "Es zählt "
                                "nicht das ganze "
                                "Gewicht, sondern "
                                "das Gewicht pro "
                                "Platz: die Dichte. "
                                "Eis ist pro cm³ "
                                "leichter als "
                                "Wasser — die Nadel "
                                "pro cm³ schwerer.",
                                "regel": "Schwimmen oder "
                                "Sinken entscheidet "
                                "der Vergleich der "
                                "Dichten: leichter "
                                "pro Volumen als "
                                "Wasser → schwimmt, "
                                "schwerer → sinkt.",
                                "bild": {"zeigt": "ein "
                                         "cm³ Eis, ein "
                                         "cm³ Wasser, "
                                         "ein cm³ "
                                         "Stahl auf "
                                         "einer "
                                         "Skala",
                                         "bewegt": "die "
                                         "Würfelchen "
                                         "steigen ins "
                                         "Wasser — "
                                         "der leichte "
                                         "oben, der "
                                         "schwere "
                                         "unten",
                                         "bleibt_gleich":
                                         "die "
                                         "Gesamtgroessen "
                                         "bleiben "
                                         "egal"},
                                "aufgabe": {"frage":
                                            "Schwimmt "
                                            "ein Körper "
                                            "mit "
                                            "Dichte "
                                            "0,5 g/cm³?",
                                            "loesung":
                                            "Ja"}},
                            "visualisierung": _NETZ(
                                ["Körper", "Dichte",
                                 "Wasser 1 g/cm³",
                                 "schwimmt/sinkt"],
                                ["Körper → Dichte",
                                 "Dichte < Wasser → "
                                 "schwimmt",
                                 "Dichte > Wasser → "
                                 "sinkt"]),
                            "visualisierung_alternativ":
                            _TABELLE(
                                ["Stoff", "Dichte",
                                 "in Wasser"],
                                ["Holz | 0,6 | "
                                 "schwimmt",
                                 "Wasser | 1,0 | "
                                 "schwebt",
                                 "Eisen | 7,9 | "
                                 "sinkt"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Was schwimmt: "
                                    "ein riesiger "
                                    "Eisberg oder "
                                    "eine Nähnadel?",
                                    "Der Eisberg",
                                    ["Die Nadel",
                                     "Beide"],
                                    "Nicht das "
                                    "Gesamtgewicht "
                                    "zählt — die "
                                    "Dichte."),
                                "beispiel": aufgabe(
                                    "Eis: 0,9 g pro "
                                    "cm³. Wasser: "
                                    "1 g pro cm³. "
                                    "Der Eisberg ist "
                                    "leichter pro "
                                    "Platz — er "
                                    "schwimmt.",
                                    "Eis schwimmt, "
                                    "weil seine "
                                    "Dichte kleiner "
                                    "ist."),
                                "gefuehrt": aufgabe(
                                    "Ein Körper hat "
                                    "Dichte 1,5 "
                                    "g/cm³ — schwimmt "
                                    "oder sinkt er "
                                    "in Wasser?",
                                    "Er sinkt",
                                    fehler="er schwimmt",
                                    art="begriffe",
                                    rubrik=begriffe("sinkt"),
                                    tipps=["Wasser "
                                           "hat 1 "
                                           "g/cm³ — "
                                           "was ist "
                                           "mit "
                                           "mehr?"]),
                                "selbststaendig": aufgabe(
                                    "Öl mit 0,8 g/cm³ "
                                    "auf Wasser — "
                                    "was passiert?",
                                    "Es schwimmt oben",
                                    fehler="es sinkt",
                                    art="begriffe",
                                    rubrik=begriffe("schwimmt"),
                                    tipps=["Weniger "
                                           "als 1 "
                                           "g/cm³ "
                                           "schwimmt."]),
                                "transfer": auswahl(
                                    "Warum schwimmt "
                                    "ein riesiges "
                                    "Frachtschiff aus "
                                    "Stahl?",
                                    "Mit Luft im "
                                    "Rumpf ist seine "
                                    "Gesamtdichte "
                                    "unter der des "
                                    "Wassers",
                                    ["Stahl schwimmt "
                                     "sowieso",
                                     "Es ist zu groß "
                                     "zum Sinken"],
                                    "Durchschnitts-"
                                    "dichte zählt — "
                                    "Stahl + Luft "
                                    "zusammen sind "
                                    "leicht genug.")}},
                        {
                            "key": "formel_ohne_sinn",
                            "label": "Die Formel bleibt "
                                     "Magie",
                            "beschreibung": "m/V wird "
                            "gerechnet ohne zu "
                            "wissen, was herauskommt — "
                            "die Zahl hat keinen "
                            "Namen.",
                            "antworten": ["keine ahnung",
                                          "irgendwas",
                                          "eine zahl"],
                            "erklaerung": {
                                "haken": "20 g ÷ 10 "
                                        "cm³ = 2. "
                                        "Wovon 2? "
                                        "Die Zahl "
                                        "braucht "
                                        "ihren "
                                        "Namen.",
                                "erkenntnis": "20 g "
                                "verteilt auf 10 "
                                "Würfelchen: jedes "
                                "trägt 2 g. Die "
                                "Dichte sagt: "
                                "„so schwer ist "
                                "EIN cm³ davon“ — "
                                "2 g/cm³.",
                                "regel": "Dichte = "
                                "Masse ÷ Volumen = "
                                "Masse pro cm³. Es "
                                "ist eine Pro-"
                                "Rechnung, keine "
                                "Magie.",
                                "bild": {"zeigt": "20 g "
                                         "verteilen "
                                         "sich auf "
                                         "10 "
                                         "Würfelchen",
                                         "bewegt": "die "
                                         "Gramm "
                                         "wandern in "
                                         "die "
                                         "Würfel",
                                         "bleibt_gleich":
                                         "die "
                                         "Gesamtmasse "
                                         "bleibt 20 g"},
                                "aufgabe": {"frage":
                                            "Was "
                                            "bedeutet "
                                            "5 g/cm³?",
                                            "loesung":
                                            "Jeder "
                                            "cm³ "
                                            "wiegt "
                                            "5 g"}},
                            "visualisierung": _FLUSS(
                                ["Masse: 20 g",
                                 "Platz: 10 cm³",
                                 "20 ÷ 10 = 2",
                                 "jeder cm³ trägt "
                                 "2 g → 2 g/cm³"]),
                            "visualisierung_alternativ":
                            _TABELLE(
                                ["Masse", "Volumen",
                                 "Dichte"],
                                ["20 g | 10 cm³ | "
                                 "2 g/cm³",
                                 "30 g | 10 cm³ | "
                                 "3 g/cm³",
                                 "20 g | 5 cm³ | "
                                 "4 g/cm³"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Was bedeutet "
                                    "„Dichte 3 "
                                    "g/cm³“?",
                                    "Jeder cm³ "
                                    "wiegt 3 g",
                                    ["Der Körper "
                                     "wiegt 3 g",
                                     "3 cm³ wiegen "
                                     "1 g"],
                                    "Dichte ist "
                                    "eine Pro-"
                                    "Angabe: Masse "
                                    "pro Würfel-"
                                    "chen."),
                                "beispiel": aufgabe(
                                    "30 g auf 10 "
                                    "cm³ verteilt: "
                                    "jeder cm³ "
                                    "bekommt 3 g → "
                                    "3 g/cm³.",
                                    "3 g/cm³"),
                                "gefuehrt": aufgabe(
                                    "40 g auf 8 cm³ "
                                    "— die Dichte?",
                                    "5",
                                    fehler="32",
                                    art="zahl",
                                    tipps=["Masse ÷ "
                                           "Volumen.",
                                           "Pro-"
                                           "Rechnung: "
                                           "Gramm auf "
                                           "jeden "
                                           "cm³."]),
                                "selbststaendig": aufgabe(
                                    "100 g auf "
                                    "50 cm³ — die "
                                    "Dichte?",
                                    "2",
                                    fehler="5000",
                                    art="zahl",
                                    tipps=["Pro cm³ "
                                           "wie viel "
                                           "Gramm?"]),
                                "transfer": auswahl(
                                    "Zwei Körper "
                                    "gleicher Masse, "
                                    "einer ist "
                                    "kleiner — "
                                    "welcher ist "
                                    "dichter?",
                                    "Der kleinere — "
                                    "gleiche Masse "
                                    "auf weniger "
                                    "Platz",
                                    ["Der größere",
                                     "Gleich"],
                                    "Gleiche Masse, "
                                    "weniger Platz "
                                    "= mehr pro "
                                    "cm³.")}},
                    ],
                    "hilfe": _hilfe({
                        "HOOK": "Nicht wie schwer — "
                                "wie schwer pro Platz "
                                "entscheidet.",
                        "RULE": "Dichte = Masse ÷ "
                                "Volumen (g/cm³). "
                                "Unter 1 g/cm³ "
                                "schwimmt in "
                                "Wasser, darüber "
                                "sinkt.",
                        "WORKED_EXAMPLE": "Verteile die "
                                "Masse auf die "
                                "Würfelchen — das "
                                "ist die Dichte.",
                        "GUIDED_TASK": "Pro-Rechnung: "
                                "Masse auf jeden "
                                "cm³ verteilen.",
                        "INDEPENDENT_TASK": "Die "
                                "Nadel sinkt, der "
                                "Eisberg schwimmt "
                                "— Dichte schlägt "
                                "Größe.",
                        "ADAPTATION": "Die Tabelle "
                                "ordnet Stoff, "
                                "Dichte und "
                                "Verhalten."}),
                    "faq": [
                        {"frage": "Warum schwimmt "
                                  "Holz?",
                         "antwort": "Weil es pro cm³ "
                                    "weniger wiegt "
                                    "als Wasser — "
                                    "seine Dichte "
                                    "ist kleiner "
                                    "als 1 g/cm³."},
                        {"frage": "Was ist die Dichte "
                                  "von Wasser?",
                         "antwort": "1 g/cm³ — das "
                                    "ist der "
                                    "Vergleichspunkt: "
                                    "weniger "
                                    "schwimmt, mehr "
                                    "sinkt."}],
                }},
        ]}]}
