"""Admin-Routen: Klassenarbeit, Protokoll.

Reine HTTP-Schicht: Formulardaten entgegennehmen, den passenden Service
aufrufen, Fehler in Flash-Meldungen uebersetzen, Redirect/Response
zurueckgeben. Die eigentliche Klassenarbeits-Logik lebt in
`services/exam.py`, die Uebersicht in `services/measurement.py`
(change.txt Abschnitt 2).

`/protokoll` bleibt hier: eine reine, folgenlose Lese-Anzeige ohne
Geschaeftsentscheidung, fuer die ein eigener Service keinen Mehrwert
haette (change.txt Abschnitt 3: "Do not move trivial presentation-only
reads if doing so adds complexity for no benefit").
"""

import datetime as dt
import logging
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from .. import config, db, quizzes, teaching, topics
from ..services import exam, exam_calendar, learning_progress, measurement
from ..services.exam import ExamError
from .shared import alter_generator_aus, render, flash, zurueck

log = logging.getLogger("karo.admin")
router = APIRouter()


@router.get("/klassenarbeit", response_class=HTMLResponse)
def klassenarbeit(request: Request, monat: str = ""):
    return measurement.render_klassenarbeit(request, monat)


@router.post("/klassenarbeit")
def klassenarbeit_neu(request: Request, exam_date: str = Form(...),
                      scan_id: str = Form(""), themen: str = Form(""), fach: str = Form("")):
    try:
        ergebnis = exam.create_exam(exam_date, scan_id, themen, fach)
    except ExamError as exc:
        flash(request, str(exc), "warn")
        return measurement.render_klassenarbeit_neu(request, draft={
            "exam_date": exam_date, "themen": themen, "fach": fach, "scan_id": scan_id})
    # Ohne geprüfte Aufgaben kann Karo weder einstufen noch üben. Der Auftrag
    # dafür entsteht schon hier: wer die Themen gleich beim Anlegen eintraegt,
    # wartete sonst bis zum ersten Oeffnen der Einstufung auf etwas, das nie
    # angefordert wurde.
    from ..services import exam_effort
    offen = exam_effort.inhalte_anfordern(ergebnis.exam_id)
    if offen:
        flash(request, f"Deine Klassenarbeit ist angelegt. Karo sucht gerade passende "
                       f"Aufgaben für {offen} Themen — das läuft im Hintergrund weiter. "
                       "Wähle solange deine Lerntage.")
    else:
        flash(request, "Deine Klassenarbeit ist angelegt. Wähle jetzt deine Lerntage.")
    return zurueck(f"/klassenarbeit/{ergebnis.exam_id}#exam-next-step")


# Hier standen „/klassenarbeit/themenblatt" und sein Status: ein Foto des
# Ankündigungsblatts ging an ein Modell, das Themen und Termin ablas.
# Bestätigen musste ein Mensch sie ohnehin immer — jetzt tippt er sie gleich
# ein. Siehe app/ai/base.py; das Lesen kommt zurück, sobald es auf dem Gerät
# läuft (docs/Karo_Prompts_Schritt_fuer_Schritt.MD, Schritt 2).


@router.post("/klassenarbeit/{exam_id}/kalender")
async def klassenarbeit_kalender(request: Request, exam_id: int):
    formular = await request.form()
    minuten = {
        key.removeprefix("minutes_"): value
        for key, value in formular.multi_items()
        if key.startswith("minutes_")
    }
    try:
        exam_calendar.save_days(exam_id, minuten)
        exam_calendar.set_simulation_early(
            exam_id, formular.get("simulation_early") == "ja")
    except exam_calendar.ExamCalendarError as exc:
        flash(request, str(exc), "warn")
        return zurueck(f"/klassenarbeit/{exam_id}#exam-calendar-title")
    # Reicht die gewaehlte Zeit nicht, sagt Karo es — aendert aber nichts.
    # Ein Plan, den ein Kind nicht selbst gewaehlt hat, wird nicht gehalten.
    from ..services import exam_effort
    lage = exam_effort.lage(exam_id)
    if lage["themen"] and not lage["reicht"]:
        flash(request,
              f"Gespeichert. Achtung: {lage['gewaehlt']} Minuten sind für deine "
              f"{lage['offen']} offenen Themen knapp — Karo rechnet mit mindestens "
              f"{lage['min']}. Es fehlen {lage['fehlend']} Minuten. Du kannst so "
              "planen; dann beginnt Karo mit dem Wichtigsten.", "warn")
    else:
        flash(request, "Dein Plan ist gespeichert. Karo verteilt deine Themen auf deine Lerntage.")
    return zurueck(f"/klassenarbeit/{exam_id}#exam-next-step")


