"""Lernpilot: deterministischer Prototyp für den adaptiven Lernprozess.

Isolierter Testballon für EINE Frage — kann Karo ein falsches mentales
Modell durch Interaktion verändern? Konzept: Brüche mit verschiedenen
Nennern addieren, Zielfehlvorstellung "Zähler und Nenner getrennt
addieren" (1/2 + 1/3 -> 2/5).

Keine LLM-Aufrufe, keine NotebookLM-/Video-/TTS-Erzeugung. Der gesamte
Zustand ist ein JSON-fähiges Dict, das der Router in der Session hält —
diese Datei kennt keine Session, keine Requests, kein HTTP.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Optional

# --------------------------------------------------------------------------
# Zustandsautomat
# --------------------------------------------------------------------------

PHASES = (
    "ANCHOR", "DIAGNOSTIC", "DIAGNOSTIC_REASONING", "CONFLICT", "PREDICTION",
    "VISUAL_DISCOVERY", "DISCOVERY", "RULE", "WORKED_EXAMPLE", "GUIDED_TASK",
    "ADAPTATION", "INDEPENDENT_TASK", "TRANSFER", "FINAL_RETRIEVAL", "COMPLETE",
)

#: Vollstaendig vorgerechnetes Beispiel zwischen der Regel und der ersten
#: eigenen Aufgabe — die Regel allein reichte Kindern in der Erprobung nicht,
#: sie wollten vorher ein durchgerechnetes Beispiel mit Bild sehen.
WORKED_EXAMPLE_FRACTIONS = (Fraction(1, 3), Fraction(1, 6))

#: Wahl A bestätigt die Zielfehlvorstellung auch bei einer Zahl, die nicht
#: exakt der (Zähler+Zähler)/(Nenner+Nenner)-Rechnung entspricht (z. B.
#: Tippfehler) — die anderen Wahlen bekommen bewusst keine erfundene Diagnose.
DIAGNOSTIC_REASONING_MISCONCEPTION_CHOICE = "A"

REPRESENTATIONS = ("streifen", "pizza", "zahlenstrahl")

DIAGNOSTIC_TASK = (Fraction(1, 2), Fraction(1, 3))
GUIDED_TASK_FRACTIONS = (Fraction(1, 2), Fraction(1, 4))
INDEPENDENT_TASK_FRACTIONS = (Fraction(2, 3), Fraction(1, 6))

GUIDED_HINTS = (
    "Schau zuerst auf die Größe der Stücke.",
    "Kannst du Halbe und Viertel direkt zusammenzählen?",
    "Wie viele Viertel sind eine Hälfte?",
    "1/2 = 2/4 — also: 2/4 + 1/4 = 3/4.",
)

#: Feste Antworten für "Ich habe eine Frage" — bewusst kein LLM-Aufruf.
#: Deterministisch, kostenlos, sofort da, und stellt sicher, dass ein Kind
#: hier nie eine unpassende oder unsichere Antwort bekommen kann. Auf jedem
#: Bildschirm verfügbar, ohne den Lernfortschritt zu verändern.
HELP_FAQ = (
    ("Was ist der Zähler, was ist der Nenner?",
     "Der Nenner ist die untere Zahl. Er sagt, in wie viele gleich große "
     "Stücke das Ganze geteilt ist. Der Zähler ist die obere Zahl. Er sagt, "
     "wie viele dieser Stücke gemeint sind."),
    ("Was heißt „gemeinsamer Nenner“?",
     "Eine Nennerzahl, die zu beiden Brüchen passt. Du machst aus beiden "
     "Brüchen gleich große Stücke — erst dann kannst du sie zusammenzählen."),
    ("Wie tippe ich meine Antwort?",
     "Schreib den Bruch als Zahl/Zahl, zum Beispiel 3/4. Kommt am Ende eine "
     "ganze Zahl heraus, reicht auch einfach 1."),
    ("Ich weiß gerade nicht, was ich tun soll.",
     "Kein Problem. Schau dir die Bilder oben noch einmal an, oder klick "
     "auf „Hinweis“, wenn es gerade einen gibt. Du kannst auch einfach "
     "etwas ausprobieren — Karo merkt sich deinen Fortschritt."),
)

#: Zweite, ausführlichere Erklärung pro Bildschirm für „Das habe ich nicht
#: verstanden“. Bewusst andere Worte als der Bildschirm selbst — eine
#: wörtliche Wiederholung hilft einem Kind nicht, das genau diese Worte
#: gerade nicht verstanden hat. Erklärt die Aufgabe, verrät aber bei den
#: Übungen nicht das Ergebnis (dafür gibt es die Hinweisstufen).
EXPLAIN_MORE = {
    "ANCHOR": {
        "text":
            "Eine ganze Pizza wird in zwei gleich große Stücke geschnitten. "
            "Jede Person bekommt eins davon — also ein Stück von zwei. Man "
            "schreibt das 1/2. Du kannst „die Hälfte“ oder „1/2“ eintippen.",
        "bilder": [("So sieht eine ganze Pizza aus", 1, 1),
                   ("Und das ist die Hälfte davon: 1 Stück von 2", 1, 2)],
    },
    "DIAGNOSTIC": {
        "text":
            "Hier zählt noch nicht, ob du richtig liegst — Karo möchte nur "
            "sehen, wie du bis jetzt denkst. Tipp einfach, was dir logisch "
            "vorkommt, als Bruch geschrieben, zum Beispiel 5/6.",
        "bilder": [("1/2 heißt: ein Stück von zwei", 1, 2),
                   ("1/3 heißt: ein Stück von drei", 1, 3)],
    },
    "DIAGNOSTIC_REASONING": {
        "text":
            "Karo will nur wissen, welchen Weg du gerechnet hast — nicht, ob "
            "er stimmt. Wähl das aus, was am ehesten passt.",
        "bilder": [("Darum ging es: 1/2 …", 1, 2), ("… plus 1/3", 1, 3)],
    },
    "CONFLICT": {
        "text":
            "Denk wieder an die Pizza: Du hast schon ein halbes Stück auf dem "
            "Teller und bekommst noch etwas dazu. Wenn etwas dazukommt, kann "
            "am Ende unmöglich weniger auf dem Teller liegen als vorher. "
            "Genau darum geht es bei der Frage.",
        "bilder": [("Das hattest du schon: 1/2", 1, 2),
                   ("Dazu kommt noch: 1/3", 1, 3),
                   ("So viel wäre 2/5 — weniger als 1/2 ganz allein", 2, 5)],
    },
    "PREDICTION": {
        "text":
            "Stell dir vor, du schneidest ein halbes Stück Pizza noch einmal "
            "in drei kleinere Teile. Du hast dann mehr Teile auf dem Teller "
            "— aber isst du deswegen mehr Pizza? Rate erst, dann zeigt Karo "
            "es dir.",
        "bilder": [("Eine Hälfte", 1, 2),
                   ("Dieselbe Hälfte, nur kleiner geschnitten", 3, 6)],
    },
    "VISUAL_DISCOVERY": {
        "text":
            "Die farbigen Kästchen zeigen, wie viel von einer ganzen Pizza "
            "gemeint ist. Beide Streifen sind gleich breit — sie stehen für "
            "dieselbe ganze Pizza. Oben ist sie in zwei Stücke geteilt, "
            "unten in drei. Die Stücke sind also unterschiedlich groß, "
            "deshalb kann man sie noch nicht zusammenzählen.",
        "bilder": [("1/2 — ein Stück von zwei", 1, 2),
                   ("1/3 — ein Stück von drei", 1, 3)],
    },
    "DISCOVERY": {
        "text":
            "Beide Pizzen sind jetzt in 6 gleich große Stücke geteilt. Die "
            "Hälfte sind 3 von diesen 6 Stücken, ein Drittel sind 2 davon. "
            "Es ist genauso viel Pizza wie vorher — nur anders geschnitten.",
        "bilder": [("1/2 sind 3 von 6 Stücken", 3, 6),
                   ("1/3 sind 2 von 6 Stücken", 2, 6),
                   ("Zusammen: 5 von 6 Stücken", 5, 6)],
    },
    "RULE": {
        "text":
            "Kurz gesagt: 1/2 und 1/3 sind verschieden große Stücke. "
            "Verschieden große Stücke kann man nicht direkt zusammenzählen. "
            "Deshalb rechnet man beide erst in dieselbe Stückgröße um (hier: "
            "Sechstel) und zählt danach nur noch, wie viele Stücke es "
            "zusammen sind.",
        "bilder": [("So geht es nicht: 1/2 …", 1, 2), ("… und 1/3", 1, 3),
                   ("So geht es: beide als Sechstel, 3/6 + 2/6 = 5/6", 5, 6)],
    },
    "WORKED_EXAMPLE": {
        "text":
            "Nochmal ganz langsam: 1/3 heißt ein Stück von drei. 1/6 heißt "
            "ein Stück von sechs — Sechstel sind also kleiner. In ein Drittel "
            "passen genau zwei Sechstel, darum ist 1/3 dasselbe wie 2/6. "
            "Jetzt sind beide in Sechsteln: 2 Stück plus 1 Stück sind 3 Stück "
            "von sechs, also 3/6. Und 3 von 6 Stücken ist genau die Hälfte.",
        "bilder": [("1/3 …", 1, 3), ("… ist dasselbe wie 2/6", 2, 6),
                   ("dazu 1/6", 1, 6),
                   ("zusammen 3/6 — also die Hälfte", 3, 6)],
    },
    "GUIDED_TASK": {
        "text":
            "Die Aufgabe heißt: Du hast ein halbes Stück und ein "
            "Viertelstück. Bevor du rechnest, müssen beide gleich groß sein. "
            "Schau im Bild, wie oft ein Viertel in eine Hälfte passt. "
            "Brauchst du mehr Hilfe, klick auf „Hinweis“.",
        "bilder": [("1/2 — ein Stück von zwei", 1, 2),
                   ("1/4 — ein Stück von vier", 1, 4)],
    },
    "ADAPTATION": {
        "text":
            "Das Bild zeigt dieselbe Aufgabe noch einmal anders. Schau, wie "
            "groß das eine Stück im Vergleich zum anderen ist — passt das "
            "kleinere mehrmals in das größere?",
        "bilder": [("1/2", 1, 2), ("1/4", 1, 4)],
    },
    "INDEPENDENT_TASK": {
        "text":
            "Die Aufgabe heißt: 2 Stück von drei plus 1 Stück von sechs. "
            "Mach zuerst beide Stückgrößen gleich, dann zähl sie zusammen. "
            "Diesmal ohne Hinweise — probier es ruhig aus, Fehler sind hier "
            "erlaubt.",
        "bilder": [("2/3 — zwei Stück von drei", 2, 3),
                   ("1/6 — ein Stück von sechs", 1, 6)],
    },
    "TRANSFER": {
        "text":
            "Hier musst du gar nicht rechnen. Überleg nur: Bei B kommt zu "
            "1/2 noch etwas dazu. Kann etwas weniger werden, wenn man etwas "
            "dazugibt?",
        "bilder": [("A: 1/2", 5, 10),
                   ("B: 1/2 und noch 1/5 dazu", 7, 10)],
    },
    "FINAL_RETRIEVAL": {
        "text":
            "Denk an alles, was du gerade gemacht hast. Was musstest du jedes "
            "Mal als Erstes tun, bevor du zwei Brüche zusammenzählen "
            "konntest?",
        "bilder": [("Verschieden große Stücke — so geht es nicht", 1, 3),
                   ("Gleich große Stücke — so geht es", 2, 6)],
    },
}


def initial_state() -> dict:
    return {
        "phase": "ANCHOR",
        "error": None,
        "anchor_answer": None,
        "diagnostic_attempts": 0,
        "diagnostic_raw": None,
        "diagnostic_classification": None,
        "diagnostic_reasoning_choice": None,
        "misconception": None,
        "conflict_answer": None,
        "prediction_answer": None,
        "discovery_answers": [],
        "active_representation": "streifen",
        "representations_used": [],
        "guided_attempts": 0,
        "guided_last_classification": None,
        "hint_level": 0,
        "guided_success": False,
        "independent_attempts": 0,
        "independent_success": False,
        "transfer_attempts": 0,
        "transfer_reasoning": "",
        "transfer_success": False,
        "final_retrieval_success": False,
    }


# --------------------------------------------------------------------------
# Diagnose — rein deterministisch, keine KI
# --------------------------------------------------------------------------

def parse_fraction(raw: Optional[str]) -> Optional[Fraction]:
    if raw is None:
        return None
    text = raw.strip().replace(" ", "").replace(",", ".")
    if not text:
        return None
    try:
        if "/" in text:
            num_s, _, den_s = text.partition("/")
            return Fraction(int(num_s), int(den_s))
        return Fraction(text)
    except (ValueError, ZeroDivisionError):
        return None


def classify(raw: Optional[str], a: Fraction, b: Fraction) -> tuple[str, Optional[Fraction]]:
    """Ordnet eine Antwort einer von vier Kategorien zu.

    correct | misconception (Zähler+Nenner getrennt addiert) |
    other_wrong_answer | invalid
    """
    parsed = parse_fraction(raw)
    if parsed is None:
        return "invalid", None
    if parsed == a + b:
        return "correct", parsed
    wrong_add = Fraction(a.numerator + b.numerator, a.denominator + b.denominator)
    if parsed == wrong_add:
        return "misconception", parsed
    return "other_wrong", parsed


def next_representation(used: list[str]) -> str:
    for rep in REPRESENTATIONS:
        if rep not in used:
            return rep
    return REPRESENTATIONS[-1]


def is_mastery(state: dict) -> bool:
    """Beherrschung erfordert alle drei Erfolge — ein Treffer reicht nicht."""
    return bool(state.get("guided_success") and state.get("independent_success")
               and state.get("transfer_success"))


# --------------------------------------------------------------------------
# Übergänge — jede Funktion nimmt das Zustands-Dict entgegen und mutiert +
# liefert es zurück. Der Server (Router) ist die einzige Quelle der Wahrheit;
# der Browser sendet nie eine Phase, nur Antworten.
# --------------------------------------------------------------------------

def advance_anchor(state: dict, answer: str) -> dict:
    state["anchor_answer"] = (answer or "").strip()
    state["phase"] = "DIAGNOSTIC"
    return state


def submit_diagnostic(state: dict, raw: str) -> dict:
    """Ordnet die Diagnoseantwort zu.

    Ungültige Eingaben zählen nicht als Lernversuch und bleiben auf
    DIAGNOSTIC. Nur die Zielfehlvorstellung (2/5) führt direkt in den
    kognitiven Konflikt — jede andere falsche Zahl fragt erst nach dem
    Rechenweg, statt eine Fehlvorstellung zu unterstellen, die Karo gar
    nicht kennt.
    """
    classification, _ = classify(raw, *DIAGNOSTIC_TASK)
    if classification == "invalid":
        state["error"] = "invalid_fraction"
        return state
    state["error"] = None
    state["diagnostic_attempts"] += 1
    state["diagnostic_raw"] = raw.strip()
    state["diagnostic_classification"] = classification
    if classification == "correct":
        state["misconception"] = None
        state["phase"] = "RULE"
    elif classification == "misconception":
        state["misconception"] = "adds_numerators_and_denominators"
        state["phase"] = "CONFLICT"
    else:
        state["misconception"] = None
        state["phase"] = "DIAGNOSTIC_REASONING"
    return state


def submit_diagnostic_reasoning(state: dict, choice: str) -> dict:
    """Nur Wahl A bestätigt die Zielfehlvorstellung; B/C/D bekommen keine
    erfundene Diagnose, sondern führen neutral weiter zur Regel."""
    state["diagnostic_reasoning_choice"] = choice
    if choice == DIAGNOSTIC_REASONING_MISCONCEPTION_CHOICE:
        state["misconception"] = "adds_numerators_and_denominators"
        state["diagnostic_classification"] = "misconception"
        state["phase"] = "CONFLICT"
    else:
        state["misconception"] = "other"
        state["phase"] = "RULE"
    return state


def submit_conflict(state: dict, answer: str) -> dict:
    state["conflict_answer"] = answer
    state["phase"] = "PREDICTION"
    return state


def submit_prediction(state: dict, choice: str) -> dict:
    state["prediction_answer"] = choice
    state["phase"] = "VISUAL_DISCOVERY"
    return state


def submit_visual_discovery(state: dict) -> dict:
    if "streifen" not in state["representations_used"]:
        state["representations_used"].append("streifen")
    state["active_representation"] = "streifen"
    state["phase"] = "DISCOVERY"
    return state


def submit_discovery(state: dict, answer: str) -> dict:
    state["discovery_answers"].append(answer)
    if len(state["discovery_answers"]) >= 2:
        state["phase"] = "RULE"
    return state


def submit_rule(state: dict) -> dict:
    state["phase"] = "WORKED_EXAMPLE"
    return state


def submit_worked_example(state: dict) -> dict:
    state["phase"] = "GUIDED_TASK"
    return state


def submit_guided(state: dict, raw: str) -> dict:
    classification, _ = classify(raw, *GUIDED_TASK_FRACTIONS)
    if classification == "invalid":
        state["error"] = "invalid_fraction"
        return state
    state["error"] = None
    state["guided_attempts"] += 1
    if classification == "correct":
        state["guided_success"] = True
        state["guided_last_classification"] = classification
        state["phase"] = "INDEPENDENT_TASK"
        return state
    repeated_misconception = (classification == "misconception"
                              and state["guided_last_classification"] == "misconception")
    state["guided_last_classification"] = classification
    if repeated_misconception:
        used = state["representations_used"]
        nxt = next_representation(used)
        if nxt not in used:
            used.append(nxt)
        state["active_representation"] = nxt
        state["phase"] = "ADAPTATION"
    return state


def submit_adaptation(state: dict) -> dict:
    state["hint_level"] = 0
    state["phase"] = "GUIDED_TASK"
    return state


def request_hint(state: dict) -> dict:
    if state["phase"] == "GUIDED_TASK":
        state["hint_level"] = min(state["hint_level"] + 1, len(GUIDED_HINTS))
    return state


def submit_independent(state: dict, raw: str) -> dict:
    classification, _ = classify(raw, *INDEPENDENT_TASK_FRACTIONS)
    if classification == "invalid":
        state["error"] = "invalid_fraction"
        return state
    state["error"] = None
    state["independent_attempts"] += 1
    if classification == "correct":
        state["independent_success"] = True
        state["phase"] = "TRANSFER"
    return state


def submit_transfer(state: dict, choice: str, reasoning: str = "") -> dict:
    state["transfer_attempts"] += 1
    state["transfer_reasoning"] = (reasoning or "").strip()
    if choice == "B":
        state["transfer_success"] = True
        state["phase"] = "FINAL_RETRIEVAL"
    return state


def submit_final_retrieval(state: dict, choice: str) -> dict:
    if choice == "A" and is_mastery(state):
        state["final_retrieval_success"] = True
        state["phase"] = "COMPLETE"
    return state
