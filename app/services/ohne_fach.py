"""Der Elternordner „Ohne Fach“.

Karo nimmt nur gepflegte Fächer an. Was aus früheren
Versionen ein anderes oder gar kein Fach hat (Themen, Klassenarbeiten,
Schulblätter), wird nicht gelöscht und nicht geraten: es ist für das Kind
unsichtbar und liegt hier, bis Eltern ein Fach wählen.
"""
from __future__ import annotations

from .. import db, faecher

ARTEN = {"thema": "topic", "arbeit": "exam", "blatt": "document"}


def inhalte() -> dict[str, list[dict]]:
    ohne = f"subject NOT IN {faecher.SQL_FAECHER}"
    return {
        "thema": [dict(r) for r in db.q(
            f"""SELECT id, label AS titel, subject FROM topic
                 WHERE {ohne} AND purged_at IS NULL AND state != 'abgelehnt'
                 ORDER BY created_at DESC""")],
        "arbeit": [dict(r) for r in db.q(
            f"""SELECT id, exam_date AS titel, subject FROM exam
                 WHERE {ohne} AND purged_at IS NULL ORDER BY exam_date DESC""")],
        "blatt": [dict(r) for r in db.q(
            f"""SELECT id, COALESCE(themenname, source_name) AS titel, subject FROM document
                 WHERE rolle = 'wissen'
                   AND (subject IS NULL OR {ohne} OR state = 'fach_falsch')
                 ORDER BY created_at DESC""")],
    }


def anzahl() -> int:
    return sum(len(zeilen) for zeilen in inhalte().values())


def zuordnen(art: str, eintrag_id: int, fach: str) -> None:
    """Gibt einem Eintrag aus dem Ordner eines der gepflegten Fächer."""
    tabelle = ARTEN.get(art)
    if tabelle is None:
        raise ValueError("Unbekannte Art.")
    fach = faecher.pflicht(fach)
    with db.tx() as c:
        c.execute(f"UPDATE {tabelle} SET subject=? WHERE id=?", (fach, eintrag_id))
    if art == "arbeit":
        # Themen einer bisher geparkten Arbeit werden jetzt erst angelegt.
        from .learning_hub import migrate_exams
        migrate_exams()
    elif art == "blatt":
        from .. import jobs
        row = db.q1("SELECT state FROM document WHERE id=?", eintrag_id)
        if row and row["state"] in ("neu", "fach_falsch"):
            with db.tx() as c:
                c.execute("UPDATE document SET state='neu' WHERE id=?", (eintrag_id,))
            jobs.enqueue("kb_extract", {"document_id": eintrag_id},
                         dedup_key=f"kb_extract:{eintrag_id}:{fach}")
