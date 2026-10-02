"""Lernzeit: gemessen, wo gemessen wurde — geschaetzt, wo nicht.

Die beiden Quellen duerfen sich nie vermischen, und eine Schaetzung muss im
Bericht als solche erkennbar bleiben.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from .conftest import csrf_from
from .test_app import als_kind, einrichten, kind_modus_aktivieren


def _thema(db, code='M-ZEIT-1', label='Testthema'):
    with db.tx() as c:
        return c.execute(
            "INSERT INTO topic (subject, code, label, state, learning_visible, created_at)"
            " VALUES ('mathematik', ?, ?, 'aktiv', 1, ?)",
            (code, label, db.today())).lastrowid


def _stueck(db, tag, topic_id, sekunden, gemessen_um='10:00:00'):
    """Legt ein gemessenes Stueck direkt an — wie es viele Schlaege taeten."""
    beginn = f'{tag}T{gemessen_um}+00:00'
    with db.tx() as c:
        c.execute("INSERT INTO learning_time(topic_id,tag,beginn,letzter,sekunden)"
                  " VALUES(?,?,?,?,?)", (topic_id, tag, beginn, beginn, sekunden))


def test_schlag_beginnt_und_verlaengert_ein_stueck(client, fake_llm, app_env):
    from app.services import learning_time
    einrichten(client, fake_llm)
    topic_id = _thema(app_env.db)

    # Der erste Schlag belegt noch keine Zeit — erst der Abstand zum zweiten.
    assert learning_time.schlag(topic_id) == 0
    zeilen = app_env.db.q("SELECT * FROM learning_time WHERE topic_id=?", topic_id)
    assert len(zeilen) == 1 and zeilen[0]['sekunden'] == 0

    # Ein Schlag kurz danach verlaengert dasselbe Stueck statt ein neues zu beginnen.
    vorhin = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    with app_env.db.tx() as c:
        c.execute("UPDATE learning_time SET letzter=? WHERE id=?", (vorhin, zeilen[0]['id']))
    assert 28 <= learning_time.schlag(topic_id) <= 32
    assert len(app_env.db.q("SELECT id FROM learning_time WHERE topic_id=?", topic_id)) == 1

    # Nach einer langen Pause beginnt ein neues Stueck.
    lang_her = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    with app_env.db.tx() as c:
        c.execute("UPDATE learning_time SET letzter=? WHERE id=?", (lang_her, zeilen[0]['id']))
    assert learning_time.schlag(topic_id) == 0
    assert len(app_env.db.q("SELECT id FROM learning_time WHERE topic_id=?", topic_id)) == 2


def test_gemessener_tag_schlaegt_die_schaetzung(client, fake_llm, app_env):
    from app.services import learning_time
    einrichten(client, fake_llm)
    topic_id = _thema(app_env.db)
    heute = date.fromisoformat(app_env.db.today())
    _stueck(app_env.db, heute.isoformat(), topic_id, 1500)

    tage = learning_time.zeitraum(heute, heute)['tage']
    assert tage[heute]['gemessen'] is True
    assert tage[heute]['sekunden'] == 1500
    assert tage[heute]['themen'][topic_id] == 1500


def test_tag_ohne_messung_wird_geschaetzt_und_pausen_zaehlen_nicht(app_env):
    from app.services import learning_time
    basis = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)
    # Drei Antworten im Abstand von zwei Minuten, dann eine Stunde Pause.
    punkte = [basis, basis + timedelta(minutes=2), basis + timedelta(minutes=4),
              basis + timedelta(minutes=64)]
    sekunden = learning_time._schaetzung(punkte)
    # 4 Minuten aktiv + Gutschrift fuer den ersten Block + Gutschrift nach der Pause.
    assert sekunden == 4 * 60 + learning_time.GUTSCHRIFT * 2
    # Eine einzelne Aktivitaet ist nicht null Minuten wert.
    assert learning_time._schaetzung([basis]) == learning_time.GUTSCHRIFT
    assert learning_time._schaetzung([]) == 0


def test_dauer_liest_sich_wie_eine_uhrzeit():
    from app.services import learning_time
    assert learning_time.dauer(0) == '0 Min.'
    assert learning_time.dauer(None) == '0 Min.'
    assert learning_time.dauer(90) == '2 Min.'
    assert learning_time.dauer(3900) == '1 Std. 05 Min.'
    assert learning_time.dauer(7200) == '2 Std. 00 Min.'


def test_herzschlag_ordnet_das_thema_dem_pfad_zu(client, fake_llm, app_env):
    einrichten(client, fake_llm)
    topic_id = _thema(app_env.db)
    # Lernzeit misst nur das Kind: eine zusehende Eltern-Sitzung darf sie
    # nicht aufblaehen (siehe test_eltern_nur_ansehen.py).
    with als_kind(client, app_env):
        seite = client.get('/lernstand')
        token = csrf_from(seite.text)

        antwort = client.post('/lernen/zeit',
                              data={'_csrf': token, 'pfad': f'/lernzyklus/{topic_id}'})
        assert antwort.status_code == 200
        zeile = app_env.db.q1("SELECT topic_id FROM learning_time ORDER BY id DESC LIMIT 1")
        assert zeile['topic_id'] == topic_id

        # Ein unbekannter Pfad zaehlt auf den Tag, aber auf kein Thema.
        client.post('/lernen/zeit', data={'_csrf': token, 'pfad': '/lernen'})
        zeile = app_env.db.q1("SELECT topic_id FROM learning_time ORDER BY id DESC LIMIT 1")
        assert zeile['topic_id'] is None


def test_herzschlag_ohne_csrf_wird_abgewiesen(client, fake_llm, app_env):
    einrichten(client, fake_llm)
    with als_kind(client, app_env):
        antwort = client.post('/lernen/zeit', data={'pfad': '/lernen'},
                              follow_redirects=False)
        assert antwort.status_code == 403


def test_lernzeit_steht_im_elternbericht_mit_herkunft(client, fake_llm, app_env):
    from app.services import parent_report
    einrichten(client, fake_llm)
    topic_id = _thema(app_env.db, code='M-ZEIT-2', label='Gemessenes Thema')
    heute = date.fromisoformat(app_env.db.today())
    _stueck(app_env.db, heute.isoformat(), topic_id, 1800)

    bericht = parent_report.build('tag', heute.isoformat())
    assert bericht['work']['seconds'] == 1800
    assert bericht['work']['label'] == '30 Min.'
    assert bericht['work']['measured'] is True
    assert bericht['work']['estimated'] is False
    assert [(t['label'], t['work_label']) for t in bericht['work_topics']] \
        == [('Gemessenes Thema', '30 Min.')]

    seite = client.get(f'/eltern?ansicht=tag&datum={heute.isoformat()}')
    assert seite.status_code == 200
    assert 'Lernzeit' in seite.text and '30 Min.' in seite.text


def test_nur_lernen_und_quiz_zaehlen_als_arbeitszeit(client, fake_llm ):
    """Der Herzschlag laeuft nicht auf "Heute", nicht im Elternbereich und
    nicht in "Meine Welt" — dort wird nichts gemessen."""
    einrichten(client, fake_llm)
    kind_modus_aktivieren(client)
    for pfad, erwartet in [('/', False), ('/lernstand', False),
                           ('/lernen', True), ('/lernzyklus', True)]:
        seite = client.get(pfad)
        assert seite.status_code == 200, pfad
        assert ('lernzeit.js' in seite.text) is erwartet, pfad
