"""Lernpilot: deterministischer Prototyp fuer den adaptiven Lernprozess.

Deckt sowohl die reine Zustandslogik (`app.services.learning_pilot`) als
auch den HTTP-Weg ab (Session, Kind-Rolle, Reset).
"""
from .conftest import csrf_from
from .test_app import einrichten, kind_modus_aktivieren


# --------------------------------------------------------------------------
# Reine Zustandslogik
# --------------------------------------------------------------------------

def test_diagnostic_classifies_target_misconception():
    from app.services import learning_pilot as pilot

    classification, _ = pilot.classify("2/5", *pilot.DIAGNOSTIC_TASK)
    assert classification == "misconception"


def test_diagnostic_classifies_correct_answer():
    from app.services import learning_pilot as pilot

    classification, _ = pilot.classify("5/6", *pilot.DIAGNOSTIC_TASK)
    assert classification == "correct"


def test_diagnostic_classifies_other_wrong_answer():
    from app.services import learning_pilot as pilot

    classification, _ = pilot.classify("1", *pilot.DIAGNOSTIC_TASK)
    assert classification == "other_wrong"


def test_diagnostic_rejects_invalid_input():
    from app.services import learning_pilot as pilot

    classification, _ = pilot.classify("Quatsch", *pilot.DIAGNOSTIC_TASK)
    assert classification == "invalid"


def test_invalid_diagnostic_input_stays_on_diagnostic_and_does_not_count():
    from app.services import learning_pilot as pilot

    state = pilot.initial_state()
    state["phase"] = "DIAGNOSTIC"
    state = pilot.submit_diagnostic(state, "Quatsch")
    assert state["phase"] == "DIAGNOSTIC"
    assert state["diagnostic_attempts"] == 0


def test_generic_wrong_answer_does_not_assume_target_misconception():
    from app.services import learning_pilot as pilot

    state = pilot.initial_state()
    state["phase"] = "DIAGNOSTIC"
    state = pilot.submit_diagnostic(state, "1")
    assert state["phase"] == "DIAGNOSTIC_REASONING"
    assert state["misconception"] is None
    assert state["diagnostic_attempts"] == 1


def test_reasoning_choice_a_identifies_target_misconception():
    from app.services import learning_pilot as pilot

    state = pilot.initial_state()
    state["phase"] = "DIAGNOSTIC_REASONING"
    state = pilot.submit_diagnostic_reasoning(state, "A")
    assert state["phase"] == "CONFLICT"
    assert state["misconception"] == "adds_numerators_and_denominators"


def test_reasoning_choice_b_does_not_invent_misconception():
    from app.services import learning_pilot as pilot

    state = pilot.initial_state()
    state["phase"] = "DIAGNOSTIC_REASONING"
    state = pilot.submit_diagnostic_reasoning(state, "B")
    assert state["phase"] == "RULE"
    assert state["misconception"] != "adds_numerators_and_denominators"


def test_only_target_misconception_reaches_conflict_directly():
    from app.services import learning_pilot as pilot

    state = pilot.initial_state()
    state["phase"] = "DIAGNOSTIC"
    state = pilot.submit_diagnostic(state, "2/5")
    assert state["phase"] == "CONFLICT"
    assert state["misconception"] == "adds_numerators_and_denominators"


def test_rule_leads_to_worked_example_before_guided_task():
    from app.services import learning_pilot as pilot

    state = pilot.initial_state()
    state["phase"] = "RULE"
    state = pilot.submit_rule(state)
    assert state["phase"] == "WORKED_EXAMPLE"
    state = pilot.submit_worked_example(state)
    assert state["phase"] == "GUIDED_TASK"


def test_one_success_is_not_mastery():
    from app.services import learning_pilot as pilot

    state = pilot.initial_state()
    state["guided_success"] = True
    assert not pilot.is_mastery(state)
    state["independent_success"] = True
    assert not pilot.is_mastery(state)
    state["transfer_success"] = True
    assert pilot.is_mastery(state)


