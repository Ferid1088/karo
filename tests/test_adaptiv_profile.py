"""Adversariale Kind-Profile, Dead-End-Scanner und Resilienz.

Der Scanner stellt die UI-Invariante sicher: jeder Bildschirm, den die
Domain erzeugen kann, hat einen anklickbaren Lernschritt — ein Screen
ohne Weiter ist ein Dead End. Die Profile fahren echte Antwortketten
durch die Domain: das starke Kind, das Karo nicht uebertrainieren darf;
das inkonsistente, das Mastery erst durch den Transfer bekommt; das
Kind, das pausiert und denselben Stand wiederfindet; und das Kind, das
antwortet, ohne dass der Katalog seinen Fehler kennt.
"""
import re
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / "app" / "templates" / "adaptiv.html"

# Schirme ohne eigenen Block landen im generischen Zweig der Vorlage —
# dort gibt es immer „Mit Karo weitermachen", Pause und Hilfe.
FALLBACK_ARTEN = {"inhalt_fehlt", "unbekannt"}


def _bloecke() -> dict[str, str]:
    """Die `schirm.art`-Zweige der Vorlage: Name → Template-Text.

    Ein Zweig endet am naechsten `elif schirm.art` oder am `{% else %}` der
    Kette — verschachtelte `{% if %}`/`{% endif %}` im Zweig selbst bleiben
    Teil des Blocks.
    """
    quelle = TEMPLATE.read_text(encoding="utf-8")
    marken = list(re.finditer(
        r"{%\s*(?:el)?if schirm\.art == '(\w+)'.*?%}", quelle))
    else_marke = re.search(r"{%\s*else\s*%}", quelle[marken[-1].start():])
    kette_ende = (marken[-1].start() + else_marke.start()) \
        if else_marke else len(quelle)
    bloecke = {}
    for i, marke in enumerate(marken):
        naechste = marken[i + 1].start() if i + 1 < len(marken) else kette_ende
        bloecke[marke.group(1)] = quelle[marke.end():naechste]
    return bloecke


def test_jede_bildschirmart_bietet_eine_aktion(app_env):
    """Kein Kern-Lernscreen ist nur Text: jeder Zweig hat ein Formular
    oder einen Link — ein Screen ohne Weiter wäre ein Dead End."""
    bloecke = _bloecke()
    assert bloecke, "keine schirm.art-Zweige gefunden — Template geändert?"
    for art, koerper in bloecke.items():
        assert ('method="post"' in koerper or 'class="btn' in koerper), \
            f"Bildschirm '{art}' bietet dem Kind nichts Klickbares"


def test_fallback_zweig_bietet_weiter(app_env):
    """Der generische Zweig (unbekannt/inhalt_fehlt) bleibt ein Lernweg:
    Weitermachen ist die primaere Aktion, nicht der Ausstieg."""
    quelle = TEMPLATE.read_text(encoding="utf-8")
    else_teil = quelle.rsplit("{% else %}", 1)[-1]
    assert "/fortsetzen" in else_teil
    assert "weitermachen" in else_teil


def test_jede_domain_art_hat_einen_schirm(app_env):
    """Was `unterricht` als Bildschirmart ausgibt, muss die Vorlage
    rendern koennen — sonst zeigt sie einen Schirm ohne Sinn."""
    quelle = (Path(__file__).resolve().parents[1]
              / "app" / "adaptiv" / "unterricht.py").read_text("utf-8")
    ausgegeben = set(re.findall(r'"art":\s*"(\w+)"', quelle))
    gerendert = set(_bloecke()) | FALLBACK_ARTEN
    assert ausgegeben <= gerendert, \
        f"ohne Bildschirm: {sorted(ausgegeben - gerendert)}"


def test_next_action_kennt_keinen_dead_end(app_env):
    """Die Entscheidungsschicht liefert fuer jede erreichbare
    Zustand-Phase-Kombination eine Lernaktion — GIVE_UP gibt es nicht."""
    from app.adaptiv import naechste_aktion, sitzung as zustand
    zustaende = [zustand.INPUT_RECEIVED, zustand.MATERIAL_ANALYZED,
                 zustand.DIAGNOSING, zustand.ERROR_IDENTIFIED,
                 zustand.TEACHING, zustand.MASTERED, zustand.ESCALATED]
    phasen = [None, zustand.HOOK, zustand.RULE, zustand.WORKED_EXAMPLE,
              zustand.GUIDED_TASK, zustand.INDEPENDENT_TASK,
              zustand.ADAPTATION, zustand.COMPLETE]
    bekannte = {v for k, v in vars(naechste_aktion).items()
                if k.isupper() and isinstance(v, str)}
    for name in zustaende:
        for phase in phasen:
            for fehlertyp in (None, 7):
                schritt = naechste_aktion.fuer(
                    {"zustand": name, "phase": phase,
                     "fehlertyp_id": fehlertyp, "daten": {}})
                assert schritt.get("aktion") in bekannte, \
                    f"{name}/{phase}: {schritt}"
                assert "GIVE_UP" not in bekannte


