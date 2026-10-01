"""Schritt 4a: einzelne Antworten, aktive Zeit, Wiederholung.

Drei Grundlagen, die bisher fehlten. Ohne sie weiss Karo nur, wie eine
Sitzung ausging — nicht, was ein Kind auf eine Aufgabe geantwortet hat, wie
lange es wirklich daran war und ob es das in drei Tagen noch kann.
"""
from __future__ import annotations

import datetime as dt


def _konzept(app_env):
    """Ein gesaetes Konzept mit geprueften Aufgaben."""
    from app.adaptiv import store
    app_env.db.init()
    store.init()
    return store.konzepte_verfuegbar()[0]["id"]


# ---------------------------------------------------------------- a) Antworten

def test_jede_beantwortete_aufgabe_schreibt_genau_eine_zeile(app_env):
    from app.adaptiv import protokoll, store, unterricht
    konzept_id = _konzept(app_env)
    sitzung = unterricht.starte(konzept_id, "Brüche")

    unterricht.bildschirm(sitzung)                 # Anker ist zu sehen
    sitzung = unterricht.anker_beantwortet(sitzung, "weiß nicht")
    unterricht.bildschirm(sitzung)                 # Diagnose ist zu sehen
    unterricht.diagnose_beantwortet(sitzung, "2/5")

    zeilen = protokoll.antworten(sitzung_id=sitzung["id"])
    assert [z["rolle"] for z in zeilen] == ["anker", "diagnose"]
    assert zeilen[0]["richtig"] is None            # der Anker wird nicht benotet
    assert zeilen[1]["richtig"] == 0
    assert zeilen[1]["antwort"] == "2/5"
    assert all(z["konzept_id"] == konzept_id for z in zeilen)
    assert all(z["fach"] == store.konzept(konzept_id)["fach"] for z in zeilen)
    assert all(z["gezeigt_at"] for z in zeilen), "ohne gezeigt_at keine Zeitmessung"


def test_eine_zeile_wird_nie_geaendert(app_env):
    """Nur anhaengen: ein Verlauf, der sich nachtraeglich aendert, ist keiner."""
    from app.adaptiv import protokoll, unterricht
    konzept_id = _konzept(app_env)
    sitzung = unterricht.starte(konzept_id, "Brüche")
    unterricht.bildschirm(sitzung)
    sitzung = unterricht.anker_beantwortet(sitzung, "erste Antwort")
    erste = protokoll.antworten(sitzung_id=sitzung["id"])[0]

    unterricht.bildschirm(sitzung)
    unterricht.diagnose_beantwortet(sitzung, "2/5")

    zeilen = protokoll.antworten(sitzung_id=sitzung["id"])
    assert len(zeilen) == 2
    assert zeilen[0] == erste


def test_ein_tipp_steht_in_der_zeile_der_antwort(app_env):
    from app.adaptiv import protokoll, store, unterricht, sitzung as zustand
    konzept_id = _konzept(app_env)
    sitzung = unterricht.starte(konzept_id, "Brüche")
    unterricht.bildschirm(sitzung)
    sitzung = unterricht.anker_beantwortet(sitzung, "weiß nicht")
    unterricht.bildschirm(sitzung)
    sitzung = unterricht.diagnose_beantwortet(sitzung, "2/5")
    sitzung = store.sitzung(sitzung["id"])
    assert sitzung["phase"] == zustand.HOOK

    # Bis zur geführten Aufgabe durchgehen, dort einen Tipp holen.
    for _ in range(6):
        schirm = unterricht.bildschirm(sitzung)
        if schirm["art"] == "aufgabe":
            break
        if schirm["art"] == "vorhersage":
            sitzung = unterricht.vorhersage_beantwortet(sitzung, "mehr")
        else:
            sitzung = unterricht.weiter(sitzung)
        sitzung = store.sitzung(sitzung["id"])
    schirm = unterricht.bildschirm(sitzung)
    assert schirm["art"] == "aufgabe"

    sitzung = unterricht.tipp(sitzung)
    unterricht.aufgabe_beantwortet(store.sitzung(sitzung["id"]), "3/4")

    letzte = protokoll.antworten(sitzung_id=sitzung["id"])[-1]
    assert letzte["rolle"] == "aufgabe"
    assert letzte["tipp_genutzt"] == 1
    assert letzte["aufgabe_id"], "die Zeile nennt die Aufgabe, nicht nur die Phase"


