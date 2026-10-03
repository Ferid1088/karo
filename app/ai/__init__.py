"""Zugang zum KI-Anbieter — ein Vertrag, viele moegliche Anbieter.

Karo spricht ausschliesslich über `AIClient` mit einem KI-Anbieter. Welcher
Anbieter das ist, steht allein in `Config.ai_provider` und wird über die
Registry (`app.ai.registry`) aufgeloest — Domain-Code kennt keine
Anbieter-Namen, keine URLs, keine API-Zustaende.

Die Curriculum-Erzeugung läuft separat über den Lehrplan-Dienst — sie
teilt diese Schnittstelle nicht.
"""

from .base import (
    AIAuthError,
    AIConnectionError,
    AIError,
    AIPending,
    AISchemaError,
    AISetupError,
)
from .client import AIClient, AIResult, build_provider
from .provider import AIProvider
from .registry import credentials_present, display_name, secret_env
from .types import AIRequest, AIRun

__all__ = [
    "AIProvider", "AIRequest", "AIRun", "AIClient", "AIResult",
    "build_provider", "credentials_present", "display_name", "secret_env",
    "AIError", "AIAuthError", "AIConnectionError", "AISchemaError",
    "AISetupError", "AIPending",
]
