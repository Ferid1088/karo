"""Repository für das adaptive Lernen — die einzige Schicht mit SQL.

01_ARCHITECTURE.md §10: Meilenstein 4 tauscht die Datenbank gegen PostgreSQL
mit pgvector. Dieser Tausch darf ausschließlich diese Datei berühren, deshalb
gibt hier nichts `sqlite3.Row` nach außen und nimmt nichts SQL von außen an.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import db

CHILD_KEY = "installation"      # wie in welten/woche: eine Installation, ein Kind


#: Spalten, die nach der ersten Fassung von `schema.sql` dazukamen.
#:
#: `CREATE TABLE IF NOT EXISTS` legt sie in einer bestehenden Datenbank nicht
#: an — dieselbe Falle, die `app/db.py` mit `_ADDED_COLUMNS` abfängt. Die
#: Liste steht hier und nicht dort, weil §10 verlangt, dass SQL der
#: adaptiven Tabellen ausschließlich in dieser Datei lebt.
#:
#: Die Deklaration muss der in `schema.sql` entsprechen.
_NACHGETRAGENE_SPALTEN = [
    ("lern_eingabe", "topic_id", "INTEGER"),
    ("lern_konzept", "stichworte", "TEXT NOT NULL DEFAULT '[]'"),
    ("lern_konzept", "quelle", "TEXT NOT NULL DEFAULT 'kuratiert'"),
    ("lern_konzept", "geprueft_am", "TEXT"),
    ("lern_konzept", "aktiv", "INTEGER NOT NULL DEFAULT 1"),
    ("lern_fehlertyp", "quelle", "TEXT NOT NULL DEFAULT 'kuratiert'"),
    ("lern_fehlertyp", "geprueft_am", "TEXT"),
    ("lern_aufgabe", "quelle", "TEXT NOT NULL DEFAULT 'kuratiert'"),
    ("lern_aufgabe", "geprueft_am", "TEXT"),
    ("lern_hilfe", "visualisierung", "TEXT"),
    ("lern_erklaerung", "visualisierung_alternativ", "TEXT"),
    ("lern_aufgabe", "typischer_fehler", "TEXT"),
    ("lern_aufgabe", "antwort_art", "TEXT NOT NULL DEFAULT 'bruch'"),
    ("lern_aufgabe", "optionen", "TEXT NOT NULL DEFAULT '[]'"),
    ("lern_aufgabe", "aufloesung", "TEXT"),
    ("lern_aufgabe", "erwartete_sekunden", "INTEGER"),
    # Der Lernraum, dem eine Antwort zugehoert: 'installation' fuer
    # themenlose Sitzungen, 'installation:topic:<id>' fuer ein Thema —
    # dieselbe Regel wie `fortschritt_scope`. Geteiltes Curriculum, aber
    # kein geteilter Lernstand: eine im Pruefungsthema gesehene Aufgabe
    # gilt im eigenen Thema weiter als neu.
    ("lern_antwort", "scope", "TEXT"),
    # Die Auftragsnummer, unter der der Lehrplan-Dienst eine Bestellung
    # bearbeitet: damit findet der Folgeaufruf seine Lieferung wieder.
    ("lern_inhalt_anfrage", "external_ref", "TEXT"),
]


def init() -> None:
    c = db.conn()
    c.executescript(
        Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
    _spalten_nachziehen(c)


def _spalten_nachziehen(c) -> None:
    """Bringt eine ältere Datenbank auf den Stand von `schema.sql`.

    Idempotent: was schon da ist, bleibt unberührt. Eine frisch angelegte
    Datenbank hat alle Spalten bereits und läuft hier nur durch.
    """
    for tabelle, spalte, deklaration in _NACHGETRAGENE_SPALTEN:
        vorhanden = {r["name"] for r in c.execute(f"PRAGMA table_info({tabelle})")}
        if vorhanden and spalte not in vorhanden:
            c.execute(f"ALTER TABLE {tabelle} ADD COLUMN {spalte} {deklaration}")
    # Bestehende Antworten bekommen ihren Scope nachgerechnet: ueber die
    # Sitzung zur Eingabe und von dort zum Thema. Themenlose Antworten
    # bleiben im gemeinsamen 'installation'-Raum — sie gehoerten nie zu
    # einem einzelnen Thema.
    if "scope" in {r["name"] for r in c.execute("PRAGMA table_info(lern_antwort)")}:
        c.execute("""UPDATE lern_antwort SET scope = (
                       SELECT CASE WHEN e.topic_id IS NULL THEN a.child_key
                              ELSE a.child_key || ':topic:' || e.topic_id END
                         FROM lern_sitzung s JOIN lern_eingabe e
                           ON e.id = s.eingabe_id
                        WHERE s.id = a.sitzung_id)
                     FROM lern_antwort a
                     WHERE a.scope IS NULL AND EXISTS (
                       SELECT 1 FROM lern_sitzung s JOIN lern_eingabe e
                         ON e.id = s.eingabe_id WHERE s.id = a.sitzung_id)""")
    # Bestehende Wiederholungstermine gehoerten oft zu einer Sitzung — und
    # deren Eingabe kennt ihr Thema. Wo sich das rekonstruieren laesst,
    # wandert der Termin in den Themen-Raum; Termine ohne Sitzungsbezug
    # bleiben im gemeinsamen Raum, statt blind allen Themen zu gehoeren.
    c.execute("""UPDATE lern_wiederholung SET child_key = (
                   SELECT w.child_key || ':topic:' || e.topic_id
                     FROM lern_sitzung s JOIN lern_eingabe e
                       ON e.id = s.eingabe_id
                    WHERE s.id = w.sitzung_id AND e.topic_id IS NOT NULL)
                 FROM lern_wiederholung w
                 WHERE w.child_key NOT LIKE '%:topic:%' AND EXISTS (
                   SELECT 1 FROM lern_sitzung s JOIN lern_eingabe e
                     ON e.id = s.eingabe_id
                    WHERE s.id = w.sitzung_id AND e.topic_id IS NOT NULL)""")


def _zeile(row) -> dict | None:
    return dict(row) if row is not None else None


def _json(wert: str | None, standard):
    if not wert:
        return standard
    try:
        return json.loads(wert)
    except (ValueError, TypeError):
        return standard


# --------------------------------------------------------------------------
# Konzepte und Fehlertypen (§2)
# --------------------------------------------------------------------------

def curriculum_import(fingerprint: str) -> dict | None:
    return _zeile(db.q1("SELECT * FROM lern_curriculum_import WHERE fingerprint=?", fingerprint))


def curriculum_import_sichern(fingerprint: str, konzept_id: int, provenance: dict) -> None:
    with db.tx() as c:
        c.execute("INSERT OR IGNORE INTO lern_curriculum_import "
                  "(fingerprint, konzept_id, provenance, created_at) VALUES (?, ?, ?, ?)",
                  (fingerprint, konzept_id, json.dumps(provenance, ensure_ascii=False), db.now()))

def konzept_sichern(fach: str, thema_key: str, konzept_key: str, label: str,
                    klasse_von: int = 1, klasse_bis: int = 13, *,
                    stichworte=(), quelle: str = "kuratiert",
                    geprueft: bool = False) -> int:
    """Legt ein Konzept an oder bringt ein vorhandenes auf Stand.

    Mehrfach aufrufbar: verfasste Lektionen saeen bei jedem Start. Ein
    bestehender Eintrag behaelt seine Id; Stichworte und Pruefzustand werden
    nachgezogen, damit eine Datenbank aus der Zeit vor diesen Spalten die
    Lektion nicht verliert.
    """
    worte = json.dumps([str(w) for w in stichworte], ensure_ascii=False)
    with db.tx() as c:
        vorhanden = c.execute(
            "SELECT id, geprueft_am FROM lern_konzept "
            "WHERE fach=? AND thema_key=? AND konzept_key=?",
            (fach, thema_key, konzept_key)).fetchone()
        if vorhanden:
            c.execute("UPDATE lern_konzept SET label=?, stichworte=? WHERE id=?",
                      (label, worte, vorhanden["id"]))
            if geprueft and not vorhanden["geprueft_am"]:
                c.execute("UPDATE lern_konzept SET geprueft_am=? WHERE id=?",
                          (db.now(), vorhanden["id"]))
            return vorhanden["id"]
        return c.execute(
            """INSERT INTO lern_konzept (fach, thema_key, konzept_key, label,
                                         klasse_von, klasse_bis, stichworte,
                                         quelle, geprueft_am, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (fach, thema_key, konzept_key, label, klasse_von, klasse_bis,
             worte, quelle, db.now() if geprueft else None,
             db.now())).lastrowid


