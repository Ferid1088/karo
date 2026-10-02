"""Kein Bild geht je an ein KI-Modell — und zwar so, dass es niemand vergessen kann.

Karo hat Fotos von Schulblättern und handschriftlich bearbeiteten Fragebogen an
ein Modell geschickt. Ein Bild trägt mehr als das, was jemand zeigen wollte: den
Namen in der Kopfzeile, die Handschrift des Kindes, was daneben auf dem Tisch
lag. Und es lässt sich nicht säubern wie ein Text — `pii.scrub()` greift dort
nicht.

Diese Datei prüft die Regel an der Stelle, an der sie nicht zu umgehen ist: die
Schnittstelle zum Modell hat keinen Bildparameter mehr. Ein Aufruf mit Bild ist
damit kein Verstoß gegen eine Verabredung, sondern ein TypeError.
"""
from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
APP = WURZEL / "app"

#: Woran ein Bild erkennbar wäre, wenn es doch jemand durchreichen wollte.
VERDAECHTIG = ("image_path", "image_url", "bild_pfad", "media_type", "_bildblock")


def _python_dateien():
    for pfad in sorted(APP.rglob("*.py")):
        yield pfad, pfad.read_text(encoding="utf-8")


def test_der_llm_client_hat_keinen_bildparameter():
    """Die Regel steht in der Signatur, nicht in einer Verabredung."""
    from app.ai.client import AIClient

    parameter = set(inspect.signature(AIClient.complete).parameters)
    assert not (parameter & set(VERDAECHTIG)), parameter
    assert "prompt" in parameter and "schema" in parameter


def test_auch_die_backends_nehmen_kein_bild():
    """Sonst könnte jemand am Client vorbei direkt ein Backend rufen."""
    from app.ai.devin import DevinBackend

    parameter = set(inspect.signature(DevinBackend.call).parameters)
    assert not (parameter & set(VERDAECHTIG)), parameter


def test_kein_codepfad_reicht_ein_bild_an_ein_modell():
    """Kein `complete(...)`/`call(...)` in app/ nennt ein Bildargument."""
    treffer = []
    for pfad, quelle in _python_dateien():
        baum = ast.parse(quelle, filename=str(pfad))
        for knoten in ast.walk(baum):
            if not isinstance(knoten, ast.Call):
                continue
            name = getattr(knoten.func, "attr", None) or getattr(knoten.func, "id", None)
            if name not in ("complete", "call"):
                continue
            for kw in knoten.keywords:
                if kw.arg in VERDAECHTIG:
                    treffer.append(f"{pfad.relative_to(WURZEL)}:{knoten.lineno} {name}({kw.arg}=…)")
    assert not treffer, "Bild an ein Modell:\n" + "\n".join(treffer)


def test_nirgends_in_app_steht_noch_ein_bildparameter():
    """Auch nicht in einer Signatur, die nur darauf wartet, wieder benutzt zu werden.

    Kommentare und Docstrings zaehlen nicht: die duerfen erklaeren, was es
    nicht mehr gibt und warum. Deshalb wird hier der Code gelesen, nicht der
    Text — mit `tokenize`, statt Zeilen zu raten.
    """
    import io as _io
    import token as _token
    import tokenize as _tokenize

    treffer = []
    for pfad, quelle in _python_dateien():
        marken = _tokenize.generate_tokens(_io.StringIO(quelle).readline)
        for art, text, (nr, _), _, zeile in marken:
            if art in (_token.COMMENT, _token.STRING):
                continue
            if text in ("image_path", "_bildblock"):
                treffer.append(f"{pfad.relative_to(WURZEL)}:{nr}: {zeile.strip()[:90]}")
    assert not treffer, "Bildparameter noch vorhanden:\n" + "\n".join(treffer)


def test_die_handschrift_wird_nirgends_mehr_abgelesen():
    """`quiz_read_sheet` ist weg — samt Job, Route und Knopf."""
    for pfad, quelle in _python_dateien():
        assert "quiz_read_sheet" not in quelle, pfad
    # Kein Formular schickt mehr ein bearbeitetes Blatt an eine Ablese-Route.
    # Gesucht wird nach dem Ziel eines Formulars, nicht nach der Zeichenfolge:
    # `/static/blatt-lesen.js` liest auf dem Geraet, und `/blatt/text` nimmt
    # Text entgegen — beides ist das Gegenteil davon.
    erlaubt = {"/blatt/text", "/blatt/serverseitig"}
    ziel = re.compile(r'action="(/[^"]*blatt[^"]*)"')
    for pfad in sorted((APP / "templates").rglob("*.html")):
        for gefunden in ziel.findall(pfad.read_text(encoding="utf-8")):
            sauber = re.sub(r"\{\{[^}]*\}\}", "<id>", gefunden)
            assert sauber in erlaubt or sauber.endswith("/thema"), (pfad.name, gefunden)

    from app import quizzes
    assert not hasattr(quizzes, "blatt_hochladen")
    assert not hasattr(quizzes, "job_quiz_read_sheet")


def test_es_gibt_keine_route_mehr_die_ein_blatt_entgegennimmt(app_env):
    """Die alten Adressen sind weg — nicht nur unbenutzt."""
    app = app_env.main.app

    wege = {(r.path, m) for r in app.routes
            for m in getattr(r, "methods", ()) or ()}
    for pfad in ("/quiz/{quiz_id}/blatt", "/klassenarbeit/themenblatt",
                 "/klassenarbeit/themenblatt/status", "/lernen/material",
                 "/lernen/material/status"):
        assert not any(p == pfad and m == "POST" for p, m in wege), pfad


def test_die_upload_wege_fuer_blaetter_sind_zu(client, fake_llm ):
    """Und ein vergessener Link laeuft ins Leere statt etwas hochzuladen."""
    from .test_app import einrichten
    einrichten(client, fake_llm)
    for pfad in ("/quiz/1/blatt", "/klassenarbeit/themenblatt"):
        antwort = client.post(pfad, files={"datei": ("blatt.jpg", b"\xff\xd8\xff", "image/jpeg")},
                              follow_redirects=False)
        # 403 = die CSRF-Sperre greift schon davor; hochgeladen wird nichts.
        assert antwort.status_code in (403, 404, 405), (pfad, antwort.status_code)


@pytest.mark.parametrize("modul,funktion", [
    ("app.kb", "job_kb_extract"),
    ("app.exam_plan", "job_exam_scan_read"),
])
def test_die_verbliebenen_blattjobs_rufen_kein_modell(modul, funktion, app_env, monkeypatch):
    """Sie nehmen das Blatt nur noch entgegen."""
    import importlib

    m = importlib.import_module(modul)
    app_env.db.init()

    def niemals(*a, **kw):
        raise AssertionError(f"{funktion} hat ein Modell gerufen")

    monkeypatch.setattr(m, "client", niemals)
    getattr(m, funktion)({"document_id": 999999, "scan_id": 999999})
