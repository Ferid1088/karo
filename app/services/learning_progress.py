"""Manueller Lernfortschritt bleibt unabhängig von Karo-Bewertungen."""

from fastapi import HTTPException

from .. import db, topics, faecher


def start(topic_id: int) -> None:
    with db.tx() as c:
        changed = c.execute(
            "UPDATE topic SET learning_started_at=COALESCE(learning_started_at, ?) "
            "WHERE id=? AND state=?", (db.now(), topic_id, topics.AKTIV))
        if not changed.rowcount:
            raise HTTPException(404, "Aktives Thema nicht gefunden.")


def complete(topic_id: int, learned: bool) -> None:
    with db.tx() as c:
        changed = c.execute(
            "UPDATE topic SET learned_at=? WHERE id=? AND state=?",
            (db.now() if learned else None, topic_id, topics.AKTIV))
        if not changed.rowcount:
            raise HTTPException(404, "Aktives Thema nicht gefunden.")


def status(topic_id: int) -> str:
    """'neu' oder 'bearbeitung' fuer ein einzelnes Thema — z.B. um nach dem
    Entfernen des Gelernt-Häkchens zum passenden Tab zurueckzukehren, statt
    immer 'bearbeitung' anzunehmen."""
    grouped = groups(topics.liste(topics.AKTIV))
    if any(t['id'] == topic_id for t in grouped['bearbeitung']):
        return 'bearbeitung'
    return 'neu'


def groups(themen: list[dict]) -> dict:
    # Historische Antworten und tatsächlich bearbeitete Runden zählen.
    # Das bloße Vorbereiten von Material durch Eltern startet kein Thema.
    started = {r['topic_id'] for r in db.q(
        "SELECT l.topic_id FROM lesson l JOIN lesson_round r ON r.lesson_id=l.id "
        "WHERE r.state='gelernt' UNION SELECT topic_id FROM quiz "
        "WHERE state IN ('beantwortet', 'ausgewertet', 'freigegeben')")}
    # Und der adaptive Loop: wer eine Sitzung zu einem Thema begonnen hat,
    # bearbeitet es — unabhaengig davon, ob je ein Quiz lief. Die Abfrage
    # liegt in `adaptiv/store.py`, damit SQL der `lern_`-Tabellen dort bleibt.
    from ..adaptiv import store as adaptiv_store
    started |= set(adaptiv_store.themen_mit_sitzung())
    result = {'neu': [], 'bearbeitung': [], 'gelernt': []}
    for topic in themen:
        key = ('gelernt' if topic.get('learned_at') else 'bearbeitung'
               if topic.get('learning_started_at') or topic['id'] in started else 'neu')
        result[key].append(topic)
    return result


def exam_groups(themen: list[dict]) -> dict:
    from .learning_hub import exam_topics
    result = {'neu': [], 'bearbeitung': []}
    for exam in db.q(f'''SELECT * FROM exam WHERE exam_date >= ?
            AND deleted_at IS NULL AND purged_at IS NULL AND subject IN {faecher.SQL_FAECHER}
            ORDER BY exam_date, id''', db.today()):
        selected = exam_topics(exam['id'])
        grouped = {key: [t for t in selected if t['learning_status'] == key] for key in result}
        for key in result:
            if grouped[key] or (key == 'neu' and not selected):
                for t in grouped[key]:
                    t['learning_status'] = key
                result[key].append({'id': exam['id'], 'exam_date': exam['exam_date'],
                                    'themen': grouped[key], 'plan': None})
    return result
