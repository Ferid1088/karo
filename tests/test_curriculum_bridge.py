"""No network/paid models: exercise the real persistent worker and HTTP contract."""
import json
import time
from urllib.error import HTTPError, URLError

import pytest

from .test_lektion_erzeugung import _lektion

TOPIC = "Würfel: Volumen"


@pytest.fixture
def bridge(app_env, monkeypatch):
    monkeypatch.delenv("KARO_CURRICULUM_URL", raising=False)
    monkeypatch.delenv("KARO_CURRICULUM_KEY", raising=False)
    from app.adaptiv import curriculum_dienst as service, store
    app_env.db.init()
    store.init()
    app_env.config.update(curriculum_url="http://127.0.0.1:8088",
                          curriculum_key="kc_test_secret", learner_name="Lena")
    # Vor jedem Auftrag gleicht Karo die Vertragsfassung ab. Hier ist das nicht
    # der Prüfgegenstand, also antwortet der Dienst passend — sonst würde jeder
    # Test dieser Datei am Versionsabgleich hängen bleiben statt zu prüfen, was
    # er prüfen will. Den Abgleich selbst prüft tests/test_curriculum_vertrag.py.
    monkeypatch.setattr(service, "meta", lambda cfg: {
        "contract_version": service.CONTRACT_VERSION, "git_sha": "test",
        "formats": [service.FORMAT_ID]})
    return service


def ready(version=1):
    return {"status": "ready", "export_id": 17, "format": "karo-adaptiv-v1",
            "concept_id": "MA.GEO.WUERFEL", "concept_version": version,
            "classification": {"source": "approved_curriculum", "first_contact_grade": 5, "target_grade": 7},
            "lesson": _lektion()}


def enqueue():
    from app.adaptiv import erzeugung
    return erzeugung.anfordern(TOPIC, "Mathematik", 6)


def test_profile_one_import_keeps_canonical_range(app_env, bridge):
    from app.adaptiv import store
    cid = bridge.import_lesson(app_env.config.load(), ready(), TOPIC, 'mathematik', 1)
    c = store.konzept(cid)
    assert (c['klasse_von'], c['klasse_bis']) == (5, 7)
    assert bridge.import_lesson(app_env.config.load(), ready(), TOPIC, 'mathematik', 6) == cid


def test_plausible_schema_but_wrong_classification_is_rejected(app_env, bridge):
    from app.adaptiv import schemas
    bad = ready()
    bad['lesson']['konzept'].update(klasse_von=1, klasse_bis=1)
    with pytest.raises(schemas.InhaltUngueltig, match='Curriculum'):
        bridge.import_lesson(app_env.config.load(), bad, TOPIC, 'mathematik', 1)
    assert not app_env.db.q("SELECT * FROM lern_konzept WHERE quelle='curriculum'")


def job(app_env, jid):
    return dict(app_env.db.q1("SELECT * FROM job WHERE id=?", jid))


def test_pending_survives_restarts_and_does_not_spend_retries(app_env, bridge, monkeypatch):
    from app import jobs
    calls = []
    def pending(cfg, method, path, body=None):
        calls.append((method, path))
        return {"status": "pending", "export_id": 17, "retry_after": 15}
    monkeypatch.setattr(bridge, "request", pending)
    jid = enqueue()
    for _ in range(6):
        assert jobs.run_now(jid)[0] == "pending"
        state = job(app_env, jid)
        assert state["state"] == "wartend" and state["attempts"] == 0
        assert state["not_before"] > app_env.db.now()
        assert json.loads(state["payload"])["curriculum_export"] == 17
        assert not jobs.run_once()  # scheduled polling, no hot loop
        assert jobs.recover_stuck() == 0
    assert calls[0] == ("POST", "/v1/lessons")
    assert all(c == ("GET", "/v1/lessons/17") for c in calls[1:])
    monkeypatch.setattr(bridge, "request", lambda *a, **kw: ready())
    assert jobs.run_now(jid)[0] == "done"
    assert job(app_env, jid)["state"] == "fertig"


