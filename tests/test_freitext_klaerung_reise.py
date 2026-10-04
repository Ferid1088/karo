"""Real-Canary der Freitext-Reise — kein Modell, nur der Lehrpfad.

Eine ganze Lektion mit begriffe-Rubrik, Fehlvorstellung und Klaerung geht
durch `erzeugung.speichern` (die Pruefkette) in den Katalog. Dann faehrt
die Sitzung die echten Weichen in `unterricht.py`:

  unklare Antwort → Klaerungsschirm → Option → Resume
  Teilantwort     → gezielter Hinweis statt Wiederholung
  Widerspruch     → Fehlvorstellung schlaegt den korrekten Kern

Das ist der Laufzeitbeweis zu test_freitext_rubrik.py: dort die Matrix,
hier die Reise.
"""
from __future__ import annotations

import json

FACH = "biologie"

_BILD = {"component": "ConceptMap",
         "parameters": {"knoten": ["Zelle", "Mitochondrium"],
                        "kanten": []},
         "animation": "none"}
_VIS_ALT = {"component": "GenericStepFlow",
            "parameters": {"schritte": ["Sauerstoff kommt an",
                                        "Glucose wird abgebaut",
                                        "Energie wird frei"]},
            "animation": "none"}

_RUBRIK = {
    "begriffe": [["sauerstoff", "o2", "sauerstoff wird aufgenommen"],
                 ["glucose", "traubenzucker"],
                 ["energie", "atp"]],
    "mindestens": 3,
    "hinweise": {"teilweise": "Da fehlt noch ein Teil der Zellatmung.",
                 "unbekannt": "Ich kann deine Antwort noch nicht einordnen."},
    "missverstaendnisse": [{
        "begriffe": ["lunge", "lungen"],
        "key": "F1",
        "hinweis": "Zellatmung laeuft in jeder Zelle — nicht nur in der Lunge."}],
    "klaerung": {
        "frage": "Welche Aussage beschreibt die Zellatmung am besten?",
        "loesung": "Zellen gewinnen aus Zucker und Sauerstoff Energie",
        "optionen": [
            "Zellen gewinnen aus Zucker und Sauerstoff Energie",
            "Nur die Lunge tauscht Gase aus",
            "Pflanzen atmen nicht"],
    },
}


def _aufgabe(frage: str, loesung: str, **extra) -> dict:
    return {"frage": frage, "loesung": loesung, **extra}


def _lektion() -> dict:
    """Minimal vollstaendige Lektion — genug, dass `pruefe_lektion` sie
    annimmt und der Unterricht Material in jeder Rolle findet."""
    freitext = _aufgabe(
        "Erklaere in eigenen Worten, was bei der Zellatmung passiert.",
        "Zellen nehmen Sauerstoff auf, bauen Glucose ab und setzen "
        "Energie frei.",
        antwort_art="begriffe", rubrik=_RUBRIK)
    rechnung = _aufgabe(
        "Wie heisst der Stoff, den die Zelle dabei abbaut?", "Glucose")
    auswahl = _aufgabe(
        "Wo findet Zellatmung statt?",
        "In den Mitochondrien jeder Zelle",
        optionen=["In den Mitochondrien jeder Zelle",
                  "Nur in der Lunge", "Im Magen"],
        aufloesung="Jede Zelle atmet selbst.")
    fehler = {
        "key": "F1", "label": "Zellatmung nur in der Lunge",
        "beschreibung": "Denkt, nur die Lunge atmet.",
        "antworten": ["nur in der lunge", "in der lunge"],
        "erklaerung": {
            "haken": "Atmen tun wir mit der Lunge — atmen Zellen auch?",
            "erkenntnis": "Jede Zelle holt sich ihre Energie selbst, "
                          "die Lunge liefert nur den Sauerstoff heran.",
            "regel": "Zellatmung = Glucose plus Sauerstoff wird zu "
                     "Energie, Wasser und Kohlendioxid.",
            "bild": {"zeigt": "eine Zelle mit Mitochondrium",
                     "bewegt": "Sauerstoff wandert hinein",
                     "bleibt_gleich": "die Zelle selbst"},
            "aufgabe": {"frage": "Wo wird Energie frei?",
                        "loesung": "im Mitochondrium"},
        },
        "visualisierung": _BILD,
        "visualisierung_alternativ": _VIS_ALT,
        "aufgaben": {
            "vorhersage": auswahl,
            "beispiel": rechnung,
            "gefuehrt": {**freitext,
                         "typischer_fehler": "nur in der Lunge"},
            "selbststaendig": {**freitext,
                               "typischer_fehler": "nur in der Lunge"},
            "transfer": auswahl,
        },
    }
    return {
        "konzept": {"konzept_key": "test.zellatmung",
                    "thema_key": "test.bio", "label": "Zellatmung",
                    "klasse_von": 7, "klasse_bis": 7,
                    "stichworte": ["zellatmung"]},
        "fehlertypen": [fehler],
        "hilfe": {phase: {"text": f"Hilfe fuer {phase}."}
                  for phase in ("HOOK", "RULE", "WORKED_EXAMPLE",
                                "GUIDED_TASK", "INDEPENDENT_TASK",
                                "ADAPTATION")},
        "faq": [{"frage": "Brauchen Pflanzen Sauerstoff?",
                 "antwort": "Ja, auch Pflanzenzellen atmen."},
                {"frage": "Ist das dasselbe wie Lungenatmung?",
                 "antwort": "Nein, die Lunge versorgt nur mit Sauerstoff."}],
        "erstkontakt": {
            "anker": "Woher bekommt dein Muskel beim Sport Energie?",
            "erste_aufgabe": freitext,
            "benennung": "das, was in deinen Zellen passiert",
        },
    }


