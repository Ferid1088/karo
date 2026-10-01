"""Einzelne Antworten und die aktive Zeit an einer Aufgabe (Schritt 4a).

Dritte Datei der Speicherschicht neben `store.py` und `inhalt_store.py`: §10
verlangt, dass SQL der `lern_`-Tabellen in dieser Schicht bleibt, nicht dass
es in einer einzigen Datei steht.

Warum es diese Tabelle gibt: Karo wusste bisher nur, wie eine Sitzung ausging.
Was ein Kind auf eine einzelne Aufgabe geantwortet hat und wie lange es daran
war, stand nirgends. Ohne das gibt es weder eine ehrliche Lernzeit noch eine
Wiederholung, die neue Aufgaben stellt statt derselben.

Die aktive Zeit ist bewusst **nicht** `learning_time`: das misst Anwesenheit
(ein Schlag alle 30 s) und traegt den Elternbericht. Hier geht es um Arbeit an
einer Aufgabe — und eine Seite, die offen steht, waehrend niemand davor sitzt,
ist keine Arbeit.
"""

from __future__ import annotations

import datetime as dt

from .. import db
from .store import CHILD_KEY, _zeile

#: Rollen, unter denen eine Antwort protokolliert wird.
ANKER = "anker"
DIAGNOSE = "diagnose"
VORHERSAGE = "vorhersage"
AUFGABE = "aufgabe"
TRANSFER = "transfer"
VORAUSSETZUNG = "voraussetzung"
WIEDERHOLUNG = "wiederholung"

#: Grundzeit je Antwortart in Sekunden, geeicht auf Klasse 6. Eine Auswahl
#: ist schneller entschieden als eine Rechnung, und ein geschriebener Satz
#: dauert laenger als beides.
_GRUNDZEIT = {"auswahl": 25, "bruch": 60, "text": 90}

#: Je Klassenstufe unter 6 etwas mehr Zeit, darueber etwas weniger. Gedeckelt,
#: damit aus einer Klassenangabe keine absurde Zahl wird.
_SPANNE = (0.6, 1.8)


def _jetzt() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _zeit(wert: str | None) -> dt.datetime | None:
    if not wert:
        return None
    try:
        gelesen = dt.datetime.fromisoformat(wert)
    except ValueError:
        return None
    return gelesen if gelesen.tzinfo else gelesen.replace(tzinfo=dt.timezone.utc)


def erwartung(antwort_art: str | None, klasse: int | None = None,
              vorgabe: int | None = None) -> int:
    """Wie lange diese Aufgabe ueblicherweise dauert, in Sekunden.

    `vorgabe` kommt aus dem Curriculum und schlaegt jede Schaetzung: wer die
    Aufgabe geschrieben hat, weiss besser, wie lange sie dauert.
    """
    if vorgabe:
        return max(5, int(vorgabe))
    basis = _GRUNDZEIT.get((antwort_art or "bruch").lower(), _GRUNDZEIT["bruch"])
    stufe = int(klasse or 6)
    faktor = min(_SPANNE[1], max(_SPANNE[0], 1 + (6 - stufe) * 0.08))
    return max(5, round(basis * faktor))


# --------------------------------------------------------------------------
# Die Uhr einer laufenden Aufgabe
# --------------------------------------------------------------------------

def _beendet(sitzung_id: int) -> bool:
    zeile = db.q1("SELECT zustand, phase FROM lern_sitzung WHERE id=?", sitzung_id)
    if zeile is None:
        return True
    return (zeile["zustand"] in ("MASTERED", "ESCALATED")
            or zeile["phase"] == "COMPLETE")


def uhr(sitzung_id: int) -> dict | None:
    return _zeile(db.q1("SELECT * FROM lern_uhr WHERE sitzung_id=?", sitzung_id))


def gezeigt(sitzung_id: int, kennung: str) -> None:
    """Die Aufgabe `kennung` ist jetzt zu sehen — die Uhr beginnt.

    Idempotent: dieselbe Aufgabe noch einmal gerendert (der Router ruft
    `bildschirm()` oefter als einmal je Anfrage) laesst die laufende Uhr in
    Ruhe. Erst eine andere Aufgabe setzt sie zurueck.
    """
    if not kennung or _beendet(sitzung_id):
        return
    jetzt = db.now()
    with db.tx() as c:
        vorhanden = c.execute("SELECT kennung FROM lern_uhr WHERE sitzung_id=?",
                              (sitzung_id,)).fetchone()
        if vorhanden and vorhanden["kennung"] == kennung:
            return
        c.execute(
            """INSERT INTO lern_uhr (sitzung_id, kennung, gezeigt_at,
                   letzte_eingabe, aktiv_sekunden, tipp_genutzt)
               VALUES (?,?,?,?,0,0)
               ON CONFLICT(sitzung_id) DO UPDATE SET kennung=excluded.kennung,
                   gezeigt_at=excluded.gezeigt_at,
                   letzte_eingabe=excluded.letzte_eingabe,
                   aktiv_sekunden=0, tipp_genutzt=0""",
            (sitzung_id, kennung, jetzt, jetzt))


