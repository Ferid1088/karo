"""Lernpilot-Routen: HTTP-Schicht über `services/learning_pilot.py`.

Der Zustand lebt in der Session (kein DB-Schema für diesen Prototyp).
Der Browser schickt nur Antworten, nie eine Phase — der Server
entscheidet allein über Übergänge.
"""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from ..services import learning_pilot as pilot
from .shared import render

router = APIRouter(prefix="/lernpilot", tags=["lernpilot"])

SESSION_KEY = "lernpilot"


def _get_state(request: Request) -> dict:
    state = request.session.get(SESSION_KEY)
    if not state:
        state = pilot.initial_state()
        request.session[SESSION_KEY] = state
    return state


def _save(request: Request, state: dict) -> None:
    request.session[SESSION_KEY] = state


def _render(request: Request, state: dict) -> HTMLResponse:
    debug = request.query_params.get("debug") == "1"
    return render(request, "learning_pilot.html",
                  pilot_state=state, debug=debug, hints=pilot.GUIDED_HINTS,
                  help_faq=pilot.HELP_FAQ,
                  explain_more=pilot.EXPLAIN_MORE.get(state["phase"]))


@router.get("", response_class=HTMLResponse)
def start(request: Request):
    return _render(request, _get_state(request))


@router.post("/reset", response_class=HTMLResponse)
def reset(request: Request):
    state = pilot.initial_state()
    _save(request, state)
    return _render(request, state)


@router.post("/anchor", response_class=HTMLResponse)
def anchor(request: Request, antwort: str = Form("")):
    state = pilot.advance_anchor(_get_state(request), antwort)
    _save(request, state)
    return _render(request, state)


@router.post("/diagnostic", response_class=HTMLResponse)
def diagnostic(request: Request, antwort: str = Form("")):
    state = pilot.submit_diagnostic(_get_state(request), antwort)
    _save(request, state)
    return _render(request, state)


@router.post("/diagnostic-reasoning", response_class=HTMLResponse)
def diagnostic_reasoning(request: Request, antwort: str = Form("")):
    state = pilot.submit_diagnostic_reasoning(_get_state(request), antwort)
    _save(request, state)
    return _render(request, state)


@router.post("/conflict", response_class=HTMLResponse)
def conflict(request: Request, antwort: str = Form("")):
    state = pilot.submit_conflict(_get_state(request), antwort)
    _save(request, state)
    return _render(request, state)


@router.post("/prediction", response_class=HTMLResponse)
def prediction(request: Request, antwort: str = Form("")):
    state = pilot.submit_prediction(_get_state(request), antwort)
    _save(request, state)
    return _render(request, state)


@router.post("/visual-discovery", response_class=HTMLResponse)
def visual_discovery(request: Request):
    state = pilot.submit_visual_discovery(_get_state(request))
    _save(request, state)
    return _render(request, state)


@router.post("/discovery", response_class=HTMLResponse)
def discovery(request: Request, antwort: str = Form("")):
    state = pilot.submit_discovery(_get_state(request), antwort)
    _save(request, state)
    return _render(request, state)


@router.post("/rule", response_class=HTMLResponse)
def rule(request: Request):
    state = pilot.submit_rule(_get_state(request))
    _save(request, state)
    return _render(request, state)


@router.post("/worked-example", response_class=HTMLResponse)
def worked_example(request: Request):
    state = pilot.submit_worked_example(_get_state(request))
    _save(request, state)
    return _render(request, state)


@router.post("/guided", response_class=HTMLResponse)
def guided(request: Request, antwort: str = Form("")):
    state = pilot.submit_guided(_get_state(request), antwort)
    _save(request, state)
    return _render(request, state)


@router.post("/guided/hinweis", response_class=HTMLResponse)
def guided_hint(request: Request):
    state = pilot.request_hint(_get_state(request))
    _save(request, state)
    return _render(request, state)


@router.post("/adaptation", response_class=HTMLResponse)
def adaptation(request: Request):
    state = pilot.submit_adaptation(_get_state(request))
    _save(request, state)
    return _render(request, state)


@router.post("/independent", response_class=HTMLResponse)
def independent(request: Request, antwort: str = Form("")):
    state = pilot.submit_independent(_get_state(request), antwort)
    _save(request, state)
    return _render(request, state)


@router.post("/transfer", response_class=HTMLResponse)
def transfer(request: Request, antwort: str = Form(""), begruendung: str = Form("")):
    state = pilot.submit_transfer(_get_state(request), antwort, begruendung)
    _save(request, state)
    return _render(request, state)


@router.post("/final-retrieval", response_class=HTMLResponse)
def final_retrieval(request: Request, antwort: str = Form("")):
    state = pilot.submit_final_retrieval(_get_state(request), antwort)
    _save(request, state)
    return _render(request, state)
