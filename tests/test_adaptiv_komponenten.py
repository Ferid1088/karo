"""Meilenstein 3 — das Darstellungsregister (01_ARCHITECTURE.md §3).

Hier hängt A1 dran: ein Modell darf auswählen und Parameter füllen, sonst
nichts. Jede Zurückweisung muss zu einem sicheren Rückfall führen, nicht zu
einer halb gezeichneten Seite.
"""
import pytest

from .conftest import csrf_from
from .test_app import einrichten, kind_modus_aktivieren


# --------------------------------------------------------------------------
# A1 — nichts Ausführbares, nur Auswahl und Parameter
# --------------------------------------------------------------------------

def test_register_fuehrt_die_fuenf_komponenten():
    """§3: FractionStrip, NumberLine, AreaModel, Balance, GenericStepFlow."""
    from app.adaptiv import komponenten

    assert set(komponenten.ids()) == {"FractionStrip", "NumberLine",
                                      "AreaModel", "Balance",
                                      "GenericStepFlow"}


def test_jede_komponente_deklariert_was_sie_deklarieren_muss():
    """§3: Id und Version, Fächer, Parameterschema, erlaubte Animationen,
    Barrierefreiheit, Renderer."""
    from app.adaptiv import komponenten

    for k in komponenten.alle():
        assert k.id and k.version >= 1
        assert k.zweck
        assert isinstance(k.parameter, dict)
        assert "none" in k.animationen
        assert k.renderer
        assert k.barrierefreiheit


def test_modell_sieht_nur_metadaten_niemals_die_umsetzung():
    """§3: „The model-facing selector sees component metadata only.“"""
    from app.adaptiv import komponenten

    katalog = komponenten.fuer_modell()
    assert katalog
    for eintrag in katalog:
        assert set(eintrag) == {"component", "version", "zweck", "parameter",
                                "animationen"}
        assert "renderer" not in eintrag
        # Und nichts, was nach Umsetzung aussieht.
        assert "<" not in repr(eintrag)


def test_unbekannte_komponente_wird_verworfen_und_faellt_sicher_zurueck():
    """§3: Unbekannte Id → ablehnen, nicht zeichnen; Rückfall ist generisch."""
    from app.adaptiv import komponenten

    with pytest.raises(komponenten.ParameterUngueltig):
        komponenten.pruefe_auswahl({"component": "EvilCanvas", "parameters": {}})

    rueckfall, grund = komponenten.auswahl_oder_fallback(
        {"component": "EvilCanvas", "parameters": {}})
    assert rueckfall["component"] == komponenten.FALLBACK.id
    assert grund


@pytest.mark.parametrize("auswahl", [
    {"component": "FractionStrip", "parameters": {"a": [1, 0]}},          # Nenner 0
    {"component": "FractionStrip", "parameters": {"a": "1/2"}},           # kein Bruch
    {"component": "FractionStrip", "parameters": {}},                     # Pflicht fehlt
    {"component": "FractionStrip", "parameters": {"a": [1, 2], "x": 1}},  # unbekannt
    {"component": "AreaModel", "parameters": {"spalten": 0, "zeilen": 2}},
    {"component": "AreaModel", "parameters": {"spalten": 99, "zeilen": 2}},
    {"component": "NumberLine", "parameters": {"marken": []}},
    {"component": "NumberLine", "parameters": {"marken": [[1, 2], [3, 0]]}},
    {"component": "Balance", "parameters": {"links": [1, 2]}},            # rechts fehlt
])
def test_ungueltige_parameter_werden_nie_gezeichnet(auswahl):
    """§3: Ungültige Parameter → ablehnen, niemals rendern."""
    from app.adaptiv import komponenten

    with pytest.raises(komponenten.ParameterUngueltig):
        komponenten.pruefe_auswahl(auswahl)


def test_nicht_erlaubte_animation_wird_verworfen():
    """§3: Nur die deklarierten Animationsmodi sind zulässig."""
    from app.adaptiv import komponenten

    with pytest.raises(komponenten.ParameterUngueltig):
        komponenten.pruefe_auswahl({"component": "FractionStrip",
                                    "parameters": {"a": [1, 2]},
                                    "animation": "explode"})


def test_gueltige_auswahl_kommt_normalisiert_zurueck():
    from app.adaptiv import komponenten

    geprueft = komponenten.pruefe_auswahl(
        {"component": "FractionStrip",
         "parameters": {"a": (1, 2), "b": [1, 3], "gemeinsam": 6},
         "animation": "cut_then_slide"})
    assert geprueft == {"component": "FractionStrip",
                        "parameters": {"a": [1, 2], "b": [1, 3], "gemeinsam": 6},
                        "animation": "cut_then_slide"}


def test_markup_in_parametern_wird_abgewiesen():
    """A1: Auch als Parameter getarntes Markup kommt nicht durch."""
    from app.adaptiv import schemas

    with pytest.raises(schemas.InhaltUngueltig):
        schemas.pruefe_visualisierung(
            {"component": "GenericStepFlow",
             "parameters": {"schritte": ["<script>alert(1)</script>"]}})


