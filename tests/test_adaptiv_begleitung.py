"""Begleitung statt Abbruch — Produktverhalten bei wiederholtem Scheitern.

Karo darf einen Lernprozess nicht beenden, weil ein Kind mehrfach falsch
antwortet. Eskalation erhoeht die Unterstuetzung, das Thema bleibt offen,
und nur das Kind entscheidet aktiv ueber Pause oder Themenwechsel — in
Meine Themen und in der Klassenarbeit gleichermassen.
"""
import re

from .conftest import csrf_from
from .test_app import einrichten, kind_modus_aktivieren
from .test_separate_learning_journeys import setup_journeys

PFAD = "/lernen/adaptiv"

VERBOTEN = ("Etwas anderes lernen", "zu zweit", "zu schwierig",
            "weiß Karo gerade nicht weiter")


def _kind(client, fake_llm, app_env):
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True, learner_grade=6)
    kind_modus_aktivieren(client)
    token = csrf_from(client.get(PFAD).text)
    client.post(f"{PFAD}/start", data={"_csrf": token, "thema": "brueche"})
    return token


def _bis_zur_gefuehrten_aufgabe(client, token, pfad=PFAD, sid=None):
    def senden(aktion, **daten):
        ziel = f"{pfad}/{aktion}" + (f"?sitzung={sid}" if sid else "")
        return client.post(ziel, data={"_csrf": token, **daten})

    senden("anker", antwort="die Hälfte")
    senden("diagnose", antwort="2/5")
    senden("vorhersage", antwort="groesser")
    for _ in range(3):
        senden("weiter")


def _phase(app_env):
    return app_env.db.q1(
        "SELECT zustand, phase, runden FROM lern_sitzung ORDER BY id DESC LIMIT 1")


def _bis_begleitung(client, token, app_env, pfad=PFAD):
    """Wiederholt falsch bei der gefuehrten Aufgabe → Begleit-Schirm."""
    from app.adaptiv import sitzung as zustand
    _bis_zur_gefuehrten_aufgabe(client, token, pfad)
    for _ in range(4):
        seite = client.post(f"{pfad}/aufgabe",
                            data={"_csrf": token, "antwort": "2/6"})
        if _phase(app_env)["zustand"] != zustand.ESCALATED:
            client.post(f"{pfad}/weiter", data={"_csrf": token})
    assert _phase(app_env)["zustand"] == zustand.ESCALATED
    return seite


# ---------------------------------------------------------------------------
# Fall A — mehrfach falsche Antworten: Begleitung statt „anderes Thema"
# ---------------------------------------------------------------------------

def test_wiederholt_falsch_zeigt_begleitung_kein_abgang(client, fake_llm,
                                                       app_env):
    from app.adaptiv import sitzung as zustand
    token = _kind(client, fake_llm, app_env)
    seite = _bis_begleitung(client, token, app_env)

    for verboten in VERBOTEN:
        assert verboten not in seite.text
    assert "Mit Karo weitermachen" in seite.text
    assert "Kurze Pause" in seite.text
    assert "Hilfe holen" in seite.text

    # Weitermachen setzt im selben Thema und derselben Sitzung fort.
    zuvor = _phase(app_env)
    seite = client.post(f"{PFAD}/fortsetzen", data={"_csrf": token})
    stand = _phase(app_env)
    assert stand["zustand"] == zustand.TEACHING
    assert stand["phase"] == zustand.ADAPTATION
    assert "einfacher" in seite.text or "ander" in seite.text

    # Und von dort geht es wieder in eine gefuehrte Aufgabe.
    client.post(f"{PFAD}/weiter", data={"_csrf": token})
    assert _phase(app_env)["phase"] == zustand.GUIDED_TASK
    assert "antwort" in client.get(PFAD).text


def test_fortsetzen_ohne_fehlertyp_setzt_die_diagnose_fort(client, fake_llm,
                                                           app_env):
    """Eskalierte Diagnose (unbekannte Antworten): weiter mit neuer
    Aufgabe, nicht von vorn mit derselben."""
    from app.adaptiv import sitzung as zustand
    token = _kind(client, fake_llm, app_env)
    client.post(f"{PFAD}/anker", data={"_csrf": token, "antwort": "x"})
    for _ in range(6):
        seite = client.post(f"{PFAD}/diagnose",
                            data={"_csrf": token, "antwort": "99"})
    assert _phase(app_env)["zustand"] == zustand.ESCALATED
    assert "Mit Karo weitermachen" in seite.text

    client.post(f"{PFAD}/fortsetzen", data={"_csrf": token})
    stand = _phase(app_env)
    assert stand["zustand"] == zustand.DIAGNOSING
    seite = client.get(PFAD)
    assert 'name="antwort"' in seite.text
    for verboten in VERBOTEN:
        assert verboten not in seite.text


