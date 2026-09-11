"""Kind-Routen: Quizze, Lerneinheiten, Material."""

import logging
from pathlib import Path
from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, FileResponse
from starlette.concurrency import run_in_threadpool

from .. import config, db, ingest, jobs, kb, quizzes, research, teaching
from ..quizzes import QuizError
from ..teaching import TeachingError
from .shared import render, flash, zurueck

log = logging.getLogger("karo.kind")
router = APIRouter()


@router.post("/themen/{topic_id}/pruefen")
def quiz_starten(request: Request, topic_id: int, modus: str = Form("bildschirm")):
    try:
        quiz_id = quizzes.anfordern(topic_id, anlass="evaluation", modus=modus)
    except QuizError as exc:
        flash(request, str(exc), "err")
        return zurueck("/themen")
    flash(request, "Die Fragen werden erstellt.")
    return zurueck(f"/quiz/{quiz_id}")


def _quiz_signatur(quiz_id: int) -> str:
    """Fingerabdruck für /quiz/{id}/status — analog zu _lernen_signatur."""
    quiz = db.q1("SELECT state FROM quiz WHERE id=?", quiz_id)
    if quiz is None:
        return "weg"
    offen = jobs.counts()
    return "|".join([
        quiz["state"],
        str(offen.get("wartend", 0) + offen.get("laeuft", 0)),
    ])


@router.get("/quiz/{quiz_id}", response_class=HTMLResponse)
def quiz_seite(request: Request, quiz_id: int):
    quiz = quizzes.holen(quiz_id)
    if quiz is None:
        flash(request, "Fragerunde nicht gefunden.", "err")
        return zurueck("/")
    return render(request, "quiz.html", quiz=quiz, counts=jobs.counts(),
                  signatur=_quiz_signatur(quiz_id))


@router.get("/quiz/{quiz_id}/status")
def quiz_status(quiz_id: int):
    return {"signatur": _quiz_signatur(quiz_id)}


@router.post("/quiz/{quiz_id}/antworten")
async def quiz_antworten(request: Request, quiz_id: int):
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


@router.post("/quiz/{quiz_id}/blatt")
async def quiz_blatt(request: Request, quiz_id: int,
                     datei: UploadFile | None = None):
    formular = await request.form()
    datei = datei or formular.get("datei")
    if datei is None or not getattr(datei, "filename", ""):
        flash(request, "Es wurde keine Datei ausgewählt.", "err")
        return zurueck(f"/quiz/{quiz_id}")

    endung = Path(datei.filename).suffix.lower()
    puffer = bytearray()
    while stueck := await datei.read(1 << 20):
        puffer.extend(stueck)
        if len(puffer) > 25 * 1024 * 1024:
            flash(request, f"Die Datei ist zu groß.", "err")
            return zurueck(f"/quiz/{quiz_id}")

    try:
        await run_in_threadpool(quizzes.blatt_hochladen, quiz_id, bytes(puffer), endung)
    except (QuizError, ingest.IngestError) as exc:
        flash(request, str(exc), "err")
        return zurueck(f"/quiz/{quiz_id}")

    flash(request, "Antwortblatt aufgenommen. Karo liest es jetzt ab.")
    return zurueck(f"/quiz/{quiz_id}")


@router.get("/quiz/{quiz_id}/drucken", response_class=HTMLResponse)
def quiz_drucken(quiz_id: int, loesungen: str = ""):
    from ..media import sheets
    quiz = quizzes.holen(quiz_id)
    if quiz is None:
        return HTMLResponse("<p>Nicht gefunden.</p>", status_code=404)
    titel = (quiz["thema"] or {}).get("label", "Übung")
    if loesungen == "ja":
        return HTMLResponse(sheets.loesungsblatt(titel, quiz["fragen"]))
    return HTMLResponse(sheets.aufgabenblatt(titel, quiz["fragen"]))


