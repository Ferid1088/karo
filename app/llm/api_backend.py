"""Backend „API-Schluessel": direkter Aufruf der Messages-API.

Der Weg, der auch dann noch gilt, wenn Karo an andere Haushalte weitergegeben
wird. Kostet bei einem Kind rund einen Euro im Monat.
"""

from __future__ import annotations

import base64
import logging
import mimetypes
from pathlib import Path

from .base import (
    ClaudeAuthError,
    ClaudeConnectionError,
    ClaudeError,
    ClaudeSchemaError,
    RawResult,
)

log = logging.getLogger("karo.llm.api")

TOOL_NAME = "antwort"
MAX_IMAGE_BYTES = 5 * 1024 * 1024
SUPPORTED_IMAGE_MIME = {"image/jpeg", "image/png", "image/gif", "image/webp"}

# Preise in USD je Million Token (Eingabe, Ausgabe), Stand September 2026.
# Nur fuer die Schaetzung im Protokoll; unbekanntes Modell => None.
PRICES = {"opus": (5.0, 25.0), "sonnet": (2.0, 10.0), "haiku": (1.0, 5.0)}
_PRICE_ORDER = ("opus", "sonnet", "haiku")


def estimate_cost(model: str, tin: int, tout: int) -> float | None:
    name = (model or "").lower()
    for key in _PRICE_ORDER:
        if key in name:
            pin, pout = PRICES[key]
            return round(tin / 1_000_000 * pin + tout / 1_000_000 * pout, 6)
    return None


