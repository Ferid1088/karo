"""Abdeckung des adaptiven Kreislaufs — Invarianten aus dem Audit.

Die Voraussetzung-Luecke von Z3 (Bildschirm ohne Template und ohne Route)
soll sich nicht wiederholen. Zwei Invarianten sichern das ab:

- jede Bildschirm-Art, die `unterricht._bildschirm` liefern kann, hat
  einen eigenen Zweig in `adaptiv.html` — kein stiller Erfolgs-Fallback;
- jedes Formular eines Zweigs landet bei einer Aktion, die dieser
  Bildschirm in `ERWARTETE_BILDSCHIRME` auch hergibt.

Dazu Regressionen gegen veraltete Formulare: die Bildschirm-Art bleibt
beim Wechsel gefuehrt → selbststaendig gleich ("aufgabe"), also kann nur
die Kennung der konkreten Aufgabe einen alten POST von der neuen Aufgabe
fernhalten.
"""
import json
import re
from pathlib import Path

VORLAGE = (Path(__file__).resolve().parents[1]
           / "app/templates/adaptiv.html").read_text(encoding="utf-8")


def _kind_im_browser(client, fake_llm, app_env):
    """Eingerichtet, adaptiver Weg an, Kind-Modus — bereit zum Posten."""
    from .conftest import csrf_from
    from .test_app import einrichten, kind_modus_aktivieren
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True, learner_grade=6)
    kind_modus_aktivieren(client)
    return csrf_from(client.get("/lernen/adaptiv").text)


def _template_zweige() -> set:
    return set(re.findall(r"(?:if|elif) schirm\.art == '([a-z_]+)'", VORLAGE))


def _formen_pro_art() -> dict:
    """{art: [aktionspfade]} — gezaehlt auf Template-Zweige, mit
    Verschachtelungstiefe, damit innere {% if %}-Bloecke den Zweig
    nicht fruehzeitig schliessen."""
    tags = re.compile(
        r"{%\s*(if\b[^%]*|elif schirm\.art == '([a-z_]+)'|else|endif)\s*%}")
    formen, tiefe, art, pos = {}, 0, None, 0
    for m in tags.finditer(VORLAGE):
        zwischen = VORLAGE[pos:m.start()]
        pos = m.end()
        if art:
            formen.setdefault(art, []).extend(
                re.findall(r"learning_base \}\}/([a-z_/]+)\?", zwischen))
        tok = m.group(1)
        if tok.startswith("if"):
            tiefe += 1
            t = re.search(r"schirm\.art == '([a-z_]+)'", tok)
            if tiefe == 1 and t:
                art = t.group(1)
        elif tok.startswith("elif"):
            if tiefe == 1:
                art = m.group(2)
        elif tok == "else":
            if tiefe == 1:
                art = "<unbekannt>"
        elif tok == "endif":
            tiefe -= 1
            if tiefe == 0:
                art = None
    return formen


