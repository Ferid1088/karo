"""Wissensbasis.

Die eingescannten Blätter sind die Faktengrundlage: Erklärungen, Merkregeln,
Beispiele und Aufgaben aus dem eigenen Unterricht des Kindes. Jede Erklärung,
die Karo später erzeugt, wird gegen genau dieses Material geprüft.

Warum das wichtig ist: ein Kind, das im Unterricht einen bestimmten Rechenweg
gelernt hat, wird von einem zweiten Weg verwirrt, nicht unterstützt. Deshalb
ist nicht das Modellwissen der Maßstab, sondern das Blatt aus der Schule.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from . import config, db, jobs, pii, prompts
from .llm import ClaudeClient

log = logging.getLogger("karo.kb")

ARTEN = ("erklaerung", "regel", "beispiel", "aufgabe", "loesung")

#: Was als Lehrmaterial taugt — Aufgaben ohne Erklärung erklären nichts.
LEHR_ARTEN = ("erklaerung", "regel", "beispiel")


def client() -> ClaudeClient:
    return ClaudeClient.from_config(config.load())


# --------------------------------------------------------------------------
# Blatt erschließen
# --------------------------------------------------------------------------

@jobs.handler("kb_extract")
def job_kb_extract(payload: dict) -> None:
    """Liest ein Blatt und legt seine Abschnitte in der Wissensbasis ab."""
    doc_id = int(payload["document_id"])
    doc = db.q1("SELECT * FROM document WHERE id = ?", doc_id)
    if doc is None:
        return
    if doc["state"] not in ("neu",):
        return

    cfg = config.load()
    ergebnis = client().complete(
        purpose="kb_extract",
        prompt=prompts.kb_prompt(cfg.learner_grade, cfg.subject,
                                 themenname=doc["themenname"]),
        schema=prompts.KB_SCHEMA,
        image_path=Path(doc["stored_path"]),
        system=prompts.SYSTEM,
    )
    daten = ergebnis.data
    abschnitte = daten.get("abschnitte") or []

    with db.tx() as c:
        # Ein Blatt wird nur erschlossen, solange nichts daran hängt.
        c.execute("DELETE FROM kb_chunk WHERE document_id = ?", (doc_id,))
        for i, roh in enumerate(abschnitte, start=1):
            art = roh.get("art")
            text = (roh.get("text") or "").strip()
            if art not in ARTEN or not text:
                continue
            c.execute(
                """INSERT INTO kb_chunk (document_id, position, art, titel, text,
                                         thema_hinweis, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (doc_id, i, art, (roh.get("titel") or None),
                 text[:6000], (roh.get("thema") or None), db.now()))

        zustand = "erschlossen" if abschnitte else "leer"
        notiz = f"Lesbarkeit: {daten.get('lesbarkeit', 'unbekannt')}"
        if not abschnitte:
            notiz += " — es wurde kein Abschnitt erkannt"
        else:
            notiz += f" · {len(abschnitte)} Abschnitte"
        c.execute(
            """UPDATE document SET state=?, doc_type=COALESCE(doc_type, ?), note=?
                WHERE id=?""",
            (zustand, daten.get("dokumenttyp") or None, notiz, doc_id))

        if abschnitte:
            _einreihen(c, "topic_propose", {"document_id": doc_id},
                       f"topic:{doc_id}")


def _einreihen(c, art: str, payload: dict, schluessel: str) -> None:
    """Job im selben Schreibvorgang einreihen.

    Getrennte Transaktionen hätten hier eine Lücke: bricht der Prozess
    dazwischen ab, bliebe das Dokument für immer halb verarbeitet, während
    der Job als erledigt gilt.
    """
    c.execute(
        """UPDATE job SET dedup_key = NULL
            WHERE dedup_key = ? AND state NOT IN ('wartend', 'laeuft')""",
        (schluessel,))
    c.execute(
        """INSERT OR IGNORE INTO job (type, payload, state, dedup_key, created_at)
           VALUES (?, ?, 'wartend', ?, ?)""",
        (art, json.dumps(payload), schluessel, db.now()))


