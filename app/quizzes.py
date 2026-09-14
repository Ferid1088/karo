"""Fragen, Antworten, Flaggen.

Der Kern der Bewertung. Zwei Wege für die Antworten:

  bildschirm — das Kind tippt direkt in die App. Auswertung in Sekunden,
               damit der Lernzyklus in einer Sitzung durchlaufen kann.
  papier     — das Blatt wird gedruckt, gerechnet, fotografiert. Näher am
               echten Klassenarbeitsformat, dauert einen Tag.

Beide enden an derselben Stelle: die Lernbegleitung gibt jede Bewertung frei,
bevor sie in `answer_log` landet. Danach ist sie unveränderlich.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from . import config, db, jobs, kb, pii, prompts, topics
from .domain import (
    ERROR_LABELS,
    Answer,
    Flag,
    Rule,
    compute_flag,
)
from .llm import ClaudeClient

log = logging.getLogger("karo.quiz")

BILDSCHIRM = "bildschirm"
PAPIER = "papier"

# --- Zustandsmaschine (KaroRefactoring_Plan.md, Abschnitt 13) --------------
# offen -> bereit -> [beantwortet ->] ausgewertet.
#   offen:       Karo erstellt die Fragen noch (anfordern/job_quiz_build).
#   bereit:      Fragen stehen. Beim Bildschirmweg antwortet jetzt das Kind;
#                bei einer muendlichen Lernkontrolle (exam_learning) kann
#                die Lernbegleitung auch direkt von hier aus freigeben, ohne
#                dass das Kind digital tippt.
#   beantwortet: Antworten da (antworten_speichern); Karo schlaegt eine
#                Bewertung vor (job_quiz_check).
#   ausgewertet: der Vorschlag steht — heisst noch nicht "freigegeben".
#   freigegeben: der Endzustand. `finished_at` bleibt der Zeitstempel dazu,
#                ist aber nicht mehr die Quelle der Wahrheit — freigeben()
#                setzt beide Felder in derselben atomaren Bedingung.
# antworten_speichern()/freigeben() pruefen beide auf das jeweils Noetige
# statt auf einen einzelnen erwarteten Vorzustand (siehe deren Docstrings).
STATE_OFFEN = "offen"
STATE_BEREIT = "bereit"
STATE_BEANTWORTET = "beantwortet"
STATE_AUSGEWERTET = "ausgewertet"
STATE_FREIGEGEBEN = "freigegeben"


def client() -> ClaudeClient:
    return ClaudeClient.from_config(config.load())


class QuizError(Exception):
    """Verständlicher Fehler im Ablauf einer Fragerunde."""


# --------------------------------------------------------------------------
# Fragen erzeugen
# --------------------------------------------------------------------------

def anfordern(topic_id: int, anlass: str = "evaluation", modus: str = BILDSCHIRM,
              lesson_id: int | None = None, round_nr: int | None = None,
              anzahl: int = 5) -> int | None:
    """Legt eine leere Fragerunde an und reiht das Erzeugen ein."""
    if modus not in (BILDSCHIRM, PAPIER):
        raise QuizError("Unbekannter Antwortweg.")
    if topics.get(topic_id) is None:
        raise QuizError("Thema nicht gefunden.")

    with db.tx() as c:
        offen = c.execute(
            """SELECT id FROM quiz WHERE topic_id=? AND anlass=? AND state='offen'
                 AND COALESCE(lesson_id, -1) = COALESCE(?, -1)
                 AND COALESCE(round_nr, -1) = COALESCE(?, -1)
                ORDER BY id DESC LIMIT 1""",
            (topic_id, anlass, lesson_id, round_nr)).fetchone()
        if offen is not None:
            return offen["id"]
        cur = c.execute(
            """INSERT INTO quiz (topic_id, anlass, lesson_id, round_nr, modus,
                                 state, created_at)
               VALUES (?, ?, ?, ?, ?, 'offen', ?)""",
            (topic_id, anlass, lesson_id, round_nr, modus, db.now()))
        quiz_id = cur.lastrowid

    jobs.enqueue("quiz_build", {"quiz_id": quiz_id, "anzahl": anzahl},
                 dedup_key=f"quiz_build:{quiz_id}")
    return quiz_id


@jobs.handler("quiz_build")
def job_quiz_build(payload: dict) -> None:
    quiz_id = int(payload["quiz_id"])
    anzahl = int(payload.get("anzahl") or 5)
    quiz = db.q1("SELECT * FROM quiz WHERE id = ?", quiz_id)
    if quiz is None or quiz["state"] != STATE_OFFEN:
        return
    if db.q1("SELECT 1 FROM question WHERE quiz_id = ?", quiz_id):
        return                                  # schon gebaut

    thema = topics.get(quiz["topic_id"])
    if thema is None:
        return
    cfg = config.load()

    quellen = kb.geschwaerzt(
        kb.suche(f"{thema['label']} {thema.get('beschreibung') or ''}",
                 limit=8, topic_id=quiz["topic_id"]))

    fehlerbild = ERROR_LABELS.get(thema.get("haupt_fehler") or "")
    beschreibung = thema.get("beschreibung") or ""
    if quiz["anlass"] == "lernrunde" and quiz["lesson_id"]:
        runde = db.q1("SELECT erklaerung FROM lesson_round WHERE lesson_id=? AND nr=?",
                      quiz["lesson_id"], quiz["round_nr"])
        if runde and runde["erklaerung"]:
            beschreibung += "\nGerade gelerntes Material:\n" + runde["erklaerung"]
        alte_fragen = db.q("""SELECT q.frage FROM question q JOIN quiz z ON z.id=q.quiz_id
                             WHERE z.topic_id=? AND z.id<>? ORDER BY q.id DESC LIMIT 20""",
                           quiz["topic_id"], quiz_id)
        if alte_fragen:
            beschreibung += "\nVerwende neue Aufgaben mit anderen Zahlen als diese bisherigen Fragen:\n"
            beschreibung += "\n".join(r["frage"] for r in alte_fragen)
    ergebnis = client().complete(
        purpose=f"quiz_{quiz['anlass']}",
        prompt=prompts.quiz_prompt(
            cfg.learner_grade, cfg.subject, thema["label"],
            pii.scrub(beschreibung, cfg.learner_name), quellen, quiz["anlass"],
            anzahl=anzahl, bekannte_fehler=fehlerbild),
        schema=prompts.QUIZ_SCHEMA,
        system=prompts.SYSTEM,
    )

    fragen = ergebnis.data.get("fragen") or []
    if not fragen:
        raise QuizError("Das Modell hat keine Fragen geliefert.")

    with db.tx() as c:
        for i, f in enumerate(fragen, start=1):
            frage = (f.get("frage") or "").strip()
            if not frage:
                continue
            c.execute(
                """INSERT INTO question (quiz_id, position, frage, erwartet, stufe)
                   VALUES (?, ?, ?, ?, ?)""",
                (quiz_id, i, frage[:2000],
                 (f.get("erwartet") or "")[:1000] or None,
                 f.get("stufe") if f.get("stufe") in
                 ("leicht", "mittel", "schwer") else "mittel"))
        c.execute("UPDATE quiz SET state='bereit' WHERE id=? AND state=?",
                  (quiz_id, STATE_OFFEN))

    if quiz["modus"] == PAPIER:
        jobs.enqueue("quiz_print", {"quiz_id": quiz_id},
                     dedup_key=f"quiz_print:{quiz_id}")


# --------------------------------------------------------------------------
# Papierweg: Blatt drucken
# --------------------------------------------------------------------------

@jobs.handler("quiz_print")
def job_quiz_print(payload: dict) -> None:
    from . import ingest
    from .media import sheets

    quiz_id = int(payload["quiz_id"])
    quiz = db.q1("SELECT * FROM quiz WHERE id = ?", quiz_id)
    if quiz is None:
        return
    thema = topics.get(quiz["topic_id"])
    fragen = [dict(r) for r in db.q(
        "SELECT * FROM question WHERE quiz_id=? ORDER BY position", quiz_id)]
    html = sheets.aufgabenblatt(thema["label"] if thema else "Übung", fragen)
    pfad = ingest.write_material(
        f"{db.today()}_{(thema or {}).get('code', 'thema')}_Fragebogen.html", html)
    if pfad:
        with db.tx() as c:
            c.execute("UPDATE quiz SET blatt_pfad=? WHERE id=?", (pfad, quiz_id))


# --------------------------------------------------------------------------
# Antworten aufnehmen
# --------------------------------------------------------------------------

def antworten_speichern(quiz_id: int, antworten: dict[int, str]) -> int:
    """Nimmt die Antworten des Kindes auf und reiht die Auswertung ein.

    Die Antworten sind noch keine Bewertung — sie stehen in `question`, nicht
    in `answer_log`. Dorthin kommen sie erst nach der Freigabe.
    """
    quiz = db.q1("SELECT * FROM quiz WHERE id = ?", quiz_id)
    if quiz is None:
        raise QuizError("Fragerunde nicht gefunden.")
    if quiz["state"] == STATE_FREIGEGEBEN:
        raise QuizError(
            "Diese Fragerunde ist bereits freigegeben und kann nicht mehr "
            "geändert werden.")
    if quiz["state"] == STATE_AUSGEWERTET:
        raise QuizError("Diese Fragerunde ist bereits ausgewertet.")

    gueltig = {r["id"] for r in db.q(
        "SELECT id FROM question WHERE quiz_id = ?", quiz_id)}
    n = 0
    with db.tx() as c:
        # Frische Pruefung INNERHALB der Transaktion (BEGIN IMMEDIATE, siehe
        # db.tx()): die Pruefung oben vor der Transaktion schliesst nur den
        # ueblichen Fall aus. Kommt eine Freigabe genau zwischen dieser
        # Pruefung und dem Start der Transaktion dazwischen, sieht dieser
        # Blick hier den frischen Stand und verhindert, dass `question`
        # nach FREIGEGEBEN noch beschrieben wird (change.txt P1).
        aktuell = c.execute("SELECT state FROM quiz WHERE id=?", (quiz_id,)).fetchone()
        if aktuell is None or aktuell["state"] == STATE_FREIGEGEBEN:
            raise QuizError(
                "Diese Fragerunde ist bereits freigegeben und kann nicht "
                "mehr geändert werden.")
        for frage_id, text in antworten.items():
            if int(frage_id) not in gueltig:
                continue
            c.execute("UPDATE question SET schueler_antwort=? WHERE id=?",
                      ((text or "").strip()[:2000] or None, int(frage_id)))
            n += 1
        c.execute("UPDATE quiz SET state='beantwortet' WHERE id=? AND state != ?",
                  (quiz_id, STATE_FREIGEGEBEN))

    jobs.enqueue("quiz_check", {"quiz_id": quiz_id},
                 dedup_key=f"quiz_check:{quiz_id}")
    return n


@jobs.handler("quiz_check")
def job_quiz_check(payload: dict) -> None:
    """Wertet die Antworten aus — als Vorschlag, nicht als Ergebnis."""
    quiz_id = int(payload["quiz_id"])
    quiz = db.q1("SELECT * FROM quiz WHERE id = ?", quiz_id)
    if quiz is None or quiz["state"] != STATE_BEANTWORTET:
        return

    thema = topics.get(quiz["topic_id"])
    fragen = [dict(r) for r in db.q(
        "SELECT * FROM question WHERE quiz_id=? ORDER BY position", quiz_id)]
    if not fragen or thema is None:
        return

    cfg = config.load()
    name = cfg.learner_name
    paare = [{"position": f["position"],
              "frage": pii.scrub(f["frage"], name),
              "erwartet": pii.scrub(f.get("erwartet") or "", name),
              "antwort": pii.scrub(f.get("schueler_antwort") or "", name)}
             for f in fragen]

    ergebnis = client().complete(
        purpose="quiz_check",
        prompt=prompts.check_prompt(cfg.learner_grade, cfg.subject,
                                    thema["label"], paare),
        schema=prompts.CHECK_SCHEMA,
        system=prompts.SYSTEM,
    )

    nach_position = {f["position"]: f["id"] for f in fragen}
    gesehen: set[int] = set()
    with db.tx() as c:
        # Frische Pruefung: der LLM-Aufruf oben ist der Moment, in dem eine
        # direkte Freigabe (z. B. muendliche Lernkontrolle) dazwischenkommen
        # kann. Ohne diesen Blick wuerde die Schleife unten `question` noch
        # mit einem laengst ueberholten Vorschlag beschreiben, obwohl die
        # Fragerunde schon abschliessend freigegeben ist (change.txt P1).
        aktuell = c.execute("SELECT state FROM quiz WHERE id=?", (quiz_id,)).fetchone()
        if aktuell is None or aktuell["state"] != STATE_BEANTWORTET:
            return
        for r in ergebnis.data.get("ergebnisse") or []:
            try:
                frage_id = nach_position.get(int(r.get("position")))
            except (TypeError, ValueError):
                continue
            if frage_id is None or frage_id in gesehen:
                continue
            gesehen.add(frage_id)
            fehler = r.get("fehlertyp")
            c.execute(
                """UPDATE question
                      SET vorschlag_richtig=?, vorschlag_fehler=?,
                          vorschlag_grund=?, vorschlag_konf=?, auswert_call_id=?
                    WHERE id=?""",
                (int(bool(r.get("richtig"))),
                 fehler if fehler in ERROR_LABELS else None,
                 _grund(r), _konfidenz(r.get("konfidenz")),
                 ergebnis.call_id, frage_id))
        c.execute("UPDATE quiz SET state='ausgewertet' WHERE id=? AND state='beantwortet'",
                  (quiz_id,))


def _grund(r: dict) -> str:
    """Begründung für die Lernbegleitung und Rückmeldung für das Kind, getrennt."""
    return json.dumps({"fuer_begleitung": (r.get("begruendung") or "")[:800],
                       "fuer_kind": (r.get("rueckmeldung") or "")[:400]},
                      ensure_ascii=False)


def grund_teile(rohtext: str | None) -> dict:
    if not rohtext:
        return {"fuer_begleitung": "", "fuer_kind": ""}
    try:
        d = json.loads(rohtext)
        return {"fuer_begleitung": d.get("fuer_begleitung", ""),
                "fuer_kind": d.get("fuer_kind", "")}
    except (json.JSONDecodeError, AttributeError):
        return {"fuer_begleitung": rohtext, "fuer_kind": ""}


def _konfidenz(wert) -> float:
    """Unbrauchbare Angaben gelten als niedrige Konfidenz.

    None wäre hier falsch: die Oberfläche liest None als „sicher“ und würde die
    Warnmarkierung genau dort weglassen, wo das Modell etwas Unerwartetes
    geantwortet hat.
    """
    try:
        return max(0.0, min(1.0, float(wert)))
    except (TypeError, ValueError):
        return 0.3


# --------------------------------------------------------------------------
# Papierweg: Antwortblatt fotografieren
# --------------------------------------------------------------------------

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "lesbarkeit": {"type": "string", "enum": ["gut", "teilweise", "schlecht"]},
        "antworten": {
            "type": "array", "maxItems": 40,
            "items": {
                "type": "object",
                "properties": {
                    "position": {"type": "integer"},
                    "antwort": {"type": ["string", "null"]},
                    "sicher_gelesen": {"type": "boolean"},
                },
                "required": ["position", "antwort", "sicher_gelesen"],
            },
        },
    },
    "required": ["lesbarkeit", "antworten"],
}


def blatt_hochladen(quiz_id: int, daten: bytes, endung: str) -> int:
    """Nimmt das Foto des bearbeiteten Fragebogens auf.

    Die Zuordnung ist eindeutig, weil das Bild auf der Seite genau dieser
    Fragerunde hochgeladen wird — kein Code auf dem Blatt, kein Zuordnen im
    Nachhinein.
    """
    from . import ingest

    quiz = db.q1("SELECT * FROM quiz WHERE id = ?", quiz_id)
    if quiz is None:
        raise QuizError("Fragerunde nicht gefunden.")
    if quiz["state"] not in (STATE_BEREIT, STATE_BEANTWORTET):
        raise QuizError("Zu dieser Fragerunde passt kein Antwortblatt mehr.")

    aufnahme = ingest.aufnehmen(daten, endung, rolle="bearbeitet")
    with db.tx() as c:
        c.execute("UPDATE quiz SET blatt_pfad=COALESCE(blatt_pfad, ?) WHERE id=?",
                  (aufnahme["stored_path"], quiz_id))
    jobs.enqueue("quiz_read_sheet",
                 {"quiz_id": quiz_id, "document_id": aufnahme["document_id"]},
                 dedup_key=f"quiz_read:{quiz_id}:{aufnahme['document_id']}")
    return aufnahme["document_id"]


@jobs.handler("quiz_read_sheet")
def job_quiz_read_sheet(payload: dict) -> None:
    """Liest die handschriftlichen Antworten vom fotografierten Blatt."""
    quiz_id = int(payload["quiz_id"])
    doc_id = int(payload["document_id"])
    quiz = db.q1("SELECT * FROM quiz WHERE id = ?", quiz_id)
    doc = db.q1("SELECT * FROM document WHERE id = ?", doc_id)
    if quiz is None or doc is None:
        return
    if quiz["state"] not in (STATE_BEREIT, STATE_BEANTWORTET):
        return

    fragen = [dict(r) for r in db.q(
        "SELECT * FROM question WHERE quiz_id=? ORDER BY position", quiz_id)]
    if not fragen:
        return

    cfg = config.load()
    liste = "\n".join(f"  {f['position']}. {f['frage'][:200]}" for f in fragen)
    prompt = f"""Auf dem Bild ist ein bearbeiteter Fragebogen aus dem Fach
{cfg.subject}, Klassenstufe {cfg.learner_grade} in Deutschland.

