"""Die Entscheidungen aus Schritt 4 — jede mit eigenem Test.

Grundlage: docs/LERNKREISLAUF.md, Abschnitt „Entschieden". Wo hier ein Test
steht, steht dort eine Regel, und umgekehrt.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------- Z8

def test_z8_die_grenze_fuer_unbekannte_antworten_ist_einstellbar(app_env):
    """Die einzige Schwelle des adaptiven Wegs, an der niemand drehen konnte."""
    from app.adaptiv import sitzung
    app_env.db.init()
    assert sitzung.unbekannte_antworten() == 3
    app_env.config.update(adaptiv_unbekannte_antworten=5)
    assert sitzung.unbekannte_antworten(app_env.config.load()) == 5
    # Unter 1 ergibt sie keinen Sinn — dann waere jede Antwort die letzte.
    app_env.config.update(adaptiv_unbekannte_antworten=0)
    assert sitzung.unbekannte_antworten(app_env.config.load()) == 1


def test_z8_nach_der_eingestellten_zahl_kommt_ein_mensch(app_env, monkeypatch):
    from app.adaptiv import katalog, sitzung, store, unterricht
    app_env.db.init()
    store.init()
    app_env.config.update(adaptiv_unbekannte_antworten=2)
    cfg = app_env.config.load()

    konzept = store.konzepte_verfuegbar()[0]
    s = unterricht.starte(konzept["id"])
    s = unterricht.anker_beantwortet(s, "irgendwas")
    monkeypatch.setattr(katalog, "identifiziere",
                        lambda *a, **k: katalog.Treffer(fehlertyp=None, tier=None, grund="nicht im Katalog"))

    # Zahlen, die im Katalog nicht stehen: Text waere schon vorher am Hinweis
    # „schreib eine Zahl" haengengeblieben und haette gar nicht gezaehlt.
    s = unterricht.diagnose_beantwortet(s, "7/9", cfg=cfg)
    assert s["zustand"] != sitzung.ESCALATED
    assert dict(s["daten"] or {}).get("unbekannte_antworten") == 1
    s = unterricht.diagnose_beantwortet(s, "11/13", cfg=cfg)
    assert s["zustand"] == sitzung.ESCALATED


# ---------------------------------------------------------------- Z10

def test_z10_die_wirksamere_erklaerung_gewinnt(app_env):
    """Gezaehlt wurde sie seit jeher, gelesen hat sie niemand."""
    from app import db
    from app.adaptiv import store
    app_env.db.init()
    store.init()
    app_env.config.update(adaptiv_wirkung_ab=10)

    fehlertyp_id = store.fehlertypen(store.konzepte_verfuegbar()[0]["id"])[0]["id"]
    with db.tx() as c:
        # Zwei gleichwertige Erklaerungen, eine wirkt, eine nicht.
        for version, (wirkte, ausgeliefert) in enumerate(((9, 10), (1, 10)), start=90):
            c.execute("""INSERT INTO lern_erklaerung
                           (fehlertyp_id, klasse, version, inhalt, visualisierung,
                            schwierigkeit, quelle, geprueft_am, aktiv,
                            ausgeliefert, folge_erfolge, created_at, updated_at)
                         VALUES (?,6,?,'{}','{}',1,'test',?,1,?,?,?,?)""",
                      (fehlertyp_id, version, db.now(), ausgeliefert, wirkte,
                       db.now(), db.now()))
    gewaehlt = store.beste_erklaerung(fehlertyp_id, 6)
    assert gewaehlt["erfolgsquote"] == 0.9


def test_z10_unter_der_mindestzahl_entscheidet_die_wirkung_nicht(app_env):
    """Zwei von zwei ist keine Quote, sondern Zufall."""
    from app import db
    from app.adaptiv import store
    app_env.db.init()
    store.init()
    app_env.config.update(adaptiv_wirkung_ab=10)
    fehlertyp_id = store.fehlertypen(store.konzepte_verfuegbar()[0]["id"])[0]["id"]
    with db.tx() as c:
        c.execute("""INSERT INTO lern_erklaerung
                       (fehlertyp_id, klasse, version, inhalt, visualisierung,
                        schwierigkeit, quelle, geprueft_am, aktiv,
                        ausgeliefert, folge_erfolge, created_at, updated_at)
                     VALUES (?,6,9,'{}','{}',1,'test',?,1,2,2,?,?)""",
                  (fehlertyp_id, db.now(), db.now(), db.now()))
    gewaehlt = store.beste_erklaerung(fehlertyp_id, 6)
    # Die neue Erklaerung hat 100 %, aber nur zwei Einsaetze — sie gewinnt
    # nicht allein deswegen.
    assert gewaehlt["version"] != 9 or gewaehlt["ausgeliefert"] >= 10


def test_z10_wirkungslose_erklaerungen_werden_gemeldet_mit_zahlen(app_env):
    """Nur Zahlen. Kein Name, kein Thema, keine Antwort eines Kindes."""
    from app import db
    from app.adaptiv import store
    app_env.db.init()
    store.init()
    app_env.config.update(adaptiv_wirkung_ab=10, adaptiv_wirkung_schwelle=0.3)
    fehlertyp_id = store.fehlertypen(store.konzepte_verfuegbar()[0]["id"])[0]["id"]
    with db.tx() as c:
        c.execute("""INSERT INTO lern_erklaerung
                       (fehlertyp_id, klasse, version, inhalt, visualisierung,
                        schwierigkeit, quelle, geprueft_am, aktiv,
                        ausgeliefert, folge_erfolge, created_at, updated_at)
                     VALUES (?,6,42,'{}','{}',1,'test',?,1,20,2,?,?)""",
                  (fehlertyp_id, db.now(), db.now(), db.now()))
    befunde = store.wirkungslose_erklaerungen(app_env.config.load())
    assert befunde and befunde[0]["wirkquote"] == 0.1
    erlaubt = {"erklaerung_id", "konzept_key", "fehler_key", "klasse",
               "ausgeliefert", "wirkte", "wirkquote"}
    assert set(befunde[0]) == erlaubt, "nichts darf mitgehen, was nicht gebraucht wird"


def test_z10_dieselbe_erklaerung_wird_nicht_zweimal_gemeldet(app_env):
    from app import db
    from app.adaptiv import store
    app_env.db.init()
    store.init()
    app_env.config.update(adaptiv_wirkung_ab=10, adaptiv_wirkung_schwelle=0.3)
    fehlertyp_id = store.fehlertypen(store.konzepte_verfuegbar()[0]["id"])[0]["id"]
    with db.tx() as c:
        c.execute("""INSERT INTO lern_erklaerung
                       (fehlertyp_id, klasse, version, inhalt, visualisierung,
                        schwierigkeit, quelle, geprueft_am, aktiv,
                        ausgeliefert, folge_erfolge, created_at, updated_at)
                     VALUES (?,6,43,'{}','{}',1,'test',?,1,20,2,?,?)""",
                  (fehlertyp_id, db.now(), db.now(), db.now()))
    erste = store.wirkungslose_erklaerungen(app_env.config.load())
    store.wirkung_gemeldet([b["erklaerung_id"] for b in erste])
    assert store.wirkungslose_erklaerungen(app_env.config.load()) == []
    # Erst wenn sie weiter ausgeliefert wurde, ist es eine neue Aussage.
    with db.tx() as c:
        c.execute("UPDATE lern_erklaerung SET ausgeliefert=30 WHERE version=43")
    assert store.wirkungslose_erklaerungen(app_env.config.load())



def test_z10_am_ende_einer_sitzung_geht_die_meldung_auf_die_reise(app_env, monkeypatch):
    """Eine Meldefunktion, die niemand ruft, ist wieder nur eine Zahl.

    Am Ende einer Sitzung hat sich die Wirkung einer Erklaerung zuletzt
    geaendert — dort haengt der Auftrag.
    """
    from app import db
    from app.adaptiv import curriculum_dienst, sitzung as zustand, store
    app_env.db.init()
    store.init()
    monkeypatch.setattr(curriculum_dienst, "configured", lambda cfg: True)
    konzept_id = store.konzepte_verfuegbar()[0]["id"]
    sid = store.sitzung_anlegen(zustand.INPUT_RECEIVED, konzept_id=konzept_id)

    zustand.wechsle(sid, zustand.MATERIAL_ANALYZED)
    assert not db.q("SELECT id FROM job WHERE type='wirkung_melden'")
    zustand.wechsle(sid, zustand.DIAGNOSING)
    zustand.wechsle(sid, zustand.MASTERED, "verstanden")

    auftraege = db.q("SELECT id FROM job WHERE type='wirkung_melden'")
    assert len(auftraege) == 1

    # Eine zweite Sitzung legt keinen zweiten Auftrag daneben.
    sid2 = store.sitzung_anlegen(zustand.INPUT_RECEIVED, konzept_id=konzept_id)
    zustand.wechsle(sid2, zustand.MATERIAL_ANALYZED)
    zustand.wechsle(sid2, zustand.DIAGNOSING)
    zustand.wechsle(sid2, zustand.MASTERED, "verstanden")
    assert len(db.q("SELECT id FROM job WHERE type='wirkung_melden'")) == 1


def test_z10_ohne_lehrplan_dienst_gibt_es_niemanden_zu_melden(app_env, monkeypatch):
    from app import db
    from app.adaptiv import curriculum_dienst, sitzung as zustand, store
    app_env.db.init()
    store.init()
    monkeypatch.setattr(curriculum_dienst, "configured", lambda cfg: False)
    sid = store.sitzung_anlegen(zustand.INPUT_RECEIVED,
                                konzept_id=store.konzepte_verfuegbar()[0]["id"])
    zustand.wechsle(sid, zustand.MATERIAL_ANALYZED)
    zustand.wechsle(sid, zustand.DIAGNOSING)
    zustand.wechsle(sid, zustand.MASTERED, "verstanden")
    assert not db.q("SELECT id FROM job WHERE type='wirkung_melden'")


# ---------------------------------------------------------------- Z3

def _konzept_mit_voraussetzung(app_env):
    """Ein Konzept, dem eine importierte Voraussetzung vorausgeht."""
    from app import db
    from app.adaptiv import store
    store.init()
    konzepte = store.konzepte_verfuegbar()
    ziel = konzepte[0]["id"]
    # Ein zweites Konzept als Voraussetzung, so wie ein Import es anlegt.
    with db.tx() as c:
        vid = c.execute(
            """INSERT INTO lern_konzept (fach, thema_key, konzept_key, label,
                   klasse_von, klasse_bis, stichworte, quelle, geprueft_am, aktiv, created_at)
               VALUES ('mathematik','brueche','vorab','Brüche erweitern',5,6,'[]',
                       'curriculum',?,1,?)""", (db.now(), db.now())).lastrowid
        # geprueft_am und aktiv: ungepruefte Inhalte liefert Karo keinem Kind
        # aus — auch nicht als Voraussetzungsdiagnose.
        ft = c.execute("""INSERT INTO lern_fehlertyp (konzept_id, fehler_key, label,
                              beschreibung, geprueft_am, aktiv, created_at)
                          VALUES (?, 'erweitern-falsch', 'falsch erweitert', 'x', ?, 1, ?)""",
                       (vid, db.now(), db.now())).lastrowid
        for pos, (frage, loesung) in enumerate((("1/2 = ?/4", "2/4"), ("1/3 = ?/9", "3/9"))):
            c.execute("""INSERT INTO lern_aufgabe (fehlertyp_id, rolle, position, frage,
                             loesung, typischer_fehler, geprueft_am, aktiv, created_at)
                         VALUES (?, 'selbststaendig', ?, ?, ?, '', ?, 1, ?)""",
                      (ft, pos, frage, loesung, db.now(), db.now()))
        c.execute("""INSERT INTO lern_curriculum_import (fingerprint, konzept_id, provenance, created_at)
                     VALUES ('fp-vorab', ?, ?, ?)""",
                  (vid, '{"concept_id": "MA.BRUECHE.ERWEITERN"}', db.now()))
    store.voraussetzungen_sichern(
        ziel, [{"concept_id": "MA.BRUECHE.ERWEITERN", "title": "Brüche erweitern"}])
    return ziel, vid


def test_z3_voraussetzungen_kommen_aus_der_lieferung(app_env):
    """Geprüft, nicht geraten — und ohne Feld bleibt alles wie vorher."""
    import karo_contract
    app_env.db.init()
    geliefert = {"prerequisites": [{"concept_id": "MA.BRUECHE.ERWEITERN",
                                    "title": "Brüche erweitern"}]}
    assert karo_contract.voraussetzungen(geliefert)[0]["concept_id"] == "MA.BRUECHE.ERWEITERN"
    assert karo_contract.voraussetzungen({}) == []
    assert karo_contract.voraussetzungen({"prerequisites": "unsinn"}) == []
    assert karo_contract.voraussetzungen({"prerequisites": [{"title": "ohne id"}]}) == []


def test_z3_vor_der_eskalation_wird_die_voraussetzung_geprueft(app_env):
    """Wer Brüche nicht erweitern kann, scheitert beim Addieren zwei Schritte davor."""
    from app.adaptiv import sitzung, store, unterricht
    app_env.db.init()
    ziel, vid = _konzept_mit_voraussetzung(app_env)

    s = unterricht.starte(ziel)
    ergebnis = sitzung.eskalieren(s["id"])
    # Kein Mensch — erst die Voraussetzung.
    assert ergebnis["zustand"] != sitzung.ESCALATED
    daten = dict(ergebnis["daten"] or {})
    assert daten["voraussetzung_offen"] == "MA.BRUECHE.ERWEITERN"
    assert daten["voraussetzung_lokal"] == vid

    bildschirm = unterricht.bildschirm(ergebnis)
    assert bildschirm["art"] == "voraussetzung"
    assert bildschirm["voraussetzung"] == "Brüche erweitern"
    assert len(bildschirm["aufgaben"]) == 2


def test_z3_sitzt_die_voraussetzung_eskaliert_karo_wie_bisher(app_env):
    from app.adaptiv import sitzung, store, unterricht
    app_env.db.init()
    ziel, vid = _konzept_mit_voraussetzung(app_env)
    s = unterricht.starte(ziel)
    s = sitzung.eskalieren(s["id"])

    aufgaben = unterricht.bildschirm(s)["aufgaben"]
    richtig = [a["loesung"] for a in aufgaben]
    ergebnis = unterricht.voraussetzung_beantwortet(s, richtig)
    assert ergebnis["zustand"] == sitzung.ESCALATED, "es lag nicht an der Voraussetzung"


def test_z3_fehlt_die_voraussetzung_wird_sie_zuerst_gelernt(app_env):
    from app.adaptiv import sitzung, unterricht
    app_env.db.init()
    ziel, vid = _konzept_mit_voraussetzung(app_env)
    s = unterricht.starte(ziel)
    s = sitzung.eskalieren(s["id"])

    ergebnis = unterricht.voraussetzung_beantwortet(s, ["99/99", "88/88"])
    assert ergebnis["zustand"] != sitzung.ESCALATED
    assert dict(ergebnis["daten"] or {})["voraussetzung_lernen"] is True

    # Und danach geht es zurück an die Stelle, an der es hakte.
    zurueck = unterricht.zurueck_von_voraussetzung(ergebnis)
    assert not dict(zurueck["daten"] or {}).get("voraussetzung_offen")


def test_z3_eine_halbe_voraussetzung_zaehlt_nicht(app_env):
    """Eine von zwei richtig ist ein Anfang, keine Sicherheit."""
    from app.adaptiv import voraussetzung as vor
    app_env.db.init()
    aufgaben = [{"loesung": "2/4"}, {"loesung": "3/9"}]
    assert vor.pruefen(["2/4", "3/9"], aufgaben) is True
    assert vor.pruefen(["2/4", "falsch"], aufgaben) is False
    assert vor.pruefen(["2/4"], aufgaben) is False


def test_z3_ohne_importierte_voraussetzung_wird_eskaliert(app_env):
    """Ein Lernweg ins Leere wäre schlimmer als ein Mensch."""
    from app import db
    from app.adaptiv import sitzung, store, unterricht
    app_env.db.init()
    store.init()
    ziel = store.konzepte_verfuegbar()[0]["id"]
    store.voraussetzungen_sichern(ziel, [{"concept_id": "MA.GIBTS.NICHT", "title": "fehlt"}])
    s = unterricht.starte(ziel)
    ergebnis = sitzung.eskalieren(s["id"])
    assert ergebnis["zustand"] == sitzung.ESCALATED
    # Der Mensch erfährt, woran es lag.
    ereignisse = db.q("SELECT anlass, nutzdaten FROM lern_ereignis WHERE sitzung_id=?", s["id"])
    assert any("Voraussetzung fehlt in der Bibliothek" in e["anlass"] for e in ereignisse)


# ------------------------------------------------- Z3 im Browser

def _kind_im_browser(client, fake_llm, app_env):
    """Eingerichtet, adaptiver Weg an, Kind-Modus — bereit zum Posten."""
    from .conftest import csrf_from
    from .test_app import einrichten, kind_modus_aktivieren
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True, learner_grade=6)
    kind_modus_aktivieren(client)
    return csrf_from(client.get("/lernen/adaptiv").text)


def _sitzung_mit_offener_voraussetzung(client, fake_llm, app_env):
    """Eine laufende Sitzung, bei der die Voraussetzung offen ist (Z3)."""
    from app.adaptiv import sitzung
    token = _kind_im_browser(client, fake_llm, app_env)
    ziel, vid = _konzept_mit_voraussetzung(app_env)
    client.post("/lernen/adaptiv/start", data={"_csrf": token, "thema": "brueche"})
    ergebnis = sitzung.eskalieren(sitzung.laufende()["id"])
    assert dict(ergebnis["daten"] or {}).get("voraussetzung_offen")
    return token, vid, ergebnis


def test_z3_voraussetzung_hat_ihren_eigenen_bildschirm(
        client, fake_llm, fake_cli, app_env):
    """Kein Geschafft-Fallback: Grundlage und ihre Aufgaben sind sichtbar."""
    token, vid, s = _sitzung_mit_offener_voraussetzung(client, fake_llm, app_env)

    seite = client.get("/lernen/adaptiv")
    assert "Bevor wir weitermachen" in seite.text
    assert "Brüche erweitern" in seite.text
    assert "1/2 = ?/4" in seite.text and "1/3 = ?/9" in seite.text
    assert "kein Fehler" in seite.text
    assert "Gut gemacht" not in seite.text
    assert 'action="/lernen/adaptiv/voraussetzung' in seite.text

    # Neuladen veraendert den Zustand nicht (A6).
    seite = client.get("/lernen/adaptiv")
    assert "1/2 = ?/4" in seite.text


def test_z3_sitzt_sie_eskaliert_der_http_weg(
        client, fake_llm, fake_cli, app_env):
    """Die Grundlage sitzt — es lag nicht daran: eskalieren wie bisher."""
    from app.adaptiv import sitzung
    token, vid, s = _sitzung_mit_offener_voraussetzung(client, fake_llm, app_env)
    client.get("/lernen/adaptiv")

    seite = client.post("/lernen/adaptiv/voraussetzung",
                        data={"_csrf": token, "antwort": ["2/4", "3/9"]})
    assert "liegt nicht an dir" in seite.text
    stand = app_env.db.q1("SELECT zustand FROM lern_sitzung WHERE id=?", s["id"])
    assert stand["zustand"] == sitzung.ESCALATED


def test_z3_fehlt_sie_startet_der_umweg_und_kehrt_zurueck(
        client, fake_llm, fake_cli, app_env):
    """Kein Dead End: falsche Diagnose → Umweg lernen → zurueck an die Stelle."""
    import json
    from app.adaptiv import sitzung as zustand, store
    token, vid, s = _sitzung_mit_offener_voraussetzung(client, fake_llm, app_env)
    client.get("/lernen/adaptiv")

    seite = client.post("/lernen/adaptiv/voraussetzung",
                        data={"_csrf": token, "antwort": ["falsch", "falsch"]})
    # Die Bruecke zum Umweg — nicht dasselbe Formular noch einmal.
    assert "fehlt noch ein Stück" in seite.text
    assert 'action="/lernen/adaptiv/voraussetzung/lernen' in seite.text

    seite = client.get("/lernen/adaptiv")
    assert "fehlt noch ein Stück" in seite.text      # Neuladen bleibt stehen

    seite = client.post("/lernen/adaptiv/voraussetzung/lernen",
                        data={"_csrf": token})
    umweg = app_env.db.q1("SELECT * FROM lern_sitzung ORDER BY id DESC LIMIT 1")
    assert umweg["konzept_id"] == vid and umweg["zustand"] == "DIAGNOSING"
    assert json.loads(umweg["daten"])["voraussetzung_detour"] == s["id"]
    assert "Gut gemacht" not in seite.text           # der Umweg rendert normal

    # Umweg geschafft: erst zurueck an die Stelle, an der es hakte.
    zustand.wechsle(umweg["id"], zustand.MASTERED, "test")
    for f in store.fehlertypen(vid):
        store.fortschritt_buchen(vid, f["id"], mastery="sicher")

    seite = client.get("/lernen/adaptiv")
    assert "zurück zu" in seite.text                 # voraussetzung_geschafft

    seite = client.post("/lernen/adaptiv/voraussetzung/weiter",
                        data={"_csrf": token})
    alt = app_env.db.q1("SELECT daten FROM lern_sitzung WHERE id=?", s["id"])
    assert not json.loads(alt["daten"]).get("voraussetzung_offen")
    # Die Sitzung laeuft weiter — die Ankerfrage wartet.
    assert 'name="antwort"' in seite.text
    assert "Bevor wir weitermachen" not in seite.text


def test_z3_sitzt_sie_inzwischen_geht_es_direkt_weiter(
        client, fake_llm, fake_cli, app_env):
    """Ist die Grundlage anderswo sicher geworden, fragt die Bruecke nicht zweimal."""
    import json
    from app.adaptiv import store
    token, vid, s = _sitzung_mit_offener_voraussetzung(client, fake_llm, app_env)
    client.get("/lernen/adaptiv")

    seite = client.post("/lernen/adaptiv/voraussetzung",
                        data={"_csrf": token, "antwort": ["falsch", "falsch"]})
    assert "fehlt noch ein Stück" in seite.text

    for f in store.fehlertypen(vid):
        store.fortschritt_buchen(vid, f["id"], mastery="sicher")

    seite = client.get("/lernen/adaptiv")
    assert "sitzt jetzt" in seite.text               # voraussetzung_zurueck
    assert 'action="/lernen/adaptiv/voraussetzung/weiter' in seite.text

    seite = client.post("/lernen/adaptiv/voraussetzung/weiter",
                        data={"_csrf": token})
    alt = app_env.db.q1("SELECT daten FROM lern_sitzung WHERE id=?", s["id"])
    assert not json.loads(alt["daten"]).get("voraussetzung_offen")


def test_z3_der_umweg_verdoppelt_sich_nicht(
        client, fake_llm, fake_cli, app_env):
    """Laeuft der Umweg schon, startet kein zweiter."""
    token, vid, s = _sitzung_mit_offener_voraussetzung(client, fake_llm, app_env)
    client.post("/lernen/adaptiv/voraussetzung",
                data={"_csrf": token, "antwort": ["falsch", "falsch"]})

    client.post("/lernen/adaptiv/voraussetzung/lernen", data={"_csrf": token})
    anzahl = app_env.db.q1(
        "SELECT COUNT(*) AS n FROM lern_sitzung WHERE konzept_id=?", vid)["n"]
    # Auf der wartenden Sitzung direkt noch einmal „lernen" gedrueckt.
    client.post(f"/lernen/adaptiv/voraussetzung/lernen?sitzung={s['id']}",
                data={"_csrf": token})
    assert app_env.db.q1(
        "SELECT COUNT(*) AS n FROM lern_sitzung WHERE konzept_id=?", vid)["n"] == anzahl


def test_z3_ende_zu_ende_vom_scheitern_ueber_den_umweg_zurueck(
        client, fake_llm, fake_cli, app_env):
    """Lernen → dreimal gescheitert → Grundlage pruefen → lernen → weiter."""
    from app.adaptiv import sitzung as zustand, store
    from .test_adaptiv_lektion import _bis_zur_gefuehrten_aufgabe

    token = _kind_im_browser(client, fake_llm, app_env)
    ziel, vid = _konzept_mit_voraussetzung(app_env)
    client.post("/lernen/adaptiv/start", data={"_csrf": token, "thema": "brueche"})

    _bis_zur_gefuehrten_aufgabe(client, token)
    seite = None
    for _ in range(3):
        seite = client.post("/lernen/adaptiv/aufgabe",
                            data={"_csrf": token, "antwort": "2/6"})
        if "Bevor wir weitermachen" not in seite.text:
            client.post("/lernen/adaptiv/weiter", data={"_csrf": token})
    assert "Bevor wir weitermachen" in seite.text    # die Voraussetzung, ...
    assert "Brüche erweitern" in seite.text          # ... nicht der Mensch
    assert "liegt nicht an dir" not in seite.text

    seite = client.post("/lernen/adaptiv/voraussetzung",
                        data={"_csrf": token, "antwort": ["falsch", "falsch"]})
    assert "fehlt noch ein Stück" in seite.text

    client.post("/lernen/adaptiv/voraussetzung/lernen", data={"_csrf": token})
    umweg = app_env.db.q1("SELECT * FROM lern_sitzung ORDER BY id DESC LIMIT 1")
    assert umweg["konzept_id"] == vid

    zustand.wechsle(umweg["id"], zustand.MASTERED, "test")
    for f in store.fehlertypen(vid):
        store.fortschritt_buchen(vid, f["id"], mastery="sicher")

    seite = client.get("/lernen/adaptiv")
    assert "zurück zu" in seite.text
    seite = client.post("/lernen/adaptiv/voraussetzung/weiter",
                        data={"_csrf": token})
    # Zurueck da, wo es hakte — die Adaptation wartet noch auf das Kind.
    assert "Nochmal probieren" in seite.text
    seite = client.post("/lernen/adaptiv/weiter", data={"_csrf": token})
    assert 'name="antwort"' in seite.text            # dieselbe Aufgabe weiter


# ---------------------------------------------------------------- Z9

def test_z9_rot_kommt_vor_gelb(app_env, monkeypatch):
    """Ein rotes Thema wartete hinter einem gelben, nur weil es weiter unten stand."""
    from app.services import exam_effort
    app_env.db.init()
    zeilen = [
        {"topic_id": 1, "label": "gelbes Thema", "vorwissen": "gelb"},
        {"topic_id": 2, "label": "rotes Thema", "vorwissen": "rot"},
        {"topic_id": 3, "label": "sicheres Thema", "vorwissen": "gruen"},
        {"topic_id": 4, "label": "neues Thema", "vorwissen": "weiss"},
    ]
    monkeypatch.setattr(exam_effort, "_konzept_schluessel", lambda t: [])
    monkeypatch.setattr(exam_effort, "_konzept_ids", lambda t: [])
    sortiert = [z["label"] for z in exam_effort._lernreihenfolge(zeilen)]
    assert sortiert == ["rotes Thema", "neues Thema", "gelbes Thema", "sicheres Thema"]


def test_z9_die_voraussetzung_kommt_vor_allem_anderen(app_env, monkeypatch):
    """„Probe durchführen" setzt „Gleichungen lösen" voraus — nicht umgekehrt."""
    from app.services import exam_effort
    app_env.db.init()
    zeilen = [
        {"topic_id": 1, "label": "Probe durchführen", "vorwissen": "rot"},
        {"topic_id": 2, "label": "Gleichungen lösen", "vorwissen": "gelb"},
    ]
    monkeypatch.setattr(exam_effort, "_konzept_schluessel",
                        lambda t: {1: ["MA.PROBE"], 2: ["MA.GLEICHUNG"]}[t])
    monkeypatch.setattr(exam_effort, "_konzept_ids", lambda t: [t])
    monkeypatch.setattr("app.adaptiv.store.voraussetzungen",
                        lambda kid: [{"voraussetzung": "MA.GLEICHUNG"}] if kid == 1 else [])
    sortiert = [z["label"] for z in exam_effort._lernreihenfolge(zeilen)]
    # Obwohl „Probe" rot ist und zuerst angekündigt wurde.
    assert sortiert == ["Gleichungen lösen", "Probe durchführen"]


def test_z9_bei_gleichstand_entscheidet_die_ankuendigung(app_env, monkeypatch):
    """Die Liste bleibt die Liste — sie ist nur nicht mehr das erste Wort."""
    from app.services import exam_effort
    app_env.db.init()
    zeilen = [
        {"topic_id": 1, "label": "zuerst angekündigt", "vorwissen": "rot"},
        {"topic_id": 2, "label": "danach angekündigt", "vorwissen": "rot"},
    ]
    monkeypatch.setattr(exam_effort, "_konzept_schluessel", lambda t: [])
    monkeypatch.setattr(exam_effort, "_konzept_ids", lambda t: [])
    sortiert = [z["label"] for z in exam_effort._lernreihenfolge(zeilen)]
    assert sortiert == ["zuerst angekündigt", "danach angekündigt"]


# ---------------------------------------------------------------- Z6 / Z7

def _ablösung() -> str:
    import pathlib
    return (pathlib.Path(__file__).resolve().parents[1]
            / "docs" / "ABLOESUNG_KLASSISCH.md").read_text(encoding="utf-8")


def test_z6_der_klassische_weg_ist_eingefroren():
    """Eingefroren heißt: jede Änderung ist eine Entscheidung.

    Wird dieser Test rot, ist das kein Fehler im Test. Entweder gehört die
    Änderung in den adaptiven Weg — oder sie ist eine bewusste Fehlerbehebung
    und die neue Zahl wird in `docs/ABLOESUNG_KLASSISCH.md` eingetragen,
    mitsamt Begründung.
    """
    import hashlib
    import pathlib
    import re

    wurzel = pathlib.Path(__file__).resolve().parents[1]
    notiert = dict(re.findall(r"\|\s*`(app/[\w/]+\.py)`\s*\|\s*`([0-9a-f]{64})`\s*\|",
                              _ablösung()))

    assert set(notiert) == {"app/teaching.py", "app/quizzes.py"}
    for datei, summe in notiert.items():
        ist = hashlib.sha256((wurzel / datei).read_bytes()).hexdigest()
        assert ist == summe, f"{datei} hat sich geändert — siehe ABLOESUNG_KLASSISCH.md"


def test_z7_jeder_maßstab_hat_sein_eigenes_wort(app_env):
    """Drei Maßstäbe trugen „sitzt" und dieselbe Farbe. Jetzt nicht mehr."""
    from app import domain
    from app.routers import adaptiv

    # Ein ganzes Thema, belegt über Tage.
    assert domain.FLAG_LABELS[domain.Flag.GRUEN.value] == "Thema sicher"
    # Eine einzelne Fehlvorstellung, adaptiv überwunden.
    assert adaptiv.STAND_LABELS["sicher"] == "verstanden"
    # Und keins von beiden benutzt das Wort des anderen.
    assert "sicher" not in adaptiv.STAND_LABELS["sicher"]
    assert "verstanden" not in domain.FLAG_LABELS.values()


