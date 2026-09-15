"""Ein gespeicherter Einstieg je Thema statt neuer Prüfungen beim Öffnen."""
from .. import db, quizzes


def canonical_topic_id(topic_id: int) -> int:
    seen = set()
    while topic_id not in seen:
        seen.add(topic_id)
        row = db.q1('SELECT merged_into FROM topic WHERE id=?', topic_id)
        if not row or not row['merged_into']:
            return topic_id
        topic_id = row['merged_into']
    return topic_id


def pending_quiz(topic_id: int):
    row = db.q1('''SELECT q.* FROM quiz q WHERE q.topic_id=?
        AND q.state!='freigegeben' AND q.finished_at IS NULL AND q.superseded_by IS NULL
        AND (q.lesson_id IS NULL OR EXISTS (SELECT 1 FROM lesson l WHERE l.id=q.lesson_id
             AND l.state NOT IN ('gelernt','abgebrochen')))
        ORDER BY CASE q.state WHEN 'ausgewertet' THEN 0 WHEN 'beantwortet' THEN 1
                 WHEN 'bereit' THEN 2 ELSE 3 END,
                 (SELECT COUNT(*) FROM question x WHERE x.quiz_id=q.id AND x.schueler_antwort IS NOT NULL) DESC,
                 q.id LIMIT 1''', topic_id)
    return dict(row) if row else None


def latest_result(topic_id: int):
    row = db.q1("SELECT * FROM quiz WHERE topic_id=? AND anlass='evaluation' "
                "AND state=? AND superseded_by IS NULL ORDER BY id DESC LIMIT 1",
                topic_id, quizzes.STATE_FREIGEGEBEN)
    return dict(row) if row else None