@router.post("/klassenarbeit/{exam_id}/themen")
def klassenarbeit_themen(request: Request, exam_id: int, themen: str = Form("")):
    from ..services import learning_hub
    import json
    row = db.q1("SELECT * FROM exam WHERE id=? AND deleted_at IS NULL AND purged_at IS NULL", exam_id)
    if not row:
        raise HTTPException(404, "Klassenarbeit nicht gefunden.")
    names = list(dict.fromkeys(n.strip() for n in themen.replace(',', '\n').splitlines() if n.strip()))
    if not names or len(names) > 20 or any(len(n) > 200 for n in names):
        flash(request, "Trage 1 bis 20 Prüfungsthemen ein, jeweils in einer eigenen Zeile.", "warn")
    else:
        learning_hub.link_exam(exam_id, names, row['subject'])
        all_names = [t['label'] for t in learning_hub.exam_topics(exam_id)]
        with db.tx() as c:
            c.execute("UPDATE exam SET themen=? WHERE id=?", (json.dumps(all_names, ensure_ascii=False), exam_id))
        # Ohne geprüfte Aufgaben kann Karo weder einstufen noch üben. Der
        # Auftrag dafür entsteht hier — vorher entstand gar keiner.
        from ..services import exam_effort
        offen = exam_effort.inhalte_anfordern(exam_id)
        if offen:
            flash(request, f"Deine Prüfungsthemen sind gespeichert. Karo bereitet gerade "
                           f"Aufgaben und Erklärungen für {offen} Themen vor — das dauert "
                           "einen Moment. Wähle solange deine Lerntage.")
        else:
            flash(request, "Deine Prüfungsthemen sind gespeichert. Wähle jetzt deine Lerntage.")
    return zurueck(f"/klassenarbeit/{exam_id}#exam-calendar-title")


@router.get("/klassenarbeit/{exam_id}/einstufung", response_class=HTMLResponse)
def klassenarbeit_einstufung(request: Request, exam_id: int):
    """Ein Thema nach dem anderen einstufen — die Grundlage jeder Schätzung."""
    from ..services import exam_effort, exam_placement, measurement
    # Die Seite stösst selbst an, was ihr fehlt. Vorher entstanden Auftraege
    # nur beim Speichern der Themen — wer sie frueher eingetragen hatte,
    # wartete hier ewig auf etwas, das nie angefordert wurde.
    exam_effort.inhalte_anfordern(exam_id)
    naechstes = exam_placement.naechstes_thema(exam_id)
    offen = None
    if naechstes:
        offen = exam_placement.oeffnen(exam_id, naechstes["topic"]["id"])
    return measurement.render_einstufung(request, exam_id, naechstes, offen)


@router.post("/klassenarbeit/{exam_id}/einstufung/{topic_id}")
async def klassenarbeit_einstufung_abgeben(request: Request, exam_id: int, topic_id: int):
    from ..services import exam_placement
    formular = await request.form()
    antworten = {key.removeprefix("antwort_"): wert
                 for key, wert in formular.multi_items()
                 if key.startswith("antwort_")}
    try:
        exam_placement.abgeben(exam_id, topic_id, antworten)
    except ValueError as exc:
        flash(request, str(exc), "warn")
    return zurueck(f"/klassenarbeit/{exam_id}/einstufung")


@router.get("/klassenarbeit/{exam_id}/simulation", response_class=HTMLResponse)
def klassenarbeit_simulation(request: Request, exam_id: int):
    from ..services import exam_rehearsal
    if not exam_calendar.simulation_available(exam_id):
        raise HTTPException(403, "Die Prüfungssimulation ist erst am geplanten Simulationstag verfügbar.")
    return render(
        request, "exam_simulation.html",
        exam_id=exam_id,
        themen=exam_rehearsal.overview(exam_id),
        learning_ui=True, show_nav=False, adult_page=False,
    )


