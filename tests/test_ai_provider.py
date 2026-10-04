"""Der KI-Anbieter ist eine Config-Entscheidung, kein fachlicher Bestandteil.

Diese Datei ist der Regressionstest für die Anbieter-Unabhängigkeit:
die Registry löst `Config.ai_provider` auf, beide Adapter erfüllen denselben
`AIProvider`-Vertrag (start/poll → neutrale Statuswerte), Schlüssel kommen
nur aus der Umgebung, und Domain-Code kennt keine Anbieter-Namen.
"""
from __future__ import annotations

import inspect
import os
import re
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
APP = WURZEL / "app"

SCHEMA = {"type": "object", "required": ["ok"],
          "properties": {"ok": {"type": "boolean"}}}


def _request(**kw):
    from app.ai.types import AIRequest
    basis = dict(purpose="probe", user_prompt="Aufgabe", schema=SCHEMA)
    basis.update(kw)
    return AIRequest(**basis)


# --------------------------------------------------------------------------
# Registry: eine Wahrheit, eine Auflösung
# --------------------------------------------------------------------------

def test_registry_loest_den_gewaehlten_anbieter_auf(app_env):
    from app.ai.registry import PROVIDERS, build
    from app.ai.providers.devin import DevinProvider
    from app.ai.providers.openrouter import OpenRouterProvider
    import dataclasses

    cfg = app_env.config.load_safe()
    assert isinstance(build(cfg), DevinProvider)
    assert PROVIDERS.keys() >= {"devin", "openrouter"}
    cfg = dataclasses.replace(cfg, ai_provider="openrouter")
    assert isinstance(build(cfg), OpenRouterProvider)


def test_jeder_andere_anbieter_wird_abgelehnt(app_env):
    import dataclasses

    from app.ai import AISetupError
    from app.ai.registry import build

    cfg = dataclasses.replace(app_env.config.load_safe(),
                              ai_provider="etwas-anderes")
    with pytest.raises(AISetupError, match="Unbekannter KI-Anbieter"):
        build(cfg)


def test_schluessel_und_anzeigename_kommen_aus_dem_adapter(app_env):
    import dataclasses

    from app.ai.registry import credentials_present, display_name, secret_env

    cfg = app_env.config.load_safe()
    assert display_name(cfg) == "Devin"
    assert secret_env(cfg) == "DEVIN_API_KEY"
    assert credentials_present(cfg) is True
    cfg = dataclasses.replace(cfg, ai_provider="openrouter")
    assert display_name(cfg) == "OpenRouter"
    assert secret_env(cfg) == "OPENROUTER_API_KEY"
    assert credentials_present(cfg) is True


def test_kein_alter_anbieter_ist_registriert():
    """Die alte Backend-Wahl existiert nicht mehr als Config-Feld."""
    from app import config

    felder = {f.name for f in config.Config.__dataclass_fields__.values()}
    assert config.Config.ai_provider == "devin"
    for alt in ("llm_backend", "model_text", "model_stark", "model_vision"):
        assert alt not in felder, alt


def test_keine_alten_schluessel_werden_gelesen():
    """Kein Modul liest mehr die alten Zugangsdaten."""
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
    """Kein stiller Fallback: fehlt der Schlüssel, scheitert der Aufruf mit
    einer Meldung, die Variable und Ausweg nennt."""
    from app.ai import AIClient, AISetupError

    app_env.db.init()
    monkeypatch.delenv("DEVIN_API_KEY")
    with pytest.raises(AISetupError, match="DEVIN_API_KEY"):
        AIClient.from_config(app_env.config.load_safe()).complete(
            purpose="probe", prompt="x", schema=SCHEMA)


# --------------------------------------------------------------------------
# Forbidden Imports: Domain-Code kennt keine Anbieter
# --------------------------------------------------------------------------

