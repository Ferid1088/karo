"""Lerninhalte werden nach der ersten bestätigten Themenprüfung angeboten."""
from .. import db, quizzes


def checked_topic_ids() -> set[int]:
    return {row['topic_id'] for row in db.q(
        "SELECT DISTINCT topic_id FROM quiz WHERE anlass='evaluation' AND state=?",
        quizzes.STATE_FREIGEGEBEN)}


def add_creation_options(themen: list[dict]) -> None:
    checked = checked_topic_ids()
    for topic in themen:
        topic['can_create_content'] = topic['id'] in checked


def can_create(topic_id: int) -> bool:
    return topic_id in checked_topic_ids()
