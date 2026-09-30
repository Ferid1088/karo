"""Zeitbedarf einer Klassenarbeit: Vorwissen prüfen, Minuten schätzen, verteilen."""
from __future__ import annotations

import datetime as dt
import json

import pytest


def _arbeit(app_env, themen, tag="2026-10-20"):
    from app import topics as topic_modul
    from app.services import learning_hub
    app_env.db.init()
    with app_env.db.tx() as c:
        exam_id = c.execute(
            "INSERT INTO exam(subject,exam_date,themen,created_at) VALUES(?,?,?,?)",
            ("mathematik", tag, json.dumps(themen), app_env.db.now())).lastrowid
    learning_hub.link_exam(exam_id, themen, "mathematik")
    return exam_id


def _eigenes_thema(app_env, label, flag):
    """Ein eigenes Thema des Kindes mit einer Flagge — das ist das Vorwissen."""
    from app import topics
    app_env.db.init()
    tid = topics.anlegen(label, subject="mathematik")
    with app_env.db.tx() as c:
        c.execute("UPDATE topic SET state='aktiv' WHERE id=?", (tid,))
        c.execute("""INSERT INTO topic_flag(topic_id,flag,antworten,richtig,computed_at)
                     VALUES(?,?,?,?,?)
                     ON CONFLICT(topic_id) DO UPDATE SET flag=excluded.flag""",
                  (tid, flag, 4, 2, app_env.db.now()))
    return tid


def test_ohne_vorwissen_rechnet_karo_mit_dem_vollen_aufwand(app_env):
    from app.services import exam_effort
    exam_id = _arbeit(app_env, ["Terme vereinfachen", "Klammern auflösen", "Probe durchführen"])
    stand = exam_effort.bedarf(exam_id)
    assert all(z["vorwissen"] == "weiss" for z in stand["themen"])
    # Drei unbekannte Themen: die Anzeige nennt eine runde Spanne.
    assert stand["min"] == 60 and stand["max"] == 80
    assert stand["offen"] == 3


def test_vorwissen_aus_eigenen_themen_senkt_die_schaetzung(app_env):
    """Ein Prüfungsthema startet ohne Belege. Was das Kind unter leicht
    anderem Namen schon gezeigt hat, zaehlt trotzdem für die Schaetzung."""
    from app.services import exam_effort
    _eigenes_thema(app_env, "Klammern auflösen", "gruen")
    _eigenes_thema(app_env, "Probe durchführen", "rot")
    exam_id = _arbeit(app_env, ["Terme vereinfachen",
                                "Klammern auflösen und ausmultiplizieren",
                                "Probe durchführen"])
    nach_label = {z["label"]: z for z in exam_effort.bedarf(exam_id)["themen"]}
    assert nach_label["Terme vereinfachen"]["vorwissen"] == "weiss"
    assert nach_label["Klammern auflösen und ausmultiplizieren"]["vorwissen"] == "gruen"
    assert nach_label["Probe durchführen"]["vorwissen"] == "rot"
    # Sicheres braucht am wenigsten, belegte Fehler am meisten.
    assert (nach_label["Klammern auflösen und ausmultiplizieren"]["min"]
            < nach_label["Terme vereinfachen"]["min"]
            < nach_label["Probe durchführen"]["min"])


def test_der_zuschlag_steckt_in_der_zahl_und_wird_nicht_genannt(app_env):
    """Auf jede Schaetzung kommen still 20 Prozent. Genannt wird nur das
    Ergebnis — sonst rechnet man den Aufschlag wieder heraus."""
    from app.services import exam_effort
    exam_id = _arbeit(app_env, ["Terme vereinfachen"])
    zeile = exam_effort.bedarf(exam_id)["themen"][0]
    roh_unten, roh_oben = exam_effort.MINUTEN["weiss"]
    assert zeile["min"] == exam_effort._runden(roh_unten * exam_effort.ZUSCHLAG)
    assert zeile["max"] == exam_effort._runden(roh_oben * exam_effort.ZUSCHLAG)
    assert zeile["min"] > roh_unten


def test_zu_wenig_zeit_wird_gemeldet_aber_nicht_verhindert(app_env, monkeypatch):
    from app.services import exam_calendar, exam_effort
    exam_id = _arbeit(app_env, ["Terme vereinfachen", "Klammern auflösen"])
    monkeypatch.setattr("app.db.today", lambda: "2026-10-01")
    exam_calendar.save_days(exam_id, {"2026-10-02": 10, "2026-10-03": 5})
    lage = exam_effort.lage(exam_id)
    assert lage["gewaehlt"] == 15
    assert not lage["reicht"]
    assert lage["fehlend"] == lage["min"] - 15
    # Gespeichert ist es trotzdem: das Kind entscheidet.
    assert exam_calendar.get_days(exam_id) == {"2026-10-02": 10, "2026-10-03": 5}


