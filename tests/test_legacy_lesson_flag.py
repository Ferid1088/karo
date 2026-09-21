"""Der alte Erzeugungsweg (`/lernzyklus` → teaching.py → media/) ist
standardmäßig unerreichbar.

Er wird nicht gelöscht — nur abgeschaltet, nach demselben Muster wie
`adaptive_learning_enabled` (01_ARCHITECTURE.md §16). Solange der echte
diagnostische Loop getestet wird, darf keine Themenkarte versehentlich in
die Video-Erzeugung führen.

Was bewusst *nicht* am Schalter hängt: die Fragerunden, der „gelernt"-Haken
und die Übersicht. Die gehören dem Lernstand, nicht dem Generator.
"""
from .conftest import csrf_from
from .test_app import einrichten, kind_modus_aktivieren


def test_schalter_ist_standardmaessig_aus(client, fake_llm, fake_cli, app_env):
    einrichten(client, fake_llm)

    assert app_env.config.load().legacy_lesson_generation_enabled is False


def _kind_mit_thema(client, fake_llm, app_env, label="Brüche vergleichen"):
    """Ein aktives Thema im Kindbereich — der Ausgangspunkt der Themenkarte."""
    from app import topics
    einrichten(client, fake_llm)
    topic_id = topics.anlegen(label)
    kind_modus_aktivieren(client)
    return topic_id


def test_themenseite_fuehrt_nicht_mehr_in_den_generator(client, fake_llm,
                                                        fake_cli, app_env):
    """Der Bildschirm mit der Format-Auswahl ist nicht mehr erreichbar."""
    topic_id = _kind_mit_thema(client, fake_llm, app_env)

    r = client.get(f"/lernzyklus/{topic_id}", follow_redirects=False)

    assert r.status_code == 303
    assert r.headers["location"] == "/lernen"


def test_erzeugen_legt_keine_lerneinheit_an(client, fake_llm, fake_cli, app_env):
    """Der Knopf „Lerninhalte erstellen" erzeugt nichts mehr — auch nicht,
    wenn jemand die Adresse von Hand aufruft."""
    topic_id = _kind_mit_thema(client, fake_llm, app_env)
    token = csrf_from(client.get("/lernen").text)

    r = client.post(f"/lernzyklus/{topic_id}/start",
                    data={"_csrf": token, "ausgabe": "html"},
                    follow_redirects=False)

    assert r.status_code == 303
    assert r.headers["location"] == "/lernen"
    assert not app_env.db.q("SELECT id FROM lesson")
    assert not app_env.db.q("SELECT id FROM job")


