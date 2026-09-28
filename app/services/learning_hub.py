"""Personal topic ownership and explicit exam membership; shared teaching content."""
from __future__ import annotations

import hashlib
import json
import uuid

from .. import config, db, topics
from ..adaptiv import lektionen, store


def create_topic(label: str, subject: str = "", grade: int | None = None,
                 *, personal: bool = True, exam_id: int | None = None) -> int:
    label = " ".join(label.split())
    cfg = config.load_safe()
    subject = subject.strip() or cfg.subject
    grade = grade or cfg.learner_grade
    if not label or len(label) > 200:
        raise ValueError("Beschreibe dein Thema bitte mit 1 bis 200 Zeichen.")
    if len(subject) > 80 or not 1 <= int(grade) <= 13:
        raise ValueError("Bitte ein Fach und eine Klasse von 1 bis 13 wählen.")
    # Ein eigenes Lernthema und ein Prüfungsthema sind zwei Dinge, auch wenn
    # sie gleich heissen: "Bruchrechnen" fuer die Arbeit am Freitag hat einen
    # anderen Stand als "Bruchrechnen", das aus Neugier laeuft. Deshalb
    # sucht ein Prüfungsthema nur unter Prüfungsthemen nach einem passenden
    # Eintrag — und bekommt sonst seinen eigenen.
    if not personal and exam_id is None:
        raise ValueError("Ein Prüfungsthema braucht eine eigene Klassenarbeit.")
    members = {r['topic_id'] for r in db.q(
        'SELECT topic_id FROM exam_topic WHERE exam_id=?', exam_id)} if not personal else set()
    existing = next((t for t in topics.liste(topics.AKTIV)
                     if t['label'].casefold() == label.casefold()
                     and t['subject'].casefold() == subject.casefold()
                     and (t.get('grade') or cfg.learner_grade) == grade
                     and bool(t.get('learning_visible', 1)) == personal
                     and not t.get('deleted_at') and not t.get('purged_at')
                     and not t.get('learned_at')
                     and (personal or t['id'] in members)), None)
    if existing:
        return existing['id']
    key = hashlib.sha256(f'{subject.casefold()}:{grade}:{label.casefold()}'.encode()).hexdigest()[:16]
    with db.tx() as c:
        return c.execute('''INSERT INTO topic
            (subject,code,label,state,sort,created_at,learning_visible,grade)
            VALUES(?,?,?,'aktiv',500,?,?,?)''',
            (subject, ('LEARN.' if personal else f'EXAM.{exam_id}.') + key + '.' + uuid.uuid4().hex[:8], label,
             db.now(), int(personal), grade)).lastrowid


def link_exam(exam_id: int, names: list[str], subject: str) -> None:
    offset = db.q1('SELECT COALESCE(MAX(position),-1)+1 AS n FROM exam_topic WHERE exam_id=?', exam_id)['n']
    for position, name in enumerate(names, start=offset):
        topic_id = create_topic(name, subject, personal=False, exam_id=exam_id)
        with db.tx() as c:
            c.execute('INSERT OR IGNORE INTO exam_topic VALUES(?,?,?)',
                      (exam_id, topic_id, position))


