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
    for path in ("/", "/lernzyklus", "/vorbereitung", "/vorbereitung/inhalte",
                 "/vorbereitung/inhalte/sources", "/messung", "/messung/fortschritt",
                 "/messung/examen", "/protokoll"):
        response = client.get(path)
        assert response.status_code == 200, path
        Forms(response.text)
        for label in ("Heute", "Lernen", "Material", "Fortschritt"):
            assert label in response.text
    assert "Erstes Blatt hinzufügen" in client.get("/").text
    client.cookies.clear()
    assert client.get("/ui/status", follow_redirects=False).status_code == 303


def test_upload_proposals_and_manual_topic_use_rendered_fields(client, fake_llm, fake_cli, app_env, tmp_path):
    einrichten(client, fake_llm)
    image = make_jpeg(tmp_path / "schule.jpg")
    page = client.get("/vorbereitung")
    form = next(f for f in Forms(page.text).forms if f["action"].endswith("/hochladen"))
    response = client.post(form["action"], data=form["fields"],
                           files={"datei": ("schule.jpg", image.read_bytes(), "image/jpeg")})
    assert response.status_code == 200
    run_jobs(app_env, fake_llm)
    doc = app_env.db.q1("SELECT * FROM document")
    assert doc["state"] == "erschlossen"
    assert client.get(f"/vorbereitung/schulmaterial/{doc['id']}").status_code == 200
    assert client.get(f"/scan/{doc['id']}.jpg").headers["content-type"] == "image/jpeg"
    page = client.get("/vorbereitung/inhalte")
    form = next(f for f in Forms(page.text).forms if f["action"].endswith("/entscheiden"))
    button = next(b for b in form["buttons"] if b["value"] == "aktiv")
    client.post(form["action"], data={**form["fields"], button["name"]: button["value"]})
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
    version = client.get("/ui/status").json()["version"]
    client.post(f"/lernzyklus/{topic_id}/quiz/starten", data={"_csrf": csrf_from(page.text)})
    run_jobs(app_env, fake_llm)
    assert client.get("/ui/status").json()["version"] != version
    quiz = app_env.db.q1("SELECT * FROM quiz WHERE lesson_id=?", lesson_id)
    assert quiz["anlass"] == "lernrunde"
    assert quiz["round_nr"] == 1
    page = client.get(f"/lernzyklus/{topic_id}/quiz/{quiz['id']}")
    assert 'data-answer-form' in page.text
    assert 'class="focus-view"' in page.text
    answers = {f"antwort_{f['id']}": "1/2" for f in quizzes.holen(quiz["id"])["fragen"]}
    client.post(f"/quiz/{quiz['id']}/antworten", data={"_csrf": csrf_from(page.text), **answers})
    run_jobs(app_env, fake_llm)
    page = client.get(f"/quiz/{quiz['id']}")
    review = next(f for f in Forms(page.text).forms if f["action"].endswith("/freigabe"))
    assert not any(key.startswith("urteil_") for key in review["fields"])
    assert 'data-review-form' in page.text
    assert 'class="focus-view"' not in page.text
    client.post(review["action"], data={"_csrf": csrf_from(page.text)})
    assert app_env.db.q1("SELECT finished_at FROM quiz WHERE id=?", quiz["id"])["finished_at"] is None
    assert client.get(f"/lernzyklus/{topic_id + 999}/quiz/{quiz['id']}").status_code == 404


def test_source_buttons_and_exam_fields_match_endpoints(client, fake_llm, fake_cli, app_env):
    from app import research
    einrichten(client, fake_llm)
    blatt_einlesen(client, fake_llm, app_env)
    topic_id = themen_freigeben(client, app_env)[0]
    research.anfordern(topic_id)
    run_jobs(app_env, fake_llm)
    page = client.get("/vorbereitung/inhalte/sources")
    form = next(f for f in Forms(page.text).forms if f["action"].endswith("/entscheiden"))
    button = next(b for b in form["buttons"] if b["value"] == "freigegeben")
    client.post(form["action"], data={**form["fields"], button["name"]: button["value"]})
    assert research.freigegebene(topic_id)
    page = client.get("/messung/examen")
    form = next(f for f in Forms(page.text).forms if f["action"].endswith("/neu"))
    response = client.post(form["action"], data={**form["fields"], "exam_date": "2099-01-01", "themen": "Brüche"})
    assert response.status_code == 200
    assert "2099-01-01" in response.text
    assert app_env.db.q1("SELECT exam_date FROM exam")["exam_date"] == "2099-01-01"