Diese Fragen stehen darauf:
{liste}

Lies zu jeder Nummer die handschriftliche Antwort ab — wörtlich, mit
Zwischenschritten, wenn welche dastehen. Korrigiere nichts und rechne nichts
nach; das ist reines Ablesen. Ist ein Feld leer, gib null zurück statt zu
raten. Setze sicher_gelesen auf false, sobald du bei einem Zeichen raten
müsstest. Einen Namen auf dem Blatt übernimm nicht."""

    ergebnis = client().complete(
        purpose="quiz_read_sheet", prompt=prompt, schema=ANSWER_SCHEMA,
        image_path=Path(doc["stored_path"]), system=prompts.SYSTEM)

    nach_position = {f["position"]: f["id"] for f in fragen}
    gefunden = 0
    uebernommen = False
    with db.tx() as c:
        # Frische Pruefung: der LLM-Aufruf oben ist wieder der Moment, in
        # dem eine direkte Freigabe dazwischenkommen kann. Erst danach
        # `question` beschreiben — sonst wuerden die abgelesenen Antworten
        # dort noch landen, obwohl die Fragerunde schon freigegeben ist
        # (change.txt P1). Das Dokument selbst gilt trotzdem als gelesen:
        # das Foto wurde tatsaechlich ausgewertet, nur eben zu spaet.
        aktuell = c.execute("SELECT state FROM quiz WHERE id=?", (quiz_id,)).fetchone()
        quiz_aktiv = aktuell is not None and aktuell["state"] in (STATE_BEREIT, STATE_BEANTWORTET)
        if quiz_aktiv:
            for a in ergebnis.data.get("antworten") or []:
                try:
                    frage_id = nach_position.get(int(a.get("position")))
                except (TypeError, ValueError):
                    continue
                if frage_id is None:
                    continue
                text = (a.get("antwort") or "").strip()
                c.execute("UPDATE question SET schueler_antwort=? WHERE id=?",
                          (text[:2000] or None, frage_id))
                if text:
                    gefunden += 1
        c.execute("UPDATE document SET state='gelesen' WHERE id=?", (doc_id,))
        if quiz_aktiv and gefunden:
            uebernommen = c.execute(
                "UPDATE quiz SET state='beantwortet' WHERE id=? AND state IN (?, ?)",
                (quiz_id, STATE_BEREIT, STATE_BEANTWORTET)).rowcount == 1

    if not quiz_aktiv:
        return  # anders abgeschlossen, waehrend das Foto gelesen wurde — kein Fehler.
    if not gefunden:
        raise QuizError(
            "Auf dem Foto war keine Antwort lesbar. Blatt flach hinlegen, von "
            "oben fotografieren, keine Schatten — dann erneut versuchen.")
    if uebernommen:
        jobs.enqueue("quiz_check", {"quiz_id": quiz_id},
                     dedup_key=f"quiz_check:{quiz_id}")


# --------------------------------------------------------------------------
# Freigabe → answer_log
# --------------------------------------------------------------------------

def freigeben(quiz_id: int, entscheidungen: list[dict]) -> dict:
    """Schreibt die freigegebenen Bewertungen. Append-only.

    Regeln, die hier durchgesetzt werden:
      * Nur Fragen, die zu DIESER Fragerunde gehören.
      * Jede Frage braucht eine Entscheidung — ein leeres Formular schließt
        keine Fragerunde ab.
      * Eine bereits bewertete Frage wird nicht doppelt gezählt.
      * Die Freigabe selbst ist atomar: zwei nahezu gleichzeitige Aufrufe
        duerfen `answer_log` nicht doppelt schreiben und duerfen die
        Folgeschritte (Lernstand, Export, naechster Workflow-Schritt) nicht
        zweimal auslösen. Das erledigt die bedingte UPDATE unten — sie
        gewinnt genau einmal, unabhaengig von der fruehen Vorab-Pruefung.
      * Die Nacharbeit (Flagge, Lernrunden-Fortschritt, Export) haengt nicht
        davon ab, dass diese Anfrage zu Ende laeuft: der Job unten wird in
        DERSELBEN Transaktion wie die Freigabe angelegt, also atomar mit
        ihr — stuerzt der Prozess direkt danach ab, bleibt der Job stehen
        und der Hintergrund-Worker holt ihn nach (change.txt P2). Siehe
        services/workflow.py:job_quiz_released().
    """
    quiz = db.q1("SELECT * FROM quiz WHERE id = ?", quiz_id)
    if quiz is None:
        raise QuizError("Fragerunde nicht gefunden.")
    if quiz["finished_at"]:
        return {"geschrieben": 0, "uebersprungen": 0, "bereits": True}

    gueltig = {r["id"] for r in db.q(
        "SELECT id FROM question WHERE quiz_id = ?", quiz_id)}
    if not gueltig:
        raise QuizError("Diese Fragerunde hat keine Fragen.")

    entschieden = {int(e["frage_id"]) for e in entscheidungen
                   if int(e["frage_id"]) in gueltig}
    fehlend = gueltig - entschieden
    if fehlend:
        raise QuizError(
            f"{len(fehlend)} Frage(n) sind noch nicht bewertet. Bitte für jede "
            "„richtig“, „falsch“ oder „überspringen“ wählen.")

    tag = db.today()
    geschrieben = uebersprungen = 0
    with db.tx() as c:
        # Atomare Beanspruchung: gewinnt nur, wer die Zeile von "noch nicht
        # fertig" auf "freigegeben" dreht. BEGIN IMMEDIATE (siehe db.tx())
        # serialisiert das gegen jeden anderen gleichzeitigen Aufruf — die
        # zweite Freigabe sieht hier affected=0 und schreibt nichts mehr.
        beansprucht = c.execute(
            "UPDATE quiz SET state=?, finished_at=? WHERE id=? AND finished_at IS NULL",
            (STATE_FREIGEGEBEN, db.now(), quiz_id)).rowcount == 1
        if not beansprucht:
            return {"geschrieben": 0, "uebersprungen": 0, "bereits": True}

        for e in entscheidungen:
            frage_id = int(e["frage_id"])
            if frage_id not in gueltig:
                continue
            if e.get("skip"):
                uebersprungen += 1
                continue
            if c.execute("SELECT 1 FROM answer_log WHERE question_id=?",
                         (frage_id,)).fetchone():
                continue
            c.execute(
                """INSERT INTO answer_log
                       (question_id, topic_id, beantwortet_am, richtig, fehlertyp,
                        begruendung, konfidenz, quelle, modell_einig,
                        llm_call_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (frage_id, quiz["topic_id"], tag,
                 int(bool(e["richtig"])),
                 e.get("fehlertyp") or None,
                 (e.get("begruendung") or "")[:1000],
                 e.get("konfidenz"),
                 "lernbegleitung" if e.get("geaendert") else "llm",
                 0 if e.get("geaendert") else 1,
                 e.get("llm_call_id"), db.now()))
            geschrieben += 1

        # Persistierter Auftrag fuer die Nacharbeit — siehe Docstring oben.
        # Direktes INSERT statt jobs.enqueue(): das eroeffnet selbst eine
        # Transaktion, was hier verschachtelt waere (db.tx() erlaubt das
        # nicht und soll es auch nicht, siehe dessen eigene Absicherung).
        job_payload = json.dumps(
            {"quiz_id": quiz_id, "topic_id": quiz["topic_id"],
             "lesson_id": quiz["lesson_id"], "anlass": quiz["anlass"]},
            ensure_ascii=False)
        job_id = c.execute(
            """INSERT INTO job (type, payload, state, dedup_key, created_at)
               VALUES ('quiz_released', ?, 'wartend', ?, ?)""",
            (job_payload, f"quiz_released:{quiz_id}", db.now())).lastrowid

    return {"geschrieben": geschrieben, "uebersprungen": uebersprungen,
            "bereits": False, "topic_id": quiz["topic_id"],
            "lesson_id": quiz["lesson_id"], "anlass": quiz["anlass"],
            "job_id": job_id}


