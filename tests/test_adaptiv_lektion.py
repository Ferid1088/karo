"""Meilenstein 2 — die Mathematik-Vertikale, Ende zu Ende.

Gruppe B aus 03_INVARIANTS.md plus der Weg, den die „definition of done“
beschreibt: bekannte falsche Antwort → benannte Fehlvorstellung → Erklärung
aus dem Katalog ohne Erzeugung → Übung → Wiederholung → Beherrschung bzw.
Eskalation, und das alles übersteht ein Neuladen.
"""
import re

from .conftest import csrf_from
from .test_app import einrichten, kind_modus_aktivieren

PFAD = "/lernen/adaptiv"


def _kind(client, fake_llm, app_env):
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True)
    kind_modus_aktivieren(client)
    token = csrf_from(client.get(PFAD).text)
    # Es gibt keinen stillen Einstieg mehr: erst die Lektion wählen.
    client.post(f"{PFAD}/start", data={"_csrf": token, "thema": "brueche"})
    return token


def _post(client, token, weg, **daten):
    return client.post(f"{PFAD}/{weg}", data={"_csrf": token, **daten})


def _bis_zur_gefuehrten_aufgabe(client, token, diagnose="2/5"):
    """Anker → Diagnose mit bekannter Fehlvorstellung → Haken → Regel →
    Beispiel → geführte Aufgabe."""
    _post(client, token, "anker", antwort="die Hälfte")
    seite = _post(client, token, "diagnose", antwort=diagnose)
    seite = _post(client, token, "vorhersage", antwort="groesser")
    seite = _post(client, token, "weiter")          # HOOK  → RULE
    seite = _post(client, token, "weiter")          # RULE  → WORKED_EXAMPLE
    return _post(client, token, "weiter")           # → GUIDED_TASK


def _phase(app_env):
    return app_env.db.q1(
        "SELECT zustand, phase, runden, versuche FROM lern_sitzung "
        "ORDER BY id DESC LIMIT 1")


# --------------------------------------------------------------------------
# B1 — Phasenablauf
# --------------------------------------------------------------------------

def test_reihenfolge_regel_beispiel_gefuehrte_aufgabe(client, fake_llm,
                                                      fake_cli, app_env):
    """B1: RULE → WORKED_EXAMPLE → GUIDED_TASK ist die tatsächliche Folge."""
    from app.adaptiv import sitzung as zustand

    token = _kind(client, fake_llm, app_env)
    _post(client, token, "anker", antwort="die Hälfte")
    _post(client, token, "diagnose", antwort="2/5")
    assert _phase(app_env)["phase"] == zustand.HOOK
    _post(client, token, "vorhersage", antwort="groesser")

    _post(client, token, "weiter")
    assert _phase(app_env)["phase"] == zustand.RULE
    _post(client, token, "weiter")
    assert _phase(app_env)["phase"] == zustand.WORKED_EXAMPLE
    _post(client, token, "weiter")
    assert _phase(app_env)["phase"] == zustand.GUIDED_TASK


def test_beispiel_hat_andere_zahlen_als_die_gefuehrte_aufgabe(client, fake_llm,
                                                              fake_cli, app_env):
    """B1: Sonst schreibt das Kind die Lösung einfach ab."""
    from app.adaptiv import inhalt_store, inhalte_brueche, store

    einrichten(client, fake_llm)
    konzept_id = inhalte_brueche.saeen()
    for fehlertyp in store.fehlertypen(konzept_id):
        beispiel = inhalt_store.aufgabe(fehlertyp["id"], inhalt_store.BEISPIEL)
        gefuehrt = inhalt_store.aufgabe(fehlertyp["id"], inhalt_store.GEFUEHRT)
        assert beispiel["frage"] != gefuehrt["frage"]
        assert beispiel["loesung"] != gefuehrt["loesung"]


def test_gefuehrte_aufgabe_zeigt_ihre_brueche_sofort(client, fake_llm,
                                                     fake_cli, app_env):
    """B1: Das Bild ist von Anfang an da, nicht erst nach zwei Fehlversuchen."""
    token = _kind(client, fake_llm, app_env)
    seite = _bis_zur_gefuehrten_aufgabe(client, token)

    assert "1/2 + 1/4" in seite.text
    haupt = seite.text.split("Das habe ich nicht verstanden")[0]
    assert 'class="strip"' in haupt