def test_jede_domain_bildschirm_art_hat_einen_template_zweig(app_env):
    """Was die Domain zeigen will, sieht das Kind wirklich — nie Erfolg
    als Fallback fuer einen Zustand, der keiner ist."""
    from app.adaptiv import sitzung as zustand, store, unterricht
    from app.adaptiv import voraussetzung as vor
    app_env.db.init()
    store.init()
    konzept_id = store.konzepte_verfuegbar()[0]["id"]
    fehlertyp_id = store.fehlertypen(konzept_id)[0]["id"]
    # Ein reales Ziel fuer den Detour-Marker.
    wartend = unterricht.starte(konzept_id, "Brüche")

    def sitzung(**kw):
        return {"id": 0, "konzept_id": konzept_id, "fehlertyp_id": fehlertyp_id,
                "erklaerung_id": None, "eingabe_id": wartend["eingabe_id"],
                "letzte_antwort": None, **kw}

    varianten = [
        {},                                        # Standard-Screens je Phase
        {"schritt": "aufgabe"},                    # Diagnose-Frage
        {"zweite_diagnose": "2/3 + 1/6 = ?"},      # Kontrollfrage
        {"vorhergesagt": "kleiner"},               # Haken mit Widerspruch
        {"gerechnet": True},                       # Transfer
        {"war_selbststaendig": True},
        {"voraussetzung_offen": "X", "voraussetzung_lokal": None,
         "voraussetzung_titel": "Grundlage"},
        {"voraussetzung_offen": "X", "voraussetzung_lokal": konzept_id,
         "voraussetzung_titel": "Grundlage"},
        {"voraussetzung_offen": "X", "voraussetzung_lokal": konzept_id,
         "voraussetzung_titel": "Grundlage", "voraussetzung_lernen": True},
        {"voraussetzung_detour": wartend["id"]},
    ]
    arten = {}
    for z in zustand.ZUSTAENDE:
        for phase in list(zustand.PHASEN) + [None]:
            for daten in varianten:
                schirm = unterricht._bildschirm(
                    sitzung(zustand=z, phase=phase, daten=daten))
                arten.setdefault(schirm["art"], (z, phase, sorted(daten)))

    # Die Grundlage sitzt -> dieselbe Lernen-Variante zeigt "zurueck".
    for f in store.fehlertypen(konzept_id):
        store.fortschritt_buchen(konzept_id, f["id"], mastery="sicher")
    schirm = unterricht._bildschirm(sitzung(
        zustand=zustand.DIAGNOSING, phase=None,
        daten={"voraussetzung_offen": "X", "voraussetzung_lokal": konzept_id,
               "voraussetzung_titel": "Grundlage", "voraussetzung_lernen": True}))
    arten.setdefault(schirm["art"], None)

    # „geschafft" gehoert zu MASTERED mit gewaehltem oder gesichertem
    # Termin — nie mehr zu einem offenen Zustand.
    from app.adaptiv import wiederholung
    wiederholung.planen(konzept_id, 3)
    schirm = unterricht._bildschirm(sitzung(zustand=zustand.MASTERED,
                                          phase=None, daten={}))
    arten.setdefault(schirm["art"], None)

    zweige = _template_zweige()
    # "unbekannt" ist das Sentinel der Domain fuer nicht vorgesehene
    # Kombinationen — es faellt absichtlich in den ehrlichen else-Zweig.
    fehlend = {a: wo for a, wo in arten.items()
               if a not in zweige and a != "unbekannt"}
    assert not fehlend, (
        f"Bildschirm-Arten ohne Template-Zweig (faellen in den "
        f"Generik-Zweig): {sorted(fehlend)}")
    # Die Pflicht-Arten des Kreislaufs muessen die Domain auch erzeugen.
    for pflicht in ("anker", "diagnose", "vorhersage", "haken", "regel",
                    "beispiel", "aufgabe", "transfer", "anders",
                    "wiederholung_waehlen", "geschafft", "eskaliert",
                    "voraussetzung", "voraussetzung_lernen",
                    "voraussetzung_zurueck", "voraussetzung_geschafft"):
        assert pflicht in arten, f"unerreichbare Art: {pflicht}"


def test_jedes_formular_findet_eine_passende_route(app_env):
    """Formular-Aktion <-> Bildschirm: was der Zweig anbietet, nimmt der
    Router fuer genau diesen Bildschirm auch an (kein stale-POST-Fund)."""
    app_env.db.init()
    from app.routers import adaptiv
    formen = _formen_pro_art()
    for art, pfade in formen.items():
        for pfad in pfade:
            aktion = pfad.replace("/", "_")
            if aktion == "neu":
                continue       # eigener Endpunkt, prueft selbst Endzustaende
            assert aktion in adaptiv.ERWARTETE_BILDSCHIRME, \
                f"{art} postet /{pfad} — keine Aktion '{aktion}' im Router"
            assert art in adaptiv.ERWARTETE_BILDSCHIRME[aktion], \
                f"/{pfad} gehoert nicht zum Bildschirm '{art}'"


