"""Messung — konsolidierter Eltern-Einstieg fuer Lernfortschritt und
Klassenarbeiten (siehe KaroRefactoring_Plan.md, Abschnitt 7/9).

Ruft dieselben Service-Funktionen wie /lernstand und /klassenarbeit auf
(services/measurement.py) statt eltern.py's/admin.py's Router-Funktionen
direkt anzusprechen (change.txt Aufgabe 2). Die Klassenarbeit-Verwaltung
selbst (Themenblatt-Scan, KI-Lernplan, Lernmaterial: admin.py) bleibt
bewusst nur unter /klassenarbeit — /messung/examen zeigt dieselbe
Uebersicht, hat aber keine eigenen Formulare dafuer.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..services import measurement

router = APIRouter(prefix="/messung", tags=["measurement"])


# --- Fortschritt (== /lernstand) -------------------------------------------

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
@router.get("/fortschritt", response_class=HTMLResponse)
def fortschritt(request: Request):
    return measurement.render_lernstand(request)


@router.post("/export")
async def fortschritt_export(request: Request):
    return await measurement.handle_export(request, "/messung/fortschritt")


# --- Klassenarbeiten (== /klassenarbeit, admin.py) -------------------------

@router.get("/examen", response_class=HTMLResponse)
def examen(request: Request):
    return measurement.render_klassenarbeit(request)
