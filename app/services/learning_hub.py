"""Personal topic ownership and explicit exam membership; shared teaching content."""
from __future__ import annotations

import hashlib
import json

from .. import config, db, topics
from ..adaptiv import lektionen, store


def create_topic(label: str, subject: str = "", grade: int | None = None,
                 *, personal: bool = True) -> int:
    label = " ".join(label.split())
    cfg = config.load_safe()
    subject = subject.strip() or cfg.subject
    grade = grade or cfg.learner_grade
    if not label or len(label) > 200:
        raise ValueError("Beschreibe dein Thema bitte mit 1 bis 200 Zeichen.")
    if len(subject) > 80 or not 1 <= int(grade) <= 13:
        raise ValueError("Bitte ein Fach und eine Klasse von 1 bis 13 wählen.")
    existing = next((t for t in topics.liste(topics.AKTIV)
                     if t['label'].casefold() == label.casefold()
                     and t['subject'].casefold() == subject.casefold()
                     and (t.get('grade') or cfg.learner_grade) == grade), None)
    with db.tx() as c:
        if existing:
            if personal:
                c.execute('UPDATE topic SET learning_visible=1 WHERE id=?', (existing['id'],))
            return existing['id']
        key = hashlib.sha256(f'{subject.casefold()}:{grade}:{label.casefold()}'.encode()).hexdigest()[:16]
        return c.execute('''INSERT INTO topic
            (subject,code,label,state,sort,created_at,learning_visible,grade)
            VALUES(?,?,?,'aktiv',500,?,?,?)''',
            (subject, 'LEARN.' + key, label, db.now(), int(personal), grade)).lastrowid


def link_exam(exam_id: int, names: list[str], subject: str) -> None:
    for position, name in enumerate(names):
        topic_id = create_topic(name, subject, personal=False)
        with db.tx() as c:
            c.execute('INSERT OR IGNORE INTO exam_topic VALUES(?,?,?)',
                      (exam_id, topic_id, position))


def migrate_exams() -> None:
    """Backfill exact membership. Preserve existing personal learning history."""
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
    return decorate([t for t in topics.liste(topics.AKTIV) if t.get('learning_visible', 1)])


def exam_topics(exam_id: int) -> list[dict]:
    ids = [r['topic_id'] for r in db.q('SELECT topic_id FROM exam_topic WHERE exam_id=? ORDER BY position', exam_id)]
    return decorate([t for tid in ids if (t := topics.get(tid)) and t['state'] == topics.AKTIV])


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

    sitzungen = {zeile["tag"]: zeile["anzahl"] for zeile in db.q(
        """SELECT substr(updated_at, 1, 10) AS tag, COUNT(*) AS anzahl
             FROM lern_sitzung
            WHERE substr(updated_at, 1, 10) BETWEEN ? AND ?
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
