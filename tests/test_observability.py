"""Beobachtbarkeit: Request-Korrelation, JSON-Zeilen, Entscheidungsgründe.

Drei getrennte Schichten werden geprüft:

  1. `observability.middleware` — eine `request_id` pro Anfrage, im Header
     und in jeder Logzeile des Requests, ein `request_completed`-
     Abschluss mit Status und Dauer, einmaliges `request_failed`.
  2. `observability.logging` — eine JSON-Zeile pro Eintrag, geschwärzt
     durch `security.redact`, mit `git_sha` und `env` auf jeder Zeile.
  3. `adaptiv.sitzung` — das Mastery-Gate schreibt seine Zahlen
     (erfolge/schwelle/entscheidung) in `lern_ereignis.nutzdaten`, damit
     ein falscher Lernpfad Monate später begründbar bleibt.
"""

from __future__ import annotations

import json
import logging

import pytest

from .test_app import einrichten


# --------------------------------------------------------------------------
# Formatter: eine Zeile, maschinenlesbar, geschwärzt
# --------------------------------------------------------------------------

def _format(record: logging.LogRecord) -> dict:
    from app.observability.logging import JsonFormatter

    return json.loads(JsonFormatter().format(record))


def _record(msg="probe", **kwargs) -> logging.LogRecord:
    return logging.getLogger("karo.test").makeRecord(
        "karo.test", logging.INFO, __file__, 1, msg, (), None, **kwargs)


def test_json_zeile_traegt_grundfelder(monkeypatch):
    monkeypatch.setenv("KARO_GIT_SHA", "abc123")
    monkeypatch.setenv("KARO_ENV", "test")

    eintrag = _format(_record("hallo welt"))

    assert eintrag["level"] == "INFO"
    assert eintrag["logger"] == "karo.test"
    assert eintrag["msg"] == "hallo welt"
    assert eintrag["service"] == "karo"
    assert eintrag["env"] == "test"
    assert eintrag["git_sha"] == "abc123"
    assert eintrag["ts"].endswith("+00:00")


def test_json_zeile_uebernimmt_fachfelder():
    eintrag = _format(_record("x", extra={
        "fach": {"event": "mastery_gate_checked", "sitzung_id": 7,
                 "erfolge": 4}}))

    assert eintrag["event"] == "mastery_gate_checked"
    assert eintrag["sitzung_id"] == 7
    assert eintrag["erfolge"] == 4
    assert "fach" not in eintrag  # eingeebnet, nicht verschachtelt


def test_json_zeile_schwaerzt_geheimnisse():
    eintrag_roh = _record("schluessel sk-testkey01-AAAABBBBCCCCDDDD hier")
    from app.observability.logging import JsonFormatter

    zeile = JsonFormatter().format(eintrag_roh)
    assert "sk-testkey" not in zeile
    assert "***redigiert***" in zeile
    # …und die Zeile bleibt trotz Schwärzung gültiges JSON.
    assert json.loads(zeile)["msg"].startswith("schluessel")


def test_json_zeile_traegt_traceback_und_typ():
    try:
        raise ValueError("kaputt")
    except ValueError:
        import sys
        record = _record("fehlgeschlagen")
        record.exc_info = sys.exc_info()

    eintrag = _format(record)
    assert eintrag["exception_type"] == "ValueError"
    assert "kaputt" in eintrag["exception"]
    assert "Traceback" in eintrag["exception"]


def test_json_zeile_ueberlebt_unbekannte_fachwerte():
    class Unbekannt:
        pass

    eintrag = _format(_record("x", extra={"fach": {"ding": Unbekannt()}}))
    assert eintrag["ding"]  # default=str statt TypeError


# --------------------------------------------------------------------------
# Request-ID: eine pro Anfrage, durchgereicht, im Header zurück
# --------------------------------------------------------------------------

def _sammelhandler(name="karo.http"):
    eintraege = []

    class Sammler(logging.Handler):
        def emit(self, record):
            eintraege.append(record)

    logger = logging.getLogger(name)
    sammler = Sammler()
    logger.addHandler(sammler)
    return eintraege, logger, sammler