# --------------------------------------------------------------------------
# Flagge berechnen
# --------------------------------------------------------------------------

def flagge_neu(topic_id: int) -> str:
    """Berechnet die Flagge neu.

    Antworten sind unveränderlich, eine Korrektur ist eine neue Zeile. Deshalb
    zählt je Frage nur die jeweils jüngste.
    """
    rows = db.q(
        """SELECT a.id, a.beantwortet_am, a.richtig, a.fehlertyp, a.created_at
             FROM answer_log a
             JOIN (SELECT question_id, MAX(id) AS neueste
                     FROM answer_log WHERE topic_id = ?
                    GROUP BY question_id) j ON j.neueste = a.id
            ORDER BY a.beantwortet_am, a.created_at, a.id""",
        topic_id)
    antworten = [Answer(r["beantwortet_am"], bool(r["richtig"]), r["fehlertyp"],
                        r["created_at"] or "", r["id"]) for r in rows]
    res = compute_flag(antworten, Rule.from_config(config.load_safe()))
    with db.tx() as c:
        c.execute(
            """INSERT INTO topic_flag (topic_id, flag, antworten, richtig,
                                       haupt_fehler, letzte_uebung, begruendung,
                                       computed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(topic_id) DO UPDATE SET
                   flag=excluded.flag, antworten=excluded.antworten,
                   richtig=excluded.richtig, haupt_fehler=excluded.haupt_fehler,
                   letzte_uebung=excluded.letzte_uebung,
                   begruendung=excluded.begruendung,
                   computed_at=excluded.computed_at""",
            (topic_id, res.flag, res.antworten, res.richtig, res.haupt_fehler,
             res.letzte_uebung, res.begruendung, db.now()))
    return res.flag


