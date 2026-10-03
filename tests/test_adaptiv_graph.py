"""Kompetenzgraph — Voraussetzungen rekursiv, nicht nur eine Ebene tief.

Der Umweg ist eine normale Sitzung: scheitert sie, wird auch sie nach
ihren Voraussetzungen gefragt. So entsteht die Kette Ziel → Vorstufe →
deren Vorstufe bis zu einem tragfähigen Stand — und der Weg führt danach
Stufe für Stufe zurück ans Ziel. Zyklen im Graphen stoppen dabei die
Kette, statt zwei Konzepte im Kreis aufeinander warten zu lassen.
"""
import json


def _konzept(key: str, label: str | None = None, fach: str = "mathematik"):
    """Ein geprueftes Konzept mit Fehlertyp, Aufgaben und Import-Adresse.

    Der Import-Eintrag macht die Verknuepfung: `voraussetzungen_sichern`
    speichert die concept_id des Dienstes, `store.voraussetzungen` loest
    sie ueber die Provenance in die lokale ID auf.
    """
    from app import db
    from app.adaptiv import inhalt_store, store
    kid = store.konzept_sichern(fach, "graph", key,
                                label or key, geprueft=True)
    ft = store.fehlertyp_sichern(kid, f"{key}-fehler", f"{key} falsch",
                                 geprueft=True)
    for pos in range(3):
        inhalt_store.aufgabe_sichern(
            ft, inhalt_store.SELBSTSTAENDIG, f"{key}: {pos+1}+1 = ?",
            str(pos + 2), schwierigkeit=pos + 1, position=pos,
            antwort_art="zahl")
    inhalt_store.aufgabe_sichern(
        ft, inhalt_store.GEFUEHRT, f"{key}: gefuehrt", "1",
        antwort_art="zahl")
    inhalt_store.aufgabe_sichern(
        ft, inhalt_store.TRANSFER, f"{key}: transfer", "ja",
        antwort_art="auswahl", position=0)
    with db.tx() as c:
        c.execute("""INSERT OR IGNORE INTO lern_curriculum_import
                       (fingerprint, konzept_id, provenance, created_at)
                     VALUES (?,?,?,?)""",
                  (f"fp-{key}", kid, json.dumps({"concept_id": key}),
                   db.now()))
    return kid, ft


def _haengen(sitzung_id: int):
    """Eine Sitzung so weit treiben, bis Karo nach der Voraussetzung
    fragt: das Verhalten, das ein Kind sieht, das mehrfach scheitert."""
    from app.adaptiv import sitzung as zustand, store
    for _ in range(4):
        zustand.runde_gescheitert(sitzung_id, "0")
    return store.sitzung(sitzung_id)


def _meistern(sitzung_id: int):
    """Den Umweg sauber zu Ende bringen: Fehlertyp, Unterricht, Erfolge."""
    from app.adaptiv import sitzung as zustand, store
    s = store.sitzung(sitzung_id)
    ft = store.fehlertypen(s["konzept_id"])[0]["id"]
    if s["zustand"] == zustand.DIAGNOSING:
        s = zustand.fehler_erkannt(sitzung_id, ft, "falsch")
        s = zustand.unterricht_beginnen(sitzung_id)
    for _ in range(zustand.mastery_treffer()):
        s = zustand.antwort_richtig(sitzung_id, "richtig")
    assert s["zustand"] == zustand.MASTERED
    return s


# ---------------------------------------------------------------------------
# Rekursive Kette: Ziel → Vorstufe → Vorstufe der Vorstufe → zurück
# ---------------------------------------------------------------------------

