"""Die Brücke zu Karo — die einzige Datei im Modul, die Karo kennt.

Der Begleiter bleibt eigenständig. Diese Datei ist das schmale, einseitige
Fenster, durch das er hinüberschaut:

    Woche  ──liest──▶  Karo        erlaubt
    Karo   ──────────▶  Woche      niemals

Drei Regeln, die den Rest des Moduls sauber halten:

1. **Nur hier.** Kein anderes File in `app/woche/` importiert Karo-Logik oder
   liest eine Karo-Tabelle. Ein Test hält das fest.
2. **Immer optional.** Jede Funktion gibt einen neutralen Wert zurück, wenn
   Karo nichts weiß, noch nicht eingerichtet ist oder die Tabelle gar nicht
   existiert. Der Begleiter muss ohne Karo vollständig funktionieren — und
   ohne Brücke genauso.
3. **Nur lesen.** Keine Funktion schreibt in eine Karo-Tabelle. Karos Flaggen
   entstehen weiterhin ausschließlich aus freigegebenen Antworten.

Eine Eigenheit, die man leicht übersieht: **Karo deckt genau ein Fach ab**
(`config.subject`), der Begleiter alle. Jede Auskunft hier gilt deshalb immer
nur für dieses eine Fach; für alle anderen bleibt der Begleiter bei seiner
eigenen Tabelle.
"""

from __future__ import annotations

import json
import logging
import sqlite3

from .. import config, db

log = logging.getLogger("karo.woche.bruecke")

# Karos Flaggen in der Reihenfolge, in der sie den Begleiter interessieren.
LUECKE = ("rot", "gelb")


def _tabelle_da(name: str) -> bool:
    try:
        return db.q1("SELECT 1 AS da FROM sqlite_master WHERE type='table' "
                     "AND name=?", name) is not None
    except sqlite3.Error:                              # pragma: no cover
        return False


def karo_fach() -> str:
    """Das eine Fach, das Karo abdeckt — oder ''."""
    try:
        return (config.load_safe().subject or "").strip()
    except Exception:                                  # pragma: no cover
        return ""


def zustaendig(fach_name: str) -> bool:
    """Deckt Karo dieses Fach ab?"""
    k = karo_fach().lower()
    f = (fach_name or "").strip().lower()
    if not k or not f:
        return False
    return k == f or k.startswith(f[:4]) or f.startswith(k[:4])


def aktiv(fach_name: str = "") -> bool:
    """Ist die Brücke benutzbar? Schaltbar, prüfbar, standardmäßig aus."""
    from . import store

    k = store.kind()
    if not k or not k["karo_bruecke"]:
        return False
    if not _tabelle_da("topic_flag"):
        return False
    if fach_name and not zustaendig(fach_name):
        return False
    return True


# --------------------------------------------------------------------------
# Was Karo weiß
# --------------------------------------------------------------------------

def luecken(fach_name: str, grenze: int = 3) -> list[dict]:
    """Themen mit roter oder gelber Flagge, rot zuerst.

    Das ist die wertvollste Auskunft: Karo weiß aus freigegebenen Antworten,
    wo es hakt — der Begleiter weiß das nie, er zählt nur Anfänge.
    """
    if not aktiv(fach_name):
        return []
    try:
        zeilen = db.q(
            "SELECT t.label, t.code, f.flag, f.haupt_fehler "
            "FROM topic t JOIN topic_flag f ON f.topic_id = t.id "
            "WHERE t.subject = ? AND t.state = 'aktiv' AND f.flag IN (?, ?) "
            "ORDER BY CASE f.flag WHEN 'rot' THEN 0 ELSE 1 END, "
            "         COALESCE(f.letzte_uebung, '') "
            "LIMIT ?", karo_fach(), LUECKE[0], LUECKE[1], grenze)
    except sqlite3.Error as exc:                        # pragma: no cover
        log.debug("Brücke: Lücken nicht lesbar (%s)", exc)
        return []
    return [{"label": z["label"], "code": z["code"], "flag": z["flag"]}
            for z in zeilen]


