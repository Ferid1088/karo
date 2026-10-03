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


# ---------------------------------------------------------------- c) Wiederholung

def test_das_kind_waehlt_den_abstand_selbst(app_env):
    from app.adaptiv import wiederholung
    konzept_id = _konzept(app_env)
    heute = dt.date(2026, 5, 4)

    moeglichkeiten = wiederholung.auswahl(konzept_id, heute)

    assert [m["tage"] for m in moeglichkeiten] == [2, 3, 4, 5]
    assert moeglichkeiten[0]["datum"] == "2026-05-06"
    assert sum(1 for m in moeglichkeiten if m["empfohlen"]) == 1


def test_vor_einer_klassenarbeit_wird_der_tag_davor_vorgeschlagen(app_env):
    from app import db
    from app.adaptiv import wiederholung
    _konzept(app_env)
    heute = dt.date(2026, 5, 4)
    with db.tx() as c:                      # Arbeit am Freitag, also Donnerstag üben
        c.execute("INSERT INTO exam (subject, exam_date, titel, created_at) "
                  "VALUES ('mathematik', '2026-05-08', 'Brüche', ?)", (db.now(),))

    assert wiederholung.vorschlag(heute=heute) == 3      # 4. + 3 Tage = 7. Mai
    empfohlen = [m for m in wiederholung.auswahl(heute=heute) if m["empfohlen"]]
    assert empfohlen[0]["datum"] == "2026-05-07"


def test_eine_arbeit_ausserhalb_der_auswahl_verschiebt_nichts(app_env):
    from app import db
    from app.adaptiv import wiederholung
    _konzept(app_env)
    heute = dt.date(2026, 5, 4)
    with db.tx() as c:                      # erst in drei Wochen
        c.execute("INSERT INTO exam (subject, exam_date, titel, created_at) "
                  "VALUES ('mathematik', '2026-05-25', 'Brüche', ?)", (db.now(),))

    assert wiederholung.vorschlag(heute=heute) == 3      # die Mitte, wie sonst


def test_eine_verpasste_wiederholung_bleibt_offen_stehen(app_env):
    from app.adaptiv import wiederholung
    konzept_id = _konzept(app_env)
    wiederholung.planen(konzept_id, 2, heute=dt.date(2026, 5, 1))   # fällig am 3.

    offen = wiederholung.offene(bis=dt.date(2026, 5, 9))

    assert len(offen) == 1
    assert offen[0]["faellig_am"] == "2026-05-03"
    assert offen[0]["verpasst"] is True
    # Und sie ist vor dem Termin noch nicht dran:
    assert wiederholung.offene(bis=dt.date(2026, 5, 2)) == []


def test_bestanden_macht_das_konzept_gefestigt(app_env):
    from app.adaptiv import wiederholung
    konzept_id = _konzept(app_env)
    termin = wiederholung.planen(konzept_id, 3, heute=dt.date(2026, 5, 1))

    assert not wiederholung.gefestigt(konzept_id)
    wiederholung.abschliessen(termin["id"], bestanden_=True,
                              ergebnis_daten={"richtig": 4, "gesamt": 4})

    assert wiederholung.gefestigt(konzept_id)
    assert wiederholung.offene(bis=dt.date(2026, 5, 9)) == []


def test_nicht_bestanden_ist_kein_minus(app_env):
    from app.adaptiv import wiederholung
    konzept_id = _konzept(app_env)
    termin = wiederholung.planen(konzept_id, 3, heute=dt.date(2026, 5, 1))
    wiederholung.abschliessen(termin["id"], bestanden_=False,
                              ergebnis_daten={"richtig": 2, "gesamt": 4})

    assert not wiederholung.gefestigt(konzept_id)
    # Danach waehlt das Kind wieder: ein neuer Termin, kein Abzug.
    neu = wiederholung.planen(konzept_id, 2, heute=dt.date(2026, 5, 4))
    assert neu["id"] != termin["id"] and neu["faellig_am"] == "2026-05-06"
    assert wiederholung.eintrag(termin["id"])["status"] == "nicht_bestanden"


def test_die_wiederholung_stellt_neue_aufgaben(app_env):
    """Dieselbe Aufgabe noch einmal misst Erinnerung, nicht Koennen."""
    from app.adaptiv import protokoll, unterricht, wiederholung
    konzept_id = _konzept(app_env)
    sitzung = unterricht.starte(konzept_id, "Brüche")
    unterricht.bildschirm(sitzung)
    sitzung = unterricht.anker_beantwortet(sitzung, "weiß nicht")
    unterricht.bildschirm(sitzung)
    unterricht.diagnose_beantwortet(sitzung, "2/5")

    aufgaben = wiederholung.pruefaufgaben(konzept_id)
    gesehen = protokoll.gesehene_aufgaben(konzept_id)

    assert 3 <= len(aufgaben) <= 5
    assert all(a.get("id") is None or a["id"] not in gesehen for a in aufgaben)
    assert all(a.get("frage") and a.get("loesung") for a in aufgaben)