def alle_flaggen_neu() -> int:
    rows = db.q("SELECT id FROM topic WHERE state = 'aktiv'")
    for r in rows:
        flagge_neu(r["id"])
    return len(rows)


# --------------------------------------------------------------------------
# Lesen
# --------------------------------------------------------------------------

def holen(quiz_id: int) -> dict | None:
    quiz = db.q1("SELECT * FROM quiz WHERE id = ?", quiz_id)
    if quiz is None:
        return None
    d = dict(quiz)
    d["thema"] = topics.get(quiz["topic_id"])
    d["fragen"] = [dict(r) for r in db.q(
        """SELECT q.*, (SELECT MAX(id) FROM answer_log a
                          WHERE a.question_id = q.id) AS antwort_id,
                    (SELECT richtig FROM answer_log a WHERE a.question_id=q.id ORDER BY id DESC LIMIT 1) AS bestaetigt_richtig,
                    (SELECT fehlertyp FROM answer_log a WHERE a.question_id=q.id ORDER BY id DESC LIMIT 1) AS bestaetigt_fehler
             FROM question q WHERE q.quiz_id=? ORDER BY q.position""", quiz_id)]
    for f in d["fragen"]:
        f["grund"] = grund_teile(f.get("vorschlag_grund"))
    return d


def offene() -> list[dict]:
    """Fragerunden, die auf jemanden warten."""
    return [dict(r) for r in db.q(
        """SELECT q.*, t.label AS thema_label, t.code AS thema_code,
                  (SELECT COUNT(*) FROM question x WHERE x.quiz_id = q.id) AS n
             FROM quiz q JOIN topic t ON t.id = q.topic_id
            WHERE q.state != ?
            ORDER BY q.id DESC LIMIT 30""", STATE_FREIGEGEBEN)]


