"""Meilenstein 1 — Domänenfundament des adaptiven Lernens.

Jeder Test benennt die Invariante aus 03_INVARIANTS.md, die er hält.
Die Gruppe-A-Tests sind dauerhafte Zusicherungen: wird einer davon unbequem,
ist die Implementierung falsch, nicht der Test.
"""
from .test_app import einrichten


# --------------------------------------------------------------------------
# Hilfsaufbau: ein Konzept mit einem Fehlertyp und einer geprüften Erklärung
# --------------------------------------------------------------------------

INHALT = {
    "haken": "Du hattest schon ein halbes Stück und bekommst noch etwas dazu.",
    "erkenntnis": "Dein Ergebnis wurde kleiner, obwohl etwas dazugekommen ist.",
    "regel": "Mach die Stücke zuerst gleich groß, dann zähle sie zusammen.",
    "bild": {
        "zeigt": "Zwei gleich breite Streifen, einer in Halbe, einer in Drittel.",
        "bewegt": "Beide Streifen werden in Sechstel geschnitten.",
        "bleibt_gleich": "Die Menge bleibt gleich, nur die Anzahl der Stücke ändert sich.",
    },
    "aufgabe": {"frage": "1/2 + 1/4 = ?", "loesung": "3/4",
                "tipp": "Wie viele Viertel sind eine Hälfte?"},
}


def _katalog(geprueft: bool = True, schwierigkeit: int = 2):
    """Ein kuratierter Katalog. `geprueft` betrifft nur die Erklärung — an
    ihr hängt der Test, dass Ungeprüftes nicht ausgeliefert wird. Konzept und
    Fehlertyp sind hier immer geprüft: sie stehen für verfassten Inhalt."""
    from app.adaptiv import katalog, store

    # Eigene Schluessel: die verfasste Bruchlektion steht seit dem Hochfahren
    # im Katalog, und dieser Aufbau soll ihr nicht ins Gehege kommen
    # (Versionszaehlung der Erklaerungen, Pruefzustand).
    konzept_id = store.konzept_sichern(
        "mathematik", "brueche-pruefstand", "ungleichnamig-addieren",
        "Brüche mit verschiedenen Nennern addieren", 5, 6, geprueft=True)
    fehlertyp_id = store.fehlertyp_sichern(
        konzept_id, "zaehler-und-nenner-addiert",
        "Zähler und Nenner getrennt addiert", geprueft=True)
    katalog.fehlertyp_lernen(fehlertyp_id, "2/5", quelle="kuratiert")
    erklaerung_id = store.erklaerung_anlegen(
        fehlertyp_id, 6, INHALT,
        visualisierung={"component": "FractionStrip",
                        "parameters": {"a": [1, 2], "b": [1, 3]},
                        "animation": "cut_then_slide"},
        schwierigkeit=schwierigkeit, geprueft=geprueft)
    return konzept_id, fehlertyp_id, erklaerung_id


# --------------------------------------------------------------------------
# A3 — zwischengespeicherte Inhalte rufen kein Modell
# --------------------------------------------------------------------------

def test_tier1_treffer_ruft_kein_modell(client, fake_llm, app_env):
    """A3: Ein Tier-1-Katalogtreffer löst null Modellaufrufe aus.

    Das ist der Test, der das gesamte Kostenmodell schützt.
    """
    from app.adaptiv import katalog

    einrichten(client, fake_llm)
    konzept_id, fehlertyp_id, _ = _katalog()
    fake_llm.calls.clear()

    treffer = katalog.identifiziere(konzept_id, "2/5")
    assert treffer.erkannt and treffer.tier == 1
    assert treffer.fehlertyp["fehler_key"] == "zaehler-und-nenner-addiert"

    erklaerung = katalog.erklaerung_fuer(fehlertyp_id, 6)
    assert erklaerung["inhalt"]["regel"]
    assert fake_llm.calls == []


def test_unbekannter_fehler_ruft_ohne_schalter_kein_modell(client, fake_llm,
                                                           app_env):
    """A3/§6: Ohne Tier-2/3-Schalter wird ehrlich nichts erkannt — statt heimlich
    ein Modell zu rufen."""
    from app.adaptiv import katalog

    einrichten(client, fake_llm)
    konzept_id, _, _ = _katalog()
    fake_llm.calls.clear()

    treffer = katalog.identifiziere(konzept_id, "völlig andere Antwort")
    assert not treffer.erkannt
    assert fake_llm.calls == []


