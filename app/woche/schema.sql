-- „Meine Woche" — eigenes Schema des Begleiters.
--
-- Alle Tabellen tragen das Praefix woche_ und haben KEINEN Fremdschluessel
-- auf eine Karo-Tabelle. Der Begleiter laeuft neben Karo, nicht in Karo:
-- Themen, Flaggen, Quizze und Lernzyklus bleiben unberuehrt, und dieses
-- Schema liesse sich mit einem DROP der woche_-Tabellen rueckstandsfrei
-- entfernen.
--
-- Drei Grundsaetze, wie im Hauptschema:
--   1. `woche_ereignis` ist append-only. Trigger verhindern UPDATE und DELETE.
--      Es ist die einzige Wahrheit darueber, was passiert ist.
--   2. Alles, was die App „ueber das Kind weiss", wird aus Ereignissen
--      BERECHNET — nie im Code geraten und nie vom Modell geschrieben.
--   3. Es gibt keine Spalte fuer „nicht erledigt". Was nicht passiert ist,
--      wird nicht gespeichert, nicht gezaehlt und nicht angezeigt.

PRAGMA foreign_keys = ON;

-- ==========================================================================
-- 1. Das Kind — genau eine Zeile (id = 1)
-- ==========================================================================
CREATE TABLE IF NOT EXISTS woche_kind (
    id               INTEGER PRIMARY KEY CHECK (id = 1),
    name             TEXT NOT NULL DEFAULT '',
    klasse           INTEGER NOT NULL DEFAULT 6,
    plan_bild        TEXT,              -- Foto des Stundenplans, Pfad
    anstupser_anker  TEXT,              -- „nach dem Essen" — vom Kind gesetzt
    anstupser_aus    INTEGER NOT NULL DEFAULT 1,
    frage_index      INTEGER NOT NULL DEFAULT 0,   -- naechste Kennenlernfrage
    karo_bruecke     INTEGER NOT NULL DEFAULT 0,   -- liest Karos Themen mit
    eingerichtet_am  TEXT
);