def test_jede_antwort_traegt_eine_request_id(client):
    r = client.get("/health")
    rid = r.headers.get("x-request-id")
    assert rid and len(rid) >= 8


def test_auftraege_bekommen_eigene_ids(client):
    eins = client.get("/health").headers["x-request-id"]
    zwei = client.get("/health").headers["x-request-id"]
    assert eins != zwei


def test_saubere_fremde_id_wird_uebernommen(client):
    r = client.get("/health", headers={"x-request-id": "import-2026-10-02"})
    assert r.headers["x-request-id"] == "import-2026-10-02"


def test_verdaechtige_fremde_id_wird_ersetzt(client):
    # Leerzeichen und Anführungszeichen sind im Muster nicht vorgesehen —
    # so eine ID darf nicht unverändert in Header und Logs zurücklaufen.
    r = client.get("/health", headers={"x-request-id": 'bad "id' ' x'})
    rid = r.headers["x-request-id"]
    assert rid != 'bad "id' ' x'
    assert len(rid) == 16  # die hausgemachte uuid-Form


def test_request_id_reicht_bis_in_den_handler(client, app_env):
    """Der gleiche Wert, der im Header rausgeht, steht im Request-Kontext.

    `/setup/…` ist vor der Einrichtung der einzige Pfad, den die Gate-
    Middleware unangemeldet durchlässt — die Sonde haengt deshalb dort.
    """
    from app.observability import context
    from fastapi.responses import PlainTextResponse

    gesehen = {}

    async def innen(request):
        gesehen["rid"] = context.aktuell()
        return PlainTextResponse("ok")

    app_env.main.app.add_route("/setup/sonde", innen)
    r = client.get("/setup/sonde")
    assert gesehen["rid"] == r.headers["x-request-id"]


def test_request_abschluss_wird_mit_dauer_geloggt(client):
    eintraege, logger, sammler = _sammelhandler()
    try:
        client.get("/login")  # vor der Einrichtung: 303 auf /setup
    finally:
        logger.removeHandler(sammler)

    fertig = [e for e in eintraege
              if getattr(e, "fach", {}).get("event") == "request_completed"
              and e.fach["path"] == "/login"]
    assert len(fertig) == 1
    fach = fertig[0].fach
    assert fach["method"] == "GET"
    assert fach["status_code"] == 303
    assert fach["duration_ms"] >= 0


def test_ausnahme_wird_einmal_mit_kontext_geloggt(client, app_env):
    async def kaputt(request):
        raise RuntimeError("absichtlich")

    app_env.main.app.add_route("/setup/kaputt", kaputt)
    eintraege, logger, sammler = _sammelhandler()
    try:
        client.raise_server_exceptions = False
        r = client.get("/setup/kaputt")
    finally:
        logger.removeHandler(sammler)

    assert r.status_code == 500
    fehler = [e for e in eintraege
              if getattr(e, "fach", {}).get("event") == "request_failed"]
    assert len(fehler) == 1  # genau einmal — nicht nochmal ohne Kontext
    e = fehler[0]
    assert e.fach["path"] == "/setup/kaputt"
    assert e.exc_info and e.exc_info[0] is RuntimeError
    # Die 500-Antwort traegt die request_id der fehlgeschlagenen Anfrage.
    assert r.headers.get("x-request-id")
    # …und der Ausfall ueberlebt die Logrotation als Betriebsmeldung.
    row = app_env.db.q1(
        "SELECT bereich, text FROM betriebsmeldung WHERE bereich='http-500'")
    assert row["text"] == "GET /setup/kaputt: RuntimeError"
    # Zweiter identischer Fehler: gleiche Zeile, Zaehler hoch — kein Spam.
    client.get("/setup/kaputt")
    assert app_env.db.q1(
        "SELECT anzahl FROM betriebsmeldung WHERE bereich='http-500'"
    )["anzahl"] == 2


def test_contextvariable_ist_nach_der_anfrage_wieder_leer(client):
    from app.observability import context

    client.get("/health")
    assert context.aktuell() == ""