def migrate_exams() -> None:
    """Backfill exact membership. Preserve existing personal learning history."""
    # Old versions reused one local topic across exams. Preserve that history
    # verbatim, but do not attribute ambiguous answers to a particular exam.
    with db.tx() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS exam_topic_legacy (
            exam_id INTEGER NOT NULL, topic_id INTEGER NOT NULL,
            replacement_id INTEGER NOT NULL, migrated_at TEXT NOT NULL,
            PRIMARY KEY(exam_id, topic_id))""")
    shared = [dict(r) for r in db.q("""SELECT x.*, t.label, t.subject, t.grade
        FROM exam_topic x JOIN topic t ON t.id=x.topic_id
        WHERE t.learning_visible=1 OR x.topic_id IN
          (SELECT topic_id FROM exam_topic GROUP BY topic_id HAVING COUNT(*)>1)""")]
    for old in shared:
        # Creating without old membership prevents reuse of the ambiguous row.
        with db.tx() as c:
            new_id = c.execute("""INSERT INTO topic
                (subject,code,label,state,sort,created_at,learning_visible,grade)
                VALUES(?,?,?,'aktiv',500,?,0,?)""",
                (old['subject'], f"EXAM.{old['exam_id']}." + uuid.uuid4().hex,
                 old['label'], db.now(), old['grade'])).lastrowid
            c.execute("INSERT OR IGNORE INTO exam_topic_legacy VALUES(?,?,?,?)",
                      (old['exam_id'], old['topic_id'], new_id, db.now()))
            c.execute("UPDATE exam_topic SET topic_id=? WHERE exam_id=? AND topic_id=?",
                      (new_id, old['exam_id'], old['topic_id']))
    with db.tx() as c:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS exam_topic_owner ON exam_topic(topic_id)")
    for e in db.q('SELECT * FROM exam WHERE id NOT IN (SELECT exam_id FROM exam_topic)'):
        try:
            names = json.loads(e['themen'] or '[]')
        except (ValueError, TypeError):
            continue
        if isinstance(names, list):
            link_exam(e['id'], [n for n in names if isinstance(n, str) and n.strip()], e['subject'])


def decorate(rows: list[dict]) -> list[dict]:
    for t in rows:
        state = store.topic_mastery(t['id'])
        t['learning_status'] = ('sicher' if state == 'MASTERED' else
                                'bearbeitung' if state or t.get('learning_started_at') else 'neu')
        t['status_label'] = {'sicher': 'Sicher', 'bearbeitung': 'In Bearbeitung', 'neu': 'Neu'}[t['learning_status']]
    return rows


def personal_topics() -> list[dict]:
    return decorate([t for t in topics.liste(topics.AKTIV)
                     if t.get('learning_visible', 1) and not t.get('deleted_at')
                     and not t.get('purged_at') and not t.get('learned_at')])


def exam_topics(exam_id: int) -> list[dict]:
    ids = [r['topic_id'] for r in db.q('SELECT topic_id FROM exam_topic WHERE exam_id=? ORDER BY position', exam_id)]
    return decorate([t for tid in ids if (t := topics.get(tid)) and t['state'] == topics.AKTIV
                     and not t.get('deleted_at') and not t.get('purged_at')])


def topic_in_scope(topic_id: int, exam_id: int | None = None) -> dict | None:
    """Validate ownership at every entry point, not just on the cards."""
    topic = topics.get(topic_id)
    if not topic or topic['state'] != topics.AKTIV or topic.get('deleted_at') or topic.get('purged_at'):
        return None
    owner = db.q1('SELECT exam_id FROM exam_topic WHERE topic_id=?', topic_id)
    if exam_id is None:
        return topic if topic.get('learning_visible', 1) and not owner else None
    exam = db.q1('SELECT id FROM exam WHERE id=? AND deleted_at IS NULL AND purged_at IS NULL', exam_id)
    return topic if exam and owner and owner['exam_id'] == exam_id and not topic.get('learning_visible') else None


def catalog() -> list[dict]:
    return lektionen.verfuegbar()


def monitor(heute: str = "") -> dict:
    """Lernmonitoring der laufenden Woche — das Gegenstueck zur Lernwoche
    eines Ziels (`woche/plaene.goal_week`).

    Ein Kreis je Wochentag: gruen, wenn an dem Tag wirklich eine Lernsitzung
    lief, sonst leer. Dazu drei Kennzahlen ueber die eigenen Themen. Alles
    aus vorhandenen Spuren gerechnet, nichts geschaetzt.
    """
    import datetime as dt

    tag = dt.date.fromisoformat(heute or db.today())
    montag = tag - dt.timedelta(days=tag.isoweekday() - 1)
    sonntag = montag + dt.timedelta(days=6)

    # Nur eigene Lernthemen. Was fuer eine Klassenarbeit gelernt wird, zaehlt
    # auf deren Seite — zwei getrennte Dinge, zwei getrennte Wochen.
    sitzungen = {zeile["tag"]: zeile["anzahl"] for zeile in db.q(
        """SELECT substr(s.updated_at, 1, 10) AS tag, COUNT(*) AS anzahl
             FROM lern_sitzung s
             JOIN lern_eingabe e ON e.id = s.eingabe_id
             JOIN topic t ON t.id = e.topic_id
            WHERE substr(s.updated_at, 1, 10) BETWEEN ? AND ?
              AND t.learning_visible = 1
            GROUP BY tag""", str(montag), str(sonntag))}

    tage = []
    for versatz in range(7):
        heutiger = montag + dt.timedelta(days=versatz)
        text = str(heutiger)
        anzahl = sitzungen.get(text, 0)
        zustand = ("geschafft" if anzahl else
                   "offen" if heutiger >= tag else "frei")
        tage.append({"date": text, "weekday": heutiger.isoweekday(),
                     "state": zustand, "sessions": anzahl,
                     "today": heutiger == tag,
                     "label": (f"{anzahl} Lernrunden" if anzahl > 1 else
                               "eine Lernrunde" if anzahl else
                               "noch offen" if heutiger >= tag else
                               "nicht gelernt")})

    themen = personal_topics()
    stand = {"sicher": 0, "bearbeitung": 0, "neu": 0}
    for t in themen:
        stand[t["learning_status"]] += 1
    return {"days": tage, "sessions_week": sum(sitzungen.values()),
            "days_learned": sum(1 for t in tage if t["state"] == "geschafft"),
            "topics": len(themen), **stand}


# --------------------------------------------------------------------------
# Archiv: was gelernt, geschrieben oder geloescht ist (siehe "Erfolge")
# --------------------------------------------------------------------------

def thema_loeschen(topic_id: int) -> None:
    """Aus der Themenliste nehmen. Geloescht heisst hier: ins Archiv."""
    with db.tx() as c:
        c.execute("UPDATE topic SET deleted_at=? WHERE id=? AND deleted_at IS NULL",
                  (db.now(), _personal_id(topic_id)))


def thema_zurueck(topic_id: int) -> None:
    """Zurück zum Lernen: wieder in der Liste, ohne Haken, ohne Löschung."""
    with db.tx() as c:
        c.execute("""UPDATE topic SET deleted_at=NULL, learned_at=NULL,
                            learning_visible=1 WHERE id=?""", (_personal_id(topic_id),))


def archiv_themen() -> list[dict]:
    """Eigene Themen im Archiv: abgehakt oder geloescht, Geloeschtes zuerst.

    Nur eigene Lernthemen (learning_visible=1). Pruefungsthemen haben ihr
    eigenes Archiv — die beiden Dinge bleiben getrennt.
    """
    zeilen = [dict(r) for r in db.q(
        """SELECT * FROM topic
            WHERE learning_visible = 1 AND purged_at IS NULL
              AND (deleted_at IS NOT NULL OR learned_at IS NOT NULL)
            ORDER BY COALESCE(deleted_at, learned_at) DESC""")]
    for t in zeilen:
        t["gelöscht"] = bool(t.get("deleted_at"))
    return decorate(zeilen)


def arbeit_loeschen(exam_id: int) -> None:
    with db.tx() as c:
        c.execute("UPDATE exam SET deleted_at=? WHERE id=? AND deleted_at IS NULL",
                  (db.now(), exam_id))


def arbeit_zurueck(exam_id: int) -> None:
    with db.tx() as c:
        c.execute("UPDATE exam SET deleted_at=NULL WHERE id=?", (exam_id,))


def archiv_arbeiten() -> list[dict]:
    """Klassenarbeiten im Archiv: geschrieben (Termin vorbei) oder geloescht."""
    heute = db.today()
    zeilen = [dict(r) for r in db.q(
        """SELECT * FROM exam
            WHERE purged_at IS NULL
              AND (deleted_at IS NOT NULL OR exam_date < ?)
            ORDER BY COALESCE(deleted_at, exam_date) DESC""", heute)]
    for e in zeilen:
        e["gelöscht"] = bool(e.get("deleted_at"))
        themen = exam_topics(e["id"])
        e["themen_zahl"] = len(themen)
        e["sicher_zahl"] = sum(t["learning_status"] == "sicher" for t in themen)
    return zeilen


def thema_entfernen(topic_id: int) -> None:
    """Endgueltig loeschen: verschwindet aus Liste und Archiv.

    Die Zeile bleibt in der Datenbank stehen, nur unsichtbar. An ihr haengen
    Fragen, Antworten und der Lernverlauf; ein hartes DELETE liesse die auf
    eine Nummer zeigen, die es nicht mehr gibt. Fuer das Kind ist das Thema
    weg, und der Elternbereich behaelt seine Aufzeichnungen.
    """
    with db.tx() as c:
        c.execute("UPDATE topic SET purged_at=?, deleted_at=COALESCE(deleted_at, ?) WHERE id=?",
                  (db.now(), db.now(), _personal_id(topic_id)))


def _personal_id(topic_id: int) -> int:
    """Archive actions must never move an exam topic into personal learning."""
    row = db.q1('''SELECT id FROM topic WHERE id=? AND learning_visible=1
        AND purged_at IS NULL AND NOT EXISTS
        (SELECT 1 FROM exam_topic WHERE topic_id=topic.id)''', topic_id)
    if row is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Dieses Thema gehört nicht zu deinen Lernthemen.")
    return topic_id


def arbeit_entfernen(exam_id: int) -> None:
    """Endgueltig loeschen — wie thema_entfernen, aus demselben Grund weich."""
    with db.tx() as c:
        c.execute("UPDATE exam SET purged_at=?, deleted_at=COALESCE(deleted_at, ?) WHERE id=?",
                  (db.now(), db.now(), exam_id))
