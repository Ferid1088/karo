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


def init() -> None:
    db.conn().executescript(
        Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))


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

def konzept_sichern(fach: str, thema_key: str, konzept_key: str, label: str,
                    klasse_von: int = 1, klasse_bis: int = 13) -> int:
    with db.tx() as c:
        vorhanden = c.execute(
            "SELECT id FROM lern_konzept WHERE fach=? AND thema_key=? AND konzept_key=?",
            (fach, thema_key, konzept_key)).fetchone()
        if vorhanden:
            return vorhanden["id"]
        return c.execute(
            """INSERT INTO lern_konzept (fach, thema_key, konzept_key, label,
                                         klasse_von, klasse_bis, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (fach, thema_key, konzept_key, label, klasse_von, klasse_bis,
             db.now())).lastrowid


def konzept(konzept_id: int) -> dict | None:
    return _zeile(db.q1("SELECT * FROM lern_konzept WHERE id=?", konzept_id))


def konzept_nach_key(fach: str, thema_key: str, konzept_key: str) -> dict | None:
    return _zeile(db.q1(
        "SELECT * FROM lern_konzept WHERE fach=? AND thema_key=? AND konzept_key=?",
        fach, thema_key, konzept_key))


def fehlertyp_sichern(konzept_id: int, fehler_key: str, label: str,
                      beschreibung: str = "") -> int:
    with db.tx() as c:
        vorhanden = c.execute(
            "SELECT id FROM lern_fehlertyp WHERE konzept_id=? AND fehler_key=?",
            (konzept_id, fehler_key)).fetchone()
        if vorhanden:
            return vorhanden["id"]
        return c.execute(
            """INSERT INTO lern_fehlertyp (konzept_id, fehler_key, label,
                                           beschreibung, created_at)
               VALUES (?,?,?,?,?)""",
            (konzept_id, fehler_key, label, beschreibung or None,
             db.now())).lastrowid


def fehlertyp(fehlertyp_id: int) -> dict | None:
    return _zeile(db.q1("SELECT * FROM lern_fehlertyp WHERE id=?", fehlertyp_id))


def fehlertypen(konzept_id: int) -> list[dict]:
    return [dict(r) for r in db.q(
        "SELECT * FROM lern_fehlertyp WHERE konzept_id=? AND aktiv=1 ORDER BY id",
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
            ORDER BY f.id LIMIT 1""", muster, konzept_id))


# --------------------------------------------------------------------------
# Erklärungen (§6): versionieren, nie destruktiv ersetzen
# --------------------------------------------------------------------------

def erklaerung_anlegen(fehlertyp_id: int, klasse: int, inhalt: dict,
                       visualisierung: dict | None = None,
                       aufgabe: dict | None = None, schwierigkeit: int = 1,
                       quelle: str = "kuratiert",
                       geprueft: bool = False) -> int:
    jetzt = db.now()
    with db.tx() as c:
        letzte = c.execute(
            "SELECT MAX(version) AS v FROM lern_erklaerung WHERE fehlertyp_id=? AND klasse=?",
            (fehlertyp_id, klasse)).fetchone()
        version = (letzte["v"] or 0) + 1
        return c.execute(
            """INSERT INTO lern_erklaerung
                   (fehlertyp_id, klasse, version, inhalt, visualisierung,
                    aufgabe, schwierigkeit, quelle, geprueft_am, created_at,
                    updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (fehlertyp_id, klasse, version,
             json.dumps(inhalt, ensure_ascii=False),
             json.dumps(visualisierung, ensure_ascii=False) if visualisierung else None,
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
    sql.append("ORDER BY ABS(klasse - ?), schwierigkeit DESC, version DESC LIMIT 1")
    params.append(klasse)
    return _erklaerung_aufbereiten(db.q1(" ".join(sql), *params))


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
                    document_id: int | None = None,
                    aufgaben: list | None = None,
                    konfidenz: float | None = None,
                    child_key: str = CHILD_KEY) -> int:
    with db.tx() as c:
        return c.execute(
            """INSERT INTO lern_eingabe (child_key, art, fach, thema_text,
                    konzept_id, document_id, aufgaben, konfidenz, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (child_key, art, fach, thema_text, konzept_id, document_id,
             json.dumps(aufgaben or [], ensure_ascii=False), konfidenz,
             db.now())).lastrowid


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


def fortschritt_buchen(konzept_id: int, fehlertyp_id: int | None, *,
                       versuch: bool = False, erfolg: bool = False,
                       wiederholung: bool = False, mastery: str | None = None,
                       braucht_mensch: bool | None = None,
                       child_key: str = CHILD_KEY) -> None:
    jetzt = db.now()
    with db.tx() as c:
        c.execute(
            """INSERT OR IGNORE INTO lern_fortschritt
                   (child_key, konzept_id, fehlertyp_id, created_at, updated_at)
               VALUES (?,?,?,?,?)""",
            (child_key, konzept_id, fehlertyp_id, jetzt, jetzt))
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
            WHERE p.child_key = ?
            ORDER BY p.letzte_aktivitaet DESC, p.id DESC""", child_key)]