# --------------------------------------------------------------------------
# Adversariale Profile — echte Antwortketten durch die Domain
# --------------------------------------------------------------------------

def _lernraum(key: str = "PROFIL"):
    """Ein geprueftes Konzept mit der ganzen Leiter: Erstkontakt mit
    Kontrollfrage, Fehlertyp mit Alias, Erklaerung und Aufgaben in jeder
    Rolle — zwei selbststaendige auf verschiedenen Stufen."""
    from app.adaptiv import inhalt_store, store
    from app.adaptiv.normalisierung import normalisiere
    kid = store.konzept_sichern("mathematik", "profil", key, key,
                                geprueft=True)
    ft = store.fehlertyp_sichern(kid, f"{key}-ft", f"{key} falsch",
                                 geprueft=True)
    # Typische Fehlvorstellung als Zahl-Alias (z. B. „Nenner addiert“):
    # sie sieht wie eine plausible Antwort aus und landet im Katalog.
    store.alias_sichern(ft, normalisiere("5"))
    store.erstkontakt_anlegen(
        kid, "Was fällt dir dazu ein?",
        {"frage": "Einstieg?", "loesung": "2", "antwort_art": "zahl",
         "bestaetigung": {"frage": "Kontrolle?", "loesung": "3",
                          "antwort_art": "zahl"}},
        f"{key} nennen", geprueft=True)
    store.erklaerung_anlegen(ft, 8, {"titel": key, "text": "Erklärung."},
                             geprueft=True)
    inhalt_store.aufgabe_sichern(ft, inhalt_store.VORHERSAGE, "Vorhersage?",
                                 "a", antwort_art="auswahl",
                                 optionen=["a", "b"])
    inhalt_store.aufgabe_sichern(ft, inhalt_store.BEISPIEL, "Beispiel?",
                                 "2", antwort_art="zahl")
    inhalt_store.aufgabe_sichern(ft, inhalt_store.GEFUEHRT, "Gemeinsam?",
                                 "2", tipps=["Erster Tipp"],
                                 schritte=["Schritt eins"], antwort_art="zahl")
    inhalt_store.aufgabe_sichern(ft, inhalt_store.SELBSTSTAENDIG, "Allein 1?",
                                 "2", schwierigkeit=1, position=0,
                                 antwort_art="zahl")
    inhalt_store.aufgabe_sichern(ft, inhalt_store.SELBSTSTAENDIG, "Allein 2?",
                                 "3", schwierigkeit=2, position=1,
                                 antwort_art="zahl")
    inhalt_store.aufgabe_sichern(ft, inhalt_store.TRANSFER, "Transfer?",
                                 "a", antwort_art="auswahl",
                                 optionen=["a", "b"])
    return kid, ft


def test_profil_stark_wird_nicht_uebertrainiert(app_env):
    """Profil A: beide Diagnosefragen richtig — Karo schliesst ab, statt
    Pflichtrunden zu verlangen. Danach waehlt das Kind, nicht das System."""
    app_env.db.init()
    from app.adaptiv import (inhalt_store, naechste_aktion, store,
                             sitzung as zustand, unterricht)
    store.init()
    kid, _ = _lernraum("STARK")

    s = unterricht.starte(kid, "Stark")
    s = unterricht.anker_beantwortet(s, "hmm")
    s = unterricht.diagnose_beantwortet(s, "2")
    assert s["zustand"] == zustand.DIAGNOSING       # ein Treffer reicht nicht
    s = unterricht.diagnose_beantwortet(s, "3")
    assert s["zustand"] == zustand.MASTERED

    # Keine Pflichtaufgabe mehr: nur die Terminwahl oder „verstanden".
    assert unterricht.bildschirm(s)["art"] in ("wiederholung_waehlen",
                                              "geschafft")
    assert naechste_aktion.fuer(s)["aktion"] == naechste_aktion.GESCHAFFT
    s2 = unterricht.fortsetzen(s)
    assert unterricht.bildschirm(s2)["art"] != "aufgabe"


def _bis_gefuehrt(s):
    """HOOK bis zur gefuehrten Aufgabe durchschreiten."""
    from app.adaptiv import unterricht
    s = unterricht.vorhersage_beantwortet(s, "a")
    for _ in range(3):
        s = unterricht.weiter(s)
    return s