# --------------------------------------------------------------------------
# Regressionen: veraltete Formulare duerfen der neuen Aufgabe nicht schaden
# --------------------------------------------------------------------------

def test_veraltete_aufgaben_antwort_kostet_keine_runde(
        client, fake_llm, app_env):
    """Doppelklick, zweiter Tab oder Browser-Zurueck: die alte Antwort gehoert
    zur alten Aufgabe und darf die neue nicht als falsch markieren."""
    from app.adaptiv import sitzung as zustand, inhalt_store, store, unterricht
    app_env.db.init()
    store.init()
    token = _kind_im_browser(client, fake_llm, app_env)
    konzept_id = store.konzepte_verfuegbar()[0]["id"]
    client.post("/lernen/adaptiv/start",
                data={"_csrf": token, "thema": "brueche"})

    s = zustand.laufende()
    s = unterricht.anker_beantwortet(s, "x")
    s = unterricht.diagnose_beantwortet(s, "2/5")
    s = unterricht.vorhersage_beantwortet(s, "groesser")
    for _ in range(3):
        s = unterricht.weiter(s)
    assert s["phase"] == zustand.GUIDED_TASK

    loesung = inhalt_store.aufgabe(
        s["fehlertyp_id"], inhalt_store.GEFUEHRT)["loesung"]
    seite = client.get("/lernen/adaptiv")
    kennung = re.search(r'name="kennung" value="([^"]*)"', seite.text).group(1)

    client.post("/lernen/adaptiv/aufgabe",
                data={"_csrf": token, "antwort": loesung, "kennung": kennung})
    s = store.sitzung(s["id"])
    assert s["phase"] == zustand.INDEPENDENT_TASK

    # Dasselbe Formular ein zweites Mal — jetzt gilt die Antwort der
    # naechsten Aufgabe nicht mehr.
    client.post("/lernen/adaptiv/aufgabe",
                data={"_csrf": token, "antwort": loesung, "kennung": kennung})
    s = store.sitzung(s["id"])
    assert s["phase"] == zustand.INDEPENDENT_TASK
    assert s["runden"] == 0


def test_veraltete_diagnose_antwort_trifft_kein_neues_ziel(
        client, fake_llm, app_env):
    """Die erste Diagnose-Frage ist beantwortet — ihr altes Formular darf
    die Kontrollfrage nicht als falsch werten (kein unbekanntes Hochzaehlen)."""
    from app.adaptiv import sitzung as zustand, store, unterricht
    app_env.db.init()
    store.init()
    token = _kind_im_browser(client, fake_llm, app_env)
    konzept_id = store.konzepte_verfuegbar()[0]["id"]
    erste, _bestaetigung = unterricht._diagnose_aufgaben(konzept_id)

    client.post("/lernen/adaptiv/start",
                data={"_csrf": token, "thema": "brueche"})
    client.post("/lernen/adaptiv/anker",
                data={"_csrf": token, "antwort": "x"})
    seite = client.get("/lernen/adaptiv")
    kennung = re.search(r'name="kennung" value="([^"]*)"', seite.text).group(1)

    client.post("/lernen/adaptiv/diagnose",
                data={"_csrf": token, "antwort": erste["loesung"],
                      "kennung": kennung})
    s = zustand.laufende()
    daten = s["daten"] if isinstance(s["daten"], dict) else json.loads(s["daten"])
    assert daten.get("zweite_diagnose")          # Kontrollfrage ist dran

    # Der alte Tab schickt die erste Antwort noch einmal.
    client.post("/lernen/adaptiv/diagnose",
                data={"_csrf": token, "antwort": erste["loesung"],
                      "kennung": kennung})
    s = zustand.laufende()
    daten = s["daten"] if isinstance(s["daten"], dict) else json.loads(s["daten"])
    assert s["zustand"] == "DIAGNOSING"
    assert not daten.get("unbekannte_antworten") # nicht als falsch gezaehlt