# ---------------------------------------------------------------- b) Aktive Zeit

def _uhr_zurueckdatieren(sitzung_id: int, sekunden: float) -> None:
    """So, als haette das Kind vor `sekunden` zuletzt etwas eingegeben."""
    from app import db
    frueher = (dt.datetime.now(dt.timezone.utc)
               - dt.timedelta(seconds=sekunden)).isoformat(timespec="seconds")
    with db.tx() as c:
        c.execute("UPDATE lern_uhr SET gezeigt_at=?, letzte_eingabe=? "
                  "WHERE sitzung_id=?", (frueher, frueher, sitzung_id))


def test_eine_offene_app_ohne_eingabe_ergibt_null(app_env):
    """Der Kern der Sache: Anwesenheit ist keine Arbeit."""
    from app.adaptiv import protokoll, unterricht
    konzept_id = _konzept(app_env)
    sitzung = unterricht.starte(konzept_id, "Brüche")
    unterricht.bildschirm(sitzung)
    _uhr_zurueckdatieren(sitzung["id"], 3600)      # eine Stunde offen gestanden

    unterricht.anker_beantwortet(sitzung, "endlich")

    zeile = protokoll.antworten(sitzung_id=sitzung["id"])[0]
    assert zeile["aktive_sekunden"] == 0
    assert protokoll.aktive_zeit() == 0


def test_eingaben_halten_die_uhr_am_laufen(app_env):
    from app.adaptiv import protokoll, unterricht
    konzept_id = _konzept(app_env)
    sitzung = unterricht.starte(konzept_id, "Brüche")
    unterricht.bildschirm(sitzung)
    _uhr_zurueckdatieren(sitzung["id"], 20)        # 20 s seit der letzten Eingabe

    assert 19 <= protokoll.puls(sitzung["id"]) <= 21
    _uhr_zurueckdatieren(sitzung["id"], 0)         # gerade eben getippt
    unterricht.anker_beantwortet(sitzung, "fertig")

    zeile = protokoll.antworten(sitzung_id=sitzung["id"])[0]
    assert 19 <= zeile["aktive_sekunden"] <= 22


def test_eine_pause_zaehlt_nicht_mit(app_env):
    """Nach zwei Minuten ohne Eingabe steht die Uhr — ohne Zutun der Seite."""
    from app.adaptiv import protokoll, unterricht
    app_env.config.update(adaptiv_pause_sekunden=120)
    konzept_id = _konzept(app_env)
    sitzung = unterricht.starte(konzept_id, "Brüche")
    unterricht.bildschirm(sitzung)
    _uhr_zurueckdatieren(sitzung["id"], 600)       # zehn Minuten weg

    assert protokoll.puls(sitzung["id"]) == 0


def test_mehr_als_das_doppelte_der_erwartung_zaehlt_nicht(app_env):
    from app import db
    from app.adaptiv import protokoll, unterricht
    konzept_id = _konzept(app_env)
    sitzung = unterricht.starte(konzept_id, "Brüche")
    unterricht.bildschirm(sitzung)
    with db.tx() as c:                              # lange, aber durchgehend aktiv
        c.execute("UPDATE lern_uhr SET aktiv_sekunden=9999 WHERE sitzung_id=?",
                  (sitzung["id"],))
    _uhr_zurueckdatieren(sitzung["id"], 0)

    unterricht.anker_beantwortet(sitzung, "fertig")

    zeile = protokoll.antworten(sitzung_id=sitzung["id"])[0]
    erwartet = protokoll.erwartung("bruch", klasse=6)
    assert zeile["aktive_sekunden"] == 2 * erwartet


