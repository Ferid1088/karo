"""Deutsch-Slice: vom Satz als Sinneinheit zu den Satzgliedern.

Level 0 heißt hier: das Kind erkennt einen Satz als abgeschlossene
Sinneinheit (Anfang, Punkt, sinnvolles Ganzes). Erst dann kann es Wortarten
und schließlich Satzglieder bestimmen.

    DE.SATZGLIEDER.BESTIMMEN       (Ziel, Kl. 4–5)
      └── DE.SATZGLIEDER.SUBJEKT_PRAEDIKAT  (Kl. 3–4)
            └── DE.WORTARTEN.GRUNDLAGEN     (Kl. 2–3)
                  └── DE.SATZ.SINNEINHEIT   (Kl. 1–2, Level 0)
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
    "fach": "deutsch",
    "code": "DE",
    "name": "Deutsch",
    "blocks": [{
        "id": "DE.SATZ",
        "title": "Satz und Satzglieder",
        "description": "Vom Satz als Sinneinheit zu Subjekt, Prädikat und "
                       "Objekten — die Grammatik des einfachen Satzes.",
        "grade_min": 1, "grade_max": 6, "typical_grade": 4,
        "concepts": [
            # --------------------------------------------------- Level 0
            {
                "id": "DE.SATZ.SINNEINHEIT",
                "title": "Der Satz als Sinneinheit",
                "description": "Was ein Satz ist und was ihn von einer "
                               "Wortreihe unterscheidet: Anfang, Ende, "
                               "vollständiger Gedanke.",
                "first_contact_grade": 1, "target_grade": 2,
                "prerequisites": [],
                "levels": {
                    "below": "K1: Wörter lesen und schreiben",
                    "target": "K2: Sätze als Sinneinheit erkennen und "
                              "selbst bilden",
                    "above": "K3: Wortarten und Satzglieder"},
                "can_do": {
                    "below": ["Wörter in einem Satz erkennen"],
                    "target": ["Einen Satz von einer Wortreihe "
                               "unterscheiden und Sätze vervollständigen"],
                    "above": ["Subjekt und Verb in einem Satz finden"]},
                "difficulty_parameters": {
                    "satzlaenge": "bis 8 Wörter",
                    "aufgabe": "erkennen, vervollständigen, bilden"},
                "anchor_items": [
                    item("Welche Zeile ist ein Satz?",
                         "Der Hund spielt im Garten.",
                         level="target", grade=2,
                         answer=choice("Der Hund spielt im Garten.",
                                       ["Hund Garten Ball",
                                        "spielt im Garten"], [None, None])),
                    item("Ergänze zum Satz: Die Katze ___",
                         "Die Katze schläft.",
                         level="target", grade=2,
                         answer=text("schläft", "schläft.", "miaut",
                                     "sitzt", "läuft"))],
                "boundary_items": {
                    "below": [item("Wie viele Wörter hat der Satz "
                                   "„Der Ball rollt“?", "3",
                                   level="below", grade=1,
                                   answer=text("3", "drei"))],
                    "within": [item("Welche Zeile ist ein Satz?",
                                    "Mia liest ein Buch.",
                                    level="target", grade=2,
                                    answer=choice("Mia liest ein Buch.",
                                                  ["liest ein Buch",
                                                   "Mia Buch lesen"],
                                                  [None, None]))],
                    "above": [item("Welches Wort beschreibt, was die Katze "
                                   "tut: „Die Katze schläft“?", "schläft",
                                   level="above", grade=3,
                                   answer=text("schläft"))]},
                "diagnostics": {
                    "misconceptions": [
                        {"key": "F1", "description": "Alles mit Punkt wird "
                         "zum Satz: auch Wortreihen ohne vollständigen "
                         "Gedanken werden als Satz gelesen.",
                         "remediation_hint": "Vorlesen und fragen: ergibt "
                         "das als Ganzes Sinn? Ein Satz erzählt etwas "
                         "Fertiges.",
                         "diagnostic_item": item(
                             "Welche Zeile ist ein Satz?",
                             "Der Vogel singt.", level="target", grade=2,
                             answer=choice("Der Vogel singt.",
                                           ["Vogel singt Baum.",
                                            "Der Vogel."], ["F1", "F1"]),
                             distractors=[])},
                        {"key": "F2", "description": "Ein Satz braucht nach "
                         "Meinung des Kindes viele Wörter — kurze Sätze wie "
                         "„Er schläft.“ werden nicht als Satz gezählt.",
                         "remediation_hint": "Ein Satz braucht einen "
                         "Gedanken, nicht eine Mindestlänge.",
                         "diagnostic_item": item(
                             "Welche Zeile ist ein Satz?",
                             "Es regnet.", level="target", grade=2,
                             answer=choice("Es regnet.",
                                           ["Regen", "es regnet heute nicht"],
                                           ["F2", None]),
                             distractors=[])}],
                    "diagnostic_items": [
                        item("Zähle die Wörter: „Der Fisch schwimmt.“",
                             "3", level="below", grade=1,
                             answer=text("3", "drei")),
                        item("Welche Zeile ist ein Satz?",
                             "Lena malt ein Bild.", level="target", grade=2,
                             answer=choice("Lena malt ein Bild.",
                                           ["Lena Bild",
                                            "malt ein Bild"], [None, None]))],
                    "exit_items": [
                        item("Bilde einen Satz aus: Hund, spielt, der, "
                             "Ball, mit, einem",
                             "Der Hund spielt mit einem Ball.",
                             level="target", grade=2,
                             answer=text("der hund spielt mit einem ball",
                                         "der hund spielt mit einem ball.")),
                        item("Welche Zeile ist ein Satz?",
                             "Die Sonne scheint.", level="target", grade=2,
                             answer=choice("Die Sonne scheint.",
                                           ["Sonne scheint hell",
                                            "Die scheint."], [None, "F1"]))]},
                "lektion": {
                    "konzept": {
                        "konzept_key": "sinneinheit", "thema_key": "satz",
                        "label": "Der Satz als Sinneinheit",
                        "klasse_von": 1, "klasse_bis": 3,
                        "stichworte": ["satz", "was ist ein satz",
                                       "sinneinheit", "satz bilden",
                                       "satzeinheit"]},
                    "erstkontakt": {
                        "anker": "„Hund Ball Garten“ — ist das schon ein "
                                 "Satz? Was fehlt, damit daraus eine "
                                 "Geschichte wird?",
                        "benennung": "Satz",
                        "erste_aufgabe": {"frage": "Welche Zeile ist ein "
                                          "Satz?", "loesung":
                                          "Der Hund spielt im Garten."}},
                    "fehlertypen": [
                        {
                            "key": "punkt_macht_satz",
                            "label": "Punkt allein macht den Satz",
                            "beschreibung": "Jede Wortreihe mit Punkt gilt "
                            "als Satz — der Gedanke wird nicht geprüft.",
                            "antworten": ["vogel singt baum", "der vogel"],
                            "erklaerung": {
                                "haken": "„Vogel singt Baum.“ hat einen "
                                        "Punkt und steht doch schief — "
                                        "warum klingt es komisch?",
                                "erkenntnis": "Ein Satz erzählt einen "
                                "fertigen Gedanken: wer tut was. „Vogel "
                                "singt Baum“ verbindet Wörter, die nicht "
                                "zusammengehören.",
                                "regel": "Ein Satz ist eine abgeschlossene "
                                "Sinneinheit: er beginnt groß, endet mit "
                                "Punkt — und ergibt als Ganzes Sinn.",
                                "bild": {"zeigt": "drei Zeilen: eine erzählt "
                                         "etwas Fertiges, zwei nicht",
                                         "bewegt": "die Wörter der "
                                         "unsinnigen Zeile fallen auseinander",
                                         "bleibt_gleich": "die echten "
                                         "Satzwörter bleiben verbunden"},
                                "aufgabe": {"frage": "Ist „Katze Maus "
                                            "schnell“ ein Satz?",
                                            "loesung": "Nein"}},
                            "visualisierung": _NETZ(
                                ["Satz", "großer Anfang", "Punkt",
                                 "fertiger Gedanke"],
                                ["Satz → großer Anfang",
                                 "Satz → Punkt",
                                 "Satz → fertiger Gedanke"]),
                            "visualisierung_alternativ": _FLUSS(
                                ["Zeile laut vorlesen",
                                 "Ergibt der Gedanke Sinn?",
                                 "Dann ist es ein Satz"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Welche Zeile ist ein Satz?",
                                    "Der Vogel singt.",
                                    ["Vogel singt Baum.", "Der Vogel."],
                                    "Nur eine Zeile erzählt etwas "
                                    "Fertiges — die anderen sind Wortreihen."),
                                "beispiel": aufgabe(
                                    "„Der Vogel singt.“ Wer tut was? Der "
                                    "Vogel — singt. Das ergibt einen "
                                    "fertigen Gedanken: ein Satz.",
                                    "Der Vogel singt.",
                                    schritte=["Wer? Der Vogel.",
                                              "Was tut er? singt.",
                                              "Gedanke fertig: ein Satz."]),
                                "gefuehrt": aufgabe(
                                    "Ist „Lisa Ball“ ein Satz? "
                                    "Antwort: ja oder nein",
                                    "nein",
                                    fehler="ja",
                                    art="text",
                                    tipps=["Lies die Zeile laut — ergibt "
                                           "sie einen fertigen Gedanken?",
                                           "Was tut Lisa mit dem Ball?"]),
                                "selbststaendig": aufgabe(
                                    "Ist „Der Zug fährt schnell.“ ein "
                                    "Satz? Antwort: ja oder nein",
                                    "ja",
                                    fehler="nein",
                                    art="text",
                                    tipps=["Wer fährt? Was tut er?"]),
                                "transfer": auswahl(
                                    "Warum ist „Tom rennt.“ ein Satz, "
                                    "obwohl er nur zwei Wörter hat?",
                                    "Er erzählt einen fertigen Gedanken: "
                                    "wer, was",
                                    ["Zwei Wörter sind das Minimum",
                                     "„rennt“ ist ein langes Wort"],
                                    "Ein Satz braucht Sinn, nicht eine "
                                    "Mindestlänge.")}},
                        {
                            "key": "satz_zu_kurz",
                            "label": "Kurze Sätze werden nicht gezählt",
                            "beschreibung": "„Er schläft.“ wird für keinen "
                            "Satz gehalten, weil er zu wenige Wörter hat.",
                            "antworten": ["zu kurz", "kein satz", "nein"],
                            "erklaerung": {
                                "haken": "„Es regnet.“ Nur zwei Wörter — "
                                        "und trotzdem ein vollständiger "
                                        "Satz.",
                                "erkenntnis": "Ein Satz braucht keinen "
                                "Mindestumfang. „Es regnet.“ sagt alles: "
                                "etwas passiert, und der Gedanke ist "
                                "fertig.",
                                "regel": "Was einen Satz zum Satz macht, "
                                "ist die Sinneinheit — nicht die "
                                "Wortzahl.",
                                "bild": {"zeigt": "ein kurzer und ein "
                                         "langer Satz nebeneinander",
                                         "bewegt": "beide werden mit "
                                         "demselben Satz-Rahmen umschlossen",
                                         "bleibt_gleich": "beide erzählen "
                                         "einen fertigen Gedanken"},
                                "aufgabe": {"frage": "Ist „Sie lacht.“ "
                                            "ein Satz? (ja/nein)",
                                            "loesung": "ja"}},
                            "visualisierung": _FLUSS(
                                ["„Es regnet.“",
                                 "Wer oder was? es.",
                                 "Was passiert? regnet.",
                                 "Gedanke fertig — zwei Wörter reichen"]),
                            "visualisierung_alternativ": _TABELLE(
                                ["Satz", "Wörter", "fertiger Gedanke"],
                                ["Es regnet. | 2 | ja",
                                 "Der Hund spielt im Garten. | 5 | ja",
                                 "rennt schnell | 2 | nein"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Welche Zeile ist ein Satz?",
                                    "Er schläft.",
                                    ["schläft tief", "Er"],
                                    "Zwei Wörter können einen fertigen "
                                    "Gedanken erzählen — Länge ist nicht "
                                    "entscheidend."),
                                "beispiel": aufgabe(
                                    "„Er schläft.“ Wer? Er. Was tut er? "
                                    "schläft. Ein fertiger Gedanke in zwei "
                                    "Wörtern.",
                                    "Er schläft.",
                                    schritte=["Wer? Er.",
                                              "Was? schläft.",
                                              "fertiger Gedanke"]),
                                "gefuehrt": aufgabe(
                                    "Ist „Sie lacht.“ ein Satz? "
                                    "(ja/nein)", "ja",
                                    fehler="nein",
                                    art="text",
                                    tipps=["Wer lacht? Was tut sie?",
                                           "Fehlt ein Gedanke?"]),
                                "selbststaendig": aufgabe(
                                    "Ist „Wir spielen.“ ein Satz? "
                                    "(ja/nein)", "ja",
                                    fehler="nein",
                                    art="text",
                                    tipps=["Enthält die Zeile einen "
                                           "fertigen Gedanken?"]),
                                "transfer": auswahl(
                                    "Warum ist „rennt schnell“ kein Satz, "
                                    "obwohl es zwei Wörter hat wie „Er "
                                    "schläft.“?",
                                    "Es sagt nicht, wer rennt — der "
                                    "Gedanke bleibt offen",
                                    ["Es hat keinen Punkt",
                                     "Es sind Verben"],
                                    "Es kommt auf den Gedanken an, nicht "
                                    "auf die Wortzahl.")}},
                    ],
                    "hilfe": _hilfe({
                        "HOOK": "Ein Satz erzählt einen fertigen Gedanken "
                                "— wer tut was.",
                        "RULE": "Satz = Sinneinheit: großer Anfang, Punkt, "
                                "und er ergibt als Ganzes Sinn.",
                        "WORKED_EXAMPLE": "Frage bei jeder Zeile: wer tut "
                                "was? Fehlt die Antwort, ist es kein Satz.",
                        "GUIDED_TASK": "Lies die Zeile laut. Erzählt sie "
                                "etwas Fertiges?",
                        "INDEPENDENT_TASK": "Wortzahl ist egal — der "
                                "Gedanke zählt.",
                        "ADAPTATION": "Schau dir die Tabelle an: was alle "
                                "Sätze gemeinsam haben, ist nicht ihre "
                                "Länge."}),
                    "faq": [
                        {"frage": "Ist jedes Wort eine Sinneinheit?",
                         "antwort": "Nein — „Ball“ allein erzählt nichts. "
                                    "Ein Satz verbindet Wörter zu einem "
                                    "fertigen Gedanken."},
                        {"frage": "Muss ein Satz immer mit Punkt enden?",
                         "antwort": "Geschrieben ja — Satzzeichen gehören "
                                    "dazu. Aber was ihn zum Satz macht, "
                                    "ist der fertige Gedanke."}],
                }},
            # ----------------------------------------------- Wortarten
            {
                "id": "DE.WORTARTEN.GRUNDLAGEN",
                "title": "Nomen und Verben erkennen",
                "description": "Die zwei wichtigsten Wortarten: Wer oder "
                               "was (Nomen) und was geschieht (Verb).",
                "first_contact_grade": 2, "target_grade": 3,
                "prerequisites": ["DE.SATZ.SINNEINHEIT"],
                "levels": {
                    "below": "K2: Satz als Sinneinheit",
                    "target": "K3: Nomen und Verben im Satz erkennen",
                    "above": "K4: Artikel, Adjektive — und Satzglieder"},
                "can_do": {
                    "below": ["einen Satz von einer Wortreihe "
                              "unterscheiden"],
                    "target": ["in einem einfachen Satz das Nomen (wer/ "
                               "was) und das Verb (was geschieht) nennen"],
                    "above": ["Subjekt und Prädikat bestimmen"]},
                "difficulty_parameters": {
                    "wortarten": "Nomen, Verb",
                    "satz": "einfache Hauptsätze"},
                "anchor_items": [
                    item("Welches Wort ist ein Nomen: „Der Hund spielt.“?",
                         "Hund", level="target", grade=3,
                         answer=text("hund", "der hund")),
                    item("Welches Wort beschreibt, was geschieht: „Die "
                         "Katze schläft.“?", "schläft",
                         level="target", grade=3,
                         answer=text("schläft"))],
                "boundary_items": {
                    "below": [item("Ist „Der Vogel fliegt.“ ein Satz? "
                                   "(ja/nein)", "ja", level="below",
                                   grade=2, answer=text("ja"))],
                    "within": [item("Finde das Nomen: „Lena liest.“",
                                    "Lena", level="target", grade=3,
                                    answer=text("lena"))],
                    "above": [item("Welches Satzglied ist „der Hund“ in "
                                   "„Der Hund spielt.“?", "Subjekt",
                                   level="above", grade=4,
                                   answer=text("subjekt"))]},
                "diagnostics": {
                    "misconceptions": [
                        {"key": "F1", "description": "Jedes große Wort wird "
                         "für ein Nomen gehalten — auch „Der“ oder "
                         "Begriffe am Satzanfang aus Gewohnheit.",
                         "remediation_hint": "Nomen beantworten die Frage "
                         "„wer oder was?“ — nicht „welches Wort ist groß?“.",
                         "diagnostic_item": item(
                             "Welches Wort ist ein Nomen: „Der Hund "
                             "spielt.“?", "Hund", level="target", grade=3,
                             answer=choice("Hund", ["Der", "spielt"],
                                           ["F1", None]),
                             distractors=[])},
                        {"key": "F2", "description": "Verb und Nomen werden "
                         "vertauscht: „spielt“ wird als das Wichtige für "
                         "das Nomen gehalten.",
                         "remediation_hint": "Das Verb sagt, was "
                         "geschieht — es ist die Tätigkeit, nicht das "
                         "Ding.",
                         "diagnostic_item": item(
                             "Welches Wort beschreibt die Tätigkeit: "
                             "„Der Hund spielt.“?", "spielt",
                             level="target", grade=3,
                             answer=choice("spielt", ["Hund", "Der"],
                                           ["F2", "F1"]),
                             distractors=[])}],
                    "diagnostic_items": [
                        item("Welche Zeile ist ein Satz?",
                             "Mia liest.", level="below", grade=2,
                             answer=choice("Mia liest.",
                                           ["Mia liest Buch",
                                            "liest"], [None, None])),
                        item("Finde das Verb: „Der Ball rollt.“",
                             "rollt", level="target", grade=3,
                             answer=text("rollt"))],
                    "exit_items": [
                        item("Finde das Nomen und das Verb: „Tom lacht.“",
                             "Tom (Nomen), lacht (Verb)",
                             level="target", grade=3,
                             answer=text("tom und lacht", "tom, lacht",
                                         "tom lacht")),
                        item("Welches Wort ist ein Nomen: „Die Sonne "
                             "scheint.“?", "Sonne", level="target",
                             grade=3, answer=text("sonne"))]},
                "lektion": {
                    "konzept": {
                        "konzept_key": "grundlagen", "thema_key": "wortarten",
                        "label": "Nomen und Verben",
                        "klasse_von": 2, "klasse_bis": 4,
                        "stichworte": ["nomen", "verb", "wortarten",
                                       "nomen und verben", "was geschieht"]},
                    "erstkontakt": {
                        "anker": "„Der Hund spielt.“ Welches Wort nennt, "
                                 "WER spielt — und welches sagt, WAS er tut?",
                        "benennung": "Nomen und Verb",
                        "erste_aufgabe": {"frage": "Welches Wort beschreibt "
                                          "die Tätigkeit: „Die Katze "
                                          "schläft.“?",
                                          "loesung": "schläft"}},
                    "fehlertypen": [
                        {
                            "key": "gross_ist_nomen",
                            "label": "Großes Wort wird zum Nomen",
                            "beschreibung": "Die Großschreibung wird zum "
                            "einzigen Merkmal — „Der“ oder Satzanfang "
                            "zählt als Nomen.",
                            "antworten": ["der", "Der"],
                            "erklaerung": {
                                "haken": "„Der Hund spielt.“ Welches Wort "
                                        "ist das Nomen? Wer „Der“ sagt, "
                                        "schaut nur auf den Buchstaben.",
                                "erkenntnis": "Das Nomen beantwortet die "
                                "Frage „wer oder was?“ — Hund. „Der“ ist "
                                "nur ein Begleiter, der das Nomen "
                                "ankündigt.",
                                "regel": "Nomen nennen Personen, Tiere, "
                                "Dinge: wer oder was? Der Begleiter "
                                "(der, die, das) gehört dazu, ist aber "
                                "nicht das Nomen selbst.",
                                "bild": {"zeigt": "„der Hund“ — Begleiter "
                                         "und Nomen getrennt markiert",
                                         "bewegt": "der Begleiter rückt "
                                         "an das Nomen heran",
                                         "bleibt_gleich": "das Nomen "
                                         "bleibt das Dingwort"},
                                "aufgabe": {"frage": "Welches Wort ist das "
                                            "Nomen: „Die Katze miaut.“?",
                                            "loesung": "Katze"}},
                            "visualisierung": _NETZ(
                                ["Nomen", "wer oder was?", "Begleiter",
                                 "groß geschrieben"],
                                ["Nomen → wer oder was?",
                                 "Begleiter → Nomen",
                                 "Nomen → groß geschrieben"]),
                            "visualisierung_alternativ": _FLUSS(
                                ["Satz lesen",
                                 "Frage: wer oder was?",
                                 "Das Wort, das antwortet, ist das Nomen"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Welches Wort ist das Nomen: „Der "
                                    "Ball rollt.“?", "Ball",
                                    ["Der", "rollt"],
                                    "Frag „wer oder was rollt?“ — der "
                                    "Begleiter „Der“ antwortet nicht."),
                                "beispiel": aufgabe(
                                    "„Die Maus piept.“ Wer piept? Die "
                                    "Maus — das Nomen heißt Maus.",
                                    "Maus",
                                    schritte=["Wer piept? die Maus",
                                              "Nomen: Maus",
                                              "„Die“ ist nur der Begleiter"]),
                                "gefuehrt": aufgabe(
                                    "Finde das Nomen: „Ein Vogel singt.“",
                                    "Vogel",
                                    fehler="Ein",
                                    art="begriffe",
                                    rubrik=begriffe("vogel"),
                                    tipps=["Frage: wer singt?",
                                           "„Ein“ kündigt das Nomen nur an."]),
                                "selbststaendig": aufgabe(
                                    "Finde das Nomen: „Das Kind lacht.“",
                                    "Kind",
                                    fehler="Das",
                                    art="begriffe",
                                    rubrik=begriffe("kind"),
                                    tipps=["Wer lacht?"]),
                                "transfer": auswahl(
                                    "Warum ist „Der“ kein Nomen, obwohl "
                                    "es groß geschrieben wird?",
                                    "Es benennt nichts — es begleitet das "
                                    "Nomen nur",
                                    ["Es steht am Anfang",
                                     "Es ist ein Artikel"],
                                    "Die Frage „wer oder was?“ findet das "
                                    "Nomen — nicht die Großschreibung.")}},
                        {
                            "key": "verb_nomen_tausch",
                            "label": "Verb und Nomen vertauscht",
                            "beschreibung": "Das Tätigkeitswort wird für "
                            "das Dingwort gehalten — und umgekehrt.",
                            "antworten": ["spielt", "läuft"],
                            "erklaerung": {
                                "haken": "Welches Wort ist die Tätigkeit: "
                                        "„Der Hund spielt.“ — wer „Hund“ "
                                        "sagt, hat die Rollen vertauscht.",
                                "erkenntnis": "Das Verb sagt, was "
                                "geschieht: spielt. Das Nomen nennt, wer "
                                "es tut: Hund. Zwei Fragen, zwei "
                                "Wortarten.",
                                "regel": "Verb = was geschieht (tun). "
                                "Nomen = wer oder was es tut. Erst die "
                                "Tätigkeit suchen, dann den Täter.",
                                "bild": {"zeigt": "Hund und „spielt“ "
                                         "in zwei Rollen",
                                         "bewegt": "die Rollen-Schilder "
                                         "werden den Wörtern zugeordnet",
                                         "bleibt_gleich": "beide Wörter "
                                         "bleiben im Satz"},
                                "aufgabe": {"frage": "Welches Wort ist das "
                                            "Verb: „Mia liest.“?",
                                            "loesung": "liest"}},
                            "visualisierung": _FLUSS(
                                ["„Der Hund spielt.“",
                                 "Was geschieht? spielt → Verb",
                                 "Wer tut es? der Hund → Nomen"]),
                            "visualisierung_alternativ": _TABELLE(
                                ["Frage", "Wort", "Wortart"],
                                ["wer oder was? | Hund | Nomen",
                                 "was geschieht? | spielt | Verb"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Welches Wort beschreibt die "
                                    "Tätigkeit: „Der Ball rollt.“?",
                                    "rollt", ["Ball", "Der"],
                                    "Die Tätigkeit ist das Verb — was "
                                    "geschieht, nicht wer es tut."),
                                "beispiel": aufgabe(
                                    "„Lena lacht.“ Was geschieht? lacht "
                                    "— das Verb. Wer? Lena — das Nomen.",
                                    "lacht"),
                                "gefuehrt": aufgabe(
                                    "Finde das Verb: „Tom rennt.“",
                                    "rennt",
                                    fehler="Tom",
                                    art="begriffe",
                                    rubrik=begriffe("rennt"),
                                    tipps=["Was geschieht im Satz?",
                                           "Tom ist der, der es tut — "
                                           "nicht das Tun."]),
                                "selbststaendig": aufgabe(
                                    "Finde das Verb: „Die Katze miaut.“",
                                    "miaut",
                                    fehler="Katze",
                                    art="begriffe",
                                    rubrik=begriffe("miaut"),
                                    tipps=["Welches Wort beschreibt "
                                           "die Tätigkeit?"]),
                                "transfer": auswahl(
                                    "In „Mia liest ein Buch“: warum ist "
                                    "„liest“ das Verb und nicht „Buch“?",
                                    "Es sagt, was Mia tut — das Buch ist "
                                    "eine Sache",
                                    ["„liest“ steht in der Mitte",
                                     "„Buch“ ist kein Verb"],
                                    "Das Verb beschreibt das Geschehen — "
                                    "das Nomen benennt.")}},
                    ],
                    "hilfe": _hilfe({
                        "HOOK": "Jeder Satz hat einen Täter und eine Tat — "
                                "finde zuerst die Tat.",
                        "RULE": "Verb = was geschieht. Nomen = wer oder "
                                "was es tut. Zwei Fragen, zwei Wortarten.",
                        "WORKED_EXAMPLE": "Unterstreiche das Verb, dann "
                                "frage: wer tut das?",
                        "GUIDED_TASK": "Was geschieht im Satz? Das ist "
                                "dein Verb.",
                        "INDEPENDENT_TASK": "Prüfe mit den Fragen: wer "
                                "oder was? — was geschieht?",
                        "ADAPTATION": "Das Netz zeigt, wie Begleiter und "
                                "Nomen zusammenhängen."}),
                    "faq": [
                        {"frage": "Woran erkenne ich ein Verb?",
                         "antwort": "Es sagt, was geschieht: schläft, "
                                    "spielt, rennt. Du kannst es "
                                    "verändern: er schläft — er schlief."},
                        {"frage": "Ist „der“ ein Nomen?",
                         "antwort": "Nein — „der“ ist ein Begleiter. Er "
                                    "steht vor dem Nomen und kündigt es "
                                    "an, benennt aber nichts selbst."}],
                }},
            # --------------------------------- Subjekt und Prädikat
            {
                "id": "DE.SATZGLIEDER.SUBJEKT_PRAEDIKAT",
                "title": "Subjekt und Prädikat",
                "description": "Die zwei Pflichtteile jedes Satzes: wer "
                               "oder was (Subjekt) und was geschieht "
                               "(Prädikat).",
                "first_contact_grade": 3, "target_grade": 4,
                "prerequisites": ["DE.WORTARTEN.GRUNDLAGEN"],
                "levels": {
                    "below": "K3: Nomen und Verb im Satz finden",
                    "target": "K4: Subjekt und Prädikat bestimmen, "
                              "Prädikat auf Platz 2",
                    "above": "K5: Objekte und adverbiale Bestimmungen"},
                "can_do": {
                    "below": ["Nomen und Verb unterscheiden"],
                    "target": ["Subjekt und Prädikat in einem Hauptsatz "
                               "zuverlässig bestimmen"],
                    "above": ["alle Satzglieder eines Satzes bestimmen"]},
                "difficulty_parameters": {
                    "satzart": "Aussagesätze", "laenge": "bis 8 Wörter"},
                "anchor_items": [
                    item("Was ist das Prädikat: „Der Hund spielt im "
                         "Garten.“?", "spielt", level="target", grade=4,
                         answer=text("spielt")),
                    item("Was ist das Subjekt: „Die Katze schläft auf dem "
                         "Sofa.“?", "Die Katze", level="target", grade=4,
                         answer=text("die katze", "katze"))],
                "boundary_items": {
                    "below": [item("Finde das Verb: „Der Ball rollt.“",
                                   "rollt", level="below", grade=3,
                                   answer=text("rollt"))],
                    "within": [item("Subjekt in „Mia liest ein Buch.“?",
                                    "Mia", level="target", grade=4,
                                    answer=text("mia"))],
                    "above": [item("Welches Satzglied ist „im Garten“ in "
                                   "„Der Hund spielt im Garten.“?",
                                   "adverbiale Bestimmung", level="above",
                                   grade=5,
                                   answer=text("adverbiale bestimmung",
                                               "adverbial"))]},
                "diagnostics": {
                    "misconceptions": [
                        {"key": "F1", "description": "Subjekt wird mit dem "
                         "ersten Wort gleichgesetzt — bei Umstellung wird "
                         "das Adverbial zum Subjekt.",
                         "remediation_hint": "Subjekt beantwortet die "
                         "Frage „wer oder was?“ — die Position ist "
                         "tauschbar.",
                         "diagnostic_item": item(
                             "Subjekt in „Im Garten spielt der Hund.“?",
                             "der Hund", level="target", grade=4,
                             answer=choice("der Hund", ["Im Garten",
                                                        "spielt"],
                                           ["F1", None]),
                             distractors=[])},
                        {"key": "F2", "description": "Das Prädikat wird als "
                         "mehrteiliges Verb („spielt gern“) nicht "
                         "erkannt — nur das erste Verb zählt.",
                         "remediation_hint": "Das Prädikat sind alle "
                         "Verbteile zusammen — sie gehören zum selben "
                         "Geschehen.",
                         "diagnostic_item": item(
                             "Prädikat in „Tom hat gespielt.“?",
                             "hat gespielt", level="target", grade=4,
                             answer=choice("hat gespielt", ["hat",
                                                          "gespielt"],
                                           ["F2", "F2"]),
                             distractors=[])}],
                    "diagnostic_items": [
                        item("Finde das Verb: „Der Vogel singt.“",
                             "singt", level="below", grade=3,
                             answer=text("singt")),
                        item("Subjekt in „Die Sonne scheint hell.“?",
                             "Die Sonne", level="target", grade=4,
                             answer=text("die sonne", "sonne"))],
                    "exit_items": [
                        item("Bestimme Subjekt und Prädikat: „Der Lehrer "
                             "erklärt die Aufgabe.“",
                             "Der Lehrer (Subjekt), erklärt (Prädikat)",
                             level="target", grade=4,
                             answer=text("der lehrer, erklärt",
                                         "der lehrer und erklärt",
                                         "der lehrer erklärt")),
                        item("Prädikat in „Mia hat gespielt.“?",
                             "hat gespielt", level="target", grade=4,
                             answer=text("hat gespielt"))]},
                "lektion": {
                    "konzept": {
                        "konzept_key": "subjekt_praedikat",
                        "thema_key": "satzglieder",
                        "label": "Subjekt und Prädikat",
                        "klasse_von": 3, "klasse_bis": 5,
                        "stichworte": ["subjekt", "prädikat",
                                       "subjekt und prädikat",
                                       "satzglieder bestimmen",
                                       "wer oder was"]},
                    "erstkontakt": {
                        "anker": "„Der Hund spielt im Garten.“ Zwei Teile "
                                 "davon kann kein Satz weglassen — "
                                 "welche?",
                        "benennung": "Subjekt und Prädikat",
                        "erste_aufgabe": {"frage": "Was ist das Prädikat: "
                                          "„Mia liest ein Buch.“?",
                                          "loesung": "liest"}},
                    "fehlertypen": [
                        {
                            "key": "erstes_ist_subjekt",
                            "label": "Erstes Wort wird zum Subjekt",
                            "beschreibung": "Die Position am Satzanfang "
                            "entscheidet — bei Umstellung wird „Im Garten“ "
                            "zum Subjekt.",
                            "antworten": ["im garten", "Im Garten"],
                            "erklaerung": {
                                "haken": "„Im Garten spielt der Hund.“ "
                                        "Wer „Im Garten“ als Subjekt "
                                        "nennt, hat auf die Position "
                                        "geschaut — nicht auf die Frage.",
                                "erkenntnis": "Das Subjekt beantwortet "
                                "„wer oder was tut etwas?“ — der Hund. "
                                "Sätze lassen sich umstellen, ohne dass "
                                "die Rollen wechseln.",
                                "regel": "Subjekt = wer oder was? Prädikat "
                                "= was geschieht? Im Aussagesatz steht "
                                "das Prädikat an zweiter Stelle — das "
                                "Subjekt darf auch hinten stehen.",
                                "bild": {"zeigt": "derselbe Satz zweimal "
                                         "mit vertauschten Gliedern",
                                         "bewegt": "die Glieder "
                                         "wechseln Plätze, ihre "
                                         "Rollen-Schilder bleiben",
                                         "bleibt_gleich": "Subjekt und "
                                         "Prädikat bleiben dieselben"},
                                "aufgabe": {"frage": "Subjekt in „Heute "
                                            "lernt Mia.“?", "loesung": "Mia"}},
                            "visualisierung": _FLUSS(
                                ["Prädikat suchen: was geschieht? spielt",
                                 "Prädikat-Frage: wer spielt? der Hund",
                                 "„Im Garten“ beantwortet wo — nicht wer"]),
                            "visualisierung_alternativ": _TABELLE(
                                ["Satzglied", "Frage", "Antwort"],
                                ["Im Garten | wo? | Adverbial",
                                 "der Hund | wer? | Subjekt",
                                 "spielt | was geschieht? | Prädikat"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Subjekt in „Im Garten spielt der "
                                    "Hund.“?", "der Hund",
                                    ["Im Garten", "spielt"],
                                    "Frag „wer spielt?“ — die Position "
                                    "am Anfang täuscht."),
                                "beispiel": aufgabe(
                                    "„Heute liest Mia ein Buch.“ Was "
                                    "geschieht? liest. Wer liest? Mia — "
                                    "das ist das Subjekt.",
                                    "Mia",
                                    schritte=["Prädikat: liest",
                                              "wer liest? Mia",
                                              "„Heute“ beantwortet wann"]),
                                "gefuehrt": aufgabe(
                                    "Bestimme das Subjekt: „Am Montag "
                                    "spielt Tom Fußball.“",
                                    "Tom",
                                    fehler="Am Montag",
                                    art="begriffe",
                                    rubrik=begriffe("tom"),
                                    tipps=["Was geschieht zuerst finden.",
                                           "Dann: wer spielt?"]),
                                "selbststaendig": aufgabe(
                                    "Bestimme das Subjekt: „Im Wald "
                                    "läuft ein Fuchs.“",
                                    "ein Fuchs",
                                    fehler="Im Wald",
                                    art="begriffe",
                                    rubrik=begriffe("fuchs"),
                                    tipps=["Wer läuft?"]),
                                "transfer": auswahl(
                                    "Warum kann „Im Garten“ nie das "
                                    "Subjekt dieses Satzes sein?",
                                    "Es beantwortet „wo“, nicht „wer "
                                    "oder was“ — Orte tun nichts",
                                    ["Es steht am Anfang",
                                     "Es hat drei Wörter"],
                                    "Die Frage entscheidet das Satzglied, "
                                    "nicht die Position.")}},
                        {
                            "key": "verbteile_getrennt",
                            "label": "Mehrteiliges Prädikat getrennt",
                            "beschreibung": "„hat gespielt“ wird als zwei "
                            "getrennte Wörter gelesen — das Hilfsverb "
                            "allein gilt als Prädikat.",
                            "antworten": ["hat", "gespielt"],
                            "erklaerung": {
                                "haken": "„Tom hat gespielt.“ Was ist das "
                                        "Prädikat? Wer „hat“ sagt, lässt "
                                        "die halbe Tätigkeit liegen.",
                                "erkenntnis": "„hat gespielt“ ist EIN "
                                "Geschehen in zwei Wortteilen: das "
                                "Hilfsverb trägt die Zeit, das "
                                "Vollverb trägt den Inhalt.",
                                "regel": "Das Prädikat umfasst alle "
                                "Verbteile: „hat gespielt“, „wird "
                                "lesen“, „kann spielen“. Sie gehören "
                                "zusammen.",
                                "bild": {"zeigt": "„hat“ und „gespielt“ "
                                         "als zwei Teile eines "
                                         "Verb-Pakets",
                                         "bewegt": "die Teile rücken "
                                         "zusammen und werden "
                                         "eingerahmt",
                                         "bleibt_gleich": "das Geschehen "
                                         "bleibt dasselbe"},
                                "aufgabe": {"frage": "Prädikat in „Lena "
                                            "wird singen.“?",
                                            "loesung": "wird singen"}},
                            "visualisierung": _FLUSS(
                                ["„Tom hat gespielt.“",
                                 "das ganze Geschehen: hat gespielt",
                                 "„hat“ trägt die Zeit, „gespielt“ den "
                                 "Inhalt"]),
                            "visualisierung_alternativ": _TABELLE(
                                ["Satz", "Prädikat"],
                                ["Tom spielt. | spielt",
                                 "Tom hat gespielt. | hat gespielt",
                                 "Tom wird spielen. | wird spielen"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Prädikat in „Tom hat gespielt.“?",
                                    "hat gespielt",
                                    ["hat", "gespielt"],
                                    "Beide Verbteile gehören zum selben "
                                    "Geschehen — das Prädikat nimmt "
                                    "beide."),
                                "beispiel": aufgabe(
                                    "„Mia wird lesen.“ Das Geschehen "
                                    "braucht beide Teile: wird lesen.",
                                    "wird lesen",
                                    schritte=["Geschehen: wird lesen",
                                              "„wird“ = Zeit, „lesen“ = Inhalt"]),
                                "gefuehrt": aufgabe(
                                    "Prädikat in „Der Zug ist gefahren.“?",
                                    "ist gefahren",
                                    fehler="ist",
                                    art="begriffe",
                                    rubrik=begriffe("ist", "gefahren"),
                                    tipps=["Welche Verbteile gehören zum "
                                           "Geschehen?",
                                           "„ist“ allein trägt nur die Zeit."]),
                                "selbststaendig": aufgabe(
                                    "Prädikat in „Mia kann singen.“?",
                                    "kann singen",
                                    fehler="kann",
                                    art="begriffe",
                                    rubrik=begriffe("kann", "singen"),
                                    tipps=["Das ganze Geschehen — beide Teile."]),
                                "transfer": auswahl(
                                    "Warum gehört „kann“ in „Mia kann "
                                    "singen“ zum Prädikat?",
                                    "Es ist Teil des Geschehens — ohne es "
                                    "fehlt die Aussage über das Können",
                                    ["Es steht auf Platz 2",
                                     "Es ist ein Hilfsverb"],
                                    "Das Prädikat ist die Einheit des "
                                    "Geschehens — in wie viele Wörter "
                                    "auch immer sie fällt.")}},
                    ],
                    "hilfe": _hilfe({
                        "HOOK": "Jeder Satz hat zwei Pflichtteile: wer "
                                "oder was — und was geschieht.",
                        "RULE": "Prädikat = alle Verbteile (was "
                                "geschieht). Subjekt = wer oder was es "
                                "tut. Das Prädikat steht auf Platz 2.",
                        "WORKED_EXAMPLE": "Erst das Geschehen finden, "
                                "dann fragen: wer tut das?",
                        "GUIDED_TASK": "Unterstreiche das Verb (alle "
                                "Teile!), dann frage „wer oder was?“.",
                        "INDEPENDENT_TASK": "Position täuscht — die "
                                "Frage entscheidet das Satzglied.",
                        "ADAPTATION": "Die Tabelle zeigt Satz für Satz "
                                "dieselbe Regel."}),
                    "faq": [
                        {"frage": "Kann das Subjekt hinten stehen?",
                         "antwort": "Ja — „Heute spielt Tom.“ Das "
                                    "Subjekt beantwortet „wer oder "
                                    "was?“, egal an welcher Stelle."},
                        {"frage": "Was gehört alles zum Prädikat?",
                         "antwort": "Alle Verbteile: „hat gespielt“ ist "
                                    "ein Prädikat aus zwei Wörtern. Es "
                                    "ist ein Geschehen."}],
                }},
            # ------------------------------------- Satzglieder bestimmen
            {
                "id": "DE.SATZGLIEDER.BESTIMMEN",
                "title": "Alle Satzglieder bestimmen",
                "description": "Subjekt, Prädikat, Objekte und adverbiale "
                               "Bestimmungen — der vollständige Bauplan "
                               "eines Satzes.",
                "first_contact_grade": 4, "target_grade": 5,
                "prerequisites": ["DE.SATZGLIEDER.SUBJEKT_PRAEDIKAT"],
                "levels": {
                    "below": "K4: Subjekt und Prädikat sicher",
                    "target": "K5: alle Satzglieder mit den "
                              "Gliederfragen bestimmen",
                    "above": "K6: Glieder vertauschen, Satzglieder in "
                             "zusammengesetzten Sätzen"},
                "can_do": {
                    "below": ["Subjekt und Prädikat bestimmen"],
                    "target": ["einen Hauptsatz vollständig in seine "
                               "Satzglieder zerlegen"],
                    "above": ["Satzglieder in Nebensätzen erkennen"]},
                "difficulty_parameters": {
                    "glieder": "Subjekt, Prädikat, Akkusativ-/Dativobjekt, "
                               "adverbiale Bestimmung",
                    "satz": "Hauptsätze bis 10 Wörter"},
                "anchor_items": [
                    item("Welches Satzglied ist „dem Hund“ in „Lena "
                         "gibt dem Hund den Ball.“?",
                         "Dativobjekt", level="target", grade=5,
                         answer=text("dativobjekt", "dativ")),
                    item("Welches Satzglied ist „im Garten“ in „Der Hund "
                         "spielt im Garten.“?",
                         "adverbiale Bestimmung", level="target", grade=5,
                         answer=text("adverbiale bestimmung",
                                     "adverbial"))],
                "boundary_items": {
                    "below": [item("Subjekt in „Der Hund spielt.“?",
                                   "Der Hund", level="below", grade=4,
                                   answer=text("der hund", "hund"))],
                    "within": [item("Welches Satzglied ist „den Ball“ in "
                                    "„Lena wirft den Ball.“?",
                                    "Akkusativobjekt", level="target",
                                    grade=5,
                                    answer=text("akkusativobjekt",
                                                "akkusativ", "objekt"))],
                    "above": [item("In „Weil es regnet, bleibt Tom "
                                   "daheim“ — welches Satzglied ist "
                                   "„weil es regnet“?",
                                   "Nebensatz", level="above", grade=6,
                                   answer=text("nebensatz"))]},
                "diagnostics": {
                    "misconceptions": [
                        {"key": "F1", "description": "Alles nach dem Verb "
                         "wird zum Objekt — adverbiale Bestimmungen wie "
                         "„im Garten“ werden falsch benannt.",
                         "remediation_hint": "Die Gliederfrage "
                         "entscheidet: „wo?“ ist keine Objektfrage.",
                         "diagnostic_item": item(
                             "Welches Satzglied ist „im Garten“ in "
                             "„Der Hund spielt im Garten.“?",
                             "adverbiale Bestimmung", level="target",
                             grade=5,
                             answer=choice("adverbiale Bestimmung",
                                           ["Objekt", "Subjekt"],
                                           ["F1", None]),
                             distractors=[])},
                        {"key": "F2", "description": "Dativ- und "
                         "Akkusativobjekt werden vertauscht — „dem Hund“ "
                         "wird zum Akkusativ, weil es nach „wen oder "
                         "was“ klingt.",
                         "remediation_hint": "Zwei Fragen: „wen oder "
                         "was?“ → Akkusativ; „wem?“ → Dativ.",
                         "diagnostic_item": item(
                             "Welches Satzglied ist „dem Hund“ in „Lena "
                             "gibt dem Hund den Ball.“?",
                             "Dativobjekt", level="target", grade=5,
                             answer=choice("Dativobjekt",
                                           ["Akkusativobjekt",
                                            "adverbiale Bestimmung"],
                                           ["F2", "F1"]),
                             distractors=[])}],
                    "diagnostic_items": [
                        item("Subjekt in „Die Lehrerin erklärt die "
                             "Regel.“?", "Die Lehrerin", level="below",
                             grade=4,
                             answer=text("die lehrerin", "lehrerin")),
                        item("Welches Satzglied ist „den Ball“ in "
                             "„Tom wirft den Ball.“?",
                             "Akkusativobjekt", level="target", grade=5,
                             answer=text("akkusativobjekt",
                                         "akkusativ"))],
                    "exit_items": [
                        item("Zerlege: „Lena gibt dem Hund den Ball.“ "
                             "Nenne alle Satzglieder.",
                             "Lena Subjekt, gibt Prädikat, dem Hund "
                             "Dativobjekt, den Ball Akkusativobjekt",
                             level="target", grade=5,
                             answer=text(
                                 "lena subjekt gibt praedikat dem hund "
                                 "dativ den ball akkusativ")),
                        item("Welches Satzglied ist „heute“ in „Heute "
                             "lernt Mia.“?",
                             "adverbiale Bestimmung", level="target",
                             grade=5,
                             answer=text("adverbiale bestimmung",
                                         "adverbial"))]},
                "lektion": {
                    "konzept": {
                        "konzept_key": "bestimmen",
                        "thema_key": "satzglieder",
                        "label": "Alle Satzglieder bestimmen",
                        "klasse_von": 4, "klasse_bis": 6,
                        "stichworte": ["satzglieder", "objekt",
                                       "akkusativobjekt", "dativobjekt",
                                       "adverbiale bestimmung",
                                       "satzglieder bestimmen"]},
                    "erstkontakt": {
                        "anker": "„Lena gibt dem Hund den Ball.“ Vier "
                                 "Satzglieder — kannst du sie alle "
                                 "benennen?",
                        "benennung": "Satzglieder",
                        "erste_aufgabe": {"frage": "Welches Satzglied "
                                          "ist „den Ball“?",
                                          "loesung": "Akkusativobjekt"}},
                    "fehlertypen": [
                        {
                            "key": "alles_objekt",
                            "label": "Alles nach dem Verb wird zum Objekt",
                            "beschreibung": "Orts- und Zeitangaben werden "
                            "zu Objekten erklärt, weil sie hinter dem "
                            "Verb stehen.",
                            "antworten": ["objekt", "ein objekt"],
                            "erklaerung": {
                                "haken": "„Der Hund spielt im Garten.“ "
                                        "„im Garten“ steht hinter dem "
                                        "Verb — ist es ein Objekt?",
                                "erkenntnis": "Jedes Satzglied hat seine "
                                "eigene Frage. „im Garten“ beantwortet "
                                "„wo?“ — das ist kein Objekt, sondern "
                                "eine adverbiale Bestimmung.",
                                "regel": "Objektfragen: wen oder was? "
                                "(Akkusativ), wem? (Dativ). "
                                "Adverbiale: wo, wann, wie, warum? Die "
                                "Frage entscheidet, nicht die Position.",
                                "bild": {"zeigt": "vier Fragen und je "
                                         "ein Satzglied",
                                         "bewegt": "die Glieder "
                                         "wandern zu ihren Fragen",
                                         "bleibt_gleich": "der Satz "
                                         "bleibt derselbe"},
                                "aufgabe": {"frage": "Welches Satzglied "
                                            "ist „heute“ in „Heute "
                                            "lernt Mia.“?",
                                            "loesung": "adverbiale "
                                                       "Bestimmung"}},
                            "visualisierung": _NETZ(
                                ["Satzglied", "Subjekt", "Prädikat",
                                 "Akkusativobjekt", "Dativobjekt",
                                 "adverbiale Bestimmung"],
                                ["wer oder was? → Subjekt",
                                 "was geschieht? → Prädikat",
                                 "wen oder was? → Akkusativobjekt",
                                 "wem? → Dativobjekt",
                                 "wo/wann/wie? → adverbiale Bestimmung"]),
                            "visualisierung_alternativ": _TABELLE(
                                ["Frage", "Satzglied", "Beispiel"],
                                ["wer oder was? | Subjekt | Der Hund",
                                 "was geschieht? | Prädikat | spielt",
                                 "wen oder was? | Akkusativ | den Ball",
                                 "wem? | Dativ | dem Hund",
                                 "wo? wann? | Adverbial | im Garten"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Welches Satzglied ist „im Garten“ "
                                    "in „Der Hund spielt im Garten.“?",
                                    "adverbiale Bestimmung",
                                    ["Objekt", "Subjekt"],
                                    "„im Garten“ beantwortet „wo?“ — "
                                    "das ist die Adverbialfrage."),
                                "beispiel": aufgabe(
                                    "„Mia lernt heute.“ „heute“ "
                                    "beantwortet „wann?“ — eine "
                                    "adverbiale Bestimmung.",
                                    "adverbiale Bestimmung"),
                                "gefuehrt": aufgabe(
                                    "Welches Satzglied ist „im Wald“ "
                                    "in „Ein Fuchs läuft im Wald.“?",
                                    "adverbiale Bestimmung",
                                    fehler="Objekt",
                                    art="begriffe",
                                    rubrik=begriffe("adverbiale", teilweise="Die genaue Bezeichnung fehlt noch: adverbiale Bestimmung."),
                                    tipps=["Welche Frage beantwortet "
                                           "„im Wald“?",
                                           "„wo?“ ist keine Objektfrage."]),
                                "selbststaendig": aufgabe(
                                    "Welches Satzglied ist „am Montag“ "
                                    "in „Am Montag spielt Tom.“?",
                                    "adverbiale Bestimmung",
                                    fehler="Subjekt",
                                    art="begriffe",
                                    rubrik=begriffe("adverbiale", teilweise="Die genaue Bezeichnung fehlt noch: adverbiale Bestimmung."),
                                    tipps=["Welche Frage — wann oder "
                                           "wer?"]),
                                "transfer": auswahl(
                                    "Warum hilft die Position „hinter "
                                    "dem Verb“ nicht beim Bestimmen?",
                                    "Objekte UND Adverbiale stehen dort — "
                                    "nur die Gliederfrage trennt sie",
                                    ["Das Verb steht mal vorne",
                                     "Es gibt zu viele Wörter"],
                                    "Die Position sagt wenig — die "
                                    "Frage, die das Glied beantwortet, "
                                    "alles.")}},
                        {
                            "key": "dativ_akkusativ",
                            "label": "Dativ- und Akkusativobjekt "
                                     "vertauscht",
                            "beschreibung": "„dem Hund“ wird zum "
                            "Akkusativobjekt — die „wem“-Frage wird "
                            "nicht gestellt.",
                            "antworten": ["akkusativobjekt", "akkusativ"],
                            "erklaerung": {
                                "haken": "„Lena gibt dem Hund den Ball.“ "
                                        "Zwei Objekte — welches ist "
                                        "welches?",
                                "erkenntnis": "„den Ball“ beantwortet "
                                "„wen oder was gibt sie?“ — Akkusativ. "
                                "„dem Hund“ beantwortet „wem gibt sie "
                                "ihn?“ — Dativ.",
                                "regel": "Akkusativ: wen oder was? — "
                                "das, was direkt gehandelt wird. Dativ: "
                                "wem? — der Empfänger.",
                                "bild": {"zeigt": "der Ball wandert von "
                                         "Lena zum Hund",
                                         "bewegt": "der Weg des Balls "
                                         "zeigt: von wem zu wem",
                                         "bleibt_gleich": "die Fragen "
                                         "bleiben dieselben"},
                                "aufgabe": {"frage": "Welches Satzglied "
                                            "ist „dem Kind“ in „Mia "
                                            "liest dem Kind vor.“?",
                                            "loesung": "Dativobjekt"}},
                            "visualisierung": _FLUSS(
                                ["„Lena gibt dem Hund den Ball.“",
                                 "wen oder was gibt sie? den Ball → Akkusativ",
                                 "wem gibt sie ihn? dem Hund → Dativ"]),
                            "visualisierung_alternativ": _TABELLE(
                                ["Frage", "Satzglied", "Beispiel"],
                                ["wen oder was? | Akkusativ | den Ball",
                                 "wem? | Dativ | dem Hund"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Welches Satzglied ist „dem Hund“ "
                                    "in „Lena gibt dem Hund den Ball.“?",
                                    "Dativobjekt",
                                    ["Akkusativobjekt",
                                     "adverbiale Bestimmung"],
                                    "„wem gibt sie den Ball?“ — dem "
                                    "Hund. Die Empfängerfrage heißt Dativ."),
                                "beispiel": aufgabe(
                                    "„Tom zeigt dem Vogel das Fenster.“ "
                                    "wem? dem Vogel → Dativ. was? das "
                                    "Fenster → Akkusativ.",
                                    "dem Vogel: Dativobjekt"),
                                "gefuehrt": aufgabe(
                                    "Welches Satzglied ist „dem Kind“ "
                                    "in „Mia liest dem Kind vor.“?",
                                    "Dativobjekt",
                                    fehler="Akkusativobjekt",
                                    art="begriffe",
                                    rubrik=begriffe("dativ", teilweise="Der Kasus stimmt — die vollstaendige Form ist Dativobjekt."),
                                    tipps=["Stell die „wem“-Frage.",
                                           "Akkusativ beantwortet „wen "
                                           "oder was?“."]),
                                "selbststaendig": aufgabe(
                                    "Welches Satzglied ist „ihrem "
                                    "Freund“ in „Tom hilft ihrem "
                                    "Freund.“?",
                                    "Dativobjekt",
                                    fehler="Akkusativobjekt",
                                    art="begriffe",
                                    rubrik=begriffe("dativ", teilweise="Der Kasus stimmt — die vollstaendige Form ist Dativobjekt."),
                                    tipps=["Wem hilft Tom?"]),
                                "transfer": auswahl(
                                    "Bei „helfen“ steht der Empfänger "
                                    "im Dativ, bei „geben“ auch. Woran "
                                    "erkennt man Dativ sicher?",
                                    "An der „wem“-Frage — sie trifft "
                                    "immer auf den Empfänger zu",
                                    ["Am „dem“ vor dem Wort",
                                     "An der Position hinter dem Verb"],
                                    "Die Frage ist das Werkzeug — die "
                                    "Form kann sich ändern.")}},
                    ],
                    "hilfe": _hilfe({
                        "HOOK": "Jedes Satzglied beantwortet seine eigene "
                                "Frage — finde erst die Frage.",
                        "RULE": "wer/was → Subjekt · was geschieht → "
                                "Prädikat · wen/was → Akkusativ · wem → "
                                "Dativ · wo/wann/wie → Adverbial.",
                        "WORKED_EXAMPLE": "Geh Glied für Glied: stell die "
                                "Frage, finde die Antwort.",
                        "GUIDED_TASK": "Welche Frage beantwortet das "
                                "Wort? Schreib sie hin.",
                        "INDEPENDENT_TASK": "Position zählt nicht — die "
                                "Frage entscheidet.",
                        "ADAPTATION": "Das Netz ordnet jeder Frage ihr "
                                "Satzglied zu."}),
                    "faq": [
                        {"frage": "Woran erkenne ich das Dativobjekt?",
                         "antwort": "An der „wem“-Frage: wem gibt sie "
                                    "den Ball? — dem Hund."},
                        {"frage": "Ist „im Garten“ ein Objekt?",
                         "antwort": "Nein — es beantwortet „wo?“, das "
                                    "ist eine adverbiale Bestimmung. "
                                    "Objekte beantworten wen-/wem-"
                                    "Fragen."}],
                }},
        ]}]}
