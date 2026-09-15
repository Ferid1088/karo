"""Datenzugriff des Begleiters.

Benutzt Karos Verbindung (`app.db`) und Karos Datenverzeichnis, aber kein
einziges Karo-Tabellenobjekt. Das Schema legt sich beim ersten Aufruf selbst
an; dadurch braucht `app/main.py` genau eine geaenderte Zeile.
"""

from __future__ import annotations

import datetime as dt
import logging
import secrets
import sqlite3
from pathlib import Path

from .. import config, db

log = logging.getLogger("karo.woche")

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

_bereit = False

TAGE = {1: "Montag", 2: "Dienstag", 3: "Mittwoch", 4: "Donnerstag",
        5: "Freitag", 6: "Samstag", 7: "Sonntag"}

FORMEN = {
    "speedrun": {"symbol": "🎮", "label": "Speedrun",
                 "hinweis": "Stoppuhr läuft. Sofort nochmal, wenn du willst."},
    "clip": {"symbol": "📱", "label": "Clip",
             "hinweis": "60 Sekunden erklären. Nur du siehst es."},
    "einfach": {"symbol": "🧘", "label": "Einfach",
                "hinweis": "Nur ein Timer, sonst nichts."},
}


# --------------------------------------------------------------------------
# Einrichtung
# --------------------------------------------------------------------------

def bilder_dir() -> Path:
    pfad = config.DATA_DIR / "woche" / "bilder"
    pfad.mkdir(parents=True, exist_ok=True)
    return pfad


def ensure() -> None:
    """Legt das Schema an. Idempotent, billig, beim ersten Zugriff."""
    global _bereit
    if _bereit:
        return
    c = db.conn()
    c.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    c.execute("INSERT OR IGNORE INTO woche_kind (id) VALUES (1)")
    _nachziehen(c)
    _bereit = True


# Spalten, die spaeter dazugekommen sind. CREATE TABLE IF NOT EXISTS legt sie
# in einer bestehenden Datenbank nicht an — gleiches Muster wie in app/db.py.
_NACHGEZOGEN = [
    ("woche_kind", "karo_bruecke", "INTEGER NOT NULL DEFAULT 0"),
]


def _nachziehen(c) -> None:
    for tabelle, spalte, decl in _NACHGEZOGEN:
        try:
            da = {r["name"] for r in c.execute(f"PRAGMA table_info({tabelle})")}
        except sqlite3.Error:                          # pragma: no cover
            continue
        if da and spalte not in da:
            try:
                c.execute(f"ALTER TABLE {tabelle} ADD COLUMN {spalte} {decl}")
                log.info("Spalte %s.%s ergänzt", tabelle, spalte)
            except sqlite3.Error as exc:               # pragma: no cover
                log.warning("Konnte %s.%s nicht ergänzen: %s", tabelle, spalte, exc)


def reset_cache() -> None:
    """Nur fuer Tests: erzwingt ein erneutes ensure()."""
    global _bereit
    _bereit = False


# --------------------------------------------------------------------------
# Kind
# --------------------------------------------------------------------------

def kind() -> sqlite3.Row:
    ensure()
    return db.q1("SELECT * FROM woche_kind WHERE id=1")


def kind_setzen(**felder) -> None:
    erlaubt = {"name", "klasse", "plan_bild", "anstupser_anker",
               "anstupser_aus", "frage_index", "eingerichtet_am",
               "karo_bruecke"}
    felder = {k: v for k, v in felder.items() if k in erlaubt}
    if not felder:
        return
    sql = ", ".join(f"{k}=?" for k in felder)
    with db.tx() as c:
        c.execute(f"UPDATE woche_kind SET {sql} WHERE id=1", tuple(felder.values()))


def eingerichtet() -> bool:
    k = kind()
    return bool(k and k["eingerichtet_am"])


# --------------------------------------------------------------------------
# Faecher und Stundenplan
# --------------------------------------------------------------------------