def test_umweg_kette_laeuft_bis_zum_tragfaehigen_stand_und_zurueck(app_env):
    """A braucht B, B braucht C. Karo geht bis C, meistert, kehrt nach B,
    meistert, kehrt nach A — drei Ebenen ohne feste Tiefengrenze."""
    from app.adaptiv import sitzung as zustand, store, unterricht
    app_env.db.init()
    store.init()
    a, _ = _konzept("G.ZIEL")
    b, _ = _konzept("G.MITTE")
    c, _ = _konzept("G.BASIS")
    store.voraussetzungen_sichern(a, [{"concept_id": "G.MITTE", "title": "Mitte"}])
    store.voraussetzungen_sichern(b, [{"concept_id": "G.BASIS", "title": "Basis"}])

    sa = unterricht.starte(a, "Ziel")
    sa = _haengen(sa["id"])
    assert dict(sa["daten"] or {})["voraussetzung_lokal"] == b
    sa = unterricht.voraussetzung_beantwortet(sa, ["falsch", "falsch"])
    sb = unterricht.voraussetzung_lernen_starten(sa)
    assert sb["konzept_id"] == b
    assert dict(sb["daten"] or {})["voraussetzung_detour"] == sa["id"]

    # Die zweite Ebene: auch der Umweg findet seine fehlende Grundlage.
    sb = _haengen(sb["id"])
    assert dict(sb["daten"] or {})["voraussetzung_lokal"] == c
    sb = unterricht.voraussetzung_beantwortet(sb, ["falsch", "falsch"])
    sc = unterricht.voraussetzung_lernen_starten(sb)
    assert sc["konzept_id"] == c
    assert dict(sc["daten"] or {})["voraussetzung_detour"] == sb["id"]

    # Geschafft auf der untersten Stufe → zurück zur Mitte → zurück zum Ziel.
    sc = _meistern(sc["id"])
    schirm = unterricht.bildschirm(sc)
    assert schirm["art"] == "voraussetzung_geschafft"
    sb2 = unterricht.voraussetzung_weiter_zum_thema(sc)
    assert sb2["id"] == sb["id"]
    assert not dict(sb2["daten"] or {}).get("voraussetzung_offen")

    sb2 = _meistern(sb2["id"])
    sa2 = unterricht.voraussetzung_weiter_zum_thema(sb2)
    assert sa2["id"] == sa["id"]
    assert not dict(sa2["daten"] or {}).get("voraussetzung_offen")


def test_zyklus_im_graph_wird_gestoppt(app_env):
    """A braucht B, B braucht A: die Eskalation des Umwegs findet den
    wartenden Vorfahren und laesst ihn aus — Begleitung statt Kreis."""
    from app.adaptiv import sitzung as zustand, store, unterricht
    app_env.db.init()
    store.init()
    a, _ = _konzept("ZY.A")
    b, _ = _konzept("ZY.B")
    store.voraussetzungen_sichern(a, [{"concept_id": "ZY.B", "title": "B"}])
    store.voraussetzungen_sichern(b, [{"concept_id": "ZY.A", "title": "A"}])

    sa = unterricht.starte(a, "Ziel")
    sa = _haengen(sa["id"])
    sa = unterricht.voraussetzung_beantwortet(sa, ["falsch", "falsch"])
    sb = unterricht.voraussetzung_lernen_starten(sa)
    assert sb["konzept_id"] == b

    # B haengt ebenfalls — seine einzige Voraussetzung ist A, und A wartet
    # schon: kein zweiter Umweg, sondern die Begleitung von B.
    sb = _haengen(sb["id"])
    assert sb["zustand"] == zustand.ESCALATED
    assert not dict(sb["daten"] or {}).get("voraussetzung_offen")
    schirm = unterricht.bildschirm(sb)
    assert schirm["art"] == "begleitung"


def test_zyklus_guard_im_umweg_start(app_env):
    """Selbst wenn der Marker gesetzt ist, startet kein Umweg auf ein
    Konzept, das in der Kette oberhalb wartet."""
    from app.adaptiv import sitzung as zustand, store, unterricht
    app_env.db.init()
    store.init()
    a, _ = _konzept("ZG.A")
    b, _ = _konzept("ZG.B")
    store.voraussetzungen_sichern(a, [{"concept_id": "ZG.B", "title": "B"}])
    store.voraussetzungen_sichern(b, [{"concept_id": "ZG.A", "title": "A"}])

    sa = unterricht.starte(a, "Ziel")
    sa = _haengen(sa["id"])
    sa = unterricht.voraussetzung_beantwortet(sa, ["falsch", "falsch"])
    sb = unterricht.voraussetzung_lernen_starten(sa)

    # Vorsaetzlich verklemmt: B meint, A fehle — A wartet aber schon.
    sb = unterricht._merke(sb["id"], sb, voraussetzung_offen="ZG.A",
                           voraussetzung_lokal=a, voraussetzung_titel="A")
    ergebnis = unterricht.voraussetzung_lernen_starten(sb)
    assert ergebnis["id"] == sb["id"]
    daten = dict(ergebnis["daten"] or {})
    assert not daten.get("voraussetzung_offen")
    # Es entstand keine dritte Sitzung auf A.
    assert not db_anzahl(app_env, "lern_sitzung", "konzept_id", a) > 1


