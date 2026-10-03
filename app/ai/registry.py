"""Provider-Auswahl — die einzige Stelle, die Namen zu Adaptern auflöst.

`Config.ai_provider` ist die einzige Wahrheit für die Wahl. Hier gibt es
keine `if provider == "devin"`-Verzweigungen, nur eine Tabelle.
"""
from __future__ import annotations

import os

from .base import AISetupError
from .provider import AIProvider
from .providers.devin import DevinProvider
from .providers.openrouter import OpenRouterProvider

#: Anbieter-Schlüssel → Adapter-Klasse. Neue Anbieter tragen hier eine Zeile
#: ein — sonst nirgendwo.
PROVIDERS: dict[str, type] = {
    "devin": DevinProvider,
    "openrouter": OpenRouterProvider,
}


def provider_class(name: str) -> type:
    cls = PROVIDERS.get(name or "")
    if cls is None:
        raise AISetupError(
            f"Unbekannter KI-Anbieter: {name!r}. Bekannt: "
            + ", ".join(sorted(PROVIDERS)))
    return cls


def build(cfg, timeout: float | None = None) -> AIProvider:
    """Adapter zum in `cfg.ai_provider` gewählten Anbieter."""
    return provider_class(getattr(cfg, "ai_provider", "") or "")(timeout=timeout)


def display_name(cfg) -> str:
    return provider_class(getattr(cfg, "ai_provider", "")).display_name


def secret_env(cfg) -> str | None:
    try:
        return provider_class(getattr(cfg, "ai_provider", "")).secret_env
    except AISetupError:
        return None


def credentials_present(cfg) -> bool:
    """Ist der Schlüssel des gewählten Anbieters in der Umgebung gesetzt?"""
    env = secret_env(cfg)
    return bool(env and os.environ.get(env))
