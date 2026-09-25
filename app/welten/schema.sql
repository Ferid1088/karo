-- Private "Meine Welt" schema.
-- This file is applied to /data/meine-welt-private/world.sqlite3, not karo.db.

CREATE TABLE IF NOT EXISTS world_settings (
  child_key TEXT PRIMARY KEY DEFAULT 'installation' CHECK(child_key='installation'),
  enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
  age_band TEXT NOT NULL DEFAULT '10-11'
    CHECK(age_band IN ('8-9','10-11','12-13','14-15')),
  allow_photos INTEGER NOT NULL DEFAULT 1 CHECK(allow_photos IN (0,1)),
  allow_audio INTEGER NOT NULL DEFAULT 1 CHECK(allow_audio IN (0,1)),
  notice_version TEXT NOT NULL DEFAULT '',
  approved_at TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS world_entry (
  id INTEGER PRIMARY KEY,
  child_key TEXT NOT NULL DEFAULT 'installation' CHECK(child_key='installation'),
  kind TEXT NOT NULL CHECK(kind IN ('moment','reflection')),
  entry_date TEXT NOT NULL,
  prompt_id TEXT,
  mood TEXT CHECK(mood IS NULL OR mood IN ('schoen','lustig','besonders','schwierig','komisch')),
  text TEXT NOT NULL DEFAULT '' CHECK(length(text) <= 1500),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(child_key, kind, entry_date)
);
CREATE INDEX IF NOT EXISTS idx_world_entry_date
  ON world_entry(child_key, entry_date DESC);

CREATE TABLE IF NOT EXISTS world_capsule (
  id INTEGER PRIMARY KEY,
  child_key TEXT NOT NULL DEFAULT 'installation' CHECK(child_key='installation'),
  title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 80),
  text TEXT NOT NULL DEFAULT '' CHECK(length(text) <= 1500),
  opens_on TEXT NOT NULL,
  created_at TEXT NOT NULL,
  opened_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_world_capsule_open
  ON world_capsule(child_key, opens_on, id);

CREATE TABLE IF NOT EXISTS world_media (
  id INTEGER PRIMARY KEY,
  token TEXT NOT NULL UNIQUE CHECK(length(token) BETWEEN 24 AND 80),
  child_key TEXT NOT NULL DEFAULT 'installation' CHECK(child_key='installation'),
  entry_id INTEGER REFERENCES world_entry(id) ON DELETE CASCADE,
  capsule_id INTEGER REFERENCES world_capsule(id) ON DELETE CASCADE,
  media_type TEXT NOT NULL CHECK(media_type IN ('photo','audio')),
  storage_key TEXT NOT NULL UNIQUE,
  thumbnail_key TEXT,
  mime_type TEXT NOT NULL,
  byte_size INTEGER NOT NULL CHECK(byte_size > 0),
  duration_seconds INTEGER NOT NULL DEFAULT 0,
  created_date TEXT NOT NULL,
  created_at TEXT NOT NULL,
  CHECK((entry_id IS NOT NULL AND capsule_id IS NULL)
     OR (entry_id IS NULL AND capsule_id IS NOT NULL)),
  CHECK(
    (media_type='photo' AND duration_seconds=0 AND byte_size <= 2500000)
    OR
    (media_type='audio' AND duration_seconds BETWEEN 1 AND 60 AND byte_size <= 2000000)
  )
);
CREATE INDEX IF NOT EXISTS idx_world_media_day
  ON world_media(child_key, created_date, media_type);
CREATE INDEX IF NOT EXISTS idx_world_media_entry ON world_media(entry_id);
CREATE INDEX IF NOT EXISTS idx_world_media_capsule ON world_media(capsule_id);

-- The quota is enforced in the database as well as in the UI/router. Two
-- concurrent requests therefore cannot bypass it.
CREATE TRIGGER IF NOT EXISTS trg_world_photo_daily_limit
BEFORE INSERT ON world_media
WHEN NEW.media_type='photo'
BEGIN
  SELECT CASE WHEN (
    SELECT COUNT(*) FROM world_media
    WHERE child_key=NEW.child_key
      AND media_type='photo'
      AND created_date=NEW.created_date
  ) >= 2
  THEN RAISE(ABORT, 'photo_quota') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_world_audio_daily_limit
BEFORE INSERT ON world_media
WHEN NEW.media_type='audio'
BEGIN
  SELECT CASE WHEN (
    SELECT COALESCE(SUM(duration_seconds),0) FROM world_media
    WHERE child_key=NEW.child_key
      AND media_type='audio'
      AND created_date=NEW.created_date
  ) + NEW.duration_seconds > 60
  THEN RAISE(ABORT, 'audio_quota') END;

  SELECT CASE WHEN (
    SELECT COALESCE(SUM(byte_size),0) FROM world_media
    WHERE child_key=NEW.child_key
      AND media_type='audio'
      AND created_date=NEW.created_date
  ) + NEW.byte_size > 2000000
  THEN RAISE(ABORT, 'audio_bytes_quota') END;
END;

CREATE TABLE IF NOT EXISTS world_saved_discovery (
  id INTEGER PRIMARY KEY,
  child_key TEXT NOT NULL DEFAULT 'installation' CHECK(child_key='installation'),
  article_id TEXT NOT NULL,
  title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 160),
  saved_date TEXT NOT NULL,
  saved_at TEXT NOT NULL,
  UNIQUE(child_key, article_id)
);
CREATE INDEX IF NOT EXISTS idx_world_saved_date
  ON world_saved_discovery(child_key, saved_date DESC);
