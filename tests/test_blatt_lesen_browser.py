"""Das Lesen im Browser — auf den Engines und Geräten, die Familien benutzen.

Der Zweck dieser Datei ist nicht, Tesseract zu prüfen. Es ist, die Stellen zu
prüfen, an denen es auf einem Gerät schiefgeht und auf einem anderen nicht:

  * iOS lässt mit `capture` nur die Kamera zu und kein PDF aus der Dateien-App.
    Deshalb hat der Datei-Knopf kein `capture` — das war der Grund, warum PDFs
    auf dem iPad nie ankamen.
  * Ohne Kamera darf kein Kamera-Knopf dastehen, der ins Leere führt.
  * Der Hinweis vor der Kamera muss vor der Kamera kommen, nicht danach.
  * Ohne JavaScript bleibt das Formular ein Formular.

Die 21 MB Lesehilfe werden hier nicht geladen: diese Tests laufen in der CI,
und ein Testlauf, der bei jedem Mal 21 MB zieht, läuft bald gar nicht mehr.
Was mit echten Blättern herauskommt, misst `make ocr-report` lokal.
"""
from __future__ import annotations

import pytest

from .test_app import einrichten

GERAETE = [
    ("chromium", None, "Desktop Chrome/Edge"),
    ("firefox", None, "Desktop Firefox"),
    ("webkit", None, "Desktop Safari"),
    ("webkit", "iPad (gen 7)", "iPad Safari"),
    ("webkit", "iPhone 13", "iPhone Safari"),
    ("chromium", "Galaxy Tab S4", "Android Chrome"),
]


def _seite(client, pw, p, engine: str, geraet: str | None):
    """Die Schulblätter-Seite in einem echten Browser, gegen den Testclient."""
    try:
        browser = getattr(p, engine).launch(headless=True)
    except pw.Error as exc:                      # pragma: no cover
        pytest.skip(f"{engine} nicht verfügbar: {exc}")
    kontext = browser.new_context(**(p.devices[geraet] if geraet else {}))
    seite = kontext.new_page()
    fehler = []
    seite.on("pageerror", lambda e: fehler.append(str(e)))

    html = client.get("/wissen").text

    def bedienen(route):
        pfad = route.request.url.split("127.0.0.1")[-1].split("/", 1)[-1]
        if route.request.url.endswith("/wissen"):
            route.fulfill(status=200, content_type="text/html; charset=utf-8", body=html)
            return
        antwort = client.get("/" + pfad)
        route.fulfill(status=antwort.status_code,
                      content_type=antwort.headers.get("content-type", "text/plain"),
                      body=antwort.content)

    seite.route("**/*", bedienen)
    seite.goto("http://127.0.0.1/wissen")
    seite.wait_for_timeout(300)
    return browser, kontext, seite, fehler


@pytest.mark.parametrize("engine,geraet,name", GERAETE,
                         ids=[g[2].replace(" ", "-") for g in GERAETE])
def test_die_blattaufnahme_steht_auf_jedem_geraet(client, fake_llm, fake_cli, app_env,
                                                  engine, geraet, name):
    pw = pytest.importorskip("playwright.sync_api")
    einrichten(client, fake_llm)
    with pw.sync_playwright() as p:
        browser, kontext, seite, fehler = _seite(client, pw, p, engine, geraet)
        try:
            bereich = seite.locator("[data-lesen-bereich]")
            assert bereich.count() == 1, name
            # Der Datei-Knopf darf kein `capture` haben: iOS liesse sonst nur
            # die Kamera zu und kein PDF aus der Dateien-App.
            datei_eingaben = seite.locator("input[type=file]:not([capture])")
            assert datei_eingaben.count() >= 1, name
            akzeptiert = [datei_eingaben.nth(i).get_attribute("accept") or ""
                          for i in range(datei_eingaben.count())]
            assert any("application/pdf" in a for a in akzeptiert), (name, akzeptiert)
            # Und umgekehrt: was die Kamera meint, sagt es auch.
            kamera_eingaben = seite.locator("input[type=file][capture]")
            assert all("pdf" not in (kamera_eingaben.nth(i).get_attribute("accept") or "")
                       for i in range(kamera_eingaben.count())), name
            # Das Textfeld bleibt — ohne Lesehilfe wird eingetippt.
            assert seite.locator("textarea[name=blatt_text]").count() == 1, name
            assert not fehler, (name, fehler)
        finally:
            kontext.close()
            browser.close()


@pytest.mark.parametrize("engine,geraet", [("webkit", "iPhone 13"), ("chromium", None)],
                         ids=["iPhone", "Desktop"])
def test_der_hinweis_kommt_vor_der_kamera(client, fake_llm, fake_cli, app_env, engine, geraet):
    """Erst sagen, was passiert — dann die Kamera. Nicht andersherum."""
    pw = pytest.importorskip("playwright.sync_api")
    einrichten(client, fake_llm)
    with pw.sync_playwright() as p:
        browser, kontext, seite, fehler = _seite(client, pw, p, engine, geraet)
        try:
            kamera = seite.get_by_role("button", name="Blatt fotografieren")
            if not kamera.count():
                # Kein Kamera-Knopf ohne Kamera — das ist hier die richtige Antwort.
                assert geraet is None
                return
            kamera.click()
            seite.wait_for_timeout(200)
            text = seite.locator(".hinweis-kamera").inner_text()
            assert "bleibt auf diesem Gerät" in text
            assert "nur diesen Text" in text
            assert seite.get_by_role("button", name="Verstanden, Kamera öffnen").count() == 1
            assert not fehler, fehler
        finally:
            kontext.close()
            browser.close()


def test_ohne_javascript_bleibt_es_ein_formular(client, fake_llm, fake_cli, app_env):
    """Die Lesehilfe ist Zugabe, keine Bedingung."""
    einrichten(client, fake_llm)
    html = client.get("/wissen").text
    assert "<noscript>" in html and "Text eintippen" in html
    assert 'name="blatt_text"' in html
    assert 'name="datei"' in html
