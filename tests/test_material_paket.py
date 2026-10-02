"""Mehrseitige Materialpakete: hochladen, gemeinsam einlesen, übernehmen.

Der Browser zerlegt ein PDF in Seiten und liest sie lokal (blatt-lesen.js) —
hier kommen daher einzelne Bilder samt ihrem Text an. Ein rohes PDF darf es
trotzdem geben (Formular ohne JavaScript): dann zerlegt es der Server.
"""
from __future__ import annotations

import io
import json

import pytest

from .conftest import csrf_from, run_jobs
from .test_app import einrichten

MATERIAL_ANTWORT = {
    "fach": "mathematik",
    "themen": [
        {"titel": "Brüche addieren", "seiten": [1, 2], "konfidenz": 0.9},
        {"titel": "Brüche kürzen", "seiten": [2], "konfidenz": 0.8},
    ],
}

#: Mehr als MIN_ZEICHEN, damit die Seite als gelesen gilt.
SEITENTEXT = ("Aufgabe 1: Addiere die Brüche und kürze das Ergebnis so weit "
              "wie möglich. Schreibe den Rechenweg vollständig auf.")


def _bild(fmt="JPEG", size=(900, 1200), farbe=(245, 245, 245)) -> bytes:
    from PIL import Image
    puffer = io.BytesIO()
    Image.new("RGB", size, farbe).save(puffer, fmt)
    return puffer.getvalue()


def _pdf(seiten: int = 3) -> bytes:
    from PIL import Image
    bilder = [Image.new("RGB", (800, 1100), (250, 250, 250))
              for _ in range(seiten)]
    puffer = io.BytesIO()
    bilder[0].save(puffer, "PDF", save_all=True,
                   append_images=bilder[1:], resolution=100)
    return puffer.getvalue()


def _upload(client, dateien, fach="mathematik", zweck="lernen",
            metadaten=None):
    """POST wie material-paket.js: `seite` = Bilder, `seiten` = JSON dazu."""
    seite = client.get("/lernen/material")
    assert seite.status_code == 200
    daten = {"_csrf": csrf_from(seite.text), "zweck": zweck, "fach": fach,
             "seiten": json.dumps(
                 metadaten if metadaten is not None else [{}] * len(dateien))}
    return client.post("/lernen/material/paket", data=daten,
                       files=[("seite", d) for d in dateien])


def _paket_id(antwort) -> int:
    weiter = antwort.json()["weiter"]
    return int(weiter.rsplit("/", 1)[-1])


def _meta(text=SEITENTEXT, n=1):
    return [{"text": text, "konfidenz": 0.9, "art": "foto"} for _ in range(n)]


def _seiten(app_env, paket_id):
    return app_env.db.q(
        "SELECT * FROM material_seite WHERE paket_id=? ORDER BY position",
        paket_id)


def _bereit(client, fake_llm, app_env, dateien, metadaten, zweck="lernen"):
    """Paket hochladen und bis zur Prüfung laufen lassen."""
    fake_llm.responses["material"] = dict(MATERIAL_ANTWORT)
    antwort = _upload(client, dateien, zweck=zweck, metadaten=metadaten)
    assert antwort.status_code == 200, antwort.text
    paket_id = _paket_id(antwort)
    run_jobs(app_env, fake_llm)
    paket = app_env.db.q1("SELECT * FROM material_paket WHERE id=?", paket_id)
    assert paket["state"] == "bereit", paket["fehler"]
    return paket_id


# --------------------------------------------------------------------------
# Upload
# --------------------------------------------------------------------------