def naechste_arbeit(fach_name: str) -> dict | None:
    """Die nächste eingetragene Klassenarbeit: Datum, Tage, Themen."""
    if not aktiv(fach_name) or not _tabelle_da("exam"):
        return None
    try:
        z = db.q1("SELECT exam_date, titel, themen FROM exam "
                  "WHERE subject = ? AND exam_date >= ? "
                  "ORDER BY exam_date LIMIT 1", karo_fach(), db.today())
    except sqlite3.Error:                               # pragma: no cover
        return None
    if z is None:
        return None
    import datetime as dt
    try:
        tage = (dt.date.fromisoformat(z["exam_date"]) - dt.date.today()).days
    except (TypeError, ValueError):                     # pragma: no cover
        return None
    try:
        themen = json.loads(z["themen"] or "[]")
    except json.JSONDecodeError:                        # pragma: no cover
        themen = []
    return {"datum": z["exam_date"], "tage": tage, "titel": z["titel"] or "",
            "themen": themen if isinstance(themen, list) else []}


def ankervorschlag(fach_name: str) -> str:
    """Was zuletzt aus dem Unterricht eingelesen wurde.

    Spart dem Kind die eine Zeile Tippen — mehr soll es nicht sein. Der
    Vorschlag wird angeboten, nie gesetzt: der Anker gehört dem Kind.
    """
    if not aktiv(fach_name) or not _tabelle_da("document"):
        return ""
    try:
        z = db.q1("SELECT themenname FROM document "
                  "WHERE themenname IS NOT NULL AND TRIM(themenname) <> '' "
                  "ORDER BY id DESC LIMIT 1")
    except sqlite3.Error:                               # pragma: no cover
        return ""
    return (z["themenname"] or "").strip()[:120] if z else ""


def lerneinheit(thema_label: str) -> int | None:
    """Gibt es zu diesem Thema schon eine fertige Erklärung in Karo?"""
    if not _tabelle_da("lesson") or not thema_label:
        return None
    try:
        z = db.q1("SELECT l.id FROM lesson l JOIN topic t ON t.id = l.topic_id "
                  "WHERE t.label = ? AND l.state IN ('bereit','wartet','gelernt') "
                  "ORDER BY l.id DESC LIMIT 1", thema_label)
    except sqlite3.Error:                               # pragma: no cover
        return None
    return int(z["id"]) if z else None


# --------------------------------------------------------------------------
# Was der Begleiter daraus macht
# --------------------------------------------------------------------------

def anlass(fach_name: str) -> str | None:
    """Karos Sicht auf den Anlass — oder None, dann entscheidet der Begleiter.

    Nur das Datum zählt, nicht Karos Einschätzung: ob es eng wird, ist eine
    Frage des Kalenders, keine Bewertung des Kindes.
    """
    a = naechste_arbeit(fach_name)
    if a is None:
        return None
    if a["tage"] <= 1:
        return "morgen"
    if a["tage"] <= 7:
        return "arbeit_nah"
    if a["tage"] <= 21:
        return "arbeit_fern"
    return None


def titelzusatz(fach_name: str) -> str:
    """Macht „das schwierigste Thema üben" zu „Brüche addieren üben".

    Ohne Karo bleibt der Titel allgemein — das ist kein Mangel, sondern der
    Normalfall für alle Fächer außer dem einen, das Karo kennt.
    """
    l = luecken(fach_name, grenze=1)
    return l[0]["label"] if l else ""


def hinweis(fach_name: str) -> str:
    """Ein Satz für den Wochenstart. Nie mehr als einer."""
    a = naechste_arbeit(fach_name)
    if a is None:
        return ""
    if a["tage"] == 0:
        return f"Heute ist die {a['titel'] or 'Arbeit'}."
    if a["tage"] == 1:
        return f"Morgen ist die {a['titel'] or 'Arbeit'}."
    return f"In {a['tage']} Tagen ist die {a['titel'] or 'Arbeit'}."