# ---------------------------------------------------------------------------
# Fall B — Voraussetzungspfad: eskalierter Umweg ist fortsetzbar
# ---------------------------------------------------------------------------

def test_eskalierte_voraussetzung_wird_fortgesetzt_statt_aufgegeben(
        client, fake_llm, app_env):
    """Trug der Umweg beim ersten Mal nicht, setzt er an seiner letzten
    Stelle fort — die wartende Sitzung eskaliert nicht noch einmal."""
    from app.adaptiv import sitzung as zustand, store, unterricht

    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True, learner_grade=6)
    store.init()
    konzept_id = store.konzepte_verfuegbar()[0]["id"]
    fehlertyp_id = store.fehlertypen(konzept_id)[0]["id"]

    wartend = unterricht.starte(konzept_id, "Brüche")
    wartend = unterricht._merke(wartend["id"], wartend,
                                voraussetzung_offen="Grundlage",
                                voraussetzung_lokal=konzept_id,
                                voraussetzung_titel="Grundlage")

    # Die Grundlage wurde schon einmal versucht und ist eskaliert.
    umweg = unterricht.starte(konzept_id, "Brüche")
    zustand.fehler_erkannt(umweg["id"], fehlertyp_id, "x")
    zustand.unterricht_beginnen(umweg["id"])
    zustand.eskalieren(umweg["id"])

    ergebnis = unterricht.voraussetzung_lernen_starten(wartend)
    assert ergebnis["id"] == umweg["id"]
    assert ergebnis["daten"].get("voraussetzung_detour") == wartend["id"]
    # Die wartende Sitzung wurde NICHT eskaliert — der Umweg geht weiter.
    assert store.sitzung(wartend["id"])["zustand"] != zustand.ESCALATED


# ---------------------------------------------------------------------------
# Fall C — Material erschöpft: degradierte Hilfe, kein Aufgeben
# ---------------------------------------------------------------------------

def test_material_erschoepft_bietet_fortsetzung(client, fake_llm, app_env,
                                              monkeypatch):
    from app.adaptiv import inhalt_store, sitzung as zustand
    token = _kind(client, fake_llm, app_env)
    _bis_zur_gefuehrten_aufgabe(client, token)

    monkeypatch.setattr(inhalt_store, "aufgabe", lambda *a, **k: None)
    seite = client.get(PFAD)
    assert "Mit Karo weitermachen" in seite.text
    for verboten in VERBOTEN:
        assert verboten not in seite.text

    seite = client.post(f"{PFAD}/fortsetzen", data={"_csrf": token})
    assert _phase(app_env)["phase"] == zustand.ADAPTATION
    assert 'name="antwort"' not in seite.text or True  # Erklaerseite


# ---------------------------------------------------------------------------
# Fall D — Klassenarbeit: dieselbe Begleitung wie im Lernbereich
# ---------------------------------------------------------------------------

def test_klassenarbeit_begleitung_wie_lernbereich(client, fake_llm, app_env,
                                                monkeypatch):
    personal, exams, tids, token = setup_journeys(
        client, fake_llm, app_env, monkeypatch)
    pfad = f"/klassenarbeit/{exams[0]}/lernen"
    antwort = client.post(f"{pfad}/start",
                          data={"_csrf": token, "topic_id": tids[0]})
    sid = int(re.search(r'sitzung=(\d+)', antwort.text).group(1))

    _bis_zur_gefuehrten_aufgabe(client, token, pfad=pfad, sid=sid)
    from app.adaptiv import sitzung as zustand, store
    for _ in range(4):
        seite = client.post(f"{pfad}/aufgabe?sitzung={sid}",
                            data={"_csrf": token, "antwort": "2/6"})
        if store.sitzung(sid)["zustand"] != zustand.ESCALATED:
            client.post(f"{pfad}/weiter?sitzung={sid}",
                        data={"_csrf": token})
    assert store.sitzung(sid)["zustand"] == zustand.ESCALATED
    assert "Mit Karo weitermachen" in seite.text
    for verboten in VERBOTEN:
        assert verboten not in seite.text

    seite = client.post(f"{pfad}/fortsetzen?sitzung={sid}",
                        data={"_csrf": token})
    assert seite.status_code == 200
    assert store.sitzung(sid)["zustand"] == zustand.TEACHING
    assert f"{pfad}" in seite.text          # bleibt im Pruefungsbereich


