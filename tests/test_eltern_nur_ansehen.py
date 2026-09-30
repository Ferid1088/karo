"""Eltern sehen den Kinderbereich, aendern ihn aber nicht.

Der Lernstand soll die Arbeit des Kindes zeigen. Jede Antwort, jede Lernrunde
und jede Zielmeldung aus einer Eltern-Sitzung wuerde genau das verfaelschen.
Wer mitmachen will, schaltet in den Kind-Modus.
"""
from .conftest import csrf_from
from .test_app import einrichten, kind_modus_aktivieren


def test_eltern_duerfen_den_kinderbereich_ansehen(client, fake_llm, fake_cli):
    einrichten(client, fake_llm)
    for pfad in ('/', '/lernen', '/lernstand', '/woche/woche', '/post'):
        seite = client.get(pfad)
        assert seite.status_code == 200, pfad
        assert 'Sie sehen den Bereich Ihres Kindes' in seite.text, pfad
        assert 'class="nur-ansehen"' in seite.text or 'nur-ansehen"' in seite.text, pfad


def test_eltern_koennen_im_kinderbereich_nichts_aendern(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    token = csrf_from(client.get('/').text)
    with app_env.db.tx() as c:
        topic_id = c.execute(
            "INSERT INTO topic (subject, code, label, state, learning_visible, created_at)"
            " VALUES ('mathematik','M-RO-1','Testthema','aktiv',1,?)",
            (app_env.db.today(),)).lastrowid
    verboten = [
        f'/lernzyklus/{topic_id}/quiz/1/antworten',
        '/lernen/zeit',
        '/lernen/adaptiv/start',
        '/lernen/adaptiv/aufgabe',
        f'/lernstand/thema/{topic_id}/zurueck',
        f'/lernstand/thema/{topic_id}/entfernen',
        '/klassenarbeit/1/lernen/start',
        '/post/1/antwort',
    ]
    for pfad in verboten:
        antwort = client.post(pfad, data={'_csrf': token}, follow_redirects=False)
        assert antwort.status_code == 403, f'{pfad} → {antwort.status_code}'
        assert 'Nur ansehen' in antwort.text, pfad
    # Und es ist wirklich nichts passiert.
    assert not app_env.db.q("SELECT id FROM learning_time")


def test_elternarbeit_bleibt_moeglich(client, fake_llm, fake_cli):
    """Antworten bestaetigen und die eigenen Seiten bedienen Eltern weiter —
    beides hat nur im Lernbereich bzw. unter /eltern einen Knopf."""
    from app.main import _eltern_darf_aendern
    # Elternarbeit: bestaetigen, vorbereiten, einscannen, abbrechen.
    assert _eltern_darf_aendern('/lernzyklus/3/quiz/7/freigabe')
    assert _eltern_darf_aendern('/quiz/7/freigabe')
    assert _eltern_darf_aendern('/quiz/7/blatt')
    assert _eltern_darf_aendern('/lernen/4/fragen')
    assert _eltern_darf_aendern('/lernen/4/forschen')
    assert _eltern_darf_aendern('/lernen/4/abbrechen')
    assert _eltern_darf_aendern('/themen/3/lernen')
    assert _eltern_darf_aendern('/woche/eltern/plan')
    assert _eltern_darf_aendern('/eltern/kind-modus')
    assert _eltern_darf_aendern('/messung/export')
    # Arbeit des Kindes: was ueber sein Koennen aussagt oder seine Stimme ist.
    assert not _eltern_darf_aendern('/quiz/7/antworten')
    assert not _eltern_darf_aendern('/lernzyklus/3/quiz/7/antworten')
    assert not _eltern_darf_aendern('/klassenarbeit/2/simulation/5/antworten')
    # Der Zwischenstand traegt beim Bewerten die Urteile der Eltern.
    assert _eltern_darf_aendern('/quiz/7/entwurf')
    assert not _eltern_darf_aendern('/lernen/zeit')
    assert not _eltern_darf_aendern('/lernen/adaptiv/aufgabe')
    assert not _eltern_darf_aendern('/klassenarbeit/2/lernen/diagnose')
    assert not _eltern_darf_aendern('/lernstand/thema/3/entfernen')
    assert not _eltern_darf_aendern('/post/1/antwort')
    # Die Wochenplanung hat ihre eigenen, genaueren Regeln (woche/router.py).
    assert _eltern_darf_aendern('/woche/ziele/neu')


def test_im_kind_modus_geht_wieder_alles(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    kind_modus_aktivieren(client)
    seite = client.get('/')
    assert seite.status_code == 200
    assert 'Sie sehen den Bereich Ihres Kindes' not in seite.text
    antwort = client.post('/lernen/zeit',
                          data={'_csrf': csrf_from(seite.text), 'pfad': '/lernen'})
    assert antwort.status_code == 200
    assert app_env.db.q("SELECT id FROM learning_time")


def test_eine_zusehende_eltern_sitzung_misst_keine_lernzeit(client, fake_llm, fake_cli):
    einrichten(client, fake_llm)
    assert 'lernzeit.js' not in client.get('/lernen').text
    kind_modus_aktivieren(client)
    assert 'lernzeit.js' in client.get('/lernen').text
