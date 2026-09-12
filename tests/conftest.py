"""Testaufbau.

Die App läuft gegen ein gefälschtes Modell und ein temporäres
Datenverzeichnis. Damit ist der komplette Weg prüfbar — Einrichtung,
Wissensbasis, Themenvorschlag, Prüfung, Lernzyklus mit Gegenprüfung — ohne
Netz und ohne Kosten.

Beide Backends werden gefälscht:
  * `api`  über ein Ersatzmodul `anthropic`
  * `abo`  über ein Ersatz-`subprocess.run`, das die Claude-CLI nachbildet
"""

from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path

import pytest

# --------------------------------------------------------------------------
# Gefälschte anthropic-Bibliothek (Backend „api")
# --------------------------------------------------------------------------

def _install_fake_anthropic() -> types.ModuleType:
    mod = types.ModuleType("anthropic")

    class APIError(Exception):
        pass

    class APIStatusError(APIError):
        def __init__(self, message="", status_code=500):
            super().__init__(message)
            self.message = message
            self.status_code = status_code

    class AuthenticationError(APIStatusError):
        pass

    class PermissionDeniedError(APIStatusError):
        pass

    class RateLimitError(APIStatusError):
        pass

    class NotFoundError(APIStatusError):
        pass

    class BadRequestError(APIStatusError):
        pass

    class APIConnectionError(APIError):
        pass

    class APITimeoutError(APIConnectionError):
        pass

    class _Model:
        def __init__(self, mid, name):
            self.id, self.display_name = mid, name

    class _Page:
        def __init__(self, data):
            self.data = data

    class _Models:
        def list(self, limit=50):
            if mod.fail_auth:
                raise AuthenticationError("bad key", 401)
            return _Page([_Model("claude-sonnet-test", "Sonnet (Test)"),
                          _Model("claude-haiku-test", "Haiku (Test)")])

    class _Block:
        def __init__(self, payload):
            self.type = "tool_use"
            self.input = payload

    class _Usage:
        input_tokens, output_tokens = 1200, 300

    class _Message:
        def __init__(self, payload, stop="end_turn"):
            self.content = [_Block(payload)] if payload is not None else []
            self.usage = _Usage()
            self.stop_reason = stop

    class _Messages:
        def create(self, model=None, max_tokens=None, system=None, tools=None,
                   tool_choice=None, messages=None):
            if mod.fail_auth:
                raise AuthenticationError("bad key", 401)
            mod.calls.append({"model": model, "messages": messages,
                              "system": system, "backend": "api"})
            schema = (tools or [{}])[0].get("input_schema") or {}
            return _Message(mod.antwort(schema), mod.stop_reason)

    class Anthropic:
        def __init__(self, api_key=None, timeout=None, max_retries=None):
            self.api_key = api_key
            self.models = _Models()
            self.messages = _Messages()

    mod.Anthropic = Anthropic
    for name, cls in [
        ("APIError", APIError), ("APIStatusError", APIStatusError),
        ("AuthenticationError", AuthenticationError),
        ("PermissionDeniedError", PermissionDeniedError),
        ("RateLimitError", RateLimitError), ("NotFoundError", NotFoundError),
        ("BadRequestError", BadRequestError),
        ("APIConnectionError", APIConnectionError),
        ("APITimeoutError", APITimeoutError),
    ]:
        setattr(mod, name, cls)

    mod.fail_auth = False
    mod.calls = []
    mod.stop_reason = "end_turn"
    mod.responses = {}

    def antwort(schema: dict):
        """Waehlt die Antwort anhand der Pflichtfelder des Schemas.

        Robuster als ein von Hand gesetzter Zweck: ein Job wie lesson_build
        macht zwei Aufrufe mit verschiedenen Schemata, und der Test soll
        nicht wissen muessen, in welcher Reihenfolge.
        """
        schluessel = schema_key(schema)
        if schluessel is None:
            return mod.responses.get("_unbekannt")
        return mod.responses.get(schluessel)

    mod.antwort = antwort
    sys.modules["anthropic"] = mod
    return mod


#: Pflichtfelder -> Name der Antwort in `fake_llm.responses`
SCHEMA_KEYS = {
    frozenset({"lesbarkeit", "dokumenttyp", "themen", "abschnitte"}): "kb",
    frozenset({"themen"}): "topics",
    frozenset({"hinweis", "fragen"}): "quiz",
    frozenset({"ergebnisse"}): "check",
    frozenset({"titel", "kernidee", "folien", "benutzte_quellen"}): "lesson",
    frozenset({"urteil", "zusammenfassung", "befunde"}): "verify",
    frozenset({"suchbegriffe", "worauf_achten"}): "search_terms",
    frozenset({"treffer"}): "search",
    frozenset({"bewertungen"}): "rank",
    frozenset({"lesbarkeit", "antworten"}): "sheet",
    frozenset({"einschaetzung", "tagesplan"}): "plan",
    frozenset({"themen", "exam_date"}): "exam_scan",
    frozenset({"ok"}): "verify_ping",
    frozenset({"erreichbar", "inhalt"}): "research_fetch",
}


