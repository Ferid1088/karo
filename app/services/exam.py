"""Klassenarbeit: Themenblatt, Lernplan, Lernkontrolle, Ergebnisse.

Verbindet die Domainlogik in `exam_plan.py`/`exam_learning.py` mit der
HTTP-Schicht in `admin.py`. Validierung, mehrstufige DB-Schreibvorgaenge
und Fehlerbehandlung leben hier, nicht im Router (KaroRefactoring_Plan.md
Abschnitt 10; change.txt Abschnitt 2/5). Die Uebersicht/Kalibrierung
(GET /klassenarbeit) bleibt bewusst in `services/measurement.py` — das
ist Anzeige einer bestehenden Klassenarbeit, keine Klassenarbeits-
Verwaltung.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json

from starlette.datastructures import FormData

from .. import config, db, exam_learning, exam_plan, ingest
from ..domain import Flag
from ..topics import AKTIV, liste, passende


class ExamError(Exception):
    """Verständlicher Fehler beim Anlegen oder Pflegen einer Klassenarbeit."""


@dataclasses.dataclass(frozen=True)
class ExamCreated:
    exam_id: int
    themen_eingefroren: int


def create_exam(exam_date: str, scan_id: str) -> ExamCreated:
    """Legt eine Klassenarbeit aus einem eingelesenen Themenblatt an und
    friert die Prognose fuer die dazu passenden Themen ein — nur fuer
    Themen, die zum Themenblatt passen (`topics.passende`), sonst wuerde
    jede Arbeit sich mit ALLEN aktiven Themen im Fach befassen, auch mit
    Themen, die auf dem Blatt gar nicht standen (change.txt Abschnitt 8).
    """
    if not scan_id.isdigit():
        raise ExamError(
            "Bitte zuerst das Themenblatt hochladen und vollständig einlesen lassen.")
    scan = db.q1("SELECT * FROM exam_scan WHERE id = ?", int(scan_id))
    if scan is None or scan["state"] != "gelesen":
        raise ExamError(
            "Das Themenblatt wird noch gelesen oder konnte nicht gelesen werden. "
            "Bitte warten oder ein neues Blatt hochladen.")
    try:
        scan_themen = json.loads(scan["themen"] or "[]")
    except json.JSONDecodeError:
        scan_themen = []
    liste_themen = [str(t).strip()[:120] for t in scan_themen if str(t).strip()][:20]
    if not liste_themen:
        raise ExamError(
            "Im hochgeladenen Themenblatt wurden keine Themen erkannt. "
            "Bitte ein klareres Blatt hochladen.")
    try:
        dt.date.fromisoformat(exam_date)
    except ValueError:
        raise ExamError("Ungültiges Datum.")

    cfg = config.load_safe()
    with db.tx() as c:
        cur = c.execute(
            "INSERT INTO exam (subject, exam_date, themen, created_at) "
            "VALUES (?,?,?,?)",
            (cfg.subject, exam_date, json.dumps(liste_themen, ensure_ascii=False),
             db.now()))
        exam_id = cur.lastrowid
        n = 0
        aktiv = [t for t in liste(AKTIV) if t["flag"] != Flag.WEISS.value]
        for t in passende(liste_themen, aktiv):
            cur2 = c.execute(
                """INSERT INTO prediction (exam_id, topic_id, prognose, frozen_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(exam_id, topic_id) DO NOTHING""",
                (exam_id, t["id"], t["flag"], db.now()))
            n += cur2.rowcount

    # Erst nach dem Commit: beides loest eigene Hintergrund-Jobs aus und
    # braucht die gerade angelegte Klassenarbeit/den Scan bereits sichtbar.
    exam_plan.scan_uebernehmen(int(scan_id))
    exam_plan.plan_anfordern(exam_id)
    return ExamCreated(exam_id=exam_id, themen_eingefroren=n)


def upload_exam_topics_sheet(daten: bytes, endung: str) -> int:
    try:
        return exam_plan.foto_hochladen(daten, endung)
    except ingest.IngestError as exc:
        raise ExamError(str(exc)) from exc


def get_exam_topic_scan_status(scan_id: int) -> str:
    return exam_plan.scan_status(scan_id)


def regenerate_exam_plan(exam_id: int) -> None:
    if db.q1("SELECT id FROM exam WHERE id = ?", exam_id) is None:
        raise ExamError("Klassenarbeit nicht gefunden.")
    exam_plan.plan_anfordern(exam_id)


def get_exam_plan_status(exam_id: int) -> str:
    plan = exam_plan.holen_plan(exam_id)
    return plan["state"] if plan else "weg"


def start_exam_learning_day(exam_id: int, row_key: str, ausgabe: str) -> int:
    ausgabe = ausgabe or config.load_safe().default_ausgabe
    return exam_learning.starten(exam_id, row_key, ausgabe)


def get_exam_material(material_id: int) -> dict | None:
    return exam_learning.status(material_id)


def get_exam_material_evaluation(material: dict) -> dict:
    return exam_learning.auswertung(material)


def request_exam_questions(material_id: int) -> int:
    return exam_learning.fragen_anfordern(material_id)


def save_exam_results(exam_id: int, formular: FormData) -> int:
    """Schreibt die tatsaechlichen Ergebnisse — nur fuer Themen, die
    wirklich zu dieser Klassenarbeit gehoeren (siehe `prediction`), damit
    ein manipuliertes Formularfeld keine fremde Prognose ueberschreibt."""
    erlaubt = {f.value for f in Flag}
    gueltig = {r["topic_id"] for r in db.q(
        "SELECT topic_id FROM prediction WHERE exam_id = ?", exam_id)}
    n = 0
    with db.tx() as c:
        for schluessel in formular.keys():
            if not schluessel.startswith("ist_"):
                continue
            roh = schluessel[4:]
            wert = str(formular.get(schluessel) or "")
            if not roh.isdigit() or wert not in erlaubt:
                continue
            if int(roh) not in gueltig:
                continue
            cur = c.execute(
                "UPDATE prediction SET tatsaechlich=? WHERE exam_id=? AND topic_id=?",
                (wert, exam_id, int(roh)))
            n += cur.rowcount
    return n
