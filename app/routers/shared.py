"""Gemeinsame Helfer für alle Router."""

import logging
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from starlette.status import HTTP_303_SEE_OTHER

from .. import config, security
from ..woche import plaene
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
# Datumsangaben erscheinen in den Vorlagen deutsch: {{ wert|datum }}
templates.env.filters["datum"] = plaene.date_label
#: Technische Abbruchgruende in Saetze uebersetzen, die jemand lesen kann.
#: Der Originaltext bleibt daneben stehen — wer ihn braucht, findet ihn.
_KLARTEXT = (
    ("rate limit", "Zu viele Anfragen kurz hintereinander. Einen Moment warten, dann "
                   "erneut versuchen."),
    ("429", "Zu viele Anfragen kurz hintereinander. Einen Moment warten, dann "
            "erneut versuchen."),
    ("zu lange gedauert", "Der Aufruf hat zu lange gedauert. Ein erneuter Versuch hilft meist."),
    ("fehlt", "Die hochgeladene Datei ist nicht mehr da. Bitte laden Sie sie erneut hoch."),
    ("devin_api_key", "DEVIN_API_KEY ist nicht gesetzt oder wird abgelehnt. Bitte "
                      "unter Einstellungen prüfen."),
    ("401", "Der DEVIN_API_KEY wird abgelehnt. Bitte unter Einstellungen prüfen."),
    ("403", "Der DEVIN_API_KEY wird abgelehnt. Bitte unter Einstellungen prüfen."),
)


def klartext(fehler: str | None) -> str:
    """Was ein technischer Abbruch fuer die Familie bedeutet.

    Ohne das steht in der Oberflaeche eine Vermutung statt des Grundes — beim
    Themenblatt stand jahrelang "Lade ein deutlicheres Foto hoch", auch wenn
    in Wahrheit das Kontingent aufgebraucht war.
    """
    text = (fehler or "").strip()
    if not text:
        return "Der Grund wurde nicht festgehalten. Ein erneuter Versuch hilft oft."
    klein = text.lower()
    for merkmal, satz in _KLARTEXT:
        if merkmal in klein:
            return satz
    return text


# Fächer werden als Schlüssel gespeichert und als Name gezeigt.
from .. import faecher as _faecher  # noqa: E402
from ..services import learning_time  # noqa: E402
templates.env.filters["fachname"] = _faecher.name
templates.env.filters["klartext"] = klartext

try:
    ASSET_VERSION = str(max(
        (BASE / "static" / name).stat().st_mtime_ns
        for name in ("karo.css", "simple.css", "simple.js", "drafts.js", "setup.js", "storage.js", "areas.css", "themes.js", "begleiter.js", "meine-welt.css", "meine-welt.js", "lernzeit.js", "fonts.css")
    ))
except OSError:
    ASSET_VERSION = "0"


def render(request: Request, name: str, status_code: int = 200,
           **ctx) -> HTMLResponse:
    """Rendert ein Template mit Kontext."""
    from .. import db, profile, topics, research
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
        "learner_photo_url": profile.photo_url(),
        "learning_ui": request.url.path == "/" or request.url.path.startswith(("/lernen", "/lernzyklus", "/quiz")),
        # Lernzeit misst nur, wo wirklich gelernt wird: "Heute" ist eine
        # Uebersicht, kein Lernschritt, und der Elternbereich zaehlt nie mit.
        "lernzeit_messen": (request.session.get("role") == "child"
                            and request.url.path.startswith(("/lernen", "/lernzyklus", "/quiz"))),
        "lernzeit_takt": learning_time.TAKT,
        "wunsch_max_zeichen": config.ops().formular_wunsch_zeichen,
        "faecher": [(key, _faecher.NAMEN[key]) for key in _faecher.FAECHER],
        "aktives_fach": aktives_fach(request),
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
    # Eltern sehen den Kinderbereich, aendern ihn aber nicht (Gate in main.py).
    # Die Oberflaeche sagt das vorher, statt den Knopf ins Leere laufen zu
    # lassen — und zeigt den Weg: den Kind-Modus.
    basis["nur_ansehen"] = (basis["role"] == "parent" and not basis["adult_page"])
    # Kleiner Briefumschlag im Kinderbereich: wie viel Post von zu Hause ungelesen ist.
    basis["post_neu_anzahl"] = 0
    if not basis["adult_page"]:
        from ..services import family_post
        try:
            basis["post_neu_anzahl"] = len(family_post.unread())
        except Exception:  # noqa: BLE001 - die Anzeige darf nie eine Seite verhindern
            log.warning("Postfach-Zaehler nicht verfuegbar", exc_info=True)
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


def aktives_fach(request: Request, wert: str | None = None) -> str:
    """Das Fach, in dem das Kind gerade arbeitet.

    Ein gültiges ``wert`` (aus Adresse oder Formular) wird gemerkt. Sonst gilt
    das zuletzt gewählte Fach, dann das Fach aus den Einstellungen.
    """
    key = _faecher.schluessel(wert)
    if key:
        request.session["fach"] = key
        return key
    return (_faecher.schluessel(request.session.get("fach"))
            or _faecher.schluessel(getattr(config.load_safe(), "subject", ""))
            or "mathematik")


def flash(request: Request, text: str, art: str = "ok") -> None:
    """Setzt eine Meldung für die nächste Seite."""
    request.session["flash"] = text
    request.session["flash_kind"] = art


def zurueck(ziel: str) -> RedirectResponse:
    """Redirect mit HTTP 303 See Other."""
    return RedirectResponse(ziel, status_code=HTTP_303_SEE_OTHER)


def erfolge_ziel(ziel: str, tab: str = "") -> str:
    """Die Erfolge-Seite gibt es zweimal: /lernstand im Kinderbereich und
    /messung/fortschritt im Elternbereich. Eine Aktion darauf muss in dem
    Bereich zurueckkommen, aus dem sie kam — sonst wechselt ein Klick auf
    "löschen" oder "Zurück zum Lernen" mitten in der Bedienung den halben
    Bildschirm. Das Ergebnis ist immer einer der beiden festen Pfade, nie
    der uebergebene Wert: ein Formularfeld darf kein Umleitungsziel sein.
    """
    basis = "/messung/fortschritt" if ziel.startswith("/messung") else "/lernstand"
    return f"{basis}?tab={tab}" if tab else basis
