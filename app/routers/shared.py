"""Gemeinsame Helfer für alle Router."""

import logging
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from starlette.status import HTTP_303_SEE_OTHER

from .. import config, security
from ..domain import (
    AUSGABE_HINTS,
    AUSGABE_LABELS,
    DOC_STATE_HINTS,
    DOC_STATE_LABELS,
    ERROR_LABELS,
    FLAG_LABELS,
    FLAG_ORDER,
    STUFE_LABELS,
)

log = logging.getLogger("karo")

BASE = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE / "templates"))

try:
    ASSET_VERSION = str(int((BASE / "static" / "karo.css").stat().st_mtime))
except OSError:
    ASSET_VERSION = "0"


def render(request: Request, name: str, status_code: int = 200,
           **ctx) -> HTMLResponse:
    """Rendert ein Template mit Kontext."""
    from .. import db, topics, research
    cfg = config.load_safe()
    token = request.session.get("csrf")
    if not token:
        token = security.new_csrf_token()
        request.session["csrf"] = token
    basis = {
        "request": request,
        "asset_version": ASSET_VERSION,
        "cfg": cfg.public_dict(),
        "csrf": token,
        "csrf_field": security.CSRF_FIELD,
        "flag_labels": FLAG_LABELS,
        "flag_order": FLAG_ORDER,
        "error_labels": ERROR_LABELS,
        "doc_labels": DOC_STATE_LABELS,
        "doc_hints": DOC_STATE_HINTS,
        "ausgabe_labels": AUSGABE_LABELS,
        "ausgabe_hints": AUSGABE_HINTS,
        "stufe_labels": STUFE_LABELS,
        "today": db.today(),
        "path": request.url.path,
        "error": None,
        "offene_vorschlaege": topics.anzahl_vorschlaege(),
        "offene_funde": research.anzahl_vorschlaege(),
    }
    basis.update(ctx)
    return templates.TemplateResponse(request, name, basis,
                                      status_code=status_code)


def flash(request: Request, text: str, art: str = "ok") -> None:
    """Setzt eine Meldung für die nächste Seite."""
    request.session["flash"] = text
    request.session["flash_kind"] = art


def zurueck(ziel: str) -> RedirectResponse:
    """Redirect mit HTTP 303 See Other."""
    return RedirectResponse(ziel, status_code=HTTP_303_SEE_OTHER)