def db_anzahl(app_env, tabelle: str, spalte: str, wert) -> int:
    from app import db
    return db.q1(f"SELECT COUNT(*) AS n FROM {tabelle} WHERE {spalte}=?",
                 wert)["n"]


# ---------------------------------------------------------------------------
# Mehrere offene Voraussetzungen und erledigte Pruefungen
# ---------------------------------------------------------------------------

def test_naechste_offene_voraussetzung_wird_nach_der_ersten_geprueft(app_env):
    """Zwei Luecken: nach der ersten steht die zweite dran — der Marker
    „Voraussetzung schon geprueft" darf nicht fuer immer kleben."""
    from app.adaptiv import sitzung as zustand, store, unterricht
    app_env.db.init()
    store.init()
    a, _ = _konzept("MP.ZIEL")
    b, ft_b = _konzept("MP.B")
    c, _ = _konzept("MP.C")
    store.voraussetzungen_sichern(
        a, [{"concept_id": "MP.B", "title": "B"},
            {"concept_id": "MP.C", "title": "C"}])

    sa = unterricht.starte(a, "Ziel")
    sa = _haengen(sa["id"])
    assert dict(sa["daten"] or {})["voraussetzung_lokal"] == b

    # B sitzt laut Kurzdiagnose (Loesungen der zwei ersten Aufgaben) —
    # dann ist C die naechste offene Frage.
    sa = unterricht.voraussetzung_beantwortet(sa, ["2", "3"])
    daten = dict(sa["daten"] or {})
    assert daten["voraussetzung_lokal"] == c
    assert b in daten.get("voraussetzung_bestanden", [])


def test_bestandene_voraussetzung_kommt_nicht_nochmal(app_env):
    """Wer die Kurzdiagnose bestanden hat, wird nicht erneut befragt —
    die naechste Eskalation sucht weiter oder begleitet."""
    from app.adaptiv import sitzung as zustand, store, unterricht
    app_env.db.init()
    store.init()
    a, _ = _konzept("BV.ZIEL")
    b, _ = _konzept("BV.B")
    store.voraussetzungen_sichern(a, [{"concept_id": "BV.B", "title": "B"}])

    sa = unterricht.starte(a, "Ziel")
    sa = _haengen(sa["id"])
    sa = unterricht.voraussetzung_beantwortet(sa, ["2", "3"])
    assert sa["zustand"] == zustand.ESCALATED     # es lag nicht an B

    # Scheitert das Kind nach dem Weitermachen erneut, wird B nicht noch
    # einmal geprueft — die naechste Eskalation findet keine neue Luecke
    # und geht in die Begleitung.
    sa = unterricht.fortsetzen(sa)
    sa = _haengen(sa["id"])
    assert sa["zustand"] == zustand.ESCALATED
    assert not dict(sa["daten"] or {}).get("voraussetzung_offen")
    assert b in dict(sa["daten"] or {}).get("voraussetzung_bestanden", [])


# ---------------------------------------------------------------------------
# Fehlendes Material wird bestellt — dedupliziert
# ---------------------------------------------------------------------------

def test_fehlende_voraussetzung_wird_als_inhaltsluecke_bestellt(app_env):
    """Eine Voraussetzung ohne lokales Konzept loest keine Sackgasse aus:
    sie wird angefordert und die Begleitung geht weiter."""
    from app.adaptiv import sitzung as zustand, store, unterricht
    app_env.db.init()
    store.init()
    a, _ = _konzept("FE.ZIEL")
    store.voraussetzungen_sichern(
        a, [{"concept_id": "FE.FEHLT", "title": "Noch nicht da"}])

    sa = unterricht.starte(a, "Ziel")
    sa = _haengen(sa["id"])
    assert sa["zustand"] == zustand.ESCALATED

    anfragen = store.inhalt_anfragen()
    assert len(anfragen) == 1
    anfrage = anfragen[0]
    assert anfrage["konzept_key"] == "FE.FEHLT"
    assert anfrage["rolle"] == "voraussetzung"
    assert anfrage["grund"] == "fehlt"

    # Dieselbe Luecke faellt noch einmal an: keine zweite Bestellung,
    # nur `anzahl` steigt.
    store.inhalt_anfordern("mathematik", "FE.FEHLT", "voraussetzung",
                           "fehlt")
    anfragen = store.inhalt_anfragen()
    assert len(anfragen) == 1
    assert anfragen[0]["anzahl"] == 2


