"""Tests für „Meine Woche" — den Begleiter.

Geprüft wird nicht nur, dass die Wege funktionieren, sondern vor allem die
Zusagen, die das Konzept dem Kind macht. Ein Test, der nur Statuscodes zählt,
würde die eigentlichen Fehlerklassen dieses Moduls übersehen:

  * irgendwo taucht doch ein „nicht erledigt" auf,
  * die Verkleinerung läuft ohne Untergrenze weiter,
  * die Eltern sehen mehr, als ihnen zusteht,
  * ein Lob erscheint, für das es kein Ereignis gibt,
  * der Begleiter fasst eine Karo-Tabelle an.
"""

from __future__ import annotations

import sqlite3

import pytest

from .conftest import csrf_from
from .test_app import ALLE, TOKEN, einrichten


# --------------------------------------------------------------------------
# Helfer
# --------------------------------------------------------------------------

def anmelden(client, fake):
    passwort = einrichten(client, fake, backend="abo")
    seite = client.get("/login")
    client.post("/login", data={"_csrf": csrf_from(seite.text),
                                "password": passwort})
    return passwort


def csrf(client, pfad="/woche/einrichtung"):
    return csrf_from(client.get(pfad).text)


def woche_einrichten(client, faecher=("Mathematik", "Englisch"),
                     wort="Jellycats", form="einfach", helfer="Mama"):
    t = csrf(client)
    r = client.post("/woche/einrichtung/faecher",
                    data={"_csrf": t, "klasse": "7", "fach": list(faecher)})
    assert r.status_code in (200, 303)
    client.post("/woche/einrichtung/ding",
                data={"_csrf": t, "wort": wort, "form": form})
    client.post("/woche/einrichtung/helfer",
                data={"_csrf": t, "name": helfer, "fester_tag": "2",
                      "feste_zeit": "18:00", "fertig": "1"})


def zyklus_starten(client, fokus="Mathearbeit"):
    t = csrf(client, "/woche/plan")
    r = client.post("/woche/start", data={"_csrf": t, "fokus": fokus},
                    follow_redirects=False)
    assert r.status_code == 303
    return r


def ersten_schritt_id(app_env):
    zeile = app_env.db.q1("SELECT id FROM woche_schritt ORDER BY id LIMIT 1")
    assert zeile is not None, "kein Schritt angelegt"
    return zeile["id"]


@pytest.fixture
def woche(client, fake_llm, fake_cli):
    fake_llm.responses = dict(ALLE)
    anmelden(client, fake_llm)
    woche_einrichten(client)
    return client


# --------------------------------------------------------------------------
# Einrichtung
# --------------------------------------------------------------------------

def test_ohne_anmeldung_kein_zugang(client):
    r = client.get("/woche", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] in ("/setup", "/login")


def test_einrichtung_in_drei_schritten(client, fake_llm, fake_cli, app_env):
    anmelden(client, fake_llm)
    r = client.get("/woche", follow_redirects=False)
    assert r.headers["location"] == "/woche/einrichtung"

    woche_einrichten(client)

    assert len(app_env.db.q("SELECT * FROM woche_fach WHERE aktiv=1")) == 2
    assert app_env.db.q1("SELECT * FROM woche_ding WHERE aktiv=1")["wort"] == "Jellycats"
    assert app_env.db.q1("SELECT * FROM woche_helfer")["name"] == "Mama"
    assert app_env.db.q1("SELECT * FROM woche_kind")["eingerichtet_am"]


def test_ding_wartet_auf_freigabe_blockiert_aber_nichts(woche, app_env):
    """Bis die Eltern bestätigen, sagt die App die Form statt des Wortes."""
    from app.woche import store

    d = store.ding()
    assert d["freigabe"] == "offen"
    assert store.wort_oder_form(d) == "Einfach"      # die Form, nicht das Wort

    seite = woche.get("/woche/plan")
    assert seite.status_code == 200          # nichts ist blockiert

    store.ding_freigeben(d["id"], True)
    assert store.wort_oder_form(store.ding()) == "Jellycats"


# --------------------------------------------------------------------------
# Der Kernweg
# --------------------------------------------------------------------------

