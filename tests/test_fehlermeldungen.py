"""Eine Meldung darf nicht raten, wenn der Grund festgehalten ist.

Beim Themenblatt stand "Lade ein deutlicheres Foto hoch", auch wenn in
Wahrheit das Claude-Kontingent aufgebraucht oder die Datei verschwunden war.
Wer dem folgt, lädt dasselbe Blatt noch dreimal hoch.
"""
from .conftest import csrf_from
from .test_app import einrichten


def test_klartext_nennt_den_grund_statt_der_bildqualitaet():
    from app.routers.shared import klartext
    kontingent = ("Die Claude-CLI ist fehlgeschlagen (Code 1). "
                  "You've hit your session limit · resets 5am (Europe/Berlin)")
    assert "Kontingent" in klartext(kontingent)
    assert "Foto" not in klartext(kontingent)
    assert "nicht mehr da" in klartext("Die Bilddatei abc.jpg fehlt.")
    assert "zu lange" in klartext("Der Aufruf hat zu lange gedauert und wurde abgebrochen.")
    # Unbekanntes bleibt wörtlich stehen, statt in eine Vermutung zu kippen.
    assert klartext("Etwas ganz Neues ging schief") == "Etwas ganz Neues ging schief"
    assert "nicht festgehalten" in klartext(None)
    assert "nicht festgehalten" in klartext("   ")


def test_gescheiterter_scan_zeigt_den_festgehaltenen_grund(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    with app_env.db.tx() as c:
        doc_id = c.execute(
            "INSERT INTO document(rolle,stored_path,sha256,source_name,mime,state,created_at)"
            " VALUES('pruefung','/weg.jpg','a1','blatt.jpg','image/jpeg','neu',?)",
            (app_env.db.now(),)).lastrowid
        c.execute("""INSERT INTO exam_scan(document_id,state,themen,fehler,created_at)
                     VALUES(?,'fehler','[]',?,?)""",
                  (doc_id, "Die Claude-CLI ist fehlgeschlagen (Code 1). "
                           "You've hit your session limit · resets 5am (Europe/Berlin)",
                   app_env.db.now()))
    seite = client.get("/klassenarbeit/neu")
    assert seite.status_code == 200
    assert "Kontingent" in seite.text
    assert "Lade ein deutlicheres Foto hoch" not in seite.text


def test_leer_gelesenes_blatt_darf_weiter_nach_einem_besseren_foto_fragen(
        client, fake_llm, fake_cli, app_env):
    """Der eine Fall, in dem die Bildqualität wirklich die Ursache sein kann:
    Karo hat gelesen, aber nichts gefunden."""
    einrichten(client, fake_llm)
    with app_env.db.tx() as c:
        doc_id = c.execute(
            "INSERT INTO document(rolle,stored_path,sha256,source_name,mime,state,created_at)"
            " VALUES('pruefung','/x.jpg','b2','blatt.jpg','image/jpeg','neu',?)",
            (app_env.db.now(),)).lastrowid
        c.execute("""INSERT INTO exam_scan(document_id,state,themen,created_at)
                     VALUES(?,'gelesen','[]',?)""", (doc_id, app_env.db.now()))
    seite = client.get("/klassenarbeit/neu")
    assert "kein Thema erkannt" in seite.text


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