def test_varianten_rechnen_ihre_loesung_selbst_nach(app_env):
    import random
    from fractions import Fraction
    from app.adaptiv import varianten
    vorlage = {"frage": "Rechne: 1/2 + 1/3", "loesung": "5/6", "antwort_art": "bruch"}

    neue = varianten.varianten(vorlage, 3, zufall=random.Random(7))

    assert len(neue) == 3
    assert all(v["frage"] != vorlage["frage"] for v in neue)
    for v in neue:
        zahlen = v["frage"].rsplit(":", 1)[-1]
        links, rechts = zahlen.split("+")
        assert Fraction(links.strip()) + Fraction(rechts.strip()) == Fraction(v["loesung"])


def test_ohne_erkennbares_muster_erfindet_der_generator_nichts(app_env):
    from app.adaptiv import varianten
    assert varianten.varianten({"frage": "Warum ist das so?", "loesung": "ja"}) == []


def test_bestanden_ist_nur_wer_alle_neuen_aufgaben_kann(app_env):
    from app.adaptiv import wiederholung
    aufgaben = [{"frage": "1/2 + 1/4", "loesung": "3/4"},
                {"frage": "1/3 + 1/6", "loesung": "1/2"}]

    gut = wiederholung.auswerten(aufgaben, ["6/8", "1/2"])     # gekürzt zählt
    halb = wiederholung.auswerten(aufgaben, ["3/4", "2/9"])

    assert gut["bestanden"] and gut["richtig"] == 2
    assert not halb["bestanden"] and halb["richtig"] == 1


def test_der_check_legt_seine_aufgaben_einmal_fest(app_env):
    """Neuladen darf nicht andere Aufgaben zeigen als die gerade beantworteten."""
    from app.adaptiv import wiederholung
    konzept_id = _konzept(app_env)
    termin = wiederholung.planen(konzept_id, 2, heute=dt.date(2026, 5, 1))

    erste = wiederholung.check_aufgaben(termin["id"])
    zweite = wiederholung.check_aufgaben(termin["id"])

    assert erste and erste == zweite
    assert wiederholung.eintrag(termin["id"])["ergebnis"]["aufgaben"] == erste


def test_die_aufgaben_des_checks_bleiben_im_ergebnis(app_env):
    from app.adaptiv import wiederholung
    konzept_id = _konzept(app_env)
    termin = wiederholung.planen(konzept_id, 2, heute=dt.date(2026, 5, 1))
    gestellt = wiederholung.check_aufgaben(termin["id"])

    ergebnis = wiederholung.auswerten(gestellt, [a["loesung"] for a in gestellt])
    eintrag = wiederholung.abschliessen(termin["id"], bestanden_=ergebnis["bestanden"],
                                        ergebnis_daten={"richtig": ergebnis["richtig"]})

    assert eintrag["status"] == "bestanden"
    assert eintrag["ergebnis"]["aufgaben"] == gestellt    # nichts geht verloren
    assert eintrag["ergebnis"]["richtig"] == len(gestellt)


def test_faellige_wiederholung_steht_unter_heute(app_env):
    """Am richtigen lokalen Tag — nicht frueher, nicht spaeter."""
    from app.adaptiv import wiederholung
    from app.services import today
    konzept_id = _konzept(app_env)
    wiederholung.planen(konzept_id, 2, heute=dt.date(2026, 5, 1))   # fällig am 3.

    vorher = today.mein_tag(dt.date(2026, 5, 2))
    assert not [i for i in vorher["items"] if i["kind"] == "wiederholung"]

    tag = today.mein_tag(dt.date(2026, 5, 3))

    treffer = [i for i in tag["items"] if i["kind"] == "wiederholung"]
    assert len(treffer) == 1
    assert treffer[0]["title"].startswith("Wiederholen:")
    assert treffer[0]["done"] is False
    assert treffer[0]["verpasst"] is False


def test_verpasste_wiederholung_bleibt_unter_heute_stehen(app_env):
    from app.adaptiv import wiederholung
    from app.services import today
    konzept_id = _konzept(app_env)
    wiederholung.planen(konzept_id, 2, heute=dt.date(2026, 5, 1))   # fällig am 3.

    tag = today.mein_tag(dt.date(2026, 5, 9))                    # eine Woche später

    treffer = [i for i in tag["items"] if i["kind"] == "wiederholung"]
    assert len(treffer) == 1
    assert treffer[0]["done"] is False
    assert treffer[0]["verpasst"] is True


def test_ein_heute_bestandener_check_steht_abgehakt_da(app_env):
    from app.adaptiv import wiederholung
    from app.services import today
    from app.woche import plaene
    konzept_id = _konzept(app_env)
    heute = plaene.today()
    termin = wiederholung.planen(konzept_id, 2, heute=heute - dt.timedelta(days=2))
    aufgaben = wiederholung.check_aufgaben(termin["id"])
    ergebnis = wiederholung.auswerten(aufgaben, [a["loesung"] for a in aufgaben])
    wiederholung.abschliessen(termin["id"], bestanden_=ergebnis["bestanden"])

    treffer = [i for i in today.mein_tag(heute)["items"] if i["kind"] == "wiederholung"]

    assert len(treffer) == 1
    assert treffer[0]["done"] is True