def test_fokus_trifft_das_fach_trotz_wortstamm(woche, app_env):
    """„Mathearbeit" muss Mathematik treffen — ein reines `in` tut das nicht."""
    from app.woche import regeln, store

    assert regeln.passt_zum_fokus("Mathematik", "Mathearbeit")
    assert regeln.passt_zum_fokus("Englisch", "englisch vokabeltest")
    assert not regeln.passt_zum_fokus("Biologie", "Mathearbeit")

    zyklus_starten(woche, "Mathearbeit")
    erster = app_env.db.q1(
        "SELECT s.*, f.name AS fach FROM woche_schritt s "
        "JOIN woche_fach f ON f.id=s.fach_id ORDER BY s.id LIMIT 1")
    assert erster["fach"] == "Mathematik"
    assert erster["anlass"] == "arbeit_nah"


def test_zyklus_legt_angebot_an(woche, app_env):
    zyklus_starten(woche)
    schritte = app_env.db.q("SELECT * FROM woche_schritt")
    assert 1 <= len(schritte) <= 3
    for s in schritte:
        assert s["einstieg"], "jeder Schritt braucht eine Einstiegshandlung"


def test_einstieg_und_nein_ist_ein_vollwertiger_abschluss(woche, app_env):
    zyklus_starten(woche)
    sid = ersten_schritt_id(app_env)
    t = csrf(woche, "/woche")

    r = woche.post(f"/woche/schritt/{sid}/einstieg",
                   data={"_csrf": t, "wert": "gemacht"}, follow_redirects=False)
    assert r.headers["location"] == f"/woche/schritt/{sid}/weiter"

    r = woche.post(f"/woche/schritt/{sid}/weiter",
                   data={"_csrf": t, "wert": "nein"}, follow_redirects=False)
    assert r.headers["location"] == "/woche"

    seite = woche.get("/woche")
    assert "Du hast angefangen" in seite.text

    arten = [z["art"] for z in app_env.db.q("SELECT art FROM woche_ereignis")]
    assert "einstieg" in arten and "weiter" in arten


def test_gut_und_okay_loesen_keine_rueckfrage_aus(woche, app_env):
    zyklus_starten(woche)
    sid = ersten_schritt_id(app_env)
    t = csrf(woche, "/woche")
    r = woche.post(f"/woche/schritt/{sid}/rueckmeldung",
                   data={"_csrf": t, "wert": "okay"}, follow_redirects=False)
    assert r.headers["location"] == "/woche"


def test_schwierig_fuehrt_zu_genau_einer_frage(woche, app_env):
    zyklus_starten(woche)
    sid = ersten_schritt_id(app_env)
    t = csrf(woche, "/woche")

    r = woche.post(f"/woche/schritt/{sid}/rueckmeldung",
                   data={"_csrf": t, "wert": "schwierig"}, follow_redirects=False)
    assert r.headers["location"] == f"/woche/schritt/{sid}/grund"

    seite = woche.get(f"/woche/schritt/{sid}/grund")
    assert "zu schwer" in seite.text and "keine Zeit" in seite.text


# --------------------------------------------------------------------------
# Die Zusagen des Konzepts
# --------------------------------------------------------------------------

def test_verkleinern_hat_eine_untergrenze(woche, app_env):
    """Höchstens zweimal kleiner, danach Strategiewechsel statt Schrumpfen."""
    from app.woche import regeln, store

    zyklus_starten(woche)
    sid = ersten_schritt_id(app_env)
    t = csrf(woche, "/woche")

    for _ in range(3):
        woche.post(f"/woche/schritt/{sid}/anpassung",
                   data={"_csrf": t, "art": "kleiner", "wert": "annehmen"})

    s = store.schritt(sid)
    assert s["verkleinert"] <= regeln.VERKLEINERN_MAX
    assert regeln.anpassen(s, "zu_schwer")["art"] == "strategie"


def test_nirgends_steht_nicht_erledigt(woche, app_env):
    """Kein „offen", keine Quote — weder beim Kind noch bei den Eltern."""
    zyklus_starten(woche)
    from app.woche import store
    for nr in (1, 2, 3):
        store.zusage_setzen(nr)

    verboten = ["nicht erledigt", "nicht geschafft", "offen:", "erledigt von",
                "0 %", "Quote", "Rückstand"]
    for pfad in ("/woche", "/woche/plan", "/woche/ueber-dich", "/woche/eltern",
                 "/woche/hilfe", "/woche/stundenplan"):
        text = woche.get(pfad).text
        # Der Aufklapptext „Wie entsteht das?" und die Beruhigung auf dem
        # Heute-Bildschirm benennen genau das, was NICHT gezeigt wird. Geprüft
        # wird die Anzeige selbst, nicht die Erklärung darüber.
        text = _ohne(text, "<details", "</details>")
        text = _ohne(text, '<p class="leise">Das ist kein', "</p>")
        for wort in verboten:
            assert wort not in text, f"{wort!r} steht auf {pfad}"