@router.post("/quiz/{quiz_id}/freigabe")
async def quiz_freigabe(request: Request, quiz_id: int):
    formular = await request.form()
    frage_ids = [int(v) for v in formular.getlist("frage_id")
                 if str(v).isdigit()]
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

    await run_in_threadpool(__import__("app.export", fromlist=["nach_freigabe"]).nach_freigabe)

    n = ergebnis["geschrieben"]
    meldung = f"{n} Antwort bewertet" if n == 1 else f"{n} Antworten bewertet"
    if ergebnis["uebersprungen"]:
        meldung += f", {ergebnis['uebersprungen']} übersprungen"

    if ergebnis.get("lesson_id") and ergebnis.get("anlass") == "lernrunde":
        weiter = teaching.nach_freigabe(ergebnis["lesson_id"],
                                        ergebnis["topic_id"],
                                        auto_weiter=False)
        flash(request, f"{meldung}. {weiter['grund']}",
              "ok" if weiter.get("erfolg") or weiter.get("weiter") else "warn")
        return zurueck(f"/lernen/{ergebnis['lesson_id']}")

    from .. import topics
    from ..domain import Flag, FLAG_LABELS
    thema = topics.get(ergebnis["topic_id"])
    flagge = (thema or {}).get("flag")
    if flagge in (Flag.ROT.value, Flag.GELB.value):
        flash(request, f"{meldung}. Flagge: {FLAG_LABELS.get(flagge)} — "
                       "eine Lerneinheit wäre jetzt sinnvoll.", "warn")
    else:
        flash(request, f"{meldung}. Flagge: {FLAG_LABELS.get(flagge, '–')}.")
    return zurueck("/themen")


@router.post("/themen/{topic_id}/lernen")
def lernen_starten(request: Request, topic_id: int, ausgabe: str = Form("html")):
    try:
        lesson_id = teaching.starten(topic_id, ausgabe)
    except TeachingError as exc:
        flash(request, str(exc), "err")
        return zurueck("/themen")
    flash(request, "Bevor Karo schreibt: soll auch im Netz nach bekannten "
                   "Lernquellen gesucht werden?")
    return zurueck(f"/lernen/{lesson_id}")


def _lernen_signatur(lesson_id: int) -> str:
    """Kurzer Fingerabdruck aus allem, was die Lerneinheit-Seite anders
    rendern würde — für das automatische Neuladen unter /lernen/{id}/status,
    ohne bei jeder Prüfung die ganze Seite neu zu bauen."""
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


@router.get("/lernen/{lesson_id}", response_class=HTMLResponse)
def lernen_seite(request: Request, lesson_id: int):
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


@router.get("/lernen/{lesson_id}/status")
def lernen_status(lesson_id: int):
    return {"signatur": _lernen_signatur(lesson_id)}


@router.post("/lernen/{lesson_id}/fragen")
def lernen_fragen(request: Request, lesson_id: int,
                  modus: str = Form("bildschirm")):
    try:
        quiz_id = teaching.fragen_anfordern(lesson_id, modus)
    except (TeachingError, QuizError) as exc:
        flash(request, str(exc), "err")
        return zurueck(f"/lernen/{lesson_id}")
    flash(request, "Die Verständnisfragen werden erstellt.")
    return zurueck(f"/quiz/{quiz_id}")


@router.post("/lernen/{lesson_id}/abbrechen")
def lernen_abbrechen(request: Request, lesson_id: int,
                     prompt_wunsch: str = Form("mehr zum Thema")):
    alte = teaching.holen(lesson_id)
    if alte is None:
        flash(request, "Lerneinheit nicht gefunden.", "err")
        return zurueck("/themen")
    teaching.abbrechen(lesson_id, "Neue Erklärung angefordert")
    try:
        # Bewusst KEIN alte["ausgabe"]: das wuerde das Format der allerersten
        # Runde fuer immer festschreiben. starten() ohne eigene Angabe greift
        # auf die aktuellen Einstellungen zurueck — "Mehr zum Thema" benutzt
        # also immer das, was gerade unter Einstellungen gewaehlt ist.
        neue_id = teaching.starten(alte["topic_id"], None, prompt_wunsch)
    except TeachingError as exc:
        flash(request, str(exc), "err")
        return zurueck("/themen")
    flash(request, "Neue Erklärung wird vorbereitet. Die bisherigen Inhalte "
           "und Videos bleiben erhalten.")
    return zurueck(f"/lernen/{neue_id}")