def test_domain_code_importiert_keine_adapter():
    """Anbieter-Namen, -URLs und -Protokolle bleiben in app/ai/."""
    verboten = ("DevinProvider", "OpenRouterProvider", "ClaudeClient",
                "OpenAI", "Anthropic", "api.devin.ai", "openrouter.ai",
                "structured_output_schema", "chat/completions")
    treffer = []
    for pfad in APP.rglob("*.py"):
        if "app/ai/" in str(pfad):
            continue
        for nr, zeile in enumerate(pfad.read_text().splitlines(), 1):
            for wort in verboten:
                if wort in zeile:
                    treffer.append(f"{pfad.relative_to(APP)}:{nr}: {wort}")
    assert not treffer, "Providerwissen im Domain-Code:\n" + "\n".join(treffer)


def test_kein_ai_netzwerk_ausserhalb_der_adapter():
    """HTTP für KI-Anbieter geht nur durch app/ai/."""
    erlaubt = {
        # fachlich getrennter Dienst — eigene Verantwortung, kein AIClient
        APP / "adaptiv" / "curriculum_dienst.py",
    }
    treffer = []
    for pfad in APP.rglob("*.py"):
        if "app/ai/" in str(pfad) or pfad in erlaubt:
            continue
        quelle = pfad.read_text()
        for suchwort in ("import httpx", "import requests", "import aiohttp",
                         "urllib.request"):
            if suchwort in quelle:
                treffer.append(f"{pfad.relative_to(APP)}: {suchwort}")
    assert not treffer, "Netzwerkzugriff ausserhalb der Adapter:\n" \
        + "\n".join(treffer)


# --------------------------------------------------------------------------
# Devin-Adapter: asynchroner Lebenszyklus über das neutrale Run-Modell
# --------------------------------------------------------------------------

def test_devin_lifecycle_pending_dann_ergebnis(fake_llm, app_env):
    """start → pending → poll → completed — identischer Aufruf findet den
    Lauf wieder statt eine zweite Session anzulegen."""
    from app.ai import AIClient, AIPending

    app_env.db.init()
    fake_llm.devin.working_once = True   # Session braucht — fertig ist Ausnahme
    fake_llm.responses["verify_ping"] = {"ok": True}
    client = AIClient.from_config(app_env.config.load_safe())

    with pytest.raises(AIPending):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)
    row = app_env.db.q1("SELECT * FROM ai_run")
    assert row["run_id"] == "dev-test-1"
    assert row["provider"] == "devin"
    assert row["status"] in ("pending", "running")

    ergebnis = client.complete(purpose="probe", prompt="Aufgabe",
                               schema=SCHEMA)
    assert ergebnis.data == {"ok": True}
    assert len(fake_llm.devin.created) == 1        # keine zweite Session
    assert app_env.db.q1("SELECT status FROM ai_run")["status"] == "completed"


def test_devin_laufende_session_erzeugt_kein_duplikat(fake_llm, app_env):
    from app.ai import AIClient, AIPending

    app_env.db.init()
    fake_llm.devin.working_once = True
    client = AIClient.from_config(app_env.config.load_safe())
    with pytest.raises(AIPending):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)
    sid = next(iter(fake_llm.devin.sessions))
    fake_llm.devin.sessions[sid]["status_enum"] = "running"
    with pytest.raises(AIPending):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)
    assert len(fake_llm.devin.sessions) == 1


def test_devin_blockierte_session_wird_einmal_nachgefasst(fake_llm, app_env):
    from app.ai import AIClient, AIPending, AIError
    import json

    app_env.db.init()
    fake_llm.devin.working_once = True
    client = AIClient.from_config(app_env.config.load_safe())
    with pytest.raises(AIPending):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)
    sid = next(iter(fake_llm.devin.sessions))
    fake_llm.devin.sessions[sid]["status_enum"] = "blocked"
    fake_llm.devin.sessions[sid]["structured_output"] = None
    with pytest.raises(AIPending):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)
    row = app_env.db.q1("SELECT meta FROM ai_run")
    assert json.loads(row["meta"])["nudged"] is True
    # Zweimal blockiert heisst aufgeben.
    fake_llm.devin.sessions[sid]["status_enum"] = "blocked"
    with pytest.raises(AIError):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)