# --------------------------------------------------------------------------
# Suchen
# --------------------------------------------------------------------------

_FTS_UNSAFE = re.compile(r'[^\wäöüßÄÖÜ ]+')


def _fts_query(text: str) -> str:
    """Baut eine gutartige FTS5-Abfrage.

    Anführungszeichen, Sternchen und Klammern in einem Themennamen würden die
    FTS5-Syntax sonst sprengen und eine Ausnahme werfen.
    """
    worte = [w for w in _FTS_UNSAFE.sub(" ", text).split() if len(w) > 2]
    if not worte:
        return ""
    return " OR ".join(f'"{w}"' for w in worte[:8])


def suche(text: str, limit: int = 12, arten: tuple[str, ...] | None = None,
          topic_id: int | None = None) -> list[dict]:
    """Findet Abschnitte in der Wissensbasis.

    Erst nach Thema, dann per Volltext — ein zugeordneter Abschnitt ist immer
    relevanter als ein Volltexttreffer.
    """
    treffer: list[dict] = []
    gesehen: set[int] = set()

    if topic_id:
        for r in db.q(
            """SELECT k.*, d.source_name FROM kb_chunk k
                 JOIN document d ON d.id = k.document_id
                WHERE k.topic_id = ? ORDER BY k.art, k.id LIMIT ?""",
                topic_id, limit):
            treffer.append(dict(r))
            gesehen.add(r["id"])

    if len(treffer) < limit:
        abfrage = _fts_query(text)
        if abfrage:
            try:
                rows = db.q(
                    """SELECT k.*, d.source_name FROM kb_fts f
                         JOIN kb_chunk k ON k.id = f.rowid
                         JOIN document d ON d.id = k.document_id
                        WHERE kb_fts MATCH ?
                        ORDER BY bm25(kb_fts) LIMIT ?""",
                    abfrage, limit * 2)
            except Exception as exc:            # pragma: no cover
                log.warning("Volltextsuche fehlgeschlagen: %s", exc)
                rows = []
            for r in rows:
                if r["id"] in gesehen:
                    continue
                treffer.append(dict(r))
                gesehen.add(r["id"])
                if len(treffer) >= limit:
                    break

    if arten:
        bevorzugt = [t for t in treffer if t["art"] in arten]
        rest = [t for t in treffer if t["art"] not in arten]
        treffer = bevorzugt + rest

    return treffer[:limit]


def lehrmaterial(topic_id: int, label: str, limit: int = 10) -> list[dict]:
    """Nur das, was tatsächlich etwas erklärt."""
    alles = suche(label, limit=limit * 2, arten=LEHR_ARTEN, topic_id=topic_id)
    lehr = [a for a in alles if a["art"] in LEHR_ARTEN]
    return (lehr or alles)[:limit]


def aufgaben(topic_id: int, label: str, limit: int = 8) -> list[dict]:
    alles = suche(label, limit=limit * 2, arten=("aufgabe",), topic_id=topic_id)
    return [a for a in alles if a["art"] == "aufgabe"][:limit] or alles[:limit]


def geschwaerzt(chunks: list[dict]) -> list[dict]:
    """Kopie mit entfernten personenbezogenen Angaben, fuer Modellaufrufe."""
    name = config.load_safe().learner_name
    return [{**c, "text": pii.scrub(c["text"], name),
             "titel": pii.scrub(c.get("titel") or "", name) or None}
            for c in chunks]


def statistik() -> dict:
    row = db.q1(
        """SELECT COUNT(*) AS n,
                  SUM(art IN ('erklaerung','regel','beispiel')) AS lehr,
                  SUM(art = 'aufgabe') AS aufgaben,
                  COUNT(DISTINCT document_id) AS blaetter
             FROM kb_chunk""")
    return dict(row) if row else {"n": 0, "lehr": 0, "aufgaben": 0, "blaetter": 0}