# --------------------------------------------------------------------------
# Korrelation über die Dienst-Grenze: X-Request-Id Richtung curriculum-api
# --------------------------------------------------------------------------

def _dienstaufruf(app_env, monkeypatch):
    """Ruft `request` mit einem gefaelschten Opener; gibt den gesendeten
    Request zurueck, damit der Test seine Header lesen kann."""
    import io
    from app.adaptiv import curriculum_dienst as bridge

    app_env.config.update(curriculum_url="http://127.0.0.1:8088",
                          curriculum_key="kc_" + "x" * 32)
    gesehen = {}

    class Opener:
        def open(self, req, **kwargs):
            gesehen["req"] = req
            return io.BytesIO(b'{"ok": true}')

    monkeypatch.setattr(bridge, "build_opener", lambda *a: Opener())
    bridge.request(app_env.config.load(), "GET", "/v1/meta")
    return gesehen["req"]


def test_dienstaufruf_traegt_die_laufende_request_id(client, app_env,
                                                   monkeypatch):
    from app.observability import context

    token = context.beginne("karo-req-12345")
    try:
        req = _dienstaufruf(app_env, monkeypatch)
    finally:
        context.ende(token)

    assert req.get_header("X-request-id") == "karo-req-12345"


def test_dienstaufruf_im_job_traegt_job_kennung(client, app_env, monkeypatch):
    """Hintergrundarbeit hat keine request_id — der Auftrag geht als
    `job-<id>`, so dass der Dienst ihn unter derselben Kennung loggt."""
    from app.observability import context

    token = context.job_beginne(7)
    try:
        req = _dienstaufruf(app_env, monkeypatch)
    finally:
        context.job_ende(token)

    assert req.get_header("X-request-id") == "job-000000007"


def test_dienstaufruf_ohne_kontext_schickt_keine_id(client, app_env,
                                                    monkeypatch):
    req = _dienstaufruf(app_env, monkeypatch)
    assert req.get_header("X-request-id") is None


def test_job_kontext_endet_mit_dem_lauf(client, app_env):
    from app.observability import context

    token = context.job_beginne(9)
    context.job_ende(token)
    assert context.korrelation() == ""


# --------------------------------------------------------------------------
# Hintergrundjobs: eigene Identitaet in jeder Zeile, Fehler komplett
# --------------------------------------------------------------------------

def test_job_lauf_traegt_job_id_auf_jeder_zeile(client, app_env):
    from app import jobs
    from app.observability import context

    gesehen = {}
    jobs.HANDLERS["sonde_job"] = lambda payload: gesehen.update(
        job_id=context.job_id.get(), korrelation=context.korrelation())
    try:
        jid = jobs.enqueue("sonde_job", {})
        assert jid
        status, _ = jobs.run_now(jid)
    finally:
        del jobs.HANDLERS["sonde_job"]

    assert status == "done"
    assert gesehen["job_id"] == jid
    assert gesehen["korrelation"] == f"job-{jid:09d}"
    # …und der Kontext ist nach dem Lauf wieder weg.
    assert context.job_id.get() == 0


def test_job_fehler_einmal_mit_traceback_und_id(client, app_env):
    from app import jobs

    def kaputt(payload):
        raise RuntimeError("im Job")

    eintraege = []
    sammler = type("S", (logging.Handler,),
                   {"emit": lambda self, r: eintraege.append(r)})()
    logger = logging.getLogger("karo.jobs")
    logger.addHandler(sammler)
    jobs.HANDLERS["kaputt_job"] = kaputt
    try:
        jid = jobs.enqueue("kaputt_job", {})
        status, _ = jobs.run_now(jid)
    finally:
        del jobs.HANDLERS["kaputt_job"]
        logger.removeHandler(sammler)

    assert status == "failed"
    fehl = [e for e in eintraege
            if getattr(e, "fach", {}).get("event") == "job_failed"]
    assert len(fehl) == 1
    assert fehl[0].fach["job_id"] == jid
    assert fehl[0].fach["job_type"] == "kaputt_job"
    assert fehl[0].exc_info and fehl[0].exc_info[0] is RuntimeError
    # Der Fehler bleibt ausserdem dauerhaft in der job-Tabelle.
    row = app_env.db.q1("SELECT state, last_error FROM job WHERE id=?", jid)
    assert row["state"] == "wartend" or row["state"] == "fehler"
    assert "im Job" in (row["last_error"] or "")