def test_alle_runden_routen_sind_zu(client, fake_llm, fake_cli, app_env):
    """Auch die Folgeschritte einer laufenden Runde — sonst bliebe der Weg
    über eine alte Lesezeichen-Adresse offen."""
    topic_id = _kind_mit_thema(client, fake_llm, app_env)
    token = csrf_from(client.get("/lernen").text)

    for weg in ("runde/weiter", "forschen", "abbrechen"):
        r = client.post(f"/lernzyklus/{topic_id}/{weg}", data={"_csrf": token},
                        follow_redirects=False)
        assert r.status_code == 303, weg
        assert r.headers["location"] == "/lernen", weg

    r = client.get(f"/lernzyklus/{topic_id}/material/1",
                   follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/lernen"


def test_die_elterntuer_in_den_generator_ist_zu(client, fake_llm, fake_cli,
                                                app_env):
    """`/themen/{id}/lernen` ruft dasselbe `teaching.starten()` auf. Eltern
    kommen dort hin, Kinder nicht — der Schalter gilt für beide."""
    from app import topics
    einrichten(client, fake_llm)
    topic_id = topics.anlegen("Brüche vergleichen")
    token = csrf_from(client.get("/themen").text)

    r = client.post(f"/themen/{topic_id}/lernen", data={"_csrf": token},
                    follow_redirects=False)

    assert r.status_code == 303
    assert r.headers["location"] == "/lernen"
    assert not app_env.db.q("SELECT id FROM lesson")


def test_lernseite_und_material_sind_zu(client, fake_llm, fake_cli, app_env):
    """Die Seite der alten Lernrunde und ihre erzeugten Dateien — sonst wäre
    der Generator nur versteckt, nicht abgeschaltet."""
    _kind_mit_thema(client, fake_llm, app_env)

    for pfad in ("/lernen/1", "/lernen/1/status", "/material/1",
                 "/material/variante/1"):
        r = client.get(pfad, follow_redirects=False)
        assert r.status_code == 303, pfad
        assert r.headers["location"] == "/lernen", pfad


def test_themenkarte_zeigt_keinen_weg_in_den_generator(client, fake_llm,
                                                       fake_cli, app_env):
    """Eine tote Schaltfläche ist schlimmer als keine: die Karte darf den
    alten Weg gar nicht erst anbieten."""
    topic_id = _kind_mit_thema(client, fake_llm, app_env)

    seite = client.get("/lernen?tab=neu").text

    assert "Brüche vergleichen" in seite          # Das Thema bleibt sichtbar.
    assert "Format der Lerninhalte" not in seite
    assert "Lerninhalte erstellen" not in seite
    assert f'action="/lernzyklus/{topic_id}/start"' not in seite
    assert f'action="/lernzyklus/{topic_id}/beginnen"' not in seite
    assert f'href="/lernzyklus/{topic_id}"' not in seite


def test_keine_toten_verweise_in_erfolgen_und_themenliste(client, fake_llm,
                                                          fake_cli, app_env):
    """`/lernstand` und die Elternliste verlinkten denselben Bildschirm."""
    from app import topics
    einrichten(client, fake_llm)
    topic_id = topics.anlegen("Brüche vergleichen")
    token = csrf_from(client.get("/lernen").text)
    client.post(f"/lernzyklus/{topic_id}/gelernt",
                data={"_csrf": token, "gelernt": "ja"})

    erfolge = client.get("/lernstand").text
    themen = client.get("/themen").text

    assert "Brüche vergleichen" in erfolge
    assert f'href="/lernzyklus/{topic_id}"' not in erfolge
    assert f'href="/lernzyklus/{topic_id}"' not in themen
    assert "Material ansehen" not in themen

    # Auch eine aus der Zeit vor dem Schalter uebrige Lerneinheit darf die
    # Elternliste nicht mehr dorthin verlinken.
    with app_env.db.tx() as c:
        c.execute("INSERT INTO lesson (topic_id, state, ausgabe, created_at) "
                  "VALUES (?, 'wartet', 'html', ?)", (topic_id, app_env.db.now()))
    themen = client.get("/themen").text
    assert "Lerneinheit öffnen" not in themen


def test_fragerunden_und_lernstand_bleiben_erreichbar(client, fake_llm,
                                                      fake_cli, app_env):
    """Der Schalter trennt den Generator ab, nicht den Lernstand: Prüfungen,
    der „gelernt"-Haken und die Übersichten hängen nicht daran."""
    from app import topics
    einrichten(client, fake_llm)
    topic_id = topics.anlegen("Brüche vergleichen")
    token = csrf_from(client.get("/themen").text)

    r = client.post(f"/themen/{topic_id}/pruefen",
                    data={"_csrf": token, "modus": "bildschirm"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/quiz/")
    quiz_id = int(r.headers["location"].rsplit("/", 1)[-1])
    assert client.get(f"/quiz/{quiz_id}").status_code == 200

    for pfad in ("/lernen", "/lernzyklus", "/lernstand", "/"):
        assert client.get(pfad).status_code == 200, pfad

    kind_modus_aktivieren(client)
    token = csrf_from(client.get("/lernen").text)
    assert client.post(f"/lernzyklus/{topic_id}/beginnen",
                       data={"_csrf": token}).status_code == 200
    assert client.post(f"/lernzyklus/{topic_id}/gelernt",
                       data={"_csrf": token, "gelernt": "ja"}).status_code == 200
    assert "Brüche vergleichen" in client.get("/lernstand").text


def test_mit_gesetztem_schalter_ist_der_alte_weg_unveraendert(
        client, fake_llm, fake_cli, app_env):
    """Nichts ist gelöscht: wer den Schalter setzt, bekommt den alten Weg
    zurück — Themenseite, Format-Auswahl und Erzeugung."""
    from app import teaching
    topic_id = _kind_mit_thema(client, fake_llm, app_env)
    app_env.config.update(legacy_lesson_generation_enabled=True)

    seite = client.get(f"/lernzyklus/{topic_id}")
    assert seite.status_code == 200
    assert "Brüche vergleichen" in seite.text
    karte = client.get("/lernen?tab=neu").text
    assert f'action="/lernzyklus/{topic_id}/beginnen"' in karte
    assert "Thema anfangen" in karte

    # Die Erzeugung selbst bleibt hinter der Themenprüfung — aber sie ist
    # wieder erreichbar, statt am Schalter abzuprallen.
    token = csrf_from(seite.text)
    r = client.post(f"/lernzyklus/{topic_id}/start", data={"_csrf": token})
    assert "Bitte zuerst die Themenprüfung abschließen" in r.text

    with app_env.db.tx() as c:
        c.execute("INSERT INTO quiz (topic_id, anlass, state, created_at) "
                  "VALUES (?, 'evaluation', 'freigegeben', ?)",
                  (topic_id, app_env.db.now()))
    r = client.post(f"/lernzyklus/{topic_id}/start",
                    data={"_csrf": token, "ausgabe": "html"},
                    follow_redirects=False)
    lesson_id = int(r.headers["location"].rsplit("/", 1)[-1])
    assert teaching.holen(lesson_id)["topic_id"] == topic_id


def test_klassenarbeit_erzeugt_kein_material_mehr(client, fake_llm, fake_cli,
                                                  app_env):
    """Der Lerntag der Klassenarbeit ruft dasselbe `teaching.starten()`.

    Bliebe er offen, liefe der Generator weiter — nur wäre sein Ergebnis
    unter `/material/...` nicht mehr abrufbar. Halb abgeschaltet ist
    schlechter als ganz.
    """
    from .test_app import _bis_rot
    from .test_exam_material import plan_anlegen

    topic_id = _bis_rot(client, fake_llm, app_env)
    exam_id, tage = plan_anlegen(app_env, topic_id)
    vorher = len(app_env.db.q("SELECT id FROM lesson"))
    token = csrf_from(client.get("/klassenarbeit").text)

    r = client.post(f"/klassenarbeit/{exam_id}/lerntag",
                    data={"_csrf": token, "row_key": tage[0]["row_key"],
                          "ausgabe": "html"},
                    follow_redirects=False)

    assert r.status_code == 303
    assert r.headers["location"] == "/lernen"
    assert len(app_env.db.q("SELECT id FROM lesson")) == vorher
    assert not app_env.db.q("SELECT id FROM exam_material")


def test_lernplan_zeigt_keine_format_auswahl_mehr(client, fake_llm, fake_cli,
                                                  app_env):
    """Dieselbe Format-Auswahl steht ein zweites Mal im Lernplan."""
    from .test_app import _bis_rot
    from .test_exam_material import plan_anlegen

    topic_id = _bis_rot(client, fake_llm, app_env)
    exam_id, _ = plan_anlegen(app_env, topic_id)

    seite = client.get("/klassenarbeit").text

    assert "Montag" in seite                      # Der Plan bleibt sichtbar.
    assert "Neues Lernmaterial erstellen" not in seite
    assert "NotebookLM-Video" not in seite
    assert f'action="/klassenarbeit/{exam_id}/lerntag"' not in seite
