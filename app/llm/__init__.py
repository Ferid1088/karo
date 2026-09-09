"""Zugang zum Sprachmodell — zwei Wege, ein Vertrag."""

from .base import (
    Backend,
    ClaudeAuthError,
    ClaudeConnectionError,
    ClaudeError,
    ClaudeSchemaError,
    ClaudeSetupError,
    RawResult,
)
from .client import BACKENDS, ClaudeClient, LlmResult, build_backend, models_for

__all__ = [
    "Backend", "RawResult", "ClaudeClient", "LlmResult",
    "BACKENDS", "build_backend", "models_for",
    "ClaudeError", "ClaudeAuthError", "ClaudeConnectionError",
    "ClaudeSchemaError", "ClaudeSetupError",
]