-- ==========================================================================
-- 2. Stundenplan
-- ==========================================================================
CREATE TABLE IF NOT EXISTS woche_fach (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE,
    stunden   INTEGER NOT NULL DEFAULT 0,   -- Wochenstunden, fuer die Gewichtung
    aktiv     INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS woche_stunde (
    id       INTEGER PRIMARY KEY,
    fach_id  INTEGER NOT NULL REFERENCES woche_fach(id) ON DELETE CASCADE,
    tag      INTEGER NOT NULL CHECK (tag BETWEEN 1 AND 5),   -- 1 = Montag
    stunde   INTEGER NOT NULL DEFAULT 1,
    UNIQUE (fach_id, tag, stunde)
);
CREATE INDEX IF NOT EXISTS idx_woche_stunde_tag ON woche_stunde(tag);

-- Feste Termine ausserhalb der Schule: Training, Musik, Verein
CREATE TABLE IF NOT EXISTS woche_termin (
    id     INTEGER PRIMARY KEY,
    label  TEXT NOT NULL,
    tag    INTEGER NOT NULL CHECK (tag BETWEEN 1 AND 7),
    zeit   TEXT
);

-- ==========================================================================
-- 3. Wer hilft — mit Namen, nicht als abstrakter Knopf
-- ==========================================================================
CREATE TABLE IF NOT EXISTS woche_helfer (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    fach_id     INTEGER REFERENCES woche_fach(id) ON DELETE SET NULL,
    fester_tag  INTEGER CHECK (fester_tag BETWEEN 1 AND 7),
    feste_zeit  TEXT,
    aktiv       INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL
);

-- ==========================================================================
-- 4. „Mein Ding" — Wort, Form, eigenes Bild
-- ==========================================================================
CREATE TABLE IF NOT EXISTS woche_ding (
    id         INTEGER PRIMARY KEY,
    wort       TEXT NOT NULL,
    form       TEXT NOT NULL DEFAULT 'einfach',   -- speedrun | clip | einfach
    bild       TEXT,
    freigabe   TEXT NOT NULL DEFAULT 'offen',     -- offen | ja | nein
    aktiv      INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_woche_ding_aktiv ON woche_ding(aktiv);

-- ==========================================================================
-- 5. Zyklus — 3, 7 oder 14 Tage. Nie „Plan": ein Angebot.
-- ==========================================================================
CREATE TABLE IF NOT EXISTS woche_zyklus (
    id            INTEGER PRIMARY KEY,
    start         TEXT NOT NULL,
    ende          TEXT NOT NULL,
    fokus         TEXT,
    laenge        INTEGER NOT NULL DEFAULT 7,
    status        TEXT NOT NULL DEFAULT 'offen',   -- offen | fertig
    gefuehl       TEXT,          -- Abschluss: gut | okay | schwierig
    wunsch        TEXT,          -- genauso | mehr | leichter | anders
    still         INTEGER NOT NULL DEFAULT 0,      -- von der App hingelegt
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_woche_zyklus_status ON woche_zyklus(status, start);

-- Der Wochenanker: eine Zeile pro Fach, vom Kind, am Tag des Fachs gefragt.
CREATE TABLE IF NOT EXISTS woche_anker (
    id         INTEGER PRIMARY KEY,
    zyklus_id  INTEGER NOT NULL REFERENCES woche_zyklus(id) ON DELETE CASCADE,
    fach_id    INTEGER NOT NULL REFERENCES woche_fach(id) ON DELETE CASCADE,
    text       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (zyklus_id, fach_id)
);

-- Ein Angebot. Nicht erledigte Angebote werden nicht markiert und nicht
-- uebertragen — sie laufen mit dem Zyklus einfach aus.
CREATE TABLE IF NOT EXISTS woche_schritt (
    id           INTEGER PRIMARY KEY,
    zyklus_id    INTEGER NOT NULL REFERENCES woche_zyklus(id) ON DELETE CASCADE,
    fach_id      INTEGER REFERENCES woche_fach(id) ON DELETE SET NULL,
    titel        TEXT NOT NULL,
    einstieg     TEXT NOT NULL,          -- die Handlung unter zwei Minuten
    groesse      TEXT NOT NULL DEFAULT 'klein',   -- klein | mittel | gross
    anlass       TEXT NOT NULL DEFAULT 'normal',
    form         TEXT NOT NULL DEFAULT 'einfach', -- speedrun | clip | einfach
    verkleinert  INTEGER NOT NULL DEFAULT 0,      -- Untergrenze: max. 2
    ruht         INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_woche_schritt_zyklus ON woche_schritt(zyklus_id);

-- ==========================================================================
-- 6. Ereignisse — APPEND ONLY. Die einzige Wahrheit.
-- ==========================================================================
-- art:
--   einstieg        wert = 'gemacht' | 'nicht'
--   weiter          wert = 'ja' | 'nein'
--   rueckmeldung    wert = 'gut' | 'okay' | 'schwierig'
--   grund           wert = 'zu_schwer'|'keine_zeit'|'keine_lust'|'konzentration'
--   anpassung       wert = 'kleiner' | 'zeitpunkt' | 'kurz' | 'strategie'
--   hilfe           wert = Name des Helfers, notiz = Frage
--   notfall         wert = 'arbeit'|'abgabe'|'referat'|'anderes'
--   weglassen       wert = Fachname (bewusst weggelassen)
--   karte           wert = Thema
--   pause           wert = Anzahl Wochen
--   bestzeit        wert = Sekunden (Speedrun)
CREATE TABLE IF NOT EXISTS woche_ereignis (
    id          INTEGER PRIMARY KEY,
    zyklus_id   INTEGER REFERENCES woche_zyklus(id),
    schritt_id  INTEGER REFERENCES woche_schritt(id),
    fach_id     INTEGER REFERENCES woche_fach(id),
    tag         INTEGER,                 -- 1..7, fuer die Wochentag-Zaehler
    art         TEXT NOT NULL,
    wert        TEXT,
    notiz       TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_woche_ereignis_art ON woche_ereignis(art, created_at);
CREATE INDEX IF NOT EXISTS idx_woche_ereignis_zyklus ON woche_ereignis(zyklus_id, art);

CREATE TRIGGER IF NOT EXISTS woche_ereignis_no_update
BEFORE UPDATE ON woche_ereignis
BEGIN
    SELECT RAISE(ABORT, 'woche_ereignis ist append-only: UPDATE nicht erlaubt');
END;

CREATE TRIGGER IF NOT EXISTS woche_ereignis_no_delete
BEFORE DELETE ON woche_ereignis
BEGIN
    SELECT RAISE(ABORT, 'woche_ereignis ist append-only: DELETE nicht erlaubt');
END;

-- ==========================================================================
-- 7. „Was ich ueber dich weiss" — sichtbar, aenderbar, loeschbar
-- ==========================================================================
-- quelle='kind'   : vom Kind gesagt oder korrigiert. Wird nie ueberschrieben.
-- quelle='zaehler': aus Ereignissen berechnet. Wird bei jedem Neurechnen
--                   aktualisiert, aber niemals ueber eine Kind-Zeile.
CREATE TABLE IF NOT EXISTS woche_wissen (
    id          INTEGER PRIMARY KEY,
    schluessel  TEXT NOT NULL UNIQUE,
    symbol      TEXT NOT NULL DEFAULT '•',
    text        TEXT NOT NULL,
    quelle      TEXT NOT NULL DEFAULT 'zaehler',
    sichtbar    INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL
);

-- ==========================================================================
-- 8. Sammelkarten — eine pro verstandenem Thema, mit eigenem Bild
-- ==========================================================================
CREATE TABLE IF NOT EXISTS woche_karte (
    id         INTEGER PRIMARY KEY,
    thema      TEXT NOT NULL,
    bild       TEXT,
    created_at TEXT NOT NULL
);

-- ==========================================================================
-- 9. Pause — Aufhoeren ist eine Funktion, kein Versickern
-- ==========================================================================
CREATE TABLE IF NOT EXISTS woche_pause (
    id         INTEGER PRIMARY KEY,
    von        TEXT NOT NULL,
    bis        TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_woche_pause_bis ON woche_pause(bis);

-- ==========================================================================
-- 10. Elternseite: die drei Saetze, einzeln bestaetigt
-- ==========================================================================
CREATE TABLE IF NOT EXISTS woche_eltern_zusage (
    nr          INTEGER PRIMARY KEY CHECK (nr BETWEEN 1 AND 3),
    bestaetigt_am TEXT NOT NULL
);