# ------------------------------------------------- der Weg durch die App

def _kind_und_faelliger_termin(client, fake_llm, app_env):
    """Kind angemeldet, adaptiver Weg an, eine Wiederholung faellig."""
    from app.adaptiv import wiederholung
    from app.woche import plaene
    from .test_app import einrichten, kind_modus_aktivieren
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True, learner_grade=6)
    kind_modus_aktivieren(client)
    konzept_id = _konzept(app_env)
    heute = plaene.today()
    termin = wiederholung.planen(konzept_id, 2,
                                 heute=heute - dt.timedelta(days=2))
    return termin, konzept_id


def test_faellige_wiederholung_erscheint_auf_der_heute_seite(client, fake_llm,
                                                            app_env):
    termin, _ = _kind_und_faelliger_termin(client, fake_llm, app_env)

    seite = client.get("/")

    assert "Wiederholen:" in seite.text
    assert f"/lernen/adaptiv/wiederholung/{termin['id']}" in seite.text


def test_bestandener_check_festigt_das_konzept(client, fake_llm,
                                              app_env):
    from app.adaptiv import wiederholung
    from .conftest import csrf_from
    termin, konzept_id = _kind_und_faelliger_termin(client, fake_llm,
                                                    app_env)

    seite = client.get(f"/lernen/adaptiv/wiederholung/{termin['id']}")
    assert "kurzer Check" in seite.text
    token = csrf_from(seite.text)

    aufgaben = wiederholung.check_aufgaben(termin["id"])
    seite = client.post(f"/lernen/adaptiv/wiederholung/{termin['id']}",
                        data={"_csrf": token,
                              "antwort": [a["loesung"] for a in aufgaben]})

    assert "gefestigt" in seite.text
    assert wiederholung.gefestigt(konzept_id)
    assert wiederholung.eintrag(termin["id"])["status"] == "bestanden"


def test_verpatzter_check_endet_in_auffrischung_und_neuer_wahl(
        client, fake_llm, app_env):
    """Kein Minus: kurz auffrischen, dann waehlt das Kind wieder selbst."""
    from app.adaptiv import wiederholung
    from .conftest import csrf_from
    termin, konzept_id = _kind_und_faelliger_termin(client, fake_llm,
                                                    app_env)
    seite = client.get(f"/lernen/adaptiv/wiederholung/{termin['id']}")
    token = csrf_from(seite.text)

    aufgaben = wiederholung.check_aufgaben(termin["id"])
    seite = client.post(f"/lernen/adaptiv/wiederholung/{termin['id']}",
                        data={"_csrf": token,
                              "antwort": ["falsch"] * len(aufgaben)})

    assert "noch einmal an" in seite.text                     # Auffrischung
    assert wiederholung.eintrag(termin["id"])["status"] == "nicht_bestanden"
    assert not wiederholung.gefestigt(konzept_id)

    seite = client.post(
        f"/lernen/adaptiv/wiederholung/{termin['id']}/auffrischung",
        data={"_csrf": token, "antwort": "egal"})
    assert "noch einmal machen" in seite.text                 # neue Wahl

    client.post(f"/lernen/adaptiv/wiederholung/{termin['id']}/termin",
                data={"_csrf": token, "tage": "3"})

    neu = wiederholung.offen_fuer(konzept_id)
    assert neu is not None and neu["id"] != termin["id"]


def test_verstanden_ist_noch_nicht_thema_sicher(app_env):
    """Z7 und Z4 zusammen: „Thema sicher" wartet auf die Wiederholung.

    Sonst verspricht die Oberflaeche Sicherheit, die erst die Klassenarbeit
    widerlegt — und der Lernplan streicht das Thema vorzeitig aus der Zeit.
    """
    from app.adaptiv import sitzung as zustand, store, unterricht, wiederholung
    from app.services import learning_hub
    from app import topics
    konzept_id = _konzept(app_env)
    konzept = store.konzept(konzept_id)
    topic_id = topics.anlegen(konzept["label"], subject=konzept["fach"])
    sitzung = unterricht.starte(konzept_id, konzept["label"], topic_id)
    zustand.wechsle(sitzung["id"], zustand.MASTERED, "verstanden")

    zeile = learning_hub.decorate([dict(topics.get(topic_id))])[0]
    assert zeile["learning_status"] == "verstanden"
    assert zeile["status_label"] == "Verstanden"

    # Der Termin gehoert zum Lernraum des Themas — wie `wiederholung_gewaehlt`
    # ihn im Laufzeitpfad setzt.
    termin = wiederholung.planen(
        konzept_id, 2, sitzung_id=sitzung["id"],
        child_key=store.fortschritt_scope(sitzung))
    wiederholung.abschliessen(termin["id"], bestanden_=True)

    zeile = learning_hub.decorate([dict(topics.get(topic_id))])[0]
    assert zeile["learning_status"] == "sicher"