# --------------------------------------------------------------------------
# Lern-Audit: das Mastery-Gate schreibt seine Begründung
# --------------------------------------------------------------------------

def _lektion_anlegen():
    """Minimaler Katalogeintrag wie in test_adaptiv_domain._katalog."""
    from app.adaptiv import katalog, store

    konzept_id = store.konzept_sichern(
        "mathematik", "audit-konzept", "audit-fehler",
        "Audit-Konzept", 5, 6, geprueft=True)
    fehlertyp_id = store.fehlertyp_sichern(
        konzept_id, "audit-fehler", "Audit-Fehler", geprueft=True)
    katalog.fehlertyp_lernen(fehlertyp_id, "1/2", quelle="kuratiert")
    erklaerung_id = store.erklaerung_anlegen(
        fehlertyp_id, 6, "Regel", geprueft=True)
    return konzept_id, fehlertyp_id, erklaerung_id


def test_mastery_gate_schreibt_erfolge_schwelle_und_ausgang(
        client, fake_llm, app_env):
    from app.adaptiv import sitzung, store

    einrichten(client, fake_llm)
    app_env.config.update(adaptiv_mastery_treffer=3)
    konzept_id, fehlertyp_id, erklaerung_id = _lektion_anlegen()

    s = sitzung.starten(konzept_id=konzept_id)
    sitzung.wechsle(s["id"], sitzung.MATERIAL_ANALYZED)
    sitzung.wechsle(s["id"], sitzung.DIAGNOSING)
    sitzung.fehler_erkannt(s["id"], fehlertyp_id)
    sitzung.unterricht_beginnen(s["id"], erklaerung_id)

    stand = sitzung.antwort_richtig(s["id"], "1/2")
    assert stand["zustand"] == sitzung.TEACHING  # Schwelle noch nicht da

    letzte = store.ereignisse(s["id"])[-1]
    assert letzte["anlass"] == "Antwort richtig"
    nutz = letzte["nutzdaten"]
    assert nutz == {"erfolge": 1, "schwelle": 3, "abschluss_erlaubt": True,
                    "gemeistert": False}

    sitzung.antwort_richtig(s["id"], "1/2")
    stand = sitzung.antwort_richtig(s["id"], "1/2")
    assert stand["zustand"] == sitzung.MASTERED

    gate = [e for e in store.ereignisse(s["id"])
            if e["anlass"] == "Antwort richtig"][-1]
    nutz = gate["nutzdaten"]
    assert nutz["erfolge"] == 3 and nutz["schwelle"] == 3
    assert nutz["gemeistert"] is True


def test_gescheiterte_runde_schreibt_die_grenze(client, fake_llm,
                                                app_env):
    from app.adaptiv import sitzung, store

    einrichten(client, fake_llm)
    konzept_id, fehlertyp_id, erklaerung_id = _lektion_anlegen()

    s = sitzung.starten(konzept_id=konzept_id)
    sitzung.wechsle(s["id"], sitzung.MATERIAL_ANALYZED)
    sitzung.wechsle(s["id"], sitzung.DIAGNOSING)
    sitzung.fehler_erkannt(s["id"], fehlertyp_id)
    sitzung.unterricht_beginnen(s["id"], erklaerung_id)
    sitzung.runde_gescheitert(s["id"], "falsch")

    letzte = store.ereignisse(s["id"])[-1]
    assert letzte["anlass"] == "Lehrrunde ohne Erfolg"
    nutz = letzte["nutzdaten"]
    assert nutz["runde"] == 1
    assert nutz["grenze"] == sitzung.max_runden()