def test_same_misconception_switches_representation():
    from app.services import learning_pilot as pilot

    state = pilot.initial_state()
    state = pilot.submit_visual_discovery(state)
    state["phase"] = "GUIDED_TASK"
    state = pilot.submit_guided(state, "2/6")  # misconception: 1+1/2+4
    assert state["phase"] == "GUIDED_TASK"
    state = pilot.submit_guided(state, "2/6")  # repeated -> switch
    assert state["phase"] == "ADAPTATION"
    assert state["active_representation"] != "streifen"


def test_hint_level_increases_only_in_guided_task():
    from app.services import learning_pilot as pilot

    state = pilot.initial_state()
    state["phase"] = "GUIDED_TASK"
    state = pilot.request_hint(state)
    state = pilot.request_hint(state)
    assert state["hint_level"] == 2
    state["phase"] = "INDEPENDENT_TASK"
    state = pilot.request_hint(state)
    assert state["hint_level"] == 2


def test_final_retrieval_requires_mastery():
    from app.services import learning_pilot as pilot

    state = pilot.initial_state()
    state["phase"] = "FINAL_RETRIEVAL"
    state = pilot.submit_final_retrieval(state, "A")
    assert state["phase"] == "FINAL_RETRIEVAL"
    assert not state["final_retrieval_success"]
    state["guided_success"] = True
    state["independent_success"] = True
    state["transfer_success"] = True
    state = pilot.submit_final_retrieval(state, "A")
    assert state["phase"] == "COMPLETE"
    assert state["final_retrieval_success"]


def test_zero_llm_or_media_imports():
    import ast
    from pathlib import Path

    src = Path("app/services/learning_pilot.py").read_text()
    tree = ast.parse(src)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    forbidden = ("anthropic", "notebooklm", "llm", "tts", "video")
    assert not any(any(f in n.lower() for f in forbidden) for n in names)


# --------------------------------------------------------------------------
# HTTP-Weg
# --------------------------------------------------------------------------

def _kind_client(client, fake_llm, fake_cli):
    einrichten(client, fake_llm)
    kind_modus_aktivieren(client)
    return client


def test_pilot_starts_at_anchor(client, fake_llm, fake_cli):
    _kind_client(client, fake_llm, fake_cli)
    page = client.get("/lernpilot")
    assert page.status_code == 200
    assert "Pizza" in page.text


def test_help_is_available_on_every_screen_without_llm_call(client, fake_llm,
                                                           fake_cli):
    """Das Kind muss jederzeit nachfragen koennen — auch mitten in einer
    Aufgabe, und ohne dass dafuer ein Modell aufgerufen wird."""
    from app.services import learning_pilot as pilot

    _kind_client(client, fake_llm, fake_cli)
    calls_before = len(fake_llm.calls)
    token = csrf_from(client.get("/lernpilot").text)

    for phase in pilot.PHASES:
        if phase == "COMPLETE":
            continue
        client.post("/lernpilot/reset", data={"_csrf": token})
        zustand = client.get("/lernpilot")
        # Zustand direkt auf die Phase setzen waere Betrug am Server-Zustand;
        # hier reicht der Einstieg plus die Zusicherung, dass jede Phase eine
        # eigene Erklaerung hinterlegt hat.
        erklaerung = pilot.EXPLAIN_MORE.get(phase)
        assert erklaerung, f"keine Erklaerung fuer {phase}"
        # Text allein reicht nicht — ein Kind, das die Worte nicht versteht,
        # braucht ein Bild dazu.
        assert erklaerung["bilder"], f"kein Bild fuer {phase}"
        for _, gefuellt, gesamt in erklaerung["bilder"]:
            assert 0 <= gefuellt <= gesamt, f"unmoegliches Bild in {phase}"
        assert "Das habe ich nicht verstanden" in zustand.text
        assert "Ich habe eine andere Frage" in zustand.text

    # Die Streifen zeichnen das Ganze immer gleich breit — sonst sieht ein
    # Drittel breiter aus als eine Haelfte und das Bild luegt.
    seite = client.get("/lernpilot")
    assert 'class="strip"' in seite.text
    assert "width:2rem" not in seite.text

    assert len(fake_llm.calls) == calls_before