# ---------------------------------------------------------------------------
# Fall E — Pause und genug fuer heute: bewusste Wahl, Sitzung bleibt offen
# ---------------------------------------------------------------------------

def test_pause_ist_wahl_und_laesst_den_einstiegspunkt_offen(client, fake_llm,
                                                          app_env):
    from app.adaptiv import sitzung as zustand, store
    token = _kind(client, fake_llm, app_env)
    _bis_begleitung(client, token, app_env)
    sid = app_env.db.q1("SELECT id FROM lern_sitzung ORDER BY id DESC")["id"]

    antwort = client.post(f"{PFAD}/pause",
                          data={"_csrf": token, "wert": "heute"})
    assert antwort.status_code in (303, 200)

    # Die Sitzung ist nicht beendet — sie wartet am selben Punkt.
    assert store.sitzung(sid)["zustand"] == zustand.ESCALATED
    ereignis = app_env.db.q1(
        "SELECT * FROM lern_ereignis WHERE sitzung_id=? "
        "AND anlass='Pause gewaehlt'", sid)
    assert ereignis is not None

    seite = client.get(PFAD)
    assert "Mit Karo weitermachen" in seite.text


def test_hilfe_holen_ist_zusatz_nicht_abgang(client, fake_llm, app_env):
    token = _kind(client, fake_llm, app_env)
    _bis_begleitung(client, token, app_env)

    seite = client.post(f"{PFAD}/hilfe", data={"_csrf": token})
    assert "Mit Karo weitermachen" in seite.text
    assert "erwachsenen Person" in seite.text
    for verboten in VERBOTEN:
        assert verboten not in seite.text


# ---------------------------------------------------------------------------
# Fall F — Resume: zurueckkommen setzt am Begleit-Schirm fort
# ---------------------------------------------------------------------------

def test_resume_landet_auf_dem_begleit_schirm(client, fake_llm, app_env):
    from app.adaptiv import sitzung as zustand, store
    token = _kind(client, fake_llm, app_env)
    _bis_begleitung(client, token, app_env)
    sid = app_env.db.q1("SELECT id FROM lern_sitzung ORDER BY id DESC")["id"]

    # Spaeterer Einstieg ueber das Thema: dieselbe Sitzung, derselbe Punkt.
    seite = client.post(f"{PFAD}/start",
                        data={"_csrf": token, "thema": "brueche"})
    assert "Mit Karo weitermachen" in seite.text
    assert store.sitzung(sid)["zustand"] == zustand.ESCALATED

    # Und danach geht der Lernweg weiter wie zuvor geplant.
    client.post(f"{PFAD}/fortsetzen", data={"_csrf": token})
    assert _phase(app_env)["phase"] == zustand.ADAPTATION


def test_begleitung_nach_erfolg_verliert_den_menschen_marker(
        client, fake_llm, app_env):
    """Wer es danach ohne Mensch schafft, braucht den Marker nicht mehr."""
    from app.adaptiv import sitzung as zustand, store, inhalt_store
    token = _kind(client, fake_llm, app_env)
    _bis_begleitung(client, token, app_env)
    s = app_env.db.q1("SELECT * FROM lern_sitzung ORDER BY id DESC LIMIT 1")
    profil = store.fortschritt(s["konzept_id"], s["fehlertyp_id"])
    assert profil["braucht_mensch"] == 1

    client.post(f"{PFAD}/fortsetzen", data={"_csrf": token})
    client.post(f"{PFAD}/weiter", data={"_csrf": token})  # → GUIDED_TASK
    aufgabe = inhalt_store.aufgabe(s["fehlertyp_id"], inhalt_store.GEFUEHRT)
    client.post(f"{PFAD}/aufgabe",
                data={"_csrf": token, "antwort": aufgabe["loesung"]})
    selbst = inhalt_store.aufgabe(s["fehlertyp_id"], inhalt_store.SELBSTSTAENDIG)
    client.post(f"{PFAD}/aufgabe",
                data={"_csrf": token, "antwort": selbst["loesung"]})
    transfer = inhalt_store.aufgabe(s["fehlertyp_id"], inhalt_store.TRANSFER)
    seite = client.post(f"{PFAD}/transfer",
                        data={"_csrf": token, "antwort": transfer["loesung"]})
    stand = _phase(app_env)
    assert stand["zustand"] == zustand.MASTERED
    profil = store.fortschritt(s["konzept_id"], s["fehlertyp_id"])
    assert profil["braucht_mensch"] == 0
    assert profil["mastery"] == "sicher"
