"""Design-Themes: Katalog, Klassenrahmen, Auswahl und Persistenz.

Deckt die Stellen ab, an denen das System brechen koennte:
  * der ±2-Klassenrahmen an beiden Raendern,
  * genau 10 primaere Themes je Klasse, keine Gender-Metadaten,
  * ungueltige und fernliegende IDs werden sauber abgewiesen,
  * die Wahl ueberlebt Reload und neue Sitzung,
  * der Picker zeigt nie mehr als eine Klasse (10 Kacheln) und 2 Spalten.
"""

from __future__ import annotations

import re

import pytest

from .conftest import csrf_from
from .test_app import einrichten


@pytest.fixture
def themes_modul(app_env):
    import app.themes as t
    return t


# ---------------------------------------------------------------------------
# Katalog und Klassenrahmen
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("klasse,erwartet", [
    (1, (1, 3)),
    (2, (1, 4)),
    (3, (1, 5)),
    (7, (5, 9)),
    (12, (10, 13)),
    (13, (11, 13)),
])
def test_klassenrahmen(themes_modul, klasse, erwartet):
    assert themes_modul.grade_range(klasse) == erwartet


def test_jede_klasse_hat_genau_zehn_themes(themes_modul):
    s = themes_modul.settings()
    for klasse in range(s.min_grade, s.max_grade + 1):
        themen = themes_modul.CATALOG.get(klasse)
        assert themen is not None, f"Klasse {klasse} fehlt"
        assert len(themen) == s.themes_per_grade, \
            f"Klasse {klasse}: {len(themen)} statt {s.themes_per_grade}"


def test_katalog_ist_sauber_modelliert(themes_modul):
    ids = [t["id"] for themen in themes_modul.CATALOG.values() for t in themen]
    assert len(ids) == len(set(ids)), "doppelte Theme-IDs"
    verboten = {"gender", "girl_score", "boy_score"}
    for themen in themes_modul.CATALOG.values():
        for t in themen:
            assert not verboten & set(t), f"{t['id']}: Gender-Metadaten"
            assert t["family"] in themes_modul.FAMILIES
            assert t["interest_tags"], f"{t['id']} ohne Interessen-Tag"
            assert set(t["interest_tags"]) <= themes_modul.TAGS
            assert t["grades"] == t["recommended_grades"]


def test_reifeband_steigt_mit_der_klasse(themes_modul):
    assert themes_modul.band_for_grade(1) < themes_modul.band_for_grade(7)
    assert themes_modul.band_for_grade(7) < themes_modul.band_for_grade(13)


# ---------------------------------------------------------------------------
# Auswahl ueber die Route
# ---------------------------------------------------------------------------

def _waehlen(client, theme_id, ziel="/"):
    seite = client.get("/")
    return client.post("/themes/waehlen", data={
        "_csrf": csrf_from(seite.text), "theme_id": theme_id, "ziel": ziel},
        headers={"Accept": "application/json"})


def test_theme_wahl_wird_gespeichert_und_ueberlebt_neuanmeldung(
        client, fake_llm, app_env):
    einrichten(client, fake_llm)  # Klasse 7
    r = _waehlen(client, "shonen_adventure")
    assert r.status_code == 200 and r.json()["ok"]
    assert r.json()["theme"]["family"] == "anime"

    seite = client.get("/")
    assert 'data-theme-family="anime"' in seite.text
    assert 'data-theme-band="3"' in seite.text

    # Neue Sitzung derselben Installation: die Wahl bleibt.
    client.cookies.clear()
    seite = client.get("/login")
    client.post("/login", data={"_csrf": csrf_from(seite.text),
                                "password": "geheim123"})
    seite = client.get("/")
    assert 'data-theme-family="anime"' in seite.text


def test_unbekanntes_theme_wird_abgewiesen(client, fake_llm):
    einrichten(client, fake_llm)
    r = _waehlen(client, "gibts_nicht")
    assert r.status_code == 400
    assert r.json()["ok"] is False
    assert client.get("/").text.count("data-theme-family") == 0