def test_ein_jpg_wird_ein_paket(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    r = _upload(client, [("blatt.jpg", _bild(), "image/jpeg")],
                metadaten=_meta())
    assert r.status_code == 200, r.text
    paket_id = _paket_id(r)
    paket = app_env.db.q1("SELECT * FROM material_paket WHERE id=?", paket_id)
    assert paket["zweck"] == "lernen" and paket["state"] == "analyse"
    seiten = _seiten(app_env, paket_id)
    assert len(seiten) == 1
    assert seiten[0]["state"] == "gelesen"
    assert seiten[0]["document_id"] is not None


def test_mehrere_jpgs_bleiben_in_der_gewaehlten_reihenfolge(
        client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    r = _upload(client, [
        ("erste.jpg", _bild(farbe=(240, 0, 0)), "image/jpeg"),
        ("zweite.jpg", _bild(farbe=(0, 240, 0)), "image/jpeg"),
        ("dritte.jpg", _bild(farbe=(0, 0, 240)), "image/jpeg"),
    ], metadaten=_meta(n=3))
    assert r.status_code == 200, r.text
    seiten = _seiten(app_env, _paket_id(r))
    assert [s["position"] for s in seiten] == [1, 2, 3]
    assert [s["quell_name"] for s in seiten] == [
        "erste.jpg", "zweite.jpg", "dritte.jpg"]


def test_png_wird_angenommen(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    r = _upload(client, [("seite.png", _bild(fmt="PNG"), "image/png")],
                metadaten=_meta())
    assert r.status_code == 200, r.text
    seite = _seiten(app_env, _paket_id(r))[0]
    dokument = app_env.db.q1("SELECT * FROM document WHERE id=?",
                             seite["document_id"])
    assert dokument["stored_path"].endswith(".jpg")  # normalisiert


def test_rohes_pdf_wird_serverseitig_in_seiten_zerlegt(
        client, fake_llm, fake_cli, app_env, monkeypatch):
    """Ohne JavaScript geht ein PDF als Ganzes hoch — der Server zerlegt es
    und der lokale Tesseract-Rückfall liest es dann."""
    einrichten(client, fake_llm)
    fake_llm.responses["material"] = dict(MATERIAL_ANTWORT)

    from app import blatt_text
    monkeypatch.setattr(blatt_text, "server_lesen_moeglich", lambda: True)
    monkeypatch.setattr(blatt_text, "server_lesen", lambda pfad: SEITENTEXT)

    r = _upload(client, [("heft.pdf", _pdf(3), "application/pdf")])
    assert r.status_code == 200, r.text
    paket_id = _paket_id(r)
    seiten = _seiten(app_env, paket_id)
    assert len(seiten) == 3
    assert [s["position"] for s in seiten] == [1, 2, 3]
    assert all(s["art"] == "pdf" for s in seiten)

    run_jobs(app_env, fake_llm)
    paket = app_env.db.q1("SELECT * FROM material_paket WHERE id=?", paket_id)
    assert paket["state"] == "bereit"
    assert all(s["state"] == "gelesen" for s in _seiten(app_env, paket_id))


def test_ungueltige_datei_wird_abgewiesen(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    r = _upload(client, [("notizen.txt", b"hallo welt", "text/plain")])
    assert r.status_code == 422
    assert "fehler" in r.json()
    assert app_env.db.q("SELECT id FROM material_paket") == []


def test_ausfuehrbare_datei_wird_abgewiesen(
        client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    r = _upload(client, [("skript.sh", b"#!/bin/sh\nrm -rf /\n",
                          "application/x-sh")])
    assert r.status_code == 422
    assert app_env.db.q("SELECT id FROM material_paket") == []


def test_zu_grosses_bild_wird_abgewiesen(
        client, fake_llm, fake_cli, app_env, monkeypatch):
    einrichten(client, fake_llm)
    from app import material_paket
    monkeypatch.setattr(material_paket, "MAX_BILD_BYTES", 100)
    r = _upload(client, [("blatt.jpg", _bild(), "image/jpeg")])
    assert r.status_code == 422
    assert "groß" in r.json()["fehler"]
    assert app_env.db.q("SELECT id FROM material_paket") == []


def test_zu_grosses_pdf_wird_abgewiesen(
        client, fake_llm, fake_cli, app_env, monkeypatch):
    einrichten(client, fake_llm)
    from app import material_paket
    vorher = len(app_env.db.q("SELECT id FROM document"))
    monkeypatch.setattr(material_paket, "MAX_PDF_BYTES", 100)
    r = _upload(client, [("heft.pdf", _pdf(2), "application/pdf")])
    assert r.status_code == 422
    assert "groß" in r.json()["fehler"]
    assert app_env.db.q("SELECT id FROM material_paket") == []
    assert len(app_env.db.q("SELECT id FROM document")) == vorher


def test_paket_gesamtlimit_gilt(
        client, fake_llm, fake_cli, app_env, monkeypatch):
    """Das Paketlimit zählt alle Dateien zusammen — nicht jede für sich."""
    einrichten(client, fake_llm)
    from app import material_paket
    vorher = len(app_env.db.q("SELECT id FROM document"))
    monkeypatch.setattr(material_paket, "MAX_PAKET_BYTES",
                        len(_bild()) + 10)
    r = _upload(client, [("a.jpg", _bild(farbe=(240, 0, 0)), "image/jpeg"),
                         ("b.jpg", _bild(farbe=(0, 240, 0)), "image/jpeg")])
    assert r.status_code == 422
    assert "groß" in r.json()["fehler"]
    assert app_env.db.q("SELECT id FROM material_paket") == []
    assert len(app_env.db.q("SELECT id FROM document")) == vorher


def test_anhaengen_zaehlt_auf_das_paketlimit(
        client, fake_llm, fake_cli, app_env, monkeypatch):
    """Das Gesamtlimit gilt paketweit — Nachladen kann es überschreiten."""
    einrichten(client, fake_llm)
    from app import material_paket
    r = _upload(client, [("a.jpg", _bild(), "image/jpeg")], metadaten=_meta())
    paket_id = _paket_id(r)
    vorher = len(app_env.db.q("SELECT id FROM document"))

    paket = app_env.db.q1("SELECT original_bytes FROM material_paket "
                          "WHERE id=?", paket_id)
    monkeypatch.setattr(material_paket, "MAX_PAKET_BYTES",
                        paket["original_bytes"] + 10)
    seite = client.get(f"/lernen/material/{paket_id}")
    r = client.post(f"/lernen/material/{paket_id}/seiten", data={
        "_csrf": csrf_from(seite.text), "seiten": "[]"},
        files=[("seite", ("b.jpg", _bild(farbe=(0, 240, 0)), "image/jpeg"))])
    assert r.status_code == 422
    assert "groß" in r.json()["fehler"]
    assert len(_seiten(app_env, paket_id)) == 1
    assert len(app_env.db.q("SELECT id FROM document")) == vorher


def test_zu_viele_seiten_werden_abgewiesen(
        client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    from app import material_paket
    dateien = [(f"s{i}.jpg", _bild(size=(50 + i, 50)), "image/jpeg")
               for i in range(material_paket.MAX_SEITEN + 1)]
    r = _upload(client, dateien)
    assert r.status_code == 422
    assert "Seiten" in r.json()["fehler"]


def test_pdf_mit_zu_vielen_seiten_wird_vor_dem_einlesen_abgelehnt(
        client, fake_llm, fake_cli, app_env):
    """Ein langes PDF scheitert an der Seitenzahl, bevor eine Seite
    gerendert oder gelesen wird — kein halbfertiges Paket, keine Waisen."""
    einrichten(client, fake_llm)
    from app import material_paket
    vorher = len(app_env.db.q("SELECT id FROM document"))
    r = _upload(client, [("heft.pdf", _pdf(material_paket.MAX_SEITEN + 1),
                          "application/pdf")])
    assert r.status_code == 422
    assert "Seiten" in r.json()["fehler"]
    assert app_env.db.q("SELECT id FROM material_paket") == []
    assert len(app_env.db.q("SELECT id FROM document")) == vorher
    assert app_env.db.q("SELECT id FROM job WHERE state='wartend'") == []


def test_fehler_mitten_im_paket_raeumt_dokumente_weg(
        client, fake_llm, fake_cli, app_env):
    """Scheitert die zweite Datei, darf die erste nicht als verwaistes
    Dokument zurückbleiben."""
    einrichten(client, fake_llm)
    vorher = len(app_env.db.q("SELECT id FROM document"))
    r = _upload(client, [("ok.jpg", _bild(), "image/jpeg"),
                         ("kaputt.jpg", b"gar kein bild", "image/jpeg")])
    assert r.status_code == 422
    assert app_env.db.q("SELECT id FROM material_paket") == []
    assert len(app_env.db.q("SELECT id FROM document")) == vorher


def test_pfad_im_dateinamen_kommt_nirgends_an(
        client, fake_llm, fake_cli, app_env):
    """Ein Dateiname ist eine Bezeichnung, nie ein Pfad."""
    einrichten(client, fake_llm)
    r = _upload(client, [("../../tmp/boese.jpg", _bild(), "image/jpeg")],
                metadaten=_meta())
    assert r.status_code == 200, r.text
    seite = _seiten(app_env, _paket_id(r))[0]
    dokument = app_env.db.q1("SELECT * FROM document WHERE id=?",
                             seite["document_id"])
    from pathlib import Path
    from app import config
    assert config.scans_dir() in Path(dokument["stored_path"]).parents
    assert ".." not in dokument["stored_path"]


def test_upload_ohne_csrf_wird_abgelehnt(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    r = client.post("/lernen/material/paket",
                    data={"zweck": "lernen", "fach": "mathematik"},
                    files=[("seite", ("b.jpg", _bild(), "image/jpeg"))])
    assert r.status_code in (403, 422)
    assert app_env.db.q("SELECT id FROM material_paket") == []


# --------------------------------------------------------------------------
# Paket als Ganzes
# --------------------------------------------------------------------------

def test_seite_entfernen_nummeriert_neu(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    r = _upload(client, [
        ("eins.jpg", _bild(farbe=(240, 0, 0)), "image/jpeg"),
        ("zwei.jpg", _bild(farbe=(0, 240, 0)), "image/jpeg"),
    ], metadaten=_meta(n=2))
    paket_id = _paket_id(r)
    seiten = _seiten(app_env, paket_id)

    formular = client.get(f"/lernen/material/{paket_id}")
    r = client.post(
        f"/lernen/material/{paket_id}/seite/{seiten[0]['id']}/entfernen",
        data={"_csrf": csrf_from(formular.text)}, follow_redirects=False)
    assert r.status_code == 303
    rest = _seiten(app_env, paket_id)
    assert len(rest) == 1 and rest[0]["position"] == 1
    assert rest[0]["quell_name"] == "zwei.jpg"


def test_letzte_seite_entfernen_raeumt_das_paket_weg(
        client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    r = _upload(client, [("eins.jpg", _bild(), "image/jpeg")], metadaten=_meta())
    paket_id = _paket_id(r)
    seite = _seiten(app_env, paket_id)[0]
    formular = client.get(f"/lernen/material/{paket_id}")
    r = client.post(
        f"/lernen/material/{paket_id}/seite/{seite['id']}/entfernen",
        data={"_csrf": csrf_from(formular.text)}, follow_redirects=False)
    assert r.status_code == 303
    assert app_env.db.q1("SELECT id FROM material_paket WHERE id=?",
                         paket_id) is None


def test_paket_uebersteht_einen_reload(client, fake_llm, fake_cli, app_env):
    """Die Analyse läuft im Hintergrund — die Statusseite bleibt bestehen."""
    einrichten(client, fake_llm)
    fake_llm.responses["material"] = dict(MATERIAL_ANTWORT)
    r = _upload(client, [("b.jpg", _bild(), "image/jpeg")], metadaten=_meta())
    paket_id = _paket_id(r)
    for _ in range(2):
        seite = client.get(f"/lernen/material/{paket_id}")
        assert seite.status_code == 200
        assert "liest deine" in seite.text
    run_jobs(app_env, fake_llm)
    seite = client.get(f"/lernen/material/{paket_id}")
    assert "hat das gefunden" in seite.text
    assert "Brüche addieren" in seite.text


def test_analyse_laeuft_nur_einmal(client, fake_llm, fake_cli, app_env):
    """Der Job steht mit Dedup-Schlüssel in der Queue — ein zweites
    Anlegen wartet nicht noch einmal."""
    einrichten(client, fake_llm)
    fake_llm.responses["material"] = dict(MATERIAL_ANTWORT)
    r = _upload(client, [("b.jpg", _bild(), "image/jpeg")], metadaten=_meta())
    paket_id = _paket_id(r)
    wartend = app_env.db.q("SELECT id FROM job WHERE state='wartend'")
    assert len(wartend) == 1
    run_jobs(app_env, fake_llm)
    aufrufe = len(fake_llm.calls)
    run_jobs(app_env, fake_llm)   # Wiederholung: nichts Neues
    assert len(fake_llm.calls) == aufrufe


def test_unleserliche_seite_richtet_kein_paket_zugrunde(
        client, fake_llm, fake_cli, app_env):
    """Eine schwer lesbare Seite wird markiert, die anderen lesen weiter."""
    einrichten(client, fake_llm)
    fake_llm.responses["material"] = dict(MATERIAL_ANTWORT)
    r = _upload(client, [
        ("gut.jpg", _bild(farbe=(240, 0, 0)), "image/jpeg"),
        ("schlecht.jpg", _bild(farbe=(0, 240, 0)), "image/jpeg"),
    ], metadaten=[{"text": SEITENTEXT, "konfidenz": 0.9, "art": "foto"},
                  {"text": "", "konfidenz": 0, "art": "foto"}])
    paket_id = _paket_id(r)
    run_jobs(app_env, fake_llm)
    paket = app_env.db.q1("SELECT * FROM material_paket WHERE id=?", paket_id)
    assert paket["state"] == "bereit"
    seiten = _seiten(app_env, paket_id)
    assert seiten[0]["state"] == "gelesen"
    assert seiten[1]["state"] == "fehler"


# --------------------------------------------------------------------------
# Übernehmen
# --------------------------------------------------------------------------

def test_bestaetigte_themen_landen_im_lernen(
        client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    paket_id = _bereit(client, fake_llm, app_env,
                       [("s1.jpg", _bild(farbe=(240, 0, 0)), "image/jpeg"),
                        ("s2.jpg", _bild(farbe=(0, 240, 0)), "image/jpeg")],
                       _meta(n=2))

    seite = client.get(f"/lernen/material/{paket_id}")
    r = client.post(f"/lernen/material/{paket_id}/uebernehmen", data={
        "_csrf": csrf_from(seite.text), "fach": "mathematik", "klasse": "7",
        "thema": ["Brüche addieren", "Brüche kürzen"],
    }, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/lernen/mathematik"

    from app import topics
    labels = {t["label"] for t in topics.liste(topics.AKTIV)}
    assert {"Brüche addieren", "Brüche kürzen"} <= labels

    paket = app_env.db.q1("SELECT * FROM material_paket WHERE id=?", paket_id)
    assert paket["state"] == "uebernommen"
    # Der Seitentext liegt jetzt als Wissen am Thema.
    chunks = app_env.db.q(
        "SELECT topic_id FROM kb_chunk WHERE topic_id IS NOT NULL")
    assert chunks


def test_fachfremdes_thema_wird_nicht_angelegt(
        client, fake_llm, fake_cli, app_env):
    """Die Fachprüfung bleibt auch beim Upload — „vocabulary" gehört nicht
    in Mathematik."""
    einrichten(client, fake_llm)
    paket_id = _bereit(client, fake_llm, app_env,
                       [("s.jpg", _bild(), "image/jpeg")], _meta())
    seite = client.get(f"/lernen/material/{paket_id}")
    r = client.post(f"/lernen/material/{paket_id}/uebernehmen", data={
        "_csrf": csrf_from(seite.text), "fach": "mathematik",
        "thema": ["Brüche addieren", "English vocabulary words"],
    }, follow_redirects=False)
    assert r.status_code == 303

    from app import topics
    labels = {t["label"] for t in topics.liste(topics.AKTIV)}
    assert "Brüche addieren" in labels
    assert "English vocabulary words" not in labels


def test_klassenarbeit_uebernimmt_themen_ins_formular(
        client, fake_llm, fake_cli, app_env, monkeypatch):
    """Zweck klassenarbeit: die bestätigten Themen füllen das Formular,
    Termin und Anlegen bleiben der übliche Weg."""
    einrichten(client, fake_llm)
    monkeypatch.setattr("app.db.today", lambda: "2026-09-27")
    paket_id = _bereit(client, fake_llm, app_env,
                       [("s.jpg", _bild(), "image/jpeg")], _meta(),
                       zweck="klassenarbeit")

    seite = client.get(f"/lernen/material/{paket_id}")
    r = client.post(f"/lernen/material/{paket_id}/uebernehmen", data={
        "_csrf": csrf_from(seite.text), "fach": "mathematik",
        "thema": ["Brüche addieren", "Brüche kürzen"],
    }, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/klassenarbeit/neu")

    # Das Formular trägt die Themen schon — als bearbeitbarer Text.
    formular = client.get(r.headers["location"])
    assert "Brüche addieren" in formular.text
    assert "Brüche kürzen" in formular.text

    # Termin bleibt ein kontrolliertes Feld, die Arbeit entsteht erst hier.
    csrf = csrf_from(formular.text)
    r = client.post("/klassenarbeit", data={
        "_csrf": csrf, "fach": "mathematik", "exam_date": "2026-10-01",
        "themen": "Brüche addieren\nBrüche kürzen"}, follow_redirects=True)
    assert r.status_code == 200
    exam = app_env.db.q1("SELECT * FROM exam ORDER BY id DESC LIMIT 1")
    assert exam["exam_date"] == "2026-10-01"


def test_ohne_thema_wird_nichts_uebernommen(
        client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    paket_id = _bereit(client, fake_llm, app_env,
                       [("s.jpg", _bild(), "image/jpeg")], _meta())
    seite = client.get(f"/lernen/material/{paket_id}")
    r = client.post(f"/lernen/material/{paket_id}/uebernehmen", data={
        "_csrf": csrf_from(seite.text), "fach": "mathematik",
    }, follow_redirects=False)
    assert r.status_code == 303  # zurück zur Prüfung mit Hinweis
    paket = app_env.db.q1("SELECT * FROM material_paket WHERE id=?", paket_id)
    assert paket["state"] == "bereit"


def test_doppeltes_uebernehmen_geht_nicht(
        client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    paket_id = _bereit(client, fake_llm, app_env,
                       [("s.jpg", _bild(), "image/jpeg")], _meta())
    seite = client.get(f"/lernen/material/{paket_id}")
    csrf = csrf_from(seite.text)
    daten = {"_csrf": csrf, "fach": "mathematik", "thema": ["Brüche addieren"]}
    client.post(f"/lernen/material/{paket_id}/uebernehmen", data=daten)
    r = client.post(f"/lernen/material/{paket_id}/uebernehmen", data=daten,
                    follow_redirects=False)
    assert r.status_code == 303
    from app import topics
    assert sum(1 for t in topics.liste(topics.AKTIV)
               if t["label"] == "Brüche addieren") == 1


# --------------------------------------------------------------------------
# Sicherheit und Datenschutz
# --------------------------------------------------------------------------

def test_seitenbild_nur_ueber_das_eigene_paket(
        client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    r = _upload(client, [("b.jpg", _bild(), "image/jpeg")], metadaten=_meta())
    paket_id = _paket_id(r)
    seite = _seiten(app_env, paket_id)[0]

    bild = client.get(f"/lernen/material/{paket_id}/seite/{seite['id']}.jpg")
    assert bild.status_code == 200
    assert bild.headers["content-type"] == "image/jpeg"

    # Eine Seite eines anderen Pakets darf hier nicht ausgeliefert werden.
    fremd = client.get(f"/lernen/material/{paket_id + 99}/seite/{seite['id']}.jpg")
    assert fremd.status_code == 404
    assert client.get(
        f"/lernen/material/{paket_id}/seite/{seite['id'] + 99}.jpg"
    ).status_code == 404


MARKER = "GEHEIMES_BLATT_4711_QSXZ"


def _llm_aufruf(app_env, paket_index=-1):
    return app_env.db.q(
        "SELECT * FROM llm_call WHERE purpose='material_analyse' "
        "ORDER BY id")[paket_index]


def test_kein_ocr_inhalt_in_den_logs(client, fake_llm, fake_cli, app_env,
                                     caplog):
    """Das Protokoll zählt Seiten und IDs — nie Blattinhalte."""
    einrichten(client, fake_llm)   # Kind heißt hier „Milena"
    fake_llm.responses["material"] = dict(MATERIAL_ANTWORT)
    r = _upload(client, [("b.jpg", _bild(), "image/jpeg")],
                metadaten=[{"text": SEITENTEXT + " Milena " + MARKER,
                            "konfidenz": 0.9, "art": "foto"}])
    paket_id = _paket_id(r)
    run_jobs(app_env, fake_llm)

    import logging
    from app import material_paket
    with caplog.at_level(logging.INFO, logger="karo.material"):
        # Erneut analysieren läuft noch einmal durch alle Logzeilen.
        material_paket.erneut_analysieren(paket_id)
        run_jobs(app_env, fake_llm)
    assert MARKER not in caplog.text
    assert "Milena" not in caplog.text


def test_audit_speichert_keinen_blattinhalt(
        client, fake_llm, fake_cli, app_env):
    """Arbeitsblatt-OCR ist selbst geschwärzt zu sensibel für den
    Audit-Speicher: in llm_call bleiben nur Metadaten und der Hash."""
    einrichten(client, fake_llm)
    fake_llm.responses["material"] = dict(MATERIAL_ANTWORT)
    r = _upload(client, [("b.jpg", _bild(), "image/jpeg")],
                metadaten=[{"text": SEITENTEXT + " Milena " + MARKER,
                            "konfidenz": 0.9, "art": "foto"}])
    paket_id = _paket_id(r)
    run_jobs(app_env, fake_llm)

    aufruf = _llm_aufruf(app_env)
    prompt = aufruf["prompt"]
    # Weder der Blattinhalt noch der Kindesname noch die Antwort des
    # Modells liegen dauerhaft im Audit.
    for verboten in (MARKER, "Milena", "Addiere die Brüche", "=== Seite"):
        assert verboten not in prompt
    assert "Brüche" not in (aufruf["response_raw"] or "")
    assert aufruf["response_raw"].startswith("sha256:")

    # Was bleibt: Zweck, Backend, Modell, Kennzahlen, Hash — auditierbar,
    # ohne den Inhalt zu kennen.
    assert "[MATERIAL_ANALYSE_REDACTED]" in prompt
    assert f"upload_id={paket_id}" in prompt
    assert "page_count=1" in prompt
    assert "subject=mathematik" in prompt
    assert "input_chars=" in prompt
    assert "prompt_hash=sha256:" in prompt
    assert aufruf["model"] and aufruf["backend"]
    assert aufruf["schema_ok"] == 1


def test_prompt_hash_stabil_und_empfindlich(
        client, fake_llm, fake_cli, app_env):
    """Gleicher Modellinput → gleicher Hash; ein anderes Blatt → anderer."""
    import re
    einrichten(client, fake_llm)
    fake_llm.responses["material"] = dict(MATERIAL_ANTWORT)
    for text in (SEITENTEXT, SEITENTEXT, SEITENTEXT + " Zusatzaufgabe."):
        _upload(client, [("b.jpg", _bild(), "image/jpeg")],
                metadaten=[{"text": text, "konfidenz": 0.9, "art": "foto"}])
    run_jobs(app_env, fake_llm)

    def hash_von(aufruf):
        m = re.search(r"prompt_hash=sha256:([0-9a-f]{64})", aufruf["prompt"])
        assert m, aufruf["prompt"]
        return m.group(1)

    aufrufe = app_env.db.q(
        "SELECT * FROM llm_call WHERE purpose='material_analyse' ORDER BY id")
    assert len(aufrufe) == 3
    assert hash_von(aufrufe[0]) == hash_von(aufrufe[1])
    assert hash_von(aufrufe[0]) != hash_von(aufrufe[2])


def test_andere_zwecke_behalten_ihr_vollaudit(
        client, fake_llm, fake_cli, app_env):
    """Nur der sensible Blatt-Pfad wird anonymisiert — der Rest des Audits
    hält weiter fest, was wirklich zum Modell ging."""
    einrichten(client, fake_llm)
    from app import config
    from app.llm import ClaudeClient
    schema = {"type": "object", "required": ["ok"],
              "properties": {"ok": {"type": "boolean"}}}
    ClaudeClient.from_config(config.load_safe()).complete(
        "verify_ping", f"AUDITVOLLMARKER {MARKER}", schema)
    aufruf = app_env.db.q1(
        "SELECT * FROM llm_call WHERE purpose='verify_ping' "
        "ORDER BY id DESC LIMIT 1")
    assert MARKER in aufruf["prompt"]
    assert "REDACTED" not in aufruf["prompt"]
    assert aufruf["response_raw"] and not \
        aufruf["response_raw"].startswith("sha256:")