def test_selbststaendige_aufgabe_zeigt_kein_bild(client, fake_llm, fake_cli,
                                                 app_env):
    """B1: Ohne Bild — genau das ist die Prüfung.

    Die Phase hat zwei Schirme (Rechnung, dann Transfer). B1 gilt für die
    Phase, also für beide — sonst könnte jemand dem Transfer ein Bild geben,
    ohne dass eine Prüfung anschlägt.
    """
    from app.adaptiv import sitzung as zustand

    token = _kind(client, fake_llm, app_env)
    _bis_zur_gefuehrten_aufgabe(client, token)

    rechnung = _post(client, token, "aufgabe", antwort="3/4")
    assert "2/3 + 1/6" in rechnung.text

    transfer = _post(client, token, "aufgabe", antwort="5/6")
    assert "Was ist größer" in transfer.text
    assert _phase(app_env)["phase"] == zustand.INDEPENDENT_TASK

    for schirm in (rechnung, transfer):
        haupt = schirm.text.split("Das habe ich nicht verstanden")[0]
        assert 'class="strip"' not in haupt
        assert 'class="numberline"' not in haupt
        assert 'class="area"' not in haupt


def test_adaptation_zeigt_eine_andere_darstellung(client, fake_llm, fake_cli,
                                                  app_env):
    """B1: Nach einem Fehlversuch nicht dasselbe Bild noch einmal."""
    from app.adaptiv import sitzung as zustand

    token = _kind(client, fake_llm, app_env)
    _bis_zur_gefuehrten_aufgabe(client, token)
    seite = _post(client, token, "aufgabe", antwort="2/6")   # dieselbe Fehlvorstellung

    assert _phase(app_env)["phase"] == zustand.ADAPTATION

    # Nicht derselbe Streifen noch einmal, sondern eine andere Komponente.
    haupt = seite.text.split("Das habe ich nicht verstanden")[0]
    assert 'class="numberline"' in haupt
    assert 'class="strip"' not in haupt


# --------------------------------------------------------------------------
# B2 — Streifen korrekt zeichnen
# --------------------------------------------------------------------------

def test_streifen_sind_immer_gleich_breit(client, fake_llm, fake_cli, app_env):
    """B2: Der wichtige Test — ein Drittel darf nicht breiter aussehen als
    eine Hälfte, sonst widerspricht das Bild dem Begriff."""
    token = _kind(client, fake_llm, app_env)
    seite = client.get(PFAD)

    assert ".strip{display:flex" in seite.text.replace(" ", "")
    assert re.search(r"\.adaptiv \.strip\{[^}]*width:20rem", seite.text)
    assert re.search(r"\.adaptiv \.piece\{[^}]*flex:1 1 0", seite.text)
    # Keine feste Breite am einzelnen Stück.
    assert not re.search(r"\.adaptiv \.piece\{[^}]*width:\d", seite.text)


def test_jeder_streifen_hat_eine_vorlesbare_beschriftung(client, fake_llm,
                                                         fake_cli, app_env):
    """B2: Jeder gezeichnete Streifen ist beschriftet."""
    token = _kind(client, fake_llm, app_env)
    seite = _bis_zur_gefuehrten_aufgabe(client, token)

    streifen = re.findall(r'<div class="strip"([^>]*)>', seite.text)
    assert streifen
    assert all('role="img"' in s and "aria-label=" in s for s in streifen)


def test_jeder_streifen_ist_rechnerisch_moeglich(client, fake_llm, fake_cli,
                                                 app_env):
    """B2: 0 <= gefüllt <= gesamt und gesamt > 0 — für jedes gezeichnete Bild."""
    token = _kind(client, fake_llm, app_env)
    seite = _bis_zur_gefuehrten_aufgabe(client, token)

    paare = re.findall(r'aria-label="(\d+) von (\d+) gleich großen Stücken"',
                       seite.text)
    assert paare
    for gefuellt, gesamt in paare:
        assert int(gesamt) > 0
        assert 0 <= int(gefuellt) <= int(gesamt)