# --------------------------------------------------------------------------
# A4 — Fehler, nicht Themen, steuern die Inhaltsauswahl
# --------------------------------------------------------------------------

def test_gleiche_fehlvorstellung_andere_schreibweise_gleicher_fehlertyp(
        client, fake_llm, app_env):
    """A4: Zwei verschieden geschriebene Antworten derselben Fehlvorstellung
    landen beim selben Fehlertyp."""
    from app.adaptiv import katalog

    einrichten(client, fake_llm)
    konzept_id, fehlertyp_id, _ = _katalog()

    for schreibweise in ("2/5", " 2 / 5 ", "2:5"):
        treffer = katalog.identifiziere(konzept_id, schreibweise)
        assert treffer.erkannt, schreibweise
        assert treffer.fehlertyp["id"] == fehlertyp_id, schreibweise


def test_zwei_fehlvorstellungen_ergeben_zwei_erklaerungen(client, fake_llm,
                                                          app_env):
    """A4: Dasselbe Thema mit zwei Fehlvorstellungen liefert zwei Erklärungen."""
    from app.adaptiv import katalog, store

    einrichten(client, fake_llm)
    konzept_id, erster, _ = _katalog()
    zweiter = store.fehlertyp_sichern(konzept_id, "nenner-multipliziert",
                                      "Nenner einfach multipliziert",
                                      geprueft=True)
    katalog.fehlertyp_lernen(zweiter, "2/6")
    anderer_inhalt = {**INHALT, "regel": "Nimm den kleinsten gemeinsamen Nenner."}
    store.erklaerung_anlegen(zweiter, 6, anderer_inhalt, geprueft=True)

    a = katalog.identifiziere(konzept_id, "2/5")
    b = katalog.identifiziere(konzept_id, "2/6")
    assert a.fehlertyp["id"] != b.fehlertyp["id"]
    assert (katalog.erklaerung_fuer(a.fehlertyp["id"], 6)["inhalt"]["regel"]
            != katalog.erklaerung_fuer(b.fehlertyp["id"], 6)["inhalt"]["regel"])


def test_neue_schreibweise_erzeugt_keinen_neuen_fehlertyp(client, fake_llm,
                                                          app_env):
    """A4: Eine andere Formulierung erzeugt keinen zweiten Fehlertyp."""
    from app.adaptiv import katalog, store

    einrichten(client, fake_llm)
    konzept_id, fehlertyp_id, _ = _katalog()
    vorher = len(store.fehlertypen(konzept_id))

    katalog.fehlertyp_lernen(fehlertyp_id, "2 zu 5", quelle="beobachtet")

    assert len(store.fehlertypen(konzept_id)) == vorher
    assert katalog.identifiziere(konzept_id, "2 zu 5").fehlertyp["id"] == fehlertyp_id


# --------------------------------------------------------------------------
# A1/A2 — kein ausführbares Modell-Erzeugnis, alles schemageprüft
# --------------------------------------------------------------------------

def test_markup_im_inhalt_wird_abgelehnt():
    """A1: Ein Katalogeintrag enthält kein HTML, SVG, JS oder CSS."""
    import pytest
    from app.adaptiv import schemas

    boese = {**INHALT, "regel": "<script>alert(1)</script>"}
    with pytest.raises(schemas.InhaltUngueltig):
        schemas.pruefe_inhalt(boese)


def test_unbekannte_komponente_wird_abgelehnt_und_faellt_zurueck():
    """A1: Unbekannte Komponenten-Id wird verworfen, nicht gerendert — und es
    greift die sichere Rückfallkomponente."""
    import pytest
    from app.adaptiv import schemas

    with pytest.raises(schemas.InhaltUngueltig):
        schemas.pruefe_visualisierung({"component": "EvilCanvas",
                                       "parameters": {}})

    rueckfall, grund = schemas.visualisierung_oder_fallback(
        {"component": "EvilCanvas", "parameters": {}})
    assert rueckfall == schemas.FALLBACK_VISUALISIERUNG
    assert grund


def test_ungueltige_parameter_werden_abgelehnt():
    """A1: Unpassende Parameter werden verworfen, nicht gerendert."""
    import pytest
    from app.adaptiv import schemas

    with pytest.raises(schemas.InhaltUngueltig):
        schemas.pruefe_visualisierung({"component": "FractionStrip",
                                       "parameters": "1/2"})


