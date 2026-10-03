"""Provider-neutrale Datenmodelle.

`AIRequest` ist das einzige, was Domain-Code beschreibt: ein Zweck, zwei
Prompts, ein Schema. `AIRun` ist der Lauf dieses Auftrags beim Anbieter —
mit neutralen Statuswerten, nie mit API-spezifischen Zuständen.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

#: Neutrale Statuswerte. Adapter übersetzen ihre API-Zustände hierhin;
#: Domain-Code kennt keine weiteren.
STATUS_PENDING = "pending"      # angelegt, noch nicht gelaufen
STATUS_RUNNING = "running"      # Anbieter arbeitet
STATUS_COMPLETED = "completed"  # Ergebnis liegt vor
STATUS_FAILED = "failed"        # endgültig gescheitert

LAEUFT = {STATUS_PENDING, STATUS_RUNNING}


@dataclass(frozen=True)
class AIRequest:
    """Ein fachlicher Auftrag an den KI-Anbieter — nichts Provider-spezifisches.

    `model`: optionale fachliche Auswahl (leer = Provider-/Config-Default).
    `web_search`/`web_fetch`: der Auftrag darf aus dem Netz antworten bzw.
    eine freigegebene Quelle abrufen — ob der Anbieter das kann, entscheidet
    der Adapter.
    """

    purpose: str
    user_prompt: str
    schema: dict
    system_prompt: str = ""
    max_output_tokens: int = 8_192
    model: str = ""
    web_search: bool = False
    web_fetch: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass
class AIRun:
    """Ein Lauf beim Anbieter — wird in `ai_run` persistiert.

    `meta` ist ein JSON-Kleingepäck für adapter-interne Zustände (z. B. ob
    schon einmal nachgefragt wurde). Domain-Code liest es nie.
    """

    provider: str
    run_id: str
    status: str
    output: dict | None = None
    error: str | None = None
    truncated: bool = False
    meta: dict = field(default_factory=dict)
    restarts: int = 0
    created_ts: float = field(default_factory=time.time)
    updated_ts: float = field(default_factory=time.time)

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_ts

    def to_row(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "run_id": self.run_id,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "truncated": int(self.truncated),
            "meta": dict(self.meta),
            "restarts": self.restarts,
            "created_ts": self.created_ts,
            "updated_ts": self.updated_ts,
        }