@router.post("/klassenarbeit/{exam_id}/simulation/{topic_id}")
def klassenarbeit_simulation_starten(request: Request, exam_id: int, topic_id: int):
    if not exam_calendar.simulation_available(exam_id):
        raise HTTPException(403, "Die Prüfungssimulation ist heute nicht verfügbar.")
    erlaubt = {t["id"] for t in exam_calendar.simulation_topics(exam_id)}
    if topic_id not in erlaubt:
        raise HTTPException(404, "Dieses Thema gehört nicht zu dieser Klassenarbeit.")
    from ..services import exam_rehearsal
    try:
        exam_rehearsal.start(exam_id, topic_id)
    except LookupError:
        from ..adaptiv import erzeugung
        topic = topics.get(topic_id)
        if config.load_safe().llm_error_creation_enabled:
            erzeugung.anfordern(topic['label'], fach=topic['subject'], klasse=topic.get('grade'))
            flash(request, "Karo bereitet die geprüften Aufgaben vor. Öffne dieses Thema gleich noch einmal.")
        else:
            flash(request, "Für dieses Thema fehlt noch die geprüfte Lernreihe. Bitte deine Eltern um Hilfe.", "warn")
        return zurueck(f"/klassenarbeit/{exam_id}/simulation")
    except ValueError as exc:
        flash(request, str(exc), "warn")
        return zurueck(f"/klassenarbeit/{exam_id}/simulation")
    return zurueck(f"/klassenarbeit/{exam_id}/simulation/{topic_id}")


@router.get("/klassenarbeit/{exam_id}/simulation/{topic_id}")
def klassenarbeit_simulation_aufgaben(request: Request, exam_id: int, topic_id: int):
    from ..services import exam_rehearsal
    try:
        attempt = exam_rehearsal.get(exam_id, topic_id)
    except ValueError as exc:
        raise HTTPException(403, str(exc))
    if not attempt:
        return zurueck(f"/klassenarbeit/{exam_id}/simulation")
    return render(request, "exam_rehearsal.html", exam_id=exam_id, topic=topics.get(topic_id),
                  attempt=attempt, learning_ui=True, show_nav=False, adult_page=False)


@router.post("/klassenarbeit/{exam_id}/simulation/{topic_id}/antworten")
async def klassenarbeit_simulation_antworten(request: Request, exam_id: int, topic_id: int):
    from ..services import exam_rehearsal
    form = await request.form()
    answers = {key.removeprefix('answer_'): value for key, value in form.items()
               if key.startswith('answer_')}
    try:
        exam_rehearsal.submit(exam_id, topic_id, answers)
    except ValueError as exc:
        flash(request, str(exc), "warn")
    return zurueck(f"/klassenarbeit/{exam_id}/simulation/{topic_id}")


@router.post("/klassenarbeit/{exam_id}/plan/neu")
def klassenarbeit_plan_neu(request: Request, exam_id: int):
    flash(request, "Wähle deine Lerntage und Minuten. Daraus entsteht dein Prüfungsplan.")
    return zurueck(f"/klassenarbeit/{exam_id}#exam-calendar-title")


@router.post("/klassenarbeit/{exam_id}/lernen")
def klassenarbeit_lernen(request: Request, exam_id: int, topic_id: int = Form(0)):
    """Startet einen Lerntag ausschließlich im Klassenarbeitsbereich."""
    return RedirectResponse(f"/klassenarbeit/{exam_id}/lernen/start", status_code=307)


@router.post("/klassenarbeit/{exam_id}/lerntag")
def klassenarbeit_lerntag(request: Request, exam_id: int,
                          row_key: str = Form(...), ausgabe: str = Form("")):
    flash(request, "Deine Vorbereitung geht jetzt direkt in deinem Prüfungsplan weiter.")
    return zurueck(f"/klassenarbeit/{exam_id}#exam-next-step")


