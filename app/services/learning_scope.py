"""Reject exam-owned resources at legacy personal-learning entry points."""
import re

from .. import db


def exam_resource_on_personal_path(path: str) -> bool:
    topic_id = lesson_id = None
    match = re.match(r'/(?:lernzyklus|themen)/(\d+)(?:/|$)', path)
    if match:
        topic_id = int(match[1])
    match = re.fullmatch(r'/lernen/(\d+)/loeschen', path)
    if match:
        topic_id = int(match[1])
    elif match := re.match(r'/lernen/(\d+)(?:/|$)', path):
        lesson_id = int(match[1])
    if match := re.match(r'/quiz/(\d+)(?:/|$)', path):
        quiz = db.q1('SELECT topic_id,lesson_id FROM quiz WHERE id=?', int(match[1]))
        if quiz:
            topic_id = quiz['topic_id']
            lesson_id = quiz['lesson_id']
    if match := re.match(r'/material/(\d+)(?:/|$)', path):
        row = db.q1('SELECT lesson_id FROM lesson_round WHERE id=?', int(match[1]))
        lesson_id = row['lesson_id'] if row else None
    if match := re.match(r'/material/variante/(\d+)(?:/|$)', path):
        row = db.q1('''SELECT r.lesson_id FROM lesson_round_variant v
            JOIN lesson_round r ON r.id=v.lesson_round_id WHERE v.id=?''', int(match[1]))
        lesson_id = row['lesson_id'] if row else None
    if lesson_id:
        if db.q1('SELECT 1 FROM exam_material WHERE lesson_id=?', lesson_id):
            return True
        row = db.q1('SELECT topic_id FROM lesson WHERE id=?', lesson_id)
        topic_id = row['topic_id'] if row else None
    return bool(topic_id and db.q1('''SELECT 1 FROM topic WHERE id=? AND
        (learning_visible=0 OR EXISTS(SELECT 1 FROM exam_topic WHERE topic_id=topic.id))''', topic_id))
