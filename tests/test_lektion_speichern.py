"""Schritt 2: eine geprüfte Lektion in den Katalog schreiben und freigeben.

Die Freigabe kommt zum Schluss, und das ist kein Detail. Die Schreibvorgänge
laufen über mehrere Transaktionen; bräche einer davon ab, stünde eine halbe
Lektion in der Datenbank. Weil aber alles ungeprüft geschrieben und erst
danach freigegeben wird, ist eine halbe Lektion für ein Kind unsichtbar —
die Prüf-Sperre aus §11 trägt hier die Atomarität.

Freigegeben wird nach bestandener Prüfung, ohne Klick eines Elternteils:
das ist die Entscheidung „auto-approve after validation". Ungeprüft heisst
weiterhin unsichtbar, nur wartet die Sperre nicht mehr auf einen Menschen.
"""
import copy

import pytest

from .test_lektion_erzeugung import _lektion
from .test_app import einrichten


def test_eine_geprueufte_lektion_landet_vollstaendig_im_katalog(
        client, fake_llm, fake_cli, app_env):
    from app.adaptiv import erzeugung, inhalt_store, lektionen, store, schemas
    einrichten(client, fake_llm)

    konzept_id = erzeugung.speichern(_lektion())

    lektion = lektionen.fuer_thema("Würfel: Volumen")
    assert lektion is not None and lektion["konzept_id"] == konzept_id
    fehlertypen = store.fehlertypen(konzept_id)
    assert [f["fehler_key"] for f in fehlertypen] == ["kanten-addiert"]
    rollen = {a["rolle"] for a in inhalt_store.aufgaben(fehlertypen[0]["id"])}
    assert rollen == set(schemas.AUFGABEN_ROLLEN)
    assert store.erstkontakt(konzept_id)["anker"].startswith("Wie viele")


def test_tier_eins_erkennt_die_erzeugte_fehlvorstellung(client, fake_llm,
                                                        fake_cli, app_env):
    """Der Zweck des Ganzen: beim nächsten Kind trifft der Katalog."""
    from app.adaptiv import erzeugung, katalog
    einrichten(client, fake_llm)
    konzept_id = erzeugung.speichern(_lektion())

    treffer = katalog.identifiziere(konzept_id, "9")

    assert treffer.erkannt and treffer.tier == 1
    assert treffer.fehlertyp["fehler_key"] == "kanten-addiert"


def test_das_ausliefern_ruft_kein_modell(client, fake_llm, fake_cli, app_env):
    """A3: einmal erzeugt, danach reiner Lookup — das ganze Kostenmodell."""
    from app.adaptiv import erzeugung, katalog
    einrichten(client, fake_llm)
    konzept_id = erzeugung.speichern(_lektion())
    fake_llm.calls.clear()

    treffer = katalog.identifiziere(konzept_id, "9")
    erklaerung = katalog.erklaerung_fuer(treffer.fehlertyp["id"], 6)

    assert erklaerung is not None
    assert fake_llm.calls == []


def test_erzeugtes_ist_als_erzeugt_erkennbar(client, fake_llm, fake_cli,
                                             app_env):
    """§6 speichert die Herkunft — kuratiert und erzeugt sind nicht dasselbe,
    auch wenn beide ausgeliefert werden."""
    from app.adaptiv import erzeugung, store
    einrichten(client, fake_llm)
    konzept_id = erzeugung.speichern(_lektion())

    konzept = store.konzept(konzept_id)
    assert konzept["quelle"] == "erzeugt"
    assert konzept["geprueft_am"]
    assert all(f["quelle"] == "erzeugt" for f in store.fehlertypen(konzept_id))


def test_eine_ungueltige_lektion_hinterlaesst_nichts(client, fake_llm,
                                                     fake_cli, app_env):
    """Kein halber Katalogeintrag: geprüft wird vor dem ersten Schreiben."""
    from app.adaptiv import erzeugung, schemas, store
    einrichten(client, fake_llm)
    kaputt = _lektion()
    del kaputt["fehlertypen"][0]["aufgaben"]["transfer"]

    with pytest.raises(schemas.InhaltUngueltig):
        erzeugung.speichern(kaputt)

    assert store.konzept_nach_key("mathematik", "geometrie",
                                  "wuerfel-volumen") is None


def test_zweimal_speichern_verdoppelt_nichts(client, fake_llm, fake_cli,
                                             app_env):
    from app.adaptiv import erzeugung, inhalt_store, store
    einrichten(client, fake_llm)

    erster = erzeugung.speichern(_lektion())
    zweiter = erzeugung.speichern(_lektion())

    assert erster == zweiter
    fehlertypen = store.fehlertypen(erster)
    assert len(fehlertypen) == 1
    assert len(inhalt_store.aufgaben(fehlertypen[0]["id"])) == 5


def test_eine_erzeugte_lektion_verdraengt_keine_verfasste(client, fake_llm,
                                                          fake_cli, app_env):
    """Die Bruchlektion bleibt, was sie ist."""
    from app.adaptiv import erzeugung, lektionen, store
    einrichten(client, fake_llm)

    erzeugung.speichern(_lektion())

    brueche = store.konzept_nach_key("mathematik", "brueche",
                                     "ungleichnamig-addieren")
    assert brueche["quelle"] == "kuratiert"
    assert lektionen.fuer_thema("Brüche addieren")["konzept_id"] == brueche["id"]


def test_ein_abbruch_mitten_im_schreiben_bleibt_unsichtbar(
        client, fake_llm, fake_cli, app_env, monkeypatch):
    """Die eigentliche Zusicherung: die Freigabe zum Schluss trägt die
    Atomarität. Bricht das Schreiben ab, steht zwar eine halbe Lektion in
    der Datenbank — sichtbar wird sie nie, weil nichts freigegeben ist.
    """
    from app.adaptiv import erzeugung, inhalt_store, lektionen, store
    einrichten(client, fake_llm)

    echtes_sichern = inhalt_store.aufgabe_sichern
    aufrufe = {"n": 0}

    def bricht_ab(*args, **kwargs):
        aufrufe["n"] += 1
        if aufrufe["n"] == 3:          # mitten in den fünf Rollen
            raise RuntimeError("Verbindung weg")
        return echtes_sichern(*args, **kwargs)

    monkeypatch.setattr(inhalt_store, "aufgabe_sichern", bricht_ab)

    with pytest.raises(RuntimeError):
        erzeugung.speichern(_lektion())

    # Die Zeilen sind da — aber nichts davon erreicht ein Kind.
    halb = store.konzept_nach_key("mathematik", "geometrie", "wuerfel-volumen")
    assert halb is not None
    assert halb["geprueft_am"] is None
    assert lektionen.fuer_thema("Würfel: Volumen") is None
    assert store.fehlertypen(halb["id"]) == []
