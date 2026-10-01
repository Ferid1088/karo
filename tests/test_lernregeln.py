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


