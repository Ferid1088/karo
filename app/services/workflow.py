"""Geteilte Workflow-Schritte fuer Quiz und Lernrunde.

Frueher rief `lernzyklus.py` die Router-Funktionen aus `kind.py` direkt auf
(Router ruft Router) — hier stehen dieselben Schritte einmal, und beide
Router rufen sie auf (siehe KaroRefactoring_Plan.md, Abschnitt 10/14).
"""

from __future__ import annotations

import dataclasses

from fastapi import Request
from starlette.concurrency import run_in_threadpool

from .. import config, db, exam_learning, export, jobs, kb, quizzes, research, teaching, topics
from ..domain import FLAG_ORDER, Flag
from ..quizzes import QuizError
from ..routers.shared import flash, render, zurueck


# --- Quiz-Seite -------------------------------------------------------------

def _quiz_signatur(quiz_id: int) -> str:
    """Fingerabdruck fuer /quiz/{id}/status — analog zu `_lernen_signatur`."""
    quiz = db.q1("SELECT state FROM quiz WHERE id=?", quiz_id)
    if quiz is None:
        return "weg"
    offen = jobs.counts()
    return "|".join([
        quiz["state"],
        str(offen.get("wartend", 0) + offen.get("laeuft", 0)),
    ])


def quiz_status_signatur(quiz_id: int) -> str:
    return _quiz_signatur(quiz_id)


def render_quiz_page(request: Request, quiz_id: int):
    quiz = quizzes.holen(quiz_id)
    if quiz is None:
        flash(request, "Fragerunde nicht gefunden.", "err")
        return zurueck("/")
    return render(request, "quiz.html", quiz=quiz, counts=jobs.counts(),
                  signatur=_quiz_signatur(quiz_id))


async def handle_quiz_antworten(request: Request, quiz_id: int):
    formular = await request.form()
    antworten: dict[int, str] = {}
    for schluessel in formular.keys():
        if not schluessel.startswith("antwort_"):
            continue
        roh = schluessel[8:]
        if roh.isdigit():
            antworten[int(roh)] = str(formular.get(schluessel) or "")
    try:
        n = quizzes.antworten_speichern(quiz_id, antworten)
    except QuizError as exc:
        flash(request, str(exc), "err")
        return zurueck(f"/quiz/{quiz_id}")
    flash(request, f"{n} Antworten aufgenommen. Die Auswertung läuft.")
    return zurueck(f"/quiz/{quiz_id}")


# --- Nach der Quiz-Freigabe: wohin geht es weiter? --------------------------

@dataclasses.dataclass(frozen=True)
class NextAction:
    kind: str          # "exam_material" | "lesson" | "review_cycle"
    url: str
    reason: str
    context: dict = dataclasses.field(default_factory=dict)


def after_quiz_release(ergebnis: dict, quiz_id: int) -> NextAction:
    """Entscheidet, wohin eine Freigabe fuehrt — die groesste Kreuzung der
    App (siehe KaroRefactoring_Plan.md, Abschnitt 13). `ergebnis` kommt
    unveraendert aus `quizzes.freigeben()`."""
    if ergebnis.get("lesson_id") and ergebnis.get("anlass") == "lernrunde":
        weiter = teaching.nach_freigabe(ergebnis["lesson_id"], ergebnis["topic_id"],
                                        auto_weiter=False)
        material = db.q1("SELECT id FROM exam_material WHERE lesson_id=?",
                         ergebnis["lesson_id"])
        if material:
            original = exam_learning.status(material["id"])
            if original["quiz"] and original["quiz"]["id"] == quiz_id:
                return NextAction(
                    kind="exam_material",
                    url=f"/klassenarbeit/material/{material['id']}",
                    reason="Quiz gehörte zu Klassenarbeits-Lernmaterial",
                    context={"weiter": weiter})
        return NextAction(
            kind="lesson", url=f"/lernen/{ergebnis['lesson_id']}",
            reason="Quiz gehörte zu einer laufenden Lernrunde",
            context={"weiter": weiter})

    thema = topics.get(ergebnis["topic_id"])
    return NextAction(
        kind="review_cycle", url=f"/lernzyklus/{ergebnis['topic_id']}",
        reason="Themenprüfung außerhalb einer Lernrunde",
        context={"flagge": (thema or {}).get("flag")})


async def handle_quiz_freigabe(request: Request, quiz_id: int):
    formular = await request.form()
    frage_ids = [int(v) for v in formular.getlist("frage_id") if str(v).isdigit()]
    entscheidungen = []
    for frage_id in frage_ids:
        urteil = formular.get(f"urteil_{frage_id}")
        if urteil is None:
            continue
        vorschlag = formular.get(f"v_urteil_{frage_id}", "")
        fehler = formular.get(f"fehler_{frage_id}") or None
        v_fehler = formular.get(f"v_fehler_{frage_id}") or None
        call_roh = str(formular.get(f"call_{frage_id}") or "")
        entscheidungen.append({
            "frage_id": frage_id,
            "skip": urteil == "skip",
            "richtig": urteil == "ja",
            "fehlertyp": None if urteil == "ja" else fehler,
            "begruendung": formular.get(f"grund_{frage_id}", "")[:1000],
            "konfidenz": None,
            "llm_call_id": int(call_roh) if call_roh.isdigit() else None,
            "geaendert": urteil != vorschlag or fehler != v_fehler,
        })

    try:
        ergebnis = quizzes.freigeben(quiz_id, entscheidungen)
    except QuizError as exc:
        flash(request, str(exc), "err")
        return zurueck(f"/quiz/{quiz_id}")

    if ergebnis["bereits"]:
        flash(request, "Diese Fragerunde war bereits freigegeben.", "warn")
        return zurueck("/themen")

    await run_in_threadpool(export.nach_freigabe)

    n = ergebnis["geschrieben"]
    meldung = f"{n} Antwort bewertet" if n == 1 else f"{n} Antworten bewertet"
    if ergebnis["uebersprungen"]:
        meldung += f", {ergebnis['uebersprungen']} übersprungen"

    aktion = after_quiz_release(ergebnis, quiz_id)
    if aktion.kind == "review_cycle":
        flagge = aktion.context.get("flagge")
        if flagge in (Flag.ROT.value, Flag.GELB.value):
            flash(request, f"{meldung}. Schau dir jetzt eine Erklärung an und übe weiter.", "ok")
        else:
            flash(request, f"{meldung}. Deine Ergebnisse sind gespeichert.")
    else:
        weiter = aktion.context["weiter"]
        flash(request, f"{meldung}. {weiter['grund']}",
              "ok" if weiter.get("erfolg") or weiter.get("weiter") else "warn")
    return zurueck(aktion.url)


