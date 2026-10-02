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

from . import config, db, jobs, pii
from .ai import AIClient

log = logging.getLogger("karo.kb")

ARTEN = ("erklaerung", "regel", "beispiel", "aufgabe", "loesung")

#: Was als Lehrmaterial taugt — Aufgaben ohne Erklärung erklären nichts.
LEHR_ARTEN = ("erklaerung", "regel", "beispiel")


def client() -> AIClient:
    return AIClient.from_config(config.load())


# --------------------------------------------------------------------------
# Blatt erschließen
# --------------------------------------------------------------------------

@jobs.handler("kb_extract")
def job_kb_extract(payload: dict) -> None:
    """Nimmt ein Blatt in die Sammlung auf — ohne es zu lesen.

    Hier ging das Foto des Blatts an ein Modell, das daraus Abschnitte
    machte. Damit verliess das Bild den Haushalt, mit allem, was zufaellig
    mit drauf war: der Name in der Kopfzeile, die Handschrift des Kindes,
    was neben dem Blatt auf dem Tisch lag. Ein Bild laesst sich nicht
    saeubern wie ein Text.

    Bis das Lesen auf dem Geraet laeuft (Schritt 2: Tesseract im Browser,
    zum Server geht nur gefilterter Text), bleibt das Blatt liegen und
    das Thema kommt von den Eltern — das tut es beim Hochladen ohnehin
    schon, es war nur doppelt.
    """
    doc_id = int(payload["document_id"])
    doc = db.q1("SELECT * FROM document WHERE id = ?", doc_id)
    if doc is None or doc["state"] not in ("neu",):
        return

    from .faecher import schluessel
    if schluessel(doc["subject"]) is None:
        # Ohne Fach wird nichts aufgenommen: das Blatt wartet im Elternordner.
        return

    with db.tx() as c:
        c.execute(
            """UPDATE document SET state='abgelegt', note=?
                WHERE id=? AND state='neu'""",
            ("Abgelegt. Karo liest Blätter gerade nicht selbst — das Thema "
             "steht beim Hochladen dabei.", doc_id))

    # Das eingetippte Thema wird zum Vorschlag, den ein Mensch bestaetigt —
    # genau wie vorher, nur ohne den Umweg ueber ein Modell.
    from . import topics
    topics.aus_blatt(doc_id)

    # Liegt zu diesem Blatt schon Text vor, schlaegt Karo daraus wie bisher
    # Unterthemen vor. Heute ist das nie der Fall — Text entsteht erst, wenn
    # das Lesen auf dem Geraet laeuft (Schritt 2). Die Zeile steht hier, damit
    # der Weg dann wieder zusammenhaengt und nicht jemand suchen muss, warum
    # `topic_propose` niemand mehr ruft.
    hat_text = db.q1("SELECT 1 AS da FROM kb_chunk WHERE document_id=? LIMIT 1", doc_id)
    if hat_text:
        with db.tx() as c:
            _einreihen(c, "topic_propose", {"document_id": doc_id}, f"topic:{doc_id}")


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


def suche(text: str, fach: str, limit: int = config.ops().kb_suche_treffer, arten: tuple[str, ...] | None = None,
          topic_id: int | None = None) -> list[dict]:
    """Findet Abschnitte in der Wissensbasis — nur auf Blättern des Fachs.

    Erst nach Thema, dann per Volltext — ein zugeordneter Abschnitt ist immer
    relevanter als ein Volltexttreffer. Ein Blatt aus Englisch taucht nie in
    einer Mathematikerklärung auf, auch wenn ein Wort zufällig passt.
    """
    from .faecher import schluessel
    fach = schluessel(fach)
    if fach is None:
        return []
    treffer: list[dict] = []
    gesehen: set[int] = set()

    if topic_id:
        for r in db.q(
            """SELECT k.*, d.source_name FROM kb_chunk k
                 JOIN document d ON d.id = k.document_id
                WHERE k.topic_id = ? AND d.subject = ?
                ORDER BY k.art, k.id LIMIT ?""",
                topic_id, fach, limit):
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
                        WHERE kb_fts MATCH ? AND d.subject = ?
                        ORDER BY bm25(kb_fts) LIMIT ?""",
                    abfrage, fach, limit * 2)
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


def _fach_von(topic_id: int) -> str | None:
    row = db.q1("SELECT subject FROM topic WHERE id=?", topic_id)
    return row["subject"] if row else None


def lehrmaterial(topic_id: int, label: str, limit: int = config.ops().kb_lehrmaterial_treffer) -> list[dict]:
    """Nur das, was tatsächlich etwas erklärt — aus dem Fach des Themas."""
    alles = suche(label, _fach_von(topic_id), limit=limit * 2, arten=LEHR_ARTEN, topic_id=topic_id)
    lehr = [a for a in alles if a["art"] in LEHR_ARTEN]
    return (lehr or alles)[:limit]


def aufgaben(topic_id: int, label: str, limit: int = 8) -> list[dict]:
    alles = suche(label, _fach_von(topic_id), limit=limit * 2, arten=("aufgabe",), topic_id=topic_id)
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