def konzept_freigeben(konzept_id: int) -> None:
    """§11: erst nach der Freigabe sieht ein Kind die Lektion."""
    with db.tx() as c:
        c.execute("UPDATE lern_konzept SET geprueft_am=? WHERE id=?",
                  (db.now(), konzept_id))


def konzepte_verfuegbar() -> list[dict]:
    """Alle Lektionen, die ausgeliefert werden duerfen — aktiv und geprueft.

    Die Quelle der Wahrheit fuer „was gibt es?". Frueher war das eine fest
    verdrahtete Modulliste; damit war eine erzeugte Lektion unauffindbar.
    """
    return [_konzept_aufbereiten(r) for r in db.q(
        """SELECT * FROM lern_konzept
            WHERE aktiv=1 AND geprueft_am IS NOT NULL
            ORDER BY fach, thema_key, konzept_key""")]


def _konzept_aufbereiten(row) -> dict | None:
    eintrag = _zeile(row)
    if eintrag is not None:
        eintrag["stichworte"] = _json(eintrag.get("stichworte"), [])
    return eintrag


def konzept(konzept_id: int) -> dict | None:
    return _konzept_aufbereiten(
        db.q1("SELECT * FROM lern_konzept WHERE id=?", konzept_id))


def konzept_nach_key(fach: str, thema_key: str, konzept_key: str) -> dict | None:
    return _konzept_aufbereiten(db.q1(
        "SELECT * FROM lern_konzept WHERE fach=? AND thema_key=? AND konzept_key=?",
        fach, thema_key, konzept_key))