# --- Lernen-Seite ------------------------------------------------------------

def _lernen_signatur(lesson_id: int) -> str:
    """Fingerabdruck fuer /lernen/{id}/status — alles, was die Seite anders
    rendern wuerde, ohne bei jeder Pruefung die ganze Seite neu zu bauen."""
    lesson = db.q1("SELECT state FROM lesson WHERE id=?", lesson_id)
    if lesson is None:
        return "weg"
    runde = db.q1(
        """SELECT state, material_pfad FROM lesson_round
            WHERE lesson_id=? ORDER BY nr DESC LIMIT 1""", lesson_id)
    offen = jobs.counts()
    return "|".join([
        lesson["state"],
        runde["state"] if runde else "-",
        "m" if runde and runde["material_pfad"] else "-",
        str(offen.get("wartend", 0) + offen.get("laeuft", 0)),
    ])


def lernen_status_signatur(lesson_id: int) -> str:
    return _lernen_signatur(lesson_id)


# --- „Heute": ein zentraler naechster Schritt ------------------------------
#
# Vorher hatte nur dashboard.py diese Logik, aber schon dreifach genutzt
# (/, /lernen, /eltern) — jetzt lebt sie hier, wie in Abschnitt 15 des Plans
# vorgesehen, und alle Dashboards rufen dieselbe Funktion auf.

def offene_schritte():
    """Alle offenen Lernschritte, dringlichste zuerst — fuer die Uebersichten
    unter /lernen und /eltern sowie als Basis fuer `get_next_action()`."""
    themen = topics.liste(topics.AKTIV)
    themen.sort(key=lambda t: (FLAG_ORDER.index(t['flag']), t['sort']))
    quizze = quizzes.offene()
    lessons = teaching.offene()
    schritte = []
    # Ein Material aus dem Lernplan führt immer zurück zu seinem Materialtab.
    material = {r['lesson_id']: r['id'] for r in db.q('SELECT id, lesson_id FROM exam_material')}
    for q in quizze:
        if q['state'] == 'geprueft':
            continue
        text = {'bereit': 'Deine Fragen sind da', 'offen': 'Deine Fragen werden vorbereitet',
                'beantwortet': 'Deine Antworten werden angeschaut'}.get(q['state'], 'Weiterlernen')
        schritte.append({'titel': q['thema_label'], 'text': text, 'url': f"/quiz/{q['id']}",
                         'topic_id': q['topic_id'], 'bereit': q['state'] == 'bereit'})
    quiz_themen = {q['topic_id'] for q in quizze}
    for l in lessons:
        if l['topic_id'] in quiz_themen:
            continue
        url = f"/klassenarbeit/material/{material[l['id']]}" if l['id'] in material else f"/lernen/{l['id']}"
        schritte.append({'titel': l['thema_label'], 'text': 'Hier geht deine Lernrunde weiter',
                         'url': url, 'topic_id': l['topic_id'], 'bereit': l['state'] == 'bereit'})
    schritte.sort(key=lambda s: not s['bereit'])
    return themen, schritte, [q for q in quizze if q['state'] == 'geprueft']


def get_next_action(themen: list[dict], schritte: list[dict]) -> dict | None:
    """Der eine naechste Schritt fuer die „Heute"-Kachel: ein offener Schritt
    (Quiz vor Lernrunde, siehe `offene_schritte()`) hat Vorrang; sonst ein
    neues, bereits bestaetigtes Thema; sonst gibt es gerade nichts zu tun."""
    if schritte:
        return {**schritte[0], 'button': 'Weiterlernen'}
    if themen:
        return {'titel': themen[0]['label'], 'text': 'Ein kleiner Schritt für heute.',
                'url': f"/lernzyklus/{themen[0]['id']}", 'button': 'Los geht’s'}
    return None


def render_lernen_page(request: Request, lesson_id: int):
    lesson = teaching.holen(lesson_id)
    if lesson is None:
        flash(request, "Lerneinheit nicht gefunden.", "err")
        return zurueck("/themen")
    thema = lesson.get("thema") or {}
    hat_material = bool(
        kb.lehrmaterial(lesson["topic_id"], thema.get("label", ""), limit=1)
        or research.material_fuer(lesson["topic_id"]))
    return render(request, "lernen.html", lesson=lesson, counts=jobs.counts(),
                  funde=research.freigegebene(lesson["topic_id"]),
                  vorschlaege=research.vorschlaege(lesson["topic_id"]),
                  recherche_erlaubt=config.load_safe().recherche_erlaubt,
                  hat_material=hat_material,
                  alle_materialien=teaching.materialien_fuer_thema(lesson["topic_id"]),
                  signatur=_lernen_signatur(lesson_id))