def test_z7_gruen_gehoert_nur_dem_thema(app_env):
    """Die Farbe ist für das Thema reserviert — ein verstandener Denkfehler
    ist ein Schritt dorthin, nicht das Ziel."""
    from app.routers import adaptiv

    for wort in adaptiv.STAND_LABELS.values():
        assert "grün" not in wort.lower() and "gruen" not in wort.lower(), wort


def test_z7_die_abgeloesten_woerter_stehen_nirgends_mehr(app_env):
    """Dieselbe Sache zweimal benannt ist schlimmer als unbenannt."""
    import pathlib

    wurzel = pathlib.Path(__file__).resolve().parents[1] / "app"
    treffer = []
    for pfad in list(wurzel.rglob("*.py")) + list(wurzel.rglob("*.html")):
        text = pfad.read_text(encoding="utf-8")
        for altes_wort in ("Themenprüfung", "Erste Prüfung starten"):
            if altes_wort in text:
                treffer.append(f"{pfad.name}: {altes_wort}")
    assert not treffer, treffer


def test_z6_die_ablöseschritte_stehen_geschrieben():
    """Ohne Reihenfolge wird aus „eingefroren" stilles Liegenlassen."""
    text = _ablösung()
    assert "Ersteinschätzung" in text and "verstanden" in text
    assert "Thema sicher" in text
    for datei in ("app/teaching.py", "app/quizzes.py"):
        assert datei in text
