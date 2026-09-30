"""Die Brücke bis Schritt 2: Text vom Blatt füllt die Wissensbasis.

Seit Schritt 1 geht kein Foto mehr an ein Modell — damit füllte sich die
Wissensbasis nicht mehr, und ohne eigenes Material kann Karo nichts erklären.
Der Text kommt jetzt von einem Menschen und ab Schritt 2 vom Browser-OCR,
über denselben Weg: `POST /blatt/text`.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from .conftest import csrf_from, run_jobs
from .test_app import einrichten, themen_freigeben

BLATT = """Name: Lena Musterfrau      Klasse: 6b      Datum: 12.09.2026
__________________________

Regel: Ungleichnamige Brüche werden zuerst gleichnamig gemacht.
Dann addiert man nur die Zähler.

Beispiel: 1/2 + 1/3 = 3/6 + 2/6 = 5/6

Aufgabe 1: Rechne 1/4 + 1/6.
Aufgabe 2: Rechne 2/5 + 1/10.
"""


def _hochladen(client, text="", themenname="Brüche addieren", name="blatt.jpg",
               size=(900, 1200), fach="mathematik"):
    puffer = io.BytesIO()
    Image.new("RGB", size, (245, 245, 245)).save(puffer, "JPEG")
    seite = client.get("/wissen")
    daten = {"_csrf": csrf_from(seite.text), "fach": fach, "themenname": themenname}
    if text:
        daten["blatt_text"] = text
    return client.post("/wissen/upload", data=daten,
                       files={"datei": (name, puffer.getvalue(), "image/jpeg")},
                       follow_redirects=True)


# ---------------------------------------------------------------- Zerlegen

def test_kopfzeilen_und_name_verschwinden(app_env):
    from app import blatt_text
    app_env.db.init()
    app_env.config.update(learner_name="Lena")
    ergebnis = blatt_text.aufnehmen(BLATT, "mathematik", themenname="Brüche addieren")
    assert ergebnis["abschnitte"] >= 3
    # Nichts aus der Kopfzeile ueberlebt — weder das Feld noch der Name.
    text = " ".join(a["text"] for a in blatt_text.zerlegen(
        blatt_text.kopf_entfernen(BLATT)))
    assert "Klasse: 6b" not in text and "Musterfrau" not in text
    assert "Datum" not in text


def test_die_ueberschrift_bleibt_stehen(app_env):
    """Blind die ersten Zeilen abzuschneiden haette das Thema mitgenommen."""
    from app import blatt_text
    app_env.db.init()
    text = "Bruchrechnung — Übersicht\n\nRegel: erst gleichnamig machen."
    assert "Bruchrechnung" in blatt_text.kopf_entfernen(text)


def test_abschnitte_bekommen_eine_art_ohne_modell(app_env):
    from app import blatt_text
    app_env.db.init()
    arten = [a["art"] for a in blatt_text.zerlegen(blatt_text.kopf_entfernen(BLATT))]
    assert "regel" in arten and "beispiel" in arten and "aufgabe" in arten


# ---------------------------------------------------------------- Der Weg

def test_text_beim_hochladen_fuellt_die_wissensbasis(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    vorher = len(fake_llm.calls)
    antwort = _hochladen(client, text=BLATT)
    assert antwort.status_code == 200

    abschnitte = app_env.db.q("SELECT * FROM kb_chunk ORDER BY position")
    assert len(abschnitte) >= 3
    assert {a["art"] for a in abschnitte} >= {"regel", "beispiel", "aufgabe"}
    # Kein Modellaufruf: Einordnen ist Regelarbeit.
    assert len(fake_llm.calls) == vorher
    # Und nichts Persoenliches in der Wissensbasis.
    assert all("Musterfrau" not in a["text"] for a in abschnitte)

    doc = app_env.db.q1("SELECT * FROM document ORDER BY id DESC LIMIT 1")
    assert doc["state"] == "erschlossen"
    assert "Abschnitte" in (doc["note"] or "")


def test_ohne_text_bleibt_es_beim_eingetippten_thema(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    _hochladen(client, text="")
    run_jobs(app_env, fake_llm)
    assert app_env.db.q("SELECT * FROM kb_chunk") == []
    doc = app_env.db.q1("SELECT * FROM document ORDER BY id DESC LIMIT 1")
    assert doc["state"] == "abgelegt"
    vorschlag = app_env.db.q1("SELECT label FROM topic WHERE state='vorschlag'")
    assert vorschlag["label"] == "Brüche addieren"


def test_blatt_text_endpunkt_liefert_top_drei(client, fake_llm, fake_cli, app_env):
    """Derselbe Endpunkt, den ab Schritt 2 das Browser-OCR benutzt."""
    einrichten(client, fake_llm)
    _hochladen(client, text="", themenname="Brüche addieren")
    run_jobs(app_env, fake_llm)
    themen_freigeben(client, app_env)
    doc = app_env.db.q1("SELECT * FROM document ORDER BY id DESC LIMIT 1")

    seite = client.get("/wissen")
    antwort = client.post("/blatt/text", data={
        "_csrf": csrf_from(seite.text), "fach": "mathematik",
        "document_id": doc["id"], "themenname": "Brüche addieren",
        "text": BLATT, "ocr_konfidenz": "0.87"},
        headers={"accept": "application/json"})
    assert antwort.status_code == 200
    ergebnis = antwort.json()
    assert ergebnis["abschnitte"] >= 3
    assert len(ergebnis["vorschlaege"]) <= 3
    assert "Brüche addieren" in [v["label"] for v in ergebnis["vorschlaege"]]
    # Die Lesesicherheit steht beim Blatt, nicht im Nichts.
    doc = app_env.db.q1("SELECT note FROM document WHERE id=?", doc["id"])
    assert "87" in doc["note"]


def test_der_endpunkt_nimmt_kein_bild_und_kein_leeres(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    seite = client.get("/wissen")
    token = csrf_from(seite.text)
    leer = client.post("/blatt/text", data={"_csrf": token, "fach": "mathematik", "text": "  "})
    assert leer.status_code == 422
    ohne_fach = client.post("/blatt/text", data={"_csrf": token, "text": "etwas"})
    assert ohne_fach.status_code == 422


# ---------------------------------------------------------------- Bestätigen

def test_ein_mensch_bestaetigt_das_thema(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    _hochladen(client, text=BLATT)
    doc = app_env.db.q1("SELECT * FROM document ORDER BY id DESC LIMIT 1")
    seite = client.get(f"/wissen/{doc['id']}")
    assert seite.status_code == 200
    assert "Wozu gehört dieses Blatt" in seite.text
    # Solange niemand bestaetigt hat, haengt kein Abschnitt an einem Thema.
    assert all(a["topic_id"] is None for a in
               app_env.db.q("SELECT topic_id FROM kb_chunk"))

    client.post(f"/blatt/{doc['id']}/thema", data={
        "_csrf": csrf_from(seite.text), "label": "Brüche addieren"})
    thema = app_env.db.q1("SELECT * FROM topic WHERE label='Brüche addieren'")
    assert thema
    assert all(a["topic_id"] == thema["id"] for a in
               app_env.db.q("SELECT topic_id FROM kb_chunk"))


def test_ein_thema_aus_einem_anderen_fach_bekommt_das_blatt_nicht(
        client, fake_llm, fake_cli, app_env):
    from app import topics
    einrichten(client, fake_llm)
    _hochladen(client, text=BLATT)
    doc = app_env.db.q1("SELECT * FROM document ORDER BY id DESC LIMIT 1")
    fremd = topics.anlegen("present perfect", subject="englisch")
    seite = client.get(f"/wissen/{doc['id']}")
    antwort = client.post(f"/blatt/{doc['id']}/thema", data={
        "_csrf": csrf_from(seite.text), "topic_id": fremd}, follow_redirects=True)
    assert "anderen Fach" in antwort.text
    assert all(a["topic_id"] is None for a in
               app_env.db.q("SELECT topic_id FROM kb_chunk"))


# ---------------------------------------------------------------- Der Zweck

def test_mit_text_kann_karo_wieder_erklaeren(client, fake_llm, fake_cli, app_env):
    """Der eigentliche Punkt: ohne Text keine Lerneinheit, mit Text schon."""
    from app import teaching
    einrichten(client, fake_llm)
    _hochladen(client, text="")
    run_jobs(app_env, fake_llm)
    topic_id = themen_freigeben(client, app_env)[0]
    lesson_id = teaching.starten(topic_id)
    with pytest.raises(teaching.TeachingError) as ohne:
        teaching.naechste_runde_bestaetigen(lesson_id)
    # Die Meldung zeigt den Weg, statt nur zu sagen, dass etwas fehlt.
    assert "Text vom Blatt" in str(ohne.value)

    doc = app_env.db.q1("SELECT * FROM document ORDER BY id DESC LIMIT 1")
    seite = client.get(f"/wissen/{doc['id']}")
    client.post("/blatt/text", data={
        "_csrf": csrf_from(seite.text), "fach": "mathematik",
        "document_id": doc["id"], "text": BLATT},
        headers={"accept": "application/json"})
    client.post(f"/blatt/{doc['id']}/thema", data={
        "_csrf": csrf_from(seite.text), "topic_id": topic_id})

    assert teaching.naechste_runde_bestaetigen(lesson_id)