def test_kaputte_modellausgabe_erreicht_die_datenbank_nicht(client, fake_llm,
                                                            app_env):
    """A2: Kaputtes JSON erreicht weder Datenbank noch Template — und erzeugt
    keinen 500er, sondern einen definierten Rückfall."""
    import pytest
    from app.adaptiv import schemas, store

    einrichten(client, fake_llm)
    konzept_id = store.konzept_sichern("mathematik", "brueche", "kuerzen",
                                       "Brüche kürzen")
    fehlertyp_id = store.fehlertyp_sichern(konzept_id, "nur-zaehler-geteilt",
                                           "Nur den Zähler geteilt")

    for kaputt in ({}, {"haken": "nur ein Feld"}, "kein Objekt", None):
        with pytest.raises(schemas.InhaltUngueltig):
            store.erklaerung_anlegen(fehlertyp_id, 6,
                                     schemas.pruefe_inhalt(kaputt))

    assert store.erklaerungen(fehlertyp_id) == []


def test_schwache_erklaerung_wird_gemeldet():
    """§4: `erkenntnis` und `bild.bleibt_gleich` sind die Qualitätssignale."""
    from app.adaptiv import schemas

    schwach = {**INHALT, "erkenntnis": "Falsch.",
               "bild": {**INHALT["bild"], "bleibt_gleich": "gleich"}}
    mangel = schemas.schwachstellen(schemas.pruefe_inhalt(schwach))
    assert len(mangel) == 2
    assert schemas.schwachstellen(schemas.pruefe_inhalt(INHALT)) == []


# --------------------------------------------------------------------------
# §6/§11 — versionieren statt ersetzen, Ungeprüftes bleibt drin
# --------------------------------------------------------------------------

def test_ungeprueftes_wird_keinem_kind_ausgeliefert(client, fake_llm,
                                                    app_env):
    """§11: Ein nicht geprüfter Inhalt wird nicht ausgeliefert."""
    from app.adaptiv import katalog

    einrichten(client, fake_llm)
    _, fehlertyp_id, erklaerung_id = _katalog(geprueft=False)

    assert katalog.erklaerung_fuer(fehlertyp_id, 6) is None

    from app.adaptiv import store
    store.erklaerung_freigeben(erklaerung_id)
    assert katalog.erklaerung_fuer(fehlertyp_id, 6) is not None


def test_neue_variante_ersetzt_die_alte_nicht(client, fake_llm,
                                              app_env):
    """§6: Versionieren, nie destruktiv ersetzen; Verlierer werden archiviert."""
    from app.adaptiv import store

    einrichten(client, fake_llm)
    _, fehlertyp_id, erste = _katalog()
    zweite = store.erklaerung_anlegen(fehlertyp_id, 6,
                                      {**INHALT, "regel": "Andere Formulierung."},
                                      geprueft=True)

    assert store.erklaerung(erste)["version"] == 1
    assert store.erklaerung(zweite)["version"] == 2

    store.erklaerung_archivieren(zweite)
    assert store.erklaerung(zweite) is not None          # archiviert, nicht weg
    assert [e["id"] for e in store.erklaerungen(fehlertyp_id)] == [erste]
    assert len(store.erklaerungen(fehlertyp_id, mit_archivierten=True)) == 2


# --------------------------------------------------------------------------
# A5 — Wiederholungen sind endlich
# --------------------------------------------------------------------------

def test_drei_erfolglose_runden_eskalieren(client, fake_llm, app_env):
    """A5: Drei erfolglose Lehrrunden auf einen Fehlertyp → ESCALATED, danach
    keine weitere Erklärung, und der Fehlertyp ist im Profil markiert."""
    from app.adaptiv import sitzung, store

    einrichten(client, fake_llm)
    konzept_id, fehlertyp_id, erklaerung_id = _katalog()

    s = sitzung.starten(konzept_id=konzept_id)
    sitzung.wechsle(s["id"], sitzung.MATERIAL_ANALYZED)
    sitzung.wechsle(s["id"], sitzung.DIAGNOSING)
    sitzung.fehler_erkannt(s["id"], fehlertyp_id, "2/5")
    sitzung.unterricht_beginnen(s["id"], erklaerung_id)

    for _ in range(sitzung.max_runden()):
        stand = sitzung.runde_gescheitert(s["id"])

    assert stand["zustand"] == sitzung.ESCALATED
    assert not sitzung.darf_erklaeren(stand)

    profil = store.fortschritt(konzept_id, fehlertyp_id)
    assert profil["braucht_mensch"] == 1
    assert profil["mastery"] == "braucht_mensch"