def test_streifen_entstehen_nur_an_einer_stelle(client, fake_llm, fake_cli,
                                                app_env):
    """B2: Genau ein Makro zeichnet Streifen — keine Kopie in einem anderen
    Template."""
    from pathlib import Path

    vorlagen = Path("app/templates")
    erzeuger = [p.name for p in vorlagen.glob("*.html")
                if 'class="piece' in p.read_text(encoding="utf-8")]
    assert erzeuger == ["adaptiv.html"]
    quelle = (vorlagen / "adaptiv.html").read_text(encoding="utf-8")
    assert quelle.count('<div class="piece') == 1


# --------------------------------------------------------------------------
# B3 — Hilfe ist überall da
# --------------------------------------------------------------------------

def test_jede_phase_ausser_complete_hat_erklaer_mehr(client, fake_llm,
                                                     fake_cli, app_env):
    """B3: Jede Phase hat einen Eintrag, und jeder Eintrag hat ein Bild."""
    from app.adaptiv import inhalt_store, inhalte_brueche, sitzung as zustand

    einrichten(client, fake_llm)
    konzept_id = inhalte_brueche.saeen()

    for phase in zustand.PHASEN:
        if phase == zustand.COMPLETE:
            continue
        eintrag = inhalt_store.hilfe_fuer_phase(konzept_id, phase)
        assert eintrag, f"keine Erklärung für {phase}"
        assert eintrag["bilder"], f"kein Bild für {phase}"
        for _, gefuellt, gesamt in eintrag["bilder"]:
            assert gesamt > 0 and 0 <= gefuellt <= gesamt


def test_erklaer_mehr_wiederholt_nicht_den_bildschirmtext(client, fake_llm,
                                                          fake_cli, app_env):
    """B3: Denselben Satz noch einmal zu lesen hilft niemandem — geprüft für
    JEDE Phase, nicht nur für zwei."""
    from app.adaptiv import inhalt_store, inhalte_brueche, sitzung as zustand

    einrichten(client, fake_llm)
    konzept_id = inhalte_brueche.saeen()

    e = inhalte_brueche.ERKLAERUNGEN["zaehler-und-nenner-addiert"]
    beispiel = " ".join(s["text"] for s in inhalte_brueche.BEISPIEL["schritte"])
    bildschirmtext = {
        zustand.HOOK: " ".join([e["haken"], e["erkenntnis"],
                                inhalte_brueche.VORHERSAGE["frage"],
                                inhalte_brueche.VORHERSAGE["aufloesung"]]),
        zustand.RULE: " ".join([e["regel"], e["bild"]["bleibt_gleich"]]),
        zustand.WORKED_EXAMPLE: beispiel,
        zustand.GUIDED_TASK: " ".join(
            [inhalte_brueche.GEFUEHRT["frage"]] + inhalte_brueche.GEFUEHRT["tipps"]),
        zustand.INDEPENDENT_TASK: " ".join(
            [inhalte_brueche.SELBSTSTAENDIG["frage"],
             inhalte_brueche.TRANSFER["frage"]]
            + inhalte_brueche.SELBSTSTAENDIG["tipps"]),
        zustand.ADAPTATION: " ".join([e["bild"]["zeigt"],
                                      e["bild"]["bleibt_gleich"]]),
    }
    # Jede Phase außer COMPLETE ist abgedeckt.
    assert set(bildschirmtext) == set(zustand.PHASEN) - {zustand.COMPLETE}

    for phase, text in bildschirmtext.items():
        hilfe = inhalt_store.hilfe_fuer_phase(konzept_id, phase)["text"]
        assert hilfe not in text, phase
        assert text not in hilfe, phase


# --------------------------------------------------------------------------
# A7 — Privatsphäre
# --------------------------------------------------------------------------

