"""Deutsch, Mathematik und Englisch sind strikt getrennt.

Jede Prüfung hier sichert eine Stelle, an der Inhalte zwischen den Fächern
wandern könnten: Anlegen, Listen, Suche, Wissensbasis, Lektionen, Curriculum,
Schulblätter, Klassenarbeiten und der Elternordner.
"""
import pytest

from .conftest import csrf_from, make_jpeg, run_jobs
from .test_app import einrichten, kind_modus_aktivieren


# --------------------------------------------------------------------------
# Das Fach-Modul
# --------------------------------------------------------------------------

def test_nur_drei_faecher_und_ihre_schreibweisen():
    from app import faecher
    assert faecher.FAECHER == ("deutsch", "mathematik", "englisch")
    for wert, key in (("Mathe", "mathematik"), ("Mathematik", "mathematik"),
                      ("English", "englisch"), ("Englisch", "englisch"),
                      ("deutsch", "deutsch"), ("German", "deutsch")):
        assert faecher.schluessel(wert) == key
    for fremd in ("Biologie", "", None, "Physik", "Französisch"):
        assert faecher.schluessel(fremd) is None
        with pytest.raises(faecher.FachFehler):
            faecher.pflicht(fremd)


@pytest.mark.parametrize("text,fach", [
    ("Brüche addieren", "mathematik"), ("Prozentrechnung", "mathematik"),
    ("present perfect", "englisch"), ("irregular verbs", "englisch"),
    ("Kommasetzung", "deutsch"), ("Gedichte analysieren", "deutsch"),
    ("Photosynthese", "andere"),
])
def test_erkennung_ohne_modell(app_env, text, fach):
    from app import faecher
    app_env.db.init()
    assert faecher.erkenne(text) == fach


def test_mehrdeutiges_bleibt_offen(app_env):
    from app import faecher
    app_env.db.init()
    # „Zeitformen“ gibt es in Deutsch und Englisch: keine Entscheidung ohne Modell.
    assert faecher.erkenne("Zeitformen") is None


# --------------------------------------------------------------------------
# SUBJECT_MISMATCH: nichts wird im falschen Fach gespeichert
# --------------------------------------------------------------------------

def test_fachfremdes_thema_wird_nicht_gespeichert(client, fake_llm, fake_cli, app_env):
    from app import faecher
    from app.services import learning_hub
    einrichten(client, fake_llm)
    with pytest.raises(faecher.SubjectMismatch) as fehler:
        learning_hub.create_topic("present perfect", "mathematik", 7)
    assert fehler.value.code == faecher.SUBJECT_MISMATCH == "SUBJECT_MISMATCH"
    assert fehler.value.erkannt == "englisch"
    assert app_env.db.q("SELECT id FROM topic WHERE label='present perfect'") == []
    # Im richtigen Fach geht es.
    assert learning_hub.create_topic("present perfect", "englisch", 7)


def test_das_modell_entscheidet_wenn_stichworte_schweigen(client, fake_llm, fake_cli, app_env):
    from app import faecher
    from app.services import learning_hub
    einrichten(client, fake_llm)
    fake_llm.responses["fach"] = {"fach": "englisch"}
    with pytest.raises(faecher.SubjectMismatch):
        learning_hub.create_topic("Zeitformen", "deutsch", 7)
    assert app_env.db.q("SELECT id FROM topic WHERE label='Zeitformen'") == []
    fake_llm.responses["fach"] = {"fach": "deutsch"}
    assert learning_hub.create_topic("Zeitformen", "deutsch", 7)