def test_doppeltes_weiter_ueberspringt_keine_phase(
        client, fake_llm, app_env):
    """Zwei Weiter-POSTs vom selben Bildschirm duerfen nicht zwei Phasen
    weitergehen — sonst verschluckt ein Doppelklick das Beispiel."""
    from app.adaptiv import sitzung as zustand, store, unterricht
    app_env.db.init()
    store.init()
    token = _kind_im_browser(client, fake_llm, app_env)
    client.post("/lernen/adaptiv/start",
                data={"_csrf": token, "thema": "brueche"})
    s = zustand.laufende()
    s = unterricht.anker_beantwortet(s, "x")
    s = unterricht.diagnose_beantwortet(s, "2/5")
    s = unterricht.vorhersage_beantwortet(s, "groesser")
    assert s["phase"] == zustand.HOOK

    seite = client.get("/lernen/adaptiv")
    kennung = re.search(r'name="kennung" value="([^"]*)"', seite.text).group(1)
    client.post("/lernen/adaptiv/weiter",
                data={"_csrf": token, "kennung": kennung})
    client.post("/lernen/adaptiv/weiter",
                data={"_csrf": token, "kennung": kennung})
    s = store.sitzung(s["id"])
    assert s["phase"] == zustand.RULE       # einmal weiter, nicht zweimal


def test_fehlende_aufgabe_wird_kein_leeres_formular(
        client, fake_llm, app_env, monkeypatch):
    """Gibt der Katalog die Aufgabe nicht her, ist ein Formular ohne
    Antwortmoeglichkeit ein Dead End — die ehrliche Seite tritt an."""
    from app.adaptiv import sitzung as zustand, inhalt_store, store, unterricht
    app_env.db.init()
    store.init()
    token = _kind_im_browser(client, fake_llm, app_env)
    client.post("/lernen/adaptiv/start",
                data={"_csrf": token, "thema": "brueche"})

    s = zustand.laufende()
    s = unterricht.anker_beantwortet(s, "x")
    s = unterricht.diagnose_beantwortet(s, "2/5")
    s = unterricht.vorhersage_beantwortet(s, "groesser")
    for _ in range(3):
        s = unterricht.weiter(s)
    assert s["phase"] == zustand.GUIDED_TASK

    monkeypatch.setattr(inhalt_store, "aufgabe", lambda *a, **k: None)
    seite = client.get("/lernen/adaptiv")
    assert "weiß Karo gerade nicht weiter" in seite.text
    assert "Gut gemacht" not in seite.text
    assert 'name="antwort"' not in seite.text


def test_termin_formular_ignoriert_eine_geschaffte_wiederholung(
        client, fake_llm, app_env):
    """/wiederholung/{wid}/termin gehoert zur Auffrischung — ein alter Tab
    plant einer bestandenen Wiederholung sonst eine neue nach."""
    from app.adaptiv import store, wiederholung
    app_env.db.init()
    store.init()
    token = _kind_im_browser(client, fake_llm, app_env)
    konzept_id = store.konzepte_verfuegbar()[0]["id"]

    eintrag = wiederholung.planen(konzept_id, 2)
    wiederholung.abschliessen(eintrag["id"], bestanden_=True)
    vorher = app_env.db.q1(
        "SELECT COUNT(*) AS n FROM lern_wiederholung")["n"]

    client.post(f"/lernen/adaptiv/wiederholung/{eintrag['id']}/termin",
                data={"_csrf": token, "tage": "3"})
    nachher = app_env.db.q1(
        "SELECT COUNT(*) AS n FROM lern_wiederholung")["n"]
    assert nachher == vorher
    assert wiederholung.offen_fuer(konzept_id) is None


# --------------------------------------------------------------------------
# Runde statt Parkplatz: richtiger Transfer ohne genug Belege
# --------------------------------------------------------------------------