def _setup(app_env) -> int:
    app_env.db.init()
    from app.adaptiv import erzeugung, store
    store.init()
    return erzeugung.speichern(_lektion(), FACH, quelle="test")


def _daten(sitzung: dict) -> dict:
    roh = sitzung.get("daten")
    return dict(json.loads(roh) if isinstance(roh, str) else (roh or {}))


def test_klaerung_reise_unbekannt_option_resume(app_env):
    """UNKNOWN → Klaerungsschirm → richtige Option → normaler Pfad weiter."""
    from app.adaptiv import store, unterricht
    from app.adaptiv import protokoll

    konzept_id = _setup(app_env)
    s = unterricht.starte(konzept_id, "Zellatmung")
    s = unterricht.anker_beantwortet(s, "keine Ahnung")

    # 1. Unklare Freitextantwort → nicht falsch, sondern Klaerung.
    s = unterricht.diagnose_beantwortet(s, "hmm vielleicht irgendwas")
    daten = _daten(store.sitzung(s["id"]))
    assert daten.get("klaerung"), daten
    assert daten["klaerung"]["frage"] == _RUBRIK["klaerung"]["frage"]

    schirm = unterricht.bildschirm(store.sitzung(s["id"]))
    assert schirm["art"] == "klaerung"
    assert schirm["aktion"] == "diagnose"
    optionen = [o[0] for o in schirm["optionen"]]
    assert _RUBRIK["klaerung"]["loesung"] in optionen

    # 2. Die Klaerung wird lokal bewertet; eine richtige Option setzt die
    #    Diagnose fort — als haette das Kind die Frage selbst beantwortet.
    s = store.sitzung(s["id"])
    s = unterricht.diagnose_beantwortet(s, _RUBRIK["klaerung"]["loesung"])
    daten = _daten(s)
    assert not daten.get("klaerung"), "Klaerung muss verbraucht sein"
    # Richtige Klaerung zaehlt wie eine richtige Diagnoseantwort: es geht
    # zur Kontrollaufgabe oder weiter — nicht zur Fehlvorstellung.
    assert s["zustand"] in ("DIAGNOSING", "TEACHING", "MASTERED"), \
        s["zustand"]

    # 3. Protokoll zeigt beide Ereignisse — der Befund ist nachvollziehbar.
    from app import db
    arten = {r["anlass"] for r in db.q(
        "SELECT anlass FROM lern_ereignis WHERE sitzung_id = ?",
        s["id"])}
    assert "Klaerung gestellt" in arten
    assert "Klaerung beantwortet" in arten


def test_klaerung_falsche_option_geht_in_lernpfad(app_env):
    """Eine falsche Klaerungsoption ist eine normale falsche Antwort —
    kein Dead End, kein Modellaufruf."""
    from app.adaptiv import store, unterricht

    konzept_id = _setup(app_env)
    s = unterricht.starte(konzept_id, "Zellatmung")
    s = unterricht.anker_beantwortet(s, "")
    s = unterricht.diagnose_beantwortet(s, "irgendwas")
    assert _daten(store.sitzung(s["id"])).get("klaerung")

    s = store.sitzung(s["id"])
    s = unterricht.diagnose_beantwortet(s, "Pflanzen atmen nicht")
    daten = _daten(s)
    assert not daten.get("klaerung")
    # Falsch eingeordnet → der allgemeine Lernpfad greift (Hinweis oder
    # Fehlertyp), die Sitzung laeuft weiter.
    assert s["zustand"] in ("DIAGNOSING", "TEACHING", "ESCALATED")