def faecher(nur_aktive: bool = True) -> list[sqlite3.Row]:
    ensure()
    if nur_aktive:
        return db.q("SELECT * FROM woche_fach WHERE aktiv=1 ORDER BY name")
    return db.q("SELECT * FROM woche_fach ORDER BY name")


def fach(fach_id: int) -> sqlite3.Row | None:
    return db.q1("SELECT * FROM woche_fach WHERE id=?", fach_id)


def fach_nach_name(name: str) -> sqlite3.Row | None:
    return db.q1("SELECT * FROM woche_fach WHERE name=?", name)


def faecher_setzen(namen: list[str]) -> None:
    """Setzt die Fachliste. Bestehende Faecher bleiben erhalten."""
    ensure()
    namen = [n.strip() for n in namen if n and n.strip()]
    with db.tx() as c:
        c.execute("UPDATE woche_fach SET aktiv=0")
        for name in namen:
            c.execute(
                "INSERT INTO woche_fach (name, aktiv, created_at) VALUES (?,1,?) "
                "ON CONFLICT(name) DO UPDATE SET aktiv=1",
                (name, db.now()))


def stunden_setzen(fach_id: int, tage: list[int]) -> None:
    with db.tx() as c:
        c.execute("DELETE FROM woche_stunde WHERE fach_id=?", (fach_id,))
        for tag in sorted(set(t for t in tage if 1 <= t <= 5)):
            c.execute("INSERT INTO woche_stunde (fach_id, tag, stunde) "
                      "VALUES (?,?,1)", (fach_id, tag))
        c.execute("UPDATE woche_fach SET stunden=? WHERE id=?",
                  (len(set(tage)), fach_id))


def stundenplan() -> dict[int, list[sqlite3.Row]]:
    """Tag -> Faecher."""
    ensure()
    plan: dict[int, list[sqlite3.Row]] = {t: [] for t in range(1, 6)}
    for zeile in db.q(
            "SELECT s.tag, f.id, f.name FROM woche_stunde s "
            "JOIN woche_fach f ON f.id=s.fach_id WHERE f.aktiv=1 "
            "ORDER BY s.tag, s.stunde, f.name"):
        plan[zeile["tag"]].append(zeile)
    return plan


def faecher_am_tag(tag: int) -> list[sqlite3.Row]:
    return db.q(
        "SELECT f.* FROM woche_stunde s JOIN woche_fach f ON f.id=s.fach_id "
        "WHERE s.tag=? AND f.aktiv=1 ORDER BY s.stunde", tag)


def naechster_tag_mit(fach_id: int, ab_tag: int) -> int | None:
    """Wann ist dieses Fach das naechste Mal dran? Fuer die Hausaufgabenfrist."""
    tage = [z["tag"] for z in db.q(
        "SELECT DISTINCT tag FROM woche_stunde WHERE fach_id=? ORDER BY tag",
        fach_id)]
    if not tage:
        return None
    spaeter = [t for t in tage if t > ab_tag]
    return spaeter[0] if spaeter else tage[0]


# --------------------------------------------------------------------------
# Termine und Helfer
# --------------------------------------------------------------------------

def termine() -> list[sqlite3.Row]:
    ensure()
    return db.q("SELECT * FROM woche_termin ORDER BY tag, zeit")


def termin_anlegen(label: str, tag: int, zeit: str = "") -> None:
    with db.tx() as c:
        c.execute("INSERT INTO woche_termin (label, tag, zeit) VALUES (?,?,?)",
                  (label.strip()[:60], tag, zeit.strip()[:10]))


def helfer(nur_aktive: bool = True) -> list[sqlite3.Row]:
    ensure()
    sql = ("SELECT h.*, f.name AS fach_name FROM woche_helfer h "
           "LEFT JOIN woche_fach f ON f.id=h.fach_id")
    if nur_aktive:
        sql += " WHERE h.aktiv=1"
    return db.q(sql + " ORDER BY h.id")