def verlauf(topic_id: int, limit: int = 14) -> list[dict]:
    rows = db.q(
        """SELECT beantwortet_am, richtig, fehlertyp, quelle FROM answer_log
            WHERE topic_id=? ORDER BY beantwortet_am DESC, created_at DESC, id DESC
            LIMIT ?""", topic_id, limit)
    return [dict(r) for r in reversed(rows)]


def schwaechen(topic_id: int, limit: int = 8) -> dict:
    """Woran es konkret hakt — und was schon sitzt, damit Karo es nicht
    doppelt erklärt.

    Nur die jeweils jüngste Antwort je Frage zählt (Antworten sind
    unveränderlich, eine Korrektur ist eine neue Zeile — wie in
    `flagge_neu()`). Anders als `haupt_fehler` (ein einzelnes Fehlerbild
    über alle Antworten) liefert das hier die tatsächlichen Fragen samt
    Begründung, damit eine Erklärung gezielt auf die konkreten Lücken
    eingehen kann statt allgemein auf einen Fehlertyp.
    """
    rows = db.q(
        """SELECT a.richtig, a.fehlertyp, a.begruendung, q.frage
             FROM answer_log a
             JOIN question q ON q.id = a.question_id
             JOIN (SELECT question_id, MAX(id) AS neueste
                     FROM answer_log WHERE topic_id = ?
                    GROUP BY question_id) j ON j.neueste = a.id
            ORDER BY a.beantwortet_am DESC, a.created_at DESC, a.id DESC""",
        topic_id)
    falsch: list[dict] = []
    richtig: list[dict] = []
    for r in rows:
        if r["richtig"]:
            if len(richtig) < limit:
                richtig.append({"frage": r["frage"]})
        elif len(falsch) < limit:
            falsch.append({"frage": r["frage"], "fehlertyp": r["fehlertyp"],
                           "begruendung": r["begruendung"] or ""})
    return {"falsch": falsch, "richtig": richtig}


def uebereinstimmung(letzte: int = 100) -> dict:
    rows = db.q(
        """SELECT modell_einig FROM answer_log WHERE modell_einig IS NOT NULL
            ORDER BY id DESC LIMIT ?""", letzte)
    gesamt = len(rows)
    einig = sum(1 for r in rows if r["modell_einig"])
    return {"gesamt": gesamt, "einig": einig,
            "quote": round(einig / gesamt, 3) if gesamt else None}