def _exam_material(material_id: int):
    material = exam.get_exam_material(material_id)
    if material is None or not db.q1('''SELECT id FROM exam WHERE id=?
            AND deleted_at IS NULL AND purged_at IS NULL''', material['exam_id']):
        raise HTTPException(404, "Lernmaterial nicht gefunden.")
    return material


@router.get("/klassenarbeit/material/{material_id}", response_class=HTMLResponse)
def klassenarbeit_material(request: Request, material_id: int):
    material = _exam_material(material_id)
    return render(request, "klassenarbeit_material.html", material=material,
                  learning_ui=True, show_nav=False, adult_page=False)


@router.get("/klassenarbeit/material/{material_id}/inhalt")
def klassenarbeit_material_inhalt(material_id: int):
    from ..services import workflow
    material = _exam_material(material_id)
    if material['state'] != 'bereit' or not material['round_id']:
        raise HTTPException(404, 'Dieses Material ist noch nicht verfügbar.')
    return workflow.render_material(material['round_id'])


@router.get("/klassenarbeit/material/{material_id}/status")
def klassenarbeit_material_status(material_id: int):
    material = _exam_material(material_id)
    material["signatur"] = material["state"]
    return material


@router.post("/klassenarbeit/material/{material_id}/fragen")
def klassenarbeit_material_fragen(request: Request, material_id: int):
    material = _exam_material(material_id)
    flash(request, "Deine Aufgaben findest du jetzt direkt in deiner Prüfungsvorbereitung.")
    return zurueck(f"/klassenarbeit/{material['exam_id']}#exam-next-step")


@router.get("/klassenarbeit/{exam_id}/plan/status")
def klassenarbeit_plan_status(exam_id: int):
    return {"signatur": exam.get_exam_plan_status(exam_id)}


@router.post("/klassenarbeit/{exam_id}/ergebnis")
async def klassenarbeit_ergebnis(request: Request, exam_id: int):
    formular = await request.form()
    n = exam.save_exam_results(exam_id, formular)
    flash(request, f"{n} Ergebnis eingetragen." if n == 1
          else f"{n} Ergebnisse eingetragen.")
    return zurueck("/klassenarbeit")


@router.get("/klassenarbeit/kalender", response_class=HTMLResponse)
def klassenarbeit_kalender_seite(request: Request, monat: str = ""):
    return measurement.render_klassenarbeit_kalender(request, monat)


@router.get("/klassenarbeit/neu", response_class=HTMLResponse)
def klassenarbeit_neu_seite(request: Request):
    return measurement.render_klassenarbeit_neu(request)


# Steht bewusst hinter allen festen Pfaden (/klassenarbeit/neu,
# /klassenarbeit/themenblatt, ...): eine Zahl im Pfad faengt sonst nichts
# davon ab.
@router.get("/klassenarbeit/{exam_id}", response_class=HTMLResponse)
def klassenarbeit_detail(request: Request, exam_id: int):
    return measurement.render_klassenarbeit_detail(request, exam_id)


@router.get("/protokoll", response_class=HTMLResponse)
def protokoll(request: Request):
    zeilen = [dict(r) for r in db.q(
        """SELECT id, purpose, backend, model, had_image, schema_ok, error,
                  tokens_in, tokens_out, cost_usd, duration_ms, created_at
             FROM llm_call ORDER BY id DESC LIMIT 120""")]
    gesamt = dict(db.q1(
        "SELECT COUNT(*) AS n, COALESCE(SUM(cost_usd),0) AS c FROM llm_call"))
    monat = dict(db.q1(
        "SELECT COUNT(*) AS n, COALESCE(SUM(cost_usd),0) AS c FROM llm_call "
        "WHERE created_at >= ?", dt.date.today().replace(day=1).isoformat()))
    return render(request, "protokoll.html", zeilen=zeilen, gesamt=gesamt,
                  monat=monat, backend=config.load_safe().ai_provider)


@router.get("/protokoll/{call_id}", response_class=HTMLResponse)
def protokoll_detail(request: Request, call_id: int):
    zeile = db.q1("SELECT * FROM llm_call WHERE id = ?", call_id)
    if zeile is None:
        return HTMLResponse("<p>Nicht gefunden.</p>", status_code=404)
    return render(request, "protokoll_detail.html", zeile=dict(zeile))