def test_themen_werden_nach_minuten_und_reihenfolge_verteilt(app_env):
    from app.services import exam_effort
    exam_id = _arbeit(app_env, ["Erstes Thema", "Zweites Thema", "Drittes Thema"])
    zeilen = exam_effort.bedarf(exam_id)["themen"]
    je = zeilen[0]["min"]          # alle unbekannt, also gleich viel
    tage = [(dt.date(2026, 10, 2), je), (dt.date(2026, 10, 3), je * 2)]
    plan = exam_effort.verteilung(exam_id, tage)
    assert [z["label"] for z in plan["2026-10-02"]] == ["Erstes Thema"]
    # Der zweite Tag hat Platz für zwei Themen — in der angekündigten Folge.
    assert [z["label"] for z in plan["2026-10-03"]] == ["Zweites Thema", "Drittes Thema"]
    assert sum(z["minuten"] for tag in plan.values() for z in tag) == je * 3


def test_ein_langes_thema_laeuft_ueber_mehrere_tage(app_env):
    from app.services import exam_effort
    exam_id = _arbeit(app_env, ["Ein grosses Thema"])
    je = exam_effort.bedarf(exam_id)["themen"][0]["min"]
    plan = exam_effort.verteilung(exam_id, [(dt.date(2026, 10, 2), 5),
                                            (dt.date(2026, 10, 3), 5)])
    assert plan["2026-10-02"][0]["minuten"] == 5
    assert plan["2026-10-03"][0]["minuten"] == 5
    assert plan["2026-10-02"][0]["topic_id"] == plan["2026-10-03"][0]["topic_id"]
    assert je > 10  # der Rest bleibt offen, der Hinweis im Kalender sagt das


def test_karo_behauptet_kein_wissen_das_es_nicht_hat(app_env):
    """"weiss" heisst nicht "kann es nicht", sondern "noch nie zusammen
    geübt". Die Zahlen dafür muss die Oberfläche trennen können, sonst
    klingt eine Vorsichtsannahme wie eine Messung."""
    from app.services import exam_effort
    ohne = exam_effort.bedarf(_arbeit(app_env, ["Ganz neues Thema", "Noch eins"]))
    assert ohne["belegt"] == 0 and ohne["ohne_beleg"] == 2

    _eigenes_thema(app_env, "Prozentwert berechnen", "gelb")
    mit = exam_effort.bedarf(_arbeit(app_env, ["Prozentwert berechnen", "Ganz neu"],
                                     tag="2026-11-20"))
    assert mit["belegt"] == 1 and mit["ohne_beleg"] == 1


def test_fehlende_inhalte_werden_beim_speichern_angefordert(app_env, monkeypatch):
    """Zu einem frisch eingetragenen Prüfungsthema gibt es keine geprüften
    Aufgaben. Ohne die kann Karo weder einstufen noch üben — der Auftrag
    dafür muss beim Speichern entstehen, nicht erst beim Öffnen."""
    from app.services import exam_effort
    exam_id = _arbeit(app_env, ["Pythagoras anwenden", "Winkel berechnen"])
    app_env.config.update(adaptive_learning_enabled=True)

    angefordert = []
    monkeypatch.setattr("app.adaptiv.erzeugung.anfordern",
                        lambda thema, fach, klasse=None: angefordert.append(thema) or 1)
    monkeypatch.setattr("app.adaptiv.lektionen.fuer_thema",
                        lambda *a, **k: None)
    assert exam_effort.inhalte_anfordern(exam_id) == 2
    assert sorted(angefordert) == ["Pythagoras anwenden", "Winkel berechnen"]

    # Ist die adaptive Schicht aus, entsteht kein Auftrag ins Leere.
    app_env.config.update(adaptive_learning_enabled=False)
    angefordert.clear()
    assert exam_effort.inhalte_anfordern(exam_id) == 0
    assert angefordert == []


def test_die_herkunft_der_einschaetzung_steht_dabei(app_env):
    """Der Abgleich läuft über Namensähnlichkeit. Das ist ein Indiz, kein
    Beweis — also muss dabeistehen, worauf es beruht."""
    from app.services import exam_effort
    _eigenes_thema(app_env, "Bruchteile", "rot")
    exam_id = _arbeit(app_env, ["Bruchteile eines Ganzen", "Etwas ganz Neues"])
    nach_label = {z["label"]: z for z in exam_effort.bedarf(exam_id)["themen"]}
    assert nach_label["Bruchteile eines Ganzen"]["quelle"] == 'aus deinem Thema „Bruchteile“'
    assert nach_label["Etwas ganz Neues"]["quelle"] == ""