def test_aufgebrauchtes_material_wird_bestellt(client, fake_llm, app_env,
                                             monkeypatch):
    """Der inhalt_fehlt-Schirm bestellt die Aufgabe, die der Katalog nicht
    mehr hergibt — einmal, nicht bei jedem Rendern."""
    from app.adaptiv import inhalt_store, store
    from .conftest import csrf_from
    from .test_app import einrichten, kind_modus_aktivieren
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True, learner_grade=6)
    kind_modus_aktivieren(client)
    token = csrf_from(client.get("/lernen/adaptiv").text)
    client.post("/lernen/adaptiv/start",
                data={"_csrf": token, "thema": "brueche"})
    client.post("/lernen/adaptiv/anker",
                data={"_csrf": token, "antwort": "x"})
    client.post("/lernen/adaptiv/diagnose",
                data={"_csrf": token, "antwort": "2/5"})
    client.post("/lernen/adaptiv/vorhersage",
                data={"_csrf": token, "antwort": "groesser"})
    for _ in range(3):
        client.post("/lernen/adaptiv/weiter", data={"_csrf": token})

    monkeypatch.setattr(inhalt_store, "aufgabe", lambda *a, **k: None)
    for _ in range(3):
        client.get("/lernen/adaptiv")
    anfragen = [a for a in store.inhalt_anfragen()
                if a["rolle"] == "aufgabe"]
    assert len(anfragen) == 1
    assert anfragen[0]["grund"] == "erschoepft"
    assert anfragen[0]["anzahl"] >= 1


# ---------------------------------------------------------------------------
# Niveau: die Aufgabenwahl folgt dem erreichten Schwierigkeitsstand
# ---------------------------------------------------------------------------

def test_naechste_aufgabe_folgt_dem_niveau(app_env):
    """Nach einem Fehler sinkt das Niveau — die naechste freie Aufgabe ist
    die einfachste; nach Erfolgen steigt sie stufenweise."""
    from app.adaptiv import sitzung as zustand, store, unterricht
    app_env.db.init()
    store.init()
    kid, ft = _konzept("NV.ZIEL")
    s = unterricht.starte(kid, "Niveau")
    s = zustand.fehler_erkannt(s["id"], ft, "falsch")
    s = zustand.unterricht_beginnen(s["id"])

    einfach = dict(s["daten"] or {})
    einfach["niveau"] = 1
    s = _merke_daten(s["id"], einfach)
    aufgabe = unterricht._neue_selbstaufgabe(s)
    assert aufgabe["schwierigkeit"] == 1

    einfach["niveau"] = 3
    s = _merke_daten(s["id"], einfach)
    aufgabe = unterricht._neue_selbstaufgabe(s)
    assert aufgabe["schwierigkeit"] == 3


def _merke_daten(sitzung_id: int, daten: dict) -> dict:
    from app.adaptiv import store
    store.sitzung_aktualisieren(sitzung_id, daten=daten)
    return store.sitzung(sitzung_id)


def test_naechste_aktion_kennt_kein_aufgeben(app_env):
    """Die zentrale Entscheidungsschicht endet immer in einem Lernschritt
    oder einer Wahl des Kindes — niemals in einem Ausstieg."""
    from app.adaptiv import naechste_aktion
    from app.adaptiv import sitzung as zustand, store, unterricht
    app_env.db.init()
    store.init()
    kid, _ = _konzept("NA.ZIEL")
    s = unterricht.starte(kid, "Ziel")
    for aktion in (naechste_aktion.fuer(s),
                   naechste_aktion.fuer(_haengen(s["id"]))):
        assert aktion["aktion"] != "GIVE_UP"
        assert aktion["aktion"] in {
            naechste_aktion.DIAGNOSE, naechste_aktion.ERKLAEREN,
            naechste_aktion.ERKLAEREN_ANDERS, naechste_aktion.UEBUNG_GEFUEHRT,
            naechste_aktion.UEBUNG_SELBST, naechste_aktion.TRANSFER,
            naechste_aktion.VORAUSSETZUNG_PRUEFEN,
            naechste_aktion.VORAUSSETZUNG_LERNEN,
            naechste_aktion.ZURUECK_ZUM_ZIEL, naechste_aktion.BEGLEITEN,
            naechste_aktion.GESCHAFFT}
