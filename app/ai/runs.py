"""`ai_run` — wo Lauf-Kennungen des Anbieters gespeichert liegen.

Der Fingerabdruck eines Auftrags (Anbieter + System + Prompt + Schema) ist
der Schlüssel: derselbe Auftrag findet seinen Lauf wieder, ein geänderter
Prompt ist ein neuer Auftrag. Die Tabelle kennt nur neutrale Felder —
alles Anbieter-interne steckt im `meta`-JSON, das nur der Adapter liest.
"""
from __future__ import annotations

import hashlib
import json
import time

from .. import db
from .types import AIRun


def key(provider: str, system: str, user: str, schema: dict) -> str:
    parts = [provider, system, user, json.dumps(schema, sort_keys=True,
                                              default=str)]
    return hashlib.sha256("\x00".join(parts).encode()).hexdigest()


def get(call_key: str) -> AIRun | None:
    row = db.q1("SELECT * FROM ai_run WHERE call_key=?", call_key)
    if not row:
        return None
    row = dict(row)
    try:
        meta = json.loads(row.get("meta") or "{}")
    except ValueError:
        meta = {}
    try:
        out = json.loads(row.get("output") or "null")
    except ValueError:
        out = None
    return AIRun(provider=row["provider"], run_id=row["run_id"],
                 status=row["status"], output=out, error=row.get("detail"),
                 truncated=bool(row.get("truncated")), meta=meta,
                 restarts=int(row.get("restarts") or 0),
                 created_ts=float(row.get("created_ts") or 0.0),
                 updated_ts=float(row.get("updated_ts") or 0.0))


def save(call_key: str, run: AIRun, purpose: str) -> None:
    run.updated_ts = time.time()
    with db.tx() as c:
        c.execute(
            """INSERT INTO ai_run (call_key, provider, run_id, status, output,
                                   detail, truncated, meta, restarts, purpose,
                                   created_ts, updated_ts)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(call_key) DO UPDATE SET
                   run_id=excluded.run_id, status=excluded.status,
                   output=excluded.output, detail=excluded.detail,
                   truncated=excluded.truncated, meta=excluded.meta,
                   restarts=excluded.restarts, updated_ts=excluded.updated_ts""",
            (call_key, run.provider, run.run_id, run.status,
             json.dumps(run.output, default=str) if run.output else None,
             run.error, int(run.truncated),
             json.dumps(run.meta, default=str) or None,
             run.restarts, purpose, run.created_ts, run.updated_ts))
