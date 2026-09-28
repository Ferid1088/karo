"""Content level is curriculum metadata, never the requesting child's class.

An acknowledgement doubles as a durable in-app parent notification. Its key
includes the learning area, concept, profile class and content range, so an old
acknowledgement cannot authorize a different exam or a changed classification.
"""
from __future__ import annotations

import hashlib
import json

from .. import config, db


def guidance(concept: dict, area: str, topic_id: int | None, thema: str) -> dict:
    grade = config.load_safe().learner_grade
    lo, hi = concept['klasse_von'], concept['klasse_bis']
    key = hashlib.sha256(json.dumps(
        [area, topic_id, thema.strip().casefold(), concept['id'], grade, lo, hi],
        ensure_ascii=False).encode()).hexdigest()
    return dict(key=key, area=area, topic_id=topic_id, thema=thema,
                concept_id=concept['id'], profile_grade=grade, grade_from=lo, grade_to=hi,
                mismatch=not lo <= grade <= hi,
                level=f'Klasse {lo}' if lo == hi else f'Klassen {lo}–{hi}',
                acknowledged=bool(db.q1('SELECT 1 FROM learning_grade_notice WHERE consent_key=?', key)))


def acknowledge(info: dict) -> None:
    if not info['mismatch']:
        return
    with db.tx() as c:
        c.execute('''INSERT OR IGNORE INTO learning_grade_notice
            (consent_key,area,topic_id,concept_id,topic_label,profile_grade,grade_from,grade_to,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)''',
            (info['key'], info['area'], info['topic_id'], info['concept_id'], info['thema'],
             info['profile_grade'], info['grade_from'], info['grade_to'], db.now()))


def unread() -> list[dict]:
    return [dict(r) for r in db.q('SELECT * FROM learning_grade_notice WHERE read_at IS NULL ORDER BY id DESC')]


def mark_read(notice_id: int) -> None:
    with db.tx() as c:
        c.execute('UPDATE learning_grade_notice SET read_at=COALESCE(read_at,?) WHERE id=?',
                  (db.now(), notice_id))