def test_kein_anbieteraufruf_und_keine_kinderantwort_im_protokoll(
        client, fake_llm, fake_cli, app_env, caplog):
    """A7, soweit hier anwendbar.

    Es gibt in dieser Lektion keinen Anbieteraufruf, also auch nichts zu
    schwärzen — der Rest von A7 (Schwärzen vor dem Aufruf, Audit-Eintrag)
    wird erst prüfbar, wenn Tier 3 in Meilenstein 4 wirklich ein Modell ruft.
    Was hier schon gilt: die Rohantwort des Kindes gehört nicht ins
    Anwendungsprotokoll. In der Datenbank steht sie bewusst — ohne sie gäbe
    es keinen Lernverlauf.
    """
    import logging

    token = _kind(client, fake_llm, app_env)
    fake_llm.calls.clear()
    with caplog.at_level(logging.DEBUG):
        _bis_zur_gefuehrten_aufgabe(client, token, diagnose="2/5")
        _post(client, token, "aufgabe", antwort="2/6")

    assert fake_llm.calls == []
    protokoll = " ".join(eintrag.getMessage() for eintrag in caplog.records)
    for rohantwort in ("2/5", "2/6", "die Hälfte"):
        assert rohantwort not in protokoll

    # In der Sitzung selbst ist sie erhalten, sonst wäre kein Verlauf möglich.
    assert app_env.db.q1(
        "SELECT letzte_antwort FROM lern_sitzung ORDER BY id DESC LIMIT 1"
    )["letzte_antwort"]


def test_erklaer_mehr_verraet_die_loesung_nicht(client, fake_llm, fake_cli,
                                                app_env):
    """B3: Auf Übungsschirmen erklärt die Hilfe die Aufgabe, nicht die Antwort —
    dafür gibt es die Tippstufen."""
    from app.adaptiv import inhalt_store, inhalte_brueche, sitzung as zustand

    einrichten(client, fake_llm)
    konzept_id = inhalte_brueche.saeen()

    for phase, loesung in ((zustand.GUIDED_TASK, "3/4"),
                           (zustand.INDEPENDENT_TASK, "5/6")):
        hilfe = inhalt_store.hilfe_fuer_phase(konzept_id, phase)
        assert loesung not in hilfe["text"]


def test_hilfe_ist_in_jeder_phase_erreichbar(client, fake_llm, fake_cli,
                                             app_env):
    """B3: In jeder Phase außer COMPLETE — auch mitten in einer Aufgabe."""
    token = _kind(client, fake_llm, app_env)

    for seite in (client.get(PFAD),
                  _post(client, token, "anker", antwort="die Hälfte"),
                  _post(client, token, "diagnose", antwort="2/5"),
                  _post(client, token, "vorhersage", antwort="groesser"),
                  _post(client, token, "weiter"),
                  _post(client, token, "weiter"),
                  _post(client, token, "weiter")):
        assert "Das habe ich nicht verstanden" in seite.text
        assert "Ich habe eine andere Frage" in seite.text


# --------------------------------------------------------------------------
# B4 — Hilfe ändert nichts
# --------------------------------------------------------------------------

def test_hilfe_kann_den_zustand_gar_nicht_aendern(client, fake_llm, fake_cli,
                                                  app_env):
    """B4: Die Hilfe ist reines Aufklappen — sie schickt nichts an den Server,
    kann also Phase, Versuche, Beherrschung und Tipps nicht verändern."""
    token = _kind(client, fake_llm, app_env)
    seite = _bis_zur_gefuehrten_aufgabe(client, token)
    vorher = dict(_phase(app_env))

    for block in re.findall(r"<details[^>]*>(.*?)</details>", seite.text,
                            re.S):
        assert "<form" not in block
        assert "/lernen/adaptiv/" not in block

    assert dict(_phase(app_env)) == vorher


# --------------------------------------------------------------------------
# Der Weg Ende zu Ende
# --------------------------------------------------------------------------

