"""Was Karo vorschlägt, muss zum gefragten Thema gehören.

Die Auswahlseite listete schlicht alles, was im Katalog steht. Bei einem
einzigen verfassten Inhalt heißt das: wer „Würfel: Volumen" wählt, bekommt
„Brüche mit verschiedenen Nennern addieren" als „Das geht schon"
angeboten. Das ist kein Vorschlag, das ist ein Inhaltsverzeichnis — und für
ein Kind schlicht verwirrend.

Ein Vorschlag ist nur dann einer, wenn er mit dem gefragten Thema zu tun
hat. Lieber gar keiner als ein unpassender.
"""
from .test_app import einrichten


def _bereit(client, fake_llm):
    einrichten(client, fake_llm)
    from app.adaptiv import lektionen
    return lektionen


def test_fremdes_thema_bekommt_keinen_vorschlag(client, fake_llm, fake_cli,
                                                app_env):
    lektionen = _bereit(client, fake_llm)

    assert lektionen.empfehlungen("Würfel: Volumen", "mathematik") == []
    assert lektionen.empfehlungen("Photosynthese", "mathematik") == []


def test_verwandtes_thema_bekommt_die_passende_lernreihe(client, fake_llm,
                                                         fake_cli, app_env):
    """„Brüche kürzen" ist ein anderes Konzept, aber dasselbe Gebiet — hier
    ist der Verweis auf die Bruchlektion sinnvoll."""
    lektionen = _bereit(client, fake_llm)

    vorschlaege = lektionen.empfehlungen("Brüche kürzen", "mathematik")

    assert [l["konzept_key"] for l in vorschlaege] == ["ungleichnamig-addieren"]


def test_fuellwoerter_stiften_keine_verwandtschaft(client, fake_llm, fake_cli,
                                                   app_env):
    """„Volumen bei verschiedenen Maßeinheiten" und „Brüche mit
    verschiedenen Nennern addieren" teilen nur „verschiedenen". Das ist
    keine Verwandtschaft, das ist Grammatik."""
    lektionen = _bereit(client, fake_llm)

    assert lektionen.empfehlungen("Volumen bei verschiedenen Maßeinheiten", "mathematik") == []


def test_die_seite_bietet_nichts_unpassendes_an(client, fake_llm, fake_cli,
                                                app_env):
    from .conftest import csrf_from
    from .test_app import kind_modus_aktivieren
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True)
    kind_modus_aktivieren(client)
    token = csrf_from(client.get("/lernen").text)

    seite = client.post("/lernen/adaptiv/start",
                        data={"_csrf": token, "thema": "Würfel: Volumen"}).text

    assert "Würfel: Volumen" in seite
    assert "Brüche mit verschiedenen Nennern addieren" not in seite
    assert "Das geht schon" not in seite
