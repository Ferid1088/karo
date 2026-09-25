"""Private data store for the deterministic "Meine Welt" area."""
from __future__ import annotations

import datetime as dt
import secrets
import sqlite3

from . import world_db

CHILD_KEY = "installation"
PRIVACY_NOTICE_VERSION = "1.0"
AGE_BANDS = {"8-9", "10-11", "12-13", "14-15"}
MOODS = {"schoen", "lustig", "besonders", "schwierig", "komisch"}


def init() -> None:
    world_db.init()


def settings() -> dict:
    row = world_db.q1("SELECT * FROM world_settings WHERE child_key=?", CHILD_KEY)
    if row:
        return dict(row)
    return {
        "child_key": CHILD_KEY,
        "enabled": 0,
        "age_band": "10-11",
        "allow_photos": 1,
        "allow_audio": 1,
        "notice_version": "",
        "approved_at": None,
        "updated_at": world_db.now(),
    }


def approve(age_band: str, allow_photos: bool, allow_audio: bool) -> None:
    if age_band not in AGE_BANDS:
        raise ValueError("Bitte eine Altersstufe auswählen.")
    now = world_db.now()
    with world_db.tx() as conn:
        conn.execute(
            """INSERT INTO world_settings
               (child_key,enabled,age_band,allow_photos,allow_audio,
                notice_version,approved_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(child_key) DO UPDATE SET
                 enabled=excluded.enabled,
                 age_band=excluded.age_band,
                 allow_photos=excluded.allow_photos,
                 allow_audio=excluded.allow_audio,
                 notice_version=excluded.notice_version,
                 approved_at=excluded.approved_at,
                 updated_at=excluded.updated_at""",
            (CHILD_KEY, 1, age_band, int(allow_photos), int(allow_audio),
             PRIVACY_NOTICE_VERSION, now, now),
        )


def disable() -> None:
    current = settings()
    now = world_db.now()
    with world_db.tx() as conn:
        conn.execute(
            """INSERT INTO world_settings
               (child_key,enabled,age_band,allow_photos,allow_audio,
                notice_version,approved_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(child_key) DO UPDATE SET enabled=0,updated_at=excluded.updated_at""",
            (CHILD_KEY, 0, current["age_band"], current["allow_photos"],
             current["allow_audio"], current["notice_version"],
             current["approved_at"], now),
        )


def _text(value, maximum: int, label: str, required: bool = False) -> str:
    result = str(value or "").strip()
    if len(result) > maximum:
        raise ValueError(f"{label}: höchstens {maximum} Zeichen.")
    if required and not result:
        raise ValueError(f"{label} darf nicht leer sein.")
    return result


def reflection_for_day(entry_date: str | None = None) -> dict | None:
    entry_date = entry_date or world_db.today()
    row = world_db.q1(
        "SELECT * FROM world_entry WHERE child_key=? AND kind='reflection' AND entry_date=?",
        CHILD_KEY, entry_date,
    )
    return dict(row) if row else None


def save_reflection(prompt_id: str, text: str, entry_date: str | None = None) -> int:
    prompt_id = _text(prompt_id, 80, "Frage", required=True)
    text = _text(text, 1000, "Antwort", required=True)
    entry_date = entry_date or world_db.today()
    now = world_db.now()
    with world_db.tx() as conn:
        conn.execute(
            """INSERT INTO world_entry
               (child_key,kind,entry_date,prompt_id,text,created_at,updated_at)
               VALUES (?,'reflection',?,?,?,?,?)
               ON CONFLICT(child_key,kind,entry_date) DO UPDATE SET
                 prompt_id=excluded.prompt_id,text=excluded.text,updated_at=excluded.updated_at""",
            (CHILD_KEY, entry_date, prompt_id, text, now, now),
        )
        row = conn.execute(
            "SELECT id FROM world_entry WHERE child_key=? AND kind='reflection' AND entry_date=?",
            (CHILD_KEY, entry_date),
        ).fetchone()
        return int(row["id"])


def moment_for_day(entry_date: str | None = None) -> dict | None:
    entry_date = entry_date or world_db.today()
    row = world_db.q1(
        "SELECT * FROM world_entry WHERE child_key=? AND kind='moment' AND entry_date=?",
        CHILD_KEY, entry_date,
    )
    return dict(row) if row else None


