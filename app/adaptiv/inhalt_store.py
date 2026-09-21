"""Repository für Aufgaben und Hilfetexte — zweite Hälfte der Speicherschicht.

Eigene Datei, damit `store.py` überschaubar bleibt; gehört fachlich zur selben
Schicht und wandert in Meilenstein 4 mit (01_ARCHITECTURE.md §10).
"""

from __future__ import annotations

import json

from .. import db
from .store import _json, _zeile          # eine Aufbereitung, nicht zwei

# Rollen einer Aufgabe im Unterrichtsablauf (02_LESSON_BRUECHE.md §1)
BEISPIEL = "beispiel"
GEFUEHRT = "gefuehrt"
SELBSTSTAENDIG = "selbststaendig"

# Arten gespeicherter Hilfe (02 §5/§6)
HILFE_PHASE = "phase"
HILFE_FAQ = "faq"


def _aufgabe_aufbereiten(row) -> dict | None:
    eintrag = _zeile(row)
    if eintrag is None:
        return None
    eintrag["tipps"] = _json(eintrag.get("tipps"), [])
    eintrag["schritte"] = _json(eintrag.get("schritte"), [])
    eintrag["visualisierung"] = _json(eintrag.get("visualisierung"), None)
    return eintrag


def aufgabe_sichern(fehlertyp_id: int, rolle: str, frage: str, loesung: str,
                    tipps: list | None = None, schritte: list | None = None,
                    visualisierung: dict | None = None,
                    schwierigkeit: int = 1, position: int = 0,
                    typischer_fehler: str | None = None) -> int:
    """Idempotent über (fehlertyp, rolle, position) — erneutes Säen ändert nur."""
    werte = (json.dumps(tipps or [], ensure_ascii=False),
             json.dumps(schritte or [], ensure_ascii=False),
             json.dumps(visualisierung, ensure_ascii=False) if visualisierung else None)
    with db.tx() as c:
        vorhanden = c.execute(
            "SELECT id FROM lern_aufgabe WHERE fehlertyp_id=? AND rolle=? AND position=?",
            (fehlertyp_id, rolle, position)).fetchone()
        if vorhanden:
            c.execute(
                """UPDATE lern_aufgabe SET frage=?, loesung=?, typischer_fehler=?,
                       tipps=?, schritte=?, visualisierung=?, schwierigkeit=?,
                       aktiv=1 WHERE id=?""",
                (frage, loesung, typischer_fehler, *werte, schwierigkeit,
                 vorhanden["id"]))
            return vorhanden["id"]
        return c.execute(
            """INSERT INTO lern_aufgabe (fehlertyp_id, rolle, position, frage,
                    loesung, typischer_fehler, tipps, schritte, visualisierung,
                    schwierigkeit, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (fehlertyp_id, rolle, position, frage, loesung, typischer_fehler,
             *werte, schwierigkeit, db.now())).lastrowid


def aufgabe(fehlertyp_id: int, rolle: str, position: int = 0) -> dict | None:
    return _aufgabe_aufbereiten(db.q1(
        """SELECT * FROM lern_aufgabe
            WHERE fehlertyp_id=? AND rolle=? AND position=? AND aktiv=1""",
        fehlertyp_id, rolle, position))


def aufgaben(fehlertyp_id: int, rolle: str | None = None) -> list[dict]:
    sql = "SELECT * FROM lern_aufgabe WHERE fehlertyp_id=? AND aktiv=1"
    params: list = [fehlertyp_id]
    if rolle:
        sql += " AND rolle=?"
        params.append(rolle)
    sql += " ORDER BY rolle, position"
    return [_aufgabe_aufbereiten(r) for r in db.q(sql, *params)]


# --------------------------------------------------------------------------
# Hilfe
# --------------------------------------------------------------------------

def hilfe_sichern(konzept_id: int, art: str, schluessel: str, text: str,
                  bilder: list | None = None, sortierung: int = 0,
                  geprueft: bool = True) -> int:
    bilder_json = json.dumps(bilder or [], ensure_ascii=False)
    with db.tx() as c:
        vorhanden = c.execute(
            "SELECT id FROM lern_hilfe WHERE konzept_id=? AND art=? AND schluessel=?",
            (konzept_id, art, schluessel)).fetchone()
        if vorhanden:
            c.execute(
                """UPDATE lern_hilfe SET text=?, bilder=?, sortierung=?,
                       geprueft_am=?, aktiv=1 WHERE id=?""",
                (text, bilder_json, sortierung,
                 db.now() if geprueft else None, vorhanden["id"]))
            return vorhanden["id"]
        return c.execute(
            """INSERT INTO lern_hilfe (konzept_id, art, schluessel, text,
                    bilder, sortierung, geprueft_am, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (konzept_id, art, schluessel, text, bilder_json, sortierung,
             db.now() if geprueft else None, db.now())).lastrowid


def _hilfe_aufbereiten(row) -> dict | None:
    eintrag = _zeile(row)
    if eintrag is None:
        return None
    eintrag["bilder"] = _json(eintrag.get("bilder"), [])
    return eintrag


def hilfe_fuer_phase(konzept_id: int, phase: str) -> dict | None:
    """§11: Ungeprüftes wird nicht ausgeliefert — auch keine Hilfe."""
    return _hilfe_aufbereiten(db.q1(
        """SELECT * FROM lern_hilfe
            WHERE konzept_id=? AND art=? AND schluessel=? AND aktiv=1
              AND geprueft_am IS NOT NULL""",
        konzept_id, HILFE_PHASE, phase))


def faq(konzept_id: int) -> list[dict]:
    return [_hilfe_aufbereiten(r) for r in db.q(
        """SELECT * FROM lern_hilfe
            WHERE konzept_id=? AND art=? AND aktiv=1 AND geprueft_am IS NOT NULL
            ORDER BY sortierung, id""", konzept_id, HILFE_FAQ)]
