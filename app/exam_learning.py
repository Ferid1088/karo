"""Lernmaterial einer konkreten Lernplanzeile und dessen Lernkontrolle."""
import json
import threading

from . import db, quizzes, teaching

_start_lock = threading.RLock()


def punktestand(quiz_id: int | None) -> dict | None:
    if quiz_id is None:
        return None
    quiz = db.q1("SELECT * FROM quiz WHERE id=? AND finished_at IS NOT NULL", quiz_id)
    if not quiz:
        return None
    row = db.q1("""SELECT COUNT(q.id) AS gesamt, COUNT(a.id) AS bewertet,
                    COALESCE(SUM(a.richtig), 0) AS richtig
                    FROM question q LEFT JOIN answer_log a ON a.question_id=q.id
                    WHERE q.quiz_id=?""", quiz_id)
    return {**dict(row), "quiz_id": quiz_id, "datum": quiz["finished_at"][:10]}


def starten(exam_id: int, row_key: str, ausgabe: str) -> int:
    from . import exam_plan
    plan = exam_plan.holen_plan(exam_id)
    tag = next((t for t in (plan or {}).get("tagesplan_liste", [])
                if t["row_key"] == row_key), None)
    if not plan or plan["state"] != "bereit" or not tag or not tag["topic_id"]:
        raise teaching.TeachingError("Diese Lernplanzeile ist nicht mehr verfügbar. Bitte den Lernplan neu laden.")
    with _start_lock:
        for m in fuer_zeile(exam_id, row_key):
            if m["ausgabe"] == ausgabe and m["state"] in ("offen", "wartet"):
                return m["id"]
        vorher = db.q1("""SELECT id FROM quiz WHERE topic_id=? AND finished_at IS NOT NULL
                           ORDER BY finished_at DESC, id DESC LIMIT 1""", tag["topic_id"])
        lesson_id = teaching.starten(tag["topic_id"], ausgabe,
                                     prompt_wunsch=tag["inhalt"], neue_einheit=True)
        with db.tx() as c:
            cur = c.execute("""INSERT INTO exam_material (exam_id, row_key, lesson_id, vorher, created_at)
                               VALUES (?, ?, ?, ?, ?)""",
                            (exam_id, row_key, lesson_id,
                             json.dumps(punktestand(vorher["id"]) if vorher else None), db.now()))
            material_id = cur.lastrowid
        try:
            teaching.naechste_runde_bestaetigen(lesson_id)
        except teaching.TeachingError:
            # Der Materialtab zeigt den konkreten Quellen-/Ausgabefehler und
            # führt zur bestehenden Quellenverwaltung dieser Einheit.
            pass
        return material_id


def status(material_id: int) -> dict | None:
    row = db.q1("""SELECT em.*, l.ausgabe, t.label FROM exam_material em
                    JOIN lesson l ON l.id=em.lesson_id JOIN topic t ON t.id=l.topic_id
                    WHERE em.id=?""", material_id)
    if row is None:
        return None
    lesson = teaching.holen(row["lesson_id"])
    # Der Link bleibt am ersten fertigen Material, auch bei späteren Runden.
    runde = next((r for r in reversed(lesson["runden_liste"]) if r["material_pfad"]), None)
    if runde is None:
        runde = lesson["aktuelle"]
    state, meldung = "offen", "Lernmaterial wird erstellt und geprüft …"
    if runde and runde["material_pfad"]:
        state, meldung = "bereit", "Lernmaterial öffnen ↗"
    elif runde and (runde["state"] == "fehler" or runde["job_fehler"]):
        state, meldung = "fehler", "Erstellung fehlgeschlagen – Details öffnen ↗"
    elif lesson["state"] == "abgebrochen":
        state, meldung = "fehler", "Erstellung abgebrochen – Details öffnen ↗"
    elif lesson["state"] == "wartet":
        state, meldung = "wartet", "Zuerst eine Lernquelle ergänzen ↗"
    name = ((runde or {}).get("erklaerung") or {}).get("titel") or row["label"]
    if row["label"].casefold() not in name.casefold():
        name = f"{row['label']} – {name}"
    name = f"{name} · {row['created_at'][:10]} · Material {material_id}"
    mime = "video/mp4" if runde and (runde["material_pfad"] or "").lower().endswith(".mp4") else "text/html"
    result = {"id": material_id, "lesson_id": row["lesson_id"], "state": state,
            "meldung": meldung, "titel": name, "ausgabe": row["ausgabe"],
            "url": f"/klassenarbeit/material/{material_id}",
            "round_id": runde["id"] if runde else None, "mime": mime,
            "quiz": runde["quiz"] if runde else None,
            "vorher": json.loads(row["vorher"]),
            "fehler": ((runde or {}).get("pruefung") or {}).get("ausgabe_hinweis")
                       or (runde or {}).get("job_fehler") or lesson["abbruch_grund"]}
    result["ergebnis"] = auswertung(result)["text"] if result["quiz"] and result["quiz"]["finished_at"] else ""
    return result


def fuer_zeile(exam_id: int, row_key: str) -> list[dict]:
    return [status(r["id"]) for r in db.q(
        "SELECT id FROM exam_material WHERE exam_id=? AND row_key=? ORDER BY id DESC",
        exam_id, row_key)]


def auswertung(material: dict) -> dict:
    vorher = material["vorher"]
    quiz = material["quiz"]
    nachher = punktestand(quiz["id"]) if quiz else None
    text = "Nach dem Material beantwortest du neue Kontrollfragen. Die Bewertung wird anschließend bestätigt."
    differenz = None
    if nachher:
        if not nachher["bewertet"] or nachher["bewertet"] != nachher["gesamt"]:
            text = "Die Lernkontrolle wurde nicht vollständig bewertet. Ein Lernzuwachs lässt sich noch nicht beurteilen."
        elif not vorher or not vorher["gesamt"] or vorher["bewertet"] != vorher["gesamt"]:
            text = "Dein Verständnis wurde geprüft. Ohne vollständig bewertete Fragen vor dem Material ist der Lernzuwachs nicht bestimmbar."
        else:
            differenz = round(100 * (nachher["richtig"] / nachher["gesamt"]
                                    - vorher["richtig"] / vorher["gesamt"]))
            if differenz > 0:
                text = "Mehr richtige Antworten: Die Lernkontrolle deutet auf einen Lernzuwachs hin."
            elif differenz == 0:
                text = "Gleicher Anteil richtiger Antworten: Bisher ist kein zusätzlicher Lernzuwachs erkennbar."
            else:
                text = "Weniger richtige Antworten: Ein Lernzuwachs ist bisher nicht nachgewiesen. Übe die unsicheren Stellen noch einmal."
    return {"vorher": vorher, "nachher": nachher, "text": text, "differenz": differenz}


def fragen_anfordern(material_id: int) -> int:
    with _start_lock:
        m = status(material_id)
        if not m or m["state"] != "bereit":
            raise teaching.TeachingError("Das Lernmaterial ist noch nicht fertig.")
        if m["quiz"]:
            return m["quiz"]["id"]
        r = db.q1("SELECT * FROM lesson_round WHERE id=?", m["round_id"])
        lesson = db.q1("SELECT topic_id FROM lesson WHERE id=?", m["lesson_id"])
        quiz_id = quizzes.anfordern(lesson["topic_id"], anlass="lernrunde", lesson_id=m["lesson_id"],
                                    round_nr=r["nr"], anzahl=5)
        with db.tx() as c:
            c.execute("UPDATE lesson_round SET state='gelernt' WHERE id=?", (r["id"],))
        return quiz_id
