"""Einmalige, verlustfreie Anpassung alter Workflow-Daten."""
import unicodedata
import re


def topic_key(label: str) -> str:
    key = re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', label).casefold())
    # Nur eindeutige Schreibweisen, keine unscharfen Mathe-Themen zusammenführen.
    return {'multiplication': 'multiplikation'}.get(key, key)


def repair(c) -> None:
    # Alte Versionen verwendeten ausschließlich finished_at als Abschluss.
    c.execute("UPDATE quiz SET state='freigegeben' WHERE finished_at IS NOT NULL AND state!='freigegeben'")
    canonical = {}
    for topic in c.execute('SELECT * FROM topic WHERE merged_into IS NULL ORDER BY id').fetchall():
        key = (topic['subject'], topic_key(topic['label']))
        previous = canonical.get(key)
        if previous is None:
            canonical[key] = topic
            continue
        # Historische Bewertungen und Lernrunden werden niemals umgeschrieben.
        if (topic['state'] != 'aktiv' or previous['state'] != 'aktiv'
                or c.execute('SELECT 1 FROM answer_log WHERE topic_id=? LIMIT 1', (topic['id'],)).fetchone()
                or c.execute('SELECT 1 FROM lesson WHERE topic_id=? LIMIT 1', (topic['id'],)).fetchone()
                or c.execute('SELECT 1 FROM prediction WHERE topic_id=? LIMIT 1', (topic['id'],)).fetchone()
                or topic['learned_at']):
            continue
        c.execute('UPDATE quiz SET topic_id=? WHERE topic_id=?', (previous['id'], topic['id']))
        c.execute('UPDATE kb_chunk SET topic_id=? WHERE topic_id=?', (previous['id'], topic['id']))
        c.execute('UPDATE topic SET learning_started_at=COALESCE(learning_started_at, ?) WHERE id=?',
                  (topic['learning_started_at'], previous['id']))
        c.execute("UPDATE topic SET state='zusammengefuehrt', merged_into=? WHERE id=?", (previous['id'], topic['id']))
    grouped = {}
    for quiz in c.execute('''SELECT q.*, (SELECT COUNT(*) FROM question x
            WHERE x.quiz_id=q.id AND x.schueler_antwort IS NOT NULL) AS answered
            FROM quiz q WHERE q.superseded_by IS NULL ORDER BY q.id''').fetchall():
        grouped.setdefault((quiz['topic_id'], quiz['anlass'], quiz['lesson_id'], quiz['round_nr']), []).append(quiz)
    rank = {'freigegeben': 5, 'ausgewertet': 4, 'beantwortet': 3, 'bereit': 2, 'offen': 1}
    for rows in grouped.values():
        winner = max(rows, key=lambda q: (rank.get(q['state'], 0), q['answered'], -q['id']))
        for quiz in rows:
            if quiz['id'] != winner['id'] and quiz['state'] in ('offen', 'bereit') and not quiz['answered']:
                c.execute('UPDATE quiz SET superseded_by=? WHERE id=?', (winner['id'], quiz['id']))