def test_bekannte_falsche_antwort_fuehrt_zur_katalogerklaerung(
        client, fake_llm, fake_cli, app_env):
    """Definition of done: Fehlvorstellung benannt, Erklärung aus dem Katalog
    geladen — ohne jede Erzeugung."""
    token = _kind(client, fake_llm, app_env)
    _post(client, token, "anker", antwort="die Hälfte")
    fake_llm.calls.clear()

    seite = _post(client, token, "diagnose", antwort="2/5")

    # HOOK fragt ZUERST nach einer Vorhersage — und zeigt dabei die beiden
    # Brüche (02 §1: visual support „the two fractions“).
    haupt = seite.text.split("Das habe ich nicht verstanden")[0]
    assert "größer oder kleiner" in haupt
    assert 'class="strip"' in haupt
    assert "kleiner als das halbe Stück" not in haupt

    # Erst nach der Vorhersage wird der Widerspruch sichtbar.
    seite = _post(client, token, "vorhersage", antwort="groesser")
    assert "wer etwas dazubekommt, hat danach mehr" in seite.text.lower()
    assert "2/5" in seite.text

    sitzung = app_env.db.q1("SELECT * FROM lern_sitzung ORDER BY id DESC LIMIT 1")
    fehlertyp = app_env.db.q1("SELECT * FROM lern_fehlertyp WHERE id=?",
                              sitzung["fehlertyp_id"])
    assert fehlertyp["fehler_key"] == "zaehler-und-nenner-addiert"
    assert sitzung["erklaerung_id"]
    assert fake_llm.calls == []


def test_richtige_antworten_fuehren_zu_beherrschung(client, fake_llm, fake_cli,
                                                    app_env):
    """Eine richtige Antwort reicht nicht, zwei schon (A8)."""
    from app.adaptiv import sitzung as zustand

    token = _kind(client, fake_llm, app_env)
    _bis_zur_gefuehrten_aufgabe(client, token)

    _post(client, token, "aufgabe", antwort="3/4")
    assert _phase(app_env)["zustand"] == zustand.TEACHING

    # Die Rechnung allein schließt die Lektion NICHT ab — der Transfer fehlt.
    seite = _post(client, token, "aufgabe", antwort="5/6")
    assert _phase(app_env)["zustand"] == zustand.TEACHING
    assert "Was ist größer" in seite.text

    seite = _post(client, token, "transfer", antwort="B")
    assert _phase(app_env)["zustand"] == zustand.MASTERED
    assert "verstanden" in seite.text

    fortschritt = app_env.db.q1("SELECT * FROM lern_fortschritt ORDER BY id DESC LIMIT 1")
    assert fortschritt["mastery"] == "sicher"
    assert fortschritt["erfolge"] == 3


def test_gekuerzte_antwort_zaehlt_als_richtig(client, fake_llm, fake_cli,
                                              app_env):
    """6/8 ist dieselbe Antwort wie 3/4."""
    from app.adaptiv import sitzung as zustand

    token = _kind(client, fake_llm, app_env)
    _bis_zur_gefuehrten_aufgabe(client, token)
    _post(client, token, "aufgabe", antwort="6/8")

    assert _phase(app_env)["phase"] == zustand.INDEPENDENT_TASK


def test_drei_fehlversuche_eskalieren_im_browser(client, fake_llm, fake_cli,
                                                 app_env):
    """A5 auf dem echten Weg: danach wird nichts mehr erklärt."""
    from app.adaptiv import sitzung as zustand

    token = _kind(client, fake_llm, app_env)
    _bis_zur_gefuehrten_aufgabe(client, token)

    for _ in range(3):
        seite = _post(client, token, "aufgabe", antwort="2/6")
        if _phase(app_env)["zustand"] != zustand.ESCALATED:
            _post(client, token, "weiter")       # aus der Adaptation zurück

    assert _phase(app_env)["zustand"] == zustand.ESCALATED
    assert "liegt nicht an dir" in seite.text
    assert "Prüfen" not in seite.text

    fortschritt = app_env.db.q1("SELECT * FROM lern_fortschritt ORDER BY id DESC LIMIT 1")
    assert fortschritt["braucht_mensch"] == 1


def test_neuladen_setzt_an_derselben_stelle_fort(client, fake_llm, fake_cli,
                                                 app_env):
    """A6 auf dem echten Weg."""
    from app.adaptiv import sitzung as zustand

    token = _kind(client, fake_llm, app_env)
    _bis_zur_gefuehrten_aufgabe(client, token)
    assert _phase(app_env)["phase"] == zustand.GUIDED_TASK

    seite = client.get(PFAD)
    assert "1/2 + 1/4" in seite.text
    assert _phase(app_env)["phase"] == zustand.GUIDED_TASK