def test_eskalierte_sitzung_zaehlt_nicht_endlos_weiter(client, fake_llm,
                                                       app_env):
    """A5: Kein Pfad kann Lehrrunden unbegrenzt wiederholen."""
    from app.adaptiv import sitzung

    einrichten(client, fake_llm)
    konzept_id, fehlertyp_id, erklaerung_id = _katalog()

    s = sitzung.starten(konzept_id=konzept_id)
    sitzung.wechsle(s["id"], sitzung.MATERIAL_ANALYZED)
    sitzung.wechsle(s["id"], sitzung.DIAGNOSING)
    sitzung.fehler_erkannt(s["id"], fehlertyp_id)
    sitzung.unterricht_beginnen(s["id"], erklaerung_id)

    for _ in range(sitzung.max_runden() + 5):
        stand = sitzung.runde_gescheitert(s["id"])

    assert stand["zustand"] == sitzung.ESCALATED
    assert stand["runden"] == sitzung.max_runden()


def test_verbotener_uebergang_wird_abgewiesen(client, fake_llm,
                                              app_env):
    """§7: Der Automat lässt nur vorgesehene Übergänge zu."""
    import pytest
    from app.adaptiv import sitzung

    einrichten(client, fake_llm)
    s = sitzung.starten()
    with pytest.raises(sitzung.UebergangVerboten):
        sitzung.wechsle(s["id"], sitzung.TEACHING)


# --------------------------------------------------------------------------
# A6 — Zustand übersteht Unterbrechung
# --------------------------------------------------------------------------

def test_sitzung_wird_an_derselben_phase_fortgesetzt(client, fake_llm,
                                                     app_env):
    """A6: Phase, Versuche, Beherrschung und die gegebene Antwort überstehen
    Neuladen und Neuanmeldung — der Zustand liegt in der Datenbank, nicht im
    Cookie."""
    from app.adaptiv import sitzung, store

    einrichten(client, fake_llm)
    konzept_id, fehlertyp_id, erklaerung_id = _katalog()

    s = sitzung.starten(konzept_id=konzept_id)
    sitzung.wechsle(s["id"], sitzung.MATERIAL_ANALYZED)
    sitzung.wechsle(s["id"], sitzung.DIAGNOSING)
    sitzung.fehler_erkannt(s["id"], fehlertyp_id, "2/5")
    sitzung.unterricht_beginnen(s["id"], erklaerung_id)
    sitzung.wechsle_phase(s["id"], sitzung.RULE)
    sitzung.wechsle_phase(s["id"], sitzung.WORKED_EXAMPLE)

    client.post("/logout")
    einrichten(client, fake_llm)          # neue Anmeldung, neue Cookie-Session

    wieder = sitzung.laufende()
    assert wieder["id"] == s["id"]
    assert wieder["zustand"] == sitzung.TEACHING
    assert wieder["phase"] == sitzung.WORKED_EXAMPLE
    assert wieder["letzte_antwort"] == "2/5"
    assert wieder["fehlertyp_id"] == fehlertyp_id


def test_jeder_uebergang_ist_festgeschrieben(client, fake_llm,
                                             app_env):
    """§7: Jeder Übergang wird geschrieben und ist damit prüfbar."""
    from app.adaptiv import sitzung, store

    einrichten(client, fake_llm)
    konzept_id, fehlertyp_id, erklaerung_id = _katalog()

    s = sitzung.starten(konzept_id=konzept_id)
    sitzung.wechsle(s["id"], sitzung.MATERIAL_ANALYZED)
    sitzung.wechsle(s["id"], sitzung.DIAGNOSING)
    sitzung.fehler_erkannt(s["id"], fehlertyp_id)
    sitzung.unterricht_beginnen(s["id"], erklaerung_id)
    sitzung.wechsle_phase(s["id"], sitzung.RULE)

    protokoll = store.ereignisse(s["id"])
    assert [e["nach_zustand"] for e in protokoll if e["nach_zustand"]] == [
        sitzung.INPUT_RECEIVED, sitzung.MATERIAL_ANALYZED, sitzung.DIAGNOSING,
        sitzung.ERROR_IDENTIFIED, sitzung.TEACHING]
    assert [e["nach_phase"] for e in protokoll if e["nach_phase"]] == [
        sitzung.HOOK, sitzung.RULE]


# --------------------------------------------------------------------------
# A8 — Beherrschung wird verdient
# --------------------------------------------------------------------------