def test_devin_abgelaufene_session_wird_begrenzt_neu_gestartet(
        fake_llm, app_env):
    from app.ai import AIClient, AIPending, AIError

    app_env.db.init()
    fake_llm.devin.working_once = True
    client = AIClient.from_config(app_env.config.load_safe())
    with pytest.raises(AIPending):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)
    sid = next(iter(fake_llm.devin.sessions))
    fake_llm.devin.sessions[sid]["status_enum"] = "expired"
    # Erster Neustart ist erlaubt.
    with pytest.raises(AIPending):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)
    assert len(fake_llm.devin.sessions) == 2
    assert app_env.db.q1("SELECT restarts FROM ai_run")["restarts"] == 1
    # Zweite Leiche nicht mehr — das Restart-Limit greift.
    neu = [s for s in fake_llm.devin.sessions.values()][-1]
    neu["status_enum"] = "expired"
    with pytest.raises(AIError):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)


def test_devin_404_poll_startet_begrenzt_neu(fake_llm, app_env):
    """Die lokale Zeile kennt die Session, Devin nicht mehr: missing_remote
    ist ein Neustart, kein Auftrags-Fail — und er bleibt begrenzt."""
    from app.ai import AIClient, AIPending, AIError

    app_env.db.init()
    fake_llm.devin.working_once = True
    client = AIClient.from_config(app_env.config.load_safe())
    with pytest.raises(AIPending):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)
    sid = next(iter(fake_llm.devin.sessions))
    del fake_llm.devin.sessions[sid]                 # remote ist sie weg
    with pytest.raises(AIPending):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)
    assert len(fake_llm.devin.sessions) == 1         # restart, nicht Fail
    assert app_env.db.q1("SELECT restarts FROM ai_run")["restarts"] == 1

    # Die neue Session geht ebenfalls verloren — das Limit greift.
    del fake_llm.devin.sessions[next(iter(fake_llm.devin.sessions))]
    with pytest.raises(AIError):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)


def test_devin_404_restart_legt_kein_duplikat_an(fake_llm, app_env):
    """Nach missing_remote führt derselbe Auftrag zu genau einer neuen
    Session — kein zweiter Parallel-Bau."""
    from app.ai import AIClient, AIPending

    app_env.db.init()
    fake_llm.devin.working_once = True
    client = AIClient.from_config(app_env.config.load_safe())
    with pytest.raises(AIPending):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)
    del fake_llm.devin.sessions[next(iter(fake_llm.devin.sessions))]
    with pytest.raises(AIPending):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)
    neu = next(iter(fake_llm.devin.sessions))
    fake_llm.devin.sessions[neu]["status_enum"] = "working"
    with pytest.raises(AIPending):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)
    assert len(fake_llm.devin.sessions) == 1 and len(fake_llm.devin.created) == 2


def test_devin_zu_alte_session_gilt_als_fehlgeschlagen(fake_llm, app_env):
    from app.ai import AIClient, AIPending, AIError

    app_env.db.init()
    fake_llm.devin.working_once = True
    client = AIClient.from_config(app_env.config.load_safe())
    with pytest.raises(AIPending):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)
    with app_env.db.tx() as c:
        c.execute("UPDATE ai_run SET created_ts=created_ts-99999")
    with pytest.raises(AIError, match="Zeitfenster"):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)


def test_pending_parkt_den_job_statt_ihn_scheitern_zu_lassen(
        fake_llm, app_env):
    """AIPending → Deferred: der Auftrag wartet, ein Versuch wird nicht
    verbraucht und `not_before` parkt ihn sichtbar."""
    from app import jobs
    from app.ai import AIPending

    app_env.db.init()

    @jobs.handler("probe_pending")
    def _job(_payload):
        raise AIPending("Lauf läuft", wait_seconds=42)

    job_id = jobs.enqueue("probe_pending", {"x": 1})
    assert jobs.run_once() is True

    row = app_env.db.q1("SELECT * FROM job WHERE id=?", job_id)
    assert row["state"] == "wartend"
    assert row["attempts"] == 0            # kein Versuch verbraucht
    assert row["not_before"] is not None   # geparkt, nicht sofort wieder
    assert row["last_error"] is None       # Pending ist kein Fehler