def test_unbekannte_antwort_erfindet_keine_fehlvorstellung(client, fake_llm,
                                                           fake_cli, app_env):
    """A4: Lieber nachfragen als eine Diagnose erfinden."""
    token = _kind(client, fake_llm, app_env)
    _post(client, token, "anker", antwort="die Hälfte")
    fake_llm.calls.clear()

    seite = _post(client, token, "diagnose", antwort="9/11")

    sitzung = app_env.db.q1("SELECT * FROM lern_sitzung ORDER BY id DESC LIMIT 1")
    assert sitzung["fehlertyp_id"] is None
    assert sitzung["zustand"] == "DIAGNOSING"
    assert "Interessant" in seite.text
    assert fake_llm.calls == []


def test_ohne_schalter_bleibt_alles_beim_alten(client, fake_llm, fake_cli,
                                               app_env):
    """§16: Abgeschaltet ist die Route nicht erreichbar, der Rest unberührt."""
    einrichten(client, fake_llm)
    kind_modus_aktivieren(client)

    antwort = client.get(PFAD, follow_redirects=False)
    assert antwort.status_code == 303
    assert antwort.headers["location"] == "/lernen"
    assert app_env.db.q("SELECT * FROM lern_sitzung") == []


# --------------------------------------------------------------------------
# Was es noch nicht gibt, wird gesagt — nicht stillschweigend ersetzt
# --------------------------------------------------------------------------

def test_einstieg_zeigt_die_vorhandenen_lernreihen(client, fake_llm, fake_cli,
                                                   app_env):
    """Ohne Themenwahl startet nichts von selbst."""
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True)
    kind_modus_aktivieren(client)

    seite = client.get(PFAD)
    assert "Woran möchtest du arbeiten" in seite.text
    assert "Brüche mit verschiedenen Nennern addieren" in seite.text
    assert app_env.db.q("SELECT * FROM lern_sitzung") == []


def test_unbekanntes_thema_startet_nicht_heimlich_die_bruchlektion(
        client, fake_llm, fake_cli, app_env):
    """Der eigentliche Punkt: Karo tut nicht so, als könnte es alles.

    Vorher lieferte die Route immer die Bruchlektion, egal welches Thema
    gemeint war. Das sah nach einem allgemeinen System aus und war keines.
    """
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True)
    kind_modus_aktivieren(client)
    token = csrf_from(client.get(PFAD).text)

    seite = client.post(f"{PFAD}/start",
                        data={"_csrf": token, "thema": "Photosynthese"})

    assert "noch keine Lernreihe" in seite.text
    assert "Photosynthese" in seite.text
    # Vor allem: keine Sitzung, kein Anker, keine Brüche.
    assert app_env.db.q("SELECT * FROM lern_sitzung") == []
    assert "1/2 + 1/3" not in seite.text


def test_passendes_thema_startet_die_richtige_lernreihe(client, fake_llm,
                                                        fake_cli, app_env):
    """„Bruchrechnung“ findet die Bruchlektion — ohne Modell, per Stichwort."""
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True)
    kind_modus_aktivieren(client)
    token = csrf_from(client.get(PFAD).text)

    seite = client.post(f"{PFAD}/start",
                        data={"_csrf": token, "thema": "Bruchrechnung"})

    assert "Pizza" in seite.text
    sitzung = app_env.db.q1("SELECT * FROM lern_sitzung ORDER BY id DESC LIMIT 1")
    assert sitzung["zustand"] == "DIAGNOSING"


def test_das_eingetippte_thema_wird_festgehalten(client, fake_llm, fake_cli,
                                                 app_env):
    """§13: Die Eingabe ist der Anfang der Kette, nicht nur ein Klick."""
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True)
    kind_modus_aktivieren(client)
    token = csrf_from(client.get(PFAD).text)
    client.post(f"{PFAD}/start", data={"_csrf": token, "thema": "Bruchrechnung"})

    eingabe = app_env.db.q1("SELECT * FROM lern_eingabe ORDER BY id DESC LIMIT 1")
    assert eingabe["thema_text"] == "Bruchrechnung"
    assert eingabe["art"] == "manuell"
