"""SHARED CURRICULUM ≠ SHARED LEARNING STATE.

Ein Lernthema und ein Prüfungsthema dürfen denselben Namen tragen und auf
dieselbe Lektion zeigen — Inhalt, Erklärungen, Aufgaben und Validatoren
bleiben geteilt. Alles, was ein Kind an diesem Thema belegt, gehoert aber
nur diesem Thema: Mastery, Versuche, Wiederholungstermine, gesehene
Aufgaben, laufende Sitzungen und `braucht_mensch`.
"""
import pytest

from .test_app import einrichten
from .conftest import csrf_from


def _welt(app_env, label="Brüche mit verschiedenen Nennern addieren"):
    """Zwei Themen, ein Konzept: `lern` sichtbar, `pruefung` verborgen."""
    from app import topics as topic_modul
    from app.adaptiv import inhalte_brueche, store
    from app.services import exam, learning_hub

    app_env.db.init()
    store.init()
    konzept_id = inhalte_brueche.saeen()
    lern_id = learning_hub.create_topic(label, "mathematik", modell=False)
    eid = exam.create_exam("2027-10-15", manual_topics=label,
                           subject="Mathematik").exam_id
    exam_id = learning_hub.exam_topics(eid)[0]["id"]

    lern = topic_modul.get(lern_id)
    pruef = topic_modul.get(exam_id)
    assert lern["learning_visible"] == 1
    assert pruef["learning_visible"] == 0
    # Beide Themen duerfen auf dasselbe Konzept zeigen — das ist Absicht.
    from app.adaptiv import lektionen
    assert lektionen.fuer_thema(label, "mathematik")["konzept_id"] == konzept_id
    return konzept_id, lern_id, exam_id, eid


def _sitzung(konzept_id, label, topic_id):
    from app.adaptiv import unterricht
    s = unterricht.starte(konzept_id, label, topic_id)
    return unterricht.anker_beantwortet(s, "zwei Hälften")


# --------------------------------------------------------------------------
# Geteiltes Curriculum, getrennte Evidence — in beide Richtungen
# --------------------------------------------------------------------------

def _evidence(konzept_id, label, topic_id):
    """Eine Lerneinheit in einem Thema: Antwort, Termin, Mastery, Eskalation."""
    from app.adaptiv import (inhalt_store, protokoll,
                             sitzung as zustand, store, unterricht)

    s = _sitzung(konzept_id, label, topic_id)
    scope = store.fortschritt_scope(s)
    assert scope == f"installation:topic:{topic_id}"

    # Eine beantwortete Katalog-Aufgabe — „gesehen" zaehlt den Lernraum.
    fehlertypen = store.fehlertypen(konzept_id)
    fehlertyp = fehlertypen[0]
    aufgabe = inhalt_store.aufgabe(fehlertyp["id"],
                                   inhalt_store.SELBSTSTAENDIG)
    protokoll.antwort_buchen(s, protokoll.AUFGABE, aufgabe=aufgabe,
                             antwort=aufgabe["loesung"], richtig=True)

    # Wiederholungstermin und verfestigter Fortschritt nur in diesem Raum.
    unterricht.wiederholung_gewaehlt(s, 3)
    store.fortschritt_buchen(konzept_id, fehlertyp["id"], mastery="sicher",
                             child_key=scope)

    # `braucht_mensch` gehoert ebenfalls zum Thema, nicht zum Konzept —
    # auf einem anderen Fehlertyp, damit beide Signale nebeneinander stehen.
    zweite = _sitzung(konzept_id, label, topic_id)
    zustand.fehler_erkannt(zweite["id"], fehlertypen[-1]["id"], "2/5")
    zustand.unterricht_beginnen(zweite["id"], None, phase=zustand.HOOK)
    zustand.eskalieren(zweite["id"])
    return s, scope, aufgabe, fehlertypen