# --------------------------------------------------------------------------
# OpenRouter-Adapter: synchroner Lebenszyklus, derselbe Vertrag
# --------------------------------------------------------------------------

def _openrouter_client(app_env, monkeypatch):
    from app import config
    from app.ai import AIClient

    monkeypatch.setenv("KARO_AI_OPENROUTER_MODEL", "test-modell")
    config.ops.cache_clear()
    cfg = app_env.config.load_safe()
    import dataclasses
    return AIClient.from_config(dataclasses.replace(cfg,
                                                    ai_provider="openrouter"))


def test_openrouter_antwortet_synchron(fake_llm, app_env, monkeypatch):
    """Ein synchroner Anbieter durchläuft dasselbe Run-Modell — der Aufruf
    sieht keinen Unterschied, nur kein Pending."""
    app_env.db.init()
    fake_llm.responses["verify_ping"] = {"ok": True}
    client = _openrouter_client(app_env, monkeypatch)

    ergebnis = client.complete(purpose="probe", prompt="Aufgabe",
                               schema=SCHEMA)
    assert ergebnis.data == {"ok": True}
    assert ergebnis.model == "test-modell"
    row = app_env.db.q1("SELECT * FROM ai_run")
    assert row["provider"] == "openrouter"
    assert row["status"] == "completed"


def test_openrouter_fehler_werden_uebersetzt(fake_llm, app_env, monkeypatch):
    from app.ai import AIAuthError

    app_env.db.init()
    fake_llm.fail_auth = True
    client = _openrouter_client(app_env, monkeypatch)
    with pytest.raises(AIAuthError):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)


def test_openrouter_ungueltige_ausgabe_ist_ein_fehler(
        fake_llm, app_env, monkeypatch):
    """Nicht-JSON landet als `failed`-Run in ai_run — nie als Freitext beim
    Aufrufer."""
    from app.ai import AIError

    app_env.db.init()
    fake_llm.responses["verify_ping"] = "kein json"
    client = _openrouter_client(app_env, monkeypatch)
    with pytest.raises(AIError, match="JSON-Objekt"):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)
    assert app_env.db.q1("SELECT status FROM ai_run")["status"] == "failed"


def test_openrouter_ohne_modell_klare_meldung(fake_llm, app_env, monkeypatch):
    from app import config
    from app.ai import AIClient, AISetupError
    import dataclasses

    app_env.db.init()
    monkeypatch.delenv("KARO_AI_OPENROUTER_MODEL", raising=False)
    config.ops.cache_clear()
    cfg = dataclasses.replace(app_env.config.load_safe(),
                              ai_provider="openrouter")
    with pytest.raises(AISetupError, match="Modell"):
        AIClient.from_config(cfg).complete(purpose="probe", prompt="x",
                                           schema=SCHEMA)


def test_openrouter_abgeschnittene_antwort_gilt_als_fehler(
        fake_llm, app_env, monkeypatch):
    from app.ai import AISchemaError

    app_env.db.init()
    fake_llm.responses["verify_ping"] = {"ok": True}
    fake_llm.stop_reason = "max_tokens"
    client = _openrouter_client(app_env, monkeypatch)
    with pytest.raises(AISchemaError):
        client.complete(purpose="probe", prompt="Aufgabe", schema=SCHEMA)


