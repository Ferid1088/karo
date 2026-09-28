"""Jede Themenkarte sagt selbst, ob Karo sie unterrichten kann.

Vorher stand ein einziger Verweis („Brüche üben mit Karo") über dem Raster
— rollenabhängig, ohne Bezug zu einem Thema, und er verriet nicht, welches
der Themen überhaupt eine Lernreihe hat. Die Karte ist der Ort, an dem das
Kind die Frage stellt, also gehört die Antwort auf die Karte.

Was es nicht gibt, wird gesagt statt versteckt (`lektionen.py`).
"""
from .conftest import csrf_from
from .test_app import einrichten


def _themen(client, fake_llm, app_env, *labels):
    from app import topics
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True)
    return [topics.anlegen(label) for label in labels]


def test_thema_mit_lernreihe_bekommt_einen_knopf(client, fake_llm, fake_cli,
                                                 app_env):
    _themen(client, fake_llm, app_env, "Brüche addieren und subtrahieren")

    seite = client.get("/lernen?status=neu").text

    assert "Starten" in seite
    assert 'action="/lernen/adaptiv/start"' in seite
    assert 'value="Brüche addieren und subtrahieren"' in seite


def test_jede_karte_hat_einen_aktiven_knopf(client, fake_llm, fake_cli,
                                            app_env):
    """Auch ohne verfasste Lernreihe. Ein abgeblendeter Knopf auf zehn von elf
    Karten sieht aus wie eine kaputte App, nicht wie eine ehrliche."""
    _themen(client, fake_llm, app_env, "Brüche kürzen", "Würfel: Volumen")

    seite = client.get("/lernen?status=neu").text

    assert seite.count('action="/lernen/adaptiv/start"') == 2
    assert "disabled" not in seite
    assert 'value="Brüche kürzen"' in seite
    assert 'value="Würfel: Volumen"' in seite


def test_ohne_lernreihe_sagt_das_die_naechste_seite(client, fake_llm,
                                                    fake_cli, app_env):
    """Die Ehrlichkeit wandert vom Kärtchen auf die Antwortseite — sie
    verschwindet nicht. Untergeschoben wird weiterhin nichts."""
    from .test_app import kind_modus_aktivieren
    (topic_id,) = _themen(client, fake_llm, app_env, "Würfel: Volumen")
    kind_modus_aktivieren(client)
    token = csrf_from(client.get("/lernen?status=neu").text)

    seite = client.post("/lernen/adaptiv/start",
                        data={"_csrf": token, "thema": "Würfel: Volumen",
                              "topic_id": str(topic_id)})

    assert "noch keine Lernreihe" in seite.text
    assert "Würfel: Volumen" in seite.text
    # Kein Werkstattbericht auf dem Kinderschirm: wie eine Lernreihe
    # entsteht, beantwortet keine Frage, die das Kind gerade hat.
    hinweis = seite.text[seite.text.index("noch keine Lernreihe"):]
    hinweis = hinweis[:hinweis.index("</section>")]
    assert "von Hand" not in hinweis
    assert "geprüft" not in hinweis
    # Und nichts Unpassendes: die Bruchlektion hat mit Volumen nichts zu tun
    # (siehe test_empfehlungen.py).
    assert "Brüche mit verschiedenen Nennern addieren" not in seite.text
    # Vor allem: keine Sitzung, keine untergeschobene Bruchlektion.
    assert app_env.db.q("SELECT * FROM lern_sitzung") == []


def test_der_knopf_startet_wirklich_den_diagnoseweg(client, fake_llm,
                                                    fake_cli, app_env):
    """Derselbe Loop wie „Brüche addieren" — nicht nur ein Link."""
    from .test_app import kind_modus_aktivieren
    _themen(client, fake_llm, app_env, "Brüche addieren und subtrahieren")
    kind_modus_aktivieren(client)
    token = csrf_from(client.get("/lernen?status=neu").text)

    seite = client.post("/lernen/adaptiv/start",
                        data={"_csrf": token,
                              "thema": "Brüche addieren und subtrahieren"})

    assert "noch keine Lernreihe" not in seite.text
    sitzung = app_env.db.q1("SELECT * FROM lern_sitzung ORDER BY id DESC LIMIT 1")
    assert sitzung["zustand"] == "DIAGNOSING"


def test_ohne_den_schalter_bleibt_die_karte_wie_bisher(client, fake_llm,
                                                       fake_cli, app_env):
    from app import topics
    einrichten(client, fake_llm)
    topics.anlegen("Brüche addieren und subtrahieren")

    seite = client.get("/lernen?status=neu").text

    assert "Mit Karo üben" not in seite
    assert "noch keine Lernreihe" not in seite


def test_kein_globaler_verweis_mehr_ueber_dem_raster(client, fake_llm,
                                                     fake_cli, app_env):
    """Der alte Sammelverweis hing an der Rolle und an keinem Thema: als
    Elternteil war er unsichtbar, und er verriet nie, welches der Themen
    überhaupt unterrichtet werden kann. Die Karte kann beides."""
    from .test_app import kind_modus_aktivieren
    _themen(client, fake_llm, app_env, "Brüche addieren und subtrahieren")
    kind_modus_aktivieren(client)

    seite = client.get("/lernen?status=neu").text

    assert "Brüche üben mit Karo" not in seite
    assert "Starten" in seite


def test_der_knopf_erscheint_auch_fuer_eltern(client, fake_llm, fake_cli,
                                              app_env):
    """Die Route prüft den Schalter, nicht die Rolle — die Karte jetzt auch.
    Sonst sucht man als Elternteil wieder vergeblich nach dem Einstieg."""
    _themen(client, fake_llm, app_env, "Brüche addieren und subtrahieren")

    seite = client.get("/lernen?status=neu")

    assert "Für Eltern" in seite.text          # also eine Elternsitzung
    assert "Starten" in seite.text


def test_der_knopf_traegt_die_handlungsfarbe(client, fake_llm, fake_cli,
                                             app_env):
    _themen(client, fake_llm, app_env, "Brüche addieren und subtrahieren")

    seite = client.get("/lernen?status=neu").text

    assert 'aria-label="Starten: Brüche addieren und subtrahieren"' in seite
    assert 'class="topics-start"' in seite
    css = client.get('/static/meine-themen.css').text
    assert '.topics-start' in css


def test_die_lektionszeile_traegt_keine_eigene_gestaltung(client, fake_llm,
                                                          fake_cli, app_env):
    """„Das geht schon" ist ein <button>, sieht aber wie eine Listenzeile aus.

    Ohne eigene Regel gewinnt die Knopf-Grundregel mit ihrer vollen
    Handlungsfarbe, während `.simple-list-link` die Schrift dunkel lässt —
    dunkelviolett auf violett, also unlesbar. Die Gestalt gehört ins
    Stylesheet, nicht in ein `style`-Attribut, das genau das verdeckt.
    """
    from .test_app import kind_modus_aktivieren
    _themen(client, fake_llm, app_env, "Würfel: Volumen")
    kind_modus_aktivieren(client)

    seite = client.get("/lernen/adaptiv").text
    zeile = seite[seite.index("Das geht schon"):]
    zeile = zeile[:zeile.index("</section>")]

    assert 'class="simple-list-link"' in zeile
    assert "style=" not in zeile

    css = client.get("/static/simple.css").text
    assert "button.simple-list-link" in css