def helfer_anlegen(name: str, fach_id: int | None = None,
                   fester_tag: int | None = None,
                   feste_zeit: str = "") -> int:
    ensure()
    with db.tx() as c:
        cur = c.execute(
            "INSERT INTO woche_helfer (name, fach_id, fester_tag, feste_zeit, "
            "created_at) VALUES (?,?,?,?,?)",
            (name.strip()[:40], fach_id, fester_tag, feste_zeit.strip()[:10],
             db.now()))
        return int(cur.lastrowid)


def fester_termin() -> sqlite3.Row | None:
    ensure()
    return db.q1("SELECT * FROM woche_helfer WHERE aktiv=1 AND fester_tag "
                 "IS NOT NULL ORDER BY id LIMIT 1")


# --------------------------------------------------------------------------
# Mein Ding
# --------------------------------------------------------------------------

def ding() -> sqlite3.Row | None:
    ensure()
    return db.q1("SELECT * FROM woche_ding WHERE aktiv=1 ORDER BY id DESC LIMIT 1")


def ding_setzen(wort: str, form: str, bild: str | None = None) -> int:
    """Ein neues Ding ersetzt das alte. Keine Historie — das waere peinlich."""
    ensure()
    form = form if form in FORMEN else "einfach"
    with db.tx() as c:
        c.execute("UPDATE woche_ding SET aktiv=0")
        cur = c.execute(
            "INSERT INTO woche_ding (wort, form, bild, freigabe, created_at) "
            "VALUES (?,?,?,'offen',?)",
            (wort.strip()[:40], form, bild, db.now()))
        return int(cur.lastrowid)


def ding_freigeben(ding_id: int, ja: bool) -> None:
    with db.tx() as c:
        c.execute("UPDATE woche_ding SET freigabe=? WHERE id=?",
                  ("ja" if ja else "nein", ding_id))


def ding_bild_speichern(daten: bytes, endung: str) -> str:
    """Legt ein Bild ab und gibt den Dateinamen zurueck."""
    endung = endung.lower()
    if endung not in (".jpg", ".jpeg", ".png", ".webp", ".heic"):
        endung = ".jpg"
    name = f"ding_{secrets.token_hex(8)}{endung}"
    (bilder_dir() / name).write_bytes(daten)
    return name


def datum_kurz(iso: str) -> str:
    """2026-09-21 -> „Montag, 21.9." — ein Kind liest keine ISO-Daten."""
    try:
        d = dt.date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ""
    return f"{TAGE[d.isoweekday()]}, {d.day}.{d.month}."


def wort_oder_form(d: sqlite3.Row | None) -> str:
    """Bis die Eltern freigeben, sagt die App die Form statt des Wortes.

    Nichts ist blockiert, nur unpersoenlicher."""
    if d is None:
        return "deine Sache"
    if d["freigabe"] == "ja":
        return d["wort"]
    return FORMEN.get(d["form"], FORMEN["einfach"])["label"]


# --------------------------------------------------------------------------
# Zyklus
# --------------------------------------------------------------------------

def heute() -> dt.date:
    return dt.date.today()


def wochentag() -> int:
    return heute().isoweekday()


def zyklus() -> sqlite3.Row | None:
    """Der laufende Zyklus, falls einer laeuft und nicht abgelaufen ist."""
    ensure()
    return db.q1("SELECT * FROM woche_zyklus WHERE status='offen' "
                 "AND ende >= ? ORDER BY id DESC LIMIT 1", db.today())


def zyklus_faellig() -> sqlite3.Row | None:
    """Ein offener Zyklus, dessen Ende vorbei ist — wartet auf den Abschluss."""
    ensure()
    return db.q1("SELECT * FROM woche_zyklus WHERE status='offen' "
                 "AND ende < ? ORDER BY id DESC LIMIT 1", db.today())