def _assert_evidence_nur_im_scope(konzept_id, aktiv, fremd, aufgabe,
                                  fehlertypen):
    from app.adaptiv import protokoll, store, wiederholung
    aktiv_scope = f"installation:topic:{aktiv}"
    fremd_scope = f"installation:topic:{fremd}"

    assert store.fortschritt(konzept_id, fehlertypen[0]["id"],
                             child_key=aktiv_scope)["mastery"] == "sicher"
    for fehlertyp in fehlertypen:
        assert store.fortschritt(konzept_id, fehlertyp["id"],
                                 child_key=fremd_scope) is None
    assert wiederholung.offen_fuer(konzept_id, aktiv_scope) is not None
    assert wiederholung.offen_fuer(konzept_id, fremd_scope) is None
    assert aufgabe["id"] in protokoll.gesehene_aufgaben(konzept_id, aktiv_scope)
    assert aufgabe["id"] not in protokoll.gesehene_aufgaben(
        konzept_id, fremd_scope)
    assert store.fortschritt(konzept_id, fehlertypen[-1]["id"],
                             child_key=aktiv_scope)["braucht_mensch"] == 1
    # Das Thema des anderen bleibt neu — kein Termin, kein Stand, keine
    # laufende Sitzung.
    assert store.topic_mastery(fremd) is None
    assert store.offene_fuer_thema(fremd) is None


def test_lernthema_und_pruefungsthema_teilen_kein_evidence(app_env):
    """A lernt → B bleibt unberuehrt. Danach umgekehrt, aus einer dritten,
    frischen Welt heraus nicht noetig: dieselben Asserts gelten symmetrisch,
    weil die Scopes gleich gebaut sind."""
    from app.adaptiv import store

    konzept_id, lern_id, exam_id, _ = _welt(app_env)
    label = store.konzept(konzept_id)["label"]
    s, scope, aufgabe, fehlertypen = _evidence(konzept_id, label, lern_id)

    _assert_evidence_nur_im_scope(konzept_id, lern_id, exam_id, aufgabe,
                                fehlertypen)
    # Die Antwortzeile traegt den Themen-Scope, nicht nur 'installation'.
    antwort = app_env.db.q1(
        "SELECT scope FROM lern_antwort WHERE sitzung_id=? AND rolle='aufgabe'",
        s["id"])
    assert antwort["scope"] == scope


def test_umgekehrt_pruefungsthema_allein_laesst_lernthema_neu(app_env):
    from app.adaptiv import store

    konzept_id, lern_id, exam_id, _ = _welt(app_env)
    label = store.konzept(konzept_id)["label"]
    _s, _scope, aufgabe, fehlertypen = _evidence(konzept_id, label, exam_id)

    _assert_evidence_nur_im_scope(konzept_id, exam_id, lern_id, aufgabe,
                                fehlertypen)


# --------------------------------------------------------------------------
# Heute: der Tag des Kindes sieht beide Lernraeume, aber getrennt
# --------------------------------------------------------------------------

def test_heute_zeigt_themen_wiederholungen_getrennt(app_env):
    import datetime as dt
    from app.adaptiv import store, wiederholung
    from app.woche import plaene

    konzept_id, lern_id, exam_id, _ = _welt(app_env)
    label = store.konzept(konzept_id)["label"]
    _evidence(konzept_id, label, lern_id)
    bis = plaene.today() + dt.timedelta(days=10)

    faellig = {e["child_key"] for e in wiederholung.offene(bis=bis)
               if e["konzept_id"] == konzept_id}
    assert faellig == {f"installation:topic:{lern_id}"}
    # Ein Termin im Prüfungsthema taucht auf demselben Tag auf — aber als
    # eigener Eintrag, nicht als der des Lernthemas.
    from app.adaptiv import unterricht
    s_b = _sitzung(konzept_id, label, exam_id)
    unterricht.wiederholung_gewaehlt(s_b, 4)
    eintraege = [e for e in wiederholung.offene(bis=bis)
                 if e["konzept_id"] == konzept_id]
    assert {e["child_key"] for e in eintraege} == {
        f"installation:topic:{lern_id}", f"installation:topic:{exam_id}"}
    assert len(eintraege) == 2


# --------------------------------------------------------------------------
# Die Oberflaeche: decorate() liest denselben Lernraum
# --------------------------------------------------------------------------

