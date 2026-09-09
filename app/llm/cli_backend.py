"""Backend „Abo": die Claude-Code-CLI als Unterprozess.

Damit bezahlt das vorhandene Claude-Abo die Aufrufe — kein API-Guthaben, keine
Kreditkarte. Der Token kommt aus

    claude setup-token

und wird als CLAUDE_CODE_OAUTH_TOKEN an den Unterprozess gegeben.

Zwei Dinge, die beim Bauen Zeit kosten, wenn man sie nicht weiss:

  * `--bare` darf NICHT gesetzt werden. Dieser Modus ignoriert die
    Abo-Anmeldung und verlangt einen API-Schluessel.
  * Weil ohne `--bare` das Arbeitsverzeichnis mitgelesen wird, laeuft der
    Aufruf in einem leeren Wegwerf-Verzeichnis: keine CLAUDE.md, keine Skills,
    keine MCP-Server, die das Ergebnis beeinflussen.

Rechtlicher Hinweis, der im Setup auch angezeigt wird: Anthropic erlaubt
Dritt-Entwicklern nicht, claude.ai-Anmeldungen fuer ihre Produkte anzubieten.
Fuer die eigene Familie ist dieser Weg in Ordnung; fuer ein verkauftes Produkt
ist der API-Schluessel der vorgesehene Weg.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .base import (
    Backend,
    ClaudeAuthError,
    ClaudeConnectionError,
    ClaudeError,
    ClaudeSchemaError,
    ClaudeSetupError,
    RawResult,
)

log = logging.getLogger("karo.llm.cli")

TOOL_NAME = "antwort"
DEFAULT_TIMEOUT = 300           # die CLI startet ein Agenten-Harness, das dauert

#: Modelle, die die CLI ueber `--model` versteht. Kurznamen, damit ein
#: Versionswechsel bei Anthropic nichts kaputt macht.
CLI_MODELS = [
    {"id": "sonnet", "name": "Sonnet — stark, für Handschrift und Diagnose"},
    {"id": "haiku", "name": "Haiku — schnell und sparsam, für Texte"},
    {"id": "opus", "name": "Opus — am stärksten, langsamer"},
]


class CliBackend:
    """Ruft `claude -p` auf und liest strukturiertes JSON zurueck."""

    name = "abo"

    def __init__(self, oauth_token: str, *, timeout: int = DEFAULT_TIMEOUT,
                 binary: str = "claude") -> None:
        token = (oauth_token or "").strip()
        if not token:
            raise ClaudeAuthError("Es ist kein Abo-Token hinterlegt.")
        if not token.isascii() or any(c.isspace() for c in token):
            raise ClaudeAuthError(
                "Der Token enthält Leerzeichen, Zeilenumbrüche oder Sonderzeichen. "
                "Bitte die Ausgabe von „claude setup-token“ vollständig und in "
                "einem Stück einfügen."
            )
        self._token = token
        self._timeout = timeout
        self._binary = binary

    # -- Vorbedingungen -----------------------------------------------------

    @staticmethod
    def cli_available(binary: str = "claude") -> str | None:
        """Pfad zur CLI oder None."""
        return shutil.which(binary)

    def _require_cli(self) -> str:
        path = self.cli_available(self._binary)
        if path is None:
            raise ClaudeSetupError(
                "Die Claude-Code-CLI ist in diesem Container nicht installiert. "
                "Bitte das Image neu bauen (make up) — dabei wird sie mitinstalliert."
            )
        return path

    # -- Aufrufe ------------------------------------------------------------

    def verify(self) -> str:
        self._require_cli()
        result = self._run(
            prompt="Antworte mit ok: true.",
            schema={"type": "object",
                    "properties": {"ok": {"type": "boolean"}},
                    "required": ["ok"]},
            model="haiku",
            max_tokens=256,
            timeout=90,
        )
        return result.model

    def list_models(self) -> list[dict]:
        return list(CLI_MODELS)

    def call(self, prompt: str, schema: dict, *, model: str, system: str = "",
             image_path: Path | None = None, max_tokens: int = 8192,
             web_search: bool = False, web_fetch: bool = False) -> RawResult:
        self._require_cli()
        return self._run(prompt, schema, model=model, system=system,
                         image_path=image_path, max_tokens=max_tokens,
                         web_search=web_search, web_fetch=web_fetch)

    # -- intern -------------------------------------------------------------

    def _run(self, prompt: str, schema: dict, *, model: str, system: str = "",
             image_path: Path | None = None, max_tokens: int = 8192,
             timeout: int | None = None, web_search: bool = False,
             web_fetch: bool = False) -> RawResult:
        # Bilder gehen nicht in den Prompt, sondern werden gelesen: die CLI
        # bekommt das Read-Werkzeug und den Pfad genannt. Ohne ausdrückliche
        # Freigabe hat die CLI im Kopfmodus (-p) KEIN Werkzeug — auch keine
        # Websuche, selbst wenn der Prompt danach fragt. Das war lange
        # unbemerkt: die Recherche lief fehlerfrei durch, fand aber nie
        # etwas, weil das Modell ehrlich nichts suchen konnte.
        volltext = prompt
        werkzeuge = []
        if image_path:
            werkzeuge.append("Read")
        if web_search:
            werkzeuge.append("WebSearch")
        if web_fetch:
            werkzeuge.append("WebFetch")
        allowed = ",".join(werkzeuge)
        arbeitsverzeichnis = tempfile.mkdtemp(prefix="karo-claude-")
        try:
            if image_path is not None:
                if not image_path.is_file():
                    raise ClaudeError(f"Die Bilddatei {image_path.name} fehlt.")
                kopie = Path(arbeitsverzeichnis) / image_path.name
                kopie.write_bytes(image_path.read_bytes())
                volltext = (
                    f"Lies zuerst die Bilddatei ./{kopie.name} mit dem "
                    f"Read-Werkzeug. Dann:\n\n{prompt}"
                )

            argv = [
                self._binary, "-p", volltext,
                "--output-format", "json",
                "--json-schema", json.dumps(schema, ensure_ascii=False),
                "--model", model,
                "--permission-mode", "dontAsk",
                "--permission-prompts", "none",
                "--max-turns", "6",
            ]
            if allowed:
                argv += ["--allowedTools", allowed]
            if system:
                argv += ["--append-system-prompt", system]

            umgebung = {
                **os.environ,
                "CLAUDE_CODE_OAUTH_TOKEN": self._token,
                # Ein API-Schluessel in der Umgebung wuerde das Abo verdraengen.
                "ANTHROPIC_API_KEY": "",
                "DISABLE_TELEMETRY": "1",
                "CLAUDE_CODE_MAX_OUTPUT_TOKENS": str(max_tokens),
            }

            try:
                proc = subprocess.run(
                    argv, capture_output=True, text=True,
                    timeout=timeout or self._timeout,
                    cwd=arbeitsverzeichnis, env=umgebung, check=False,
                )
            except subprocess.TimeoutExpired:
                raise ClaudeConnectionError(
                    "Der Aufruf hat zu lange gedauert und wurde abgebrochen. "
                    "Meist hilft ein erneuter Versuch."
                ) from None
            except FileNotFoundError:
                raise ClaudeSetupError(
                    "Die Claude-Code-CLI wurde nicht gefunden."
                ) from None

            return self._parse(proc, model)
        finally:
            shutil.rmtree(arbeitsverzeichnis, ignore_errors=True)

    def _parse(self, proc: subprocess.CompletedProcess, model: str) -> RawResult:
        rohtext = (proc.stdout or "").strip()
        fehlertext = (proc.stderr or "").strip()

        if not rohtext:
            raise self._deuten(proc.returncode, fehlertext)

        try:
            hülle = json.loads(rohtext)
        except json.JSONDecodeError:
            # Die CLI schreibt Fehlschlaege im Lauf als Text auf stdout.
            raise self._deuten(proc.returncode, rohtext[:400]) from None

        if isinstance(hülle, list):                     # stream-json-Reste
            hülle = next((m for m in reversed(hülle)
                          if isinstance(m, dict) and m.get("type") == "result"), {})

        if hülle.get("is_error") or hülle.get("subtype") not in (None, "success"):
            raise self._deuten(proc.returncode,
                               str(hülle.get("result") or hülle.get("error") or ""))

        nutzdaten = hülle.get("structured_output")
        if nutzdaten is None:
            raise ClaudeSchemaError(
                "Das Modell hat keine strukturierte Antwort geliefert. "
                "Der Vorgang wurde nicht gespeichert."
            )

        verwendung = hülle.get("usage") or {}
        return RawResult(
            data=nutzdaten,
            model=hülle.get("model") or model,
            tokens_in=int(verwendung.get("input_tokens") or 0),
            tokens_out=int(verwendung.get("output_tokens") or 0),
            # Beim Abo entstehen keine Einzelkosten. Die CLI schaetzt trotzdem
            # einen Betrag; der wird nicht uebernommen, sonst stehen im
            # Protokoll Kosten, die niemand bezahlt.
            cost_usd=None,
            truncated=hülle.get("stop_reason") == "max_tokens",
        )

    @staticmethod
    def _deuten(returncode: int, text: str) -> ClaudeError:
        klein = (text or "").lower()
        if any(w in klein for w in ("oauth", "unauthorized", "authentication",
                                    "not logged in", "invalid token", "401")):
            return ClaudeAuthError(
                "Der Abo-Token wurde abgelehnt. Bitte am Rechner erneut "
                "„claude setup-token“ ausführen und den neuen Token eintragen."
            )
        if any(w in klein for w in ("rate limit", "429", "usage limit",
                                    "quota", "overloaded")):
            return ClaudeConnectionError(
                "Das Abo-Kontingent ist gerade erschöpft oder Anthropic ist "
                "überlastet. In einigen Minuten erneut versuchen."
            )
        if any(w in klein for w in ("network", "econn", "enotfound", "timeout",
                                    "getaddrinfo")):
            return ClaudeConnectionError(
                "Keine Verbindung zu Anthropic. Besteht eine Internetverbindung?"
            )
        if "model" in klein and ("not found" in klein or "unavailable" in klein):
            return ClaudeError(
                "Das eingestellte Modell ist für dieses Abo nicht verfügbar. "
                "Bitte im Setup ein anderes wählen."
            )
        return ClaudeError(
            f"Die Claude-CLI ist fehlgeschlagen (Code {returncode}). "
            + (text[:300] if text else "Keine weitere Meldung.")
        )


__all__ = ["CliBackend", "CLI_MODELS"]
