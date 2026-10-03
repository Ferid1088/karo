"""OpenRouter als synchroner KI-Anbieter.

Chat-Completions-Vertrag (`openrouter.ai/api/v1/chat/completions`): eine
Anfrage, eine Antwort — `start()` liefert deshalb direkt einen
`STATUS_COMPLETED`-Run (oder wirft), `poll()` hat nichts zu tun.

Das JSON-Schema geht als `response_format: json_schema` mit; lehnt das
gewählte Modell das ab, fällt der Adapter auf die Schemavorgabe im Prompt
zurück — die lokale Prüfung in `AIClient` bleibt in beiden Fällen Pflicht.

Der Schlüssel kommt nur aus `OPENROUTER_API_KEY`.
"""
from __future__ import annotations

import json
import logging
import os

from ... import config
from ..base import AIError, AISetupError
from ..http import api_request
from ..types import AIRequest, AIRun, STATUS_COMPLETED, STATUS_FAILED

log = logging.getLogger("karo.ai.openrouter")

_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider:
    """Adapter für `openrouter.ai` — Chat-Completions, synchron."""

    name = "openrouter"
    display_name = "OpenRouter"
    secret_env = "OPENROUTER_API_KEY"

    def __init__(self, timeout: float | None = None) -> None:
        ops = config.ops()
        self.base_url = (ops.ai_openrouter_base_url or _BASE_URL).rstrip("/")
        self.model = ops.ai_openrouter_model
        self.poll_seconds = ops.ai_poll_seconds
        self.timeout_s = timeout if timeout is not None \
            else ops.ai_http_timeout_seconds
        self._key: str | None = None

    def _api(self, method: str, path: str, payload: dict | None = None) -> dict:
        if self._key is None:
            self._key = os.environ.get(self.secret_env)
            if not self._key:
                raise AISetupError(
                    f"{self.secret_env} fehlt: als Umgebungsvariable setzen "
                    "(siehe .env.example).")
        return api_request(self.display_name, method, self.base_url, path,
                           headers={"Authorization": f"Bearer {self._key}"},
                           payload=payload, timeout=self.timeout_s)

    # ------------------------------------------------------------- Schnittstelle
    def verify(self) -> str:
        """Zugangsprobe: Restguthaben/Kennung abrufen, keine Vervollständigung."""
        self._api("GET", "/key")
        return self.name

    def start(self, request: AIRequest) -> AIRun:
        modell = request.model or self.model
        if not modell:
            raise AISetupError(
                "Kein Modell für OpenRouter konfiguriert "
                "(ai_openrouter_model / KARO_AI_OPENROUTER_MODEL).")
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.user_prompt})
        payload: dict = {
            "model": modell,
            "messages": messages,
            "max_tokens": request.max_output_tokens,
        }
        if request.web_search:
            payload["plugins"] = [{"id": "web"}]
        if request.schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": request.purpose or "antwort",
                    "strict": True,
                    "schema": request.schema,
                },
            }
        try:
            info = self._api("POST", "/chat/completions", payload)
        except AIError as exc:
            # Nicht jedes Modell kennt response_format — dann trägt der
            # Prompt die Schemavorgabe; die lokale Prüfung bleibt Pflicht.
            if "response_format" in payload and "400" in str(exc):
                payload.pop("response_format")
                info = self._api("POST", "/chat/completions", payload)
            else:
                raise

        run = AIRun(provider=self.name,
                    run_id=str(info.get("id") or "openrouter"),
                    status=STATUS_FAILED)
        try:
            wahl = info["choices"][0]
            inhalt = wahl["message"]["content"]
        except (KeyError, IndexError, TypeError):
            run.error = "Antwort ohne choices"
            return run
        run.truncated = wahl.get("finish_reason") == "length"
        try:
            run.output = json.loads(inhalt) if isinstance(inhalt, str) else None
        except ValueError:
            run.output = None
        if not isinstance(run.output, dict):
            run.error = "Antwort ist kein JSON-Objekt"
            log.warning("ai_request_failed run_id=%s purpose=%s error=kein_json",
                        run.run_id, request.purpose)
            return run
        run.status = STATUS_COMPLETED
        usage = info.get("usage") or {}
        run.meta = {"model": info.get("model") or modell,
                    "tokens_in": usage.get("prompt_tokens") or 0,
                    "tokens_out": usage.get("completion_tokens") or 0}
        log.info("ai_request_completed run_id=%s purpose=%s",
                 run.run_id, request.purpose)
        return run

    def poll(self, run: AIRun, request: AIRequest) -> AIRun:
        """Synchron: der Lauf war bei `start()` schon fertig."""
        return run