def test_decorate_kennt_nur_den_eigenen_lernraum(app_env):
    """Eine feste Prüfungs-Wiederholung macht das Lernthema nicht „sicher"."""
    from app.adaptiv import store, unterricht, wiederholung
    from app.services import learning_hub
    from app import topics

    konzept_id, lern_id, exam_id, _ = _welt(app_env)
    label = store.konzept(konzept_id)["label"]

    # Prüfungsthema bis MASTERED + feste Wiederholung.
    s_b = _sitzung(konzept_id, label, exam_id)
    unterricht.wiederholung_gewaehlt(s_b, 3)
    termin = wiederholung.offen_fuer(
        konzept_id, f"installation:topic:{exam_id}")
    wiederholung.abschliessen(termin["id"], bestanden_=True)
    app_env.db.q("UPDATE lern_sitzung SET zustand='MASTERED' WHERE id=?",
                 s_b["id"])

    pruef = learning_hub.decorate([dict(topics.get(exam_id))])[0]
    lern = learning_hub.decorate([dict(topics.get(lern_id))])[0]
    assert pruef["learning_status"] == "sicher"
    # Dasselbe Konzept, anderes Thema: keine Festigung, kein Stand.
    assert lern["learning_status"] == "neu"


# --------------------------------------------------------------------------
# Didaktik: falsch heisst lernen, nicht Dead End
# --------------------------------------------------------------------------

def _diagnose_sitzung(konzept_id, label):
    from app.adaptiv import unterricht
    s = unterricht.starte(konzept_id, label)
    s = unterricht.anker_beantwortet(s, "weiß nicht")
    return unterricht.bildschirm(s) and s


def test_unbekannte_diagnose_unterrichtet_statt_zu_enden(app_env):
    """Diagnose falsch, kein Alias: kein MASTERED, kein ESCALATED — die
    naechste Anzeige ist eine Lernintervention."""
    from app.adaptiv import inhalte_brueche, sitzung as zustand, store, unterricht

    app_env.db.init()
    store.init()
    konzept_id = inhalte_brueche.saeen()
    s = _diagnose_sitzung(konzept_id, "Brüche")

    s = unterricht.diagnose_beantwortet(s, "9/11")   # kein Katalogtreffer
    assert s["zustand"] == zustand.DIAGNOSING
    schirm = unterricht.bildschirm(s)
    assert schirm["art"] == "diagnose"
    assert "genauer an" in schirm["fehlerhinweis"]


def test_wiederholt_falsch_aendert_die_intervention(app_env):
    """Gleiche Frage, gleiche Antwort, gleicher Text ist keine Lehrrunde —
    jede Intervention muss sich unterscheiden, bis das Material ausgeht
    oder `adaptiv_unbekannte_antworten` erreicht ist."""
    from app.adaptiv import (inhalte_brueche, sitzung as zustand, store,
                             unterricht)

    app_env.db.init()
    store.init()
    konzept_id = inhalte_brueche.saeen()
    s = _diagnose_sitzung(konzept_id, "Brüche")

    gesehen = []
    for _ in range(zustand.unbekannte_antworten() + 2):
        s = unterricht.diagnose_beantwortet(s, "9/11")
        if s["zustand"] == zustand.ESCALATED:
            break
        schirm = unterricht.bildschirm(s)
        gesehen.append((schirm.get("frage"), schirm.get("fehlerhinweis")))

    assert len(gesehen) >= 2
    # Keine Intervention ist bloss dieselbe Meldung noch einmal.
    assert len(set(h for _, h in gesehen)) == len(gesehen)


def test_richtig_nach_hilfe_zurueck_im_normalen_weg(app_env):
    """Nach Hilfe richtig: weiter im bekannten Fluss — Kontrollfrage, nicht
    MASTERED aus einer einzelnen Antwort."""
    from app.adaptiv import (inhalte_brueche, sitzung as zustand, store,
                             unterricht)

    app_env.db.init()
    store.init()
    konzept_id = inhalte_brueche.saeen()
    s = _diagnose_sitzung(konzept_id, "Brüche")

    s = unterricht.diagnose_beantwortet(s, "9/11")     # unbekannt → Hilfe
    s = unterricht.diagnose_beantwortet(s, "5/6")      # jetzt richtig
    assert s["zustand"] != zustand.ESCALATED
    assert s["zustand"] != zustand.MASTERED            # A8: eine reicht nicht
    schirm = unterricht.bildschirm(s)
    assert schirm["art"] == "diagnose"                  # Kontrollfrage folgt
    assert schirm["frage"]                              # und ist gestellt


