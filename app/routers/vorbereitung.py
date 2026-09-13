"""Vorbereitung — konsolidierter Eltern-Einstieg fuer Schulmaterial, Themen
und Recherche (siehe KaroRefactoring_Plan.md, Abschnitt 5/9).

Ruft bewusst dieselben Funktionen wie /wissen, /themen und /recherche auf
(eltern.py), statt sie zu duplizieren: eine fachliche Entscheidung soll nur
an einer Stelle im Code stehen (Abschnitt 28, "Ein Prozess - eine
Wahrheit"). Die alten Adressen bleiben erreichbar, bis sie in einer
spaeteren Phase abgebaut werden (Abschnitt 17/24, Phase 6).
"""

from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from . import eltern

router = APIRouter(prefix="/vorbereitung", tags=["preparation"])


# --- Schulmaterial (== /wissen) --------------------------------------------

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def schulmaterial_index(request: Request):
    return eltern.wissen(request)


@router.post("/schulmaterial/einlesen")
async def schulmaterial_einlesen(request: Request, quelle: str = Form("drive")):
    return await eltern.wissen_einlesen(request, quelle)


@router.post("/schulmaterial/hochladen")
async def schulmaterial_hochladen(request: Request, rolle: str = Form("wissen"),
                                  datei: UploadFile | None = None):
    return await eltern.wissen_upload(request, rolle, datei)


@router.get("/schulmaterial/{doc_id}", response_class=HTMLResponse)
def schulmaterial_detail(request: Request, doc_id: int):
    return eltern.wissen_detail(request, doc_id)


# --- Inhalte / Themen genehmigen (== /themen) ------------------------------

@router.get("/inhalte", response_class=HTMLResponse)
def inhalte_genehmigen(request: Request):
    return eltern.themen(request)


@router.post("/inhalte/entscheiden")
async def inhalte_entscheiden(request: Request):
    return await eltern.themen_entscheiden(request)


@router.post("/inhalte/neu")
def inhalte_neu(request: Request, label: str = Form(""),
                beschreibung: str = Form("")):
    return eltern.themen_neu(request, label, beschreibung)


# --- Recherche / Quellen (== /recherche) -----------------------------------

@router.get("/inhalte/sources", response_class=HTMLResponse)
def quellen_verwalten(request: Request):
    return eltern.recherche(request)


@router.post("/inhalte/sources/entscheiden")
async def quellen_entscheiden(request: Request):
    return await eltern.recherche_entscheiden(request)
