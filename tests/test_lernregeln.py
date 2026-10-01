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