def schema_key(schema: dict) -> str | None:
    pflicht = frozenset(schema.get("required") or [])
    return SCHEMA_KEYS.get(pflicht)


FAKE = _install_fake_anthropic()


@pytest.fixture
def fake_llm():
    FAKE.fail_auth = False
    FAKE.calls.clear()
    FAKE.responses = {}
    FAKE.stop_reason = "end_turn"
    return FAKE


# --------------------------------------------------------------------------
# Gefälschte Claude-CLI (Backend „abo")
# --------------------------------------------------------------------------

class FakeCli:
    """Bildet `claude -p --output-format json --json-schema ...` nach."""

    def __init__(self, fake):
        self.fake = fake
        self.aufrufe: list[list[str]] = []
        self.rueckgabe = 0
        self.stderr = ""

    def which(self, name):
        return "/usr/local/bin/claude" if name == "claude" else None

    def run(self, argv, **kwargs):
        self.aufrufe.append(list(argv))
        env = kwargs.get("env") or {}
        # Der Abo-Weg darf nie über einen API-Schlüssel laufen.
        assert not env.get("ANTHROPIC_API_KEY"), \
            "Der Abo-Weg darf keinen API-Schlüssel benutzen"
        assert env.get("CLAUDE_CODE_OAUTH_TOKEN"), "Token fehlt in der Umgebung"
        assert "--bare" not in argv, "--bare ignoriert die Abo-Anmeldung"

        if self.fake.fail_auth:
            return types.SimpleNamespace(
                returncode=1, stdout="", stderr="OAuth token invalid (401)")
        if self.rueckgabe != 0:
            return types.SimpleNamespace(
                returncode=self.rueckgabe, stdout="", stderr=self.stderr)

        self.fake.calls.append({"argv": argv, "backend": "abo"})
        schema = {}
        if "--json-schema" in argv:
            try:
                schema = json.loads(argv[argv.index("--json-schema") + 1])
            except (ValueError, IndexError, json.JSONDecodeError):
                schema = {}
        nutzdaten = self.fake.antwort(schema)
        huelle = {
            "type": "result", "subtype": "success", "is_error": False,
            "model": "claude-sonnet-test",
            "structured_output": nutzdaten,
            "usage": {"input_tokens": 900, "output_tokens": 250},
            "total_cost_usd": 0.004,
            "stop_reason": self.fake.stop_reason,
        }
        return types.SimpleNamespace(
            returncode=0, stdout=json.dumps(huelle, ensure_ascii=False),
            stderr="")


@pytest.fixture
def fake_cli(fake_llm, monkeypatch):
    from app.llm import cli_backend

    cli = FakeCli(fake_llm)
    monkeypatch.setattr(cli_backend.shutil, "which", cli.which)
    monkeypatch.setattr(cli_backend.subprocess, "run", cli.run)
    return cli


# --------------------------------------------------------------------------
# App mit temporären Verzeichnissen
# --------------------------------------------------------------------------

@pytest.fixture
def app_env(tmp_path, monkeypatch):
    daten = tmp_path / "data"
    drive = tmp_path / "drive"
    daten.mkdir()
    drive.mkdir()
    monkeypatch.setenv("KARO_DATA_DIR", str(daten))
    monkeypatch.setenv("KARO_DRIVE_DIR", str(drive))

    for name in [m for m in list(sys.modules) if m.startswith("app")]:
        del sys.modules[name]

    from app import config, db

    importlib.reload(config)
    importlib.reload(db)
    db._local.__dict__.clear()

    from app import main

    importlib.reload(main)

    return types.SimpleNamespace(main=main, data=daten, drive=drive,
                                 config=config, db=db)


@pytest.fixture
def client(app_env):
    from fastapi.testclient import TestClient

    with TestClient(app_env.main.app, base_url="http://127.0.0.1:8080") as c:
        c.headers["sec-fetch-site"] = "same-origin"
        yield c


# --------------------------------------------------------------------------
# Helfer
# --------------------------------------------------------------------------

def csrf_from(html: str) -> str:
    import re

    m = re.search(r'name="_csrf" value="([^"]+)"', html)
    assert m, "kein CSRF-Token in der Seite gefunden"
    return m.group(1)


def make_jpeg(path: Path, size=(900, 1200)) -> Path:
    from PIL import Image

    Image.new("RGB", size, (245, 245, 245)).save(path, "JPEG", quality=80)
    return path


def run_jobs(app_env, fake, limit: int = 30) -> None:
    """Arbeitet die Warteschlange ab.

    Welche Antwort ein Aufruf bekommt, entscheidet das Schema — siehe
    SCHEMA_KEYS. Der Test muss die Aufrufreihenfolge nicht kennen.
    """
    from app import jobs

    for _ in range(limit):
        zeile = app_env.db.q1(
            """SELECT id FROM job WHERE state='wartend'
                 AND (not_before IS NULL OR not_before <= ?)
                ORDER BY id LIMIT 1""", app_env.db.now())
        if zeile is None:
            return
        if not jobs.run_once():
            return
