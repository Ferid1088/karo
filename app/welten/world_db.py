"""Separate SQLite database for private "Meine Welt" data.

This module intentionally does not import app.db. Personal memories, photos/audio
metadata and time capsules must not be mixed with the learning database.
"""
from __future__ import annotations

import datetime as dt
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from zoneinfo import ZoneInfo

from .. import config

BERLIN = ZoneInfo("Europe/Berlin")
_local = threading.local()


def private_dir() -> Path:
    path = config.DATA_DIR / "meine-welt-private"
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass
    return path


def db_path() -> Path:
    return private_dir() / "world.sqlite3"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def today() -> str:
    return dt.datetime.now(BERLIN).date().isoformat()


def _connect() -> sqlite3.Connection:
    path = db_path()
    conn_ = sqlite3.connect(
        str(path),
        timeout=30.0,
        isolation_level=None,
        check_same_thread=False,
    )
    conn_.row_factory = sqlite3.Row
    conn_.execute("PRAGMA journal_mode=WAL")
    conn_.execute("PRAGMA foreign_keys=ON")
    conn_.execute("PRAGMA recursive_triggers=ON")
    conn_.execute("PRAGMA busy_timeout=30000")
    conn_.execute("PRAGMA synchronous=FULL")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return conn_


def conn() -> sqlite3.Connection:
    current = getattr(_local, "conn", None)
    if current is None:
        current = _connect()
        _local.conn = current
    return current


def discard_connection() -> None:
    current = getattr(_local, "conn", None)
    _local.conn = None
    if current is not None:
        try:
            current.close()
        except sqlite3.Error:
            pass


@contextmanager
def tx():
    current = conn()
    if current.in_transaction:
        raise RuntimeError("Nested Meine-Welt transaction is not allowed.")
    current.execute("BEGIN IMMEDIATE")
    try:
        yield current
    except BaseException:
        try:
            if current.in_transaction:
                current.execute("ROLLBACK")
        except sqlite3.Error:
            discard_connection()
        raise
    else:
        try:
            current.execute("COMMIT")
        except sqlite3.Error:
            discard_connection()
            raise


def init() -> None:
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    conn().executescript(schema)


def q(sql: str, *params) -> list[sqlite3.Row]:
    return conn().execute(sql, params).fetchall()


def q1(sql: str, *params) -> sqlite3.Row | None:
    return conn().execute(sql, params).fetchone()
