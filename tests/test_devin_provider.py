"""Devin ist der einzige KI-Anbieter — Vertrag, Session-Lebenszyklus, Grenzen.

Diese Datei ist der Regressionstest für die Ablösung: sie verankert, dass
es genau einen externen Anbieter gibt, dass sein Schlüssel nur aus der
Umgebung kommt, dass seine asynchronen Sessions dauerhaft persistiert
werden und dass ein ausstehender Auftrag den Job parkt statt ihn
fehlschlagen zu lassen.
"""
from __future__ import annotations

import inspect
import os
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
APP = WURZEL / "app"

SCHEMA = {"type": "object", "required": ["ok"],
          "properties": {"ok": {"type": "boolean"}}}


def _backend(fake_llm, app_env):
    """Devin-Backend, dessen HTTP-Ebene die Session-Attrappe bedient."""
    from app.ai.devin import DevinBackend

    return DevinBackend()


# --------------------------------------------------------------------------
# Ein einziger Anbieter, kein Weg zurück
# --------------------------------------------------------------------------

def test_devin_ist_der_einzige_anbieter(app_env):
    from app.ai.client import build_backend
    from app.ai.devin import DevinBackend

    backend = build_backend(app_env.config.load_safe())
    assert isinstance(backend, DevinBackend)
    assert backend.name == "devin"


def test_jeder_andere_anbieter_wird_abgelehnt(app_env):
    from app.ai import AISetupError
    from app.ai.client import build_backend
    import dataclasses

    cfg = dataclasses.replace(app_env.config.load_safe(), ai_provider="etwas-anderes")
    with pytest.raises(AISetupError):
        build_backend(cfg)


def test_kein_alter_anbieter_ist_registriert():
    """Weder Paket noch Konfiguration kennen einen anderen Anbieter."""
    from app import config

    felder = {f.name for f in config.Config.__dataclass_fields__.values()}
    assert config.Config.ai_provider == "devin"
    for alt in ("llm_backend", "model_text", "model_stark", "model_vision"):
        assert alt not in felder, alt


def test_keine_alten_schluessel_werden_gelesen():
    """Kein Modul liest mehr die alten Zugangsdaten — weder als Config-Feld
    noch als Umgebungsvariable."""
    import re

    muster = re.compile(
        r"environ.*?(OAUTH|_KEY)|environ\.get\(['\"][A-Z_]+|getenv\(['\"][A-Z_]+")
    verboten = ("CLAUDE", "ANTHROPIC")
    treffer = []
    for pfad in APP.rglob("*.py"):
        for nr, zeile in enumerate(pfad.read_text().splitlines(), 1):
            if any(v in zeile for v in verboten):
                treffer.append(f"{pfad.name}:{nr}: {zeile.strip()[:80]}")
    assert not treffer, "alte Schlüssel werden noch gelesen:\n" + "\n".join(treffer)


def test_kein_cli_aufruf_mehr():
    """Kein Unterprozess darf mehr eine fremde Kommandozeile starten."""
    treffer = []
    for pfad in APP.rglob("*.py"):
        quelle = pfad.read_text()
        for suchwort in ("subprocess", "Popen", "shutil.which"):
            if suchwort in quelle:
                treffer.append(f"{pfad.name}: {suchwort}")
    # Erlaubt bleiben lokale Werkzeuge (tesseract, ffmpeg) — aber nie ein
    # Modell-Frontend. Wer hier eine neue Stelle sieht, muss sie prüfen.
    erlaubt = {"notebooklm.py", "tts.py", "video.py", "ingest.py",
               "blatt_text.py", "export.py"}
    rest = {t.split(":")[0] for t in treffer} - erlaubt
    assert not rest, f"unerwartete Unterprozess-Stellen: {rest}"


def test_ohne_schluessel_klare_fehlermeldung(app_env, monkeypatch):
    """Kein stiller Fallback: fehlt DEVIN_API_KEY, scheitert der Aufruf mit
    einer Meldung, die den Ausweg nennt — am HTTP-Aufbau, nicht erst beim
    ersten Request."""
    from app.ai import AISetupError
    from app.ai.devin import DevinBackend

    monkeypatch.delenv("DEVIN_API_KEY")
    app_env.db.init()
    backend = DevinBackend()
    with pytest.raises(AISetupError, match="DEVIN_API_KEY"):
        _ = backend.client