def zyklus_starten(fokus: str, laenge: int = 7, still: bool = False) -> int:
    ensure()
    start = heute()
    ende = start + dt.timedelta(days=max(1, laenge) - 1)
    with db.tx() as c:
        c.execute("UPDATE woche_zyklus SET status='fertig' WHERE status='offen'")
        cur = c.execute(
            "INSERT INTO woche_zyklus (start, ende, fokus, laenge, still, "
            "created_at) VALUES (?,?,?,?,?,?)",
            (start.isoformat(), ende.isoformat(), fokus.strip()[:80], laenge,
             1 if still else 0, db.now()))
        zid = int(cur.lastrowid)
        c.execute("INSERT INTO woche_ereignis (zyklus_id, tag, art, wert, "
                  "created_at) VALUES (?,?,'zyklus_start',?,?)",
                  (zid, wochentag(), str(laenge), db.now()))
    return zid


def zyklus_abschliessen(zyklus_id: int, gefuehl: str, wunsch: str) -> None:
    with db.tx() as c:
        c.execute("UPDATE woche_zyklus SET status='fertig', gefuehl=?, wunsch=? "
                  "WHERE id=?", (gefuehl, wunsch, zyklus_id))
        c.execute("INSERT INTO woche_ereignis (zyklus_id, tag, art, wert, "
                  "notiz, created_at) VALUES (?,?,'zyklus_ende',?,?,?)",
                  (zyklus_id, wochentag(), gefuehl, wunsch, db.now()))


def letzte_zyklen(n: int = 6) -> list[sqlite3.Row]:
    ensure()
    return db.q("SELECT * FROM woche_zyklus ORDER BY id DESC LIMIT ?", n)


# --------------------------------------------------------------------------
# Anker und Schritte
# --------------------------------------------------------------------------

def anker(zyklus_id: int, fach_id: int) -> sqlite3.Row | None:
    return db.q1("SELECT * FROM woche_anker WHERE zyklus_id=? AND fach_id=?",
                 zyklus_id, fach_id)


def anker_setzen(zyklus_id: int, fach_id: int, text: str) -> None:
    with db.tx() as c:
        c.execute(
            "INSERT INTO woche_anker (zyklus_id, fach_id, text, created_at) "
            "VALUES (?,?,?,?) ON CONFLICT(zyklus_id, fach_id) "
            "DO UPDATE SET text=excluded.text",
            (zyklus_id, fach_id, text.strip()[:120], db.now()))


def anker_fehlend_heute(zyklus_id: int) -> sqlite3.Row | None:
    """Ein Fach, das heute Unterricht hatte und noch keinen Anker hat."""
    for f in faecher_am_tag(wochentag()):
        if anker(zyklus_id, f["id"]) is None:
            return f
    return None


def schritte(zyklus_id: int) -> list[sqlite3.Row]:
    return db.q(
        "SELECT s.*, f.name AS fach_name FROM woche_schritt s "
        "LEFT JOIN woche_fach f ON f.id=s.fach_id "
        "WHERE s.zyklus_id=? AND s.ruht=0 ORDER BY s.id", zyklus_id)


def schritt(schritt_id: int) -> sqlite3.Row | None:
    return db.q1(
        "SELECT s.*, f.name AS fach_name FROM woche_schritt s "
        "LEFT JOIN woche_fach f ON f.id=s.fach_id WHERE s.id=?", schritt_id)


def schritt_anlegen(zyklus_id: int, fach_id: int | None, titel: str,
                    einstieg: str, groesse: str = "klein",
                    anlass: str = "normal", form: str = "einfach") -> int:
    with db.tx() as c:
        cur = c.execute(
            "INSERT INTO woche_schritt (zyklus_id, fach_id, titel, einstieg, "
            "groesse, anlass, form, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (zyklus_id, fach_id, titel[:120], einstieg[:240], groesse, anlass,
             form, db.now()))
        return int(cur.lastrowid)


def schritt_anpassen(schritt_id: int, titel: str, einstieg: str,
                     groesse: str) -> None:
    with db.tx() as c:
        c.execute("UPDATE woche_schritt SET titel=?, einstieg=?, groesse=?, "
                  "verkleinert=verkleinert+1 WHERE id=?",
                  (titel[:120], einstieg[:240], groesse, schritt_id))