def create_moment(mood: str | None, text: str, has_media: bool,
                  entry_date: str | None = None) -> int:
    mood = str(mood or "").strip() or None
    if mood is not None and mood not in MOODS:
        raise ValueError("Bitte ein gültiges Gefühl auswählen.")
    text = _text(text, 1500, "Text")
    if not (mood or text or has_media):
        raise ValueError("Halte mindestens eine Kleinigkeit fest.")
    entry_date = entry_date or world_db.today()
    now = world_db.now()
    try:
        with world_db.tx() as conn:
            return int(conn.execute(
                """INSERT INTO world_entry
                   (child_key,kind,entry_date,mood,text,created_at,updated_at)
                   VALUES (?,'moment',?,?,?,?,?)""",
                (CHILD_KEY, entry_date, mood, text, now, now),
            ).lastrowid)
    except sqlite3.IntegrityError as exc:
        if "UNIQUE" in str(exc):
            raise ValueError("Für heute hast du schon einen Moment festgehalten.") from None
        raise


def entry(entry_id: int) -> dict | None:
    row = world_db.q1(
        "SELECT * FROM world_entry WHERE id=? AND child_key=?", entry_id, CHILD_KEY)
    return dict(row) if row else None


def entries_for_year(year: int) -> list[dict]:
    start, end = f"{year:04d}-01-01", f"{year + 1:04d}-01-01"
    return [dict(row) for row in world_db.q(
        """SELECT * FROM world_entry
           WHERE child_key=? AND entry_date>=? AND entry_date<?
           ORDER BY entry_date DESC,id DESC""",
        CHILD_KEY, start, end,
    )]


def save_discovery(article_id: str, title: str) -> None:
    article_id = _text(article_id, 80, "Artikel", required=True)
    title = _text(title, 160, "Titel", required=True)
    today = world_db.today()
    with world_db.tx() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO world_saved_discovery
               (child_key,article_id,title,saved_date,saved_at)
               VALUES (?,?,?,?,?)""",
            (CHILD_KEY, article_id, title, today, world_db.now()),
        )


def discovery_is_saved(article_id: str) -> bool:
    return world_db.q1(
        "SELECT 1 FROM world_saved_discovery WHERE child_key=? AND article_id=?",
        CHILD_KEY, article_id,
    ) is not None


def discoveries_for_year(year: int) -> list[dict]:
    start, end = f"{year:04d}-01-01", f"{year + 1:04d}-01-01"
    return [dict(row) for row in world_db.q(
        """SELECT * FROM world_saved_discovery
           WHERE child_key=? AND saved_date>=? AND saved_date<?
           ORDER BY saved_date DESC,id DESC""",
        CHILD_KEY, start, end,
    )]


def create_capsule(title: str, text: str, opens_on: str, has_media: bool) -> int:
    title = _text(title, 80, "Titel", required=True)
    text = _text(text, 1500, "Text")
    if not text and not has_media:
        raise ValueError("Die Zeitkapsel braucht einen Text, ein Foto oder eine Aufnahme.")
    try:
        target = dt.date.fromisoformat(str(opens_on))
    except ValueError:
        raise ValueError("Bitte ein gültiges Öffnungsdatum wählen.") from None
    today = dt.date.fromisoformat(world_db.today())
    if target <= today:
        raise ValueError("Die Zeitkapsel muss sich in der Zukunft öffnen.")
    if target > today + dt.timedelta(days=366 * 5):
        raise ValueError("Das Öffnungsdatum darf höchstens fünf Jahre in der Zukunft liegen.")
    with world_db.tx() as conn:
        return int(conn.execute(
            """INSERT INTO world_capsule(child_key,title,text,opens_on,created_at)
               VALUES (?,?,?,?,?)""",
            (CHILD_KEY, title, text, target.isoformat(), world_db.now()),
        ).lastrowid)


def capsule(capsule_id: int) -> dict | None:
    row = world_db.q1(
        "SELECT * FROM world_capsule WHERE id=? AND child_key=?",
        capsule_id, CHILD_KEY,
    )
    return dict(row) if row else None


def capsules() -> list[dict]:
    return [dict(row) for row in world_db.q(
        """SELECT * FROM world_capsule WHERE child_key=?
           ORDER BY opens_on,id""", CHILD_KEY)]


def capsule_is_open(item: dict) -> bool:
    return str(item["opens_on"]) <= world_db.today()


def mark_capsule_opened(capsule_id: int) -> None:
    item = capsule(capsule_id)
    if not item or not capsule_is_open(item) or item.get("opened_at"):
        return
    with world_db.tx() as conn:
        conn.execute(
            "UPDATE world_capsule SET opened_at=? WHERE id=? AND child_key=?",
            (world_db.now(), capsule_id, CHILD_KEY),
        )


def usage_today() -> dict:
    day = world_db.today()
    row = world_db.q1(
        """SELECT
             SUM(CASE WHEN media_type='photo' THEN 1 ELSE 0 END) AS photos,
             SUM(CASE WHEN media_type='audio' THEN duration_seconds ELSE 0 END) AS audio_seconds
           FROM world_media WHERE child_key=? AND created_date=?""",
        CHILD_KEY, day,
    )
    photos = int((row["photos"] if row else 0) or 0)
    audio = int((row["audio_seconds"] if row else 0) or 0)
    return {
        "photos": photos,
        "photos_left": max(0, 2 - photos),
        "audio_seconds": audio,
        "audio_seconds_left": max(0, 60 - audio),
    }


def add_media(*, entry_id: int | None, capsule_id: int | None, media_type: str,
              storage_key: str, thumbnail_key: str | None, mime_type: str,
              byte_size: int, duration_seconds: int = 0) -> dict:
    token = secrets.token_urlsafe(24)
    try:
        with world_db.tx() as conn:
            media_id = conn.execute(
                """INSERT INTO world_media
                   (token,child_key,entry_id,capsule_id,media_type,storage_key,
                    thumbnail_key,mime_type,byte_size,duration_seconds,created_date,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (token, CHILD_KEY, entry_id, capsule_id, media_type, storage_key,
                 thumbnail_key, mime_type, int(byte_size), int(duration_seconds),
                 world_db.today(), world_db.now()),
            ).lastrowid
    except sqlite3.IntegrityError as exc:
        message = str(exc)
        if "photo_quota" in message:
            raise ValueError("Heute sind bereits zwei Fotos gespeichert.") from None
        if "audio_quota" in message or "audio_bytes_quota" in message:
            raise ValueError("Heute ist bereits eine Minute Audio gespeichert.") from None
        raise
    return {"id": int(media_id), "token": token}