# --------------------------------------------------------------------------
# Session-Lebenszyklus
# --------------------------------------------------------------------------

def test_erster_aufruf_legt_session_an_und_meldet_pending(
        fake_llm, app_env):
    from app.ai import AIPending

    app_env.db.init()
    fake_llm.devin.working_once = True   # Session braucht — sofort fertig ist die Ausnahme
    backend = _backend(fake_llm, app_env)
    with pytest.raises(AIPending) as ausstehend:
        backend.call("Aufgabe", SCHEMA, model="devin", purpose="probe")

    assert len(fake_llm.devin.sessions) == 1
    assert ausstehend.value.session_id == "dev-test-1"
    # Die Zuordnung ist persistiert — ein Prozessneustart legt keine zweite
    # Session an.
    row = app_env.db.q1("SELECT * FROM provider_session")
    assert row["session_id"] == "dev-test-1"
    assert row["provider"] == "devin"


def test_zweiter_aufruf_holt_das_ergebnis_ab(fake_llm, app_env):
    from app.ai import AIPending

    app_env.db.init()
    fake_llm.devin.working_once = True
    fake_llm.responses["verify_ping"] = {"ok": True}
    backend = _backend(fake_llm, app_env)
    with pytest.raises(AIPending):
        backend.call("Aufgabe", SCHEMA, model="devin", purpose="probe")

    ergebnis = backend.call("Aufgabe", SCHEMA, model="devin", purpose="probe")
    assert ergebnis.data == {"ok": True}
    assert len(fake_llm.devin.created) == 1   # keine zweite Session


def test_laufende_session_erzeugt_kein_duplikat(fake_llm, app_env):
    from app.ai import AIPending

    app_env.db.init()
    fake_llm.devin.working_once = True
    backend = _backend(fake_llm, app_env)
    with pytest.raises(AIPending):
        backend.call("Aufgabe", SCHEMA, model="devin", purpose="probe")
    # Session bleibt dauerhaft im Lauf — kein zweites POST beim nächsten Aufruf.
    sid = next(iter(fake_llm.devin.sessions))
    fake_llm.devin.sessions[sid]["status_enum"] = "running"
    with pytest.raises(AIPending):
        backend.call("Aufgabe", SCHEMA, model="devin", purpose="probe")
    assert len(fake_llm.devin.sessions) == 1


def test_blockierte_session_wird_einmal_nachgefasst(fake_llm, app_env,
                                                    monkeypatch):
    from app.ai import AIPending

    app_env.db.init()
    fake_llm.devin.working_once = True
    backend = _backend(fake_llm, app_env)
    with pytest.raises(AIPending):
        backend.call("Aufgabe", SCHEMA, model="devin", purpose="probe")
    # Session künstlich auf blocked stellen.
    sid = next(iter(fake_llm.devin.sessions))
    fake_llm.devin.sessions[sid]["status_enum"] = "blocked"
    fake_llm.devin.sessions[sid]["structured_output"] = None
    with pytest.raises(AIPending):
        backend.call("Aufgabe", SCHEMA, model="devin", purpose="probe")
    row = app_env.db.q1("SELECT * FROM provider_session")
    assert row["nudged"] == 1


def test_dauerhaft_blockierte_session_gilt_als_fehler(fake_llm, app_env):
    from app.ai import AIPending, AIError

    app_env.db.init()
    fake_llm.devin.working_once = True
    backend = _backend(fake_llm, app_env)
    with pytest.raises(AIPending):
        backend.call("Aufgabe", SCHEMA, model="devin", purpose="probe")
    with app_env.db.tx() as c:
        c.execute("UPDATE provider_session SET nudged=1")
    sid = next(iter(fake_llm.devin.sessions))
    fake_llm.devin.sessions[sid]["status_enum"] = "blocked"
    fake_llm.devin.sessions[sid]["structured_output"] = None
    with pytest.raises(AIError):
        backend.call("Aufgabe", SCHEMA, model="devin", purpose="probe")