def test_komponenten_kennen_ihr_fach():
    """§3: Eine Komponente erklärt, welche Fächer und Konzepte sie bedient."""
    from app.adaptiv import komponenten

    assert komponenten.FRACTION_STRIP.dient("mathematik")
    assert not komponenten.FRACTION_STRIP.dient("biologie")
    # Der Rückfall trägt jedes Fach, sonst wäre er keiner.
    assert komponenten.FALLBACK.dient("biologie")
    assert [e["component"] for e in komponenten.fuer_modell("biologie")] == [
        komponenten.FALLBACK.id]


# --------------------------------------------------------------------------
# Die Zeichnung selbst
# --------------------------------------------------------------------------

def test_jede_komponente_hat_einen_renderer_im_template():
    """Ein Register ohne Zeichnung wäre eine Liste von Versprechen."""
    from pathlib import Path

    from app.adaptiv import komponenten

    vorlage = Path("app/templates/adaptiv.html").read_text(encoding="utf-8")
    for k in komponenten.alle():
        assert f"cfg.component == '{k.id}'" in vorlage, k.id


def test_gezeichnete_komponenten_sind_vorlesbar(client, fake_llm, fake_cli,
                                                app_env):
    """§3: Barrierefreiheit gehört zur Komponente, nicht zum Zufall."""
    import re

    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True)
    kind_modus_aktivieren(client)
    token = csrf_from(client.get("/lernen/adaptiv").text)
    client.post("/lernen/adaptiv/start", data={"_csrf": token, "thema": "brueche"})
    client.post("/lernen/adaptiv/anker", data={"_csrf": token, "antwort": "x"})
    seite = client.post("/lernen/adaptiv/diagnose",
                        data={"_csrf": token, "antwort": "2/5"})

    bilder = re.findall(r'role="img"([^>]*)>', seite.text)
    assert bilder
    assert all("aria-label=" in b for b in bilder)


# --------------------------------------------------------------------------
# §18 — die Elternsicht
# --------------------------------------------------------------------------

def _kind_lernt(client, fake_llm, app_env):
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True)
    kind_modus_aktivieren(client)
    token = csrf_from(client.get("/lernen/adaptiv").text)
    client.post("/lernen/adaptiv/start", data={"_csrf": token, "thema": "brueche"})
    for weg, daten in (("anker", {"antwort": "die Hälfte"}),
                       ("diagnose", {"antwort": "2/5"}),
                       ("vorhersage", {"antwort": "groesser"}),
                       ("weiter", {}), ("weiter", {}), ("weiter", {}),
                       ("aufgabe", {"antwort": "3/4"})):
        client.post(f"/lernen/adaptiv/{weg}", data={"_csrf": token, **daten})
    return token


def test_eltern_sehen_denkfehler_und_stand(client, fake_llm, fake_cli, app_env):
    """§9 „definition of done“: Die Eltern sehen einen sinnvollen Fortschritt."""
    _kind_lernt(client, fake_llm, app_env)

    # Zurück in die Elternrolle.
    seite = client.get("/login")
    client.post("/login", data={"_csrf": csrf_from(seite.text),
                                "password": "geheim123"})
    seite = client.get("/eltern/lernfortschritt")

    assert seite.status_code == 200
    assert "Brüche" in seite.text
    assert "Zähler und Nenner getrennt addiert" in seite.text
    assert "im Aufbau" in seite.text


def test_elternsicht_ist_fuer_kinder_gesperrt(client, fake_llm, fake_cli,
                                              app_env):
    """Die Rollentrennung bleibt unverändert (§16)."""
    _kind_lernt(client, fake_llm, app_env)
    antwort = client.get("/eltern/lernfortschritt")
    assert antwort.status_code == 403
    assert "Eltern-Bereich" in antwort.text


def test_elternsicht_zeigt_keine_modellgedanken(client, fake_llm, fake_cli,
                                                app_env):
    """§18: beobachtbare Lernsignale — keine rohen Modellüberlegungen."""
    _kind_lernt(client, fake_llm, app_env)
    seite = client.get("/login")
    client.post("/login", data={"_csrf": csrf_from(seite.text),
                                "password": "geheim123"})
    seite = client.get("/eltern/lernfortschritt")

    for verraeterisch in ("prompt", "token", "temperature", "system:"):
        assert verraeterisch not in seite.text.lower()


def test_die_modellsicht_erklaert_die_form_jedes_typs(app_env):
    """Ein Modell kann „typ: bruch" nicht erraten.

    Auf der Testinstallation scheiterte die Erzeugung reihenweise an
    „„a" muss ein Bruch [Zähler, Nenner] mit Nenner > 0 sein" — das Register
    verlangte eine Form, die es dem Modell nie mitgeteilt hatte. Der Fehler
    lag nicht beim Modell.
    """
    from app.adaptiv import komponenten

    sicht = {k["component"]: k for k in komponenten.fuer_modell()}

    bruch = sicht["FractionStrip"]["parameter"]["a"]
    assert bruch["form"] == "[Zähler, Nenner]"
    assert bruch["beispiel"] == [1, 2]

    liste = sicht["NumberLine"]["parameter"]["marken"]
    assert liste["form"] == "Liste von [Zähler, Nenner]"
    assert liste["beispiel"] == [[1, 2], [1, 3]]

    ganz = sicht["AreaModel"]["parameter"]["zeilen"]
    assert ganz["form"] == "ganze Zahl"

    # Und der Renderer bleibt weiterhin unsichtbar (§3).
    for eintrag in sicht.values():
        assert "renderer" not in eintrag
