"""Einstufung: erst prüfen, dann schätzen.

Eine Minutenangabe ohne Einstufung ist geraten. Deshalb steht der Schritt
vor dem Kalender, und sein Ergebnis schlägt jede andere Quelle.
"""
from __future__ import annotations

import json


def _konzept_mit_aufgaben(app_env, thema, fach="mathematik", richtig=("4", "9")):
    """Ein geprüftes Konzept mit zwei freigegebenen Kontrollaufgaben."""
    from app import db
    from app.adaptiv.normalisierung import normalisiere
    db.init()
    schluessel = normalisiere(thema).replace(" ", "-")
    with db.tx() as c:
        konzept_id = c.execute(
            """INSERT INTO lern_konzept(fach,thema_key,konzept_key,label,
                                        klasse_von,klasse_bis,geprueft_am,created_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            (fach, schluessel, schluessel, thema, 6, 8, db.now(), db.now())).lastrowid
        fehlertyp_id = c.execute(
            """INSERT INTO lern_fehlertyp(konzept_id,fehler_key,label,beschreibung,
                                          geprueft_am,created_at)
               VALUES(?,?,?,?,?,?)""",
            (konzept_id, "grundfehler", "Grundfehler", "Testfehler",
             db.now(), db.now())).lastrowid
        for nr, loesung in enumerate(richtig):
            c.execute(
                """INSERT INTO lern_aufgabe(fehlertyp_id,rolle,position,frage,loesung,
                                            antwort_art,aktiv,geprueft_am,created_at)
                   VALUES(?,?,?,?,?,?,1,?,?)""",
                (fehlertyp_id, "selbststaendig", nr, f"Aufgabe {nr + 1} zu {thema}",
                 loesung, "text", db.now(), db.now()))
    return konzept_id


def _arbeit_mit_thema(app_env, thema):
    from app.services import learning_hub
    from app import db
    db.init()
    with db.tx() as c:
        exam_id = c.execute(
            "INSERT INTO exam(subject,exam_date,themen,created_at) VALUES(?,?,?,?)",
            ("mathematik", "2026-11-20", json.dumps([thema]), db.now())).lastrowid
    learning_hub.link_exam(exam_id, [thema], "mathematik")
    return exam_id, learning_hub.exam_topics(exam_id)[0]


def test_ohne_geprüfte_aufgaben_gibt_es_nichts_zu_fragen(app_env):
    from app.services import exam_placement
    exam_id, thema = _arbeit_mit_thema(app_env, "Thema ganz ohne Inhalte")
    assert exam_placement.naechstes_thema(exam_id) is None
    assert exam_placement.oeffnen(exam_id, thema["id"]) is None
    stand = exam_placement.stand(exam_id)
    assert stand["moeglich"] == 0 and stand["ohne_aufgaben"] == 1
    assert not stand["vollstaendig"]


def test_beide_richtig_ergibt_gruen_und_senkt_die_zeit(app_env):
    from app.services import exam_effort, exam_placement
    _konzept_mit_aufgaben(app_env, "Brüche kürzen")
    exam_id, thema = _arbeit_mit_thema(app_env, "Brüche kürzen")

    vorher = exam_effort.bedarf(exam_id)
    assert vorher["themen"][0]["vorwissen"] == "weiss"

    offen = exam_placement.oeffnen(exam_id, thema["id"])
    assert offen and len(offen["questions"]) == 2
    loesungen = {str(i): f["loesung"] for i, f in enumerate(offen["questions"])}
    exam_placement.abgeben(exam_id, thema["id"], loesungen)

    assert exam_placement.ergebnis(exam_id) == {thema["id"]: "gruen"}
    nachher = exam_effort.bedarf(exam_id)
    assert nachher["themen"][0]["vorwissen"] == "gruen"
    assert nachher["themen"][0]["quelle"] == "in der Einstufung gezeigt"
    assert nachher["eingestuft"] == 1
    # Was sitzt, braucht weniger Zeit — genau darum geht es.
    assert nachher["min"] < vorher["min"]


def test_keine_richtig_ergibt_rot_und_erhoeht_die_zeit(app_env):
    from app.services import exam_effort, exam_placement
    _konzept_mit_aufgaben(app_env, "Pythagoras anwenden")
    exam_id, thema = _arbeit_mit_thema(app_env, "Pythagoras anwenden")
    vorher = exam_effort.bedarf(exam_id)["min"]

    offen = exam_placement.oeffnen(exam_id, thema["id"])
    exam_placement.abgeben(exam_id, thema["id"],
                           {str(i): "völlig daneben" for i in range(len(offen["questions"]))})
    nachher = exam_effort.bedarf(exam_id)
    assert nachher["themen"][0]["vorwissen"] == "rot"
    assert nachher["min"] > vorher


def test_halb_richtig_ergibt_gelb(app_env):
    from app.services import exam_placement
    _konzept_mit_aufgaben(app_env, "Terme vereinfachen")
    exam_id, thema = _arbeit_mit_thema(app_env, "Terme vereinfachen")
    offen = exam_placement.oeffnen(exam_id, thema["id"])
    antworten = {"0": offen["questions"][0]["loesung"], "1": "falsch"}
    ergebnis = exam_placement.abgeben(exam_id, thema["id"], antworten)
    assert ergebnis["flagge"] == "gelb"


def test_die_einstufung_schlaegt_den_namensabgleich(app_env):
    """Ein Namenstreffer ist ein Indiz. Eine Abfrage ist ein Beleg."""
    from app import topics, db
    from app.services import exam_effort, exam_placement
    _konzept_mit_aufgaben(app_env, "Prozentwert berechnen")
    # Ein eigenes Thema mit gleichem Namen steht auf "gruen" …
    tid = topics.anlegen("Prozentwert berechnen", subject="mathematik")
    with db.tx() as c:
        c.execute("UPDATE topic SET state='aktiv' WHERE id=?", (tid,))
        c.execute("""INSERT INTO topic_flag(topic_id,flag,antworten,richtig,computed_at)
                     VALUES(?,'gruen',6,6,?)""", (tid, db.now()))
    exam_id, thema = _arbeit_mit_thema(app_env, "Prozentwert berechnen")
    assert exam_effort.bedarf(exam_id)["themen"][0]["vorwissen"] == "gruen"

    # … die Abfrage zeigt aber, dass es nicht sitzt. Der Beleg gewinnt.
    offen = exam_placement.oeffnen(exam_id, thema["id"])
    exam_placement.abgeben(exam_id, thema["id"],
                           {str(i): "nein" for i in range(len(offen["questions"]))})
    zeile = exam_effort.bedarf(exam_id)["themen"][0]
    assert zeile["vorwissen"] == "rot"
    assert zeile["quelle"] == "in der Einstufung gezeigt"


def test_abgegeben_bleibt_abgegeben(app_env):
    from app.services import exam_placement
    _konzept_mit_aufgaben(app_env, "Winkel berechnen")
    exam_id, thema = _arbeit_mit_thema(app_env, "Winkel berechnen")
    offen = exam_placement.oeffnen(exam_id, thema["id"])
    erst = exam_placement.abgeben(exam_id, thema["id"],
                                  {str(i): f["loesung"] for i, f in enumerate(offen["questions"])})
    nochmal = exam_placement.abgeben(exam_id, thema["id"], {"0": "anders", "1": "anders"})
    assert nochmal["flagge"] == erst["flagge"] == "gruen"
    # Und das Thema taucht nicht wieder als nächstes auf.
    assert exam_placement.naechstes_thema(exam_id) is None
    assert exam_placement.stand(exam_id)["vollstaendig"]


def test_die_einstufung_gehoert_dem_kind(client, fake_llm, fake_cli, app_env):
    """Sie ist eine Abfrage: was dabei herauskommt, steht danach als Können
    des Kindes in der Planung. Eltern dürfen zusehen, aber nicht antworten —
    sonst plant Karo die Prüfung nach dem Wissen der Erwachsenen."""
    from app.main import _eltern_darf_aendern, _kind_erlaubt
    # Mit Freigabe kommt das Kind an seine Einstufung.
    assert _kind_erlaubt('/klassenarbeit/6/einstufung', klassenarbeit_kind=True)
    assert _kind_erlaubt('/klassenarbeit/6/einstufung/42', klassenarbeit_kind=True)
    # Ohne Freigabe bleibt der ganze Prüfungsbereich Elternsache.
    assert not _kind_erlaubt('/klassenarbeit/6/einstufung', klassenarbeit_kind=False)
    # Eltern sehen die Seite, geben aber nicht ab.
    assert _eltern_darf_aendern('/klassenarbeit/6/einstufung')
    assert not _eltern_darf_aendern('/klassenarbeit/6/einstufung/42')
