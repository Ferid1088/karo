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
  -- Wonach ein Kind suchen koennte. Beim Konzept, nicht in einer
  -- Tabelle daneben: eine erzeugte Lektion bringt ihre eigenen mit.
  stichworte    TEXT NOT NULL DEFAULT '[]',
  -- §11: ungeprueft erreicht kein Kind. Verfasst heisst geprueft.
  quelle        TEXT NOT NULL DEFAULT 'kuratiert',
  geprueft_am   TEXT,
  aktiv         INTEGER NOT NULL DEFAULT 1,
  created_at    TEXT NOT NULL,
  UNIQUE (fach, thema_key, konzept_key)
);

-- … → ErrorType (§2). Die Fehlvorstellung ist die Inhaltseinheit, nicht das Thema.
CREATE TABLE IF NOT EXISTS lern_curriculum_import (
  fingerprint TEXT PRIMARY KEY,
  konzept_id INTEGER NOT NULL REFERENCES lern_konzept(id),
  provenance TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lern_fehlertyp (
  id            INTEGER PRIMARY KEY,
  konzept_id    INTEGER NOT NULL REFERENCES lern_konzept(id),
  fehler_key    TEXT NOT NULL,
  label         TEXT NOT NULL,
  beschreibung  TEXT,
  quelle        TEXT NOT NULL DEFAULT 'kuratiert',
  geprueft_am   TEXT,
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
  -- B1: die Adaptation muss eine ANDERE Darstellung zeigen, nicht dieselbe
  -- noch einmal — sonst wiederholt Karo genau das, was schon nicht geholfen hat.
  visualisierung_alternativ TEXT,
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
  -- Nicht jede Aufgabe ist ein Bruch: Vorhersage und Transfer sind Auswahlen.
  antwort_art    TEXT NOT NULL DEFAULT 'bruch',
  -- Wie lange diese Aufgabe ueblicherweise dauert (Schritt 4a). Kommt aus dem
  -- Curriculum, wenn es etwas dazu sagt; sonst aus `protokoll.erwartung()`.
  -- Sie begrenzt die aktive Zeit nach oben: eine Aufgabe, die eine halbe
  -- Stunde offen stand, wurde nicht eine halbe Stunde lang bearbeitet.
  erwartete_sekunden INTEGER,
  optionen       TEXT NOT NULL DEFAULT '[]',
  aufloesung     TEXT,
  tipps          TEXT NOT NULL DEFAULT '[]',
  schritte       TEXT NOT NULL DEFAULT '[]',
  visualisierung TEXT,
  schwierigkeit  INTEGER NOT NULL DEFAULT 1,
  quelle         TEXT NOT NULL DEFAULT 'kuratiert',
  geprueft_am    TEXT,
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
  -- Bilder der Hilfe gehen denselben Weg wie alle anderen (§3). `bilder`
  -- bleibt fuer die Bruchstreifen des Pilotkapitels.
  visualisierung TEXT,
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
  -- Die einzige Stelle, an der ein lokales Thema und ein geteiltes Konzept
  -- zusammenkommen: hier hat DIESES Kind auf DIESE Themenkarte getippt.
  -- Die Inhaltstabellen bleiben bewusst frei davon (siehe Kopf der Datei).
  topic_id     INTEGER,
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

-- Schon gemeldete Erklaerungen (Z10).
--
-- Ohne diese Tabelle ginge dieselbe Meldung bei jedem Lauf erneut hinaus.
-- Gemerkt wird der Stand bei der Meldung: erst wenn weitere Einsaetze
-- dazugekommen sind, ist eine zweite Meldung eine neue Aussage.
CREATE TABLE IF NOT EXISTS lern_erklaerung_gemeldet (
    erklaerung_id INTEGER PRIMARY KEY REFERENCES lern_erklaerung(id) ON DELETE CASCADE,
    gemeldet_am   TEXT NOT NULL,
    ausgeliefert  INTEGER,
    folge_erfolge INTEGER
);

-- Voraussetzungen eines Konzepts (Vertrag 1.4, Z3).
--
-- Der Lehrplan-Dienst fuehrt sie seit jeher, Karo konnte sie nicht sehen.
-- Ohne sie blieb bei einem Kind, das haengt, nur die Eskalation — auch wenn
-- in Wahrheit nur eine Voraussetzung fehlte. Die Voraussetzung steht als
-- Konzeptschluessel des Dienstes da, nicht als lokale ID: sie kann noch
-- fehlen, wenn das Konzept selbst schon da ist.
CREATE TABLE IF NOT EXISTS lern_voraussetzung (
    id            INTEGER PRIMARY KEY,
    konzept_id    INTEGER NOT NULL REFERENCES lern_konzept(id) ON DELETE CASCADE,
    voraussetzung TEXT NOT NULL,          -- concept_id beim Lehrplan-Dienst
    titel         TEXT,
    created_at    TEXT NOT NULL,
    UNIQUE(konzept_id, voraussetzung)
);
CREATE INDEX IF NOT EXISTS idx_lern_voraussetzung ON lern_voraussetzung(konzept_id);

-- Fehlender Lehrstoff wird bestellt, nicht bedauert (Master-Invariante):
-- eine Voraussetzung, die Karo nicht hat, eine Aufgabe, die der Katalog
-- nicht mehr hergibt. Die Zeile beschreibt die fachliche Luecke — sie
-- gehoert keinem Kind und traegt deshalb keine Kinddaten.
--
-- Dedup ueber (fach, konzept_key, rolle, grund): dieselbe Luecke wird
-- nicht zweimal bestellt, egal wie oft sie anfaellt.
CREATE TABLE IF NOT EXISTS lern_inhalt_anfrage (
    id          INTEGER PRIMARY KEY,
    fach        TEXT NOT NULL DEFAULT '',
    konzept_key TEXT NOT NULL,          -- concept_id beim Lehrplan-Dienst
    konzept_id  INTEGER REFERENCES lern_konzept(id),
    -- Was fehlt: aufgabe | diagnose | voraussetzung | erklaerung
    rolle       TEXT NOT NULL,
    -- Warum: fehlt | erschoepft | unbrauchbar
    grund       TEXT NOT NULL,
    kontext     TEXT NOT NULL DEFAULT '{}',   -- Niveau, Fehlertyp, Klasse
    status      TEXT NOT NULL DEFAULT 'offen',-- offen | erfuellt | verworfen
    anzahl      INTEGER NOT NULL DEFAULT 1,   -- wie oft sie anfiel
    external_ref TEXT,                        -- Export-Nr. beim Lehrplan-Dienst
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    UNIQUE(fach, konzept_key, rolle, grund)
);
CREATE INDEX IF NOT EXISTS idx_lern_inhalt_anfrage
  ON lern_inhalt_anfrage(status, updated_at);

-- Jede beantwortete Aufgabe, genau eine Zeile (Schritt 4a).
--
-- Bisher wusste Karo nur, wie eine Sitzung ausging: `lern_fortschritt` zaehlt
-- Versuche und Erfolge, `lern_ereignis` haelt Uebergaenge fest. Was ein Kind
-- auf eine einzelne Aufgabe geantwortet hat und wie lange es daran war, stand
-- nirgends — und ohne das gibt es weder eine ehrliche Lernzeit noch eine
-- Wiederholung mit neuen Aufgaben.
--
-- Nur anhaengen, nie aendern: eine Zeile beschreibt einen Moment. Wer sie
-- spaeter korrigiert, hat keinen Verlauf mehr, sondern eine Meinung.
CREATE TABLE IF NOT EXISTS lern_antwort (
    id              INTEGER PRIMARY KEY,
    child_key       TEXT NOT NULL DEFAULT 'installation',
    -- Der Lernraum der Antwort ('installation' oder
    -- 'installation:topic:<id>', siehe store.topic_scope): geteiltes
    -- Curriculum, getrennter Lernstand. NULL bei Zeilen aus der Zeit
    -- vor der Spalte — sie gelten als global gesehen.
    scope           TEXT,
    sitzung_id      INTEGER REFERENCES lern_sitzung(id),
    aufgabe_id      INTEGER REFERENCES lern_aufgabe(id),
    konzept_id      INTEGER REFERENCES lern_konzept(id),
    fach            TEXT,
    phase           TEXT,
    rolle           TEXT NOT NULL,        -- anker, diagnose, vorhersage, aufgabe, transfer, voraussetzung, wiederholung
    gezeigt_at      TEXT,
    beantwortet_at  TEXT NOT NULL,
    antwort         TEXT,
    richtig         INTEGER,              -- NULL, wo nicht bewertet wird (Anker, Vorhersage)
    tipp_genutzt    INTEGER NOT NULL DEFAULT 0,
    -- Aktive Zeit dieser Aufgabe in Sekunden, gedeckelt. Getrennt von
    -- `learning_time`, das weiter den Elternbericht traegt: das misst
    -- Anwesenheit, das hier misst Arbeit an einer Aufgabe.
    aktive_sekunden REAL NOT NULL DEFAULT 0,
    -- Unter der Mindestzeit beantwortet. Eine Tatsache ueber diese eine
    -- Antwort — ob ein ganzer Abschnitt nicht ernsthaft war, ergibt sich
    -- daraus beim Lesen (`protokoll.nicht_ernsthaft`) und wird nicht
    -- nachtraeglich in alte Zeilen geschrieben.
    zu_schnell      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lern_antwort_kind
  ON lern_antwort(child_key, beantwortet_at);
CREATE INDEX IF NOT EXISTS idx_lern_antwort_aufgabe
  ON lern_antwort(child_key, aufgabe_id);

-- Die Uhr einer laufenden Aufgabe. Eigene Tabelle, nicht `lern_sitzung.daten`:
-- die Daten werden aus einem im Speicher gehaltenen Stand neu geschrieben
-- (`unterricht._merke`), und eine Uhr, die dabei still verschwindet, misst
-- irgendwann falsch statt gar nicht. Hier ueberlebt sie jeden Schreibvorgang.
CREATE TABLE IF NOT EXISTS lern_uhr (
    sitzung_id      INTEGER PRIMARY KEY REFERENCES lern_sitzung(id) ON DELETE CASCADE,
    kennung         TEXT NOT NULL,        -- welche Aufgabe gerade sichtbar ist
    gezeigt_at      TEXT NOT NULL,
    letzte_eingabe  TEXT NOT NULL,
    aktiv_sekunden  REAL NOT NULL DEFAULT 0,
    tipp_genutzt    INTEGER NOT NULL DEFAULT 0
);

-- Wiederholung mit Abstand (Z4).
--
-- Nach `MASTERED` passierte bisher nichts mehr: kein Termin, keine
-- Auffrischung, keine Vergessenskurve. Das Kind waehlt den Abstand selbst
-- (2 bis 5 Tage) — wer den Tag mitbestimmt, haelt ihn eher ein.
CREATE TABLE IF NOT EXISTS lern_wiederholung (
    id          INTEGER PRIMARY KEY,
    child_key   TEXT NOT NULL DEFAULT 'installation',
    konzept_id  INTEGER NOT NULL REFERENCES lern_konzept(id) ON DELETE CASCADE,
    sitzung_id  INTEGER REFERENCES lern_sitzung(id),
    faellig_am  TEXT NOT NULL,            -- lokales Datum, YYYY-MM-DD
    gewaehlt_am TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'offen',   -- offen, bestanden, nicht_bestanden
    ergebnis    TEXT NOT NULL DEFAULT '{}',
    erledigt_am TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lern_wiederholung_faellig
  ON lern_wiederholung(child_key, status, faellig_am);
