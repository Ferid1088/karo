"""Versionsgeschützte Entwürfe; Speichern löst keine Bewertung aus."""
import json

from fastapi import HTTPException

from .. import config, db


def save(quiz_id: int, role: str, phase: str, revision: int, values: dict, position: int) -> dict:
    if phase not in ('answers', 'review') or not isinstance(values, dict):
        raise HTTPException(400, 'Ungültiger Entwurf.')
    if phase == 'review' and role != 'parent' and not config.load().antworten_pruefen_kind:
        raise HTTPException(403, 'Bewertungen bleiben im Elternbereich.')
    with db.tx() as c:
        quiz = c.execute('SELECT * FROM quiz WHERE id=?', (quiz_id,)).fetchone()
        if not quiz:
            raise HTTPException(404, 'Prüfung nicht gefunden.')
        if quiz['superseded_by'] or quiz['state'] != ('bereit' if phase == 'answers' else 'ausgewertet'):
            raise HTTPException(409, 'Diese Prüfung wurde bereits weiterbearbeitet. Bitte neu laden.')
        if revision != quiz['draft_revision']:
            raise HTTPException(409, 'Ein anderes Fenster hat neuere Änderungen gespeichert. Bitte neu laden.')
        ids = {str(row['id']) for row in c.execute('SELECT id FROM question WHERE quiz_id=?', (quiz_id,))}
        clean = {}
        for key, value in values.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise HTTPException(400, 'Ungültiges Antwortformat.')
            prefix, _, question_id = key.partition('_')
            if question_id not in ids:
                continue
            if phase == 'answers' and prefix == 'antwort':
                c.execute('UPDATE question SET schueler_antwort=? WHERE id=? AND quiz_id=?',
                          (value[:2000] or None, int(question_id), quiz_id))
            elif phase == 'review' and prefix in ('urteil', 'fehler'):
                clean[key] = value[:100]
        position = max(0, min(position, max(0, len(ids) - 1)))
        c.execute('''UPDATE quiz SET draft_revision=draft_revision+1,
            draft_position=?, draft_updated_at=?, review_draft=? WHERE id=?''',
            (position, db.now(), json.dumps(clean) if phase == 'review' else quiz['review_draft'], quiz_id))
        return {'revision': revision + 1, 'saved': True}