def test_http_fehlereinordnung_ist_einheitlich(monkeypatch, app_env):
    """401→auth, 429→rate-limited, 5xx→retryable — fuer beide Adapter."""
    import httpx

    from app.ai.base import AIAuthError, AIConnectionError
    from app.ai.http import api_request

    class _Antwort:
        def __init__(self, status):
            self.status_code = status
            self.headers = {}

        def json(self):
            return {}

    def _fake_client(status):
        class _C:
            def __init__(self, **kw):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def request(self, *a, **kw):
                return _Antwort(status)
        return _C

    monkeypatch.setattr(httpx, "Client", _fake_client(401))
    with pytest.raises(AIAuthError):
        api_request("X", "GET", "https://x", "/p")
    monkeypatch.setattr(httpx, "Client", _fake_client(429))
    with pytest.raises(AIConnectionError) as e:
        api_request("X", "GET", "https://x", "/p")
    assert e.value.rate_limited and e.value.retryable
    monkeypatch.setattr(httpx, "Client", _fake_client(503))
    with pytest.raises(AIConnectionError) as e:
        api_request("X", "GET", "https://x", "/p")
    assert e.value.retryable

    class _TO:
        def __init__(self, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def request(self, *a, **kw):
            raise httpx.TimeoutException("zu langsam")

    monkeypatch.setattr(httpx, "Client", _TO)
    with pytest.raises(AIConnectionError) as e:
        api_request("X", "GET", "https://x", "/p")
    assert e.value.retryable


# --------------------------------------------------------------------------
# Providerwechsel: gleicher Domain-Aufruf, anderer Adapter, kein Code-Diff
# --------------------------------------------------------------------------

@pytest.mark.parametrize("anbieter", ["devin", "openrouter"])
def test_materialanalyse_selbes_ergebnis_bei_beiden_anbietern(
        client, fake_llm, app_env, monkeypatch, anbieter):
    """Der wichtigste Architekturtest: dieselbe fachliche Anfrage läuft
    einmal asynchron (Sessions, geparkter Job) und einmal synchron —
    die Domain-Wirkung ist identisch."""
    import dataclasses

    from app import config
    from .test_app import einrichten
    from .test_material_paket import (MATERIAL_ANTWORT, _bild, _meta,
                                      _paket_id, _upload)
    from .conftest import run_jobs

    if anbieter == "openrouter":
        monkeypatch.setenv("KARO_AI_OPENROUTER_MODEL", "test-modell")
        config.ops.cache_clear()
        config.update(ai_provider="openrouter")

    einrichten(client, fake_llm)
    fake_llm.responses["material"] = dict(MATERIAL_ANTWORT)
    antwort = _upload(client, [("blatt.jpg", _bild(), "image/jpeg")],
                      metadaten=_meta())
    assert antwort.status_code == 200, antwort.text
    _paket_id(antwort)
    run_jobs(app_env, fake_llm)
    paket = app_env.db.q1("SELECT * FROM material_paket ORDER BY id DESC")
    assert paket["state"] == "bereit", paket["fehler"]
    if anbieter == "devin":
        assert len(fake_llm.devin.created) == 1
        assert fake_llm.devin.created[0].get("structured_output_schema")
    else:
        assert len(fake_llm.devin.completions) == 1
        assert fake_llm.devin.completions[0]["model"] == "test-modell"


# --------------------------------------------------------------------------
# Oberfläche ohne alte Wege
# --------------------------------------------------------------------------

def test_kein_bildparameter_am_anbieter():
    """Bleibt in Stein gemeisselt — siehe auch test_keine_bilder_an_modelle."""
    from app.ai.client import AIClient
    from app.ai.provider import AIProvider

    namen = set(inspect.signature(AIClient.complete).parameters)
    assert not (namen & {"image_path", "image_url", "bild_pfad",
                         "media_type"})


def test_setup_seite_zeigt_den_konfigurierten_anbieter(
        client, fake_llm, app_env):
    seite = client.get("/setup")
    assert seite.status_code == 200
    assert "DEVIN_API_KEY" in seite.text
    assert 'name="backend"' not in seite.text
    assert 'name="token"' not in seite.text
    assert 'name="api_key"' not in seite.text
