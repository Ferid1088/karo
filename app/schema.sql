-- Karo — Datenbankschema
--
-- Alles liegt in einer Datei auf dem Rechner der Familie. Drei Grundsaetze
-- werden im Schema selbst durchgesetzt:
--
--   1. `answer_log` ist append-only. Trigger verhindern UPDATE und DELETE.
--      Eine Korrektur ist eine NEUE Zeile, die die alte ersetzt.
--   2. `topic_flag` wird nur berechnet, nie von Hand geschrieben.
--   3. Nichts wird gespeichert, was ein Mensch nicht freigegeben hat —
--      das steht in den `state`-Spalten und wird im Code erzwungen.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL
);

-- ==========================================================================
-- 1. Eingang: gescannte Blaetter
-- ==========================================================================
CREATE TABLE IF NOT EXISTS document (
    id            INTEGER PRIMARY KEY,
    sha256        TEXT NOT NULL UNIQUE,
    source_name   TEXT NOT NULL,
    stored_path   TEXT NOT NULL,
    mime          TEXT NOT NULL,
    rolle         TEXT NOT NULL DEFAULT 'wissen',  -- 'wissen' | 'bearbeitet'
    doc_type      TEXT,                 -- AB | HA | Test | KA | Buch | Loesung
    captured_on   TEXT,
    state         TEXT NOT NULL DEFAULT 'neu',
    note          TEXT,
    themenname    TEXT,      -- von der Familie vorgegebener Rahmen beim Upload
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_document_state ON document(state);

-- ==========================================================================
-- 2. Wissensbasis: was auf den Blaettern steht
-- ==========================================================================
CREATE TABLE IF NOT EXISTS kb_chunk (
    id           INTEGER PRIMARY KEY,
    document_id  INTEGER NOT NULL REFERENCES document(id),
    position     INTEGER NOT NULL,
    art          TEXT NOT NULL,     -- erklaerung | regel | beispiel | aufgabe | loesung
    titel        TEXT,
    text         TEXT NOT NULL,
    thema_hinweis TEXT,
    topic_id     INTEGER REFERENCES topic(id),
    created_at   TEXT NOT NULL,
    UNIQUE (document_id, position)
);
CREATE INDEX IF NOT EXISTS idx_kb_topic ON kb_chunk(topic_id, art);
CREATE INDEX IF NOT EXISTS idx_kb_document ON kb_chunk(document_id);

-- Volltextsuche über die Wissensbasis, damit der Lernzyklus gezielt
-- Erklärungen aus den eigenen Blättern findet.
CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts USING fts5(
    text, titel, content='kb_chunk', content_rowid='id', tokenize='unicode61'
);
CREATE TRIGGER IF NOT EXISTS kb_fts_insert AFTER INSERT ON kb_chunk BEGIN
    INSERT INTO kb_fts(rowid, text, titel) VALUES (new.id, new.text, new.titel);
END;
CREATE TRIGGER IF NOT EXISTS kb_fts_delete AFTER DELETE ON kb_chunk BEGIN
    INSERT INTO kb_fts(kb_fts, rowid, text, titel)
        VALUES ('delete', old.id, old.text, old.titel);
END;
CREATE TRIGGER IF NOT EXISTS kb_fts_update AFTER UPDATE ON kb_chunk BEGIN
    INSERT INTO kb_fts(kb_fts, rowid, text, titel)
        VALUES ('delete', old.id, old.text, old.titel);
    INSERT INTO kb_fts(rowid, text, titel) VALUES (new.id, new.text, new.titel);
END;

-- ==========================================================================
-- 3. Themen — vorgeschlagen, dann freigegeben
-- ==========================================================================
CREATE TABLE IF NOT EXISTS topic (
    id           INTEGER PRIMARY KEY,
    subject      TEXT NOT NULL,
    code         TEXT NOT NULL UNIQUE,
    label        TEXT NOT NULL,
    beschreibung TEXT,
    state        TEXT NOT NULL DEFAULT 'vorschlag',  -- vorschlag|aktiv|abgelehnt
    quelle_doc   INTEGER REFERENCES document(id),
    sort         INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_topic_state ON topic(state, sort);

-- Berechnete Flagge je Thema. Nur aus answer_log abgeleitet.
CREATE TABLE IF NOT EXISTS topic_flag (
    topic_id       INTEGER PRIMARY KEY REFERENCES topic(id),
    flag           TEXT NOT NULL,          -- weiss | rot | gelb | gruen
    antworten      INTEGER NOT NULL DEFAULT 0,
    richtig        INTEGER NOT NULL DEFAULT 0,
    haupt_fehler   TEXT,
    letzte_uebung  TEXT,
    begruendung    TEXT,
    computed_at    TEXT NOT NULL
);

-- ==========================================================================
-- 4. Fragen — aus Evaluation oder aus einer Lernrunde
-- ==========================================================================
CREATE TABLE IF NOT EXISTS quiz (
    id          INTEGER PRIMARY KEY,
    topic_id    INTEGER NOT NULL REFERENCES topic(id),
    anlass      TEXT NOT NULL,      -- evaluation | lernrunde | probe
    lesson_id   INTEGER REFERENCES lesson(id),
    round_nr    INTEGER,
    modus       TEXT NOT NULL DEFAULT 'bildschirm',  -- bildschirm | papier
    state       TEXT NOT NULL DEFAULT 'offen',  -- offen|beantwortet|ausgewertet
    blatt_pfad  TEXT,               -- gedrucktes Blatt, wenn modus=papier
    created_at  TEXT NOT NULL,
    finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_quiz_topic ON quiz(topic_id, created_at);
CREATE INDEX IF NOT EXISTS idx_quiz_state ON quiz(state);

CREATE TABLE IF NOT EXISTS question (
    id            INTEGER PRIMARY KEY,
    quiz_id       INTEGER NOT NULL REFERENCES quiz(id) ON DELETE CASCADE,
    position      INTEGER NOT NULL,
    frage         TEXT NOT NULL,
    erwartet      TEXT,
    stufe         TEXT,             -- leicht | mittel | schwer
    quelle_chunk  INTEGER REFERENCES kb_chunk(id),
    -- Vorschlag des Modells nach der Auswertung, vor der Freigabe:
    schueler_antwort TEXT,
    vorschlag_richtig INTEGER,
    vorschlag_fehler  TEXT,
    vorschlag_grund   TEXT,
    vorschlag_konf    REAL,
    auswert_call_id   INTEGER REFERENCES llm_call(id),
    UNIQUE (quiz_id, position)
);
CREATE INDEX IF NOT EXISTS idx_question_quiz ON question(quiz_id, position);

-- ==========================================================================
-- 5. Antworten — APPEND ONLY, die einzige Wahrheit über den Lernstand
-- ==========================================================================
CREATE TABLE IF NOT EXISTS answer_log (
    id            INTEGER PRIMARY KEY,
    question_id   INTEGER NOT NULL REFERENCES question(id),
    topic_id      INTEGER NOT NULL REFERENCES topic(id),
    beantwortet_am TEXT NOT NULL,
    richtig       INTEGER NOT NULL CHECK (richtig IN (0, 1)),
    fehlertyp     TEXT,
    begruendung   TEXT,
    konfidenz     REAL,
    quelle        TEXT NOT NULL CHECK (quelle IN ('llm', 'lernbegleitung')),
    modell_einig  INTEGER,
    llm_call_id   INTEGER REFERENCES llm_call(id),
    ersetzt_id    INTEGER REFERENCES answer_log(id),
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_answer_topic ON answer_log(topic_id, beantwortet_am);
CREATE INDEX IF NOT EXISTS idx_answer_question ON answer_log(question_id, id);

CREATE TRIGGER IF NOT EXISTS answer_no_update
BEFORE UPDATE ON answer_log
BEGIN
    SELECT RAISE(ABORT, 'answer_log ist append-only: UPDATE nicht erlaubt');
END;

CREATE TRIGGER IF NOT EXISTS answer_no_delete
BEFORE DELETE ON answer_log
BEGIN
    SELECT RAISE(ABORT, 'answer_log ist append-only: DELETE nicht erlaubt');
END;

-- ==========================================================================
-- 6. Lerneinheit: ein Thema, mehrere Runden bis grün
-- ==========================================================================
CREATE TABLE IF NOT EXISTS lesson (
    id          INTEGER PRIMARY KEY,
    topic_id    INTEGER NOT NULL REFERENCES topic(id),
    ausgabe     TEXT NOT NULL DEFAULT 'html',   -- html | mp4 | notebooklm
    state       TEXT NOT NULL DEFAULT 'offen',
    -- offen | material | bereit | wartet | gelernt | abgebrochen
    -- wartet: Runde ist bewertet, wartet auf Bestätigung für die nächste
    runden      INTEGER NOT NULL DEFAULT 0,
    max_runden  INTEGER NOT NULL DEFAULT 4,
    created_at  TEXT NOT NULL,
    finished_at TEXT,
    abbruch_grund TEXT,      -- für Menschen lesbar, warum state='abgebrochen' wurde
    prompt_wunsch TEXT       -- zusätzlicher Wunsch für diese Erklärungseinheit
);
CREATE INDEX IF NOT EXISTS idx_lesson_topic ON lesson(topic_id, created_at);

CREATE TABLE IF NOT EXISTS lesson_round (
    id            INTEGER PRIMARY KEY,
    lesson_id     INTEGER NOT NULL REFERENCES lesson(id) ON DELETE CASCADE,
    nr            INTEGER NOT NULL,
    stufe         TEXT NOT NULL DEFAULT 'normal',  -- normal|einfacher|ganz_einfach
    state         TEXT NOT NULL DEFAULT 'offen',
    -- offen | erstellt | geprueft | gelernt | fehler
    erklaerung    TEXT,               -- JSON: Folien und Sprechtext
    pruefung      TEXT,               -- JSON: Gegenprüfung gegen die Wissensbasis
    material_pfad TEXT,               -- HTML oder MP4 im Drive-Ordner
    quellen       TEXT,               -- JSON: benutzte kb_chunk-IDs und Links
    -- Nur bei Ausgabe notebooklm gesetzt: Pfad zu der .txt-Datei mit exakt
    -- dem Text, den Karo an NotebookLM geschickt hat (oder geschickt hätte).
    notebooklm_quelle_pfad TEXT,
    created_at    TEXT NOT NULL,
    UNIQUE (lesson_id, nr)
);

-- Zusaetzliche Ausspielung einer bereits gegengeprueften Runde mit einem
-- Gestaltungswunsch der Familie ("laenger", "mehr Beispiele", ...). Zaehlt
-- nicht als eigene Runde: keine Flagge, kein Fortschritt, kein Einfluss auf
-- max_runden. Trotzdem durchlaeuft jede Variante dieselbe Gegenpruefung wie
-- eine normale Runde, bevor sie angezeigt wird.
CREATE TABLE IF NOT EXISTS lesson_round_variant (
    id              INTEGER PRIMARY KEY,
    lesson_round_id INTEGER NOT NULL REFERENCES lesson_round(id) ON DELETE CASCADE,
    wunsch          TEXT NOT NULL,     -- Freitext der Familie, ungeprueft
    ausgabe         TEXT,              -- gewaehlte Ausgabeart, leer = wie die Runde
    state           TEXT NOT NULL DEFAULT 'offen',  -- offen | bereit | fehler
    material_pfad   TEXT,
    notebooklm_quelle_pfad TEXT,       -- wie bei lesson_round, siehe dort
    fehler          TEXT,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_variant_round ON lesson_round_variant(lesson_round_id);

-- ==========================================================================
-- 7. Recherche: Fundstellen aus dem Netz, nur nach Freigabe benutzt
-- ==========================================================================
CREATE TABLE IF NOT EXISTS research_hit (
    id          INTEGER PRIMARY KEY,
    topic_id    INTEGER NOT NULL REFERENCES topic(id),
    titel       TEXT NOT NULL,
    url         TEXT NOT NULL,
    kanal       TEXT,
    warum       TEXT,
    state       TEXT NOT NULL DEFAULT 'vorschlag',
    -- vorschlag | freigegeben | abgelehnt
    -- Erst nach Freigabe geholt: der eigentliche Lerninhalt der Quelle, damit
    -- sie bei fehlendem eigenem Material auch als Faktengrundlage taugt, nicht
    -- nur als Titel-Anregung. NULL, solange nicht geholt oder das Holen scheitert.
    inhalt          TEXT,
    inhalt_geholt_am TEXT,
    created_at  TEXT NOT NULL,
    UNIQUE (topic_id, url)
);
CREATE INDEX IF NOT EXISTS idx_research_topic ON research_hit(topic_id, state);

-- ==========================================================================
-- 8. Klassenarbeit und eingefrorene Prognose
-- ==========================================================================
CREATE TABLE IF NOT EXISTS exam (
    id         INTEGER PRIMARY KEY,
    subject    TEXT NOT NULL,
    exam_date  TEXT NOT NULL,
    titel      TEXT,
    themen     TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prediction (
    id         INTEGER PRIMARY KEY,
    exam_id    INTEGER NOT NULL REFERENCES exam(id) ON DELETE CASCADE,
    topic_id   INTEGER NOT NULL REFERENCES topic(id),
    prognose   TEXT NOT NULL,
    tatsaechlich TEXT,
    frozen_at  TEXT NOT NULL,
    UNIQUE (exam_id, topic_id)
);

-- ==========================================================================
-- 9. Protokoll jedes Modellaufrufs
-- ==========================================================================
CREATE TABLE IF NOT EXISTS llm_call (
    id           INTEGER PRIMARY KEY,
    purpose      TEXT NOT NULL,
    backend      TEXT,
    model        TEXT,
    prompt       TEXT NOT NULL,
    had_image    INTEGER NOT NULL DEFAULT 0,
    response_raw TEXT,
    schema_ok    INTEGER NOT NULL DEFAULT 0,
    error        TEXT,
    tokens_in    INTEGER,
    tokens_out   INTEGER,
    cost_usd     REAL,
    duration_ms  INTEGER,
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_llm_created ON llm_call(created_at);

-- ==========================================================================
-- 10. Jobs
-- ==========================================================================
CREATE TABLE IF NOT EXISTS job (
    id          INTEGER PRIMARY KEY,
    type        TEXT NOT NULL,
    payload     TEXT NOT NULL DEFAULT '{}',
    state       TEXT NOT NULL DEFAULT 'wartend',
    attempts    INTEGER NOT NULL DEFAULT 0,
    last_error  TEXT,
    dedup_key   TEXT UNIQUE,
    not_before  TEXT,
    created_at  TEXT NOT NULL,
    started_at  TEXT,
    finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_job_state ON job(state, not_before, id);