@router.post("/lernen/{lesson_id}/runde/weiter")
def lernen_naechste_runde(request: Request, lesson_id: int):
    try:
        teaching.naechste_runde_bestaetigen(lesson_id)
    except TeachingError as exc:
        flash(request, str(exc), "err")
    return zurueck(f"/lernen/{lesson_id}")


@router.post("/lernen/{lesson_id}/forschen")
def lernen_forschen(request: Request, lesson_id: int):
    try:
        ok = teaching.forschung_anfordern(lesson_id)
    except TeachingError as exc:
        flash(request, str(exc), "err")
        return zurueck(f"/lernen/{lesson_id}")
    if ok:
        flash(request, "Karo sucht auf den zugelassenen Seiten. Diese Seite "
                       "in ein bis zwei Minuten neu laden.")
    else:
        flash(request, "Die Recherche ist ausgeschaltet oder läuft schon "
                       "für heute.", "warn")
    return zurueck(f"/lernen/{lesson_id}")


@router.post("/lernen/{lesson_id}/ausgabe/erneut")
def lernen_ausgabe_erneut(request: Request, lesson_id: int,
                          ausgabe: str = Form("")):
    try:
        teaching.ausgabe_erneut(lesson_id, ausgabe or None)
    except TeachingError as exc:
        flash(request, str(exc), "err")
    else:
        flash(request, "Die Ausgabe wird erneut vorbereitet.")
    return zurueck(f"/lernen/{lesson_id}")


@router.post("/lernen/{lesson_id}/runde/{round_id}/variante")
def lernen_variante(request: Request, lesson_id: int, round_id: int,
                    wunsch: str = Form(""), ausgabe: str = Form("")):
    try:
        teaching.variante_anfordern(round_id, wunsch, ausgabe or None)
    except TeachingError as exc:
        flash(request, str(exc), "err")
    else:
        flash(request, "Karo erzeugt eine weitere Version — das dauert etwas.")
    return zurueck(f"/lernen/{lesson_id}")


def _material_antwort(pfad_text: str | None):
    if not pfad_text:
        return HTMLResponse("<p>Noch kein Material vorhanden.</p>",
                            status_code=404)
    pfad = Path(pfad_text)
    if not pfad.is_file():
        return HTMLResponse("<p>Die Datei ist nicht mehr da.</p>",
                            status_code=404)
    if pfad.suffix.lower() == ".mp4":
        return FileResponse(pfad, media_type="video/mp4", filename=pfad.name)
    if pfad.suffix.lower() == ".txt":
        return PlainTextResponse(pfad.read_text(encoding="utf-8"))
    return HTMLResponse(pfad.read_text(encoding="utf-8"))


@router.get("/material/{round_id}", response_class=HTMLResponse)
def material(round_id: int):
    runde = db.q1("SELECT material_pfad FROM lesson_round WHERE id = ?", round_id)
    return _material_antwort(runde["material_pfad"] if runde else None)


@router.get("/material/{round_id}/notebooklm-quelle", response_class=PlainTextResponse)
def material_notebooklm_quelle(round_id: int):
    runde = db.q1(
        "SELECT notebooklm_quelle_pfad FROM lesson_round WHERE id = ?", round_id)
    return _material_antwort(runde["notebooklm_quelle_pfad"] if runde else None)


@router.get("/material/variante/{variant_id}", response_class=HTMLResponse)
def material_variante(variant_id: int):
    v = db.q1("SELECT material_pfad FROM lesson_round_variant WHERE id = ?",
             variant_id)
    return _material_antwort(v["material_pfad"] if v else None)


@router.get("/material/variante/{variant_id}/notebooklm-quelle",
         response_class=PlainTextResponse)
def material_variante_notebooklm_quelle(variant_id: int):
    v = db.q1(
        "SELECT notebooklm_quelle_pfad FROM lesson_round_variant WHERE id = ?",
        variant_id)
    return _material_antwort(v["notebooklm_quelle_pfad"] if v else None)