def test_ready_is_checked_stored_and_reused_without_service(app_env, bridge, monkeypatch):
    from app import jobs
    from app.adaptiv import erzeugung, lektionen, store
    calls = []
    monkeypatch.setattr(bridge, "request", lambda *a, **kw: (calls.append(a), ready())[1])
    jid = enqueue()
    assert erzeugung.anfordern(TOPIC, "Mathematik", 6) is None
    assert jobs.run_now(jid)[0] == "done"
    lesson = lektionen.fuer_thema(TOPIC, "Mathematik", 6)
    assert store.konzept(lesson["konzept_id"])["quelle"] == "curriculum"
    assert jobs.run_now(enqueue())[0] == "done"
    assert len(calls) == 1
    assert len(app_env.db.q("SELECT * FROM lern_curriculum_import")) == 1


def test_versions_are_immutable_and_do_not_change_active_session(app_env, bridge):
    from app.adaptiv import store, unterricht
    cfg = app_env.config.load()
    first = bridge.import_lesson(cfg, ready(), TOPIC, "Mathematik", 6)
    session = unterricht.starte(first, TOPIC)
    assert bridge.import_lesson(cfg, ready(), TOPIC, "Mathematik", 6) == first
    newer = ready(2)
    newer["lesson"]["erstkontakt"]["anker"] = "Eine andere Einstiegsfrage"
    second = bridge.import_lesson(cfg, newer, TOPIC, "Mathematik", 6)
    assert second != first
    assert store.sitzung(session["id"])["konzept_id"] == first
    assert store.erstkontakt(first)["anker"] != store.erstkontakt(second)["anker"]


@pytest.mark.parametrize("failure", ["arithmetic", "grade", "topic", "markup", "duplicate", "entry"])
def test_invalid_content_is_rejected_before_any_import(app_env, bridge, monkeypatch, failure):
    from app import jobs
    bad = ready()
    lesson = bad["lesson"]
    if failure == "arithmetic":
        lesson["fehlertypen"][0]["aufgaben"]["gefuehrt"].update(frage="2 + 2", loesung="5")
    elif failure == "grade":
        lesson["konzept"]["klasse_von"] = 9
    elif failure == "topic":
        lesson["konzept"].update(label="Englische Zeiten", stichworte=["past tense"])
    elif failure == "markup":
        lesson["erstkontakt"]["anker"] = "<script>alert(1)</script>"
    elif failure == "duplicate":
        lesson["fehlertypen"][0]["aufgaben"]["gefuehrt"]["frage"] = "Kante 2 cm"
    else:
        del lesson["erstkontakt"]
    calls = []
    def respond(cfg, method, path, body=None):
        calls.append(path)
        return {"status": "pending", "export_id": 18} if path.endswith("reject") else bad
    monkeypatch.setattr(bridge, "request", respond)
    jid = enqueue()
    assert jobs.run_now(jid)[0] == "pending"
    assert calls == ["/v1/lessons", "/v1/lessons/17/reject"]
    assert json.loads(job(app_env, jid)["payload"])["curriculum_export"] == 18
    assert not app_env.db.q("SELECT id FROM lern_konzept WHERE quelle='curriculum'")


def test_unavailable_waits_but_never_falls_back_to_local_generation(app_env, bridge, monkeypatch):
    """"Nicht verfügbar" heißt meistens "gerade nicht".

    Der Dienst drosselt, wenn viele Themen auf einmal kommen: bei siebzehn
    Prüfungsthemen starben so die ersten Aufträge sofort, obwohl dieselben
    Themen Sekunden später wieder ausgeliefert wurden. Der Auftrag wartet
    deshalb und fragt erneut — was er nie tut, ist lokal erzeugen. Die
    Gesamtdauer deckelt `MAX_WAIT_SECONDS`, siehe den Test darunter.
    """
    from app import jobs
    monkeypatch.setattr(bridge, "request", lambda *a, **kw: {"status": "unavailable"})
    vorher = len(app_env.db.q("SELECT id FROM lern_konzept"))
    jid = enqueue()
    assert jobs.run_now(jid)[0] == "pending"
    assert job(app_env, jid)["state"] == "wartend"
    # Kein lokal erzeugtes Konzept, und kein verbrauchter Versuch.
    assert len(app_env.db.q("SELECT id FROM lern_konzept")) == vorher
    assert job(app_env, jid)["attempts"] == 0


