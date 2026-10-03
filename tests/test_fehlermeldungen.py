"""Eine Meldung darf nicht raten, wenn der Grund festgehalten ist.

Beim Themenblatt stand "Lade ein deutlicheres Foto hoch", auch wenn in
Wahrheit eine Ratenbegrenzung des Anbieters oder eine verschwundene Datei
der Grund war. Wer dem folgt, lädt dasselbe Blatt noch dreimal hoch.
"""
from .conftest import csrf_from
from .test_app import einrichten


def test_klartext_nennt_den_grund_statt_der_bildqualitaet():
    from app.routers.shared import klartext
    ratenlimit = "Devin API POST /sessions: 429 Rate-Limit"
    assert "Anfragen" in klartext(ratenlimit)
    assert "Foto" not in klartext(ratenlimit)
    assert "Zugangsschlüssel" in klartext("DEVIN_API_KEY ist nicht gesetzt.")
    assert "nicht mehr da" in klartext("Die Bilddatei abc.jpg fehlt.")
    assert "zu lange" in klartext("Der Aufruf hat zu lange gedauert und wurde abgebrochen.")
    # Unbekanntes bleibt wörtlich stehen, statt in eine Vermutung zu kippen.
    assert klartext("Etwas ganz Neues ging schief") == "Etwas ganz Neues ging schief"
    assert "nicht festgehalten" in klartext(None)
    assert "nicht festgehalten" in klartext("   ")


def test_der_festgehaltene_grund_steht_bei_den_eltern(client, fake_llm,
                                                     app_env, monkeypatch):
    """Nicht „lade ein deutlicheres Foto hoch", sondern der wirkliche Grund.

    Frueher stand der Satz ueber die Bildqualitaet auch dann da, wenn in
    Wahrheit das Kontingent aufgebraucht war — und man suchte stundenlang am
    falschen Ende. Die Seite mit dem Themenblatt-Upload gibt es nicht mehr
    (Schritt 1); dieselbe Zusage gilt jetzt im Elternbereich, wo steht, was
    Karo gerade vorbereitet.
    """
    from app import db
    from app.services import exam, exam_effort
    from .test_app import einrichten
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True, learner_grade=6)
    monkeypatch.setattr("app.adaptiv.lektionen.fuer_thema", lambda *a, **k: None)
    exam_id = exam.create_exam("2099-05-05", manual_topics="Satz des Thales",
                               subject="mathematik").exam_id
    exam_effort.inhalte_anfordern(exam_id)
    with db.tx() as c:
        c.execute("UPDATE job SET state='fehler', last_error=? WHERE type='lektion_erzeugen'",
                  ("Devin API POST /sessions: 429 Rate-Limit",))

    seite = client.get("/eltern/lernfortschritt")
    assert seite.status_code == 200
    assert "Zu viele Anfragen" in seite.text
    assert "deutlicheres Foto" not in seite.text


def test_verschwundenes_bild_wird_beim_erneuten_hochladen_neu_abgelegt(app_env, tmp_path):
    """Gleiche Datei = gleicher Eintrag. Liegt dessen Bild aber nicht mehr
    da, führte jeder weitere Versuch auf denselben toten Pfad — der
    Hochladende kam aus dem Fehler nicht mehr heraus."""
    from pathlib import Path
    from app import db, ingest
    from .conftest import make_jpeg
    db.init()
    daten = make_jpeg(tmp_path / "blatt.jpg").read_bytes()

    erst = ingest.aufnehmen(daten, ".jpg", rolle="klassenarbeit_themenblatt")
    assert erst["status"] == "neu"
    assert Path(erst["stored_path"]).is_file()

    # Zweimal dasselbe Bild: derselbe Eintrag, kein neuer.
    wieder = ingest.aufnehmen(daten, ".jpg", rolle="klassenarbeit_themenblatt")
    assert wieder["status"] == "doppelt"
    assert wieder["document_id"] == erst["document_id"]

    # Jetzt ist die Datei weg — etwa nach einem Umzug aus dem Container.
    Path(erst["stored_path"]).unlink()
    with db.tx() as c:
        c.execute("UPDATE document SET stored_path='/data/scans/weg.jpg' WHERE id=?",
                  (erst["document_id"],))

    geheilt = ingest.aufnehmen(daten, ".jpg", rolle="klassenarbeit_themenblatt")
    assert geheilt["document_id"] == erst["document_id"]
    assert geheilt["status"] == "erneuert"
    assert Path(geheilt["stored_path"]).is_file()
    assert db.q1("SELECT stored_path FROM document WHERE id=?",
                 erst["document_id"])["stored_path"] == geheilt["stored_path"]
