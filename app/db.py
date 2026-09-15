"""SQLite-Zugriff.

Alle Datenbankzugriffe der App laufen ueber dieses Modul. Das ist die Stelle,
an der spaeter ein tenant_id ergaenzt oder auf PostgreSQL gewechselt wird —
und zwar nur hier.
"""

from __future__ import annotations

import datetime as dt
import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from . import config

log = logging.getLogger("karo.db")

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
SCHEMA_VERSION = 6

_local = threading.local()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def today() -> str:
    return dt.date.today().isoformat()


def _connect() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn_ = sqlite3.connect(
        str(config.DATA_DIR / "karo.db"),
        timeout=30.0,
        isolation_level=None,       # explizite Transaktionen
        check_same_thread=False,
    )
    conn_.row_factory = sqlite3.Row
    conn_.execute("PRAGMA journal_mode=WAL")
    conn_.execute("PRAGMA foreign_keys=ON")
    # Ohne recursive_triggers umgeht ein INSERT OR REPLACE den
    # BEFORE-DELETE-Trigger und koennte eine Beobachtung ueberschreiben.
    conn_.execute("PRAGMA recursive_triggers=ON")
    conn_.execute("PRAGMA busy_timeout=30000")
    conn_.execute("PRAGMA synchronous=NORMAL")
    return conn_


def conn() -> sqlite3.Connection:
    """Eine Verbindung pro Thread."""
    c = getattr(_local, "conn", None)
    if c is None:
        c = _connect()
        _local.conn = c
    return c


def _discard_connection() -> None:
    """Wirft eine Verbindung weg, die in einem unklaren Zustand steckt.

    Ohne das bleibt eine Verbindung nach einem fehlgeschlagenen ROLLBACK in
    einer offenen Transaktion, und jeder weitere Schreibversuch in diesem
    Thread scheitert bis zum Neustart."""
    c = getattr(_local, "conn", None)
    _local.conn = None
    if c is not None:
        try:
            c.close()
        except sqlite3.Error:
            pass


@contextmanager
def tx():
    """Transaktion. Verschachtelung ist nicht erlaubt und wird erkannt."""
    c = conn()
    if c.in_transaction:
        raise RuntimeError(
            "Verschachtelte Transaktion: db.tx() darf nicht innerhalb einer "
            "anderen db.tx() aufgerufen werden."
        )
    c.execute("BEGIN IMMEDIATE")
    try:
        yield c
    except BaseException:
        try:
            if c.in_transaction:
                c.execute("ROLLBACK")
        except sqlite3.Error:
            _discard_connection()
        raise
    else:
        try:
            c.execute("COMMIT")
        except sqlite3.Error:
            _discard_connection()
            raise


def init() -> None:
    c = conn()
    c.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    _migrate(c)
    row = c.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
    if row is None or row["v"] is None or row["v"] < SCHEMA_VERSION:
        with tx() as migration:
            from .services.workflow_repair import repair
            repair(migration)
            migration.execute(
                "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, now()))


# Spalten, die spaeter dazugekommen sind. CREATE TABLE IF NOT EXISTS legt sie
# in einer bestehenden Datenbank nicht an, deshalb hier einzeln nachziehen.
_ADDED_COLUMNS = [
    ("topic", "merged_into", "INTEGER REFERENCES topic(id)"),
    ("quiz", "superseded_by", "INTEGER REFERENCES quiz(id)"),
    ("quiz", "draft_revision", "INTEGER NOT NULL DEFAULT 0"),
    ("quiz", "draft_position", "INTEGER NOT NULL DEFAULT 0"),
    ("quiz", "draft_updated_at", "TEXT"),
    ("quiz", "review_draft", "TEXT NOT NULL DEFAULT '{}'"),
    ("topic", "learning_started_at", "TEXT"),
    ("topic", "learned_at", "TEXT"),
    ("document", "rolle", "TEXT NOT NULL DEFAULT 'wissen'"),
    ("llm_call", "backend", "TEXT"),
    ("job", "not_before", "TEXT"),
    ("lesson", "max_runden", "INTEGER NOT NULL DEFAULT 4"),
    ("question", "auswert_call_id", "INTEGER"),
    ("lesson_round_variant", "ausgabe", "TEXT"),
    ("lesson", "abbruch_grund", "TEXT"),
    ("lesson", "prompt_wunsch", "TEXT"),
    ("document", "themenname", "TEXT"),
    ("research_hit", "inhalt", "TEXT"),
    ("research_hit", "inhalt_geholt_am", "TEXT"),
    ("lesson_round", "notebooklm_quelle_pfad", "TEXT"),
    ("lesson_round_variant", "notebooklm_quelle_pfad", "TEXT"),
]


def _migrate(c: sqlite3.Connection) -> None:
    for table, column, decl in _ADDED_COLUMNS:
        try:
            existing = {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}
        except sqlite3.Error:
            continue
        if existing and column not in existing:
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
                log.info("Spalte %s.%s ergänzt", table, column)
            except sqlite3.Error as exc:      # pragma: no cover
                log.warning("Konnte %s.%s nicht ergänzen: %s", table, column, exc)


def q(sql: str, *params) -> list[sqlite3.Row]:
    return conn().execute(sql, params).fetchall()


def q1(sql: str, *params) -> sqlite3.Row | None:
    return conn().execute(sql, params).fetchone()


def rebuild_fts() -> int:
    """Baut den Volltextindex der Wissensbasis neu auf.

    Wird nach einer Wiederherstellung aus einer Sicherung gebraucht: der
    FTS-Index haengt an Triggern und ist in einem Schnappschuss enthalten,
    kann aber nach einem Schemawechsel veralten.
    """
    with tx() as c:
        c.execute("INSERT INTO kb_fts(kb_fts) VALUES ('rebuild')")
        row = c.execute("SELECT COUNT(*) AS n FROM kb_chunk").fetchone()
        return row["n"] if row else 0
