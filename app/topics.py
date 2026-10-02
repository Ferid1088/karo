"""Themen — vorgeschlagen vom KI-Anbieter, freigegeben von einem Menschen.

Ein Thema ist die Einheit, in der Karo bewertet und lehrt. Es kommt nicht aus
einer festen Liste, sondern aus dem Material, das tatsächlich im Unterricht
verwendet wurde — und es wird erst benutzt, wenn ein Erwachsener es bestätigt
hat.
"""

from __future__ import annotations

import difflib
import logging
import re
import unicodedata

from . import config, db, jobs, kb, prompts
from .domain import Flag
from .ai import AIClient

log = logging.getLogger("karo.topics")

VORSCHLAG = "vorschlag"
AKTIV = "aktiv"
ABGELEHNT = "abgelehnt"


def client() -> AIClient:
    return AIClient.from_config(config.load())


# --------------------------------------------------------------------------
# Vorschlagen
# --------------------------------------------------------------------------

def aus_blatt(doc_id: int) -> str | None:
    """Legt das beim Hochladen eingetippte Thema an, ohne Modell.

    Frueher schlug ein Modell Themen vor, nachdem es das Foto des Blatts
    gelesen hatte. Das Foto geht nicht mehr hinaus (siehe app/llm/base.py) —
    und es braucht auch keins: den Themennamen tippt beim Hochladen ohnehin
    ein Mensch ein, das Modell hat ihn bisher nur bestaetigt.

    Gibt den Code des angelegten Themas zurueck, oder None, wenn es das
    Thema schon gibt.
    """
    from .faecher import schluessel

    doc = db.q1("SELECT themenname, subject FROM document WHERE id = ?", doc_id)
    if doc is None:
        return None
    fach = schluessel(doc["subject"])
    label = (doc["themenname"] or "").strip()
    if fach is None or not label:
        return None
    code = normalize_code(label)
    if not code:
        return None
    with db.tx() as c:
        if c.execute("SELECT 1 FROM topic WHERE code = ?", (code,)).fetchone():
            return None
        # Aehnliche Namen fangen wir wie bisher ab: „Brueche addieren" und
        # „Brueche addieren." sind dasselbe Thema, und zwei davon zu fuehren
        # verwirrt mehr, als es hilft.
        labels = [r["label"] for r in c.execute(
            "SELECT label FROM topic WHERE subject = ? AND state != ?",
            (fach, ABGELEHNT)).fetchall()]
        if naechstes_duplikat(label, labels):
            return None
        c.execute(
            """INSERT INTO topic (subject, code, label, beschreibung, state,
                                  quelle_doc, sort, created_at)
               VALUES (?, ?, ?, NULL, ?, ?, 500, ?)""",
            (fach, code, label[:200], VORSCHLAG, doc_id, db.now()))
    return code