def test_vom_dienst_endgueltig_abgelehntes_material_wartet_nicht(app_env, bridge, monkeypatch):
    """Was Karos eigene Prüfung abgelehnt hat, gibt der Dienst nicht wieder
    heraus. Darauf zu warten wäre endloses Nichts."""
    from app import jobs
    monkeypatch.setattr(bridge, "request", lambda *a, **kw: {
        "status": "unavailable", "reason_code": "rejected_by_client"})
    jid = enqueue()
    assert jobs.run_now(jid)[0] == "failed"
    assert job(app_env, jid)["state"] == "fehler"
    assert "nichts Geprüftes mehr" in job(app_env, jid)["last_error"]


def test_service_change_cannot_resume_old_export_elsewhere(app_env, bridge, monkeypatch):
    from app import jobs
    jid = enqueue()
    app_env.config.update(curriculum_url="", curriculum_key="")
    def unexpected(*a, **kw):
        pytest.fail("must not contact a changed service")
    monkeypatch.setattr(bridge, "request", unexpected)
    assert jobs.run_now(jid)[0] == "failed"
    assert "geändert" in job(app_env, jid)["last_error"]


def test_wait_has_a_finite_deadline(app_env, bridge, monkeypatch):
    from app import jobs
    monkeypatch.setattr(bridge, "request", lambda *a, **kw: pytest.fail("expired request"))
    with pytest.raises(jobs.PermanentFailure, match="zu lange"):
        bridge.prepare(app_env.config.load(), {"curriculum_started": time.time() - 90000},
                       TOPIC, "Mathematik", 6)


def test_only_sanitized_subject_topic_and_format_leave_app(app_env, bridge, monkeypatch):
    from app import jobs
    sent = []
    def capture(cfg, method, path, body=None):
        sent.append(body)
        return {"status": "pending", "export_id": 17}
    monkeypatch.setattr(bridge, "request", capture)
    with pytest.raises(jobs.Deferred):
        bridge.prepare(app_env.config.load(), {"exam_id": 4, "topic_id": 9},
                       "Lena Würfel Volumen", "Mathematik", 6)
    assert set(sent[0]) == {"subject", "grade", "topic", "format"}
    assert "Lena" not in json.dumps(sent[0])
    assert "kc_test_secret" not in repr(app_env.config.load())
    assert "curriculum_key" not in app_env.config.load().public_dict()
    from app.security import redact
    key = "kc_" + "a" * 40
    assert key not in redact("key: " + key)


@pytest.mark.parametrize("code,terminal", [(401, True), (403, True), (422, True),
                                          (302, True), (429, False), (503, False)])
def test_http_errors_are_sanitized(app_env, bridge, monkeypatch, code, terminal):
    from app import jobs
    class Opener:
        def open(self, req, **kw):
            raise HTTPError(req.full_url, code, "SECRET BODY", {}, None)
    monkeypatch.setattr(bridge, "build_opener", lambda *a: Opener())
    with pytest.raises(jobs.PermanentFailure if terminal else RuntimeError) as error:
        bridge.request(app_env.config.load(), "POST", "/v1/lessons", {})
    assert "SECRET" not in str(error.value) and "kc_test_secret" not in str(error.value)


def test_transport_failure_retries_without_an_import(app_env, bridge, monkeypatch):
    from app import jobs
    class Opener:
        def open(self, req, **kw):
            raise URLError("sensitive connection information")
    monkeypatch.setattr(bridge, "build_opener", lambda *a: Opener())
    jid = enqueue()
    for expected in ("wartend", "wartend", "fehler"):
        assert jobs.run_now(jid)[0] == "failed"
        assert job(app_env, jid)["state"] == expected
    assert not app_env.db.q("SELECT * FROM lern_curriculum_import")


