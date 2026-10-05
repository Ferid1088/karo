"""Design-Wahl: ein einziger Endpunkt fuer den kleinen Kopf-Picker.

Der Picker selbst wird serverseitig in `base.html` gerendert (Kontext aus
`shared.render` → `app.themes.oberflaeche`); hier wird nur die Wahl
entgegengenommen, geprueft und gespeichert. Beim normalen Formular-POST
gibt es einen Redirect zurueck auf die Seite, per fetch kommt JSON, damit
das Popover fuer die Sofort-Vorschau offen bleiben kann.
"""

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse

from .. import themes
from .shared import flash, zurueck

router = APIRouter()


def _ziel(ziel: str) -> str:
    """Ruecksprung-Adresse nach einem Formular-POST: nur lokale Pfade —
    ein Formularfeld darf kein Umleitungsziel nach draussen sein."""
    if ziel.startswith("/") and not ziel.startswith("//"):
        return ziel
    return "/"


@router.post("/themes/waehlen")
def theme_waehlen(request: Request, theme_id: str = Form(""),
                  ziel: str = Form("/")):
    try:
        gewaehlt = themes.auswaehlen(theme_id)
    except ValueError as exc:
        if "text/html" in (request.headers.get("accept") or ""):
            flash(request, str(exc), "warn")
            return zurueck(_ziel(ziel))
        return JSONResponse({"ok": False, "fehler": str(exc)},
                            status_code=400)
    if "text/html" in (request.headers.get("accept") or ""):
        return zurueck(_ziel(ziel))
    return JSONResponse({"ok": True, "theme": gewaehlt})