def test_theme_ausserhalb_des_klassenrahmens_wird_abgewiesen(
        client, fake_llm):
    einrichten(client, fake_llm)  # Klasse 7 -> 5..9
    r = _waehlen(client, "dino_abenteuer")  # Klasse 1
    assert r.status_code == 400
    r = _waehlen(client, "ai_startup")      # Klasse 13
    assert r.status_code == 400


def test_standard_theme_loescht_die_wahl(client, fake_llm):
    einrichten(client, fake_llm)
    assert _waehlen(client, "coding_lab").json()["ok"]
    r = _waehlen(client, "default")
    assert r.status_code == 200 and r.json()["ok"]
    assert 'data-theme-family' not in client.get("/").text


def test_themes_route_ist_kindfreigabe(client, fake_llm, app_env):
    """Der Picker ist ein Kind-Werkzeug: ein Kind-Login darf ihn nutzen."""
    from .test_app import kind_passwort_setzen
    einrichten(client, fake_llm)
    kind_passwort_setzen(client)

    client.cookies.clear()
    seite = client.get("/login")
    client.post("/login", data={"_csrf": csrf_from(seite.text),
                                "password": "kindpw123"})
    r = _waehlen(client, "coding_lab")
    assert r.status_code == 200 and r.json()["ok"]


# ---------------------------------------------------------------------------
# Picker in der Oberflaeche
# ---------------------------------------------------------------------------

def test_picker_zeigt_genau_eine_klasse_und_zwei_spalten(
        client, fake_llm):
    einrichten(client, fake_llm)  # Klasse 7
    html = client.get("/").text
    assert 'class="theme-picker"' in html
    grid = re.search(r'data-theme-grid[^>]*>(.*?)</div>', html, re.S)
    assert grid, "kein Kachel-Raster gefunden"
    assert len(re.findall(r'<form[^>]*data-theme-id=', grid.group(0))) == 10
    assert '--spalten: 2' in grid.group(0)
    # Alle sichtbaren Klassen als Chips, die eigene ist als aktiv markiert.
    for chip in ('5', '6', '8', '9'):
        assert re.search(rf'class="theme-klasse"\s+data-grade="{chip}"',
                         html)
    assert re.search(
        r'class="theme-klasse aktiv eigen"\s+data-grade="7" aria-current="true"',
        html)
    assert 'data-grade="4"' not in html
    assert 'data-grade="10"' not in html
    assert "Klasse 7" in html


def test_picker_fehlt_im_elternbereich(client, fake_llm):
    einrichten(client, fake_llm)
    html = client.get("/eltern").text
    assert 'data-design-picker' not in html
    assert 'data-theme-family' not in html


def test_formularpost_leitet_zurueck(client, fake_llm):
    """Ohne JavaScript funktioniert die Wahl per normalem POST + Redirect."""
    einrichten(client, fake_llm)
    seite = client.get("/")
    r = client.post("/themes/waehlen", data={
        "_csrf": csrf_from(seite.text), "theme_id": "manga_studio",
        "ziel": "/"}, headers={"Accept": "text/html"},
        follow_redirects=False)
    assert r.status_code == 303
    assert 'data-theme-family="manga"' in client.get("/").text


def test_personalisierung_sortiert_nach_interessen(client, fake_llm, themes_modul):
    einrichten(client, fake_llm)
    _waehlen(client, "shonen_adventure")          # Tags: Anime, Abenteuer
    _waehlen(client, "manga_studio")              # Tags: Manga, Kreativ
    _waehlen(client, "coding_lab")                # Tags: Coding, Technik
    reihenfolge = [t["id"] for t in themes_modul.themes_for_grade(7)]
    # Die drei gewaehlten Welten haben die meisten gemeinsamen Tags und
    # stehen deshalb vorn — Welten ohne Beruehrungspunkt fallen zurueck.
    assert set(reihenfolge[:3]) == {
        "shonen_adventure", "manga_studio", "coding_lab"}
    assert reihenfolge[-1] in {
        "competitive_gaming", "football_gaming", "music_kpop", "fashion_7",
        "photography_travel"}