def uhr_beenden(sitzung_id: int) -> None:
    """Die Einheit ist vorbei — eine laufende Uhr gehoert dann niemandem."""
    with db.tx() as c:
        c.execute("DELETE FROM lern_uhr WHERE sitzung_id=?", (sitzung_id,))


def puls(sitzung_id: int, cfg=None) -> float:
    """Eine Eingabe des Kindes: Tippen, Auswaehlen, einen Tipp oeffnen.

    Gezaehlt wird nur die Luecke seit der letzten Eingabe, und nur solange sie
    kuerzer ist als die Pausengrenze. Eine Seite, die zwei Minuten lang nichts
    hoeren laesst — weil sie im Hintergrund liegt oder niemand davor sitzt —
    bringt damit keine Sekunde ein.
    """
    laufend = uhr(sitzung_id)
    if laufend is None or _beendet(sitzung_id):
        # Nach COMPLETE, MASTERED oder ESCALATED entsteht keine aktive Zeit
        # mehr: die Einheit ist vorbei, auch wenn die Seite noch offen ist.
        return 0.0
    grenze = pause(cfg)
    letzte = _zeit(laufend["letzte_eingabe"]) or _jetzt()
    luecke = (_jetzt() - letzte).total_seconds()
    aktiv = float(laufend["aktiv_sekunden"])
    if 0 <= luecke <= grenze:
        aktiv += luecke
    with db.tx() as c:
        c.execute("UPDATE lern_uhr SET letzte_eingabe=?, aktiv_sekunden=? "
                  "WHERE sitzung_id=?", (db.now(), aktiv, sitzung_id))
    return aktiv


def tipp_genutzt(sitzung_id: int, cfg=None) -> None:
    """Ein Tipp ist eine Eingabe — und er gehoert in die Zeile der Antwort."""
    puls(sitzung_id, cfg)
    with db.tx() as c:
        c.execute("UPDATE lern_uhr SET tipp_genutzt=1 WHERE sitzung_id=?",
                  (sitzung_id,))


def pause(cfg=None) -> int:
    from .. import config
    return max(10, int(getattr(cfg or config.load_safe(),
                               "adaptiv_pause_sekunden", 120)))


def mindestzeit(cfg=None) -> int:
    from .. import config
    return max(0, int(getattr(cfg or config.load_safe(),
                              "adaptiv_mindest_sekunden", 3)))


# --------------------------------------------------------------------------
# Eine beantwortete Aufgabe
# --------------------------------------------------------------------------

