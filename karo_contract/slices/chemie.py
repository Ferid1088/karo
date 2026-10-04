"""Chemie-Slice: vom Stoff zur chemischen Reaktion.

Level 0: das Kind kennt Stoffe und ihre Zustände. Dann das Teilchen-
modell, dann die Reaktion als Umbau — und oben die Massenerhaltung,
die beweist, dass nichts „verschwindet“.

    CH.REAKTION.ERHALTUNG     (Ziel, Kl. 7–8)
      └── CH.REAKTION.BEGRIFF     (Kl. 7)
            └── CH.TEILCHEN.MODELL    (Kl. 5–6)
                  └── CH.STOFFE.BEGRIFF   (Kl. 3–4, Level 0)
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
    "fach": "chemie",
    "code": "CH",
    "name": "Chemie",
    "blocks": [{
        "id": "CH.GRUNDLAGEN",
        "title": "Stoffe, Teilchen und Reaktionen",
        "description": "Vom Stoff über das Teilchenmodell zur "
                       "chemischen Reaktion und zur "
                       "Massenerhaltung.",
        "grade_min": 3, "grade_max": 9, "typical_grade": 6,
        "concepts": [
            # ---------------------------------------------- Level 0
            {
                "id": "CH.STOFFE.BEGRIFF",
                "title": "Stoffe und ihre Zustände",
                "description": "Alles ist aus Stoffen — fest, "
                               "flüssig, gasförmig. Stoffe "
                               "unterscheiden sich durch ihre "
                               "Eigenschaften.",
                "first_contact_grade": 3, "target_grade": 4,
                "prerequisites": [],
                "levels": {
                    "below": "K1–2: Materialien benennen",
                    "target": "K4: Stoffe und ihre drei "
                              "Zustände erkennen und durch "
                              "Eigenschaften unterscheiden",
                    "above": "K5–6: das Teilchenmodell dahinter"},
                "can_do": {
                    "below": ["Alltagsmaterialien benennen"],
                    "target": ["einen Stoff seinem Zustand "
                               "zuordnen und eine "
                               "Eigenschaft nennen, die ihn "
                               "auszeichnet"],
                    "above": ["Stoffe durch Teilchen "
                              "erklären"]},
                "difficulty_parameters": {
                    "zustaende": "fest, flüssig, gasförmig",
                    "eigenschaften": "hart/weich, farbig, "
                                     "schmilzt, siedet"},
                "anchor_items": [
                    item("Wasser dampft — in welchem "
                         "Zustand ist es dann?",
                         "gasförmig", level="target", grade=4,
                         answer=text("gasförmig", "gas",
                                     "gasförmig (dampf)")),
                    item("Nenne einen festen Stoff.",
                         "Eisen", level="target", grade=4,
                         answer=text("eisen", "holz", "stein",
                                     "glas", "eis", "metall"))],
                "boundary_items": {
                    "below": [item("Ist Wasser ein Stoff?",
                                   "Ja", level="below",
                                   grade=3, answer=text("ja"))],
                    "within": [item("In welchem Zustand ist "
                                    "Eis?", "fest",
                                    level="target", grade=4,
                                    answer=text("fest"))],
                    "above": [item("Woraus besteht Wasser "
                                   "im Kleinsten?",
                                   "Aus Wasserteilchen",
                                   level="above", grade=6,
                                   answer=text("teilchen",
                                               "wasserteilchen",
                                               "moleküle",
                                               "molekülen"))]},
                "diagnostics": {
                    "misconceptions": [
                        {"key": "F1", "description": "Luft "
                         "und Dampf gelten als „nichts“ — "
                         "was unsichtbar ist, ist kein "
                         "Stoff.",
                         "remediation_hint": "Luft drückt "
                         "den Ballon auf — unsichtbar "
                         "heißt nicht nichts.",
                         "diagnostic_item": item(
                             "Ist Luft ein Stoff?",
                             "Ja, sie ist gasförmig",
                             level="target", grade=4,
                             answer=choice("Ja, gasförmig",
                                           ["Nein, Luft ist "
                                            "nichts",
                                            "Nur wenn man "
                                            "sie sieht"],
                                           ["F1", "F1"]),
                             distractors=[])},
                        {"key": "F2", "description": "Beim "
                         "Schmelzen wird ein „neuer "
                         "Stoff“ angenommen — Eis wird "
                         "zu etwas anderem.",
                         "remediation_hint": "Eis, "
                         "Wasser und Dampf sind "
                         "dasselbe in drei Kleidern.",
                         "diagnostic_item": item(
                             "Eis schmilzt zu Wasser — "
                             "ist Wasser ein neuer "
                             "Stoff?",
                             "Nein, es ist derselbe "
                             "Stoff", level="target",
                             grade=4,
                             answer=choice(
                                 "Nein, derselbe Stoff",
                                 ["Ja, ein neuer",
                                  "Halb neu"],
                                 ["F2", "F2"]),
                             distractors=[])}],
                    "diagnostic_items": [
                        item("Nenne einen flüssigen "
                             "Stoff.", "Wasser",
                             level="below", grade=3,
                             answer=text("wasser", "milch",
                                         "saft", "öl")),
                        item("In welchem Zustand ist "
                             "Wasserdampf?",
                             "gasförmig", level="target",
                             grade=4,
                             answer=text("gasförmig",
                                         "gas"))],
                    "exit_items": [
                        item("Ordne zu: Eis, Wasser, "
                             "Dampf — welche Zustände?",
                             "fest, flüssig, gasförmig",
                             level="target", grade=4,
                             answer=text(
                                 "fest flüssig gasförmig",
                                 "eis fest wasser "
                                 "flüssig dampf "
                                 "gasförmig")),
                        item("Nenne eine Eigenschaft, "
                             "die Eisen von Holz "
                             "unterscheidet.",
                             "Eisen ist hart und "
                             "kalt/leitend", level="target",
                             grade=4,
                             answer=text("hart", "kalt",
                                         "leitet",
                                         "schwer",
                                         "glänzend"))]},
                "lektion": {
                    "konzept": {
                        "konzept_key": "begriff",
                        "thema_key": "stoffe",
                        "label": "Stoffe und ihre "
                                 "Zustände",
                        "klasse_von": 3, "klasse_bis": 5,
                        "stichworte": ["stoff",
                                       "aggregatzustand",
                                       "fest flüssig "
                                       "gasförmig",
                                       "was ist ein stoff"]},
                    "erstkontakt": {
                        "anker": "Eis, Wasser, Dampf — "
                                 "drei Dinge oder "
                                 "einer in drei "
                                 "Kleidern?",
                        "benennung": "Stoff",
                        "erste_aufgabe": {"frage": "In "
                                          "welchem "
                                          "Zustand "
                                          "ist Eis?",
                                          "loesung":
                                          "fest"}},
                    "fehlertypen": [
                        {
                            "key": "unsichtbar_ist_nichts",
                            "label": "Unsichtbar heißt "
                                     "nichts",
                            "beschreibung": "Luft und "
                            "Dampf gelten als leer — "
                            "was man nicht sieht, kann "
                            "kein Stoff sein.",
                            "antworten": ["nein", "luft "
                                          "ist nichts",
                                          "nichts"],
                            "erklaerung": {
                                "haken": "Pust in einen "
                                        "Ballon — er "
                                        "wird dick. "
                                        "Was ist da "
                                        "drin, wenn "
                                        "„nichts“ "
                                        "reinkommt?",
                                "erkenntnis": "Die Luft "
                                "füllt den Ballon und "
                                "drückt ihn auseinander "
                                "— sie nimmt Platz ein, "
                                "sie wiegt sogar etwas. "
                                "Unsichtbar, aber "
                                "wirklich da.",
                                "regel": "Ein Stoff "
                                "braucht Platz und hat "
                                "Masse — auch wenn er "
                                "unsichtbar ist. Luft "
                                "ist ein gasförmiger "
                                "Stoff.",
                                "bild": {"zeigt": "ein "
                                         "aufgeblasener "
                                         "Ballon neben "
                                         "einem "
                                         "leeren",
                                         "bewegt": "die "
                                         "unsichtbare "
                                         "Luft füllt "
                                         "den Raum "
                                         "im Ballon",
                                         "bleibt_gleich":
                                         "der Ballon "
                                         "bleibt "
                                         "derselbe"},
                                "aufgabe": {"frage":
                                            "Ist Luft "
                                            "ein "
                                            "Stoff?",
                                            "loesung":
                                            "Ja"}},
                            "visualisierung": _NETZ(
                                ["Stoff", "fest",
                                 "flüssig", "gasförmig",
                                 "Luft"],
                                ["Stoff → fest: Eis",
                                 "Stoff → flüssig: "
                                 "Wasser",
                                 "Stoff → gasförmig: "
                                 "Luft"]),
                            "visualisierung_alternativ":
                            _TABELLE(
                                ["Zustand",
                                 "Beispiel",
                                 "sichtbar?"],
                                ["fest | Stein | ja",
                                 "flüssig | "
                                 "Wasser | ja",
                                 "gasförmig | "
                                 "Luft | nein"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Ist Luft ein "
                                    "Stoff?",
                                    "Ja — sie ist "
                                    "gasförmig",
                                    ["Nein, sie ist "
                                     "nichts",
                                     "Nur atmen "
                                     "macht sie "
                                     "real"],
                                    "Sie füllt den "
                                    "Ballon und "
                                    "drückt — ein "
                                    "echter "
                                    "Stoff."),
                                "beispiel": aufgabe(
                                    "Ein aufge-"
                                    "blasener Ballon "
                                    "ist schwerer "
                                    "als ein "
                                    "leerer — die "
                                    "Luft wiegt "
                                    "etwas.",
                                    "Luft ist ein "
                                    "Stoff."),
                                "gefuehrt": aufgabe(
                                    "Warum weißt "
                                    "du, dass Luft "
                                    "ein Stoff "
                                    "ist? Antworte "
                                    "in einem "
                                    "Satz.",
                                    "Weil sie "
                                    "Platz "
                                    "einnimmt "
                                    "und Masse "
                                    "hat.",
                                    fehler="weil man "
                                           "sie "
                                           "atmet",
                                    art="begriffe",
                                    rubrik={
                                        "begriffe": [
                                            "platz",
                                            "masse",
                                            "gewicht",
                                            "drückt",
                                            "ballon"],
                                        "mindestens": 1,
                                        "hinweise": {
                                            "teilweise":
                                                "Atmen "
                                                "zeigt "
                                                "es — "
                                                "aber "
                                                "was "
                                                "macht "
                                                "sie "
                                                "zum "
                                                "Stoff?"}},
                                    tipps=["Was tut "
                                           "die Luft "
                                           "im "
                                           "Ballon?"]),
                                "selbststaendig": aufgabe(
                                    "Erkläre in "
                                    "einem Satz, "
                                    "warum "
                                    "Wasserdampf "
                                    "ein Stoff "
                                    "ist.",
                                    "Er nimmt "
                                    "Platz ein "
                                    "und hat "
                                    "Masse — "
                                    "wie jeder "
                                    "Stoff.",
                                    fehler="weil er "
                                           "aus "
                                           "wasser "
                                           "ist",
                                    art="begriffe",
                                    rubrik={
                                        "begriffe": [
                                            "platz",
                                            "masse",
                                            "stoff",
                                            "gas"],
                                        "mindestens": 2,
                                        "hinweise": {
                                            "teilweise":
                                                "Woher "
                                                "er "
                                                "kommt, "
                                                "weißt "
                                                "du — "
                                                "was "
                                                "macht "
                                                "ihn "
                                                "zum "
                                                "Stoff?"}},
                                    tipps=["Was "
                                           "macht "
                                           "einen "
                                           "Stoff "
                                           "zum "
                                           "Stoff?"]),
                                "transfer": auswahl(
                                    "Warum zeigt "
                                    "der "
                                    "Ballontrick "
                                    "mehr als "
                                    "das "
                                    "Atmen?",
                                    "Der Ballon "
                                    "zeigt Platz "
                                    "und Druck — "
                                    "messbare "
                                    "Stoff-"
                                    "eigenschaften",
                                    ["Er ist "
                                     "bunter",
                                     "Atmen "
                                     "zählt "
                                     "nicht"],
                                    "Ein Stoff "
                                    "beweist "
                                    "sich über "
                                    "seine "
                                    "Eigenschaften "
                                    "— nicht "
                                    "über "
                                    "Gefühle.")}},
                        {
                            "key": "schmelzen_ist_neu",
                            "label": "Schmelzen macht "
                                     "einen neuen Stoff",
                            "beschreibung": "Eis wird "
                            "zu „etwas anderem“ — der "
                            "Zustandswechsel wird "
                            "für eine Umwandlung "
                            "gehalten.",
                            "antworten": ["ja",
                                          "neuer stoff",
                                          "es wird "
                                          "neu"],
                            "erklaerung": {
                                "haken": "Eis schmilzt "
                                        "zu Wasser — "
                                        "ist das ein "
                                        "neuer "
                                        "Stoff? "
                                        "Dann "
                                        "müsste er "
                                        "nicht "
                                        "wieder "
                                        "gefrieren "
                                        "können.",
                                "erkenntnis": "Eis, "
                                "Wasser und Dampf "
                                "sind derselbe "
                                "Stoff in drei "
                                "Zuständen. Nur "
                                "die "
                                "Anordnung "
                                "ändert sich — "
                                "nicht der "
                                "Stoff.",
                                "regel": "Ein "
                                "Zustandswechsel "
                                "macht keinen "
                                "neuen Stoff: "
                                "schmelzen, "
                                "gefrieren, "
                                "verdampfen "
                                "sind "
                                "umkehrbar.",
                                "bild": {"zeigt": "Eis, "
                                         "Wasser und "
                                         "Dampf mit "
                                         "Pfeilen "
                                         "hin und "
                                         "zurück",
                                         "bewegt": "der "
                                         "Stoff "
                                         "wechselt "
                                         "die "
                                         "Zustände "
                                         "hin und "
                                         "her",
                                         "bleibt_gleich":
                                         "der Stoff "
                                         "bleibt "
                                         "Wasser"},
                                "aufgabe": {"frage":
                                            "Dampf "
                                            "wird "
                                            "wieder "
                                            "zu "
                                            "Wasser "
                                            "— "
                                            "neuer "
                                            "Stoff?",
                                            "loesung":
                                            "Nein"}},
                            "visualisierung": _FLUSS(
                                ["Eis (fest)",
                                 "schmelzen → "
                                 "Wasser (flüssig)",
                                 "verdampfen → "
                                 "Dampf "
                                 "(gasförmig)",
                                 "alles "
                                 "derselbe Stoff"]),
                            "visualisierung_alternativ":
                            _TABELLE(
                                ["Zustand",
                                 "Name",
                                 "Stoff"],
                                ["fest | Eis | "
                                 "Wasser",
                                 "flüssig | "
                                 "Wasser | Wasser",
                                 "gasförmig | "
                                 "Dampf | Wasser"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Eis schmilzt "
                                    "zu Wasser — "
                                    "ist Wasser "
                                    "ein neuer "
                                    "Stoff?",
                                    "Nein, es ist "
                                    "derselbe "
                                    "Stoff",
                                    ["Ja, ein "
                                     "neuer",
                                     "Zur "
                                     "Hälfte"],
                                    "Schmelzen "
                                    "wechselt "
                                    "nur den "
                                    "Zustand — "
                                    "nicht den "
                                    "Stoff."),
                                "beispiel": aufgabe(
                                    "Wasser kann "
                                    "gefrieren "
                                    "und wieder "
                                    "schmelzen — "
                                    "hin und "
                                    "her. Ein "
                                    "neuer "
                                    "Stoff wäre "
                                    "nicht "
                                    "umkehrbar.",
                                    "Derselbe "
                                    "Stoff."),
                                "gefuehrt": aufgabe(
                                    "Kerzenwachs "
                                    "schmilzt — "
                                    "ist das "
                                    "flüssige "
                                    "Wachs ein "
                                    "neuer "
                                    "Stoff? "
                                    "(ja/nein)",
                                    "nein",
                                    fehler="ja",
                                    art="text",
                                    tipps=["Kann "
                                           "es "
                                           "wieder "
                                           "fest "
                                           "werden?"]),
                                "selbststaendig": aufgabe(
                                    "Butter "
                                    "schmilzt "
                                    "in der "
                                    "Pfanne — "
                                    "neuer "
                                    "Stoff? "
                                    "(ja/nein)",
                                    "nein",
                                    fehler="ja",
                                    art="text",
                                    tipps=["Umkehrbar "
                                           "oder "
                                           "nicht?"]),
                                "transfer": auswahl(
                                    "Warum ist "
                                    "„verbranntes "
                                    "Holz“ anders "
                                    "als "
                                    "„geschmolzenes "
                                    "Eis“?",
                                    "Verbrennen "
                                    "macht neue "
                                    "Stoffe — "
                                    "Schmelzen "
                                    "nur einen "
                                    "neuen "
                                    "Zustand",
                                    ["Es ist "
                                     "heißer",
                                     "Holz ist "
                                     "fester"],
                                    "Der "
                                    "Unterschied: "
                                    "umkehrbar "
                                    "oder neue "
                                    "Stoffe.")}},
                    ],
                    "hilfe": _hilfe({
                        "HOOK": "Ein Stoff nimmt Platz "
                                "ein und hat Masse — "
                                "auch unsichtbar.",
                        "RULE": "Fest, flüssig, "
                                "gasförmig sind "
                                "Zustände eines "
                                "Stoffs — kein "
                                "Wechsel macht "
                                "einen neuen.",
                        "WORKED_EXAMPLE": "Eis → "
                                "Wasser → Dampf: "
                                "derselbe Stoff, "
                                "drei Kleider.",
                        "GUIDED_TASK": "Frag: nimmt es "
                                "Platz ein? Hat es "
                                "Masse?",
                        "INDEPENDENT_TASK": "Umkehrbar "
                                "= Zustandswechsel. "
                                "Nicht umkehrbar = "
                                "neue Stoffe.",
                        "ADAPTATION": "Die Tabelle "
                                "vergleicht die "
                                "drei Zustände."}),
                    "faq": [
                        {"frage": "Ist Luft ein "
                                  "Stoff?",
                         "antwort": "Ja — ein "
                                    "gasförmiger. "
                                    "Er füllt "
                                    "Platz und "
                                    "hat Masse, "
                                    "nur sieht "
                                    "man ihn "
                                    "nicht."},
                        {"frage": "Wird aus Eis ein "
                                  "neuer Stoff, "
                                  "wenn es "
                                  "schmilzt?",
                         "antwort": "Nein — Eis, "
                                    "Wasser und "
                                    "Dampf sind "
                                    "derselbe "
                                    "Stoff in "
                                    "drei "
                                    "Zuständen."}],
                }},
            # --------------------------------------- Teilchen
            {
                "id": "CH.TEILCHEN.MODELL",
                "title": "Das Teilchenmodell",
                "description": "Stoffe bestehen aus "
                               "winzigen Teilchen — die "
                               "Vorstellung, die alles "
                               "weitere trägt.",
                "first_contact_grade": 5, "target_grade": 6,
                "prerequisites": ["CH.STOFFE.BEGRIFF"],
                "levels": {
                    "below": "K4: Stoffe und Zustände",
                    "target": "K6: Stoffe als Ansammlung "
                              "kleinster Teilchen "
                              "verstehen",
                    "above": "K7: Teilchen-Umbau bei "
                             "Reaktionen"},
                "can_do": {
                    "below": ["Stoffe und Zustände "
                              "nennen"],
                    "target": ["erklären, dass Stoffe "
                               "aus winzigen Teilchen "
                               "bestehen und Zustände "
                               "als Teilchen-Anordnung "
                               "deuten"],
                    "above": ["chemische Reaktionen als "
                              "Teilchen-Umbau "
                              "beschreiben"]},
                "difficulty_parameters": {
                    "bild": "Teilchen als Kügelchen",
                    "zustaende": "fest = eng geordnet, "
                                 "flüssig = beweglich, "
                                 "gas = frei"},
                "anchor_items": [
                    item("Woraus besteht Wasser im "
                         "Kleinsten?",
                         "Aus Wasserteilchen",
                         level="target", grade=6,
                         answer=text("teilchen",
                                     "wasserteilchen",
                                     "moleküle",
                                     "molekülen")),
                    item("Wie liegen die Teilchen in "
                         "Eis?", "Eng und geordnet",
                         level="target", grade=6,
                         answer=text("eng", "geordnet",
                                     "eng und geordnet",
                                     "fest"))],
                "boundary_items": {
                    "below": [item("In welchem Zustand "
                                   "ist Eis?", "fest",
                                   level="below",
                                   grade=4,
                                   answer=text("fest"))],
                    "within": [item("Wie bewegen sich "
                                    "Teilchen in "
                                    "Gas?",
                                    "Frei und schnell",
                                    level="target",
                                    grade=6,
                                    answer=text("frei",
                                                "frei und "
                                                "schnell",
                                                "schnell"))],
                    "above": [item("Was passiert mit "
                                   "den Teilchen bei "
                                   "einer Reaktion?",
                                   "Sie werden neu "
                                   "angeordnet",
                                   level="above",
                                   grade=7,
                                   answer=text(
                                       "neu angeordnet",
                                       "umgebaut",
                                       "neu "
                                       "zusammengesetzt"))]},
                "diagnostics": {
                    "misconceptions": [
                        {"key": "F1", "description": "Die "
                         "Teilchen selbst schmelzen — "
                         "das Teilchen wird zum "
                         "Mini-Eisstück, das weich "
                         "wird.",
                         "remediation_hint": "Die "
                         "Teilchen bleiben hart — "
                         "nur ihre Anordnung "
                         "lockert sich.",
                         "diagnostic_item": item(
                             "Was passiert beim "
                             "Schmelzen mit den "
                             "Teilchen?",
                             "Sie bleiben gleich, "
                             "nur ihre Anordnung "
                             "lockert sich",
                             level="target", grade=6,
                             answer=choice(
                                 "Anordnung "
                                 "lockert sich",
                                 ["Die Teilchen "
                                  "schmelzen",
                                  "Sie werden "
                                  "weicher"],
                                 ["F1", "F1"]),
                             distractors=[])},
                        {"key": "F2", "description": "Beim "
                         "Verdampfen verschwinden "
                         "die Teilchen — „weg ist "
                         "weg“.",
                         "remediation_hint": "Ver-"
                         "dampftes Wasser ist in der "
                         "Luft — die Teilchen sind "
                         "nur weiter weg.",
                         "diagnostic_item": item(
                             "Wasser verdampft — "
                             "wo sind die "
                             "Teilchen?",
                             "In der Luft, frei "
                             "beweglich",
                             level="target", grade=6,
                             answer=choice(
                                 "In der Luft",
                                 ["Sie sind weg",
                                  "Sie wurden "
                                  "Luft"],
                                 ["F2", "F2"]),
                             distractors=[])}],
                    "diagnostic_items": [
                        item("Welcher Zustand: die "
                             "Teilchen liegen eng "
                             "und geordnet?",
                             "fest", level="below",
                             grade=5,
                             answer=text("fest")),
                        item("Wie liegen Teilchen in "
                             "einer Flüssigkeit?",
                             "Nahe, aber beweglich",
                             level="target", grade=6,
                             answer=text("beweglich",
                                         "nahe "
                                         "beweglich",
                                         "nahe, aber "
                                         "beweglich"))],
                    "exit_items": [
                        item("Zeichne/erkläre: "
                             "Teilchen in fest, "
                             "flüssig, gas",
                             "fest eng geordnet, "
                             "flüssig beweglich, "
                             "gas frei",
                             level="target", grade=6,
                             answer=text(
                                 "fest geordnet "
                                 "flüssig beweglich "
                                 "gas frei")),
                        item("Was ändert sich beim "
                             "Schmelzen: die "
                             "Teilchen oder ihre "
                             "Anordnung?",
                             "Die Anordnung",
                             level="target", grade=6,
                             answer=text("anordnung",
                                         "die "
                                         "anordnung"))]},
                "lektion": {
                    "konzept": {
                        "konzept_key": "modell",
                        "thema_key": "teilchen",
                        "label": "Das Teilchenmodell",
                        "klasse_von": 5, "klasse_bis": 7,
                        "stichworte": ["teilchenmodell",
                                       "teilchen",
                                       "kleinste "
                                       "teilchen",
                                       "stoffe "
                                       "teilchen"]},
                    "erstkontakt": {
                        "anker": "Zerschneide einen "
                                 "Apfel immer "
                                 "weiter — wo "
                                 "hört es auf, "
                                 "Apfel zu sein?",
                        "benennung": "Teilchen",
                        "erste_aufgabe": {"frage":
                                          "Woraus "
                                          "besteht "
                                          "Wasser "
                                          "im "
                                          "Kleinsten?",
                                          "loesung":
                                          "Aus "
                                          "Wasser-"
                                          "teilchen"}},
                    "fehlertypen": [
                        {
                            "key": "teilchen_schmelzen",
                            "label": "Die Teilchen "
                                     "schmelzen mit",
                            "beschreibung": "Das "
                            "Teilchen wird zum "
                            "Miniatur-Eis, das "
                            "weich wird — die "
                            "Anordnung wird "
                            "übersehen.",
                            "antworten": ["sie "
                                          "schmelzen",
                                          "werden "
                                          "weich",
                                          "verlieren "
                                          "form"],
                            "erklaerung": {
                                "haken": "Wenn Eis "
                                        "schmilzt, "
                                        "was schmilzt "
                                        "dann wirk-"
                                        "lich — die "
                                        "Teilchen "
                                        "oder ihre "
                                        "Ordnung?",
                                "erkenntnis": "Die "
                                "Teilchen sind "
                                "winzig und "
                                "unveränderlich. "
                                "Was sich ändert, "
                                "ist nur ihr "
                                "Abstand: eng "
                                "geordnet in Eis, "
                                "beweglich in "
                                "Wasser.",
                                "regel": "Zustands-"
                                "wechsel ändern "
                                "die Anordnung, "
                                "nicht die "
                                "Teilchen. Fest "
                                "= eng und "
                                "geordnet, "
                                "flüssig = nah "
                                "und beweglich, "
                                "gas = frei.",
                                "bild": {"zeigt":
                                         "dieselben "
                                         "Kügelchen "
                                         "einmal "
                                         "in "
                                         "Reihen, "
                                         "einmal "
                                         "durchein-"
                                         "ander",
                                         "bewegt": "die "
                                         "Kügelchen "
                                         "lockern "
                                         "ihre "
                                         "Reihen",
                                         "bleibt_gleich":
                                         "die "
                                         "Kügelchen "
                                         "bleiben "
                                         "identisch"},
                                "aufgabe": {"frage":
                                            "Was "
                                            "ändert "
                                            "sich "
                                            "beim "
                                            "Verdampfen?",
                                            "loesung":
                                            "Nur "
                                            "die "
                                            "Anordnung "
                                            "— "
                                            "die "
                                            "Teilchen "
                                            "bleiben"}},
                            "visualisierung": _TABELLE(
                                ["Zustand",
                                 "Anordnung"],
                                ["fest | eng, "
                                 "geordnet",
                                 "flüssig | nah, "
                                 "beweglich",
                                 "gas | frei, "
                                 "weit"]),
                            "visualisierung_alternativ":
                            _FLUSS(
                                ["Eis: Kügelchen "
                                 "in Reihen",
                                 "Wärme: Reihen "
                                 "lockern sich",
                                 "Wasser: "
                                 "Kügelchen "
                                 "beweglich",
                                 "gleiche "
                                 "Kügelchen"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Was passiert "
                                    "beim "
                                    "Schmelzen "
                                    "mit den "
                                    "Teilchen?",
                                    "Nur ihre "
                                    "Anordnung "
                                    "lockert "
                                    "sich",
                                    ["Sie "
                                     "schmelzen",
                                     "Sie "
                                     "werden "
                                     "weicher"],
                                    "Die "
                                    "Kügelchen "
                                    "bleiben "
                                    "hart — die "
                                    "Reihen "
                                    "lockern "
                                    "sich."),
                                "beispiel": aufgabe(
                                    "Wie Menschen "
                                    "in einer "
                                    "Schlange: "
                                    "fest = "
                                    "stramm "
                                    "stehen, "
                                    "flüssig = "
                                    "eng "
                                    "wuselig, "
                                    "gas = "
                                    "weit "
                                    "verteilt.",
                                    "Die "
                                    "Anordnung "
                                    "ändert "
                                    "sich."),
                                "gefuehrt": aufgabe(
                                    "Wie liegen "
                                    "Teilchen "
                                    "im "
                                    "festen "
                                    "Zustand?",
                                    "Eng und "
                                    "geordnet",
                                    fehler="sie "
                                           "sind "
                                           "fest "
                                           "und "
                                           "hart",
                                    art="begriffe",
                                    rubrik=begriffe(
                                        ("eng", "dicht", "fest"),
                                        "geordnet"),
                                    tipps=["Es "
                                           "geht "
                                           "um "
                                           "die "
                                           "Anordnung "
                                           "— "
                                           "nicht "
                                           "die "
                                           "Teilchen."]),
                                "selbststaendig": aufgabe(
                                    "Was ändert "
                                    "sich beim "
                                    "Verdampfen: "
                                    "Teilchen "
                                    "oder "
                                    "Anordnung?",
                                    "Die "
                                    "Anordnung",
                                    fehler="die "
                                           "teilchen",
                                    art="begriffe",
                                    rubrik=begriffe("anordnung"),
                                    tipps=["Die "
                                           "Teilchen "
                                           "sind "
                                           "immer "
                                           "dieselben."]),
                                "transfer": auswahl(
                                    "Warum kann "
                                    "man "
                                    "Dampf "
                                    "wieder "
                                    "zu "
                                    "Wasser "
                                    "machen?",
                                    "Die "
                                    "Teilchen "
                                    "sind "
                                    "gleich "
                                    "geblieben "
                                    "— nur "
                                    "engen "
                                    "sie sich "
                                    "wieder "
                                    "an",
                                    ["Dampf ist "
                                     "schwer",
                                     "Wasser "
                                     "kühlt "
                                     "ab"],
                                    "Der Stoff "
                                    "blieb — "
                                    "nur die "
                                    "Ordnung "
                                    "kehrt "
                                    "zurück.")}},
                    ],
                    "hilfe": _hilfe({
                        "HOOK": "Stoffe sind wie "
                                "Menschenmengen: "
                                "dieselben "
                                "Leute, "
                                "verschiedene "
                                "Ordnung.",
                        "RULE": "Fest = eng "
                                "geordnet, "
                                "flüssig = "
                                "beweglich, "
                                "gas = frei. "
                                "Die Teilchen "
                                "bleiben "
                                "immer "
                                "dieselben.",
                        "WORKED_EXAMPLE": "Denk an "
                                "die Schlange: "
                                "stramm stehen "
                                "= fest, "
                                "wuseln = "
                                "flüssig, "
                                "verteilen = "
                                "gas.",
                        "GUIDED_TASK": "Frag nicht "
                                "„was wird aus "
                                "dem "
                                "Teilchen“ — "
                                "frag „wie "
                                "stehen "
                                "sie?“.",
                        "INDEPENDENT_TASK": "Zustands-"
                                "wechsel = "
                                "Anordnung. "
                                "Reaktion = "
                                "Umbau. "
                                "Unter-"
                                "scheide "
                                "beides.",
                        "ADAPTATION": "Die "
                                "Tabelle "
                                "ordnet "
                                "Zustand "
                                "und "
                                "Anordnung."}),
                    "faq": [
                        {"frage": "Schmelzen die "
                                  "Teilchen "
                                  "beim "
                                  "Schmelzen?",
                         "antwort": "Nein — die "
                                    "Teilchen "
                                    "bleiben "
                                    "gleich. "
                                    "Nur ihre "
                                    "Anord-"
                                    "nung "
                                    "lockert "
                                    "sich."},
                        {"frage": "Wohin gehen "
                                  "die "
                                  "Teilchen "
                                  "beim "
                                  "Verdampfen?",
                         "antwort": "In die "
                                    "Luft — "
                                    "sie "
                                    "werden "
                                    "frei und "
                                    "verteilen "
                                    "sich, "
                                    "ver-"
                                    "schwinden "
                                    "aber "
                                    "nicht."}],
                }},
            # -------------------------------------- Reaktion
            {
                "id": "CH.REAKTION.BEGRIFF",
                "title": "Chemische Reaktion — neue "
                         "Stoffe entstehen",
                "description": "Edukte werden zu "
                               "Produkten: die "
                               "Teilchen setzen sich "
                               "neu zusammen und "
                               "ein neuer Stoff "
                               "entsteht.",
                "first_contact_grade": 7, "target_grade": 8,
                "prerequisites": ["CH.TEILCHEN.MODELL"],
                "levels": {
                    "below": "K5–6: Teilchenmodell",
                    "target": "K7–8: Reaktion als "
                              "Teilchen-Umbau von "
                              "Edukten zu Produkten",
                    "above": "K8–9: Reaktions-"
                             "gleichungen und "
                             "Energie"},
                "can_do": {
                    "below": ["Zustände als "
                              "Anordnung deuten"],
                    "target": ["eine Reaktion als "
                               "Umbau von Edukten zu "
                               "Produkten beschreiben "
                               "und von einem "
                               "Zustandswechsel "
                               "unterscheiden"],
                    "above": ["Massenerhaltung in "
                              "Reaktionen anwenden"]},
                "difficulty_parameters": {
                    "begriffe": "Edukt, Produkt",
                    "beispiele": "Verbrennen, Rosten, "
                                 "Wasserstoff + "
                                 "Sauerstoff"},
                "anchor_items": [
                    item("Was entsteht bei einer "
                         "chemischen Reaktion?",
                         "Ein neuer Stoff",
                         level="target", grade=8,
                         answer=text("neuer stoff",
                                     "ein neuer stoff",
                                     "produkt",
                                     "produkte")),
                    item("Eisen rostet — ist das eine "
                         "Reaktion?",
                         "Ja, es entsteht ein neuer "
                         "Stoff (Rost)",
                         level="target", grade=8,
                         answer=text("ja",
                                     "ja neue stoffe",
                                     "ja rost"))],
                "boundary_items": {
                    "below": [item("Woraus besteht "
                                   "Wasser im "
                                   "Kleinsten?",
                                   "Aus Teilchen",
                                   level="below",
                                   grade=6,
                                   answer=text(
                                       "teilchen",
                                       "moleküle"))],
                    "within": [item("Wie heißt der "
                                    "Stoff vor der "
                                    "Reaktion?",
                                    "Edukt",
                                    level="target",
                                    grade=8,
                                    answer=text(
                                        "edukt"))],
                    "above": [item("Holz verbrennt "
                                   "mit 10 g — "
                                   "wie viel "
                                   "Masse haben "
                                   "die Produkte "
                                   "insgesamt "
                                   "(mit Luft)?",
                                   "10 g + die "
                                   "Luftmasse",
                                   level="above",
                                   grade=8,
                                   answer=text(
                                       "gleich",
                                       "die gleiche "
                                       "masse",
                                       "10 g plus "
                                       "luft"))]},
                "diagnostics": {
                    "misconceptions": [
                        {"key": "F1", "description": "Jede "
                         "Veränderung wird zur "
                         "Reaktion — Schmelzen und "
                         "Zerschneiden zählen mit.",
                         "remediation_hint": "Der "
                         "Test: entsteht ein "
                         "neuer Stoff? "
                         "Zustandswechsel sind "
                         "umkehrbar, Reaktionen "
                         "nicht.",
                         "diagnostic_item": item(
                             "Eis schmilzt — "
                             "chemische "
                             "Reaktion?",
                             "Nein, nur ein "
                             "Zustandswechsel",
                             level="target",
                             grade=8,
                             answer=choice(
                                 "Nein, "
                                 "Zustandswechsel",
                                 ["Ja, eine "
                                  "Reaktion",
                                  "Halbe "
                                  "Reaktion"],
                                 ["F1", "F1"]),
                             distractors=[])},
                        {"key": "F2", "description": "Beim "
                         "Verbrennen „verschwindet“ "
                         "der Stoff — das Holz "
                         "wird zu Nichts plus "
                         "Rauch.",
                         "remediation_hint": "Alles "
                         "bleibt: die Produkte "
                         "(Asche, Gase) wiegen "
                         "zusammen so viel wie "
                         "Edukte + Luft.",
                         "diagnostic_item": item(
                             "Holz verbrennt — "
                             "wohin geht die "
                             "Masse?",
                             "Sie bleibt in "
                             "Asche und "
                             "Gasen erhalten",
                             level="target",
                             grade=8,
                             answer=choice(
                                 "In Asche und "
                                 "Gasen",
                                 ["Sie "
                                  "verschwindet",
                                  "Sie wird "
                                  "Wärme"],
                                 ["F2", "F2"]),
                             distractors=[])},
                        {"key": "F3", "description": "Edukt "
                         "und Produkt werden "
                         "verwechselt — die "
                         "Richtung des Pfeils "
                         "läuft falsch herum.",
                         "remediation_hint": "Der "
                         "Pfeil zeigt die "
                         "Richtung des Umbaus: "
                         "links was reinkommt, "
                         "rechts was "
                         "rauskommt.",
                         "diagnostic_item": item(
                             "In „Wasserstoff + "
                             "Sauerstoff → "
                             "Wasser“ — was "
                             "ist das "
                             "Produkt?",
                             "Wasser",
                             level="target",
                             grade=8,
                             answer=choice(
                                 "Wasser",
                                 ["Wasserstoff",
                                  "Sauerstoff"],
                                 ["F3", "F3"]),
                             distractors=[])}],
                    "diagnostic_items": [
                        item("Was ist ein Teilchen?",
                             "Der kleinste "
                             "Baustein eines "
                             "Stoffs",
                             level="below", grade=6,
                             answer=text("baustein",
                                         "kleinster "
                                         "baustein",
                                         "winziges "
                                         "teil")),
                        item("Neuer Stoff entsteht "
                             "— wie heißt das?",
                             "Chemische Reaktion",
                             level="target",
                             grade=8,
                             answer=text(
                                 "chemische "
                                 "reaktion",
                                 "reaktion"))],
                    "exit_items": [
                        item("Ordne: „Eisen + "
                             "Sauerstoff → Rost“ "
                             "— Edukte und "
                             "Produkt?",
                             "Eisen und "
                             "Sauerstoff sind "
                             "Edukte, Rost ist "
                             "das Produkt",
                             level="target",
                             grade=8,
                             answer=text(
                                 "eisen "
                                 "sauerstoff "
                                 "edukte rost "
                                 "produkt")),
                        item("Schmelzen oder "
                             "Reaktion: Butter "
                             "in der Pfanne vs. "
                             "Holz im Feuer?",
                             "Schmelzen / "
                             "Reaktion",
                             level="target",
                             grade=8,
                             answer=text(
                                 "schmelzen "
                                 "reaktion",
                                 "butter "
                                 "schmelzen "
                                 "holz "
                                 "reaktion"))]},
                "lektion": {
                    "konzept": {
                        "konzept_key": "begriff",
                        "thema_key": "reaktion",
                        "label": "Chemische "
                                 "Reaktion",
                        "klasse_von": 7, "klasse_bis": 9,
                        "stichworte": ["chemische "
                                       "reaktion",
                                       "edukt",
                                       "produkt",
                                       "reaktion "
                                       "chemie",
                                       "neue stoffe"]},
                    "erstkontakt": {
                        "anker": "Holz verbrennt zu "
                                 "Asche und Rauch — "
                                 "ist die Asche "
                                 "noch Holz, nur "
                                 "heiß?",
                        "benennung": "Reaktion",
                        "erste_aufgabe": {"frage":
                                          "Was "
                                          "entsteht "
                                          "bei "
                                          "einer "
                                          "Reaktion?",
                                          "loesung":
                                          "Ein "
                                          "neuer "
                                          "Stoff"}},
                    "fehlertypen": [
                        {
                            "key": "alles_ist_reaktion",
                            "label": "Jede "
                                     "Veränderung "
                                     "zählt als "
                                     "Reaktion",
                            "beschreibung": "Schmelzen, "
                            "Zerschneiden, "
                            "Auflösen — alles wird "
                            "zur chemischen "
                            "Reaktion "
                            "erklärt.",
                            "antworten": ["ja",
                                          "schmelzen "
                                          "ist eine",
                                          "ja reaktion"],
                            "erklaerung": {
                                "haken": "Eis "
                                        "schmilzt, "
                                        "Holz "
                                        "brennt — "
                                        "beides "
                                        "ändert "
                                        "sich. Ist "
                                        "beides "
                                        "eine "
                                        "Reaktion?",
                                "erkenntnis": "Der "
                                "Test: entsteht "
                                "ein NEUER "
                                "Stoff? Eis→"
                                "Wasser ist "
                                "umkehrbar — "
                                "gleicher "
                                "Stoff. Holz→"
                                "Asche "
                                "nicht — "
                                "neuer "
                                "Stoff.",
                                "regel": "Chemische "
                                "Reaktion = "
                                "neue Stoffe "
                                "entstehen "
                                "(Edukte → "
                                "Produkte). "
                                "Zustands-"
                                "wechsel = "
                                "gleicher "
                                "Stoff, neue "
                                "Form.",
                                "bild": {"zeigt": "zwei "
                                         "Wege: "
                                         "Eis↔Wasser "
                                         "mit "
                                         "Rück-"
                                         "pfeil, "
                                         "Holz→"
                                         "Asche "
                                         "ohne",
                                         "bewegt": "der "
                                         "Rückpfeil "
                                         "zeigt "
                                         "die "
                                         "umkehr-"
                                         "bare "
                                         "Richtung",
                                         "bleibt_gleich":
                                         "der "
                                         "Stoff-"
                                         "Name "
                                         "bleibt "
                                         "die "
                                         "Probe"},
                                "aufgabe": {"frage":
                                            "Ist "
                                            "Zerkleinern "
                                            "eine "
                                            "Reaktion?",
                                            "loesung":
                                            "Nein"}},
                            "visualisierung": _FLUSS(
                                ["Veränderung "
                                 "passiert",
                                 "Frage: entsteht "
                                 "ein neuer "
                                 "Stoff?",
                                 "ja → Reaktion, "
                                 "nein → Zustand/"
                                 "Form"]),
                            "visualisierung_alternativ":
                            _TABELLE(
                                ["Vorgang", "neuer "
                                 "Stoff?", "Art"],
                                ["Eis schmilzt | "
                                 "nein | "
                                 "Zustandswechsel",
                                 "Holz brennt | "
                                 "ja | Reaktion",
                                 "Apfel "
                                 "zerschnitten | "
                                 "nein | "
                                 "Formänderung"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Eis "
                                    "schmilzt — "
                                    "chemische "
                                    "Reaktion?",
                                    "Nein, ein "
                                    "Zustands-"
                                    "wechsel",
                                    ["Ja, eine "
                                     "Reaktion",
                                     "Beides"],
                                    "Der Stoff "
                                    "bleibt "
                                    "Wasser — "
                                    "nur der "
                                    "Zustand "
                                    "wechselt."),
                                "beispiel": aufgabe(
                                    "Holz→Asche "
                                    "ist nicht "
                                    "umkehrbar — "
                                    "ein neuer "
                                    "Stoff "
                                    "entstand. "
                                    "Reaktion.",
                                    "Reaktion"),
                                "gefuehrt": aufgabe(
                                    "Zucker "
                                    "löst sich "
                                    "in Wasser "
                                    "— "
                                    "Reaktion? "
                                    "(ja/nein)",
                                    "nein",
                                    fehler="ja",
                                    art="text",
                                    tipps=["Kannst "
                                           "du "
                                           "den "
                                           "Zucker "
                                           "zurück-"
                                           "holen? "
                                           "(Ein-"
                                           "dampfen)"]),
                                "selbststaendig": aufgabe(
                                    "Eisen "
                                    "rostet — "
                                    "Reaktion? "
                                    "(ja/nein)",
                                    "ja",
                                    fehler="nein",
                                    art="text",
                                    tipps=["Ist "
                                           "Rost "
                                           "noch "
                                           "Eisen?"]),
                                "transfer": auswahl(
                                    "Warum ist "
                                    "„neuer "
                                    "Stoff“ der "
                                    "Prüfstein?",
                                    "Nur dann "
                                    "wurden die "
                                    "Teilchen "
                                    "umgebaut — "
                                    "alles "
                                    "andere "
                                    "ist "
                                    "Ordnung "
                                    "oder "
                                    "Form",
                                    ["Es "
                                     "klingt "
                                     "wissen-"
                                     "schaftlich",
                                     "Neue "
                                     "Stoffe "
                                     "sind "
                                     "bunt"],
                                    "Die "
                                    "Definition "
                                    "trifft "
                                    "den Kern: "
                                    "Umbau der "
                                    "Teilchen.")}},
                        {
                            "key": "masse_verschwindet",
                            "label": "Verbrennen "
                                     "vernichtet "
                                     "Stoff",
                            "beschreibung": "Das Holz "
                            "„ist weg“ — Asche "
                            "plus Rauch scheinen "
                            "weniger als das "
                            "Holz zu sein.",
                            "antworten": ["weg",
                                          "verschwindet",
                                          "wird "
                                          "nichts"],
                            "erklaerung": {
                                "haken": "Ein Holz-"
                                        "scheit "
                                        "wiegt "
                                        "ein Kilo "
                                        "— die "
                                        "Asche "
                                        "nur "
                                        "Gramm. "
                                        "Wo ist "
                                        "der "
                                        "Rest?",
                                "erkenntnis": "Der "
                                "Rest ist in "
                                "der Luft: "
                                "die Gase, "
                                "die beim "
                                "Brennen "
                                "entstehen, "
                                "tragen "
                                "die feh-"
                                "lende "
                                "Masse "
                                "davon.",
                                "regel": "Bei "
                                "Reaktionen "
                                "geht "
                                "nichts "
                                "verloren: "
                                "Edukte "
                                "(inkl. Luft) "
                                "= Produkte "
                                "(inkl. "
                                "Gasen).",
                                "bild": {"zeigt": "die "
                                         "Waage "
                                         "mit "
                                         "Holz "
                                         "und "
                                         "Luft "
                                         "links, "
                                         "Asche "
                                         "und "
                                         "Gasen "
                                         "rechts",
                                         "bewegt": "die "
                                         "Gase "
                                         "steigen "
                                         "auf — "
                                         "und "
                                         "füllen "
                                         "die "
                                         "rechte "
                                         "Schale",
                                         "bleibt_gleich":
                                         "die "
                                         "Waage "
                                         "bleibt "
                                         "im "
                                         "Gleich-"
                                         "gewicht"},
                                "aufgabe": {"frage":
                                            "Wohin "
                                            "geht "
                                            "die "
                                            "Masse "
                                            "beim "
                                            "Brennen?",
                                            "loesung":
                                            "In "
                                            "Asche "
                                            "und "
                                            "Gase"}},
                            "visualisierung": _NETZ(
                                ["Holz + Luft",
                                 "Asche + Gase",
                                 "Masse"],
                                ["Holz + Luft "
                                 "→ Asche + "
                                 "Gase",
                                 "Masse → "
                                 "bleibt "
                                 "gleich"]),
                            "visualisierung_alternativ":
                            _FLUSS(
                                ["Holz wiegen",
                                 "Brennen — "
                                 "alles "
                                 "auffangen",
                                 "Asche + "
                                 "Gase "
                                 "wiegen",
                                 "Gleiche "
                                 "Masse"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Holz "
                                    "verbrennt "
                                    "— wohin "
                                    "geht "
                                    "die "
                                    "Masse?",
                                    "In "
                                    "Asche "
                                    "und "
                                    "Gase",
                                    ["Sie "
                                     "ver-"
                                     "schwindet",
                                     "Sie "
                                     "wird "
                                     "Wärme"],
                                    "Nichts "
                                    "geht "
                                    "ver-"
                                    "loren — "
                                    "die "
                                    "Gase "
                                    "tragen "
                                    "ihren "
                                    "Teil "
                                    "davon."),
                                "beispiel": aufgabe(
                                    "In einem "
                                    "geschlossenen "
                                    "Becher "
                                    "brennt "
                                    "Holz — "
                                    "die "
                                    "Waage "
                                    "bleibt "
                                    "gleich. "
                                    "Die "
                                    "Gase "
                                    "wiegen "
                                    "mit.",
                                    "Masse "
                                    "bleibt "
                                    "er-"
                                    "halten."),
                                "gefuehrt": aufgabe(
                                    "Warum "
                                    "scheint "
                                    "die "
                                    "Masse "
                                    "beim "
                                    "Brennen "
                                    "zu "
                                    "ver-"
                                    "schwinden?",
                                    "Weil "
                                    "die "
                                    "Gase "
                                    "in die "
                                    "Luft "
                                    "entweichen.",
                                    fehler="sie wird "
                                           "zerstört",
                                    art="begriffe",
                                    rubrik=begriffe(("gas", "gase"), ("entweicht", "entweichen")),
                                    tipps=["Was "
                                           "steigt "
                                           "aus "
                                           "dem "
                                           "Feuer "
                                           "auf?"]),
                                "selbststaendig": aufgabe(
                                    "Kerze "
                                    "brennt "
                                    "ab — "
                                    "wohin "
                                    "geht "
                                    "das "
                                    "Wachs?",
                                    "Es "
                                    "reagiert "
                                    "zu "
                                    "Gasen "
                                    "und "
                                    "entweicht.",
                                    fehler="es "
                                           "ver-"
                                           "schwindet",
                                    art="begriffe",
                                    rubrik=begriffe(("gas", "gasen", "gase"), ("entweicht", "entweichen")),
                                    tipps=["Was "
                                           "riechen "
                                           "wir "
                                           "beim "
                                           "Aus-"
                                           "blasen?"]),
                                "transfer": auswahl(
                                    "Warum "
                                    "beweist "
                                    "der "
                                    "geschlossene "
                                    "Becher "
                                    "die "
                                    "Erhaltung?",
                                    "Nichts "
                                    "kann "
                                    "entweichen "
                                    "— die "
                                    "Gase "
                                    "werden "
                                    "mit-"
                                    "gewogen",
                                    ["Er "
                                     "ist "
                                     "glas",
                                     "Er "
                                     "ist "
                                     "klein"],
                                    "Die "
                                    "Waage "
                                    "lügt "
                                    "nicht — "
                                    "was "
                                    "drin "
                                    "bleibt, "
                                    "zählt.")}},
                    ],
                    "hilfe": _hilfe({
                        "HOOK": "Neuer Stoff = "
                                "Reaktion. "
                                "Umkehrbar = "
                                "nur ein "
                                "Zustands-"
                                "wechsel.",
                        "RULE": "Edukte → "
                                "Produkte. "
                                "Nichts "
                                "geht "
                                "verloren — "
                                "die Gase "
                                "zählen "
                                "mit.",
                        "WORKED_EXAMPLE": "Holz → "
                                "Asche + "
                                "Gase: "
                                "neue "
                                "Stoffe, "
                                "gleiche "
                                "Masse.",
                        "GUIDED_TASK": "Frag: "
                                "entsteht "
                                "etwas "
                                "Neues — "
                                "oder nur "
                                "eine "
                                "neue "
                                "Form?",
                        "INDEPENDENT_TASK": "Der "
                                "Pfeil "
                                "zeigt "
                                "die "
                                "Richtung: "
                                "Edukte "
                                "links, "
                                "Produkte "
                                "rechts.",
                        "ADAPTATION": "Die "
                                "Tabelle "
                                "sortiert "
                                "Vorgänge "
                                "nach "
                                "ihrem "
                                "Typ."}),
                    "faq": [
                        {"frage": "Was ist der "
                                  "Unterschied "
                                  "zwischen "
                                  "Schmelzen "
                                  "und einer "
                                  "Reaktion?",
                         "antwort": "Schmelzen "
                                    "ist "
                                    "umkehrbar "
                                    "— "
                                    "derselbe "
                                    "Stoff. "
                                    "Bei einer "
                                    "Reaktion "
                                    "entsteht "
                                    "ein "
                                    "neuer "
                                    "Stoff."},
                        {"frage": "Wo sind Edukte "
                                  "und "
                                  "Produkte "
                                  "in der "
                                  "Gleichung?",
                         "antwort": "Edukte "
                                    "links "
                                    "vom "
                                    "Pfeil "
                                    "(was "
                                    "rein-"
                                    "kommt), "
                                    "Produkte "
                                    "rechts "
                                    "(was "
                                    "raus-"
                                    "kommt)."}],
                }},
            # ---------------------------------- Erhaltung
            {
                "id": "CH.REAKTION.ERHALTUNG",
                "title": "Massenerhaltung bei "
                         "Reaktionen",
                "description": "Nichts geht verloren, "
                               "nichts kommt aus "
                               "nichts — die Masse "
                               "bleibt bei jeder "
                               "Reaktion gleich.",
                "first_contact_grade": 7, "target_grade": 8,
                "prerequisites": ["CH.REAKTION.BEGRIFF"],
                "levels": {
                    "below": "K7: Reaktion als "
                             "Teilchen-Umbau",
                    "target": "K8: Massenerhaltung "
                              "anwenden und "
                              "fehlende Masse "
                              "erklären",
                    "above": "K9: Reaktions-"
                             "gleichungen "
                             "ausgleichen"},
                "can_do": {
                    "below": ["Edukte und Produkte "
                              "unterscheiden"],
                    "target": ["berechnen oder "
                               "begründen, dass die "
                               "Gesamtmasse vor und "
                               "nach der Reaktion "
                               "gleich ist"],
                    "above": ["einfache Reaktions-"
                              "gleichungen "
                              "ausgleichen"]},
                "difficulty_parameters": {
                    "prinzip": "Masse vor = Masse "
                               "nach",
                    "fallstrick": "Gase entweichen "
                                  "und scheinen "
                                  "Masse zu "
                                  "stehlen"},
                "anchor_items": [
                    item("10 g Holz verbrennen "
                         "vollständig — wie "
                         "schwer sind Asche + "
                         "Gase zusammen?",
                         "10 g + die dazugekommene "
                         "Luftmasse",
                         level="target", grade=8,
                         answer=text(
                             "gleiche masse",
                             "10 g plus luft",
                             "gleich viel")),
                    item("In einem geschlossenen "
                         "Gefäß reagieren 5 g "
                         "und 3 g — die Masse "
                         "der Produkte?",
                         "8 g", level="target",
                         grade=8,
                         answer=number("8"))],
                "boundary_items": {
                    "below": [item("Neuer Stoff "
                                   "entsteht — "
                                   "wie heißt "
                                   "das?",
                                   "Chemische "
                                   "Reaktion",
                                   level="below",
                                   grade=7,
                                   answer=text(
                                       "reaktion"))],
                    "within": [item("7 g + 2 g "
                                    "reagieren "
                                    "vollständig "
                                    "— Produkt-"
                                    "masse?",
                                    "9 g",
                                    level="target",
                                    grade=8,
                                    answer=number(
                                        "9"))],
                    "above": [item("2 H₂ + O₂ → "
                                   "2 H₂O — "
                                   "warum "
                                   "stimmt "
                                   "die "
                                   "Gleichung?",
                                   "Gleiche "
                                   "Teilchen "
                                   "auf "
                                   "beiden "
                                   "Seiten",
                                   level="above",
                                   grade=9,
                                   answer=text(
                                       "gleiche "
                                       "teilchen",
                                       "teilchen "
                                       "bleiben "
                                       "gleich",
                                       "bilanz"))]},
                "diagnostics": {
                    "misconceptions": [
                        {"key": "F1", "description": "Gase "
                         "wiegen nichts — die "
                         "entweichende Masse "
                         "wird für vernichtet "
                         "gehalten.",
                         "remediation_hint": "Der "
                         "geschlossene Becher "
                         "beweist es: dort "
                         "bleibt die Waage "
                         "exakt gleich.",
                         "diagnostic_item": item(
                             "Eine Kerze "
                             "brennt in einem "
                             "geschlossenen "
                             "Gefäß — die "
                             "Anzeige der "
                             "Waage?",
                             "Bleibt gleich",
                             level="target",
                             grade=8,
                             answer=choice(
                                 "Bleibt "
                                 "gleich",
                                 ["Wird "
                                  "kleiner",
                                  "Wird "
                                  "größer"],
                                 ["F1", "F1"]),
                             distractors=[])},
                        {"key": "F2", "description": "Beim "
                         "Rosten nimmt das "
                         "Objekt zu — die "
                         "zugebundene "
                         "Luftmasse wird "
                         "vergessen.",
                         "remediation_hint": "Rost "
                         "wiegt MEHR als das "
                         "Eisen — der "
                         "Sauerstoff kam "
                         "dazu.",
                         "diagnostic_item": item(
                             "Eisen rostet — "
                             "wiegt Rost "
                             "mehr als das "
                             "Eisen?",
                             "Ja, der "
                             "Sauerstoff kam "
                             "dazu",
                             level="target",
                             grade=8,
                             answer=choice(
                                 "Ja, "
                                 "Sauerstoff "
                                 "dazu",
                                 ["Nein, "
                                  "gleich",
                                  "Nein, "
                                  "weniger"],
                                 ["F2", "F2"]),
                             distractors=[])}],
                    "diagnostic_items": [
                        item("Was ist ein "
                             "Produkt?",
                             "Der neue "
                             "Stoff nach der "
                             "Reaktion",
                             level="below",
                             grade=7,
                             answer=text(
                                 "neuer "
                                 "stoff",
                                 "der "
                                 "neue "
                                 "stoff")),
                        item("4 g + 5 g "
                             "reagieren "
                             "vollständig — "
                             "Produktmasse?",
                             "9 g",
                             level="target",
                             grade=8,
                             answer=number(
                                 "9"))],
                    "exit_items": [
                        item("12 g Eisen "
                             "rosten mit "
                             "3 g "
                             "Sauerstoff — "
                             "Rost-"
                             "masse?",
                             "15 g",
                             level="target",
                             grade=8,
                             answer=number(
                                 "15")),
                        item("Erkläre: warum "
                             "wiegt die "
                             "Asche eines "
                             "Lagerfeuers "
                             "weniger "
                             "als das "
                             "Holz?",
                             "Die Gase "
                             "entwichen "
                             "in die "
                             "Luft",
                             level="target",
                             grade=8,
                             answer=text(
                                 "gase "
                                 "entwichen",
                                 "die gase "
                                 "entwichen",
                                 "weil gase "
                                 "entweichen"))]},
                "lektion": {
                    "konzept": {
                        "konzept_key": "erhaltung",
                        "thema_key": "reaktion",
                        "label": "Massenerhaltung",
                        "klasse_von": 7, "klasse_bis": 9,
                        "stichworte": ["massenerhaltung",
                                       "masse "
                                       "bleibt",
                                       "erhaltung "
                                       "chemie",
                                       "nichts "
                                       "geht "
                                       "verloren"]},
                    "erstkontakt": {
                        "anker": "Eine Kerze "
                                 "brennt "
                                 "unter einem "
                                 "verschlossenen "
                                 "Glas auf der "
                                 "Waage — die "
                                 "Anzeige "
                                 "bewegt "
                                 "sich "
                                 "nicht. "
                                 "Warum?",
                        "benennung": "Massen-"
                                     "erhaltung",
                        "erste_aufgabe": {"frage":
                                          "5 g "
                                          "+ 3 g "
                                          "reagieren "
                                          "— "
                                          "Produkt-"
                                          "masse?",
                                          "loesung":
                                          "8 g"}},
                    "fehlertypen": [
                        {
                            "key": "gase_wiegen_nichts",
                            "label": "Gase wiegen "
                                     "nichts",
                            "beschreibung": "Was "
                            "davonfliegt, kann "
                            "nichts wiegen — "
                            "entweichende Gase "
                            "stehlen "
                            "scheinbar "
                            "Masse.",
                            "antworten": ["wird "
                                          "kleiner",
                                          "weniger",
                                          "gase "
                                          "wiegen "
                                          "nichts"],
                            "erklaerung": {
                                "haken": "Die "
                                        "Kerze "
                                        "brennt "
                                        "unter "
                                        "einem "
                                        "ver-"
                                        "schlossenen "
                                        "Glas "
                                        "— "
                                        "die "
                                        "Waage "
                                        "bleibt "
                                        "exakt. "
                                        "Wohin "
                                        "ging "
                                        "das "
                                        "Wachs?",
                                "erkenntnis": "Ins "
                                "Glas — als "
                                "Gas. "
                                "Dass es "
                                "davon-"
                                "fliegt, "
                                "heißt "
                                "nicht, "
                                "dass es "
                                "nichts "
                                "wiegt. "
                                "Im "
                                "geschlossenen "
                                "Gefäß "
                                "bleibt "
                                "alles "
                                "auf der "
                                "Waage.",
                                "regel": "Gase "
                                "haben "
                                "Masse. "
                                "Massen-"
                                "erhaltung "
                                "gilt "
                                "immer — "
                                "aber nur "
                                "geschlossene "
                                "Systeme "
                                "zeigen "
                                "sie "
                                "direkt.",
                                "bild": {"zeigt": "die "
                                         "Waage "
                                         "mit "
                                         "ver-"
                                         "schlossenem "
                                         "Glas "
                                         "— "
                                         "vorher "
                                         "und "
                                         "nachher",
                                         "bewegt": "die "
                                         "Gas-"
                                         "teilchen "
                                         "füllen "
                                         "das "
                                         "Glas, "
                                         "die "
                                         "Anzeige "
                                         "bleibt",
                                         "bleibt_gleich":
                                         "die "
                                         "Masse "
                                         "bleibt "
                                         "gleich"},
                                "aufgabe": {"frage":
                                            "7 g "
                                            "+ 2 g "
                                            "reagieren "
                                            "— "
                                            "Produkt-"
                                            "masse?",
                                            "loesung":
                                            "9 g"}},
                            "visualisierung": _FLUSS(
                                ["Edukte "
                                 "wiegen: "
                                 "5 + 3 g",
                                 "Reaktion "
                                 "läuft",
                                 "Produkte "
                                 "wiegen: "
                                 "8 g",
                                 "nichts "
                                 "entwich"]),
                            "visualisierung_alternativ":
                            _TABELLE(
                                ["System", "Waage "
                                 "zeigt"],
                                ["offen "
                                 "(Gase "
                                 "weg) | "
                                 "weniger — "
                                 "scheinbar",
                                 "geschlossen | "
                                 "gleich — "
                                 "wirklich"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Kerze "
                                    "brennt "
                                    "im "
                                    "geschlossenen "
                                    "Gefäß "
                                    "— die "
                                    "Waage?",
                                    "Bleibt "
                                    "gleich",
                                    ["Wird "
                                     "kleiner",
                                     "Wird "
                                     "größer"],
                                    "Nichts "
                                    "entweicht "
                                    "— "
                                    "die "
                                    "Gase "
                                    "bleiben "
                                    "drin."),
                                "beispiel": aufgabe(
                                    "4 g + "
                                    "5 g → "
                                    "9 g. "
                                    "Die "
                                    "Teilchen "
                                    "wechseln "
                                    "nur "
                                    "ihre "
                                    "Partner "
                                    "— "
                                    "keiner "
                                    "verschwindet.",
                                    "9 g"),
                                "gefuehrt": aufgabe(
                                    "6 g + "
                                    "3 g "
                                    "reagieren "
                                    "voll-"
                                    "ständig "
                                    "— "
                                    "Produkt-"
                                    "masse?",
                                    "9",
                                    fehler="18",
                                    art="zahl",
                                    tipps=["Pro "
                                           "heißt "
                                           "hier "
                                           "zu-"
                                           "sammen "
                                           "— "
                                           "nicht "
                                           "mal."]),
                                "selbststaendig": aufgabe(
                                    "10 g "
                                    "+ 7 g "
                                    "reagieren "
                                    "— "
                                    "Produkt-"
                                    "masse?",
                                    "17",
                                    fehler="70",
                                    art="zahl",
                                    tipps=["Masse "
                                           "addiert "
                                           "sich."]),
                                "transfer": auswahl(
                                    "Warum "
                                    "zeigt "
                                    "die "
                                    "offene "
                                    "Schale "
                                    "beim "
                                    "Verbrennen "
                                    "weniger?",
                                    "Die "
                                    "Gase "
                                    "entweichen "
                                    "ungewogen "
                                    "— "
                                    "nicht "
                                    "die "
                                    "Masse "
                                    "ver-"
                                    "schwindet",
                                    ["Die "
                                     "Waage "
                                     "ist "
                                     "schlecht",
                                     "Feuer "
                                     "frisst "
                                     "Masse"],
                                    "Der "
                                    "Becher "
                                    "beweist: "
                                    "was "
                                    "drin "
                                    "bleibt, "
                                    "zählt "
                                    "— "
                                    "was "
                                    "fliegt, "
                                    "fehlt.")}},
                        {
                            "key": "rost_wird_leichter",
                            "label": "Rosten "
                                     "verliert "
                                     "Masse",
                            "beschreibung": "Das "
                            "rostige Eisen "
                            "soll leichter "
                            "sein als "
                            "vorher — der "
                            "zugebundene "
                            "Sauerstoff "
                            "wird "
                            "vergessen.",
                            "antworten": ["weniger",
                                          "leichter",
                                          "gleich"],
                            "erklaerung": {
                                "haken": "Ein "
                                        "Eisen-"
                                        "nagel "
                                        "rostet "
                                        "— "
                                        "wird "
                                        "er "
                                        "leichter "
                                        "oder "
                                        "schwerer? "
                                        "Etwas "
                                        "kommt "
                                        "aus "
                                        "der "
                                        "Luft "
                                        "dazu.",
                                "erkenntnis": "Rost "
                                "= Eisen "
                                "+ Sauerstoff. "
                                "Der "
                                "Sauerstoff "
                                "aus der "
                                "Luft "
                                "dockt "
                                "an — "
                                "der "
                                "Nagel "
                                "wird "
                                "schwerer, "
                                "nicht "
                                "leichter.",
                                "regel": "Beim "
                                "Rosten "
                                "(und "
                                "jedem "
                                "Oxidieren) "
                                "kommt "
                                "Luft "
                                "dazu: "
                                "Produkt "
                                "= Edukt "
                                "+ gebundene "
                                "Luftmasse.",
                                "bild": {"zeigt": "der "
                                         "Nagel "
                                         "vorher "
                                         "und "
                                         "nachher "
                                         "mit "
                                         "angelagerten "
                                         "Luft-"
                                         "teilchen",
                                         "bewegt": "Sauerstoff-"
                                         "Kügelchen "
                                         "docken "
                                         "an "
                                         "das "
                                         "Eisen",
                                         "bleibt_gleich":
                                         "das "
                                         "Eisen "
                                         "bleibt "
                                         "drin"},
                                "aufgabe": {"frage":
                                            "12 g "
                                            "Eisen "
                                            "+ 3 g "
                                            "Sauerstoff "
                                            "= "
                                            "Rost — "
                                            "Masse?",
                                            "loesung":
                                            "15 g"}},
                            "visualisierung": _NETZ(
                                ["Eisen",
                                 "Sauerstoff "
                                 "aus Luft",
                                 "Rost"],
                                ["Eisen + "
                                 "Sauerstoff "
                                 "→ Rost",
                                 "Rost "
                                 "wiegt "
                                 "Eisen "
                                 "+ O"]),
                            "visualisierung_alternativ":
                            _TABELLE(
                                ["Edukt", "+ Luft",
                                 "= Produkt"],
                                ["12 g "
                                 "Eisen | "
                                 "3 g O₂ | "
                                 "15 g "
                                 "Rost"]),
                            "aufgaben": {
                                "vorhersage": auswahl(
                                    "Eisen "
                                    "rostet "
                                    "— "
                                    "wiegt "
                                    "der "
                                    "Rost "
                                    "mehr "
                                    "als "
                                    "das "
                                    "Eisen?",
                                    "Ja, "
                                    "der "
                                    "Sauerstoff "
                                    "kam "
                                    "dazu",
                                    ["Nein, "
                                     "gleich",
                                     "Nein, "
                                     "weniger"],
                                    "Rost "
                                    "ist "
                                    "Eisen "
                                    "PLUS "
                                    "Sauerstoff "
                                    "— die "
                                    "Luft "
                                    "lieferte "
                                    "Masse."),
                                "beispiel": aufgabe(
                                    "12 g "
                                    "Eisen "
                                    "+ 3 g "
                                    "Sauerstoff "
                                    "= "
                                    "15 g "
                                    "Rost. "
                                    "Die "
                                    "Waage "
                                    "zeigt "
                                    "die "
                                    "Luft-"
                                    "Beigabe.",
                                    "15 g"),
                                "gefuehrt": aufgabe(
                                    "8 g "
                                    "Kupfer "
                                    "werden "
                                    "mit "
                                    "2 g "
                                    "Sauerstoff "
                                    "zu "
                                    "Oxid "
                                    "— "
                                    "Masse?",
                                    "10",
                                    fehler="8",
                                    art="zahl",
                                    tipps=["Das "
                                           "Gas "
                                           "aus "
                                           "der "
                                           "Luft "
                                           "zählt "
                                           "mit."]),
                                "selbststaendig": aufgabe(
                                    "20 g "
                                    "Magnesium "
                                    "+ 10 g "
                                    "Sauerstoff "
                                    "— "
                                    "Oxid-"
                                    "masse?",
                                    "30",
                                    fehler="20",
                                    art="zahl",
                                    tipps=["Beide "
                                           "Edukte "
                                           "zählen."]),
                                "transfer": auswahl(
                                    "Warum "
                                    "beweist "
                                    "das "
                                    "Rosten "
                                    "die "
                                    "Erhaltung "
                                    "ebenso "
                                    "wie "
                                    "das "
                                    "Verbrennen?",
                                    "Beide "
                                    "Male "
                                    "zählt "
                                    "man "
                                    "alles — "
                                    "das "
                                    "Gas "
                                    "kommt "
                                    "dazu "
                                    "statt "
                                    "zu "
                                    "fehlen",
                                    ["Rost "
                                     "ist "
                                     "rot",
                                     "Es "
                                     "dauert "
                                     "länger"],
                                    "Erhaltung "
                                    "heißt: "
                                    "nichts "
                                    "weg, "
                                    "nichts "
                                    "dazu — "
                                    "nur "
                                    "um-"
                                    "gebaut.")}},
                    ],
                    "hilfe": _hilfe({
                        "HOOK": "Nichts geht "
                                "verloren — "
                                "aber nur "
                                "geschlossene "
                                "Systeme "
                                "zeigen es.",
                        "RULE": "Masse(Edukte) "
                                "= Masse"
                                "(Produkte) "
                                "— Gase "
                                "zählen "
                                "auf "
                                "beiden "
                                "Seiten "
                                "mit.",
                        "WORKED_EXAMPLE": "Edukte "
                                "wiegen, "
                                "reagieren "
                                "lassen, "
                                "Produkte "
                                "wiegen — "
                                "gleiche "
                                "Zahl.",
                        "GUIDED_TASK": "Addiere "
                                "die "
                                "Edukte — "
                                "die "
                                "Produkte "
                                "geben "
                                "dieselbe "
                                "Summe.",
                        "INDEPENDENT_TASK": "Entweicht "
                                "ein Gas, "
                                "fehlt es "
                                "auf der "
                                "Waage — "
                                "nicht "
                                "in "
                                "der "
                                "Bilanz.",
                        "ADAPTATION": "Die "
                                "Tabelle "
                                "zeigt "
                                "offen "
                                "gegen "
                                "geschlossen."}),
                    "faq": [
                        {"frage": "Warum wiegt "
                                  "Asche "
                                  "weniger "
                                  "als das "
                                  "Holz?",
                         "antwort": "Weil die "
                                    "Gase "
                                    "in die "
                                    "Luft "
                                    "entwichen "
                                    "— im "
                                    "geschlossenen "
                                    "Gefäß "
                                    "bleibt "
                                    "die "
                                    "Waage "
                                    "gleich."},
                        {"frage": "Wird Rost "
                                  "schwerer "
                                  "als "
                                  "das "
                                  "Eisen?",
                         "antwort": "Ja — "
                                    "der "
                                    "Sauerstoff "
                                    "aus "
                                    "der "
                                    "Luft "
                                    "kommt "
                                    "dazu. "
                                    "Rost = "
                                    "Eisen "
                                    "+ Luft."}],
                }},
        ]}]}