def _bis_zur_selbstaendigen_aufgabe(client, fake_llm, app_env,
                                    treffer=5, runden=3):
    """Bis zur ersten selbststaendigen Aufgabe — mit Schwellen, die das
    Verhalten nach dem Transfer sichtbar machen."""
    from app.adaptiv import sitzung as zustand, inhalt_store, store, unterricht
    app_env.db.init()
    store.init()
    app_env.config.update(adaptiv_mastery_treffer=treffer,
                          adaptiv_max_lehrrunden=runden)
    token = _kind_im_browser(client, fake_llm, app_env)
    client.post("/lernen/adaptiv/start",
                data={"_csrf": token, "thema": "brueche"})
    s = zustand.laufende()
    s = unterricht.anker_beantwortet(s, "x")
    s = unterricht.diagnose_beantwortet(s, "2/5")
    s = unterricht.vorhersage_beantwortet(s, "groesser")
    for _ in range(3):
        s = unterricht.weiter(s)
    loesung = inhalt_store.aufgabe(s["fehlertyp_id"],
                                   inhalt_store.GEFUEHRT)["loesung"]
    s = unterricht.aufgabe_beantwortet(s, loesung)
    assert s["phase"] == zustand.INDEPENDENT_TASK
    return s


def test_richtiger_transfer_ohne_beleg_startet_neue_runde(
        client, fake_llm, app_env):
    """Treffer=5: ein richtiger Transfer mit zu wenig Belegen gibt keine
    Pause auf COMPLETE, sondern eine neue Runde mit einer neuen Aufgabe —
    jede Runde eine andere, und „verstanden" erst bei MASTERED."""
    from app.adaptiv import sitzung as zustand, unterricht
    s = _bis_zur_selbstaendigen_aufgabe(client, fake_llm, app_env)

    gestellte, arten, mutmacher = [], [], []
    for _ in range(10):                     # Schutz gegen jeden Stillstand
        assert s["phase"] != zustand.COMPLETE          # kein Parkplatz
        schirm = unterricht.bildschirm(s)
        arten.append(schirm["art"])
        assert schirm["art"] == "aufgabe"
        assert schirm["phase"] == zustand.INDEPENDENT_TASK
        gestellte.append(schirm["aufgabe"]["frage"])
        mutmacher.append(schirm.get("aufmunterung"))
        s = unterricht.aufgabe_beantwortet(s, schirm["aufgabe"]["loesung"])
        schirm = unterricht.bildschirm(s)
        arten.append(schirm["art"])
        assert schirm["art"] == "transfer"   # richtige Uebung → Transfer
        s = unterricht.transfer_beantwortet(s, schirm["aufgabe"]["loesung"])
        if s["zustand"] == zustand.MASTERED:
            break
    assert s["zustand"] == zustand.MASTERED
    # Jede selbststaendige Runde stellt eine andere Aufgabe.
    assert len(gestellte) >= 2
    assert len(gestellte) == len(set(gestellte))
    # Erst die Extra-Runde verspricht „fast geschafft" — nie „verstanden".
    assert mutmacher[0] is None
    assert all(m == "Fast geschafft — eine neue Aufgabe wartet noch."
               for m in mutmacher[1:])
    assert "geschafft" not in arten


def test_rundengrenze_gilt_auch_in_extra_runden(
        client, fake_llm, app_env):
    """Die Extra-Runde ist keine Endlosschleife: jede falsche Antwort zaehlt
    eine Runde — bei adaptiv_max_lehrrunden eskaliert Karo wie immer."""
    from app.adaptiv import sitzung as zustand, inhalt_store, unterricht
    s = _bis_zur_selbstaendigen_aufgabe(client, fake_llm, app_env,
                                        treffer=5, runden=2)
    selbst = inhalt_store.aufgabe(s["fehlertyp_id"],
                                  inhalt_store.SELBSTSTAENDIG)
    s = unterricht.aufgabe_beantwortet(s, selbst["loesung"])
    transfer = inhalt_store.aufgabe(s["fehlertyp_id"], inhalt_store.TRANSFER)
    s = unterricht.transfer_beantwortet(s, transfer["loesung"])
    assert s["zustand"] == zustand.TEACHING
    assert s["phase"] == zustand.INDEPENDENT_TASK      # Extra-Runde

    # Nenner > 60 kommt als Generator-Ergebnis nicht vor — sicher falsch.
    s = unterricht.aufgabe_beantwortet(s, "123/456")   # falsch — Runde 1
    assert s["phase"] == zustand.ADAPTATION
    s = unterricht.weiter_nach_adaptation(s)
    s = unterricht.aufgabe_beantwortet(s, "123/456")   # falsch — Runde 2
    assert s["zustand"] == zustand.ESCALATED


