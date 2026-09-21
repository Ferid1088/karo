-- Adaptives Lernen — Domänenfundament (01_ARCHITECTURE.md §2, §6, §7, §8, §13).
--
-- Getrennt von `topic`/`lesson` im Kern: jene Zeilen gehören zu EINER
-- Installation und entstehen aus deren Schulblättern. Der Katalog hier ist
-- das Gegenteil davon — er wird über Kinder hinweg wiederverwendet und ist
-- deshalb über Schlüssel-Strings adressiert, nicht über lokale topic-IDs.

-- Subject → Topic → Concept (§2)
CREATE TABLE IF NOT EXISTS lern_konzept (
  id            INTEGER PRIMARY KEY,
  fach          TEXT NOT NULL,
  thema_key     TEXT NOT NULL,
  konzept_key   TEXT NOT NULL,
  label         TEXT NOT NULL,
  klasse_von    INTEGER NOT NULL DEFAULT 1,
  klasse_bis    INTEGER NOT NULL DEFAULT 13,
  created_at    TEXT NOT NULL,
  UNIQUE (fach, thema_key, konzept_key)
);

-- … → ErrorType (§2). Die Fehlvorstellung ist die Inhaltseinheit, nicht das Thema.
CREATE TABLE IF NOT EXISTS lern_fehlertyp (
  id            INTEGER PRIMARY KEY,
  konzept_id    INTEGER NOT NULL REFERENCES lern_konzept(id),
  fehler_key    TEXT NOT NULL,
  label         TEXT NOT NULL,
  beschreibung  TEXT,
  aktiv         INTEGER NOT NULL DEFAULT 1,
  created_at    TEXT NOT NULL,
  UNIQUE (konzept_id, fehler_key)
);

-- Tier 1 (§6): bekannte falsche Antworten und Schreibweisen. Reiner Abgleich,
-- kein Modell. `muster` ist immer normalisiert (siehe normalisierung.py).
CREATE TABLE IF NOT EXISTS lern_fehler_alias (
  id            INTEGER PRIMARY KEY,
  fehlertyp_id  INTEGER NOT NULL REFERENCES lern_fehlertyp(id),
  muster        TEXT NOT NULL,
  quelle        TEXT NOT NULL DEFAULT 'kuratiert',
  created_at    TEXT NOT NULL,
  UNIQUE (fehlertyp_id, muster)
);
CREATE INDEX IF NOT EXISTS idx_lern_alias_muster ON lern_fehler_alias(muster);

-- … → ExplanationVariant / VisualizationConfig / PracticeTask (§2, §4, §6).
-- Versionieren statt überschreiben: Verlierer werden archiviert, nicht gelöscht.
CREATE TABLE IF NOT EXISTS lern_erklaerung (
  id             INTEGER PRIMARY KEY,
  fehlertyp_id   INTEGER NOT NULL REFERENCES lern_fehlertyp(id),
  klasse         INTEGER NOT NULL,
  version        INTEGER NOT NULL DEFAULT 1,
  inhalt         TEXT NOT NULL,
  visualisierung TEXT,
  aufgabe        TEXT,
  schwierigkeit  INTEGER NOT NULL DEFAULT 1,
  quelle         TEXT NOT NULL DEFAULT 'kuratiert',
  geprueft_am    TEXT,
  aktiv          INTEGER NOT NULL DEFAULT 1,
  archiviert_am  TEXT,
  ausgeliefert   INTEGER NOT NULL DEFAULT 0,
  folge_erfolge  INTEGER NOT NULL DEFAULT 0,
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL,
  UNIQUE (fehlertyp_id, klasse, version)
);
CREATE INDEX IF NOT EXISTS idx_lern_erklaerung_key
  ON lern_erklaerung(fehlertyp_id, klasse, aktiv, archiviert_am);

-- … → PracticeTask (§2). Eigene Zeilen statt eines Felds in der Erklärung:
-- eine Aufgabe wird pro Rolle gebraucht (vorgerechnet, geführt, selbstständig)
-- und muss andere Zahlen haben als das Beispiel (03_INVARIANTS.md B1).
CREATE TABLE IF NOT EXISTS lern_aufgabe (
  id             INTEGER PRIMARY KEY,
  fehlertyp_id   INTEGER NOT NULL REFERENCES lern_fehlertyp(id),
  rolle          TEXT NOT NULL,
  position       INTEGER NOT NULL DEFAULT 0,
  frage          TEXT NOT NULL,
  loesung        TEXT NOT NULL,
  -- Was DIESER Fehlertyp bei DIESER Aufgabe produziert. Die Aliasliste des
  -- Fehlertyps taugt dafür nicht: sie ist auf die Diagnoseaufgabe geeicht,
  -- und "2/6" bedeutet bei 1/2+1/4 etwas anderes als bei 1/2+1/3.
  typischer_fehler TEXT,
  tipps          TEXT NOT NULL DEFAULT '[]',
  schritte       TEXT NOT NULL DEFAULT '[]',
  visualisierung TEXT,
  schwierigkeit  INTEGER NOT NULL DEFAULT 1,
  aktiv          INTEGER NOT NULL DEFAULT 1,
  created_at     TEXT NOT NULL,
  UNIQUE (fehlertyp_id, rolle, position)
);