def antwort_buchen(sitzung: dict, rolle: str, *, aufgabe: dict | None = None,
                   antwort: str | None = None, richtig: bool | None = None,
                   fach: str | None = None, klasse: int | None = None,
                   cfg=None) -> dict:
    """Genau eine Zeile je beantworteter Aufgabe. Nur anhaengen, nie aendern.

    Die aktive Zeit wird hier abgerechnet und die Uhr danach entfernt: sie
    gehoert zu einer sichtbaren Aufgabe, nicht zu einer Sitzung.
    """
    sitzung_id = sitzung["id"]
    laufend = uhr(sitzung_id)
    grenze = pause(cfg)
    aktiv = 0.0
    gezeigt_at = None
    tipp = 0
    if laufend is not None:
        gezeigt_at = laufend["gezeigt_at"]
        tipp = int(laufend["tipp_genutzt"])
        aktiv = float(laufend["aktiv_sekunden"])
        letzte = _zeit(laufend["letzte_eingabe"])
        if letzte is not None:
            luecke = (_jetzt() - letzte).total_seconds()
            if 0 <= luecke <= grenze:
                aktiv += luecke

    erwartet = erwartung((aufgabe or {}).get("antwort_art"), klasse,
                         (aufgabe or {}).get("erwartete_sekunden"))
    # Hoechstens das Doppelte des Erwarteten: wer eine Aufgabe dreimal so
    # lange offen hatte, hat nicht dreimal so lange gearbeitet.
    aktiv = min(aktiv, 2 * erwartet)
    zu_schnell = int(aktiv < mindestzeit(cfg))
    if zu_schnell:
        aktiv = 0.0

    jetzt = db.now()
    with db.tx() as c:
        zeile = c.execute(
            """INSERT INTO lern_antwort (child_key, sitzung_id, aufgabe_id,
                   konzept_id, fach, phase, rolle, gezeigt_at, beantwortet_at,
                   antwort, richtig, tipp_genutzt, aktive_sekunden, zu_schnell,
                   created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (sitzung.get("child_key") or CHILD_KEY, sitzung_id,
             (aufgabe or {}).get("id"), sitzung.get("konzept_id"), fach,
             sitzung.get("phase"), rolle, gezeigt_at, jetzt,
             (antwort or None), (None if richtig is None else int(richtig)),
             tipp, round(aktiv, 1), zu_schnell, jetzt)).lastrowid
        c.execute("DELETE FROM lern_uhr WHERE sitzung_id=?", (sitzung_id,))
    return {"id": zeile, "aktive_sekunden": round(aktiv, 1),
            "zu_schnell": bool(zu_schnell), "erwartet": erwartet}


def antworten(child_key: str = CHILD_KEY, von: str | None = None,
              bis: str | None = None, fach: str | None = None,
              sitzung_id: int | None = None) -> list[dict]:
    sql = "SELECT * FROM lern_antwort WHERE child_key=?"
    params: list = [child_key]
    # `beantwortet_at` ist UTC; `von`/`bis` sind lokale Kalendertage — ohne
    # 'localtime' faellt eine Antwort um lokale Mitternacht in den falschen
    # Tag.
    if von:
        sql += " AND datetime(beantwortet_at, 'localtime') >= ?"
        params.append(str(von))
    if bis:
        # Einschliesslich des ganzen Tages: ein Datum ohne Uhrzeit meint den Tag.
        sql += " AND datetime(beantwortet_at, 'localtime') <= ?"
        params.append(str(bis) + ("T23:59:59" if len(str(bis)) == 10 else ""))
    if fach:
        sql += " AND fach=?"
        params.append(fach)
    if sitzung_id is not None:
        sql += " AND sitzung_id=?"
        params.append(sitzung_id)
    sql += " ORDER BY id"
    return [_zeile(r) for r in db.q(sql, *params)]


def aktive_zeit(child_key: str = CHILD_KEY, von: str | None = None,
                bis: str | None = None, fach: str | None = None) -> float:
    """Summe der aktiven Sekunden im Zeitraum.

    Eine offene App ohne Eingabe ergibt 0 — das ist der Punkt der ganzen
    Uebung. `learning_time` misst weiter die Anwesenheit; die beiden Zahlen
    duerfen auseinanderliegen, und wenn sie es tun, sagt das etwas.
    """
    return round(sum(z["aktive_sekunden"] or 0
                     for z in antworten(child_key, von, bis, fach)), 1)


def nicht_ernsthaft(child_key: str = CHILD_KEY, von: str | None = None,
                    bis: str | None = None, fach: str | None = None,
                    cfg=None) -> bool:
    """Eine Serie zu schneller Antworten — geraten, nicht gerechnet.

    Keine Strafe und kein Minus: die Zahl sagt nur, dass dieser Abschnitt
    nichts ueber das Koennen des Kindes aussagt.
    """
    from .. import config
    serie = max(2, int(getattr(cfg or config.load_safe(),
                               "adaptiv_nicht_ernsthaft_serie", 3)))
    lauf = 0
    for zeile in antworten(child_key, von, bis, fach):
        lauf = lauf + 1 if zeile["zu_schnell"] else 0
        if lauf >= serie:
            return True
    return False


def gesehene_aufgaben(konzept_id: int, child_key: str = CHILD_KEY) -> set[int]:
    """Welche Aufgaben dieses Konzepts das Kind schon beantwortet hat.

    Die Wiederholung braucht neue Aufgaben. Ohne diese Liste waere „neu" eine
    Behauptung.
    """
    return {z["aufgabe_id"] for z in db.q(
        "SELECT DISTINCT aufgabe_id FROM lern_antwort "
        "WHERE child_key=? AND konzept_id=? AND aufgabe_id IS NOT NULL",
        child_key, konzept_id)}
