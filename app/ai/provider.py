"""Der Vertrag, den jeder Anbieter-Adapter erfüllt.

Drei Operationen statt einer — weil Anbieter asynchron arbeiten können:

- `start(request)` legt den Lauf an. Ein synchroner Anbieter darf hier
  schon `STATUS_COMPLETED` liefern; ein asynchroner liefert `STATUS_PENDING`
  oder `STATUS_RUNNING` samt `run_id`.
- `poll(run, request)` fragt den Lauf erneut ab. Der Adapter übersetzt
  seine API-Zustände in die neutralen Statuswerte und kann intern
  Heilversuche unternehmen (Nachfragen, Neustart — begrenzt und in
  `run.meta`/`run.restarts` dokumentiert).
- Fehler werden als `AIError`-Familie geworfen, nicht als Status gemeldet:
  Transportfehler sind `retryable`, Zugangsfehler und Strukturfehler nicht.
  Eine hängende Session ist dagegen kein Fehler — dann bleibt der Run
  schlicht `pending`/`running`, und `AIClient` meldet `AIPending`.
"""

from __future__ import annotations

from typing import Protocol

from .types import AIRequest, AIRun


class AIProvider(Protocol):
    """Was `AIClient` von einem Anbieter braucht."""

    #: Maschineller Schlüssel in `Config.ai_provider` und `ai_run.provider`.
    name: str
    #: Menschenlesbarer Name für die Oberfläche.
    display_name: str
    #: Name der Umgebungsvariable mit dem Zugangsschlüssel.
    secret_env: str
    #: Vorschlag, wie lange `AIPending` den Job parken soll.
    poll_seconds: int

    def verify(self) -> str:
        """Billige Zugangsprobe — kein Auftrag, kein Ergebnis. Gibt `name` zurück."""

    def start(self, request: AIRequest) -> AIRun:
        """Lauf anlegen — synchron fertig oder asynchron laufend."""

    def poll(self, run: AIRun, request: AIRequest) -> AIRun:
        """Lauf aktualisieren — denselben `AIRun` zurückgeben, mutiert."""
