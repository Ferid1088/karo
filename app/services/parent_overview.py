"""Read-only facts for the parent home; personal learning and exams stay separate."""
from datetime import date

from .. import db, faecher


def summary() -> dict:
    personal = db.q1(f"""SELECT COUNT(*) AS total FROM topic t
        WHERE t.state='aktiv' AND t.learning_visible=1
          AND t.subject IN {faecher.SQL_FAECHER}
          AND t.deleted_at IS NULL AND t.purged_at IS NULL
          AND t.learned_at IS NULL AND t.merged_into IS NULL
          AND NOT EXISTS (SELECT 1 FROM exam_topic x WHERE x.topic_id=t.id)""")['total']
    exams = db.q(f"""SELECT id, subject, exam_date FROM exam
        WHERE exam_date>=? AND deleted_at IS NULL AND purged_at IS NULL
          AND subject IN {faecher.SQL_FAECHER}
        ORDER BY exam_date, id""", db.today())
    upcoming = None
    if exams:
        upcoming = dict(exams[0])
        upcoming['date_label'] = date.fromisoformat(upcoming['exam_date']).strftime('%d.%m.%Y')
        upcoming['days'] = (date.fromisoformat(upcoming['exam_date']) - date.fromisoformat(db.today())).days
    return {'personal_topics': personal, 'upcoming_exams': len(exams), 'next_exam': upcoming}
