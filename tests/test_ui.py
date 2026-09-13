"""Navigation and form contracts for the simplified, complete learning flow."""
from html.parser import HTMLParser

from .conftest import csrf_from, make_jpeg, run_jobs
from .test_app import einrichten, blatt_einlesen, themen_freigeben


class Forms(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.forms = []
        self.current = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            assert self.current is None, "Nested form"
            self.current = {"action": attrs.get("action"), "fields": {}, "buttons": []}
            self.forms.append(self.current)
        elif self.current is not None and attrs.get("name"):
            if tag == "button":
                self.current["buttons"].append(attrs)
            elif tag == "input" and attrs.get("type") != "radio":
                self.current["fields"][attrs["name"]] = attrs.get("value", "")
            elif tag == "input" and "checked" in attrs:
                self.current["fields"][attrs["name"]] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.current = None


def test_new_navigation_and_empty_pages(client, fake_llm, fake_cli):
    einrichten(client, fake_llm)
    for path in ("/", "/lernen", "/lernzyklus", "/eltern", "/wissen", "/themen",
                 "/recherche", "/lernstand", "/klassenarbeit", "/protokoll", "/setup"):
        response = client.get(path)
        assert response.status_code == 200, path
        Forms(response.text)
        for label in ("Heute", "Lernen", "Erfolge", "Für Eltern"):
            assert label in response.text
    assert "Erstes Blatt hinzufügen" in client.get("/").text
    client.cookies.clear()
    assert client.get("/eltern", follow_redirects=False).status_code == 303


def test_help_keeps_full_documentation_without_tabs(client, fake_llm, fake_cli):
    einrichten(client, fake_llm)
    page = client.get('/hilfe')
    assert page.status_code == 200
    assert 'class="tab-btn"' not in page.text
    for section in ('ablauf', 'bereiche', 'flaggen', 'datenschutz', 'einstellungen'):
        assert f'id="hilfe-{section}"' in page.text
    assert 'So geht Karo' in page.text
    assert 'Karo verwendet zuerst das Material' in page.text


def test_upload_proposals_and_manual_topic_use_rendered_fields(client, fake_llm, fake_cli, app_env, tmp_path):
    einrichten(client, fake_llm)
    image = make_jpeg(tmp_path / "schule.jpg")
    page = client.get("/wissen")
    form = next(f for f in Forms(page.text).forms if f["action"].endswith("/upload"))
    response = client.post(form["action"], data={**form["fields"], "themenname": "Bruchrechnung"},
                           files={"datei": ("schule.jpg", image.read_bytes(), "image/jpeg")})
    assert response.status_code == 200
    run_jobs(app_env, fake_llm)
    doc = app_env.db.q1("SELECT * FROM document")
    assert doc["state"] == "erschlossen"
    assert client.get(f"/wissen/{doc['id']}").status_code == 200
    assert client.get(f"/scan/{doc['id']}.jpg").headers["content-type"] == "image/jpeg"
    page = client.get("/themen")
    form = next(f for f in Forms(page.text).forms if f["action"].endswith("/entscheiden"))
    action = next(key for key in form["fields"] if key.startswith("aktion_"))
    client.post(form["action"], data={"_csrf": form["fields"]["_csrf"], action: "aktiv"})
    assert app_env.db.q1("SELECT COUNT(*) n FROM topic WHERE state='aktiv'")["n"] == 1
    form = next(f for f in Forms(page.text).forms if f["action"].endswith("/neu"))
    client.post(form["action"], data={**form["fields"], "label": "Dezimalzahlen"})
    assert app_env.db.q1("SELECT id FROM topic WHERE label='Dezimalzahlen'")


def test_topic_and_lesson_ids_are_not_interchangeable(client, fake_llm, fake_cli, app_env):
    from app import teaching, topics
    einrichten(client, fake_llm)
    topics.anlegen("Ein anderes Thema")
    topic_id = topics.anlegen("Unser Thema")
    lesson_id = teaching.starten(topic_id)
    assert lesson_id != topic_id
    page = client.get(f"/lernzyklus/{topic_id}")
    assert page.status_code == 200
    assert "Unser Thema" in page.text
    assert f'action="/lernen/{lesson_id}/runde/weiter"' in page.text
    token = csrf_from(page.text)
    response = client.post(f"/lernzyklus/{topic_id}/abbrechen", data={"_csrf": token})
    assert response.status_code == 200
    assert teaching.holen(lesson_id)["state"] == "abgebrochen"


def test_learning_quiz_keeps_lesson_association_and_review_gate(client, fake_llm, fake_cli, app_env):
    from app import quizzes, teaching
    einrichten(client, fake_llm)
    blatt_einlesen(client, fake_llm, app_env)
    topic_id = themen_freigeben(client, app_env)[0]
    lesson_id = teaching.starten(topic_id)
    teaching.naechste_runde_bestaetigen(lesson_id)
    run_jobs(app_env, fake_llm)
    page = client.get(f"/lernzyklus/{topic_id}")
    assert page.status_code == 200
    Forms(page.text)
    before = len(app_env.db.q("SELECT id FROM quiz"))
    client.post(f"/lernzyklus/{topic_id}/quiz/starten", data={"_csrf": csrf_from(page.text)})
    run_jobs(app_env, fake_llm)
    assert len(app_env.db.q("SELECT id FROM quiz")) > before
    quiz = app_env.db.q1("SELECT * FROM quiz WHERE lesson_id=?", lesson_id)
    assert quiz["anlass"] == "lernrunde"
    assert quiz["round_nr"] == 1
    page = client.get(f"/lernzyklus/{topic_id}/quiz/{quiz['id']}")
    assert 'data-answer-form' in page.text
    assert 'simple-main focus-view' in page.text
    answers = {f"antwort_{f['id']}": "1/2" for f in quizzes.holen(quiz["id"])["fragen"]}
    client.post(f"/quiz/{quiz['id']}/antworten", data={"_csrf": csrf_from(page.text), **answers})
    run_jobs(app_env, fake_llm)
    page = client.get(f"/quiz/{quiz['id']}")
    review = next(f for f in Forms(page.text).forms if f["action"].endswith("/freigabe"))
    assert not any(key.startswith("urteil_") for key in review["fields"])
    assert 'data-review-form' in page.text
    assert 'simple-main focus-view' not in page.text
    client.post(review["action"], data={"_csrf": csrf_from(page.text)})
    assert app_env.db.q1("SELECT finished_at FROM quiz WHERE id=?", quiz["id"])["finished_at"] is None
    assert client.get(f"/lernzyklus/{topic_id + 999}/quiz/{quiz['id']}").status_code == 404
    # The saved human decision must replace the model's suggestion on revisits.
    questions = quizzes.holen(quiz['id'])['fragen']
    with app_env.db.tx() as c:
        c.execute('UPDATE question SET vorschlag_richtig=0 WHERE quiz_id=?', (quiz['id'],))
    result = client.post(review['action'], data={
        '_csrf': csrf_from(page.text), 'frage_id': [str(f['id']) for f in questions],
        **{f"urteil_{f['id']}": 'ja' for f in questions},
    })
    assert result.status_code == 200
    page = client.get(f"/quiz/{quiz['id']}")
    assert page.text.count('Bestätigte Bewertung: richtig') == len(questions)
    assert 'Vorschlag von Karo: falsch' not in page.text


def test_source_buttons_and_exam_fields_match_endpoints(client, fake_llm, fake_cli, app_env):
    from app import research
    einrichten(client, fake_llm)
    blatt_einlesen(client, fake_llm, app_env)
    topic_id = themen_freigeben(client, app_env)[0]
    research.anfordern(topic_id)
    run_jobs(app_env, fake_llm)
    page = client.get("/recherche")
    form = next(f for f in Forms(page.text).forms if f["action"].endswith("/entscheiden"))
    action = next(key for key in form["fields"] if key.startswith("hit_"))
    client.post(form["action"], data={"_csrf": form["fields"]["_csrf"], action: "freigegeben"})
    assert research.freigegebene(topic_id)
    # Exam creation still requires the reviewed topics from an uploaded scan.
    import json
    with app_env.db.tx() as c:
        scan_id = c.execute("INSERT INTO exam_scan(document_id, state, themen, created_at) VALUES (?, 'gelesen', ?, ?)",
                            (app_env.db.q1('SELECT id FROM document')[0], json.dumps(['Brüche']), app_env.db.now())).lastrowid
    page = client.get('/klassenarbeit')
    form = next(f for f in Forms(page.text).forms if f['action'] == '/klassenarbeit')
    response = client.post(form['action'], data={**form['fields'], 'exam_date': '2099-01-01', 'scan_id': str(scan_id)})
    assert response.status_code == 200
    assert app_env.db.q1('SELECT exam_date FROM exam')['exam_date'] == '2099-01-01'


def test_only_three_main_links_and_parent_features_remain(client, fake_llm, fake_cli):
    import re
    einrichten(client, fake_llm)
    page = client.get('/')
    nav = re.search(r'<nav class="simple-nav".*?</nav>', page.text, re.S).group()
    assert nav.count('<a ') == 3
    assert 'verbindung-popup-slot' not in page.text
    parent = client.get('/eltern').text
    for path in ('/wissen', '/themen', '/klassenarbeit', '/lernstand#ausfuehrlich', '/recherche', '/setup', '/protokoll', '/hilfe'):
        assert f'href="{path}"' in parent
    for path in ('/', '/lernen', '/lernstand', '/klassenarbeit', '/themen', '/wissen', '/recherche', '/hilfe'):
        assert 'class="tab-btn"' not in client.get(path).text


def test_topic_start_immediately_builds_existing_material(client, fake_llm, fake_cli, app_env):
    from app import teaching
    einrichten(client, fake_llm)
    blatt_einlesen(client, fake_llm, app_env)
    topic_id = themen_freigeben(client, app_env)[0]
    page = client.get(f'/lernzyklus/{topic_id}')
    response = client.post(f'/lernzyklus/{topic_id}/start', data={'_csrf': csrf_from(page.text), 'ausgabe': 'html'}, follow_redirects=False)
    lesson_id = int(response.headers['location'].rsplit('/', 1)[-1])
    assert teaching.holen(lesson_id)['state'] == 'material'
    run_jobs(app_env, fake_llm)
    page = client.get(f'/lernen/{lesson_id}')
    assert '<iframe' in page.text
    assert f'action="/lernen/{lesson_id}/fragen"' in page.text
    assert f'action="/lernen/{lesson_id}/abbrechen"' in page.text
    assert '/variante"' in page.text
    assert 'class="tab-btn"' not in page.text
    Forms(page.text)


def test_home_prefers_child_ready_work_to_parent_review(client, fake_llm, fake_cli, app_env):
    from app import quizzes
    einrichten(client, fake_llm)
    blatt_einlesen(client, fake_llm, app_env)
    topic_id = themen_freigeben(client, app_env)[0]
    first = quizzes.anfordern(topic_id)
    run_jobs(app_env, fake_llm)
    with app_env.db.tx() as c:
        # 'ausgewertet' ist der echte Zustand, den job_quiz_check nach der
        # LLM-Auswertung setzt — eine Fragerunde, die auf die Freigabe der
        # Lernbegleitung wartet (siehe quizzes.py, STATE_AUSGEWERTET).
        c.execute("UPDATE quiz SET state=? WHERE id=?",
                 (quizzes.STATE_AUSGEWERTET, first))
    second = quizzes.anfordern(topic_id)
    run_jobs(app_env, fake_llm)
    page = client.get('/')
    assert f'href="/quiz/{second}"' in page.text
    assert f'href="/quiz/{first}"' not in page.text
    assert f'href="/quiz/{first}"' in client.get('/eltern').text
