"""Der Katalog entscheidet, welche Lektionen es gibt — nicht eine Modulliste.

Zwei Dinge, die zusammengehören:

1. **Auffindbarkeit.** `lektionen.MODULE` war eine fest verdrahtete Liste von
   Python-Modulen, `STICHWORTE` eine handgeschriebene Tabelle daneben. Eine
   Lektion, die in der Datenbank steht und kein Modul ist, konnte damit nie
   gefunden werden. Verfasste Lektionen säen weiterhin — gesucht wird aber
   im Katalog.

2. **Prüfzustand.** §11 verlangt, dass ungeprüfter Inhalt kein Kind
   erreicht, und `lern_erklaerung`, `lern_erstkontakt` und `lern_hilfe`
   setzen das auch durch. `lern_konzept`, `lern_fehlertyp` und `lern_aufgabe`
   taten es nicht: eine ungeprüfte Aufgabe oder Fehlvorstellung wäre
   ausgeliefert worden.
"""
from .test_app import einrichten


def _katalog(client, fake_llm):
    einrichten(client, fake_llm)
    from app.adaptiv import lektionen
    lektionen.saee_alle()
    return lektionen


# --------------------------------------------------------------------------
# Auffindbarkeit: der Katalog ist die Quelle, nicht die Modulliste
# --------------------------------------------------------------------------

def test_eine_nur_in_der_datenbank_stehende_lektion_wird_gefunden(
        client, fake_llm, app_env):
    """Der Kern: ohne das kann keine erzeugte Lektion je ausgeliefert werden."""
    from app.adaptiv import lektionen, store
    _katalog(client, fake_llm)
    konzept_id = store.konzept_sichern(
        "mathematik", "geometrie", "wuerfel-volumen",
        "Volumen eines Würfels", 6, 8,
        stichworte=("wuerfel volumen", "volumen wuerfel"), geprueft=True)

    gefunden = {l["konzept_id"] for l in lektionen.verfuegbar()}
    treffer = lektionen.fuer_thema("Würfel: Volumen", "mathematik")

    assert konzept_id in gefunden
    assert treffer is not None and treffer["konzept_id"] == konzept_id


def test_ohne_stichworte_traegt_das_label(client, fake_llm, app_env):
    from app.adaptiv import lektionen, store
    _katalog(client, fake_llm)
    store.konzept_sichern("mathematik", "geometrie", "quader-volumen",
                          "Quader Volumen", 6, 8, geprueft=True)

    treffer = lektionen.fuer_thema("Quader Volumen", "mathematik")

    assert treffer is not None
    assert treffer["konzept_key"] == "quader-volumen"


def test_die_verfasste_bruchlektion_bleibt_unveraendert_auffindbar(
        client, fake_llm, app_env):
    """Die Umstellung darf die eine vorhandene Lektion nicht verlieren."""
    lektionen = _katalog(client, fake_llm)

    treffer = lektionen.fuer_thema("Brüche addieren und subtrahieren", "mathematik")

    assert treffer is not None
    assert treffer["konzept_key"] == "ungleichnamig-addieren"
    assert lektionen.fuer_thema("Brüche kürzen", "mathematik") is None
    assert lektionen.fuer_thema("Photosynthese", "mathematik") is None


# --------------------------------------------------------------------------
# Prüfzustand: ungeprüft erreicht kein Kind (§11)
# --------------------------------------------------------------------------

def test_ungeprueftes_konzept_wird_nicht_angeboten(client, fake_llm,
                                                   app_env):
    from app.adaptiv import lektionen, store
    _katalog(client, fake_llm)
    konzept_id = store.konzept_sichern(
        "mathematik", "geometrie", "prisma-volumen", "Prisma Volumen", 6, 8,
        stichworte=("prisma",), geprueft=False)

    assert konzept_id not in {l["konzept_id"] for l in lektionen.verfuegbar()}
    assert lektionen.fuer_thema("Prisma", "mathematik") is None

    store.konzept_freigeben(konzept_id)

    assert lektionen.fuer_thema("Prisma", "mathematik")["konzept_id"] == konzept_id


def test_ungepruefter_fehlertyp_trifft_nicht(client, fake_llm,
                                             app_env):
    """Tier 1 darf keine ungeprüfte Fehlvorstellung zurückgeben."""
    from app.adaptiv import katalog, store
    _katalog(client, fake_llm)
    konzept_id = store.konzept_sichern("mathematik", "x", "y", "Y", 5, 6,
                                       geprueft=True)
    fehlertyp_id = store.fehlertyp_sichern(konzept_id, "erfunden",
                                           "Erfunden", "", geprueft=False)
    store.alias_sichern(fehlertyp_id, "9/9", "test")

    assert katalog.identifiziere(konzept_id, "9/9").fehlertyp is None

    store.fehlertyp_freigeben(fehlertyp_id)

    assert katalog.identifiziere(konzept_id, "9/9").fehlertyp is not None


def test_ungepruefte_aufgabe_wird_nicht_ausgeliefert(client, fake_llm,
                                                     app_env):
    from app.adaptiv import inhalt_store, store
    _katalog(client, fake_llm)
    konzept_id = store.konzept_sichern("mathematik", "x", "z", "Z", 5, 6,
                                       geprueft=True)
    fehlertyp_id = store.fehlertyp_sichern(konzept_id, "k", "K", "",
                                           geprueft=True)
    inhalt_store.aufgabe_sichern(fehlertyp_id, inhalt_store.GEFUEHRT,
                                 "1/2 + 1/2 = ?", "1", geprueft=False)

    assert inhalt_store.aufgabe(fehlertyp_id, inhalt_store.GEFUEHRT) is None
    assert inhalt_store.aufgaben(fehlertyp_id) == []


def test_verfasster_inhalt_gilt_als_geprueft(client, fake_llm,
                                             app_env):
    """Von Menschen geschrieben heißt geprüft (§11) — sonst verschwände die
    Bruchlektion beim ersten Start nach der Umstellung."""
    from app.adaptiv import inhalt_store, store
    lektionen = _katalog(client, fake_llm)
    konzept = store.konzept_nach_key("mathematik", "brueche",
                                     "ungleichnamig-addieren")

    assert konzept["geprueft_am"]
    assert konzept["quelle"] == "kuratiert"
    for fehlertyp in store.fehlertypen(konzept["id"]):
        assert fehlertyp["geprueft_am"], fehlertyp["fehler_key"]
        assert inhalt_store.aufgaben(fehlertyp["id"]), fehlertyp["fehler_key"]


def test_der_katalog_steht_beim_start_und_nicht_erst_beim_ersten_klick(
        client, fake_llm, app_env):
    """Verfasste Lektionen säen beim Hochfahren, nicht beim ersten Aufruf.

    Lazy war es nur, solange `verfuegbar()` auf jedem Seitenaufbau lief.
    Seit die Themenkarte den Zustand nicht mehr vormerkt, rührt `/lernen`
    die adaptive Schicht nicht mehr an — eine frisch migrierte Datenbank
    behielte ihr ungeprüftes Konzept, bis zufällig jemand `/lernen/adaptiv`
    öffnet. Der Katalog darf nicht davon abhängen, welche Seite zuerst
    besucht wird.
    """
    from app.adaptiv import store
    einrichten(client, fake_llm)

    # Kein saee_alle(), kein Aufruf von /lernen/adaptiv.
    konzepte = store.konzepte_verfuegbar()

    assert [k["konzept_key"] for k in konzepte] == ["ungleichnamig-addieren"]
    assert konzepte[0]["stichworte"] == ["ungleichnamig", "brueche addieren"]