def test_profil_inkonsistent_mastery_erst_durch_transfer(app_env):
    """Profil D: mal richtig, mal falsch. Jeder Fehler wechselt die
    Intervention, einzelne Erfolge reichen nicht — erst der Transfer
    nach den Erfolgen schliesst die Lernreise ab."""
    app_env.db.init()
    from app.adaptiv import store, sitzung as zustand, unterricht
    store.init()
    kid, ft = _lernraum("WACKEL")

    s = unterricht.starte(kid, "Wackel")
    s = unterricht.anker_beantwortet(s, "")
    s = unterricht.diagnose_beantwortet(s, "5")
    assert s["zustand"] == zustand.TEACHING
    assert s["fehlertyp_id"] == ft

    s = _bis_gefuehrt(s)
    assert s["phase"] == zustand.GUIDED_TASK
    s = unterricht.aufgabe_beantwortet(s, "2")         # gefuehrt richtig
    assert s["phase"] == zustand.INDEPENDENT_TASK

    s = unterricht.aufgabe_beantwortet(s, "99")        # allein falsch
    assert s["phase"] == zustand.ADAPTATION            # Intervention aendert sich
    s = unterricht.weiter_nach_adaptation(s)
    assert s["phase"] == zustand.GUIDED_TASK
    s = unterricht.aufgabe_beantwortet(s, "2")         # gefuehrt richtig
    assert s["phase"] == zustand.INDEPENDENT_TASK

    s = unterricht.aufgabe_beantwortet(s, "3")         # neue Aufgabe richtig
    assert s["zustand"] != zustand.MASTERED            # Transfer fehlt noch
    assert s["phase"] == zustand.INDEPENDENT_TASK
    s = unterricht.transfer_beantwortet(s, "a")
    assert s["zustand"] == zustand.MASTERED


def test_profil_genug_pause_und_resume(app_env):
    """Profil G: Pause ist eine Wahl — die Sitzung bleibt offen, und der
    Resume findet genau den Stand wieder, an dem das Kind aufhoerte."""
    app_env.db.init()
    from app.adaptiv import store, sitzung as zustand, unterricht
    store.init()
    kid, _ = _lernraum("PAUSE")

    s = unterricht.starte(kid, "Pause")
    s = unterricht.anker_beantwortet(s, "")
    s = unterricht.diagnose_beantwortet(s, "5")
    s = _bis_gefuehrt(s)
    store.ereignis_schreiben(s["id"], "Pause gewaehlt",
                           nutzdaten={"art": "heute"})

    # „Neustart": alles, was Karo braucht, steht in der Datenbank.
    wieder = unterricht.laufende_oder_neue(kid)
    assert wieder["id"] == s["id"]                     # dieselbe Sitzung
    assert wieder["zustand"] == zustand.TEACHING
    assert wieder["phase"] == zustand.GUIDED_TASK
    schirm = unterricht.bildschirm(wieder)
    assert schirm["art"] == "aufgabe"                  # genau da weiter


def test_profil_unbekannter_fehler_bleibt_lernweg(app_env):
    """Profil F: der Katalog kennt die falsche Antwort nicht — Hinweis,
    Loesungsweg, andere Aufgabe; danach Begleitung, die fortsetzbar ist."""
    app_env.db.init()
    from app.adaptiv import store, sitzung as zustand, unterricht
    store.init()
    kid, _ = _lernraum("UNBEKANNT")

    s = unterricht.starte(kid, "Unbekannt")
    s = unterricht.anker_beantwortet(s, "")
    for _ in range(4):
        s = unterricht.diagnose_beantwortet(s, "77")
    assert s["zustand"] == zustand.ESCALATED           # Begleitung, kein Ende
    assert unterricht.bildschirm(s)["art"] == "begleitung"

    s = unterricht.fortsetzen(s)                       # weiterlernen
    assert s["zustand"] == zustand.DIAGNOSING
    schirm = unterricht.bildschirm(s)
    assert schirm["art"] == "diagnose"
    assert schirm["frage"] != "Einstieg?"              # eine ANDERE Aufgabe


def test_unterricht_ohne_dienst_und_ohne_anbieter(app_env):
    """Resilienz (Gate D): die Unterrichtsschicht kennt kein Netz und
    keinen Anbieter — ein Ausfall von Curriculum-Service oder
    LLM-Backend kann eine laufende Lernreise nicht stoppen."""
    paket = Path(__file__).resolve().parents[1] / "app" / "adaptiv"
    verboten = ("urllib", "httpx", "requests", "anthropic", "openai")
    for datei in paket.glob("*.py"):
        if datei.name == "curriculum_dienst.py":
            continue                                 # der Dienst-Client selbst
        quelle = datei.read_text("utf-8")
        for name in verboten:
            assert name not in quelle, f"{datei.name} spricht mit {name}"