def test_unter_der_mindestzeit_zaehlt_null_und_faellt_auf(app_env):
    from app.adaptiv import protokoll, unterricht
    app_env.config.update(adaptiv_mindest_sekunden=3)
    konzept_id = _konzept(app_env)
    sitzung = unterricht.starte(konzept_id, "Brüche")
    unterricht.bildschirm(sitzung)

    unterricht.anker_beantwortet(sitzung, "x")      # sofort, ohne Nachdenken

    zeile = protokoll.antworten(sitzung_id=sitzung["id"])[0]
    assert zeile["aktive_sekunden"] == 0 and zeile["zu_schnell"] == 1


def test_eine_serie_zu_schneller_antworten_ist_nicht_ernsthaft(app_env):
    from app.adaptiv import protokoll, unterricht
    app_env.config.update(adaptiv_nicht_ernsthaft_serie=3)
    konzept_id = _konzept(app_env)
    sitzung = unterricht.starte(konzept_id, "Brüche")

    assert not protokoll.nicht_ernsthaft()
    for antwort in ("a", "b", "c"):
        unterricht.bildschirm(sitzung)
        unterricht.anker_beantwortet(sitzung, antwort)

    assert protokoll.nicht_ernsthaft()


def test_die_erwartung_haengt_an_antwortart_und_klasse(app_env):
    from app.adaptiv import protokoll
    # Eine Auswahl ist schneller entschieden als eine Rechnung.
    assert protokoll.erwartung("auswahl", 6) < protokoll.erwartung("bruch", 6)
    # Juengere bekommen mehr Zeit.
    assert protokoll.erwartung("bruch", 4) > protokoll.erwartung("bruch", 8)
    # Was das Curriculum sagt, schlaegt jede Schaetzung.
    assert protokoll.erwartung("bruch", 6, vorgabe=12) == 12


def test_nach_dem_ende_der_einheit_entsteht_keine_zeit_mehr(app_env):
    from app.adaptiv import protokoll, sitzung as zustand, store, unterricht
    konzept_id = _konzept(app_env)
    sitzung = unterricht.starte(konzept_id, "Brüche")
    unterricht.bildschirm(sitzung)
    _uhr_zurueckdatieren(sitzung["id"], 10)

    zustand.wechsle(sitzung["id"], zustand.MASTERED, "verstanden")

    # Die Seite meldet weiter Eingaben — die Einheit ist trotzdem vorbei.
    assert protokoll.puls(sitzung["id"]) == 0
    unterricht.bildschirm(store.sitzung(sitzung["id"]))
    assert protokoll.uhr(sitzung["id"]) is None
    assert protokoll.aktive_zeit() == 0


def test_aktive_zeit_laesst_sich_nach_fach_und_zeitraum_fragen(app_env):
    from app import db
    from app.adaptiv import protokoll, store, unterricht
    konzept_id = _konzept(app_env)
    fach = store.konzept(konzept_id)["fach"]
    sitzung = unterricht.starte(konzept_id, "Brüche")
    unterricht.bildschirm(sitzung)
    _uhr_zurueckdatieren(sitzung["id"], 30)
    with db.tx() as c:
        c.execute("UPDATE lern_uhr SET aktiv_sekunden=30 WHERE sitzung_id=?",
                  (sitzung["id"],))
    _uhr_zurueckdatieren(sitzung["id"], 0)
    unterricht.anker_beantwortet(sitzung, "fertig")

    heute = str(dt.date.today())
    assert protokoll.aktive_zeit(von=heute, bis=heute, fach=fach) > 0
    assert protokoll.aktive_zeit(von=heute, bis=heute, fach="englisch") == 0
    gestern = str(dt.date.today() - dt.timedelta(days=1))
    assert protokoll.aktive_zeit(von=gestern, bis=gestern) == 0
