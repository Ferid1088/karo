-- "Meine Welt": der persönliche Begleiter des Kindes (Name + Bild ersetzen
-- "Karo" im Kind-Bereich) und ein Interessen-Tagebuch. Beide sind reine
-- Verlaufs-Tabellen — nie UPDATE, nur INSERT. Die jeweils neueste Zeile ist
-- die aktuell gültige; ältere Zeilen bleiben als Verlauf erhalten.
-- Matches Karo's single configured learner. There is no second identity model.
CREATE TABLE IF NOT EXISTS begleiter_verlauf (
 id INTEGER PRIMARY KEY,
 child_key TEXT NOT NULL DEFAULT 'installation' CHECK(child_key='installation'),
 name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 40),
 foto_pfad TEXT,
 farbe TEXT NOT NULL DEFAULT 'lila' CHECK(farbe IN ('lila','ozean','wiese','sonne','zuckerwatte','lava','dunkel')),
 spass_antwort TEXT NOT NULL DEFAULT '' CHECK(length(spass_antwort)<=200),
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_begleiter_verlauf_created ON begleiter_verlauf(child_key, created_at);

CREATE TABLE IF NOT EXISTS interesse_eintrag (
 id INTEGER PRIMARY KEY,
 child_key TEXT NOT NULL DEFAULT 'installation' CHECK(child_key='installation'),
 text TEXT NOT NULL DEFAULT '' CHECK(length(text)<=300),
 audio_pfad TEXT,
 created_at TEXT NOT NULL,
 CHECK(length(text) > 0 OR audio_pfad IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_interesse_eintrag_created ON interesse_eintrag(child_key, created_at);