def _bis_transfer(app_env):
    """Eine Sitzung, die die Transferfrage sieht — komplett durch den
    regulären Weg: Diagnose-Treffer → Erklärung → geführt → selbstständig."""
    from app.adaptiv import (inhalte_brueche, inhalt_store, sitzung as zustand,
                             store, unterricht)

    app_env.db.init()
    store.init()
    konzept_id = inhalte_brueche.saeen()
    s = _diagnose_sitzung(konzept_id, "Brüche")
    s = unterricht.diagnose_beantwortet(s, "2/5")      # bekannte Fehlvorstellung
    assert s["zustand"] == zustand.TEACHING
    s = unterricht.vorhersage_beantwortet(s, "groesser")
    for _ in range(3):                                 # HOOK→RULE→BEISPIEL→GUIDED
        s = unterricht.weiter(s)
    gefuehrt = inhalt_store.aufgabe(s["fehlertyp_id"], inhalt_store.GEFUEHRT)
    s = unterricht.aufgabe_beantwortet(s, gefuehrt["loesung"])
    selbst = inhalt_store.aufgabe(s["fehlertyp_id"],
                                  inhalt_store.SELBSTSTAENDIG)
    s = unterricht.aufgabe_beantwortet(s, selbst["loesung"])
    assert unterricht.bildschirm(s)["art"] == "transfer"
    return s, konzept_id


def test_transfer_falsch_fuehrt_ueber_adaptation_zu_neuem_transfer(app_env):
    """Transfer falsch → andere Darstellung → gefuehrte Aufgabe → neue
    selbststaendige Aufgabe → NEUER Transfer, nicht derselbe noch einmal."""
    from app.adaptiv import (inhalte_brueche, inhalt_store, sitzung as zustand,
                             store, unterricht)

    s, konzept_id = _bis_transfer(app_env)
    fehlertyp_id = s["fehlertyp_id"]
    # Ein zweiter gepruefter Transfer steht im Katalog — geteilt, nicht
    # themenspezifisch.
    inhalt_store.aufgabe_sichern(
        fehlertyp_id, inhalt_store.TRANSFER, "Zweite Transferfrage?",
        "richtige Option", position=1,
        antwort_art=inhalt_store.AUSWAHL, optionen=["a", "b"])

    erster = unterricht._transfer_aufgabe(s)["frage"]
    s = unterricht.transfer_beantwortet(s, "falsche Option")
    assert s["phase"] == zustand.ADAPTATION            # Regel in anderer Form

    s = unterricht.weiter_nach_adaptation(s)
    assert s["phase"] == zustand.GUIDED_TASK           # kleine gefuehrte Aufgabe
    gefuehrt = inhalt_store.aufgabe(fehlertyp_id, inhalt_store.GEFUEHRT)
    s = unterricht.aufgabe_beantwortet(s, gefuehrt["loesung"])
    assert s["phase"] == zustand.INDEPENDENT_TASK

    s = unterricht.aufgabe_beantwortet(s, _selbst_loesung(s, fehlertyp_id))
    schirm = unterricht.bildschirm(s)
    assert schirm["art"] == "transfer"
    assert schirm["aufgabe"]["frage"] != erster        # ein neuer Transfer


def _selbst_loesung(sitzung, fehlertyp_id):
    from app.adaptiv import inhalt_store, unterricht
    aufgabe = unterricht._uebungsaufgabe(sitzung, "independent")
    return (aufgabe or inhalt_store.aufgabe(
        fehlertyp_id, inhalt_store.SELBSTSTAENDIG))["loesung"]


# --------------------------------------------------------------------------
# Die Spalte scope wandert auch in eine bestehende Datenbank
# --------------------------------------------------------------------------

