"""Messung — konsolidierter Eltern-Einstieg fuer Lernfortschritt und
Klassenarbeiten (siehe KaroRefactoring_Plan.md, Abschnitt 7/9).

Fortschritt ruft dieselbe Logik wie /lernstand auf (eltern.py). Klassenar-
beiten laufen ueber admin.py, das inzwischen den KI-Lernplan, Themenblatt-
Scan und die Klassenarbeits-Material-Pipeline mitbringt — das war in einer
eigenstaendigen Kopie hier nicht mehr abgebildet. Statt diese neuere Logik
zu duplizieren (und dadurch zwei auseinanderlaufende Implementierungen
derselben Entscheidung zu riskieren), zeigt /messung/examen dieselbe Seite
wie /klassenarbeit; ihre Formulare fuehren bewusst dorthin weiter.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from starlette.concurrency import run_in_threadpool

from .. import export
from . import admin, eltern
from .shared import flash, zurueck

router = APIRouter(prefix="/messung", tags=["measurement"])


# --- Fortschritt (== /lernstand) -------------------------------------------

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
@router.get("/fortschritt", response_class=HTMLResponse)
def fortschritt(request: Request):
    return eltern.lernstand(request)


@router.post("/export")
async def fortschritt_export(request: Request):
    pfad = await run_in_threadpool(export.nach_freigabe)
    if pfad:
        flash(request, f"Tabelle geschrieben: {__import__('pathlib').Path(pfad).name}")
    else:
        flash(request, "Export nicht verfügbar.", "warn")
    return zurueck("/messung/fortschritt")


# --- Klassenarbeiten (== /klassenarbeit, admin.py) -------------------------

@router.get("/examen", response_class=HTMLResponse)
def examen(request: Request):
    return admin.klassenarbeit(request)