def _ohne(text: str, von: str, bis: str) -> str:
    while von in text:
        a = text.index(von)
        e = text.index(bis, a) + len(bis) if bis in text[a:] else len(text)
        text = text[:a] + text[e:]
    return text


def test_rueckblick_lobt_nur_mit_ereignis(woche, app_env):
    """Ohne Ereignis kein Lob — ein Kind erkennt unverdientes Lob sofort."""
    from app.woche import regeln, store

    zyklus_starten(woche)
    z = store.zyklus()
    assert regeln.rueckblick(z["id"]) == []

    sid = ersten_schritt_id(app_env)
    t = csrf(woche, "/woche")
    for _ in range(2):
        woche.post(f"/woche/schritt/{sid}/einstieg",
                   data={"_csrf": t, "wert": "gemacht"})

    saetze = regeln.rueckblick(z["id"])
    assert any("angefangen" in s for s in saetze)
    assert all("toll" not in s.lower() for s in saetze)


def test_eltern_sehen_die_gruende_nicht(woche, app_env):
    from app.woche import store

    zyklus_starten(woche)
    sid = ersten_schritt_id(app_env)
    t = csrf(woche, "/woche")
    woche.post(f"/woche/schritt/{sid}/rueckmeldung",
               data={"_csrf": t, "wert": "schwierig"})
    woche.post(f"/woche/schritt/{sid}/grund",
               data={"_csrf": t, "wert": "keine_lust"})
    for nr in (1, 2, 3):
        store.zusage_setzen(nr)

    text = woche.get("/woche/eltern").text
    assert "keine Lust" not in text
    assert "schwierig" not in text


def test_eltern_muessen_erst_zusagen(woche):
    seite = woche.get("/woche/eltern")
    assert "Ich frage nicht nach" in seite.text
    assert "Der Plan läuft" not in seite.text


def test_hilferuf_setzt_den_elternzustand(woche, app_env):
    from app.woche import regeln, store

    zyklus_starten(woche)
    t = csrf(woche, "/woche/hilfe")
    h = store.helfer()[0]
    woche.post("/woche/hilfe", data={"_csrf": t, "helfer_id": str(h["id"]),
                                     "frage": "Bruchrechnen"})
    assert regeln.eltern_zustand()["key"] == "gefragt"


def test_pause_ist_eine_funktion_und_umkehrbar(woche, app_env):
    from app.woche import regeln, store

    t = csrf(woche, "/woche")
    woche.post("/woche/pause", data={"_csrf": t, "wochen": "1"})
    assert store.pause_aktiv() is not None
    assert regeln.eltern_zustand()["key"] == "pause"
    assert "Pause" in woche.get("/woche").text

    woche.post("/woche/pause/ende", data={"_csrf": t})
    assert store.pause_aktiv() is None


def test_notfall_ist_ehrlich_und_kennt_die_schlafgrenze(woche):
    from app.woche import regeln

    frueh = regeln.notfall("Mathematik", 20, stunde=19)
    assert frueh["schlaf"] is False
    assert "nicht mehr komplett" in frueh["text"]
    assert frueh["schritt"]["titel"]

    spaet = regeln.notfall("Mathematik", 20, stunde=22)
    assert spaet["schlaf"] is True
    assert spaet["schritt"] is None


def test_weglassen_ist_eine_entscheidung(woche, app_env):
    from app.woche import store

    f = store.faecher()[0]
    t = csrf(woche, "/woche/plan")
    woche.post("/woche/weglassen", data={"_csrf": t, "fach_id": str(f["id"])})
    zeile = app_env.db.q1("SELECT * FROM woche_ereignis WHERE art='weglassen'")
    assert zeile["wert"] == f["name"]


def test_wissen_ist_sichtbar_und_loeschbar(woche, app_env):
    from app.woche import regeln

    regeln.wissen_sagen("ort", "🍳", "Du lernst am liebsten in der Küche.")
    seite = woche.get("/woche/ueber-dich")
    assert "in der Küche" in seite.text

    zid = app_env.db.q1("SELECT id FROM woche_wissen WHERE schluessel='ort'")["id"]
    t = csrf_from(seite.text)
    woche.post(f"/woche/wissen/{zid}/aus", data={"_csrf": t})
    assert "in der Küche" not in woche.get("/woche/ueber-dich").text