-- Laufzeithilfe ist ein Nachschlagen (§11, 02 §5/§6): „Das habe ich nicht
-- verstanden“ je Phase und die feste FAQ. Gespeichert wie jeder andere
-- Inhalt, inklusive Prüfgatter — damit kein Kind Ungeprüftes zu sehen bekommt.
CREATE TABLE IF NOT EXISTS lern_hilfe (
  id           INTEGER PRIMARY KEY,
  konzept_id   INTEGER NOT NULL REFERENCES lern_konzept(id),
  art          TEXT NOT NULL,
  schluessel   TEXT NOT NULL,
  text         TEXT NOT NULL,
  bilder       TEXT NOT NULL DEFAULT '[]',
  sortierung   INTEGER NOT NULL DEFAULT 0,
  geprueft_am  TEXT,
  aktiv        INTEGER NOT NULL DEFAULT 1,
  created_at   TEXT NOT NULL,
  UNIQUE (konzept_id, art, schluessel)
);

-- Erstkontakt ohne Fehlersignal (§11): einmal erzeugt, für jedes Kind gleich.
CREATE TABLE IF NOT EXISTS lern_erstkontakt (
  id             INTEGER PRIMARY KEY,
  konzept_id     INTEGER NOT NULL REFERENCES lern_konzept(id),
  version        INTEGER NOT NULL DEFAULT 1,
  anker          TEXT NOT NULL,
  erste_aufgabe  TEXT NOT NULL,
  benennung      TEXT NOT NULL,
  quelle         TEXT NOT NULL DEFAULT 'kuratiert',
  geprueft_am    TEXT,
  aktiv          INTEGER NOT NULL DEFAULT 1,
  created_at     TEXT NOT NULL,
  UNIQUE (konzept_id, version)
);

-- §13: drei Eingabewege, eine normalisierte Struktur.
CREATE TABLE IF NOT EXISTS lern_eingabe (
  id           INTEGER PRIMARY KEY,
  child_key    TEXT NOT NULL DEFAULT 'installation',
  art          TEXT NOT NULL,
  fach         TEXT,
  thema_text   TEXT,
  konzept_id   INTEGER REFERENCES lern_konzept(id),
  document_id  INTEGER,
  aufgaben     TEXT NOT NULL DEFAULT '[]',
  konfidenz    REAL,
  created_at   TEXT NOT NULL
);

-- §7: ein Zustandsautomat. Der Server besitzt den Zustand, nicht der Browser,
-- und er liegt in der Datenbank — eine Cookie-Session überlebt kein Neu-Login.
CREATE TABLE IF NOT EXISTS lern_sitzung (
  id             INTEGER PRIMARY KEY,
  child_key      TEXT NOT NULL DEFAULT 'installation',
  eingabe_id     INTEGER REFERENCES lern_eingabe(id),
  konzept_id     INTEGER REFERENCES lern_konzept(id),
  fehlertyp_id   INTEGER REFERENCES lern_fehlertyp(id),
  erklaerung_id  INTEGER REFERENCES lern_erklaerung(id),
  zustand        TEXT NOT NULL,
  phase          TEXT,
  runden         INTEGER NOT NULL DEFAULT 0,
  versuche       INTEGER NOT NULL DEFAULT 0,
  letzte_antwort TEXT,
  daten          TEXT NOT NULL DEFAULT '{}',
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lern_sitzung_aktiv
  ON lern_sitzung(child_key, zustand, id);

-- Jeder Übergang wird festgeschrieben und ist damit prüfbar (§7, A6).
CREATE TABLE IF NOT EXISTS lern_ereignis (
  id            INTEGER PRIMARY KEY,
  sitzung_id    INTEGER NOT NULL REFERENCES lern_sitzung(id),
  von_zustand   TEXT,
  nach_zustand  TEXT,
  von_phase     TEXT,
  nach_phase    TEXT,
  anlass        TEXT NOT NULL,
  nutzdaten     TEXT NOT NULL DEFAULT '{}',
  created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lern_ereignis_sitzung ON lern_ereignis(sitzung_id, id);

-- §8: Beherrschung getrennt von erledigten Aufgaben.
CREATE TABLE IF NOT EXISTS lern_fortschritt (
  id                INTEGER PRIMARY KEY,
  child_key         TEXT NOT NULL DEFAULT 'installation',
  konzept_id        INTEGER NOT NULL REFERENCES lern_konzept(id),
  fehlertyp_id      INTEGER REFERENCES lern_fehlertyp(id),
  versuche          INTEGER NOT NULL DEFAULT 0,
  erfolge           INTEGER NOT NULL DEFAULT 0,
  wiederholungen    INTEGER NOT NULL DEFAULT 0,
  schwierigkeit     INTEGER NOT NULL DEFAULT 1,
  mastery           TEXT NOT NULL DEFAULT 'offen',
  braucht_mensch    INTEGER NOT NULL DEFAULT 0,
  letzte_aktivitaet TEXT,
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL,
  UNIQUE (child_key, konzept_id, fehlertyp_id)
);
CREATE INDEX IF NOT EXISTS idx_lern_fortschritt_kind
  ON lern_fortschritt(child_key, letzte_aktivitaet);
