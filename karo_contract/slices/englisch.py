"""Englisch-Slice: vom Verb zum Simple Past.

Level 0: das Kind erkennt Verben als Tätigkeitswörter und baut damit
einfache Sätze. Erst dann hat die Frage „wann?“ — Gegenwart oder
Vergangenheit — einen tragfähigen Boden, um auf die Vergangenheitsform
abzusteigen.

    EN.GRAMMAR.SIMPLE_PAST      (Ziel, Kl. 5–6)
      └── EN.GRAMMAR.PRESENT_PAST   (Kl. 5)
            └── EN.SENTENCE.BUILD       (Kl. 4)
                  └── EN.WORDS.VERBS        (Kl. 3–4, Level 0)
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
    "fach": "englisch",
    "code": "EN",
    "name": "Englisch",
    "blocks": [
        {
            "id": "EN.BASICS",
            "title": "Wörter und Sätze",
            "description": "Tätigkeitswörter und der englische Satzbau — "
                           "die Grundlage jeder Zeitform.",
            "grade_min": 3, "grade_max": 5, "typical_grade": 4,
            "concepts": [
                # ---------------------------------------------- Level 0
                {
                    "id": "EN.WORDS.VERBS",
                    "title": "Verbs: Tätigkeitswörter",
                    "description": "Verben als die Wörter, die sagen, was "
                                   "jemand tut — erkennen und im Satz finden.",
                    "first_contact_grade": 3, "target_grade": 4,
                    "prerequisites": [],
                    "levels": {
                        "below": "K3: einfache englische Wörter lesen",
                        "target": "K4: Verben im Satz erkennen und "
                                  "gebrauchen",
                        "above": "K5: Zeitformen der Verben"},
                    "can_do": {
                        "below": ["Bekannte englische Wörter lesen"],
                        "target": ["In einem einfachen englischen Satz "
                                   "das Verb finden"],
                        "above": ["Verben in eine andere Zeit setzen"]},
                    "difficulty_parameters": {
                        "wortschatz": "Basisverben: run, play, read, "
                                      "walk, eat",
                        "satz": "drei bis fünf Wörter"},
                    "anchor_items": [
                        item("Which word is the verb: „The dog runs.“?",
                             "runs", level="target", grade=4,
                             answer=text("runs")),
                        item("Which word is the verb: „Mia reads a book.“?",
                             "reads", level="target", grade=4,
                             answer=text("reads"))],
                    "boundary_items": {
                        "below": [item("Which word means „laufen“?",
                                       "run", level="below", grade=3,
                                       answer=text("run"))],
                        "within": [item("Verb in „The cat sleeps.“?",
                                        "sleeps", level="target",
                                        grade=4, answer=text("sleeps"))],
                        "above": [item("Put into the past: „walks“",
                                       "walked", level="above", grade=5,
                                       answer=text("walked"))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Das Verb wird "
                             "mit dem Subjekt verwechselt — das "
                             "Namenwort wird für die Tätigkeit gehalten.",
                             "remediation_hint": "The verb tells what "
                             "someone DOES — not who does it.",
                             "diagnostic_item": item(
                                 "Which word is the verb: „The dog "
                                 "runs.“?", "runs", level="target",
                                 grade=4,
                                 answer=choice("runs", ["dog", "The"],
                                               ["F1", None]),
                                 distractors=[])},
                            {"key": "F2", "description": "Jedes längere "
                             "oder unbekannte Wort wird zum Verb "
                             "erklärt — die Bedeutung zählt nicht.",
                             "remediation_hint": "Ask: can someone DO "
                             "this word? 'sleep' yes, 'the' no.",
                             "diagnostic_item": item(
                                 "Which word is the verb: „A bird "
                                 "sings.“?", "sings", level="target",
                                 grade=4,
                                 answer=choice("sings", ["bird", "A"],
                                               ["F1", None]),
                                 distractors=[])}],
                        "diagnostic_items": [
                            item("What does „play“ mean?", "spielen",
                                 level="below", grade=3,
                                 answer=text("spielen", "to play")),
                            item("Verb in „Tom walks.“?", "walks",
                                 level="target", grade=4,
                                 answer=text("walks"))],
                        "exit_items": [
                            item("Verb in „She eats an apple.“?", "eats",
                                 level="target", grade=4,
                                 answer=text("eats")),
                            item("Which word is the verb: „We play "
                                 "football.“?", "play", level="target",
                                 grade=4, answer=text("play"))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "verbs", "thema_key": "words",
                            "label": "Verbs — Tätigkeitswörter",
                            "klasse_von": 3, "klasse_bis": 5,
                            "stichworte": ["verb", "verbs",
                                           "tätigkeitswort",
                                           "action word", "englisch verb"]},
                        "erstkontakt": {
                            "anker": "„The dog runs.“ Which word tells "
                                     "what the dog DOES?",
                            "benennung": "Verb",
                            "erste_aufgabe": {"frage": "Which word is the "
                                              "verb: „Mia reads.“?",
                                              "loesung": "reads"}},
                        "fehlertypen": [
                            {
                                "key": "verb_ist_name",
                                "label": "Das Namenwort wird zum Verb",
                                "beschreibung": "Das Subjekt wird für das "
                                "Verb gehalten — „dog“ soll die "
                                "Tätigkeit sein.",
                                "antworten": ["dog", "cat", "the dog"],
                                "erklaerung": {
                                    "haken": "„The dog runs.“ Is „dog“ "
                                            "the verb? It is the one "
                                            "doing — not the doing.",
                                    "erkenntnis": "The verb tells the "
                                    "action: runs. The noun tells WHO "
                                    "does it: dog. Two different jobs.",
                                    "regel": "Verb = the action word "
                                    "(what someone does). Noun = the "
                                    "name (who does it).",
                                    "bild": {"zeigt": "dog und runs mit "
                                             "verschiedenen Rollen",
                                             "bewegt": "die Rollen "
                                             "wandern zu ihren Wörtern",
                                             "bleibt_gleich": "der Satz "
                                             "bleibt derselbe"},
                                    "aufgabe": {"frage": "Verb in „The "
                                                "cat sleeps.“?",
                                                "loesung": "sleeps"}},
                                "visualisierung": _FLUSS(
                                    ["„The dog runs.“",
                                     "Who? the dog → noun",
                                     "Does what? runs → verb"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Question", "Word", "Job"],
                                    ["who? | dog | noun",
                                     "does what? | runs | verb"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Which word is the verb: „The "
                                        "bird sings.“?",
                                        "sings", ["bird", "The"],
                                        "The verb is the action — "
                                        "singing, not the singer."),
                                    "beispiel": aufgabe(
                                        "„Mia reads.“ Who? Mia. Does "
                                        "what? reads — the verb.",
                                        "reads"),
                                    "gefuehrt": aufgabe(
                                        "Find the verb: „Tom walks.“",
                                        "walks",
                                        fehler="Tom",
                                        art="begriffe",
                                        rubrik=begriffe("walks"),
                                        tipps=["What does Tom DO?",
                                               "Tom is WHO walks."]),
                                    "selbststaendig": aufgabe(
                                        "Find the verb: „She eats.“",
                                        "eats",
                                        fehler="She",
                                        art="begriffe",
                                        rubrik=begriffe("eats"),
                                        tipps=["The action word."]),
                                    "transfer": auswahl(
                                        "Why is „quickly“ not the verb "
                                        "in „Tom runs quickly.“?",
                                        "It tells HOW he runs — the "
                                        "action is „runs“",
                                        ["It is too long",
                                         "It stands last"],
                                        "The verb names the action — "
                                        "other words describe it.")}},
                            {
                                "key": "unbekannt_ist_verb",
                                "label": "Unbekanntes Wort wird zum Verb",
                                "beschreibung": "Was das Kind nicht "
                                "versteht, muss die Tätigkeit sein.",
                                "antworten": ["the", "a", "an"],
                                "erklaerung": {
                                    "haken": "„A bird sings.“ Is „A“ "
                                            "the verb because it is "
                                            "strange? Little words are "
                                            "never actions.",
                                    "erkenntnis": "You test a word by "
                                    "asking: can somebody DO this? "
                                    "You can sing — you cannot „a“.",
                                    "regel": "Try the word: „I can ___“ "
                                    "— if it fits an action, it is a "
                                    "verb. „the, a, an“ only stand "
                                    "before names.",
                                    "bild": {"zeigt": "every word with "
                                             "a test question",
                                             "bewegt": "the words move "
                                             "to verb or not-verb",
                                             "bleibt_gleich": "the "
                                             "sentence keeps all words"},
                                    "aufgabe": {"frage": "Is „the“ a "
                                                "verb? (yes/no)",
                                                "loesung": "no"}},
                                "visualisierung": _NETZ(
                                    ["verb", "action", "I can ___"],
                                    ["verb → action",
                                     "test → I can ___"]),
                                "visualisierung_alternativ": _FLUSS(
                                    ["Take the word",
                                     "Ask: can someone DO it?",
                                     "yes → verb, no → something else"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Which is the verb: „A bird "
                                        "sings.“?",
                                        "sings", ["A", "bird"],
                                        "Only one word is an action — "
                                        "test: I can sing."),
                                    "beispiel": aufgabe(
                                        "Test each word: „I can the?“ — "
                                        "no. „I can sing?“ — yes. "
                                        "The verb is sings.",
                                        "sings"),
                                    "gefuehrt": aufgabe(
                                        "Is „eat“ a verb? (yes/no)",
                                        "yes",
                                        fehler="no",
                                        art="text",
                                        tipps=["Can someone eat?",
                                               "Eating is an action."]),
                                    "selbststaendig": aufgabe(
                                        "Find the verb: „The dog "
                                        "barks.“",
                                        "barks",
                                        fehler="the",
                                        art="begriffe",
                                        rubrik=begriffe("barks"),
                                        tipps=["I can ___ — which fits?"]),
                                    "transfer": auswahl(
                                        "How can you check if a word "
                                        "is a verb?",
                                        "Ask: can somebody DO it?",
                                        ["Check if it is long",
                                         "Check if it is English"],
                                        "The action test finds the "
                                        "verb, not the word length.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "A verb tells what someone DOES.",
                            "RULE": "Verb = action word. Test it: "
                                    "„I can ___“ — if it fits, it is "
                                    "a verb.",
                            "WORKED_EXAMPLE": "Read the sentence. Ask "
                                    "of each word: is this an action?",
                            "GUIDED_TASK": "Find the action first — "
                                    "then the word for it.",
                            "INDEPENDENT_TASK": "Who does it is the "
                                    "noun — what they do is the verb.",
                            "ADAPTATION": "The table shows: one "
                                    "question for nouns, another for "
                                    "verbs."}),
                        "faq": [
                            {"frage": "What is a verb?",
                             "antwort": "An action word: run, play, "
                                        "read. It tells what somebody "
                                        "does."},
                            {"frage": "Can „the“ be a verb?",
                             "antwort": "No — „the, a, an“ only come "
                                        "before names. You cannot "
                                        "„the“ anything."}],
                    }},
                # -------------------------------------- Satz bauen
                {
                    "id": "EN.SENTENCE.BUILD",
                    "title": "Englische Sätze bauen",
                    "description": "Subjekt + Verb + Rest — die feste "
                                   "Wortstellung des englischen "
                                   "Aussagesatzes.",
                    "first_contact_grade": 4, "target_grade": 4,
                    "prerequisites": ["EN.WORDS.VERBS"],
                    "levels": {
                        "below": "K4: Verben erkennen",
                        "target": "K4: einfache Aussagesätze mit "
                                  "Subjekt + Verb bauen",
                        "above": "K5: Fragen und Verneinungen"},
                    "can_do": {
                        "below": ["das Verb in einem Satz finden"],
                        "target": ["aus drei bis fünf Wörtern einen "
                                   "richtigen englischen Satz bauen"],
                        "above": ["Fragen mit do/does stellen"]},
                    "difficulty_parameters": {
                        "wortstellung": "Subjekt + Verb + Objekt",
                        "satz": "Aussagesatz, 3–5 Wörter"},
                    "anchor_items": [
                        item("Order the words: reads / Mia / a book",
                             "Mia reads a book", level="target",
                             grade=4,
                             answer=text("mia reads a book",
                                         "mia reads a book.")),
                        item("Order: the dog / runs / fast",
                             "The dog runs fast", level="target",
                             grade=4,
                             answer=text("the dog runs fast",
                                         "the dog runs fast."))],
                    "boundary_items": {
                        "below": [item("Verb in „The cat sleeps.“?",
                                       "sleeps", level="below", grade=4,
                                       answer=text("sleeps"))],
                        "within": [item("Order: plays / Tom / football",
                                        "Tom plays football",
                                        level="target", grade=4,
                                        answer=text("tom plays football",
                                                    "tom plays football."))],
                        "above": [item("Make a question: „She reads.“",
                                       "Does she read?", level="above",
                                       grade=5,
                                       answer=text("does she read",
                                                   "does she read?"))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Deutsche "
                             "Wortstellung wird übertragen: „Mia a "
                             "book reads“ — das Verb wandert ans Ende.",
                             "remediation_hint": "English keeps the "
                             "verb on place 2 — never at the end.",
                             "diagnostic_item": item(
                                 "Order: reads / Mia / a book",
                                 "Mia reads a book", level="target",
                                 grade=4,
                                 answer=choice("Mia reads a book",
                                               ["Mia a book reads",
                                                "Reads Mia a book"],
                                               ["F1", None]),
                                 distractors=[])},
                            {"key": "F2", "description": "Das s der "
                             "3. Person wird vergessen: „he play“ "
                             "statt „he plays“.",
                             "remediation_hint": "he/she/it + s — "
                             "the verb shows who acts.",
                             "diagnostic_item": item(
                                 "Complete: „She ___ football.“",
                                 "plays", level="target", grade=4,
                                 answer=choice("plays", ["play", "playes"],
                                               ["F2", None]),
                                 distractors=[])}],
                        "diagnostic_items": [
                            item("Verb in „She sings.“?", "sings",
                                 level="below", grade=4,
                                 answer=text("sings")),
                            item("Order: eats / He / an apple",
                                 "He eats an apple", level="target",
                                 grade=4,
                                 answer=text("he eats an apple",
                                             "he eats an apple."))],
                        "exit_items": [
                            item("Order: plays / The dog / with the ball",
                                 "The dog plays with the ball",
                                 level="target", grade=4,
                                 answer=text("the dog plays with the "
                                             "ball",
                                             "the dog plays with the "
                                             "ball.")),
                            item("Complete: „Tom ___ a book.“",
                                 "reads", level="target", grade=4,
                                 answer=text("reads"))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "build", "thema_key": "sentence",
                            "label": "Englische Sätze bauen",
                            "klasse_von": 4, "klasse_bis": 5,
                            "stichworte": ["englischer satz",
                                           "wortstellung englisch",
                                           "subject verb",
                                           "englisch satz bauen"]},
                        "erstkontakt": {
                            "anker": "German: „Mia ein Buch liest.“ — "
                                     "why does English keep the verb "
                                     "on place 2?",
                            "benennung": "Wortstellung",
                            "erste_aufgabe": {"frage": "Order: reads / "
                                              "Mia / a book",
                                              "loesung": "Mia reads a "
                                                         "book"}},
                        "fehlertypen": [
                            {
                                "key": "verb_ans_ende",
                                "label": "Verb ans Ende gestellt",
                                "beschreibung": "Die deutsche "
                                "Wortstellung wandert ins Englische — "
                                "das Verb rutscht ans Satzende.",
                                "antworten": ["mia a book reads",
                                              "the dog a ball plays"],
                                "erklaerung": {
                                    "haken": "„Mia a book reads.“ — "
                                            "in German word order this "
                                            "works. In English the verb "
                                            "never goes to the end.",
                                    "erkenntnis": "English keeps a "
                                    "fixed order: WHO + DOES + the "
                                    "rest. „Mia reads a book“ — the "
                                    "verb stays on place 2.",
                                    "regel": "English sentence = "
                                    "Subject + Verb + the rest. The "
                                    "verb always sits on place 2.",
                                    "bild": {"zeigt": "drei Sitzplätze: "
                                             "Wer — Tut — Rest",
                                             "bewegt": "die Wörter "
                                             "setzen sich auf ihre "
                                             "Plätze",
                                             "bleibt_gleich": "die "
                                             "Bedeutung bleibt "
                                             "dieselbe"},
                                    "aufgabe": {"frage": "Order: plays / "
                                                "Tom / football",
                                                "loesung": "Tom plays "
                                                           "football"}},
                                "visualisierung": _FLUSS(
                                    ["Platz 1: WHO — Mia",
                                     "Platz 2: DOES — reads",
                                     "Rest: a book"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Platz", "Wortart", "Beispiel"],
                                    ["1 | Subjekt | Mia",
                                     "2 | Verb | reads",
                                     "3 | Rest | a book"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Order: reads / Mia / a book",
                                        "Mia reads a book",
                                        ["Mia a book reads",
                                         "Reads Mia a book"],
                                        "Place 2 belongs to the verb — "
                                        "English never sends it to "
                                        "the end."),
                                    "beispiel": aufgabe(
                                        "„The dog runs fast.“ — WHO? "
                                        "the dog. DOES? runs. Rest? "
                                        "fast.",
                                        "The dog runs fast"),
                                    "gefuehrt": aufgabe(
                                        "Order: eats / He / an apple",
                                        "He eats an apple",
                                        fehler="He an apple eats",
                                        art="text",
                                        tipps=["Who? — then DOES — "
                                               "then the rest.",
                                               "The verb sits on "
                                               "place 2."]),
                                    "selbststaendig": aufgabe(
                                        "Order: sings / The bird / "
                                        "loudly",
                                        "The bird sings loudly",
                                        fehler="The bird loudly sings",
                                        art="text",
                                        tipps=["Verb on place 2."]),
                                    "transfer": auswahl(
                                        "Why can't the verb go to the "
                                        "end in English?",
                                        "English has fixed places: "
                                        "Subject + Verb + Rest",
                                        ["It sounds wrong",
                                         "Only questions do that"],
                                        "The word order IS the "
                                        "grammar in English.")}},
                            {
                                "key": "s_vergessen",
                                "label": "Das s der 3. Person fehlt",
                                "beschreibung": "„he play“ statt „he "
                                "plays“ — die Person zeigt sich nicht "
                                "im Verb.",
                                "antworten": ["he play", "she read",
                                              "it go"],
                                "erklaerung": {
                                    "haken": "„He play football.“ — "
                                            "one letter missing, and "
                                            "the sentence is wrong.",
                                    "erkenntnis": "When he, she or it "
                                    "does something, the verb shows "
                                    "it: he plays, she reads, it "
                                    "runs. The s marks the third "
                                    "person.",
                                    "regel": "he/she/it + Verb + s. "
                                    "All other persons stay without s.",
                                    "bild": {"zeigt": "die Personen "
                                             "I-you-he-she-it und ihre "
                                             "Verbformen",
                                             "bewegt": "das s wandert "
                                             "nur zu he, she, it",
                                             "bleibt_gleich": "die "
                                             "Handlung bleibt dieselbe"},
                                    "aufgabe": {"frage": "Complete: "
                                                "„She ___ football.“",
                                                "loesung": "plays"}},
                                "visualisierung": _TABELLE(
                                    ["Person", "Verb"],
                                    ["I / you | play",
                                     "he / she / it | plays",
                                     "we / they | play"]),
                                "visualisierung_alternativ": _FLUSS(
                                    ["Who acts? she",
                                     "she → verb gets +s",
                                     "she plays"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Complete: „She ___ "
                                        "football.“",
                                        "plays", ["play", "playes"],
                                        "she gets the s — just an s, "
                                        "not -es."),
                                    "beispiel": aufgabe(
                                        "„He reads.“ he → read + s. "
                                        "I read — he reads.",
                                        "He reads"),
                                    "gefuehrt": aufgabe(
                                        "Complete: „Tom ___ a book.“",
                                        "reads",
                                        fehler="read",
                                        art="begriffe",
                                        rubrik=begriffe("reads"),
                                        tipps=["Tom is he — and he "
                                               "gets the s."]),
                                    "selbststaendig": aufgabe(
                                        "Complete: „The dog ___ "
                                        "fast.“",
                                        "runs",
                                        fehler="run",
                                        art="begriffe",
                                        rubrik=begriffe("runs"),
                                        tipps=["The dog is it."]),
                                    "transfer": auswahl(
                                        "Why does „she plays“ have "
                                        "an s but „they play“ not?",
                                        "The s marks he/she/it — one "
                                        "single person",
                                        ["It is a plural",
                                         "It sounds better"],
                                        "The verb shows who acts — "
                                        "only the third person gets "
                                        "the s.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "English has fixed seats: WHO + "
                                    "DOES + the rest.",
                            "RULE": "Subject + Verb + Rest. he/she/it "
                                    "gets an s on the verb.",
                            "WORKED_EXAMPLE": "Sort the words into "
                                    "their seats — verb always on "
                                    "place 2.",
                            "GUIDED_TASK": "Who? — then the verb — "
                                    "then the rest.",
                            "INDEPENDENT_TASK": "Check the person: "
                                    "he/she/it needs the s.",
                            "ADAPTATION": "The table shows every "
                                    "person with its verb form."}),
                        "faq": [
                            {"frage": "Where does the verb go in "
                                      "English?",
                             "antwort": "Always on place 2 — Subject "
                                        "+ Verb + the rest."},
                            {"frage": "When does the verb get an s?",
                             "antwort": "With he, she or it: he "
                                        "plays, she reads, it runs."}],
                    }},
            ]},
        {
            "id": "EN.GRAMMAR",
            "title": "Zeiten",
            "description": "Gegenwart und Vergangenheit — bis zum "
                           "Simple Past.",
            "grade_min": 5, "grade_max": 6, "typical_grade": 5,
            "concepts": [
                # ------------------------------ Gegenwart/Vergangenheit
                {
                    "id": "EN.GRAMMAR.PRESENT_PAST",
                    "title": "Gegenwart und Vergangenheit unterscheiden",
                    "description": "Wann passiert es — jetzt oder "
                                   "früher? Zeitwörter lesen und die "
                                   "Verbform erkennen.",
                    "first_contact_grade": 5, "target_grade": 5,
                    "prerequisites": ["EN.SENTENCE.BUILD"],
                    "levels": {
                        "below": "K4: Sätze mit Subjekt + Verb bauen",
                        "target": "K5: present und past an "
                                  "Zeitwörtern und Verbform erkennen",
                        "above": "K6: Simple Past selbst bilden"},
                    "can_do": {
                        "below": ["einen englischen Satz bauen"],
                        "target": ["sagen, ob ein Satz in Gegenwart "
                                   "oder Vergangenheit steht"],
                        "above": ["Sätze selbst in die Vergangenheit "
                                  "setzen"]},
                    "difficulty_parameters": {
                        "zeitwoerter": "now, every day / yesterday, "
                                       "last week",
                        "form": "regelmäßige -ed"},
                    "anchor_items": [
                        item("Present or past: „Mia played football "
                             "yesterday.“?", "past",
                             level="target", grade=5,
                             answer=text("past")),
                        item("Present or past: „She reads every "
                             "day.“?", "present", level="target",
                             grade=5, answer=text("present"))],
                    "boundary_items": {
                        "below": [item("Complete: „He ___ football.“",
                                       "plays", level="below", grade=4,
                                       answer=text("plays"))],
                        "within": [item("Present or past: „They "
                                        "walked home.“?", "past",
                                        level="target", grade=5,
                                        answer=text("past"))],
                        "above": [item("Put into past: „She plays.“",
                                       "She played.", level="above",
                                       grade=6,
                                       answer=text("she played",
                                                   "played"))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Das "
                             "Zeitwort wird ignoriert — „yesterday“ "
                             "wird mit Gegenwart kombiniert.",
                             "remediation_hint": "Time words tell "
                             "when: yesterday = past, every day = "
                             "present.",
                             "diagnostic_item": item(
                                 "Present or past: „He played "
                                 "yesterday.“?", "past",
                                 level="target", grade=5,
                                 answer=choice("past", ["present"],
                                               ["F1"]),
                                 distractors=[])},
                        {"key": "F2", "description": "Das -ed wird als "
                             "Teil des Wortstamms gelesen statt als "
                             "Zeichen der Vergangenheit.",
                             "remediation_hint": "-ed at the end of "
                             "a verb means: it already happened.",
                             "diagnostic_item": item(
                                 "What does „walked“ mean?",
                                 "lief / ist gelaufen",
                                 level="target", grade=5,
                                 answer=text("lief", "ist gelaufen",
                                             "ging", "laufen früher"),
                                 distractors=[])}],
                        "diagnostic_items": [
                            item("Present or past: „She plays.“?",
                                 "present", level="below", grade=5,
                                 answer=text("present")),
                            item("Present or past: „We watched a "
                                 "film.“?", "past", level="target",
                                 grade=5, answer=text("past"))],
                        "exit_items": [
                            item("Present or past: „Tom visited "
                                 "grandma last week.“?", "past",
                                 level="target", grade=5,
                                 answer=text("past")),
                            item("Present or past: „Birds sing in "
                                 "spring.“?", "present",
                                 level="target", grade=5,
                                 answer=text("present"))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "present_past",
                            "thema_key": "grammar",
                            "label": "Gegenwart oder Vergangenheit",
                            "klasse_von": 5, "klasse_bis": 6,
                            "stichworte": ["present past",
                                           "vergangenheit englisch",
                                           "past or present",
                                           "vergangenheit erkennen",
                                           "yesterday"]},
                        "erstkontakt": {
                            "anker": "„Mia played yesterday.“ — how "
                                     "does the sentence tell you WHEN "
                                     "it happened?",
                            "benennung": "Zeit",
                            "erste_aufgabe": {"frage": "Present or "
                                              "past: „He played "
                                              "yesterday.“?",
                                              "loesung": "past"}},
                        "fehlertypen": [
                            {
                                "key": "zeitwort_ignoriert",
                                "label": "Zeitwort wird ignoriert",
                                "beschreibung": "„yesterday“ wird "
                                "überlesen — die Zeit wird nur aus "
                                "dem Verb geschätzt.",
                                "antworten": ["present", "he plays",
                                              "play"],
                                "erklaerung": {
                                    "haken": "„He played yesterday.“ "
                                            "Two signs point to the "
                                            "past — the verb AND the "
                                            "time word.",
                                    "erkenntnis": "Time words tell "
                                    "when it happens: yesterday, "
                                    "last week → past. every day, "
                                    "now → present.",
                                    "regel": "Look for the time word "
                                    "first — it answers „when?“. "
                                    "Then check the verb: -ed means "
                                    "it already happened.",
                                    "bild": {"zeigt": "eine "
                                             "Zeitleiste mit "
                                             "yesterday und today",
                                             "bewegt": "der Satz "
                                             "wandert auf die "
                                             "Vergangenheitsseite",
                                             "bleibt_gleich": "die "
                                             "Handlung bleibt "
                                             "dieselbe"},
                                    "aufgabe": {"frage": "Present or "
                                                "past: „We walked "
                                                "home.“?",
                                                "loesung": "past"}},
                                "visualisierung": _TABELLE(
                                    ["When?", "Time word", "Form"],
                                    ["past | yesterday, last week | "
                                     "verb + ed",
                                     "present | now, every day | "
                                     "verb (+s)"]),
                                "visualisierung_alternativ": _FLUSS(
                                    ["Find the time word: yesterday",
                                     "yesterday → past",
                                     "verb shows -ed → past"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Present or past: „He "
                                        "played yesterday.“?",
                                        "past", ["present"],
                                        "yesterday means it already "
                                        "happened — and -ed agrees."),
                                    "beispiel": aufgabe(
                                        "„She visits grandma every "
                                        "Sunday.“ every Sunday → "
                                        "present.",
                                        "present"),
                                    "gefuehrt": aufgabe(
                                        "Present or past: „They "
                                        "watched TV last night.“?",
                                        "past",
                                        fehler="present",
                                        art="text",
                                        tipps=["When did it happen?",
                                               "last night tells the "
                                               "time."]),
                                    "selbststaendig": aufgabe(
                                        "Present or past: „Mia "
                                        "helped yesterday.“?",
                                        "past",
                                        fehler="present",
                                        art="text",
                                        tipps=["Find the time word."]),
                                    "transfer": auswahl(
                                        "Why is „yesterday“ enough "
                                        "to know the time, even "
                                        "without the verb?",
                                        "It says WHEN — yesterday "
                                        "can only be past",
                                        ["It is a noun",
                                         "It stands last"],
                                        "Time words fix the time — "
                                        "the verb only agrees.")}},
                            {
                                "key": "ed_ignoriert",
                                "label": "Das -ed wird nicht gelesen",
                                "beschreibung": "walked wird wie "
                                "walk gelesen — das Vergangenheits-"
                                "zeichen am Ende fällt weg.",
                                "antworten": ["walk", "he walks",
                                              "present"],
                                "erklaerung": {
                                    "haken": "„walked“ and „walk“ "
                                            "differ by two letters — "
                                            "and a whole time.",
                                    "erkenntnis": "The little -ed "
                                    "says: finished, done, in the "
                                    "past. walk = now, walked = "
                                    "before.",
                                    "regel": "regular verb + -ed = "
                                    "past. The ending is the "
                                    "time signal.",
                                    "bild": {"zeigt": "walk und "
                                             "walked an zwei "
                                             "Zeitpunkten",
                                             "bewegt": "das ed "
                                             "schiebt das Wort in "
                                             "die Vergangenheit",
                                             "bleibt_gleich": "die "
                                             "Handlung bleibt "
                                             "dieselbe"},
                                    "aufgabe": {"frage": "Is "
                                                "„played“ present "
                                                "or past?",
                                                "loesung": "past"}},
                                "visualisierung": _FLUSS(
                                    ["walk — now",
                                     "walk + ed — finished",
                                     "-ed is the past signal"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["Verb", "Time"],
                                    ["play | now", "played | before",
                                     "walk | now", "walked | before"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "„He walked home.“ — "
                                        "present or past?",
                                        "past", ["present"],
                                        "The -ed marks: already "
                                        "done."),
                                    "beispiel": aufgabe(
                                        "play → played. The -ed "
                                        "moves the action into the "
                                        "past.",
                                        "played"),
                                    "gefuehrt": aufgabe(
                                        "Present or past: „She "
                                        "visited.“?",
                                        "past",
                                        fehler="present",
                                        art="text",
                                        tipps=["Look at the verb "
                                               "ending.",
                                               "-ed means finished."]),
                                    "selbststaendig": aufgabe(
                                        "Present or past: „We "
                                        "helped.“?",
                                        "past",
                                        fehler="present",
                                        art="text",
                                        tipps=["Check the ending."]),
                                    "transfer": auswahl(
                                        "Why does English mark the "
                                        "past on the verb itself?",
                                        "The ending carries the "
                                        "time — the sentence works "
                                        "without a time word",
                                        ["It is shorter",
                                         "It is a rule without "
                                         "reason"],
                                        "-ed makes every regular "
                                        "verb tell its time.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Two signs tell the time: the "
                                    "time word and the verb ending.",
                            "RULE": "yesterday/last week + -ed = "
                                    "past. now/every day = present.",
                            "WORKED_EXAMPLE": "Find the time word "
                                    "first, then check the verb "
                                    "ending.",
                            "GUIDED_TASK": "Ask: when does it "
                                    "happen? Look for yesterday or "
                                    "-ed.",
                            "INDEPENDENT_TASK": "The -ed is a time "
                                    "signal, not part of the word.",
                            "ADAPTATION": "The table puts every "
                                    "verb on its side of the "
                                    "timeline."}),
                        "faq": [
                            {"frage": "How do I see the past?",
                             "antwort": "Two ways: a time word like "
                                        "yesterday — or -ed at the "
                                        "end of the verb."},
                            {"frage": "Is „played“ a new word?",
                             "antwort": "No — it is „play“ with the "
                                        "past signal -ed. Same "
                                        "action, earlier."}],
                    }},
                # --------------------------------------- Simple Past
                {
                    "id": "EN.GRAMMAR.SIMPLE_PAST",
                    "title": "Simple Past bilden",
                    "description": "Regelmäßige Verben in die "
                                   "Vergangenheit setzen: play → "
                                   "played — und die berühmten "
                                   "unregelmäßigen.",
                    "first_contact_grade": 5, "target_grade": 6,
                    "prerequisites": ["EN.GRAMMAR.PRESENT_PAST"],
                    "levels": {
                        "below": "K5: present und past "
                                 "unterscheiden",
                        "target": "K6: Simple Past regelmäßiger "
                                  "Verben bilden und die wichtigsten "
                                  "unregelmäßigen kennen",
                        "above": "K7: Fragen und Verneinungen im "
                                 "Simple Past"},
                    "can_do": {
                        "below": ["past von present unterscheiden"],
                        "target": ["regelmäßige Verben mit -ed in "
                                   "die Vergangenheit setzen und "
                                   "go→went, eat→ate kennen"],
                        "above": ["did-Fragen und didn't-"
                                  "Verneinungen bilden"]},
                    "difficulty_parameters": {
                        "regelmaessig": "verb + ed",
                        "unregelmaessig": "go, eat, see, have, run"},
                    "anchor_items": [
                        item("Put into past: „Mia plays football.“",
                             "Mia played football.",
                             level="target", grade=6,
                             answer=text("mia played football",
                                         "mia played football.")),
                        item("Past of „go“?", "went", level="target",
                             grade=6, answer=text("went"))],
                    "boundary_items": {
                        "below": [item("Present or past: „She "
                                       "walked.“?", "past",
                                       level="below", grade=5,
                                       answer=text("past"))],
                        "within": [item("Past of „help“?", "helped",
                                        level="target", grade=6,
                                        answer=text("helped"))],
                        "above": [item("Make a question: „She "
                                       "played.“",
                                       "Did she play?", level="above",
                                       grade=7,
                                       answer=text("did she play",
                                                   "did she play?"))]},
                    "diagnostics": {
                        "misconceptions": [
                            {"key": "F1", "description": "Unregelmäßige "
                             "Verben bekommen ein -ed: „goed“ statt "
                             "„went“.",
                             "remediation_hint": "Some verbs change "
                             "completely — they must be learned, "
                             "not built.",
                             "diagnostic_item": item(
                                 "Past of „go“?", "went",
                                 level="target", grade=6,
                                 answer=choice("went",
                                               ["goed", "goes"],
                                               ["F1", None]),
                                 distractors=[])},
                            {"key": "F2", "description": "Bei "
                             "End-e wird ein zweites e angehängt: "
                             "„likeed“ statt „liked“.",
                             "remediation_hint": "Verb ends in e → "
                             "just add -d, not -ed.",
                             "diagnostic_item": item(
                                 "Past of „like“?", "liked",
                                 level="target", grade=6,
                                 answer=choice("liked",
                                               ["likeed", "liket"],
                                               ["F2", None]),
                                 distractors=[])}],
                        "diagnostic_items": [
                            item("Present or past: „They played.“?",
                                 "past", level="below", grade=5,
                                 answer=text("past")),
                            item("Past of „walk“?", "walked",
                                 level="target", grade=6,
                                 answer=text("walked"))],
                        "exit_items": [
                            item("Put into past: „She visits her "
                                 "grandma.“",
                                 "She visited her grandma.",
                                 level="target", grade=6,
                                 answer=text("she visited her grandma",
                                             "she visited her grandma.")),
                            item("Past of „eat“?", "ate",
                                 level="target", grade=6,
                                 answer=text("ate"))]},
                    "lektion": {
                        "konzept": {
                            "konzept_key": "simple_past",
                            "thema_key": "grammar",
                            "label": "Simple Past",
                            "klasse_von": 5, "klasse_bis": 7,
                            "stichworte": ["simple past",
                                           "past tense",
                                           "vergangenheit englisch",
                                           "played went",
                                           "unregelmäßige verben"]},
                        "erstkontakt": {
                            "anker": "Yesterday Mia visited her "
                                     "grandma. How does „visit“ "
                                     "change — and what about „go“?",
                            "benennung": "Simple Past",
                            "erste_aufgabe": {"frage": "Past of "
                                              "„walk“?",
                                              "loesung": "walked"}},
                        "fehlertypen": [
                            {
                                "key": "irregular_ed",
                                "label": "Unregelmäßiges Verb mit -ed",
                                "beschreibung": "„goed“ statt „went“ "
                                "— die Regel wird auf Verben "
                                "gewalttätig angewandt, die sie "
                                "nicht kennen.",
                                "antworten": ["goed", "eated",
                                              "runned", "seed"],
                                "erklaerung": {
                                    "haken": "„Yesterday he goed "
                                            "home.“ — it follows the "
                                            "rule perfectly. And it "
                                            "is wrong.",
                                    "erkenntnis": "Some very common "
                                    "verbs change completely: go → "
                                    "went, eat → ate, see → saw. "
                                    "They grew irregular over "
                                    "centuries.",
                                    "regel": "Regular verbs take "
                                    "-ed. Irregular verbs have "
                                    "their own form — you learn "
                                    "them like vocabulary.",
                                    "bild": {"zeigt": "zwei Wege "
                                             "ins Gestern: die "
                                             "regelmäßige -ed-"
                                             "Straße und die "
                                             "Sonderformen",
                                             "bewegt": "go springt "
                                             "auf went um",
                                             "bleibt_gleich": "die "
                                             "Handlung bleibt "
                                             "dieselbe"},
                                    "aufgabe": {"frage": "Past of "
                                                "„eat“?",
                                                "loesung": "ate"}},
                                "visualisierung": _TABELLE(
                                    ["present", "past"],
                                    ["play | played",
                                     "walk | walked",
                                     "go | went", "eat | ate",
                                     "see | saw"]),
                                "visualisierung_alternativ": _NETZ(
                                    ["past", "regular + ed",
                                     "irregular forms"],
                                    ["play → played",
                                     "go → went",
                                     "eat → ate"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Past of „go“?", "went",
                                        ["goed", "goes"],
                                        "go is irregular — it "
                                        "changes completely to "
                                        "went."),
                                    "beispiel": aufgabe(
                                        "eat does not take -ed: "
                                        "eat → ate. The whole word "
                                        "changes.",
                                        "ate"),
                                    "gefuehrt": aufgabe(
                                        "Past of „see“?", "saw",
                                        fehler="seed",
                                        art="begriffe",
                                        rubrik=begriffe("saw"),
                                        tipps=["see is irregular — "
                                               "it does not take "
                                               "-ed."]),
                                    "selbststaendig": aufgabe(
                                        "Past of „run“?", "ran",
                                        fehler="runned",
                                        art="begriffe",
                                        rubrik=begriffe("ran"),
                                        tipps=["run changes its "
                                               "vowel."]),
                                    "transfer": auswahl(
                                        "Why can't you build "
                                        "„went“ from „go“ + -ed?",
                                        "Irregular verbs have own "
                                        "forms learned by heart — "
                                        "the rule does not apply",
                                        ["go is too short",
                                         "went is an adjective"],
                                        "The rule covers regular "
                                        "verbs only — the common "
                                        "ones often went their "
                                        "own way.")}},
                            {
                                "key": "end_e_doppelt",
                                "label": "End-e bekommt noch ein e",
                                "beschreibung": "„likeed“ statt "
                                "„liked“ — am End-e wird die volle "
                                "Endung angehängt.",
                                "antworten": ["likeed", "useed",
                                              "loveed"],
                                "erklaerung": {
                                    "haken": "like + ed = likeed? "
                                            "Two e's in a row look "
                                            "wrong — because one is "
                                            "already there.",
                                    "erkenntnis": "A verb ending "
                                    "in e already owns the e — "
                                    "only the d is added: like → "
                                    "liked, use → used.",
                                    "regel": "Verb ends in e → "
                                    "add -d only. No e doubles.",
                                    "bild": {"zeigt": "like und "
                                             "das angehängte d",
                                             "bewegt": "das d "
                                             "dockt an das "
                                             "vorhandene e",
                                             "bleibt_gleich": "die "
                                             "Aussprache bleibt "
                                             "dieselbe"},
                                    "aufgabe": {"frage": "Past of "
                                                "„use“?",
                                                "loesung": "used"}},
                                "visualisierung": _FLUSS(
                                    ["like ends in e",
                                     "only add d",
                                     "liked — one e is enough"]),
                                "visualisierung_alternativ": _TABELLE(
                                    ["end", "add", "result"],
                                    ["play (no e) | +ed | played",
                                     "like (ends e) | +d | liked",
                                     "stop (short) | +ped | stopped"]),
                                "aufgaben": {
                                    "vorhersage": auswahl(
                                        "Past of „like“?",
                                        "liked",
                                        ["likeed", "liket"],
                                        "like already ends in e — "
                                        "only a d is missing."),
                                    "beispiel": aufgabe(
                                        "use + d: used. The verb's "
                                        "own e does the job.",
                                        "used"),
                                    "gefuehrt": aufgabe(
                                        "Past of „love“?", "loved",
                                        fehler="loveed",
                                        art="begriffe",
                                        rubrik=begriffe("loved"),
                                        tipps=["love ends in e — "
                                               "what's missing?"]),
                                    "selbststaendig": aufgabe(
                                        "Past of „dance“?",
                                        "danced",
                                        fehler="danceed",
                                        art="begriffe",
                                        rubrik=begriffe("danced"),
                                        tipps=["Just add d."]),
                                    "transfer": auswahl(
                                        "Why does „walked“ get a "
                                        "full -ed but „liked“ only "
                                        "a d?",
                                        "like brings its own e — "
                                        "the ending completes it",
                                        ["like is irregular",
                                         "It is shorter"],
                                        "The rule adapts to the "
                                        "ending the verb already "
                                        "has.")}},
                        ],
                        "hilfe": _hilfe({
                            "HOOK": "Two roads to the past: -ed "
                                    "for most, special forms for "
                                    "the famous few.",
                            "RULE": "regular + ed (ends in e → "
                                    "+d). Irregulars you learn by "
                                    "heart: go→went, eat→ate.",
                            "WORKED_EXAMPLE": "Check the ending "
                                    "first: no e → +ed, ends e → "
                                    "+d.",
                            "GUIDED_TASK": "Is the verb regular? "
                                    "Then -ed — watch the "
                                    "end-e.",
                            "INDEPENDENT_TASK": "go, eat, see, "
                                    "run — these change "
                                    "completely.",
                            "ADAPTATION": "The table separates "
                                    "regular -ed from the "
                                    "irregulars."}),
                        "faq": [
                            {"frage": "Why is it „went“ and not "
                                      "„goed“?",
                             "antwort": "go is irregular — like "
                                        "eat→ate and see→saw it "
                                        "has its own form."},
                            {"frage": "How do I form the Simple "
                                      "Past?",
                             "antwort": "Regular: verb + ed (ends "
                                        "in e → just +d). "
                                        "Irregular: learn the "
                                        "form."}],
                    }},
            ]},
    ]}