def media_by_token(token: str) -> dict | None:
    row = world_db.q1(
        """SELECT m.*,c.opens_on
           FROM world_media m
           LEFT JOIN world_capsule c ON c.id=m.capsule_id
           WHERE m.token=? AND m.child_key=?""",
        token, CHILD_KEY,
    )
    return dict(row) if row else None


def media_for_entry(entry_id: int) -> list[dict]:
    return [dict(row) for row in world_db.q(
        "SELECT * FROM world_media WHERE child_key=? AND entry_id=? ORDER BY id",
        CHILD_KEY, entry_id,
    )]


def media_for_capsule(capsule_id: int) -> list[dict]:
    return [dict(row) for row in world_db.q(
        "SELECT * FROM world_media WHERE child_key=? AND capsule_id=? ORDER BY id",
        CHILD_KEY, capsule_id,
    )]


def delete_entry(entry_id: int) -> list[dict]:
    item = entry(entry_id)
    if not item:
        return []
    media = media_for_entry(entry_id)
    with world_db.tx() as conn:
        conn.execute("DELETE FROM world_entry WHERE id=? AND child_key=?", (entry_id, CHILD_KEY))
    return media


def delete_capsule(capsule_id: int) -> list[dict]:
    item = capsule(capsule_id)
    if not item:
        return []
    media = media_for_capsule(capsule_id)
    with world_db.tx() as conn:
        conn.execute("DELETE FROM world_capsule WHERE id=? AND child_key=?", (capsule_id, CHILD_KEY))
    return media


def export_snapshot() -> dict:
    return {
        "format": "karo-meine-welt-export-v1",
        "exported_at": world_db.now(),
        "settings": settings(),
        "entries": [dict(row) for row in world_db.q(
            "SELECT * FROM world_entry WHERE child_key=? ORDER BY entry_date,id", CHILD_KEY)],
        "discoveries": [dict(row) for row in world_db.q(
            "SELECT * FROM world_saved_discovery WHERE child_key=? ORDER BY saved_date,id", CHILD_KEY)],
        "capsules": [dict(row) for row in world_db.q(
            "SELECT * FROM world_capsule WHERE child_key=? ORDER BY created_at,id", CHILD_KEY)],
        "media": [dict(row) for row in world_db.q(
            "SELECT * FROM world_media WHERE child_key=? ORDER BY created_at,id", CHILD_KEY)],
    }


def all_media() -> list[dict]:
    return [dict(row) for row in world_db.q(
        "SELECT * FROM world_media WHERE child_key=?", CHILD_KEY)]


def delete_everything() -> list[dict]:
    media = all_media()
    with world_db.tx() as conn:
        conn.execute("DELETE FROM world_media WHERE child_key=?", (CHILD_KEY,))
        conn.execute("DELETE FROM world_entry WHERE child_key=?", (CHILD_KEY,))
        conn.execute("DELETE FROM world_capsule WHERE child_key=?", (CHILD_KEY,))
        conn.execute("DELETE FROM world_saved_discovery WHERE child_key=?", (CHILD_KEY,))
        conn.execute("DELETE FROM world_settings WHERE child_key=?", (CHILD_KEY,))
    return media


# Compatibility with the retired companion concept. Shared layout code can
# continue to call this while "Meine Welt" no longer changes the Karo brand.
def current_companion():
    return None


def companion_history():
    return []


def current_interest():
    return None


def interest_history(limit=20):
    return []


FARBEN = {}
