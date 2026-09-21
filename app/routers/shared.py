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


def alter_generator_aus() -> bool:
    """Ist der alte Erzeugungsweg (`teaching.py` → `media/`) abgeschaltet?

    Er erzeugt pro Kind und Runde einen Foliensatz oder ein Video und
    widerspricht damit §11 und §12. Bis der adaptive Loop ihn ersetzt,
    bleibt der Code liegen — erreichbar ist er nur mit gesetztem Schalter.
    Gleiches Muster wie `adaptive_learning_enabled` (§16).

    Liegt in `shared`, weil zwei Router dieselbe Tür bewachen: `kind.py`
    (`/themen/{id}/lernen`, `/lernen/{id}`, `/material/...`) und
    `lernzyklus.py`.
    """
    return not getattr(config.load_safe(),
                       "legacy_lesson_generation_enabled", False)

BASE = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE / "templates"))

try:
    ASSET_VERSION = str(max(
        (BASE / "static" / name).stat().st_mtime_ns
        for name in ("karo.css", "simple.css", "simple.js", "drafts.js", "setup.js", "storage.js", "areas.css", "themes.js", "begleiter.js")
    ))
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
        "role": request.session.get("role", "parent"),
        "error": None,
        "adult_page": request.url.path.startswith(
            ("/eltern", "/wissen", "/themen", "/recherche", "/setup",
             "/protokoll", "/vorbereitung", "/messung", "/lernstand",
             "/klassenarbeit")),
        "child_flags": {"gruen": "Das kannst du gut", "gelb": "Du wirst sicherer", "rot": "Das üben wir zusammen", "weiss": "Noch nicht ausprobiert"},
        "offene_vorschlaege": topics.anzahl_vorschlaege(),
        "offene_funde": research.anzahl_vorschlaege(),
    }
    basis.update(ctx)
    # The visible area follows the page, including shared pages enabled for children.
    # This only selects presentation; authorization remains in Gate.
    if request.session.get("role") == "child":
        basis["adult_page"] = False
    quiz = ctx.get("quiz") or {}
    if (request.session.get("role") == "parent" and not cfg.antworten_pruefen_kind
            and quiz.get("state") in ("beantwortet", "ausgewertet")):
        basis["adult_page"] = True
    basis["ui_area"] = "parent" if basis["adult_page"] else "child"
    # Der Begleiter (Name/Foto) ersetzt "Karo" nur im Kind-Bereich — der
    # Eltern-Bereich bleibt bewusst bei "Karo" und dem Original-Logo.
    begleiter = None if basis["adult_page"] else _begleiter()
    basis["companion_name"] = begleiter["name"] if begleiter else "Karo"
    basis["companion_photo_url"] = (
        f"/welten/foto/{begleiter['foto_pfad']}"
        if begleiter and begleiter.get("foto_pfad") else None)
    return templates.TemplateResponse(request, name, basis,
                                      status_code=status_code)


def _begleiter():
    from ..welten import store as begleiter_store
    return begleiter_store.current_companion()


def companion_name(request: Request) -> str:
    """Fuer Meldungen (flash), die ausserhalb von render() gebaut werden —
    z.B. direkt vor einem redirect. Nur im Kind-Bereich ersetzt; sonst
    "Karo", wie render() es auch fuer Eltern-Seiten haelt."""
    if request.session.get("role") != "child":
        return "Karo"
    begleiter = _begleiter()
    return begleiter["name"] if begleiter else "Karo"


def flash(request: Request, text: str, art: str = "ok") -> None:
    """Setzt eine Meldung für die nächste Seite."""
    request.session["flash"] = text
    request.session["flash_kind"] = art


def zurueck(ziel: str) -> RedirectResponse:
    """Redirect mit HTTP 303 See Other."""
    return RedirectResponse(ziel, status_code=HTTP_303_SEE_OTHER)