def test_abgelaufene_session_wird_begrenzt_neu_gestartet(fake_llm, app_env):
    from app.ai import AIPending, AIError

    app_env.db.init()
    fake_llm.devin.working_once = True
    backend = _backend(fake_llm, app_env)
    with pytest.raises(AIPending):
        backend.call("Aufgabe", SCHEMA, model="devin", purpose="probe")
    sid = next(iter(fake_llm.devin.sessions))
    fake_llm.devin.sessions[sid]["status_enum"] = "expired"
    # Erster Neustart ist erlaubt.
    with pytest.raises(AIPending):
        backend.call("Aufgabe", SCHEMA, model="devin", purpose="probe")
    assert len(fake_llm.devin.sessions) == 2
    # Zweite Leiche nicht mehr — das Restart-Limit greift.
    neu = [s for s in fake_llm.devin.sessions.values()][-1]
    neu["status_enum"] = "expired"
    with pytest.raises(AIError):
        backend.call("Aufgabe", SCHEMA, model="devin", purpose="probe")


def test_pending_parkt_den_job_statt_ihn_scheitern_zu_lassen(
        fake_llm, app_env):
    """AIPending → Deferred: der Auftrag wartet, ein Versuch wird nicht
    verbraucht und `not_before` parkt ihn sichtbar."""
    from app import jobs
    from app.ai import AIPending

    app_env.db.init()

    @jobs.handler("probe_pending")
    def _job(_payload):
        raise AIPending("Session läuft", wait_seconds=42)

    job_id = jobs.enqueue("probe_pending", {"x": 1})
    assert jobs.run_once() is True

    row = app_env.db.q1("SELECT * FROM job WHERE id=?", job_id)
    assert row["state"] == "wartend"
    assert row["attempts"] == 0            # kein Versuch verbraucht
    assert row["not_before"] is not None   # geparkt, nicht sofort wieder
    assert row["last_error"] is None       # Pending ist kein Fehler


def test_materialanalyse_laeuft_ueber_devin(client, fake_llm, app_env):
    """Die sensible Analyse geht an denselben Anbieter wie alles andere —
    als Session mit dem Material-Schema."""
    from .test_app import einrichten
    from .test_material_paket import MATERIAL_ANTWORT, _bild, _meta, _paket_id, _upload
    from .conftest import run_jobs

    einrichten(client, fake_llm)
    fake_llm.responses["material"] = dict(MATERIAL_ANTWORT)
    antwort = _upload(client, [("blatt.jpg", _bild(), "image/jpeg")],
                      metadaten=_meta())
    assert antwort.status_code == 200, antwort.text
    _paket_id(antwort)
    run_jobs(app_env, fake_llm)
    paket = app_env.db.q1("SELECT * FROM material_paket ORDER BY id DESC")
    assert paket["state"] == "bereit", paket["fehler"]
    assert len(fake_llm.devin.created) == 1
    assert fake_llm.devin.created[0].get("structured_output_schema")


# --------------------------------------------------------------------------
# Oberfläche ohne alte Wege
# --------------------------------------------------------------------------

def test_kein_bildparameter_am_anbieter():
    """Bleibt in Stein gemeisselt — siehe auch test_keine_bilder_an_modelle."""
    from app.ai.client import AIClient
    from app.ai.devin import DevinBackend

    for fn in (AIClient.complete, DevinBackend.call):
        namen = set(inspect.signature(fn).parameters)
        assert not (namen & {"image_path", "image_url", "bild_pfad",
                             "media_type"}), fn


def test_setup_seite_zeigt_nur_devin(client, fake_llm, app_env):
    from .conftest import csrf_from

    seite = client.get("/setup")
    assert seite.status_code == 200
    assert "DEVIN_API_KEY" in seite.text
    assert 'name="backend"' not in seite.text
    assert 'name="token"' not in seite.text
    assert 'name="api_key"' not in seite.text
