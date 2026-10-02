"""Zugang zum KI-Anbieter — ein Weg, ein Vertrag.

Karo spricht ausschliesslich über `AIClient` mit einem KI-Anbieter. Der
einzige konfigurierte Anbieter ist Devin (`api.devin.ai`, asynchron per
Session). Die Curriculum-Erzeugung läuft separat über den Lehrplan-Dienst —
sie teilt diese Schnittstelle nicht.
"""

from .base import (
    AIAuthError,
    AIConnectionError,
    AIError,
    AIPending,
    AISchemaError,
    AISetupError,
    Backend,
    RawResult,
)
from .client import AIClient, AIResult, build_backend

__all__ = [
    "Backend", "RawResult", "AIClient", "AIResult", "build_backend",
    "AIError", "AIAuthError", "AIConnectionError", "AISchemaError",
    "AISetupError", "AIPending",
]