def test_kind_wissen_wird_nicht_ueberschrieben(woche):
    """Was das Kind korrigiert hat, gewinnt gegen jeden Zähler."""
    from app.woche import regeln

    regeln.wissen_sagen("ding", "🧸", "Mein Ding ist geheim.")
    regeln.wissen_neu_berechnen()
    zeilen = {z["schluessel"]: z["text"] for z in regeln.wissen_zeilen()}
    assert zeilen["ding"] == "Mein Ding ist geheim."


# --------------------------------------------------------------------------
# Unabhängigkeit von Karo
# --------------------------------------------------------------------------

def test_ereignisse_sind_append_only(woche, app_env):
    from app.woche import store

    store.ereignis("einstieg", "gemacht")
    with pytest.raises(sqlite3.IntegrityError if False else Exception):
        with app_env.db.tx() as c:
            c.execute("UPDATE woche_ereignis SET wert='nicht'")
    with pytest.raises(Exception):
        with app_env.db.tx() as c:
            c.execute("DELETE FROM woche_ereignis")


def test_begleiter_fasst_keine_karo_tabelle_an(woche, app_env):
    """Der Begleiter läuft neben Karo, nicht in Karo."""
    zyklus_starten(woche)
    sid = ersten_schritt_id(app_env)
    t = csrf(woche, "/woche")
    woche.post(f"/woche/schritt/{sid}/einstieg", data={"_csrf": t, "wert": "gemacht"})

    for tabelle in ("topic", "quiz", "answer_log", "lesson", "document",
                    "kb_chunk"):
        n = app_env.db.q1(f"SELECT COUNT(*) AS n FROM {tabelle}")["n"]
        assert n == 0, f"{tabelle} wurde vom Begleiter berührt"


def test_quelltext_importiert_keine_karo_lernlogik():
    """Statische Zusicherung: kein Import aus Karos Lernteil."""
    from pathlib import Path

    import app.woche as paket

    verboten = ("topics", "quizzes", "teaching", "kb", "llm", "research",
                "pipeline", "exam_plan", "ingest", "prompts")
    ordner = Path(paket.__file__).parent
    for datei in ordner.glob("*.py"):
        text = datei.read_text(encoding="utf-8")
        for name in verboten:
            assert f"from ..{name}" not in text, f"{datei.name} importiert {name}"
            assert f"from .. import {name}" not in text, f"{datei.name}: {name}"


def test_nur_die_bruecke_kennt_karo_tabellen():
    """Karo-Tabellen dürfen ausschließlich in bruecke.py vorkommen.

    Das ist die Zusicherung, die die Trennung trotz Integration hält: wer
    anderswo `topic` oder `lesson` abfragt, bricht sie auf."""
    from pathlib import Path

    import app.woche as paket

    karo_tabellen = ("FROM topic", "FROM lesson", "FROM exam", "FROM document",
                     "FROM kb_chunk", "FROM answer_log", "JOIN topic",
                     "JOIN lesson")
    ordner = Path(paket.__file__).parent
    for datei in ordner.glob("*.py"):
        if datei.name == "bruecke.py":
            continue
        text = datei.read_text(encoding="utf-8")
        for name in karo_tabellen:
            assert name not in text, f"{datei.name} liest {name}"


# --------------------------------------------------------------------------
# Die Brücke zu Karo
# --------------------------------------------------------------------------

def test_bruecke_ist_standardmaessig_aus(woche):
    from app.woche import bruecke, store

    assert store.kind()["karo_bruecke"] == 0
    assert bruecke.aktiv("Mathematik") is False
    assert bruecke.luecken("Mathematik") == []
    assert bruecke.naechste_arbeit("Mathematik") is None
    assert bruecke.titelzusatz("Mathematik") == ""


def test_bruecke_liest_luecke_und_termin(woche, app_env):
    """Eingeschaltet macht sie den Schritt konkret — und nur dann."""
    from app.woche import bruecke, regeln, store

    heute = app_env.db.today()
    with app_env.db.tx() as c:
        c.execute("INSERT INTO topic (id, subject, code, label, state, created_at) "
                  "VALUES (1,'Mathematik','BR.ADD','Brüche addieren','aktiv',?)",
                  (heute,))
        c.execute("INSERT INTO topic_flag (topic_id, flag, computed_at) "
                  "VALUES (1,'rot',?)", (heute,))
        c.execute("INSERT INTO exam (subject, exam_date, titel, themen, created_at) "
                  "VALUES ('Mathematik', date('now','+3 day'), 'Mathearbeit', "
                  "'[\"Brüche\"]', ?)", (heute,))

    # Aus: nichts davon wirkt.
    assert bruecke.titelzusatz("Mathematik") == ""

    store.kind_setzen(karo_bruecke=1)
    assert bruecke.titelzusatz("Mathematik") == "Brüche addieren"
    assert bruecke.anlass("Mathematik") == "arbeit_nah"
    assert "3 Tagen" in bruecke.hinweis("Mathematik")

    # Und im Angebot steht jetzt der Name der Lücke.
    zyklus_starten(woche, "Mathearbeit")
    titel = [s["titel"] for s in store.schritte(store.zyklus()["id"])]
    assert any("Brüche addieren" in t for t in titel), titel