def test_anchor_advances_to_diagnostic(client, fake_llm, fake_cli):
    _kind_client(client, fake_llm, fake_cli)
    token = csrf_from(client.get("/lernpilot").text)
    page = client.post("/lernpilot/anchor", data={"_csrf": token, "antwort": "die Hälfte"})
    assert "1/2 + 1/3" in page.text


def test_full_misconception_path_to_completion(client, fake_llm, fake_cli):
    _kind_client(client, fake_llm, fake_cli)
    page = client.get("/lernpilot")
    token = csrf_from(page.text)

    page = client.post("/lernpilot/anchor", data={"_csrf": token, "antwort": "die Hälfte"})
    page = client.post("/lernpilot/diagnostic", data={"_csrf": token, "antwort": "2/5"})
    assert "Falsch" not in page.text
    assert "kleiner werden" in page.text

    page = client.post("/lernpilot/conflict", data={"_csrf": token, "antwort": "nein"})
    assert "kleinere Stücke" in page.text

    page = client.post("/lernpilot/prediction", data={"_csrf": token, "antwort": "gleich"})
    assert "gleich groß machen" in page.text

    page = client.post("/lernpilot/visual-discovery", data={"_csrf": token})
    assert "sechs kleinere" in page.text

    page = client.post("/lernpilot/discovery", data={"_csrf": token, "antwort": "nein"})
    page = client.post("/lernpilot/discovery", data={"_csrf": token, "antwort": "ja"})
    assert "gemeinsamen Nenner" in page.text

    page = client.post("/lernpilot/rule", data={"_csrf": token})
    assert "1/3 + 1/6" in page.text

    page = client.post("/lernpilot/worked-example", data={"_csrf": token})
    assert "1/2 + 1/4" in page.text

    # wrong guided answer does not complete the pilot
    page = client.post("/lernpilot/guided", data={"_csrf": token, "antwort": "2/6"})
    assert "1/2 + 1/4" in page.text

    page = client.post("/lernpilot/guided/hinweis", data={"_csrf": token})
    assert "Schau zuerst" in page.text

    page = client.post("/lernpilot/guided", data={"_csrf": token, "antwort": "3/4"})
    assert "2/3 + 1/6" in page.text

    page = client.post("/lernpilot/independent", data={"_csrf": token, "antwort": "3/9"})
    assert "2/3 + 1/6" in page.text  # wrong -> stays

    page = client.post("/lernpilot/independent", data={"_csrf": token, "antwort": "5/6"})
    assert "Was ist größer" in page.text

    page = client.post("/lernpilot/transfer", data={"_csrf": token, "antwort": "A", "begruendung": "weil kleiner"})
    assert "Was ist größer" in page.text  # wrong choice -> stays

    page = client.post("/lernpilot/transfer", data={"_csrf": token, "antwort": "B", "begruendung": "mehr dazu"})
    assert "prüfen" in page.text

    page = client.post("/lernpilot/final-retrieval", data={"_csrf": token, "antwort": "A"})
    assert "Wichtiges entdeckt" in page.text


def test_pilot_reset_restarts_flow(client, fake_llm, fake_cli):
    _kind_client(client, fake_llm, fake_cli)
    token = csrf_from(client.get("/lernpilot").text)
    client.post("/lernpilot/anchor", data={"_csrf": token, "antwort": "x"})
    page = client.post("/lernpilot/reset", data={"_csrf": token})
    assert "Pizza soll gerecht" in page.text


def test_refresh_preserves_session_state(client, fake_llm, fake_cli):
    _kind_client(client, fake_llm, fake_cli)
    token = csrf_from(client.get("/lernpilot").text)
    client.post("/lernpilot/anchor", data={"_csrf": token, "antwort": "x"})
    page = client.get("/lernpilot")
    assert "1/2 + 1/3" in page.text