def test_eine_richtige_antwort_ist_keine_beherrschung(client, fake_llm,
                                                      app_env):
    """A8: Eine richtige Antwort erzeugt keine Beherrschung."""
    from app.adaptiv import sitzung, store

    einrichten(client, fake_llm)
    konzept_id, fehlertyp_id, erklaerung_id = _katalog()

    s = sitzung.starten(konzept_id=konzept_id)
    sitzung.wechsle(s["id"], sitzung.MATERIAL_ANALYZED)
    sitzung.wechsle(s["id"], sitzung.DIAGNOSING)
    sitzung.fehler_erkannt(s["id"], fehlertyp_id)
    sitzung.unterricht_beginnen(s["id"], erklaerung_id)

    stand = sitzung.antwort_richtig(s["id"], "3/4")
    assert stand["zustand"] == sitzung.TEACHING
    assert store.fortschritt(konzept_id, fehlertyp_id)["mastery"] == "im_aufbau"

    stand = sitzung.antwort_richtig(s["id"], "5/6")
    assert stand["zustand"] == sitzung.MASTERED
    assert store.fortschritt(konzept_id, fehlertyp_id)["mastery"] == "sicher"


def test_mastery_schwelle_kommt_aus_der_konfiguration(client, fake_llm,
                                                      app_env):
    """A8: Die Schwelle steht in der Konfiguration, nicht als Zahl im Code."""
    from app.adaptiv import sitzung

    einrichten(client, fake_llm)
    app_env.config.update(adaptiv_mastery_treffer=3)
    cfg = app_env.config.load()

    assert sitzung.mastery_treffer(cfg) == 3
    assert not sitzung.beherrscht(2, cfg)
    assert sitzung.beherrscht(3, cfg)


def test_max_lehrrunden_kommt_aus_der_konfiguration(client, fake_llm,
                                                    app_env):
    """A5: Auch die Rundenzahl ist Konfiguration."""
    from app.adaptiv import sitzung

    einrichten(client, fake_llm)
    app_env.config.update(adaptiv_max_lehrrunden=2)
    cfg = app_env.config.load()

    konzept_id, fehlertyp_id, erklaerung_id = _katalog()
    s = sitzung.starten(konzept_id=konzept_id)
    sitzung.wechsle(s["id"], sitzung.MATERIAL_ANALYZED)
    sitzung.wechsle(s["id"], sitzung.DIAGNOSING)
    sitzung.fehler_erkannt(s["id"], fehlertyp_id)
    sitzung.unterricht_beginnen(s["id"], erklaerung_id)

    sitzung.runde_gescheitert(s["id"], cfg=cfg)
    stand = sitzung.runde_gescheitert(s["id"], cfg=cfg)
    assert stand["zustand"] == sitzung.ESCALATED


# --------------------------------------------------------------------------
# §13/§16 — normalisierte Eingabe, Schalter aus
# --------------------------------------------------------------------------

def test_drei_eingabewege_ergeben_eine_struktur(client, fake_llm,
                                                app_env):
    """§13: Scan, Themenblatt und getipptes Thema landen in einer Struktur."""
    from app.adaptiv import store

    einrichten(client, fake_llm)
    konzept_id = store.konzept_sichern("mathematik", "brueche", "addieren",
                                       "Brüche addieren")
    ids = [
        store.eingabe_anlegen("scan", fach="Mathematik", document_id=1,
                              aufgaben=[{"text": "1/2 + 1/3"}], konfidenz=0.8),
        store.eingabe_anlegen("themenblatt", fach="Mathematik",
                              thema_text="Bruchrechnung"),
        store.eingabe_anlegen("manuell", fach="Mathematik",
                              thema_text="Brüche addieren",
                              konzept_id=konzept_id),
    ]
    for eingabe_id in ids:
        eintrag = store.eingabe(eingabe_id)
        assert eintrag["fach"] == "Mathematik"
        assert isinstance(eintrag["aufgaben"], list)


def test_neue_schalter_sind_standardmaessig_aus(client, fake_llm,
                                                app_env):
    """§16: Das neue System ist abschaltbar und stört die laufende App nicht."""
    einrichten(client, fake_llm)
    cfg = app_env.config.load()

    assert cfg.adaptive_learning_enabled is False
    assert cfg.semantic_error_matching_enabled is False
    assert cfg.llm_error_creation_enabled is False
    assert cfg.content_experimentation_enabled is False
    assert cfg.worksheet_ai_analysis_enabled is False