def test_personal_and_exam_resume_separately_after_remote_generation(
        client, fake_llm, app_env, bridge, monkeypatch):
    from app import jobs
    from app.adaptiv import store
    from app.services import learning_hub, exam
    from .test_app import einrichten, kind_modus_aktivieren
    from .conftest import csrf_from
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True, klassenarbeit_kind=True,
                          llm_error_creation_enabled=False, learner_grade=6)
    personal = learning_hub.create_topic(TOPIC, "Mathematik", 6)
    eid = exam.create_exam("2027-10-15", manual_topics=TOPIC, subject="Mathematik").exam_id
    etid = learning_hub.exam_topics(eid)[0]["id"]
    kind_modus_aktivieren(client)
    token = csrf_from(client.get("/lernen").text)
    fake_llm.calls.clear()
    monkeypatch.setattr(bridge, "request", lambda *a, **kw: ready())
    bases = [("/lernen/adaptiv", personal), (f"/klassenarbeit/{eid}/lernen", etid)]
    for base, tid in bases:
        page = client.post(base + "/start", data={"_csrf": token, "topic_id": tid})
        assert "bereitet" in page.text
    pending = app_env.db.q("SELECT id FROM job WHERE type='lektion_erzeugen'")
    assert len(pending) == 1
    assert jobs.run_now(pending[0]["id"])[0] == "done"
    for base, tid in bases:
        status = client.get(base + f"/status?topic_id={tid}").json()
        assert status["fertig"]
        page = client.get(base + f"/wartet?topic_id={tid}")
        assert page.status_code == 200 and "/anker?sitzung=" in page.text
    sessions = app_env.db.q("SELECT * FROM lern_sitzung")
    assert len(sessions) == 2
    assert sessions[0]["konzept_id"] == sessions[1]["konzept_id"]
    assert store.fortschritt_scope(dict(sessions[0])) != store.fortschritt_scope(dict(sessions[1]))
    assert client.get(f"/lernen/adaptiv/wartet?topic_id={etid}").status_code == 404
    # Resume still uses the pinned version when the catalogue is temporarily
    # unavailable (or points at a newer version).
    monkeypatch.setattr("app.adaptiv.lektionen.fuer_thema", lambda *a: None)
    for base, tid in bases:
        page = client.post(base + "/start", data={"_csrf": token, "topic_id": tid})
        assert "/anker?sitzung=" in page.text
    assert len(app_env.db.q("SELECT * FROM lern_sitzung")) == 2
    assert fake_llm.calls == []


def test_job_pins_grade_before_config_changes(app_env, bridge):
    from app.adaptiv import erzeugung
    app_env.config.update(learner_grade=5)
    jid = erzeugung.anfordern(TOPIC, "mathematik")
    app_env.config.update(learner_grade=7)
    assert json.loads(job(app_env, jid)["payload"])["klasse"] == 5


@pytest.mark.parametrize("raw", [b"not json", b"[]", b"x" * 2_000_001])
def test_transport_rejects_malformed_or_oversized_response(app_env, bridge, monkeypatch, raw):
    import io
    from app import jobs
    class Opener:
        def open(self, req, **kwargs):
            assert kwargs["timeout"] == 8
            assert req.get_header("Authorization") == "Bearer kc_test_secret"
            return io.BytesIO(raw)
    monkeypatch.setattr(bridge, "build_opener", lambda *a: Opener())
    with pytest.raises(jobs.PermanentFailure):
        bridge.request(app_env.config.load(), "GET", "/v1/lessons/17")


def test_placeholder_key_fails_without_network(app_env, bridge, monkeypatch):
    from app import jobs
    app_env.config.update(curriculum_key="kc_…")
    monkeypatch.setattr(bridge, "build_opener", lambda *a: pytest.fail("must not send placeholder"))
    with pytest.raises(jobs.PermanentFailure, match="eingerichtet"):
        bridge.request(app_env.config.load(), "GET", "/v1/lessons/17")


def test_polling_does_not_block_other_jobs(app_env, bridge, monkeypatch):
    from app import jobs
    monkeypatch.setattr(bridge, "request", lambda *a, **kw: {
        "status": "pending", "export_id": 17, "retry_after": 15})
    jid = enqueue()
    ran = []
    @jobs.handler("bridge_test_ping")
    def ping(payload):
        ran.append(True)
    jobs.enqueue("bridge_test_ping")
    assert jobs.run_once()
    assert job(app_env, jid)["state"] == "wartend"
    assert jobs.run_once() and ran == [True]


def test_repeated_bad_exports_stop_after_two_rework_requests(app_env, bridge, monkeypatch):
    from app import jobs
    response = ready()
    del response["lesson"]["erstkontakt"]
    rejects = []
    def respond(cfg, method, path, body=None):
        if path.endswith("/reject"):
            rejects.append(path)
            return {"status": "pending", "export_id": 17}
        return response
    monkeypatch.setattr(bridge, "request", respond)
    jid = enqueue()
    assert jobs.run_now(jid)[0] == "pending"
    assert jobs.run_now(jid)[0] == "pending"
    assert jobs.run_now(jid)[0] == "failed"
    assert len(rejects) == 2
    assert job(app_env, jid)["state"] == "fehler"
