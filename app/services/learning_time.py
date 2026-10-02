"""Lernzeit: wie lange wirklich gearbeitet wurde.

Zwei Quellen, die nie vermischt werden:

* **Gemessen** — die Lernseiten melden sich im Takt, solange sie offen und
  sichtbar sind (`learning_time`). Ein Stueck waechst, solange die Schlaege
  dicht aufeinander folgen; nach einer Pause beginnt ein neues. Das ist
  echte Zeit vor dem Bildschirm, keine gerechnete.
* **Geschaetzt** — fuer Tage, an denen noch nicht gemessen wurde (alles vor
  dem Einbau der Messung, oder ein Tag ohne JavaScript), summiert
  `_schaetzung` die Abstaende zwischen den Aktivitaeten und kappt jede Pause
  bei `PAUSE`. Ein einzelnes Ereignis bekommt `GUTSCHRIFT`, sonst waere eine
  beantwortete Frage null Minuten wert.

Ein Tag ist entweder das eine oder das andere, nie eine Summe aus beidem:
gemessene Sekunden schlagen die Schaetzung, und der Bericht sagt jedem Tag
an, woher seine Zahl kommt. Gezaehlt wird nur Lernen und Quiz — die Minuten
aus "Ziele planen" sind Selbstauskunft und bleiben ihre eigene Zahl.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from .. import config, db

#: Takt der Lernseiten in Sekunden (siehe static/lernzeit.js).
_OPS = config.ops()
TAKT = _OPS.lernzeit_takt_seconds
#: Bis hierher gehoert ein Schlag noch zum laufenden Stueck. Grosszuegiger als
#: der Takt, damit ein verlorener Schlag keine Lernrunde zerschneidet.
ANSCHLUSS = _OPS.lernzeit_anschluss_seconds
#: Laenger als das ist eine Pause und zaehlt in der Schaetzung nicht mit.
PAUSE = _OPS.lernzeit_pause_seconds
#: Was eine einzelne Aktivitaet ohne Nachbarn wert ist.
GUTSCHRIFT = _OPS.lernzeit_gutschrift_seconds
#: Obergrenze je Tag. Schuetzt die Anzeige vor einem Browserfenster, das ueber
#: Nacht offen blieb, und vor kaputten Zeitstempeln.
TAGESDECKEL = _OPS.lernzeit_tagesdeckel_seconds


def _zone():
    return config.zeitzone()


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


def _lokal(stamp: str | None) -> datetime | None:
    if not stamp:
        return None
    try:
        parsed = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)


def _tag(moment: datetime) -> date:
    return moment.astimezone(_zone()).date()


def _utc(tag: date) -> str:
    return datetime.combine(tag, time.min, _zone()).astimezone(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Messen
# --------------------------------------------------------------------------

def schlag(topic_id: int | None = None) -> int:
    """Nimmt einen Herzschlag entgegen und gibt die Sekunden des Stuecks zurueck.

    Der erste Schlag eines Stuecks zaehlt nichts — erst der zweite belegt,
    dass zwischen beiden wirklich Zeit am Thema vergangen ist.
    """
    jetzt = _jetzt()
    tag = _tag(jetzt).isoformat()
    with db.tx() as c:
        offen = c.execute(
            """SELECT id, letzter, sekunden FROM learning_time
                WHERE tag=? AND topic_id IS ? ORDER BY id DESC LIMIT 1""",
            (tag, topic_id)).fetchone()
        letzter = _lokal(offen["letzter"]) if offen else None
        if offen and letzter is not None:
            luecke = (jetzt - letzter).total_seconds()
            if 0 <= luecke <= ANSCHLUSS:
                sekunden = int(offen["sekunden"] + luecke)
                c.execute("UPDATE learning_time SET letzter=?, sekunden=? WHERE id=?",
                          (jetzt.isoformat(), sekunden, offen["id"]))
                return sekunden
        c.execute(
            "INSERT INTO learning_time(topic_id,tag,beginn,letzter,sekunden) VALUES(?,?,?,?,0)",
            (topic_id, tag, jetzt.isoformat(), jetzt.isoformat()))
        return 0


#: Woran eine Lernseite ihr Thema erkennen laesst. Reihenfolge zaehlt:
#: /lernen/thema/7 ist ein Thema, /lernen/7 eine Lerneinheit.
_PFADE = (
    re.compile(r"^/lernzyklus/(?P<topic>\d+)(?:/|$)"),
    re.compile(r"^/lernen/thema/(?P<topic>\d+)(?:/|$)"),
    re.compile(r"^/lernen/(?P<lesson>\d+)(?:/|$)"),
    re.compile(r"^/quiz/(?P<quiz>\d+)(?:/|$)"),
)


def thema_fuer_pfad(pfad: str, adaptive_sitzung=None) -> int | None:
    """Welches Thema die Seite unter `pfad` gerade zeigt — oder keins.

    Die adaptive Lernrunde traegt ihr Thema nicht im Pfad, sondern in der
    laufenden Sitzung; deren Kennung reicht der Aufrufer herein.
    """
    try:
        for muster in _PFADE:
            treffer = muster.match(pfad)
            if not treffer:
                continue
            teile = treffer.groupdict()
            if teile.get("topic"):
                return int(teile["topic"])
            if teile.get("lesson"):
                row = db.q1("SELECT topic_id FROM lesson WHERE id=?", int(teile["lesson"]))
                return row["topic_id"] if row else None
            if teile.get("quiz"):
                row = db.q1("SELECT topic_id FROM quiz WHERE id=?", int(teile["quiz"]))
                return row["topic_id"] if row else None
        if pfad.startswith("/lernen/adaptiv") and str(adaptive_sitzung).isdigit():
            row = db.q1("""SELECT i.topic_id FROM lern_sitzung s
                             JOIN lern_eingabe i ON i.id=s.eingabe_id
                            WHERE s.id=?""", int(adaptive_sitzung))
            if row and row["topic_id"]:
                return int(row["topic_id"])
    except (ValueError, TypeError):
        return None
    return None


def _gemessen(start: date, end: date) -> dict[date, dict[int | None, int]]:
    werte: dict[date, dict[int | None, int]] = defaultdict(lambda: defaultdict(int))
    for row in db.q(
            """SELECT tag, topic_id, SUM(sekunden) AS sekunden FROM learning_time
                WHERE tag BETWEEN ? AND ? GROUP BY tag, topic_id""",
            start.isoformat(), end.isoformat()):
        try:
            tag = date.fromisoformat(row["tag"])
        except (ValueError, TypeError):
            continue
        werte[tag][row["topic_id"]] += int(row["sekunden"] or 0)
    return werte


# --------------------------------------------------------------------------
# Schaetzen
# --------------------------------------------------------------------------

def _ereignisse(start: date, end: date) -> dict[date, dict[int, list[datetime]]]:
    """Zeitpunkte jeder Lern- und Quiz-Aktivitaet, nach Tag und Thema."""
    from ..adaptiv import store as learning_store

    von, bis = _utc(start), _utc(end + timedelta(days=1))
    punkte: dict[date, dict[int, list[datetime]]] = defaultdict(lambda: defaultdict(list))

    def merke(topic_id, stamp):
        moment = _lokal(stamp)
        if topic_id is None or moment is None:
            return
        tag = _tag(moment)
        if start <= tag <= end:
            punkte[tag][topic_id].append(moment)

    for event in learning_store.parent_report_events(von, bis):
        merke(event["topic_id"], event["created_at"])
    for row in db.q(
            """SELECT topic_id, beantwortet_am FROM answer_log
                WHERE julianday(beantwortet_am) >= julianday(?)
                  AND julianday(beantwortet_am) < julianday(?)""", von, bis):
        merke(row["topic_id"], row["beantwortet_am"])
    return punkte


def _schaetzung(zeitpunkte: list[datetime]) -> int:
    """Aktive Zeit aus Zeitpunkten: Abstaende summieren, Pausen kappen."""
    if not zeitpunkte:
        return 0
    folge = sorted(zeitpunkte)
    sekunden = GUTSCHRIFT
    for vorher, nachher in zip(folge, folge[1:]):
        abstand = (nachher - vorher).total_seconds()
        if abstand <= 0:
            continue
        sekunden += abstand if abstand <= PAUSE else GUTSCHRIFT
    return int(sekunden)


# --------------------------------------------------------------------------
# Lesen
# --------------------------------------------------------------------------

def zeitraum(start: date, end: date) -> dict:
    """Lernzeit je Tag und je Thema fuer einen Zeitraum.

    Rueckgabe: `{'tage': {date: {'sekunden': int, 'gemessen': bool,
    'themen': {topic_id: int}}}}`. Tage ohne Aktivitaet fehlen.
    """
    gemessen = _gemessen(start, end)
    punkte = _ereignisse(start, end)
    tage: dict[date, dict] = {}
    for tag in sorted(set(gemessen) | set(punkte)):
        if tag in gemessen and sum(gemessen[tag].values()) > 0:
            themen = {k: v for k, v in gemessen[tag].items() if v > 0}
            quelle = True
        else:
            themen = {tid: _schaetzung(liste) for tid, liste in punkte.get(tag, {}).items()}
            themen = {k: v for k, v in themen.items() if v > 0}
            quelle = False
        gesamt = min(sum(themen.values()), TAGESDECKEL)
        if gesamt <= 0:
            continue
        tage[tag] = {"sekunden": gesamt, "gemessen": quelle, "themen": themen}
    return {"tage": tage}


# --------------------------------------------------------------------------
# Anzeigen
# --------------------------------------------------------------------------

def dauer(sekunden: int | None) -> str:
    """Kurze deutsche Dauer, z. B. „0 Min.", „7 Min." oder „1 Std. 05 Min."
    """
    if not sekunden or sekunden < 0:
        return "0 Min."
    minuten = int(round(sekunden / 60))
    if minuten < 60:
        return f"{minuten} Min."
    return f"{minuten // 60} Std. {minuten % 60:02d} Min."