def test_geparkte_alt_sitzung_bekommt_ihre_runde(
        client, fake_llm, app_env):
    """Eine Sitzung auf COMPLETE aus der Parkplatz-Zeit: offen, unfertig und
    auf „verstanden" geparkt. Der naechste Bildschirm repariert sie — das
    Konzept bleibt neu startbar und spielbar bis MASTERED."""
    from app.adaptiv import sitzung as zustand, store, unterricht
    s = _bis_zur_selbstaendigen_aufgabe(client, fake_llm, app_env)
    store.sitzung_aktualisieren(s["id"], phase=zustand.COMPLETE,
                              daten={"gerechnet": True})

    seite = client.get("/lernen/adaptiv")
    # „verstanden und sicher gelöst" ist der Abschlusstext — hier gelogen.
    assert "sicher gelöst" not in seite.text
    assert "Gut gemacht" not in seite.text
    assert "Fast geschafft" in seite.text

    s = store.sitzung(s["id"])
    assert s["phase"] == zustand.INDEPENDENT_TASK
    # Und sie spielt sich normal zu Ende — bis MASTERED.
    schirm = unterricht.bildschirm(s)
    assert schirm["art"] == "aufgabe"
    for _ in range(6):
        s = unterricht.aufgabe_beantwortet(s, schirm["aufgabe"]["loesung"])
        s = unterricht.transfer_beantwortet(
            s, unterricht.bildschirm(s)["aufgabe"]["loesung"])
        if s["zustand"] == zustand.MASTERED:
            break
        schirm = unterricht.bildschirm(s)
    assert s["zustand"] == zustand.MASTERED
    # Das Konzept sperrt sich nicht: keine offene Sitzung bleibt haengen.
    assert zustand.laufende() is None


def test_kein_offener_zustand_zeigt_geschafft(
        client, fake_llm, app_env):
    """„verstanden" gibt es erst bei MASTERED: ueber alle offenen
    Zustand/Phase-Kombinationen hinweg erzeugt `bildschirm` nie den
    Abschluss-Bildschirm — die COMPLETE-Reparatur eingeschlossen."""
    from app.adaptiv import sitzung as zustand, store, unterricht
    app_env.db.init()
    store.init()
    _kind_im_browser(client, fake_llm, app_env)
    konzept_id = store.konzepte_verfuegbar()[0]["id"]
    fehlertyp_id = store.fehlertypen(konzept_id)[0]["id"]
    s = unterricht.starte(konzept_id, "Brüche")
    store.sitzung_aktualisieren(s["id"], zustand=zustand.TEACHING,
                                fehlertyp_id=fehlertyp_id)

    for phase in list(zustand.PHASEN) + [None]:
        store.sitzung_aktualisieren(s["id"], phase=phase, daten={})
        schirm = unterricht.bildschirm(store.sitzung(s["id"]))
        assert schirm["art"] != "geschafft", phase

    for z in zustand.ZUSTAENDE:
        store.sitzung_aktualisieren(s["id"], zustand=z, phase=None, daten={})
        schirm = unterricht.bildschirm(store.sitzung(s["id"]))
        if z not in zustand.ENDZUSTAENDE:
            assert schirm["art"] != "geschafft", z