def test_widerspruch_schlaegt_vollstaendige_antwort(app_env):
    """Korrekte Begriffe + Fehlvorstellung im selben Satz: nie richtig."""
    from app.adaptiv import katalog, store, unterricht
    from app.adaptiv.antwortvergleich import bewerte, RICHTIG

    konzept_id = _setup(app_env)
    # Aufgabe direkt aus dem Katalog — derselbe Rubrik-Eintrag, den der
    # Unterricht spaeter bewertet.
    erste = (katalog.erstkontakt_fuer(konzept_id) or {}).get(
        "erste_aufgabe") or {}
    befund = bewerte(
        "Sauerstoff wird aufgenommen, Glucose wird abgebaut und "
        "Energie wird frei — aber das passiert nur in der Lunge.",
        erste.get("loesung"), erste.get("antwort_art"),
        erste.get("rubrik"))
    assert befund["urteil"] != RICHTIG
    assert befund.get("missverstaendnis") == "F1"

    s = unterricht.starte(konzept_id, "Zellatmung")
    s = unterricht.anker_beantwortet(s, "")
    s = unterricht.diagnose_beantwortet(
        s, "Sauerstoff wird aufgenommen, Glucose wird abgebaut, "
           "Energie wird frei, aber nur in der Lunge")
    assert s["zustand"] != "MASTERED"
    # Der widerspruechliche Kern wurde nicht als richtig gebucht — und das
    # Urteil samt Fehlvorstellung steht lesbar in der Antwortzeile, damit die
    # Auswertung spaeter Fragen wie „welche Erklaerung wirkt nicht?" beantworten
    # kann, ohne Rohantworten erneut zu deuten.
    from app import db
    zeile = db.q1(
        "SELECT richtig, urteil, missverstaendnis FROM lern_antwort "
        "WHERE sitzung_id = ? ORDER BY id DESC LIMIT 1", s["id"])
    assert zeile is not None and zeile["richtig"] != 1
    assert zeile["urteil"] == "falsch"
    assert zeile["missverstaendnis"] == "F1"


def test_teilantwort_zielt_auf_fehlenden_teil(app_env):
    """PARTIAL nennt den fehlenden Begriff — die Nachhilfe ist gezielt."""
    from app.adaptiv import katalog, store, unterricht
    from app.adaptiv.antwortvergleich import bewerte, TEILWEISE

    konzept_id = _setup(app_env)
    erste = (katalog.erstkontakt_fuer(konzept_id) or {}).get(
        "erste_aufgabe") or {}
    befund = bewerte("Die Zelle braucht Sauerstoff.",
                     erste.get("loesung"), erste.get("antwort_art"),
                     erste.get("rubrik"))
    assert befund["urteil"] == TEILWEISE
    fehlende = " ".join(befund.get("fehlende") or []).lower()
    assert "glucose" in fehlende
    assert "sauerstoff" not in fehlende

    s = unterricht.starte(konzept_id, "Zellatmung")
    s = unterricht.anker_beantwortet(s, "")
    s = unterricht.diagnose_beantwortet(s, "Die Zelle braucht Sauerstoff.")
    assert s["zustand"] != "MASTERED"
    # `richtig` allein koennte 'teilweise' nicht von 'falsch' trennen —
    # die Zeile traegt das Urteil.
    from app import db
    zeile = db.q1(
        "SELECT urteil FROM lern_antwort WHERE sitzung_id = ? "
        "ORDER BY id DESC LIMIT 1", s["id"])
    assert zeile is not None and zeile["urteil"] == "teilweise"


def test_klaerung_kein_modellaufruf(fake_llm, app_env):
    """Die ganze Reise — unbekannt, Klaerung, Bewertung — ruft nie ein
    Modell. Der Fake-Anbieter zaehlt jeden Aufruf."""
    from app.adaptiv import store, unterricht

    konzept_id = _setup(app_env)
    s = unterricht.starte(konzept_id, "Zellatmung")
    s = unterricht.anker_beantwortet(s, "")
    s = unterricht.diagnose_beantwortet(s, "keine Ahnung")
    s = store.sitzung(s["id"])
    s = unterricht.diagnose_beantwortet(s, _RUBRIK["klaerung"]["loesung"])
    assert fake_llm.calls == []
