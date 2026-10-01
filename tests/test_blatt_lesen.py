"""Blätter auf dem Gerät lesen — die Teile, die ohne Browser prüfbar sind.

Was hier geprüft wird: dass die Dateien für den Browser aus festen, geprüften
Fassungen kommen; dass der Server-Rückfall PDF mit und ohne Textebene
auseinanderhält und die Datei danach löscht; und dass der gelesene Text
denselben Weg nimmt wie eingetippter.

Wie *gut* gelesen wird, misst `make ocr-report` lokal an echten Blättern.
Hier stehen synthetische Proben: sie beantworten, ob der Weg durchgeht.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from .conftest import csrf_from
from .ocr_fixtures import erzeugen
from .test_app import einrichten

WURZEL = Path(__file__).resolve().parent.parent
STATIC = WURZEL / "app" / "static"


# ------------------------------------------------------- Feste Fassungen

def test_die_browser_dateien_sind_festgenagelt_und_gepruefft():
    """Kein „latest", und jede Datei mit eingecheckter Pruefsumme.

    Ein stillschweigend anderes WASM-Modul im Browser einer Familie waere
    genau die Art Vorfall, gegen die Schritt 1 war.
    """
    plan = json.loads((WURZEL / "tools" / "ocr-assets.json").read_text(encoding="utf-8"))
    assert plan["npm"] and plan["tessdata"]["sprachen"]
    for paket in plan["npm"]:
        assert paket["version"] and "latest" not in paket["version"]
        assert len(paket["sha256"]) == 64, paket["name"]
        assert paket["dateien"], paket["name"]
    for name, angabe in plan["tessdata"]["sprachen"].items():
        assert len(angabe["sha256"]) == 64, name
    assert plan["tessdata"]["tag"] and "master" not in plan["tessdata"]["tag"]
    # Deutsch und Englisch, wie im Browser eingestellt.
    assert set(plan["tessdata"]["sprachen"]) == {"deu.traineddata", "eng.traineddata"}


def test_die_dateien_liegen_nicht_im_repository():
    """21 MB WASM und Sprachdaten gehoeren nicht in einen Quelltextbaum."""
    ignoriert = (WURZEL / ".gitignore").read_text(encoding="utf-8")
    for ordner in ("app/static/ocr/", "app/static/pdfjs/"):
        assert ordner in ignoriert
    bau = (WURZEL / "Dockerfile").read_text(encoding="utf-8")
    assert "fetch_ocr_assets.py" in bau          # der Bau holt sie selbst
    assert "tesseract-ocr" in bau                # und den Server-Rueckfall dazu


def test_eine_falsche_pruefsumme_bricht_den_bau_ab(tmp_path, monkeypatch):
    import tools.fetch_ocr_assets as holer

    monkeypatch.setattr(holer, "_holen", lambda url: b"etwas ganz anderes")
    plan = {"name": "tesseract.js", "version": "7.0.0", "sha256": "0" * 64, "dateien": {}}
    with pytest.raises(SystemExit) as abbruch:
        holer.npm_paket(plan, tmp_path)
    assert "Pruefsumme" in str(abbruch.value)


def test_der_browser_laedt_nur_vom_eigenen_server():
    """Kein CDN: sonst wuesste ein fremder Dienst bei jedem Blatt Bescheid."""
    for name in ("blatt-lesen.js", "blatt-aufnehmen.js", "ocr-sw.js"):
        quelle = (STATIC / name).read_text(encoding="utf-8")
        assert "//cdn" not in quelle and "unpkg" not in quelle, name
        assert "https://" not in quelle.replace("https://github.com", ""), name


# ------------------------------------------------- Rückfall auf dem Server

@pytest.fixture(scope="module")
def proben(tmp_path_factory):
    ordner = tmp_path_factory.mktemp("ocr")
    erzeugen.foto(ordner / "blatt-foto.png")
    erzeugen.pdf_mit_textebene(ordner / "blatt-text.pdf")
    erzeugen.pdf_gescannt(ordner / "blatt-scan.pdf")
    return ordner


def test_pdf_mit_textebene_wird_nicht_durch_ocr_gejagt(proben):
    """Schneller und fehlerfrei — OCR darueber wuerde Fehler erst erzeugen."""
    from app import blatt_text, ingest

    doc = ingest._open_pdf(proben / "blatt-text.pdf")
    try:
        assert "Bruchrechnung" in doc.text(0)
    finally:
        doc.close()
    text = blatt_text.server_lesen(proben / "blatt-text.pdf")
    assert "Bruchrechnung" in text
    assert "1/2 + 1/3" in text


def test_gescanntes_pdf_hat_keine_textebene(proben):
    from app import ingest

    doc = ingest._open_pdf(proben / "blatt-scan.pdf")
    try:
        assert len(doc.text(0)) < 40          # also muss OCR ran
        assert doc.seite(0).size[0] > 500     # und die Seite laesst sich zeichnen
    finally:
        doc.close()


@pytest.mark.skipif(not shutil.which("tesseract"), reason="tesseract nicht installiert")
def test_foto_und_scan_werden_gelesen(proben):
    from app import blatt_text

    for name in ("blatt-foto.png", "blatt-scan.pdf"):
        text = blatt_text.server_lesen(proben / name)
        assert "Bruch" in text, (name, text[:120])


def test_pdf_mit_zu_vielen_seiten_wird_abgelehnt(proben, monkeypatch):
    """Ein Lehrbuch als PDF wuerde sonst den Rechner der Familie blockieren."""
    from app import ingest

    monkeypatch.setattr(ingest, "MAX_PDF_PAGES", 0)
    with pytest.raises(ingest.IngestError, match="Seiten"):
        ingest._open_pdf(proben / "blatt-text.pdf")


# ------------------------------------------------------ Der Weg nach innen

def test_serverseitig_loescht_die_datei_sofort(client, fake_llm, fake_cli, app_env, proben,
                                               monkeypatch):
    """Sie geht kurz an den eigenen Server und ueberlebt die Anfrage nicht."""
    from app import blatt_text

    einrichten(client, fake_llm)
    gesehen = {}

    def gefaelscht(pfad, **kw):
        gesehen["pfad"] = Path(pfad)
        gesehen["da_waehrenddessen"] = Path(pfad).is_file()
        return "Regel: Brueche erst gleichnamig machen.\n\nAufgabe 1: 1/4 + 1/6."

    monkeypatch.setattr(blatt_text, "server_lesen", gefaelscht)
    monkeypatch.setattr(blatt_text, "server_lesen_moeglich", lambda: True)

    seite = client.get("/wissen")
    antwort = client.post("/blatt/serverseitig", data={
        "_csrf": csrf_from(seite.text), "fach": "mathematik"},
        files={"datei": ("blatt.png", (proben / "blatt-foto.png").read_bytes(), "image/png")})
    assert antwort.status_code == 200
    assert "Brueche" in antwort.json()["text"]
    assert gesehen["da_waehrenddessen"] is True
    assert not gesehen["pfad"].exists()            # und danach weg
    assert not gesehen["pfad"].parent.exists()


def test_ohne_lesehilfe_auf_dem_server_wird_das_gesagt(client, fake_llm, fake_cli, app_env,
                                                       proben, monkeypatch):
    from app import blatt_text

    einrichten(client, fake_llm)
    monkeypatch.setattr(blatt_text, "server_lesen_moeglich", lambda: False)
    seite = client.get("/wissen")
    antwort = client.post("/blatt/serverseitig", data={
        "_csrf": csrf_from(seite.text), "fach": "mathematik"},
        files={"datei": ("blatt.png", b"x", "image/png")})
    assert antwort.status_code == 503
    assert "eintippen" in antwort.json()["fehler"]


def test_gelesener_text_nimmt_denselben_weg_wie_eingetippter(client, fake_llm, fake_cli,
                                                             app_env, proben, monkeypatch):
    """Ein Weg, nicht zwei — sonst laeuft einer erst am Tag der Umstellung."""
    from app import blatt_text

    einrichten(client, fake_llm)
    gerufen = []
    echt = blatt_text.aufnehmen
    monkeypatch.setattr(blatt_text, "aufnehmen",
                        lambda *a, **kw: gerufen.append(kw) or echt(*a, **kw))
    monkeypatch.setattr(blatt_text, "server_lesen_moeglich", lambda: True)
    monkeypatch.setattr(blatt_text, "server_lesen",
                        lambda pfad, **kw: "Regel: gleichnamig machen.\n\nAufgabe: 1/4 + 1/6.")

    seite = client.get("/wissen")
    client.post("/blatt/serverseitig", data={
        "_csrf": csrf_from(seite.text), "fach": "mathematik"},
        files={"datei": ("blatt.png", b"x", "image/png")})
    assert gerufen, "der Rueckfall ging an der gemeinsamen Funktion vorbei"