def fehlertyp_sichern(konzept_id: int, fehler_key: str, label: str,
                      beschreibung: str = "", *, quelle: str = "kuratiert",
                      geprueft: bool = False) -> int:
    with db.tx() as c:
        vorhanden = c.execute(
            "SELECT id, geprueft_am FROM lern_fehlertyp "
            "WHERE konzept_id=? AND fehler_key=?",
            (konzept_id, fehler_key)).fetchone()
        if vorhanden:
            if geprueft and not vorhanden["geprueft_am"]:
                c.execute("UPDATE lern_fehlertyp SET geprueft_am=? WHERE id=?",
                          (db.now(), vorhanden["id"]))
            return vorhanden["id"]
        return c.execute(
            """INSERT INTO lern_fehlertyp (konzept_id, fehler_key, label,
                                           beschreibung, quelle, geprueft_am,
                                           created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (konzept_id, fehler_key, label, beschreibung or None, quelle,
             db.now() if geprueft else None, db.now())).lastrowid


def fehlertyp_freigeben(fehlertyp_id: int) -> None:
    """§11: eine ungepruefte Fehlvorstellung ordnet keine Antwort zu."""
    with db.tx() as c:
        c.execute("UPDATE lern_fehlertyp SET geprueft_am=? WHERE id=?",
                  (db.now(), fehlertyp_id))


def fehlertyp(fehlertyp_id: int) -> dict | None:
    return _zeile(db.q1("SELECT * FROM lern_fehlertyp WHERE id=?", fehlertyp_id))


def fehlertypen(konzept_id: int) -> list[dict]:
    return [dict(r) for r in db.q(
        "SELECT * FROM lern_fehlertyp WHERE konzept_id=? AND aktiv=1 "
        "AND geprueft_am IS NOT NULL ORDER BY id",
        konzept_id)]


def alias_sichern(fehlertyp_id: int, muster: str, quelle: str = "kuratiert") -> None:
    """`muster` muss bereits normalisiert sein (siehe normalisierung.py)."""
    if not muster:
        return
    with db.tx() as c:
        c.execute(
            """INSERT OR IGNORE INTO lern_fehler_alias
                   (fehlertyp_id, muster, quelle, created_at)
               VALUES (?,?,?,?)""",
            (fehlertyp_id, muster, quelle, db.now()))


def fehlertyp_fuer_muster(konzept_id: int, muster: str) -> dict | None:
    """Tier 1 (§6): exakter Abgleich, kein Modell, ein Index-Zugriff."""
    if not muster:
        return None
    return _zeile(db.q1(
        """SELECT f.* FROM lern_fehler_alias a
             JOIN lern_fehlertyp f ON f.id = a.fehlertyp_id
            WHERE a.muster = ? AND f.konzept_id = ? AND f.aktiv = 1
              AND f.geprueft_am IS NOT NULL
            ORDER BY f.id LIMIT 1""", muster, konzept_id))


# --------------------------------------------------------------------------
# Erklärungen (§6): versionieren, nie destruktiv ersetzen
# --------------------------------------------------------------------------

def erklaerung_anlegen(fehlertyp_id: int, klasse: int, inhalt: dict,
                       visualisierung: dict | None = None,
                       aufgabe: dict | None = None, schwierigkeit: int = 1,
                       quelle: str = "kuratiert", geprueft: bool = False,
                       visualisierung_alternativ: dict | None = None) -> int:
    jetzt = db.now()
    with db.tx() as c:
        letzte = c.execute(
            "SELECT MAX(version) AS v FROM lern_erklaerung WHERE fehlertyp_id=? AND klasse=?",
            (fehlertyp_id, klasse)).fetchone()
        version = (letzte["v"] or 0) + 1
        return c.execute(
            """INSERT INTO lern_erklaerung
                   (fehlertyp_id, klasse, version, inhalt, visualisierung,
                    visualisierung_alternativ, aufgabe, schwierigkeit, quelle,
                    geprueft_am, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (fehlertyp_id, klasse, version,
             json.dumps(inhalt, ensure_ascii=False),
             json.dumps(visualisierung, ensure_ascii=False) if visualisierung else None,
             json.dumps(visualisierung_alternativ, ensure_ascii=False)
             if visualisierung_alternativ else None,
             json.dumps(aufgabe, ensure_ascii=False) if aufgabe else None,
             schwierigkeit, quelle, jetzt if geprueft else None, jetzt,
             jetzt)).lastrowid


def erklaerung_freigeben(erklaerung_id: int) -> None:
    """§11: Ungeprüfte Inhalte werden keinem Kind ausgeliefert."""
    with db.tx() as c:
        c.execute("UPDATE lern_erklaerung SET geprueft_am=?, updated_at=? WHERE id=?",
                  (db.now(), db.now(), erklaerung_id))


def erklaerung_archivieren(erklaerung_id: int) -> None:
    """Verlierer werden archiviert, nicht gelöscht (§6)."""
    with db.tx() as c:
        c.execute(
            "UPDATE lern_erklaerung SET aktiv=0, archiviert_am=?, updated_at=? WHERE id=?",
            (db.now(), db.now(), erklaerung_id))


def _erklaerung_aufbereiten(row) -> dict | None:
    eintrag = _zeile(row)
    if eintrag is None:
        return None
    eintrag["inhalt"] = _json(eintrag.get("inhalt"), {})
    eintrag["visualisierung"] = _json(eintrag.get("visualisierung"), None)
    eintrag["visualisierung_alternativ"] = _json(
        eintrag.get("visualisierung_alternativ"), None)
    eintrag["aufgabe"] = _json(eintrag.get("aufgabe"), None)
    ausgeliefert = eintrag.get("ausgeliefert") or 0
    eintrag["erfolgsquote"] = (
        (eintrag.get("folge_erfolge") or 0) / ausgeliefert if ausgeliefert else None)
    return eintrag


def erklaerung(erklaerung_id: int) -> dict | None:
    return _erklaerung_aufbereiten(
        db.q1("SELECT * FROM lern_erklaerung WHERE id=?", erklaerung_id))


def beste_erklaerung(fehlertyp_id: int, klasse: int,
                     hoechstens_schwierigkeit: int | None = None) -> dict | None:
    """Ausgeliefert wird nur, was aktiv UND geprüft ist (§11).

    Die Klassenstufe gehört zum Katalogschlüssel (§6), trifft aber nicht immer
    exakt: eine Lektion für Klasse 5–6 hilft einem Kind in Klasse 7 weiterhin.
    Deshalb zuerst die genaue Stufe, sonst die nächstgelegene — degradieren
    statt ausfallen (§15), und niemals ein leerer Bildschirm.
    """
    sql = ["""SELECT * FROM lern_erklaerung
               WHERE fehlertyp_id=? AND aktiv=1
                 AND archiviert_am IS NULL AND geprueft_am IS NOT NULL"""]
    params: list = [fehlertyp_id]
    if hoechstens_schwierigkeit is not None:
        sql.append("AND schwierigkeit <= ?")
        params.append(hoechstens_schwierigkeit)
    # Z10: Wirkung schlaegt Reihenfolge — aber erst, wenn sie etwas bedeutet.
    #
    # `folge_erfolge/ausgeliefert` wurde seit jeher mitgezaehlt und nirgends
    # gelesen. Eine Erklaerung, die bei keinem Kind je gewirkt hat, wurde
    # weiter ausgeliefert. Jetzt zaehlt sie mit — ab `adaptiv_wirkung_ab`
    # Einsaetzen, darunter ist eine Quote Zufall und keine Aussage.
    from .. import config
    ab = max(1, int(getattr(config.load_safe(), "adaptiv_wirkung_ab", 10)))
    sql.append("""ORDER BY ABS(klasse - ?),
                     CASE WHEN ausgeliefert >= ?
                          THEN CAST(folge_erfolge AS REAL) / ausgeliefert
                          ELSE NULL END DESC NULLS LAST,
                     schwierigkeit DESC, version DESC LIMIT 1""")
    params += [klasse, ab]
    return _erklaerung_aufbereiten(db.q1(" ".join(sql), *params))


def wirkungslose_erklaerungen(cfg=None) -> list[dict]:
    """Erklaerungen, die oft genug liefen, um als wirkungslos zu gelten.

    Nur Zahlen, nie ein Kind: Konzept, Fehlertyp, Erklaerungs-ID, wie oft
    ausgeliefert und wie oft danach eine richtige Antwort kam. Mehr braucht
    der Lehrplan-Dienst nicht, um sie neu zu schreiben — und mehr bekommt er
    auch nicht.
    """
    from .. import config
    c = cfg or config.load_safe()
    ab = max(1, int(getattr(c, "adaptiv_wirkung_ab", 10)))
    schwelle = float(getattr(c, "adaptiv_wirkung_schwelle", 0.3))
    # Nicht zweimal dasselbe melden: erst wieder, wenn seit der Meldung
    # weitere Einsaetze dazugekommen sind.
    zeilen = db.q(
        """SELECT e.id, e.fehlertyp_id, e.klasse, e.ausgeliefert, e.folge_erfolge,
                  f.konzept_id, f.fehler_key, k.konzept_key
             FROM lern_erklaerung e
             JOIN lern_fehlertyp f ON f.id = e.fehlertyp_id
             JOIN lern_konzept k ON k.id = f.konzept_id
             LEFT JOIN lern_erklaerung_gemeldet g ON g.erklaerung_id = e.id
            WHERE e.aktiv=1 AND e.archiviert_am IS NULL
              AND e.ausgeliefert >= ?
              AND CAST(e.folge_erfolge AS REAL) / e.ausgeliefert < ?
              AND (g.erklaerung_id IS NULL OR e.ausgeliefert > g.ausgeliefert)
            ORDER BY CAST(e.folge_erfolge AS REAL) / e.ausgeliefert""",
        ab, schwelle)
    return [{"erklaerung_id": z["id"], "konzept_key": z["konzept_key"],
             "fehler_key": z["fehler_key"], "klasse": z["klasse"],
             "ausgeliefert": z["ausgeliefert"], "wirkte": z["folge_erfolge"],
             "wirkquote": round(z["folge_erfolge"] / z["ausgeliefert"], 2)}
            for z in zeilen]


def voraussetzungen_sichern(konzept_id: int, eintraege: list[dict]) -> int:
    """Die Voraussetzungen eines Konzepts aus der Lieferung festhalten (Z3)."""
    if not eintraege:
        return 0
    with db.tx() as c:
        c.execute("DELETE FROM lern_voraussetzung WHERE konzept_id=?", (konzept_id,))
        for e in eintraege:
            c.execute("""INSERT OR IGNORE INTO lern_voraussetzung
                           (konzept_id, voraussetzung, titel, created_at)
                         VALUES (?,?,?,?)""",
                      (konzept_id, e["concept_id"], e.get("title") or None, db.now()))
    return len(eintraege)


def voraussetzungen(konzept_id: int) -> list[dict]:
    """Was vor diesem Konzept sitzen sollte.

    `lokal` ist die Konzept-ID in Karo, falls die Voraussetzung schon
    importiert wurde — sonst None. Dann weiss Karo zwar, dass sie fehlt,
    kann sie aber noch nicht unterrichten.
    """
    return [dict(z) for z in db.q(
        """SELECT v.voraussetzung, v.titel,
                  (SELECT i.konzept_id FROM lern_curriculum_import i
                    WHERE json_extract(i.provenance, '$.concept_id') = v.voraussetzung
                    LIMIT 1) AS lokal
             FROM lern_voraussetzung v WHERE v.konzept_id=?
            ORDER BY v.id""", konzept_id)]


def inhalt_anfordern(fach: str, konzept_key: str, rolle: str, grund: str,
                     konzept_id: int | None = None,
                     kontext: dict | None = None) -> dict:
    """Eine Lücke im Katalog bestellen — dedupliziert.

    Dieselbe fachliche Lücke (Fach, Konzept, Rolle, Grund) bekommt eine
    Zeile: beim erneuten Anfallen steigt `anzahl`, es entsteht keine
    zweite Bestellung. Was hier steht, kann der Lehrplan-Dienst erzeugen
    und prüfen — Karo lernt unterdessen mit dem besten vorhandenen
    Material weiter.
    """
    jetzt = db.now()
    # Der Schluessel adressiert das Konzept — traegt er ein Fachkuerzel
    # (Dienst-Konzepte heissen `MA.`/`DE.`/…, lokale `fach.thema.konzept`),
    # ist das verbindlicher als das Fach der meldenden Sitzung: eine
    # Physik-Voraussetzung kann durchaus ein Mathe-Konzept sein, und im
    # falschen Fach sucht der Dienst sie nie.
    from karo_contract.faecher import schluessel as _fachschluessel
    fach = _fachschluessel(str(konzept_key or "").split(".")[0]) or fach
    with db.tx() as c:
        c.execute("""INSERT INTO lern_inhalt_anfrage
                       (fach, konzept_key, konzept_id, rolle, grund,
                        kontext, created_at, updated_at)
                     VALUES (?,?,?,?,?,?,?,?)
                     ON CONFLICT(fach, konzept_key, rolle, grund) DO UPDATE
                       SET konzept_id = COALESCE(lern_inhalt_anfrage.konzept_id,
                                                 excluded.konzept_id),
                           kontext    = excluded.kontext,
                           anzahl     = lern_inhalt_anfrage.anzahl + 1,
                           -- Fällt die Luecke nach Lieferung oder Verwerfen
                           -- erneut an, ist die alte Antwort offenbar nicht
                           -- genug: neue Bestellung, neuer Auftrag.
                           status     = 'offen',
                           external_ref = CASE
                               WHEN lern_inhalt_anfrage.status = 'offen'
                               THEN lern_inhalt_anfrage.external_ref
                               ELSE NULL END,
                           updated_at = excluded.updated_at""",
                  (fach or "", konzept_key, konzept_id, rolle, grund,
                   json.dumps(kontext or {}, ensure_ascii=False),
                   jetzt, jetzt))
        zeile = dict(c.execute(
            """SELECT * FROM lern_inhalt_anfrage
                WHERE fach=? AND konzept_key=? AND rolle=? AND grund=?""",
            (fach or "", konzept_key, rolle, grund)).fetchone())
    # Die Bestellung wird erst nuetzlich, wenn jemand sie zum Dienst traegt:
    # ein Hintergrundauftrag pro Lueckenmeldung, dedupliziert. Ohne
    # eingerichteten Dienst bleibt sie einfach offen — der Unterricht laeuft
    # mit dem besten vorhandenen Material weiter.
    try:
        from .. import config, jobs
        from . import curriculum_dienst          # meldet den Job an
        if curriculum_dienst.configured(config.load_safe()):
            jobs.enqueue("inhalt_anfragen", dedup_key="inhalt_anfragen")
    except Exception:                            # noqa: BLE001 - die
        pass                                     # Bestellung steht ohnehin
    return zeile


def inhalt_anfragen(status: str = "offen") -> list[dict]:
    """Die Bestellliste — z. B. fuer den Importlauf des Lehrplan-Dienstes."""
    return [dict(z) for z in db.q(
        """SELECT * FROM lern_inhalt_anfrage WHERE status=?
            ORDER BY updated_at DESC""", status)]


def inhalt_anfrage_verknuepfen(anfrage_id: int, external_ref) -> None:
    """Die Bestellung ist beim Dienst angekommen: seine Auftragsnummer
    merken, damit der naechste Lauf die fertige Lieferung findet statt
    neu zu bestellen. `None` loest die Verknuepfung wieder."""
    with db.tx() as c:
        c.execute("""UPDATE lern_inhalt_anfrage
                        SET external_ref=?, updated_at=? WHERE id=?""",
                  (None if external_ref is None else str(external_ref),
                   db.now(), anfrage_id))


def inhalt_erfuellt(anfrage_id: int, konzept_id: int | None = None) -> None:
    """Die Lieferung ist importiert: die Luecke ist geschlossen, und der
    Verweis auf das neue lokale Konzept macht nachvollziehbar, womit."""
    with db.tx() as c:
        c.execute("""UPDATE lern_inhalt_anfrage
                        SET status='erfuellt',
                            konzept_id=COALESCE(?, konzept_id),
                            updated_at=? WHERE id=?""",
                  (konzept_id, db.now(), anfrage_id))


def inhalt_verwerfen(anfrage_id: int) -> None:
    """Endgueltig unlieferbar — z. B. nach Karos eigener Ablehnung. Die
    Zeile bleibt als Gedaechtnis stehen; `inhalt_anfordern` oeffnet sie
    wieder, wenn die Luecke erneut anfaellt."""
    with db.tx() as c:
        c.execute("""UPDATE lern_inhalt_anfrage
                        SET status='verworfen', updated_at=? WHERE id=?""",
                  (db.now(), anfrage_id))


def konzept_schluessel(konzept_id: int | None) -> str | None:
    """Die concept_id, unter der der Lehrplan-Dienst das Konzept kennt.

    Kuratierte Konzepte ohne Importzeile haben keine — dann bleibt der
    lokale Schluessel `fach.thema_key.konzept_key` als Adresse uebrig.
    """
    if not konzept_id:
        return None
    zeile = db.q1("""SELECT provenance FROM lern_curriculum_import
                      WHERE konzept_id=? LIMIT 1""", konzept_id)
    if not zeile:
        return None
    try:
        return (json.loads(zeile["provenance"]) or {}).get("concept_id")
    except (ValueError, TypeError):
        return None


def wirkung_gemeldet(erklaerung_ids: list[int]) -> None:
    """Haelt fest, dass diese Erklaerung gemeldet wurde.

    Ohne das ginge dieselbe Meldung bei jedem Lauf erneut hinaus, und der
    Dienst bekaeme jeden Tag dieselbe Liste.
    """
    if not erklaerung_ids:
        return
    with db.tx() as c:
        for eid in erklaerung_ids:
            c.execute("""INSERT INTO lern_erklaerung_gemeldet
                           (erklaerung_id, gemeldet_am, ausgeliefert, folge_erfolge)
                         SELECT id, ?, ausgeliefert, folge_erfolge
                           FROM lern_erklaerung WHERE id=?
                         ON CONFLICT(erklaerung_id) DO UPDATE
                           SET gemeldet_am=excluded.gemeldet_am,
                               ausgeliefert=excluded.ausgeliefert,
                               folge_erfolge=excluded.folge_erfolge""",
                      (db.now(), eid))


def erklaerungen(fehlertyp_id: int, mit_archivierten: bool = False) -> list[dict]:
    sql = "SELECT * FROM lern_erklaerung WHERE fehlertyp_id=?"
    if not mit_archivierten:
        sql += " AND archiviert_am IS NULL"
    sql += " ORDER BY version"
    return [_erklaerung_aufbereiten(r) for r in db.q(sql, fehlertyp_id)]


def erklaerung_ausgeliefert(erklaerung_id: int) -> None:
    with db.tx() as c:
        c.execute(
            "UPDATE lern_erklaerung SET ausgeliefert=ausgeliefert+1, updated_at=? WHERE id=?",
            (db.now(), erklaerung_id))


def erklaerung_wirkte(erklaerung_id: int) -> None:
    """Eine Erklärung wird am nächsten Antwortversuch gemessen (§19)."""
    with db.tx() as c:
        c.execute(
            "UPDATE lern_erklaerung SET folge_erfolge=folge_erfolge+1, updated_at=? WHERE id=?",
            (db.now(), erklaerung_id))


# --------------------------------------------------------------------------
# Erstkontakt (§11)
# --------------------------------------------------------------------------

def erstkontakt_anlegen(konzept_id: int, anker: str, erste_aufgabe: dict,
                        benennung: str, quelle: str = "kuratiert",
                        geprueft: bool = False) -> int:
    with db.tx() as c:
        letzte = c.execute(
            "SELECT MAX(version) AS v FROM lern_erstkontakt WHERE konzept_id=?",
            (konzept_id,)).fetchone()
        return c.execute(
            """INSERT INTO lern_erstkontakt (konzept_id, version, anker,
                    erste_aufgabe, benennung, quelle, geprueft_am, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (konzept_id, (letzte["v"] or 0) + 1, anker,
             json.dumps(erste_aufgabe, ensure_ascii=False), benennung, quelle,
             db.now() if geprueft else None, db.now())).lastrowid


def erstkontakt_freigeben(konzept_id: int) -> None:
    """§11: der Erstkontakt ist das Erste, was ein Kind sieht."""
    with db.tx() as c:
        c.execute("UPDATE lern_erstkontakt SET geprueft_am=? "
                  "WHERE konzept_id=? AND geprueft_am IS NULL",
                  (db.now(), konzept_id))


def erstkontakt(konzept_id: int) -> dict | None:
    eintrag = _zeile(db.q1(
        """SELECT * FROM lern_erstkontakt
            WHERE konzept_id=? AND aktiv=1 AND geprueft_am IS NOT NULL
            ORDER BY version DESC LIMIT 1""", konzept_id))
    if eintrag:
        eintrag["erste_aufgabe"] = _json(eintrag.get("erste_aufgabe"), {})
    return eintrag


# --------------------------------------------------------------------------
# Lerneingabe (§13)
# --------------------------------------------------------------------------

def eingabe_anlegen(art: str, fach: str | None = None,
                    thema_text: str | None = None,
                    konzept_id: int | None = None,
                    topic_id: int | None = None,
                    document_id: int | None = None,
                    aufgaben: list | None = None,
                    konfidenz: float | None = None,
                    child_key: str = CHILD_KEY) -> int:
    with db.tx() as c:
        return c.execute(
            """INSERT INTO lern_eingabe (child_key, art, fach, thema_text,
                    konzept_id, topic_id, document_id, aufgaben, konfidenz,
                    created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (child_key, art, fach, thema_text, konzept_id, topic_id,
             document_id, json.dumps(aufgaben or [], ensure_ascii=False),
             konfidenz, db.now())).lastrowid


def topic_mastery(topic_id: int, child_key: str = CHILD_KEY) -> str | None:
    """Letzter beobachteter Lernzustand eines normalen Karo-Themas.

    Damit kann z. B. der Klassenarbeitsplan beim selben Thema bleiben, bis
    der adaptive Lernweg es wirklich als MASTERED abgeschlossen hat.
    """
    row = db.q1(
        """SELECT s.zustand FROM lern_sitzung s
             JOIN lern_eingabe e ON e.id=s.eingabe_id
            WHERE s.child_key=? AND e.topic_id=?
            ORDER BY s.id DESC LIMIT 1""",
        child_key, topic_id)
    return row["zustand"] if row else None


def themen_mit_sitzung(child_key: str = CHILD_KEY) -> dict:
    """Themen-ID → ob dazu gerade eine Sitzung offen ist.

    Die einzige Abfrage, die beide Welten verbindet, und sie liegt hier,
    weil §10 alles SQL der `lern_`-Tabellen in dieser Datei hält. Die
    Lernuebersicht bekommt nur einfache Typen zurück, kein `sqlite3.Row`.
    """
    zeilen = db.q(
        """SELECT e.topic_id AS topic_id, s.zustand AS zustand
             FROM lern_sitzung s JOIN lern_eingabe e ON e.id = s.eingabe_id
            WHERE s.child_key = ? AND e.topic_id IS NOT NULL""", child_key)
    ergebnis: dict = {}
    for zeile in zeilen:
        # Eskaliert ist offen: das Thema wartet auf Fortsetzung, es ist
        # nicht weg.
        offen = zeile["zustand"] != "MASTERED"
        ergebnis[zeile["topic_id"]] = ergebnis.get(zeile["topic_id"], False) or offen
    return ergebnis


def eingabe(eingabe_id: int) -> dict | None:
    eintrag = _zeile(db.q1("SELECT * FROM lern_eingabe WHERE id=?", eingabe_id))
    if eintrag:
        eintrag["aufgaben"] = _json(eintrag.get("aufgaben"), [])
    return eintrag


# --------------------------------------------------------------------------
# Sitzung und Übergänge (§7)
# --------------------------------------------------------------------------

def sitzung_anlegen(zustand: str, eingabe_id: int | None = None,
                    konzept_id: int | None = None,
                    child_key: str = CHILD_KEY) -> int:
    jetzt = db.now()
    with db.tx() as c:
        return c.execute(
            """INSERT INTO lern_sitzung (child_key, eingabe_id, konzept_id,
                    zustand, created_at, updated_at)
               VALUES (?,?,?,?,?,?)""",
            (child_key, eingabe_id, konzept_id, zustand, jetzt,
             jetzt)).lastrowid


def _sitzung_aufbereiten(row) -> dict | None:
    eintrag = _zeile(row)
    if eintrag:
        eintrag["daten"] = _json(eintrag.get("daten"), {})
    return eintrag


def sitzung(sitzung_id: int) -> dict | None:
    return _sitzung_aufbereiten(
        db.q1("SELECT * FROM lern_sitzung WHERE id=?", sitzung_id))


def offene_fuer_thema(topic_id: int) -> dict | None:
    """Resume an in-progress topic on its pinned content version.

    Auch eine eskalierte Sitzung ist offen: wer festhaengte, setzt genau an
    der Stelle fort — das Thema verschwindet nicht, weil es knifflig war.
    """
    return _sitzung_aufbereiten(db.q1('''SELECT s.* FROM lern_sitzung s
        JOIN lern_eingabe e ON e.id=s.eingabe_id
        WHERE s.child_key=? AND e.topic_id=?
        AND s.zustand != 'MASTERED'
        ORDER BY s.id DESC LIMIT 1''', CHILD_KEY, topic_id))


def letzte_fuer_thema(topic_id: int | None, konzept_id: int) -> dict | None:
    return _sitzung_aufbereiten(db.q1('''SELECT s.* FROM lern_sitzung s
        JOIN lern_eingabe e ON e.id=s.eingabe_id
        WHERE s.child_key=? AND e.topic_id IS ? AND s.konzept_id=?
        ORDER BY s.id DESC LIMIT 1''', CHILD_KEY, topic_id, konzept_id))


def offene_sitzung(child_key: str = CHILD_KEY,
                   abgeschlossen: tuple[str, ...] = ()) -> dict | None:
    """Die laufende Sitzung — Grundlage dafür, dass ein Neu-Login dort weitermacht."""
    platzhalter = ",".join("?" * len(abgeschlossen)) or "''"
    return _sitzung_aufbereiten(db.q1(
        f"""SELECT * FROM lern_sitzung
             WHERE child_key=? AND zustand NOT IN ({platzhalter})
             ORDER BY id DESC LIMIT 1""", child_key, *abgeschlossen))


def sitzung_aktualisieren(sitzung_id: int, **felder) -> None:
    erlaubt = {"konzept_id", "fehlertyp_id", "erklaerung_id", "zustand",
               "phase", "runden", "versuche", "letzte_antwort", "daten",
               "eingabe_id"}
    unbekannt = set(felder) - erlaubt
    if unbekannt:
        raise ValueError(f"Unbekannte Sitzungsfelder: {sorted(unbekannt)}")
    if not felder:
        return
    if "daten" in felder:
        felder["daten"] = json.dumps(felder["daten"], ensure_ascii=False)
    zuweisung = ", ".join(f"{name}=?" for name in felder)
    with db.tx() as c:
        c.execute(f"UPDATE lern_sitzung SET {zuweisung}, updated_at=? WHERE id=?",
                  (*felder.values(), db.now(), sitzung_id))


def ereignis_schreiben(sitzung_id: int, anlass: str, von_zustand=None,
                       nach_zustand=None, von_phase=None, nach_phase=None,
                       nutzdaten: dict | None = None) -> None:
    with db.tx() as c:
        c.execute(
            """INSERT INTO lern_ereignis (sitzung_id, von_zustand, nach_zustand,
                    von_phase, nach_phase, anlass, nutzdaten, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (sitzung_id, von_zustand, nach_zustand, von_phase, nach_phase,
             anlass, json.dumps(nutzdaten or {}, ensure_ascii=False), db.now()))


def parent_report_events(since: str, until: str) -> list[dict]:
    """Read-only report projection, deliberately without answers or payloads.

    Earlier mastery events are needed to count a topic's first successful check
    once, not again on every repetition. Timestamp bounds are UTC ISO strings.
    """
    return [dict(r) for r in db.q('''SELECT e.id, e.created_at, e.anlass,
        e.nach_zustand, i.topic_id
        FROM lern_ereignis e JOIN lern_sitzung s ON s.id=e.sitzung_id
        JOIN lern_eingabe i ON i.id=s.eingabe_id
        WHERE s.child_key=? AND i.child_key=? AND i.topic_id IS NOT NULL
          AND julianday(e.created_at)<julianday(?)
          AND (julianday(e.created_at)>=julianday(?) OR e.nach_zustand='MASTERED')
        ORDER BY e.id''', CHILD_KEY, CHILD_KEY, until, since)]


def parent_report_states(until: str) -> dict[int, str | None]:
    """Topic states as of a reporting cutoff, not today's state in old reports."""
    rows = db.q('''SELECT i.topic_id, s.id,
        COALESCE((SELECT e.nach_zustand FROM lern_ereignis e
          WHERE e.sitzung_id=s.id AND e.nach_zustand IS NOT NULL
            AND julianday(e.created_at)<julianday(?) ORDER BY e.id DESC LIMIT 1),
          CASE WHEN julianday(s.updated_at)<julianday(?) THEN s.zustand END) AS state
        FROM lern_sitzung s JOIN lern_eingabe i ON i.id=s.eingabe_id
        WHERE s.child_key=? AND i.child_key=? AND i.topic_id IS NOT NULL
          AND julianday(s.created_at)<julianday(?) ORDER BY s.id''',
        until, until, CHILD_KEY, CHILD_KEY, until)
    return {r['topic_id']: r['state'] for r in rows}


def ereignisse(sitzung_id: int) -> list[dict]:
    eintraege = [dict(r) for r in db.q(
        "SELECT * FROM lern_ereignis WHERE sitzung_id=? ORDER BY id", sitzung_id)]
    for e in eintraege:
        e["nutzdaten"] = _json(e.get("nutzdaten"), {})
    return eintraege


# --------------------------------------------------------------------------
# Fortschritt (§8)
# --------------------------------------------------------------------------

def fortschritt(konzept_id: int, fehlertyp_id: int | None = None,
                child_key: str = CHILD_KEY) -> dict | None:
    if fehlertyp_id is None:
        return _zeile(db.q1(
            """SELECT * FROM lern_fortschritt
                WHERE child_key=? AND konzept_id=? AND fehlertyp_id IS NULL""",
            child_key, konzept_id))
    return _zeile(db.q1(
        """SELECT * FROM lern_fortschritt
            WHERE child_key=? AND konzept_id=? AND fehlertyp_id=?""",
        child_key, konzept_id, fehlertyp_id))


def topic_scope(topic_id: int | None, child_key: str = CHILD_KEY) -> str:
    """Der Lernraum eines Themas — die einzige Stelle, die ihn zusammensetzt.

    'installation' ist der gemeinsame Raum themenloser Sitzungen;
    'installation:topic:<id>' gehoert genau einem Thema. Ein eigenes
    Lernthema und ein Pruefungsthema duerfen auf dasselbe Konzept zeigen —
    ihr Lernstand darf sich trotzdem nie mischen.
    """
    return f"{child_key}:topic:{topic_id}" if topic_id else child_key


def scope_teile(scope: str | None) -> tuple[str, int | None]:
    """Den Scope wieder in (child_key, topic_id) zerlegen — fuer Abfragen,
    die ueber `lern_eingabe.topic_id` filtern muessen."""
    basis, _, topic = (scope or "").partition(":topic:")
    return (basis or CHILD_KEY, int(topic) if topic.isdigit() else None)


def fortschritt_scope(sitzung: dict) -> str:
    """Shared curriculum does not mean shared evidence of mastery."""
    entry = eingabe(sitzung.get("eingabe_id")) or {}
    return topic_scope(entry.get("topic_id"), sitzung.get("child_key", CHILD_KEY))


def fortschritt_buchen(konzept_id: int, fehlertyp_id: int | None, *,
                       versuch: bool = False, erfolg: bool = False,
                       wiederholung: bool = False, mastery: str | None = None,
                       braucht_mensch: bool | None = None,
                       child_key: str = CHILD_KEY) -> None:
    jetzt = db.now()
    with db.tx() as c:
        c.execute(
            """INSERT INTO lern_fortschritt
                   (child_key, konzept_id, fehlertyp_id, created_at, updated_at)
               SELECT ?,?,?,?,? WHERE NOT EXISTS (
                 SELECT 1 FROM lern_fortschritt
                 WHERE child_key=? AND konzept_id=? AND fehlertyp_id IS ?)""",
            (child_key, konzept_id, fehlertyp_id, jetzt, jetzt,
             child_key, konzept_id, fehlertyp_id))
        bedingung = ("fehlertyp_id IS NULL" if fehlertyp_id is None
                     else "fehlertyp_id = ?")
        params: list = [1 if versuch else 0, 1 if erfolg else 0,
                        1 if wiederholung else 0, jetzt, jetzt, child_key,
                        konzept_id]
        setzen = ["versuche = versuche + ?", "erfolge = erfolge + ?",
                  "wiederholungen = wiederholungen + ?",
                  "letzte_aktivitaet = ?", "updated_at = ?"]
        if mastery is not None:
            setzen.insert(0, "mastery = ?")
            params.insert(0, mastery)
        if braucht_mensch is not None:
            setzen.insert(0, "braucht_mensch = ?")
            params.insert(0, 1 if braucht_mensch else 0)
        if fehlertyp_id is not None:
            params.append(fehlertyp_id)
        c.execute(
            f"""UPDATE lern_fortschritt SET {', '.join(setzen)}
                 WHERE child_key=? AND konzept_id=? AND {bedingung}""",
            tuple(params))


def fortschritt_uebersicht(child_key: str = CHILD_KEY) -> list[dict]:
    """Grundlage für den Elternbericht (§18) — beobachtbare Lernsignale."""
    return [dict(r) for r in db.q(
        """SELECT p.*, k.label AS konzept_label, k.fach AS fach,
                  f.label AS fehler_label, f.fehler_key AS fehler_key
             FROM lern_fortschritt p
             JOIN lern_konzept k ON k.id = p.konzept_id
             LEFT JOIN lern_fehlertyp f ON f.id = p.fehlertyp_id
            WHERE (p.child_key = ? OR p.child_key LIKE ?)
            ORDER BY p.letzte_aktivitaet DESC, p.id DESC""", child_key, child_key + ':topic:%')]