def test_antwort_scope_wird_nachgezogen(client, fake_llm, app_env):
    from app.adaptiv import store, unterricht

    app_env.db.init()
    store.init()
    konzept_id, lern_id, _, _ = _welt(app_env)
    label = store.konzept(konzept_id)["label"]

    s = _sitzung(konzept_id, label, lern_id)
    with app_env.db.tx() as c:
        c.execute("ALTER TABLE lern_antwort DROP COLUMN scope")
    store.init()                                       # zieht nach
    alte = app_env.db.q1(
        "SELECT scope FROM lern_antwort WHERE sitzung_id=?", s["id"])
    assert alte["scope"] == f"installation:topic:{lern_id}"


def test_wiederholung_ohne_thema_bleibt_im_gemeinsamen_raum(app_env):
    """Themenlose Sitzungen — die es schon immer gab — teilen sich weiter
    den Raum 'installation'. Nichts davon wird umgehaengt."""
    from app.adaptiv import inhalte_brueche, store, unterricht, wiederholung

    app_env.db.init()
    store.init()
    konzept_id = inhalte_brueche.saeen()
    s = _sitzung(konzept_id, "Brüche", None)
    assert store.fortschritt_scope(s) == "installation"

    unterricht.wiederholung_gewaehlt(s, 3)
    assert wiederholung.offen_fuer(konzept_id, "installation") is not None


# --------------------------------------------------------------------------
# Ende zu Ende: die beiden Lernwege stoeren sich an keiner Stelle
# --------------------------------------------------------------------------

def test_e2e_pruefungsrunde_laesst_lernbereich_neu(client, fake_llm,
                                                  app_env, monkeypatch):
    """§22: Erst nur im Pruefungsthema lernen — /lernen zeigt danach weder
    die Pruefungssitzung noch einen fremden Lernstand. Danach umgekehrt:
    die eigene Lernrunde nimmt der Pruefungsweg nicht als die seine."""
    from app.adaptiv import store, unterricht, wiederholung
    from app.services import learning_hub
    from .test_app import kind_modus_aktivieren

    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True,
                          klassenarbeit_kind=True, learner_grade=6)
    konzept_id, lern_id, exam_id, eid = _welt(app_env)
    label = store.konzept(konzept_id)["label"]
    kind_modus_aktivieren(client)

    # Nur im Pruefungsthema gelernt: Termin plus eine offene Sitzung dort.
    s_pruefung = _sitzung(konzept_id, label, exam_id)
    unterricht.wiederholung_gewaehlt(s_pruefung, 3)
    wid = wiederholung.offen_fuer(
        konzept_id, f"installation:topic:{exam_id}")["id"]

    # /lernen: das eigene Thema ist neu, und der Pruefungstermin taucht
    # nicht als Link im Lernbereich auf.
    seite = client.get("/lernen")
    assert seite.status_code == 200
    assert f"/wiederholung/{wid}" not in seite.text
    thema = next(t for t in learning_hub.personal_topics()
                 if t["id"] == lern_id)
    assert thema["learning_status"] == "neu"
    assert thema["status_label"] == "Neu"

    # /lernen/adaptiv nimmt die offene Pruefungssitzung nicht wieder auf —
    # der Lernbereich bietet die Auswahl an, nicht den fremden Fortschritt.
    seite = client.get("/lernen/adaptiv")
    assert seite.status_code == 200
    assert 'action="/lernen/adaptiv/start"' in seite.text
    assert f"sitzung={s_pruefung['id']}" not in seite.text

    # Jetzt das eigene Thema lernen: eine eigene Sitzung, eigenes Thema.
    token = csrf_from(seite.text)
    seite = client.post("/lernen/adaptiv/start",
                        data={"_csrf": token, "topic_id": str(lern_id)})
    assert seite.status_code == 200
    eigene = store.offene_fuer_thema(lern_id)
    assert eigene is not None and eigene["id"] != s_pruefung["id"]
    assert store.eingabe(eigene["eingabe_id"])["topic_id"] == lern_id

    # Und umgekehrt nimmt der Pruefungsweg die eigene Sitzung nicht als
    # die seine — er findet seine offene Runde wieder.
    seite = client.get(f"/klassenarbeit/{eid}/lernen")
    assert seite.status_code == 200
    assert f"sitzung={s_pruefung['id']}" in seite.text
    assert f"sitzung={eigene['id']}" not in seite.text
