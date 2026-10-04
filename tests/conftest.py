"""Testaufbau.

Die App läuft gegen einen gefälschten KI-Anbieter und ein temporäres
Datenverzeichnis. Damit ist der komplette Weg prüfbar — Einrichtung,
Wissensbasis, Themenvorschlag, Prüfung, Lernzyklus mit Gegenprüfung — ohne
Netz und ohne Kosten.

`FakeAI` bildet die HTTP-Ebene beider Adapter nach (`app.ai.providers.*`
→ `api_request`): Devin bekommt Sessions, die beim zweiten `GET`
`finished` sind — die Suite übt den echten Lebenszyklus anlegen → parken
→ abholen. OpenRouter antwortet synchron mit einer Completion, deren
Inhalt dieselbe schema-gesteuerte Fake-Antwort ist. Welcher Provider
aktiv ist, steht wie in Produktion in `Config.ai_provider`.
"""

from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path

import pytest


class FakeAI:
    """Bildet die Anbieter-APIs auf der `api_request`-Ebene nach."""

    def __init__(self, fake):
        self.fake = fake
        self.sessions: dict[str, dict] = {}
        self.created: list[dict] = []      # alle POST /sessions-Nutzdaten
        self.completions: list[dict] = []  # alle OpenRouter-Completions
        self.counter = 0
        self.probes = 0                    # Zugangsprüfungen
        self.working_once = False          # erster GET liefert "working"

    # -- verteilt auf die beiden Anbieter ------------------------------------
    def request(self, provider: str, method: str, base_url: str, path: str, *,
                headers: dict | None = None, payload: dict | None = None,
                timeout: float = 60.0):
        from app.ai import AIAuthError, AIError

        if self.fake.fail_auth:
            raise AIAuthError(
                f"{provider} API {method} {path}: 401 — der "
                "Zugangsschlüssel wird abgelehnt.")
        if "devin" in base_url:
            return self._devin(method, path, payload)
        if "openrouter" in base_url:
            return self._openrouter(method, path, payload)
        raise AIError(f"FakeAI: unbekannter Anbieter {base_url}",
                      retryable=False)

    # -- Devin: asynchrone Sessions ------------------------------------------
    def _devin(self, method: str, path: str, payload: dict | None):
        from app.ai import AIError

        if method == "GET" and path.startswith("/sessions?"):
            self.probes += 1
            return {"sessions": []}
        if method == "POST" and path == "/sessions":
            self.counter += 1
            sid = f"dev-test-{self.counter}"
            self.created.append(dict(payload or {}))
            schema = (payload or {}).get("structured_output_schema") or {}
            self.sessions[sid] = {
                "status_enum": "working" if self.working_once else "finished",
                "structured_output": self.fake.antwort(schema),
            }
            self.fake.calls.append({"backend": "devin", "session_id": sid,
                                    "purpose": (payload or {}).get("title")})
            return {"session_id": sid}
        if method == "GET" and path.startswith("/sessions/"):
            sid = path.rsplit("/", 1)[-1]
            if sid not in self.sessions:
                # Wie die echte api_request-Einordnung: Status im Text.
                raise AIError(f"Devin API GET {path}: 404", retryable=False)
            eintrag = self.sessions[sid]
            if eintrag["status_enum"] == "working":
                # Einmal warten, dann fertig — deckt das Parken ab.
                eintrag["status_enum"] = "finished"
                return {"status_enum": "working"}
            antwort = dict(eintrag)
            if self.fake.stop_reason == "max_tokens":
                antwort["truncated"] = True
            return antwort
        if method == "POST" and path.endswith("/message"):
            sid = path.split("/")[2]
            if sid in self.sessions:
                self.sessions[sid]["status_enum"] = "finished"
            return {}
        raise AIError(f"FakeAI: unbekannter Devin-Aufruf {method} {path}",
                      retryable=False)

    # -- OpenRouter: synchrone Completions ------------------------------------
    def _openrouter(self, method: str, path: str, payload: dict | None):
        from app.ai import AIError

        if method == "GET" and path == "/key":
            self.probes += 1
            return {"data": {"limit": None}}
        if method == "POST" and path == "/chat/completions":
            self.completions.append(dict(payload or {}))
            fmt = (payload or {}).get("response_format") or {}
            schema = (fmt.get("json_schema") or {}).get("schema") or {}
            inhalt = self.fake.antwort(schema)
            self.counter += 1
            self.fake.calls.append(
                {"backend": "openrouter",
                 "session_id": f"gen-test-{self.counter}",
                 "purpose": fmt.get("json_schema", {}).get("name")})
            return {
                "id": f"gen-test-{self.counter}",
                "model": (payload or {}).get("model", "test-modell"),
                "choices": [{
                    "finish_reason": ("length" if self.fake.stop_reason
                                      == "max_tokens" else "stop"),
                    "message": {"role": "assistant",
                                "content": json.dumps(inhalt,
                                                      ensure_ascii=False)},
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20},
            }
        raise AIError(f"FakeAI: unbekannter OpenRouter-Aufruf "
                      f"{method} {path}", retryable=False)


class _FakeKI:
    """Antwortvorrat plus Merkzettel — was die Tests steuern und prüfen."""

    def __init__(self):
        self.fail_auth = False
        self.calls: list[dict] = []
        self.responses: dict = {}
        self.stop_reason = "end_turn"
        self.devin = FakeAI(self)   # historischer Name — bedient beide APIs

    def antwort(self, schema: dict):
        """Waehlt die Antwort anhand der Pflichtfelder des Schemas.

        Robuster als ein von Hand gesetzter Zweck: ein Job wie lesson_build
        macht zwei Aufrufe mit verschiedenen Schemata, und der Test soll
        nicht wissen muessen, in welcher Reihenfolge.
        """
        schluessel = schema_key(schema)
        if schluessel is None:
            return self.responses.get("_unbekannt")
        return self.responses.get(schluessel)


#: Pflichtfelder -> Name der Antwort in `fake_llm.responses`
SCHEMA_KEYS = {
    frozenset({'klasse_von', 'klasse_bis', 'sicher', 'begruendung'}): 'klassenpruefung',
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
    frozenset({"fach", "themen"}): "material",
    frozenset({"fach", "pruefungsinhalte"}): "themenblatt",
    frozenset({"ok"}): "verify_ping",
    frozenset({"erreichbar", "inhalt"}): "research_fetch",
    frozenset({"ideen"}): "welten_ideas",
    frozenset({"fach"}): "fach",
    frozenset({"konzept", "erstkontakt", "fehlertypen", "hilfe",
               "faq"}): "lektion",
}


def schema_key(schema: dict) -> str | None:
    pflicht = frozenset(schema.get("required") or [])
    return SCHEMA_KEYS.get(pflicht)


FAKE = _FakeKI()


@pytest.fixture
def fake_llm():
    """Setzt den Antwortvorrat zurück. Der Name ist historisch gewachsen —
    dahinter steht der gefälschte KI-Anbieter (beide Adapter)."""
    FAKE.fail_auth = False
    FAKE.calls.clear()
    FAKE.responses = {}
    FAKE.stop_reason = "end_turn"
    FAKE.devin.sessions.clear()
    FAKE.devin.created.clear()
    FAKE.devin.completions.clear()
    FAKE.devin.counter = 0
    FAKE.devin.probes = 0
    FAKE.devin.working_once = False
    return FAKE


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
    # Die Provider-Schlüssel — kommen aus der Umgebung, nie aus der
    # Konfigurationsdatei.
    monkeypatch.setenv("DEVIN_API_KEY", "test-devin-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    # Der Fixture-Katalog bleibt minimal: die kuratierten Slices saet
    # saee_alle() in Produktion mit — Tests, die sie brauchen, rufen
    # slices.seed() selbst (siehe test_adaptiv_slices).
    monkeypatch.setenv("KARO_CURATED_SLICES_ENABLED", "0")

    for name in [m for m in list(sys.modules) if m.startswith("app")]:
        del sys.modules[name]

    from app import config, db

    importlib.reload(config)
    importlib.reload(db)
    db._local.__dict__.clear()

    # Die HTTP-Ebene beider Adapter durch die Attrappe ersetzen — erst nach
    # dem Neuladen der Module, sonst zeigt der Patch auf tote Objekte.
    from app.ai.providers import devin as devin_mod, openrouter as or_mod
    monkeypatch.setattr(devin_mod, "api_request", FAKE.devin.request)
    monkeypatch.setattr(or_mod, "api_request", FAKE.devin.request)

    from app import main

    importlib.reload(main)

    return types.SimpleNamespace(main=main, data=daten, drive=drive,
                                 config=config, db=db)


@pytest.fixture
def alter_generator(app_env):
    """Schaltet den alten Erzeugungsweg (`/lernzyklus` → teaching.py →
    media/) ein.

    Er ist seit 01_ARCHITECTURE.md §16 standardmaessig aus, damit keine
    Themenkarte am adaptiven Loop vorbei in die Video-Erzeugung fuehrt.
    Geloescht ist er nicht — Tests, die genau ihn pruefen, holen ihn hier
    zurueck.
    """
    app_env.config.update(legacy_lesson_generation_enabled=True)
    return app_env


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

    Zurückgestellte Aufträge (`not_before` in der Zukunft — der Anbieter
    arbeitet asynchron) werden sofort wieder vorgezogen: das Parken selbst
    hat eigene Tests, hier zählt das Ergebnis.
    """
    from app import jobs

    for _ in range(limit):
        zeile = app_env.db.q1(
            "SELECT id FROM job WHERE state='wartend' ORDER BY id LIMIT 1")
        if zeile is None:
            return
        with app_env.db.tx() as c:
            c.execute("UPDATE job SET not_before=NULL WHERE state='wartend'")
        if not jobs.run_once():
            return
