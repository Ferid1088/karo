"""Themen — vorgeschlagen von Claude, freigegeben von einem Menschen.

Ein Thema ist die Einheit, in der Karo bewertet und lehrt. Es kommt nicht aus
einer festen Liste, sondern aus dem Material, das tatsächlich im Unterricht
verwendet wurde — und es wird erst benutzt, wenn ein Erwachsener es bestätigt
hat.
"""

from __future__ import annotations

import logging
import re
import unicodedata

from . import config, db, jobs, kb, prompts
from .domain import Flag
from .llm import ClaudeClient

log = logging.getLogger("karo.topics")

VORSCHLAG = "vorschlag"
AKTIV = "aktiv"
ABGELEHNT = "abgelehnt"


def client() -> ClaudeClient:
    return ClaudeClient.from_config(config.load())


# --------------------------------------------------------------------------
# Vorschlagen
# --------------------------------------------------------------------------

@jobs.handler("topic_propose")
def job_topic_propose(payload: dict) -> None:
    """Schlägt Themen für ein neu erschlossenes Blatt vor."""
    doc_id = int(payload["document_id"])
    quellen = [dict(r) for r in db.q(
        """SELECT id, art, titel, text FROM kb_chunk
            WHERE document_id = ? ORDER BY position LIMIT 30""", doc_id)]
    if not quellen:
        return

    cfg = config.load()
    vorhanden = [dict(r) for r in db.q(
        "SELECT code, label FROM topic WHERE state != ? ORDER BY sort", ABGELEHNT)]
    doc = db.q1("SELECT themenname FROM document WHERE id = ?", doc_id)

    ergebnis = client().complete(
        purpose="topic_propose",
        prompt=prompts.topic_prompt(cfg.learner_grade, cfg.subject,
                                    kb.geschwaerzt(quellen), vorhanden,
                                    themenname=doc["themenname"] if doc else None),
        schema=prompts.TOPIC_SCHEMA,
        system=prompts.SYSTEM,
    )

    bekannt = {r["code"] for r in db.q("SELECT code FROM topic")}
    with db.tx() as c:
        for roh in ergebnis.data.get("themen") or []:
            code = normalize_code(roh.get("code") or roh.get("label") or "")
            label = (roh.get("label") or "").strip()
            if not code or not label or code in bekannt:
                continue
            bekannt.add(code)
            c.execute(
                """INSERT INTO topic (subject, code, label, beschreibung, state,
                                      quelle_doc, sort, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (cfg.subject, code, label[:200],
                 (roh.get("beschreibung") or "")[:500] or None,
                 VORSCHLAG, doc_id, _sortwert(roh), db.now()))


def _sortwert(roh: dict) -> int:
    try:
        return max(0, min(999, int(roh.get("reihenfolge") or 500)))
    except (TypeError, ValueError):
        return 500


def normalize_code(text: str) -> str:
    """Macht aus beliebigem Text einen stabilen Themencode."""
    text = unicodedata.normalize("NFKD", text)
    text = (text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
                .replace("ß", "ss").replace("Ä", "AE").replace("Ö", "OE")
                .replace("Ü", "UE"))
    text = text.encode("ascii", "ignore").decode().upper()
    text = re.sub(r"[^A-Z0-9.]+", ".", text).strip(".")
    text = re.sub(r"\.{2,}", ".", text)
    return text[:60]


# --------------------------------------------------------------------------
# Lesen
# --------------------------------------------------------------------------

def passende(themen: list[str], zeilen: list[dict]) -> list[dict]:
    """Von `zeilen` (Themen-Datensätze mit 'label') die, deren Bezeichnung zu
    einem der angekündigten Themen passt (Groß-/Kleinschreibung egal, als
    Teilstring in beide Richtungen — Ankündigungen und Themenkatalog nennen
    dieselbe Sache oft leicht unterschiedlich).

    Für die Klassenarbeit: ohne diesen Abgleich würde jede Arbeit sich mit
    ALLEN farbig geflaggten Themen im Fach befassen, auch mit Themen, die auf
    dem Ankündigungsblatt gar nicht standen. Ohne Angabe oder ohne Treffer
    bleibt es bei der vollen Liste — besser eine zu breite Auswahl als gar
    keine, wenn die Ankündigung leer oder schlecht lesbar war.
    """
    if not themen:
        return zeilen
    gesucht = [t.lower() for t in themen]
    treffer = [z for z in zeilen
               if any(g in z["label"].lower() or z["label"].lower() in g
                      for g in gesucht)]
    return treffer or zeilen


def liste(state: str | None = None) -> list[dict]:
    sql = """SELECT t.*, COALESCE(f.flag, ?) AS flag,
                    COALESCE(f.antworten, 0) AS antworten,
                    COALESCE(f.richtig, 0) AS richtig,
                    f.haupt_fehler, f.letzte_uebung, f.begruendung,
                    (SELECT COUNT(*) FROM kb_chunk k WHERE k.topic_id = t.id)
                        AS quellen,
                    (SELECT COUNT(*) FROM kb_chunk k WHERE k.topic_id = t.id
                       AND k.art IN ({lehr_platzhalter}))
                        AS lehr_quellen,
                    (SELECT id FROM lesson l WHERE l.topic_id = t.id
                       AND l.state NOT IN ('gelernt','abgebrochen')
                                            ORDER BY l.id DESC LIMIT 1) AS offene_lesson,
                                        (SELECT r.id FROM lesson_round r
                                             JOIN lesson l ON l.id = r.lesson_id
                                            WHERE l.topic_id = t.id AND r.material_pfad IS NOT NULL
                                            ORDER BY r.id DESC LIMIT 1) AS neues_material
               FROM topic t
               LEFT JOIN topic_flag f ON f.topic_id = t.id""".format(
        lehr_platzhalter=",".join("?" * len(kb.LEHR_ARTEN)))
    params: list = [Flag.WEISS.value, *kb.LEHR_ARTEN]
    if state:
        sql += " WHERE t.state = ?"
        params.append(state)
    sql += " ORDER BY t.sort, t.label"
    return [dict(r) for r in db.q(sql, *params)]


def get(topic_id: int) -> dict | None:
    row = db.q1(
        """SELECT t.*, COALESCE(f.flag, ?) AS flag,
                  COALESCE(f.antworten, 0) AS antworten,
                  COALESCE(f.richtig, 0) AS richtig,
                  f.haupt_fehler, f.letzte_uebung, f.begruendung
             FROM topic t LEFT JOIN topic_flag f ON f.topic_id = t.id
            WHERE t.id = ?""", Flag.WEISS.value, topic_id)
    return dict(row) if row else None


def anzahl_vorschlaege() -> int:
    row = db.q1("SELECT COUNT(*) AS n FROM topic WHERE state = ?", VORSCHLAG)
    return row["n"] if row else 0


# --------------------------------------------------------------------------
# Freigeben
# --------------------------------------------------------------------------

def entscheiden(entscheidungen: list[dict]) -> dict:
    """Übernimmt die Freigabe.

    `entscheidungen` enthält je Thema: id, aktion ('aktiv'|'abgelehnt'|'offen')
    und optional ein geändertes Label. Ein umbenanntes Thema behält seinen
    Code — daran hängen die Antworten.
    """
    angenommen = abgelehnt = umbenannt = 0
    with db.tx() as c:
        for e in entscheidungen:
            topic_id = int(e["id"])
            row = c.execute("SELECT label, state FROM topic WHERE id = ?",
                            (topic_id,)).fetchone()
            if row is None:
                continue
            aktion = e.get("aktion")
            if aktion not in (AKTIV, ABGELEHNT):
                continue

            label = (e.get("label") or "").strip()[:200]
            if label and label != row["label"]:
                c.execute("UPDATE topic SET label=? WHERE id=?", (label, topic_id))
                umbenannt += 1

            c.execute("UPDATE topic SET state=? WHERE id=?", (aktion, topic_id))
            if aktion == AKTIV:
                angenommen += 1
            else:
                abgelehnt += 1

    for e in entscheidungen:
        if e.get("aktion") == AKTIV:
            zuordnen(int(e["id"]))

    return {"angenommen": angenommen, "abgelehnt": abgelehnt,
            "umbenannt": umbenannt}


def zuordnen(topic_id: int) -> int:
    """Hängt passende Abschnitte der Wissensbasis an ein Thema.

    Nur Abschnitte, die noch keinem Thema zugeordnet sind — ein Abschnitt
    gehört zu genau einem Thema, sonst zählt er in zwei Profilen.
    """
    thema = get(topic_id)
    if thema is None:
        return 0
    treffer = kb.suche(f"{thema['label']} {thema.get('beschreibung') or ''}",
                       limit=30)
    n = 0
    with db.tx() as c:
        for t in treffer:
            cur = c.execute(
                "UPDATE kb_chunk SET topic_id=? WHERE id=? AND topic_id IS NULL",
                (topic_id, t["id"]))
            n += cur.rowcount
    return n


def anlegen(label: str, beschreibung: str = "") -> int | None:
    """Thema von Hand anlegen — für alles, was Claude nicht vorgeschlagen hat."""
    label = label.strip()[:200]
    if not label:
        return None
    cfg = config.load_safe()
    code = normalize_code(label)
    if not code:
        return None
    with db.tx() as c:
        if c.execute("SELECT 1 FROM topic WHERE code=?", (code,)).fetchone():
            return None
        cur = c.execute(
            """INSERT INTO topic (subject, code, label, beschreibung, state,
                                  sort, created_at)
               VALUES (?, ?, ?, ?, ?, 500, ?)""",
            (cfg.subject, code, label, beschreibung.strip()[:500] or None,
             AKTIV, db.now()))
        neu = cur.lastrowid
    zuordnen(neu)
    return neu
