"""Themenblatt der Klassenarbeit — eigener Weg unter /klassenarbeit.

Der gemeinsame Upload-Kern (Dateien, OCR, Analyse-Job) steht in
`material_paket` — getestet in test_material_paket.py. Hier geht es um die
Domain-Trennung: Navigation und Routen bleiben im Klassenarbeitsbereich,
bestätigte Prüfungsinhalte landen im Formular der neuen Arbeit, und nie
entsteht dabei ein Lernthema oder eine Wissensbasis-Zuordnung.
"""
from __future__ import annotations

import io
import json
import re

from .conftest import csrf_from, run_jobs
from .test_app import einrichten

THEMENBLATT_ANTWORT = {
    "fach": "mathematik",
    "pruefungsinhalte": [
        {"titel": "Brüche addieren", "seiten": [1], "konfidenz": 0.9},
        {"titel": "Brüche kürzen", "seiten": [1], "konfidenz": 0.8},
    ],
    "hinweise": ["Taschenrechner ist nicht erlaubt."],
    "termin": "2026-10-01",
}

SEITENTEXT = ("Klassenarbeit am 01.10.2026: Brüche addieren, Brüche "
              "kürzen und Textaufgaben dazu. Taschenrechner ist nicht "
              "erlaubt, Arbeitszeit 45 Minuten.")


def _bild(fmt="JPEG", size=(900, 1200), farbe=(245, 245, 245)) -> bytes:
    from PIL import Image
    puffer = io.BytesIO()
    Image.new("RGB", size, farbe).save(puffer, fmt)
    return puffer.getvalue()


def _meta(text=SEITENTEXT, n=1):
    return [{"text": text, "konfidenz": 0.9, "art": "foto"} for _ in range(n)]


def _upload(client, dateien, metadaten=None, **params):
    """POST wie material-paket.js auf den Klassenarbeits-Upload."""
    seite = client.get("/klassenarbeit/themenblatt", params=params)
    assert seite.status_code == 200
    daten = {"_csrf": csrf_from(seite.text), "fach": "mathematik",
             "seiten": json.dumps(
                 metadaten if metadaten is not None else [{}] * len(dateien))}
    for feld, wert in params.items():
        daten[feld] = wert
    return client.post("/klassenarbeit/themenblatt/paket", data=daten,
                       files=[("seite", d) for d in dateien])


def _paket_id(weiter: str) -> int:
    pfad = weiter.split("?", 1)[0]
    return int(pfad.rsplit("/", 1)[-1])


def _bereit(client, fake_llm, app_env, dateien=None, metadaten=None,
            **params) -> int:
    """Themenblatt hochladen und bis zur Prüfung laufen lassen."""
    fake_llm.responses["themenblatt"] = dict(THEMENBLATT_ANTWORT)
    dateien = dateien or [("s.jpg", _bild(), "image/jpeg")]
    if metadaten is None:
        metadaten = _meta(n=len(dateien))
    antwort = _upload(client, dateien, metadaten=metadaten, **params)
    assert antwort.status_code == 200, antwort.text
    weiter = antwort.json()["weiter"]
    assert weiter.startswith("/klassenarbeit/themenblatt/")
    paket_id = _paket_id(weiter)
    run_jobs(app_env, fake_llm)
    paket = app_env.db.q1("SELECT * FROM material_paket WHERE id=?", paket_id)
    assert paket["zweck"] == "klassenarbeit"
    assert paket["state"] == "bereit", paket["fehler"]
    return paket_id


def _aktive_lernthemen(app_env) -> list[str]:
    """Nur persönliche Lernthemen (`learning_visible=1`) — Prüfungsthemen
    sind eigene `topic`-Zeilen (`learning_visible=0`, über `exam_topic`
    verknüpft) und zählen hier absichtlich nicht."""
    from app.services import learning_hub
    return [t["label"] for t in learning_hub.personal_topics()]


# --------------------------------------------------------------------------
# Routing und Navigation
# --------------------------------------------------------------------------

