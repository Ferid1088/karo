"""Einstufung: was das Kind zu jedem Prüfungsthema schon kann.

Direkt nachdem die Prüfungsthemen feststehen, fragt Karo je Thema zwei
geprüfte Aufgaben ab. Erst daraus entsteht die Zeitschätzung — vorher
wüsste niemand, wie lange etwas dauert, und eine Zahl ohne Grundlage ist
schlimmer als keine.

Ein Thema nach dem anderen, nicht alles auf einmal: bei achtzehn Themen
wären das sonst sechsunddreißig Aufgaben in einem Rutsch. Nach jedem Thema
ist der Stand gespeichert; das Kind kann aufhören und später weitermachen.

Die Flagge ist bewusst vorsichtig. Eine einzelne richtige Antwort macht ein
Thema nicht "sicher" — sie zeigt nur, dass es nicht bei null anfängt:

===========  =================================================
beide richtig  gruen — das sitzt, kurze Wiederholung genügt
eine richtig   gelb  — im Prinzip verstanden, noch wacklig
keine richtig  rot   — hier liegt Arbeit
eine Aufgabe   gelb bei richtig, rot bei falsch (nie gruen)
===========  =================================================

Was hier herauskommt, gilt fuer **diese Prüfung**. Es wird nicht in die
Beherrschung eigener Themen zurückgeschrieben — dafür bleibt es bei der
Regel aus `adaptiv/store.fortschritt_scope`.
"""
from __future__ import annotations

import json
import random

from .. import db

#: Aufgaben je Thema. Zwei reichen fuer eine Einstufung und halten die
#: Gesamtdauer auch bei vielen Themen im Rahmen.
AUFGABEN_JE_THEMA = 2


def init() -> None:
    with db.tx() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS exam_placement (
            id INTEGER PRIMARY KEY,
            exam_id INTEGER NOT NULL REFERENCES exam(id),
            topic_id INTEGER NOT NULL REFERENCES topic(id),
            questions TEXT NOT NULL,
            answers TEXT NOT NULL DEFAULT '{}',
            flagge TEXT,
            created_at TEXT NOT NULL,
            finished_at TEXT,
            UNIQUE(exam_id, topic_id))""")


def _aufgaben(topic: dict) -> list[dict]:
    """Geprüfte Kontrollaufgaben zum Thema — oder eine leere Liste."""
    from ..adaptiv import inhalt_store, lektionen, store

    lesson = lektionen.fuer_thema(topic["label"], topic["subject"], topic.get("grade"))
    if lesson is None:
        return []
    gesammelt, gesehen = [], set()
    for fehlertyp in store.fehlertypen(lesson["konzept_id"]):
        for aufgabe in inhalt_store.aufgaben(fehlertyp["id"]):
            if aufgabe["rolle"] not in ("selbststaendig", "transfer"):
                continue
            if aufgabe["frage"] in gesehen:
                continue
            gesehen.add(aufgabe["frage"])
            gesammelt.append({"frage": aufgabe["frage"], "loesung": aufgabe["loesung"],
                              "optionen": aufgabe.get("optionen") or [],
                              "art": aufgabe["antwort_art"]})
    random.SystemRandom().shuffle(gesammelt)
    return gesammelt[:AUFGABEN_JE_THEMA]


def _zeile(exam_id: int, topic_id: int) -> dict | None:
    init()
    row = db.q1("SELECT * FROM exam_placement WHERE exam_id=? AND topic_id=?",
                exam_id, topic_id)
    if not row:
        return None
    eintrag = dict(row)
    for schluessel in ("questions", "answers"):
        eintrag[schluessel] = json.loads(eintrag[schluessel] or "[]" if schluessel == "questions" else "{}")
    return eintrag


def naechstes_thema(exam_id: int) -> dict | None:
    """Das erste Prüfungsthema, das noch keine Einstufung hat und eines haben kann."""
    from .learning_hub import exam_topics

    init()
    fertig = {r["topic_id"] for r in db.q(
        "SELECT topic_id FROM exam_placement WHERE exam_id=? AND finished_at IS NOT NULL",
        exam_id)}
    for topic in exam_topics(exam_id):
        if topic["id"] in fertig:
            continue
        aufgaben = _aufgaben(topic)
        if aufgaben:
            return {"topic": topic, "aufgaben": aufgaben}
    return None


def oeffnen(exam_id: int, topic_id: int) -> dict | None:
    """Legt die Aufgaben dieses Themas fest, damit sie beim Neuladen bleiben."""
    from .learning_hub import topic_in_scope

    vorhanden = _zeile(exam_id, topic_id)
    if vorhanden:
        return vorhanden
    topic = topic_in_scope(topic_id, exam_id)
    if topic is None:
        return None
    aufgaben = _aufgaben(topic)
    if not aufgaben:
        return None
    with db.tx() as c:
        c.execute("""INSERT OR IGNORE INTO exam_placement
                     (exam_id, topic_id, questions, created_at) VALUES(?,?,?,?)""",
                  (exam_id, topic_id, json.dumps(aufgaben, ensure_ascii=False), db.now()))
    return _zeile(exam_id, topic_id)


def abgeben(exam_id: int, topic_id: int, antworten: dict) -> dict:
    """Bewertet die Antworten und haelt die Flagge fuer dieses Thema fest."""
    from ..adaptiv.unterricht import ist_richtig

    eintrag = _zeile(exam_id, topic_id)
    if not eintrag:
        raise ValueError("Diese Einstufung wurde noch nicht geöffnet.")
    if eintrag["finished_at"]:
        return eintrag
    gereinigt = {str(i): str(antworten.get(str(i), "")).strip()[:1000]
                 for i in range(len(eintrag["questions"]))}
    treffer = sum(ist_richtig(gereinigt[str(i)], frage["loesung"])
                  for i, frage in enumerate(eintrag["questions"]))
    gesamt = len(eintrag["questions"])
    if gesamt >= 2:
        flagge = "gruen" if treffer == gesamt else "gelb" if treffer else "rot"
    else:
        # Eine einzige Aufgabe belegt keine Sicherheit, nur einen Anfang.
        flagge = "gelb" if treffer else "rot"
    with db.tx() as c:
        c.execute("""UPDATE exam_placement SET answers=?, flagge=?, finished_at=?
                     WHERE id=? AND finished_at IS NULL""",
                  (json.dumps(gereinigt, ensure_ascii=False), flagge, db.now(),
                   eintrag["id"]))
    return _zeile(exam_id, topic_id)


def ergebnis(exam_id: int) -> dict[int, str]:
    """Flagge je Thema aus der Einstufung — die belastbarste Quelle."""
    init()
    return {r["topic_id"]: r["flagge"] for r in db.q(
        """SELECT topic_id, flagge FROM exam_placement
            WHERE exam_id=? AND finished_at IS NOT NULL AND flagge IS NOT NULL""",
        exam_id)}


def stand(exam_id: int) -> dict:
    """Wie weit die Einstufung ist und ob sie ueberhaupt laufen kann."""
    from .learning_hub import exam_topics

    themen = exam_topics(exam_id)
    fertig = ergebnis(exam_id)
    moeglich = sum(1 for t in themen if t["id"] in fertig or _aufgaben(t))
    return {"gesamt": len(themen), "fertig": len(fertig), "moeglich": moeglich,
            "offen": max(0, moeglich - len(fertig)),
            "ohne_aufgaben": len(themen) - moeglich,
            "vollstaendig": bool(themen) and len(fertig) >= moeglich and moeglich > 0}