class ApiBackend:
    """Messages-API mit Werkzeugdefinition zur Schema-Erzwingung."""

    name = "api"

    def __init__(self, api_key: str, *, timeout: float = 180.0,
                 max_retries: int = 3) -> None:
        import anthropic

        self._anthropic = anthropic
        key = (api_key or "").strip()
        if not key:
            raise ClaudeAuthError("Es ist kein API-Schlüssel hinterlegt.")
        if not key.isascii() or any(c.isspace() for c in key):
            raise ClaudeAuthError(
                "Der Schlüssel enthält Leerzeichen, Zeilenumbrüche oder "
                "Sonderzeichen. Bitte vollständig und in einem Stück einfügen."
            )
        if len(key) < 20:
            raise ClaudeAuthError("Der Schlüssel sieht unvollständig aus.")
        self._client = anthropic.Anthropic(
            api_key=key, timeout=timeout, max_retries=max_retries)

    # -- Aufrufe ------------------------------------------------------------

    def verify(self) -> str:
        modelle = self.list_models()
        if not modelle:
            raise ClaudeError("Das Konto hat keine nutzbaren Modelle.")
        model = _pick(modelle, "haiku") or modelle[0]["id"]
        try:
            self._client.messages.create(
                model=model, max_tokens=8,
                messages=[{"role": "user", "content": "Antworte mit OK."}])
        except Exception as exc:
            raise self._deuten(exc) from None
        return model

    def list_models(self) -> list[dict]:
        try:
            seite = self._client.models.list(limit=50)
        except Exception as exc:
            raise self._deuten(exc) from None
        return [{"id": m.id, "name": getattr(m, "display_name", m.id)}
                for m in seite.data]

    def call(self, prompt: str, schema: dict, *, model: str, system: str = "",
             image_path: Path | None = None, max_tokens: int = 8192,
             web_search: bool = False, web_fetch: bool = False) -> RawResult:
        if web_search or web_fetch:
            # Echte Websuche/-abruf würde ein zweites, unerzwungenes Werkzeug
            # neben dem Struktur-Werkzeug brauchen — die API erzwingt aber
            # genau eines pro Aufruf. Ohne die genaue, aktuell gültige
            # Kennung des serverseitigen Werkzeugs live gegen die API geprüft
            # zu haben, wird hier bewusst nichts geraten: eine falsche
            # Kennung würde jeden Aufruf mit einem Serverfehler abbrechen,
            # statt ehrlich "nicht möglich" zu melden. Also lieber ehrlich
            # ablehnen — research.py fällt darauf ohnehin sauber zurück.
            was = "Websuche" if web_search else "Das Abrufen von Quelleninhalten"
            raise ClaudeError(
                f"{was} wird für den API-Schlüssel-Weg noch nicht "
                "unterstützt. Karo funktioniert ohne Recherche vollständig "
                "weiter.")
        inhalt: list[dict] = []
        if image_path is not None:
            inhalt.append(self._bildblock(image_path))
        inhalt.append({"type": "text", "text": prompt})

        try:
            msg = self._client.messages.create(
                model=model, max_tokens=max_tokens, system=system or "",
                tools=[{"name": TOOL_NAME,
                        "description": "Gib das Ergebnis in genau dieser Struktur zurück.",
                        "input_schema": schema}],
                tool_choice={"type": "tool", "name": TOOL_NAME},
                messages=[{"role": "user", "content": inhalt}],
            )
        except Exception as exc:
            raise self._deuten(exc) from None

        nutzdaten = next((b.input for b in msg.content
                          if getattr(b, "type", "") == "tool_use"), None)
        if nutzdaten is None:
            raise ClaudeSchemaError(
                "Das Modell hat keine strukturierte Antwort geliefert. "
                "Der Vorgang wurde nicht gespeichert.")

        tin, tout = msg.usage.input_tokens, msg.usage.output_tokens
        return RawResult(
            data=nutzdaten, model=model, tokens_in=tin, tokens_out=tout,
            cost_usd=estimate_cost(model, tin, tout),
            truncated=getattr(msg, "stop_reason", None) == "max_tokens",
        )

    # -- intern -------------------------------------------------------------

    @staticmethod
    def _bildblock(path: Path) -> dict:
        if not path.is_file():
            raise ClaudeError(f"Die Bilddatei {path.name} wurde nicht gefunden.")
        groesse = path.stat().st_size
        if groesse > MAX_IMAGE_BYTES:
            raise ClaudeError(
                f"Das Bild {path.name} ist mit {groesse // 1024} KB zu groß.")
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        if mime not in SUPPORTED_IMAGE_MIME:
            raise ClaudeError(f"Bildformat {mime} wird nicht unterstützt.")
        return {"type": "image",
                "source": {"type": "base64", "media_type": mime,
                           "data": base64.standard_b64encode(
                               path.read_bytes()).decode("ascii")}}

    def _deuten(self, exc: Exception) -> ClaudeError:
        from ..security import redact

        a = self._anthropic
        if isinstance(exc, a.AuthenticationError):
            return ClaudeAuthError(
                "Der API-Schlüssel wurde von Anthropic abgelehnt. Bitte prüfen, "
                "ob er vollständig kopiert wurde und noch gültig ist.")
        if isinstance(exc, a.PermissionDeniedError):
            return ClaudeAuthError(
                "Der Schlüssel ist gültig, hat aber keine Berechtigung für "
                "dieses Modell.")
        if isinstance(exc, a.RateLimitError):
            return ClaudeConnectionError(
                "Anthropic hat wegen zu vieler Anfragen abgelehnt. In ein paar "
                "Minuten erneut versuchen.")
        if isinstance(exc, a.NotFoundError):
            return ClaudeError(
                "Das eingestellte Modell existiert nicht oder ist für dieses "
                "Konto nicht freigeschaltet.")
        if isinstance(exc, a.BadRequestError):
            return ClaudeError("Anthropic hat die Anfrage abgelehnt: "
                               + redact(str(getattr(exc, "message", exc)))[:300])
        if isinstance(exc, (a.APIConnectionError, a.APITimeoutError)):
            return ClaudeConnectionError(
                "Keine Verbindung zu Anthropic. Besteht eine Internetverbindung?")
        if isinstance(exc, a.APIStatusError):
            return ClaudeConnectionError(
                f"Anthropic antwortete mit Status {exc.status_code}.")
        return ClaudeError(redact(str(exc))[:300] or "Unbekannter Fehler.")


def _pick(modelle: list[dict], teil: str) -> str:
    for m in modelle:
        if teil in m["id"].lower():
            return m["id"]
    return ""


__all__ = ["ApiBackend", "estimate_cost", "PRICES"]