def test_upload_seite_bleibt_im_klassenarbeitsbereich(client, fake_llm,
                                                    app_env):
    einrichten(client, fake_llm)
    r = client.get("/klassenarbeit/themenblatt")
    assert r.status_code == 200
    # Der Bereich Klassenarbeit ist markiert: Prüfungs-Seitenklasse und
    # Klassenarbeit-Unterzeile — im Elternbereich trägt „Lernstand" den
    # aktiven Hauptpunkt (die Arbeiten hängen dort).
    assert 'class="learning-ui exam-page' in r.text
    assert 'aria-label="Klassenarbeit"' in r.text
    assert re.search(r'href="/messung/fortschritt"[^>]*aria-current=page',
                     r.text)
    # Keine Lern-Navigation aktiv — die Kinder-Nav zeigt sie hier gar nicht.
    assert 'class="learning-entry"' not in r.text
    # Fachliche Sprache der Klassenarbeit — keine Lern-Formulare.
    assert "Themenblatt" in r.text
    assert "Zurück zur Klassenarbeit" in r.text


def test_lernen_upload_bleibt_im_lernbereich(client, fake_llm, app_env):
    einrichten(client, fake_llm)
    r = client.get("/lernen/material")
    assert r.status_code == 200
    # Kinderbereich-Nav: „Lernen" aktiv, „Klassenarbeit" nicht.
    assert re.search(r'class="learning-entry"[^>]*aria-current=page', r.text)
    assert not re.search(r'class="exam-entry"[^>]*aria-current=page', r.text)
    assert "exam-page" not in r.text


def test_klassenarbeit_neu_zeigt_auf_themenblatt(client, fake_llm, app_env):
    """Die Buttons auf /klassenarbeit/neu zeigen in den eigenen Bereich —
    nirgendwo mehr /lernen/material."""
    einrichten(client, fake_llm)
    r = client.get("/klassenarbeit/neu")
    assert r.status_code == 200
    assert 'href="/klassenarbeit/themenblatt"' in r.text
    assert 'href="/klassenarbeit/themenblatt?kamera=1"' in r.text
    assert "zweck=klassenarbeit" not in r.text
    assert "/lernen/material" not in r.text