def test_bruecke_gilt_nur_fuer_karos_fach(woche, app_env):
    """Karo deckt ein Fach ab. Für alle anderen bleibt der Begleiter allein."""
    from app.woche import bruecke, store

    store.kind_setzen(karo_bruecke=1)
    assert bruecke.zustaendig("Mathematik") is True      # config.subject
    assert bruecke.zustaendig("Englisch") is False
    assert bruecke.luecken("Englisch") == []


def test_bruecke_schreibt_nie_in_karo(woche, app_env):
    from app.woche import bruecke, regeln, store

    store.kind_setzen(karo_bruecke=1)
    zyklus_starten(woche, "Mathearbeit")
    regeln.notfall("Mathematik", 20, stunde=18)
    bruecke.luecken("Mathematik")
    bruecke.ankervorschlag("Mathematik")

    for tabelle in ("topic", "topic_flag", "quiz", "answer_log", "lesson",
                    "document"):
        n = app_env.db.q1(f"SELECT COUNT(*) AS n FROM {tabelle}")["n"]
        assert n == 0, f"{tabelle} wurde beschrieben"


def test_bruecke_ueberlebt_leeres_karo(woche):
    """Kein Thema, keine Arbeit, kein Blatt — der Begleiter läuft weiter."""
    from app.woche import store

    store.kind_setzen(karo_bruecke=1)
    zyklus_starten(woche)
    for pfad in ("/woche", "/woche/plan", "/woche/eltern", "/woche/notfall"):
        assert woche.get(pfad).status_code == 200, pfad


def test_alle_bildschirme_rendern(woche, app_env):
    """Jede Seite einmal aufrufen — Templatefehler fallen sonst erst live auf."""
    zyklus_starten(woche)
    sid = ersten_schritt_id(app_env)
    seiten = [
        "/woche", "/woche/plan", "/woche/hilfe", "/woche/ueber-dich",
        "/woche/stundenplan", "/woche/eltern", "/woche/einrichtung",
        "/woche/notfall", "/woche/abschluss",
        f"/woche/schritt/{sid}/weiter",
        f"/woche/schritt/{sid}/form",
        f"/woche/schritt/{sid}/rueckmeldung",
        f"/woche/schritt/{sid}/grund",
        f"/woche/schritt/{sid}/anpassung?grund=zu_schwer",
        f"/woche/schritt/{sid}/karte",
    ]
    for pfad in seiten:
        r = woche.get(pfad)
        assert r.status_code == 200, f"{pfad}: {r.status_code}"
        assert "<main" in r.text, pfad


def test_notfall_zeigt_genau_eine_sache(woche, app_env):
    from app.woche import store

    f = store.faecher()[0]
    t = csrf(woche, "/woche/notfall")
    r = woche.post("/woche/notfall", data={"_csrf": t, "fach_id": str(f["id"]),
                                           "was": "arbeit", "minuten": "20"})
    assert r.status_code == 200
    assert "zeig mir das Wichtigste" not in r.text      # Ergebnis, nicht Formular


def test_jede_form_hat_eine_seite(woche, app_env):
    from app.woche import store

    for form in ("speedrun", "clip", "einfach"):
        store.ding_setzen("Test", form)
        zyklus_starten(woche, "Mathearbeit")
        sid = app_env.db.q1("SELECT id FROM woche_schritt ORDER BY id DESC")["id"]
        r = woche.get(f"/woche/schritt/{sid}/form")
        assert r.status_code == 200, form
        assert f'data-form="{form}"' in r.text


def test_karo_laeuft_unveraendert_weiter(woche):
    """Die Hauptanwendung darf von dem Modul nichts merken."""
    for pfad in ("/", "/themen", "/wissen", "/lernstand"):
        assert woche.get(pfad).status_code == 200
