"""Der Vertrag zum Sprachmodell.

Alles oberhalb dieser Datei kennt nur `complete(...)` und bekommt entweder ein
schemakonformes Objekt oder eine Ausnahme mit einer Meldung, die man einer
Person zeigen kann. Es weiss nicht, ob dahinter ein Abo oder ein API-Schluessel
steckt.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class ClaudeError(Exception):
    """Basisklasse. Die Meldung ist immer deutsch und fuer Menschen lesbar."""


class ClaudeAuthError(ClaudeError):
    """Zugangsdaten fehlen, sind falsch, abgelaufen oder ohne Guthaben."""


class ClaudeConnectionError(ClaudeError):
    """Netzwerk, Zeitueberschreitung, Ueberlastung, Ratenbegrenzung."""


class ClaudeSchemaError(ClaudeError):
    """Antwort kam an, war aber unvollstaendig oder passte nicht zum Schema."""


class ClaudeSetupError(ClaudeError):
    """Das Backend selbst ist nicht einsatzbereit (z. B. CLI nicht installiert)."""


@dataclass(frozen=True)
class RawResult:
    """Was ein Backend zurueckgibt, bevor protokolliert und geprueft wird."""

    data: dict[str, Any]
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float | None = None
    truncated: bool = False


class Backend(Protocol):
    """Ein Weg zum Modell. Genau zwei Implementierungen, siehe Nachbardateien."""

    name: str

    def verify(self) -> str:
        """Testet die Zugangsdaten mit einem echten Aufruf. Gibt das Modell zurueck."""

    def list_models(self) -> list[dict]:
        """Verfuegbare Modelle. Leere Liste, wenn das Backend das nicht anbietet."""

    def call(
        self,
        prompt: str,
        schema: dict,
        *,
        model: str,
        system: str = "",
        image_path: Path | None = None,
        max_tokens: int = 8192,
        web_search: bool = False,
        web_fetch: bool = False,
    ) -> RawResult:
        """Ein Aufruf mit erzwungener Antwortstruktur.

        `web_search`: das Modell darf echt im Netz suchen, statt nur aus dem
        Prompt zu antworten. Nur für die Recherche gedacht (siehe
        `research.py`) — nicht jedes Backend unterstützt das; ohne
        Unterstützung liefert das Modell ehrlich "nichts gefunden" statt zu
        erfinden (siehe die Anweisung in `research._suchen()`s Prompt).

        `web_fetch`: das Modell darf den Inhalt einer konkreten URL wirklich
        abrufen. Nur dafür gedacht, den Inhalt einer von einem Menschen
        bereits freigegebenen Quelle zu holen (siehe
        `research.job_research_fetch()`) — niemals für unbeaufsichtigtes
        Abrufen beliebiger URLs.
        """