def test_altadresse_leitet_nur_um(client, fake_llm, app_env):
    """/lernen/material?zweck=klassenarbeit ist keine Produktivroute mehr —
    ein klarer Redirect, ohne dass Lernlogik läuft."""
    einrichten(client, fake_llm)
    r = client.get("/lernen/material?zweck=klassenarbeit",
                   follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/klassenarbeit/themenblatt"

    r = client.get("/lernen/material?zweck=klassenarbeit&kamera=1",
                   follow_redirects=False)
    assert r.headers["location"] == "/klassenarbeit/themenblatt?kamera=1"


def test_lern_upload_lehnt_klassenarbeits_zweck_ab(client, fake_llm,
                                                 app_env):
    einrichten(client, fake_llm)
    seite = client.get("/lernen/material")
    r = client.post("/lernen/material/paket",
                    data={"_csrf": csrf_from(seite.text),
                          "zweck": "klassenarbeit", "fach": "mathematik",
                          "seiten": "[]"},
                    files=[("seite", ("s.jpg", _bild(), "image/jpeg"))])
    assert r.status_code == 422
    assert app_env.db.q("SELECT id FROM material_paket") == []


# --------------------------------------------------------------------------
# Der volle Weg: einlesen, prüfen, ins Formular übernehmen
# --------------------------------------------------------------------------

def test_pruefinhalte_landen_im_formular(client, fake_llm, app_env):
    einrichten(client, fake_llm)
    paket_id = _bereit(client, fake_llm, app_env)

    # Die Prüfseite zeigt die erkannten Prüfungsinhalte — im eigenen Bereich.
    seite = client.get(f"/klassenarbeit/themenblatt/{paket_id}")
    assert seite.status_code == 200
    assert "Prüfungsinhalte" in seite.text
    assert "Brüche addieren" in seite.text
    assert "Taschenrechner ist nicht erlaubt." in seite.text
    # Immer noch im Klassenarbeits-Bereich — nichts zeigt auf Lernen.
    assert 'class="learning-ui exam-page' in seite.text
    assert 'aria-label="Klassenarbeit"' in seite.text
    assert 'class="learning-entry"' not in seite.text
    assert 'Zurück zur Klassenarbeit' in seite.text

    r = client.post(f"/klassenarbeit/themenblatt/{paket_id}/uebernehmen",
                    data={"_csrf": csrf_from(seite.text), "fach": "mathematik",
                          "thema": ["Brüche addieren", "Brüche kürzen"]},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/klassenarbeit/neu")
    assert not r.headers["location"].startswith("/lernen")

    # Formular vorausgefüllt — inklusive des vom Blatt erkannten Termins.
    formular = client.get(r.headers["location"])
    assert "Brüche addieren" in formular.text
    assert "Brüche kürzen" in formular.text
    assert 'value="2026-10-01"' in formular.text


def test_kein_lernthema_und_keine_wissensbasis(client, fake_llm, app_env):
    """Domain-Isolation: der komplette Klassenarbeits-Weg verändert den
    Lernbereich nicht — kein Lernthema, keine KB-Zuordnung der Seiten."""
    einrichten(client, fake_llm)
    vorher = _aktive_lernthemen(app_env)
    paket_id = _bereit(client, fake_llm, app_env)

    seite = client.get(f"/klassenarbeit/themenblatt/{paket_id}")
    client.post(f"/klassenarbeit/themenblatt/{paket_id}/uebernehmen",
                data={"_csrf": csrf_from(seite.text), "fach": "mathematik",
                      "thema": ["Brüche addieren", "Brüche kürzen"]},
                follow_redirects=False)

    assert _aktive_lernthemen(app_env) == vorher
    # Die Seiten des Themenblatts stehen nicht in der Wissensbasis.
    zuordnungen = app_env.db.q(
        """SELECT kc.id FROM kb_chunk kc
             JOIN material_seite ms ON ms.document_id = kc.document_id
            WHERE ms.paket_id=?""", paket_id)
    assert zuordnungen == []
    # Und noch keine Arbeit: die entsteht erst durch das Formular selbst.
    assert app_env.db.q("SELECT id FROM exam") == []


def test_formularzustand_ueberlebt_den_upload(client, fake_llm, app_env):
    """Termin/Fach/Themen aus dem Formular reisen zum Upload und zurück —
    eingetragene Werte gewinnen, das Blatt ergänzt nur."""
    einrichten(client, fake_llm)
    paket_id = _bereit(client, fake_llm, app_env,
                       termin="2026-12-15", themen="Textaufgaben")

    seite = client.get(f"/klassenarbeit/themenblatt/{paket_id}",
                       params={"termin": "2026-12-15",
                               "themen": "Textaufgaben"})
    r = client.post(f"/klassenarbeit/themenblatt/{paket_id}/uebernehmen",
                    data={"_csrf": csrf_from(seite.text), "fach": "mathematik",
                          "termin": "2026-12-15", "themen": "Textaufgaben",
                          "thema": ["Brüche addieren"]},
                    follow_redirects=False)
    assert r.status_code == 303
    ziel = r.headers["location"]
    assert ziel.startswith("/klassenarbeit/neu?")

    formular = client.get(ziel)
    # Der eingetragene Termin gewinnt gegen den erkannten (2026-10-01).
    assert 'value="2026-12-15"' in formular.text
    # Manuelle Zeile bleibt, bestätigter Inhalt kommt dazu.
    assert "Textaufgaben" in formular.text
    assert "Brüche addieren" in formular.text


def test_arbeit_entsteht_erst_durch_das_formular(client, fake_llm, app_env,
                                               monkeypatch):
    """Die bestätigten Inhalte werden erst zu Prüfungsthemen, wenn die
    Arbeit angelegt wird — `exam.create_exam`, nicht der Upload."""
    einrichten(client, fake_llm)
    monkeypatch.setattr("app.db.today", lambda: "2026-09-27")
    paket_id = _bereit(client, fake_llm, app_env)
    seite = client.get(f"/klassenarbeit/themenblatt/{paket_id}")
    r = client.post(f"/klassenarbeit/themenblatt/{paket_id}/uebernehmen",
                    data={"_csrf": csrf_from(seite.text), "fach": "mathematik",
                          "thema": ["Brüche addieren", "Brüche kürzen"]},
                    follow_redirects=False)

    formular = client.get(r.headers["location"])
    r = client.post("/klassenarbeit", data={
        "_csrf": csrf_from(formular.text), "fach": "mathematik",
        "exam_date": "2026-10-01",
        "themen": "Brüche addieren\nBrüche kürzen"}, follow_redirects=True)
    assert r.status_code == 200
    exam = app_env.db.q1("SELECT * FROM exam ORDER BY id DESC LIMIT 1")
    assert exam["exam_date"] == "2026-10-01"
    # Die Prüfungsthemen hängen an der Arbeit, nicht am Lernbereich.
    assert "Brüche addieren" not in _aktive_lernthemen(app_env)
    assert len(app_env.db.q("SELECT topic_id FROM exam_topic WHERE exam_id=?",
                            exam["id"])) == 2


# --------------------------------------------------------------------------
# Keine Vermischung der Domains
# --------------------------------------------------------------------------

def test_gleicher_text_zwei_getrennte_welten(client, fake_llm, app_env):
    """Dasselbe Stichwort in beiden Flüssen: keinerlei Beziehung.

    Lernen legt ein Lernthema an; das Themenblatt bleibt ein bloßer
    Formular-Beitrag — gleicher Text, kein gemeinsames Objekt.
    """
    from app import material_paket
    from .test_material_paket import _bereit as lern_bereit

    einrichten(client, fake_llm)
    # A: Lernmaterial → Lernthema.
    lern_id = lern_bereit(client, fake_llm, app_env,
                          [("l.jpg", _bild(), "image/jpeg")],
                          _meta("Brüche addieren: gemeinsamer Nenner, "
                                "Zähler addieren, dann kürzen. Aufgabe 2 "
                                "übt das Erweitern und Kürzen weiter."))
    seite = client.get(f"/lernen/material/{lern_id}")
    client.post(f"/lernen/material/{lern_id}/uebernehmen",
                data={"_csrf": csrf_from(seite.text), "fach": "mathematik",
                      "thema": ["Brüche addieren"]}, follow_redirects=False)
    assert "Brüche addieren" in _aktive_lernthemen(app_env)
    lern_themen = list(_aktive_lernthemen(app_env))

    # B: Themenblatt mit demselben Stichwort → nur Formular-Text.
    # (Eigene Bild-Bytes: identische Dateien teilen sich das `document` per
    # sha256-Dedup — dann zeigte die KB-Abfrage unten auf ein Fremdbild.)
    kla_id = _bereit(client, fake_llm, app_env,
                     dateien=[("t.jpg", _bild(farbe=(40, 40, 200)),
                               "image/jpeg")])
    seite = client.get(f"/klassenarbeit/themenblatt/{kla_id}")
    client.post(f"/klassenarbeit/themenblatt/{kla_id}/uebernehmen",
                data={"_csrf": csrf_from(seite.text), "fach": "mathematik",
                      "thema": ["Brüche addieren"]}, follow_redirects=False)

    # Der Lernbereich ist exakt wie vorher — nichts kam dazu, nichts ging.
    assert _aktive_lernthemen(app_env) == lern_themen
    auswahl = material_paket.gewaehlte_pruefinhalte(kla_id)
    assert auswahl["themen"] == ["Brüche addieren"]
    # Kein gemeinsames Objekt: das Themenblatt kennt keinen topic-Verweis.
    assert app_env.db.q(
        "SELECT id FROM kb_chunk WHERE document_id IN "
        "(SELECT document_id FROM material_seite WHERE paket_id=?)",
        kla_id) == []


def test_pakete_bleiben_in_ihrer_domain(client, fake_llm, app_env):
    """Gegenseitige Adressen werden nicht bedient: ein Lernpaket ist unter
    /klassenarbeit/themenblatt nichts, ein Themenblatt wird unter
    /lernen/material nur auf seinen eigenen Weg verwiesen."""
    from .test_material_paket import _bereit as lern_bereit

    einrichten(client, fake_llm)
    lern_id = lern_bereit(client, fake_llm, app_env,
                          [("l.jpg", _bild(), "image/jpeg")], _meta())
    kla_id = _bereit(client, fake_llm, app_env)
    csrf = csrf_from(client.get("/klassenarbeit").text)

    # Lernpaket im Klassenarbeits-Bereich: weg, nie weiter nach /lernen.
    r = client.get(f"/klassenarbeit/themenblatt/{lern_id}",
                   follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/klassenarbeit/themenblatt"
    r = client.post(f"/klassenarbeit/themenblatt/{lern_id}/uebernehmen",
                    data={"_csrf": csrf, "fach": "mathematik",
                          "thema": ["x"]}, follow_redirects=False)
    assert r.headers["location"] == "/klassenarbeit/themenblatt"

    # Themenblatt im Lernbereich: Alter-Link-Kompatibilität leitet auf den
    # eigenen Weg — keine Lernlogik, kein Überschreiben.
    r = client.get(f"/lernen/material/{kla_id}", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == f"/klassenarbeit/themenblatt/{kla_id}"
    r = client.post(f"/lernen/material/{kla_id}/uebernehmen",
                    data={"_csrf": csrf, "fach": "mathematik",
                          "thema": ["x"]}, follow_redirects=False)
    assert r.headers["location"] == "/lernen/material"
    # Und das Themenblatt ist davon unberührt geblieben.
    paket = app_env.db.q1("SELECT state FROM material_paket WHERE id=?",
                          kla_id)
    assert paket["state"] == "bereit"