def schritt_ruhen(schritt_id: int) -> None:
    with db.tx() as c:
        c.execute("UPDATE woche_schritt SET ruht=1 WHERE id=?", (schritt_id,))


# --------------------------------------------------------------------------
# Ereignisse — append only
# --------------------------------------------------------------------------

def ereignis(art: str, wert: str | None = None, *, zyklus_id: int | None = None,
             schritt_id: int | None = None, fach_id: int | None = None,
             notiz: str | None = None) -> None:
    ensure()
    with db.tx() as c:
        c.execute(
            "INSERT INTO woche_ereignis (zyklus_id, schritt_id, fach_id, tag, "
            "art, wert, notiz, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (zyklus_id, schritt_id, fach_id, wochentag(), art,
             None if wert is None else str(wert)[:80],
             None if notiz is None else str(notiz)[:400], db.now()))


def ereignisse(zyklus_id: int, art: str | None = None) -> list[sqlite3.Row]:
    if art:
        return db.q("SELECT * FROM woche_ereignis WHERE zyklus_id=? AND art=? "
                    "ORDER BY id", zyklus_id, art)
    return db.q("SELECT * FROM woche_ereignis WHERE zyklus_id=? ORDER BY id",
                zyklus_id)


def heute_schon(schritt_id: int) -> bool:
    """Wurde dieser Schritt heute schon angefangen?"""
    zeile = db.q1(
        "SELECT 1 AS da FROM woche_ereignis WHERE schritt_id=? AND art='einstieg' "
        "AND wert='gemacht' AND substr(created_at,1,10)=? LIMIT 1",
        schritt_id, db.today())
    return zeile is not None


# --------------------------------------------------------------------------
# Karten
# --------------------------------------------------------------------------

def karten() -> list[sqlite3.Row]:
    ensure()
    return db.q("SELECT * FROM woche_karte ORDER BY id DESC")


def karte_anlegen(thema: str, bild: str | None) -> None:
    with db.tx() as c:
        c.execute("INSERT INTO woche_karte (thema, bild, created_at) "
                  "VALUES (?,?,?)", (thema.strip()[:80], bild, db.now()))


# --------------------------------------------------------------------------
# Pause
# --------------------------------------------------------------------------

def pause_aktiv() -> sqlite3.Row | None:
    ensure()
    return db.q1("SELECT * FROM woche_pause WHERE bis >= ? "
                 "ORDER BY id DESC LIMIT 1", db.today())


def pause_setzen(wochen: int) -> None:
    ensure()
    von = heute()
    bis = von + dt.timedelta(weeks=max(1, wochen))
    with db.tx() as c:
        c.execute("UPDATE woche_zyklus SET status='fertig' WHERE status='offen'")
        c.execute("INSERT INTO woche_pause (von, bis, created_at) VALUES (?,?,?)",
                  (von.isoformat(), bis.isoformat(), db.now()))
        c.execute("INSERT INTO woche_ereignis (tag, art, wert, created_at) "
                  "VALUES (?,'pause',?,?)", (wochentag(), str(wochen), db.now()))


def pause_beenden() -> None:
    """Rueckkehr ist ein Tap. Kein Rueckblick, kein Aufholen."""
    ensure()
    gestern = (heute() - dt.timedelta(days=1)).isoformat()
    with db.tx() as c:
        c.execute("UPDATE woche_pause SET bis=? WHERE bis >= ?",
                  (gestern, db.today()))


# --------------------------------------------------------------------------
# Eltern
# --------------------------------------------------------------------------

def zusagen() -> set[int]:
    ensure()
    return {z["nr"] for z in db.q("SELECT nr FROM woche_eltern_zusage")}


def zusage_setzen(nr: int) -> None:
    with db.tx() as c:
        c.execute("INSERT OR IGNORE INTO woche_eltern_zusage (nr, bestaetigt_am) "
                  "VALUES (?,?)", (nr, db.now()))


def offene_freigaben() -> list[sqlite3.Row]:
    ensure()
    return db.q("SELECT * FROM woche_ding WHERE aktiv=1 AND freigabe='offen'")