def test_das_kind_erfaehrt_wohin_ein_thema_gehoert(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    kind_modus_aktivieren(client)
    seite = client.get("/lernen/neu?fach=mathematik")
    antwort = client.post("/lernen/neu", data={
        "_csrf": csrf_from(seite.text), "thema": "irregular verbs",
        "fach": "mathematik", "klasse": "7"})
    assert "Das gehört zu Englisch, nicht zu Mathematik" in antwort.text
    assert "Wechsle oben zum Fach Englisch" in antwort.text
    assert app_env.db.q("SELECT id FROM topic WHERE label='irregular verbs'") == []


def test_ohne_fach_wird_nichts_angelegt(client, fake_llm, fake_cli, app_env):
    from app import faecher
    from app.services import learning_hub
    einrichten(client, fake_llm)
    for fach in ("", "Biologie"):
        with pytest.raises(faecher.FachFehler):
            learning_hub.create_topic("Brüche addieren", fach, 7)
    assert app_env.db.q("SELECT id FROM topic") == []


# --------------------------------------------------------------------------
# Listen und Suche sehen nur das aktive Fach
# --------------------------------------------------------------------------

def _drei_themen():
    from app.services import learning_hub
    return {fach: learning_hub.create_topic(label, fach, 7) for fach, label in (
        ("deutsch", "Kommasetzung"), ("mathematik", "Brüche addieren"),
        ("englisch", "present perfect"))}


def test_reiter_zeigen_nur_ihr_fach(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    _drei_themen()
    kind_modus_aktivieren(client)
    erwartet = {"deutsch": "Kommasetzung", "mathematik": "Brüche addieren",
                "englisch": "present perfect"}
    for fach, eigenes in erwartet.items():
        seite = client.get(f"/lernen/{fach}").text
        assert eigenes in seite
        for anderes in set(erwartet.values()) - {eigenes}:
            assert anderes not in seite, (fach, anderes)


def test_suche_findet_nichts_aus_anderen_faechern(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    _drei_themen()
    assert "Brüche addieren" in client.get("/lernen/mathematik?q=Brüche").text
    englisch = client.get("/lernen/englisch?q=Brüche").text
    assert "Brüche addieren" not in englisch
    assert "0 Themen gefunden" in englisch


def test_lernen_oeffnet_das_zuletzt_gewaehlte_fach(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    client.get("/lernen/englisch")
    assert client.get("/lernen", follow_redirects=False).headers["location"] == "/lernen/englisch"


def test_wissensbasis_sucht_nur_auf_blaettern_des_fachs(client, fake_llm, fake_cli, app_env):
    from app import kb
    einrichten(client, fake_llm)
    with app_env.db.tx() as c:
        for fach, text in (("mathematik", "Brüche werden gleichnamig gemacht"),
                           ("englisch", "Brüche is the German word for fractions")):
            doc = c.execute("""INSERT INTO document(sha256,source_name,stored_path,mime,rolle,
                                   state,subject,created_at)
                               VALUES(?,?,?,'image/jpeg','wissen','erschlossen',?,?)""",
                            (fach, fach, "/tmp/x.jpg", fach, app_env.db.now())).lastrowid
            c.execute("""INSERT INTO kb_chunk(document_id,position,art,text,created_at)
                         VALUES(?,1,'regel',?,?)""", (doc, text, app_env.db.now()))
    mathe = kb.suche("Brüche", "mathematik")
    englisch = kb.suche("Brüche", "englisch")
    assert [t["text"] for t in mathe] == ["Brüche werden gleichnamig gemacht"]
    assert [t["text"] for t in englisch] == ["Brüche is the German word for fractions"]
    assert kb.suche("Brüche", "deutsch") == []
    assert kb.suche("Brüche", "") == []


def test_lektionen_nur_im_eigenen_fach(app_env):
    from app.adaptiv import lektionen
    app_env.db.init()
    assert lektionen.fuer_thema("Brüche addieren", "mathematik") is not None
    for fach in ("deutsch", "englisch", None, "Biologie"):
        assert lektionen.fuer_thema("Brüche addieren", fach) is None
        assert lektionen.empfehlungen("Brüche kürzen", fach) == []
    assert lektionen.verfuegbar("englisch") == []
    assert {l["fach"] for l in lektionen.verfuegbar("mathematik")} == {"mathematik"}


def test_curriculum_agent_bekommt_nur_das_aktive_fach(app_env, monkeypatch):
    from app import jobs
    from app.adaptiv import curriculum_dienst as bridge
    app_env.db.init()
    gesendet = []

    def anfrage(cfg, method, path, body=None):
        if path == "/v1/meta":     # Versionsabgleich vor jedem Auftrag
            return {"contract_version": bridge.CONTRACT_VERSION, "git_sha": "test", "formats": []}
        gesendet.append(body)
        return {"status": "pending", "export_id": 3}
    monkeypatch.setattr(bridge, "request", anfrage)
    with pytest.raises(jobs.Deferred):
        bridge.prepare(app_env.config.load(), {}, "present perfect", "Englisch", 7)
    assert gesendet[0]["subject"] == "englisch"
    with pytest.raises(Exception):
        bridge.prepare(app_env.config.load(), {}, "present perfect", "", 7)


def test_curriculum_antwort_aus_anderem_fach_wird_verworfen(app_env):
    from app.adaptiv import curriculum_dienst as bridge, schemas
    app_env.db.init()
    with pytest.raises(schemas.InhaltUngueltig, match="anderen Fach"):
        bridge._checked({"subject": "mathematik"}, "present perfect", 7, "englisch")


def test_lektion_erzeugen_nur_mit_fach(app_env):
    from app import faecher
    from app.adaptiv import erzeugung
    app_env.db.init()
    with pytest.raises(faecher.FachFehler):
        erzeugung.anfordern("present perfect", "")
    with pytest.raises(faecher.FachFehler):
        erzeugung.speichern({}, "Biologie")


# --------------------------------------------------------------------------
# Schulblätter je Fach
# --------------------------------------------------------------------------

def _blatt(client, tmp_path, fach, name):
    seite = client.get(f"/wissen?fach={fach}")
    jpeg = make_jpeg(tmp_path / f"{name}.jpg")
    return client.post("/wissen/upload", data={
        "_csrf": csrf_from(seite.text), "themenname": name, "fach": fach,
    }, files={"datei": (f"{name}.jpg", jpeg.read_bytes() + name.encode(), "image/jpeg")})


def test_upload_setzt_das_fach_und_liste_zeigt_nur_dieses(client, fake_llm, fake_cli, app_env, tmp_path):
    einrichten(client, fake_llm)
    _blatt(client, tmp_path, "englisch", "Vocabulary Unit 3")
    _blatt(client, tmp_path, "deutsch", "Kommasetzung")
    faecher = {r["themenname"]: r["subject"] for r in app_env.db.q("SELECT * FROM document")}
    assert faecher == {"Vocabulary Unit 3": "englisch", "Kommasetzung": "deutsch"}
    englisch = client.get("/wissen?fach=englisch").text
    assert "Vocabulary Unit 3" in englisch and "Kommasetzung" not in englisch
    deutsch = client.get("/wissen?fach=deutsch").text
    assert "Kommasetzung" in deutsch and "Vocabulary Unit 3" not in deutsch
    assert "Vocabulary" not in client.get("/wissen?fach=mathematik").text


def test_blatt_upload_ohne_fach_oder_mit_falschem_namen(client, fake_llm, fake_cli, app_env, tmp_path):
    einrichten(client, fake_llm)
    seite = client.get("/wissen?fach=mathematik")
    jpeg = make_jpeg(tmp_path / "x.jpg")
    ohne = client.post("/wissen/upload", data={"_csrf": csrf_from(seite.text), "themenname": "Brüche"},
                       files={"datei": ("x.jpg", jpeg.read_bytes(), "image/jpeg")})
    assert "Bitte zuerst ein Fach wählen" in ohne.text
    falsch = _blatt(client, tmp_path, "mathematik", "present perfect")
    assert "Das gehört zu Englisch" in falsch.text
    assert app_env.db.q("SELECT id FROM document") == []


def test_fachfremdes_blatt_wird_nicht_erschlossen(client, fake_llm, fake_cli, app_env, tmp_path):
    from .test_app import KB
    einrichten(client, fake_llm)
    fake_llm.responses["kb"] = {**KB, "fach": "englisch"}
    _blatt(client, tmp_path, "mathematik", "Arbeitsblatt")
    run_jobs(app_env, fake_llm)
    doc = app_env.db.q1("SELECT * FROM document")
    assert doc["state"] == "fach_falsch" and "SUBJECT_MISMATCH" in doc["note"]
    assert app_env.db.q("SELECT id FROM kb_chunk") == []
    assert "falsches Fach" in client.get("/wissen?fach=mathematik").text


def test_themenvorschlaege_bleiben_im_fach_des_blatts(client, fake_llm, fake_cli, app_env, tmp_path):
    from .test_app import TOPICS
    einrichten(client, fake_llm)
    fake_llm.responses["topics"] = {"themen": [
        *TOPICS["themen"],
        {"code": "EN.PP", "label": "present perfect", "beschreibung": "", "fach": "englisch"}]}
    _blatt(client, tmp_path, "mathematik", "Bruchrechnung")
    run_jobs(app_env, fake_llm)
    themen = {r["label"]: r["subject"] for r in app_env.db.q("SELECT label, subject FROM topic")}
    assert "present perfect" not in themen
    assert themen and set(themen.values()) == {"mathematik"}


# --------------------------------------------------------------------------
# Klassenarbeiten und Heute: fachübergreifend, Fach sichtbar
# --------------------------------------------------------------------------

def test_klassenarbeit_mit_fachfremdem_thema_wird_abgelehnt(client, fake_llm, fake_cli, app_env):
    from app.services import exam
    einrichten(client, fake_llm)
    with pytest.raises(exam.ExamError, match="gehören nicht zu Mathematik: present perfect"):
        exam.create_exam("2099-01-01", manual_topics="Brüche addieren\npresent perfect",
                         subject="mathematik")
    assert app_env.db.q("SELECT id FROM exam") == []
    with pytest.raises(exam.ExamError, match="Fach der Klassenarbeit"):
        exam.create_exam("2099-01-01", manual_topics="Brüche addieren", subject="Biologie")


def test_pruefungen_und_heute_zeigen_das_fach(client, fake_llm, fake_cli, app_env):
    from app.services import exam
    einrichten(client, fake_llm)
    app_env.config.update(klassenarbeit_kind=True)
    exam.create_exam("2099-01-01", manual_topics="Kommasetzung", subject="deutsch")
    exam.create_exam("2099-02-01", manual_topics="present perfect", subject="englisch")
    kind_modus_aktivieren(client)
    uebersicht = client.get("/klassenarbeit").text
    assert "Deutsch" in uebersicht and "Englisch" in uebersicht
    heute = client.get("/").text
    assert "Deutsch-Arbeit" in heute


# --------------------------------------------------------------------------
# Elternordner „Ohne Fach“
# --------------------------------------------------------------------------

def test_inhalte_ohne_gueltiges_fach_sieht_nur_der_elternordner(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    with app_env.db.tx() as c:
        tid = c.execute("""INSERT INTO topic(subject,code,label,state,created_at,learning_visible,grade)
                           VALUES('Biologie','ALT.BIO','Zellen','aktiv',?,1,7)""",
                        (app_env.db.now(),)).lastrowid
        eid = c.execute("""INSERT INTO exam(subject,exam_date,themen,created_at)
                           VALUES('Biologie','2099-03-01','[]',?)""", (app_env.db.now(),)).lastrowid
    app_env.config.update(klassenarbeit_kind=True)
    eltern = client.get("/eltern").text
    assert "2 Inhalte ohne gültiges Fach" in eltern and 'href="/eltern/ohne-fach"' in eltern
    ordner = client.get("/eltern/ohne-fach").text
    assert "Zellen" in ordner and "bisher: Biologie" in ordner

    kind_modus_aktivieren(client)
    for fach in ("deutsch", "mathematik", "englisch"):
        assert "Zellen" not in client.get(f"/lernen/{fach}").text
    assert client.get(f"/klassenarbeit/{eid}").status_code in (403, 404)
    assert client.get("/eltern/ohne-fach", follow_redirects=False).status_code == 403


def test_eltern_ordnen_ein_fach_zu(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    with app_env.db.tx() as c:
        tid = c.execute("""INSERT INTO topic(subject,code,label,state,created_at,learning_visible,grade)
                           VALUES('Sachkunde','ALT.X','Gedichte vortragen','aktiv',?,1,7)""",
                        (app_env.db.now(),)).lastrowid
    seite = client.get("/eltern/ohne-fach")
    client.post("/eltern/ohne-fach/zuordnen", data={
        "_csrf": csrf_from(seite.text), "art": "thema", "eintrag_id": tid, "fach": "deutsch"})
    assert app_env.db.q1("SELECT subject FROM topic WHERE id=?", tid)["subject"] == "deutsch"
    assert "Gedichte vortragen" in client.get("/lernen/deutsch").text
    assert "ohne gültiges Fach" not in client.get("/eltern").text


def test_alte_fachnamen_werden_beim_start_vereinheitlicht(app_env):
    app_env.db.init()
    with app_env.db.tx() as c:
        c.execute("""INSERT INTO topic(subject,code,label,state,created_at)
                     VALUES('Mathe','ALT.M','Dreisatz','aktiv',?)""", (app_env.db.now(),))
        c.execute("""INSERT INTO topic(subject,code,label,state,created_at)
                     VALUES('Biologie','ALT.B','Zellen','aktiv',?)""", (app_env.db.now(),))
    app_env.db.init()
    faecher = {r["label"]: r["subject"] for r in app_env.db.q("SELECT label, subject FROM topic")}
    # Eindeutiges wird zugeordnet, Fremdes bleibt unverändert im Elternordner.
    assert faecher == {"Dreisatz": "mathematik", "Zellen": "Biologie"}


def test_das_kind_sieht_die_meldung_bei_der_klassenarbeit(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)
    app_env.config.update(klassenarbeit_kind=True)
    kind_modus_aktivieren(client)
    seite = client.get("/klassenarbeit/neu")
    antwort = client.post("/klassenarbeit", data={
        "_csrf": csrf_from(seite.text), "exam_date": "2099-01-01", "fach": "mathematik",
        "themen": "Brüche addieren\nirregular verbs"})
    assert "Diese Themen gehören nicht zu Mathematik: irregular verbs" in antwort.text
    # Die Eingaben bleiben stehen, damit das Kind nur korrigieren muss.
    assert "Brüche addieren" in antwort.text
    assert app_env.db.q("SELECT id FROM exam") == []