@jobs.handler("topic_propose")
def job_topic_propose(payload: dict) -> None:
    """Schlägt Themen für ein neu erschlossenes Blatt vor."""
    doc_id = int(payload["document_id"])
    quellen = [dict(r) for r in db.q(
        """SELECT id, art, titel, text FROM kb_chunk
            WHERE document_id = ? ORDER BY position LIMIT 30""", doc_id)]
    if not quellen:
        return

    from .faecher import NAMEN, erkenne, schluessel
    doc = db.q1("SELECT themenname, subject FROM document WHERE id = ?", doc_id)
    fach = schluessel(doc["subject"]) if doc else None
    if fach is None:
        return
    cfg = config.load()
    # Nur Themen desselben Fachs zählen als „schon vorhanden“.
    vorhanden = [dict(r) for r in db.q(
        "SELECT code, label FROM topic WHERE state != ? AND subject = ? ORDER BY sort",
        ABGELEHNT, fach)]

    ergebnis = client().complete(
        purpose="topic_propose",
        prompt=prompts.topic_prompt(cfg.learner_grade, NAMEN[fach],
                                    kb.geschwaerzt(quellen), vorhanden,
                                    themenname=doc["themenname"] if doc else None),
        schema=prompts.TOPIC_SCHEMA,
        system=prompts.SYSTEM,
    )

    with db.tx() as c:
        bekannt_rows = [dict(r) for r in c.execute("SELECT code, label FROM topic")]
        bekannt = {r["code"] for r in bekannt_rows}
        bekannte_labels = [r["label"] for r in bekannt_rows]
        uebersprungen = []
        for roh in ergebnis.data.get("themen") or []:
            code = normalize_code(roh.get("code") or roh.get("label") or "")
            label = (roh.get("label") or "").strip()
            if not code or not label:
                continue
            if code in bekannt:
                uebersprungen.append(label)
                continue
            # SUBJECT_MISMATCH: ein Thema aus einem anderen Fach wird nicht
            # im Fach dieses Blatts angelegt.
            erkannt = schluessel(roh.get("fach")) or erkenne(label)
            if erkannt and erkannt != fach:
                uebersprungen.append(f"{label} (gehört nicht zu {NAMEN[fach]})")
                continue
            aehnlich = naechstes_duplikat(label, bekannte_labels)
            if aehnlich:
                uebersprungen.append(f"{label} (ähnlich zu „{aehnlich}“)")
                continue
            bekannt.add(code)
            bekannte_labels.append(label)
            c.execute(
                """INSERT INTO topic (subject, code, label, beschreibung, state,
                                      quelle_doc, sort, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (fach, code, label[:200],
                 (roh.get("beschreibung") or "")[:500] or None,
                 VORSCHLAG, doc_id, _sortwert(roh), db.now()))

        if uebersprungen:
            bisher = c.execute(
                "SELECT note FROM document WHERE id = ?", (doc_id,)).fetchone()
            notiz = (bisher["note"] + " · " if bisher and bisher["note"] else "")
            notiz += "Bereits vorhandenes Thema erkannt, nichts Neues angelegt: "
            notiz += "; ".join(uebersprungen)
            c.execute("UPDATE document SET note = ? WHERE id = ?",
                      (notiz[:500], doc_id))


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


DUPLIKAT_SCHWELLE = config.ops().themen_duplikat_schwelle


def _vergleichstext(label: str) -> str:
    text = unicodedata.normalize("NFKD", label).lower()
    text = (text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
                .replace("ß", "ss"))
    return re.sub(r"[^a-z0-9]+", "", text)


def naechstes_duplikat(label: str, vorhandene_labels: list[str]) -> str | None:
    """Gibt das erste Label aus `vorhandene_labels` zurueck, dem `label` zum
    Verwechseln aehnlich ist — auch wenn der Themencode (der 1:1 aus der
    Schreibweise kommt) sich unterscheidet. Ohne diesen Abgleich landet
    dasselbe Thema manchmal doppelt in der Datenbank, einmal z. B. als
    'Multiplikation', einmal als 'multiplication' aus einer anderssprachigen
    Quelle — beide aktiv, aber mit unabhaengigem Gelernt-Status, sodass
    dasselbe Thema gleichzeitig unter 'Lernen' und 'Erfolge' auftaucht.
    None, wenn kein Treffer gefunden wurde — Aufrufer nutzen den Rueckgabewert
    auch, um dem Menschen zu sagen, WELCHES Thema den Konflikt ausgeloest hat,
    statt ein Thema kommentarlos verschwinden zu lassen."""
    ziel = _vergleichstext(label)
    if not ziel:
        return None
    for vorhanden in vorhandene_labels:
        if (difflib.SequenceMatcher(None, ziel, _vergleichstext(vorhanden)).ratio()
                >= DUPLIKAT_SCHWELLE):
            return vorhanden
    return None


def ist_duplikat(label: str, vorhandene_labels: list[str]) -> bool:
    return naechstes_duplikat(label, vorhandene_labels) is not None


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
                       thema["subject"], limit=config.ops().themen_zuordnung_treffer)
    n = 0
    with db.tx() as c:
        for t in treffer:
            cur = c.execute(
                "UPDATE kb_chunk SET topic_id=? WHERE id=? AND topic_id IS NULL",
                (topic_id, t["id"]))
            n += cur.rowcount
    return n


def anlegen(label: str, beschreibung: str = "", *, subject: str) -> int | None:
    """Thema von Hand anlegen — für alles, was die KI nicht vorgeschlagen hat.

    Wirft `faecher.FachFehler`/`SubjectMismatch`, wenn das Fach fehlt oder
    das Thema in ein anderes Fach gehört.
    """
    from .faecher import pruefe
    label = label.strip()[:200]
    if not label:
        return None
    subject = pruefe(label, subject)
    code = normalize_code(label)
    if not code:
        return None
    with db.tx() as c:
        if c.execute("SELECT 1 FROM topic WHERE code=?", (code,)).fetchone():
            return None
        vorhandene_labels = [r["label"] for r in c.execute("SELECT label FROM topic").fetchall()]
        if ist_duplikat(label, vorhandene_labels):
            return None
        cur = c.execute(
            """INSERT INTO topic (subject, code, label, beschreibung, state,
                                  sort, created_at)
               VALUES (?, ?, ?, ?, ?, 500, ?)""",
            (subject, code, label, beschreibung.strip()[:500] or None,
             AKTIV, db.now()))
        neu = cur.lastrowid
    zuordnen(neu)
    return neu
