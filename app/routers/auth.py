"""Authentifizierung und Setup."""

import dataclasses
import os
import sqlite3

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from .. import config, connections, export, ingest, jobs, quizzes, security, materials, teaching
from ..config import ConfigUnreadable
from ..domain import Ausgabe
from ..llm import BACKENDS, ClaudeClient, ClaudeError, models_for
from .shared import render, flash, zurueck

router = APIRouter()


@router.get("/health")
def health() -> JSONResponse:
    try:
        cfg = config.load()
        ok, notiz = True, None
    except ConfigUnreadable as exc:
        cfg, ok, notiz = config.Config(), False, str(exc)
    return JSONResponse({"ok": ok, "note": notiz,
                         "setup_complete": cfg.setup_complete,
                         "backend": cfg.llm_backend,
                         "drive": ingest.drive_available(),
                         "jobs": jobs.counts()})


@router.get("/verbindungen/status")
def verbindungen_status() -> JSONResponse:
    return JSONResponse(connections.status())


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if not config.load_safe().setup_complete:
        return zurueck("/setup")
    return render(request, "login.html")


@router.post("/login")
def login(request: Request, password: str = Form("")):
    cfg = config.load()
    if security.verify_password(password, cfg.app_password_hash,
                               cfg.app_password_salt):
        rolle = "parent"
    elif cfg.child_password_hash and security.verify_password(
            password, cfg.child_password_hash, cfg.child_password_salt):
        rolle = "child"
    else:
        return render(request, "login.html", error="Passwort stimmt nicht.",
                      status_code=401)
    token = request.session.get("csrf")
    request.session.clear()
    request.session["auth"] = True
    request.session["role"] = rolle
    request.session["csrf"] = token or security.new_csrf_token()
    return zurueck("/")


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return zurueck("/login")


@router.post("/eltern/kind-modus")
def kind_modus(request: Request):
    """Schaltet die laufende Eltern-Session in den eingeschraenkten Kind-Modus.

    Zurueck geht es nur ueber ein erneutes Login mit dem Eltern-Passwort —
    ein Kind in dieser Session kann sich also nicht selbst hochstufen."""
    request.session["role"] = "child"
    return zurueck("/")


def _setup_context(cfg, modelle=None) -> dict:
    from ..llm.cli_backend import CliBackend
    from ..media import notebooklm, tts, video
    cli = CliBackend.cli_available()
    mp4_ok, mp4_grund = video.verfuegbar()
    nlm_ok, nlm_grund = notebooklm.verfuegbar()
    claude_status = connections.status(cfg).get("claude", {})
    return {
        "backends": BACKENDS,
        "modelle": modelle if modelle is not None else [],
        "cli_vorhanden": cli is not None,
        "cli_pfad": cli,
        "claude_ok": claude_status.get("ok", False),
        "claude_note": claude_status.get("note", ""),
        "drive_ok": ingest.drive_available(),
        "drive_writable": ingest.drive_writable(),
        "drive_path": os.environ.get("KARO_DRIVE_PATH") or str(config.DRIVE_DIR),
        "heif_ok": ingest.HEIF_OK,
        "mp4_ok": mp4_ok, "mp4_grund": mp4_grund,
        "nlm_ok": nlm_ok, "nlm_grund": nlm_grund,
        "nlm_warnung": notebooklm.WARNUNG,
        "nlm_login": notebooklm.login_status(),
        "stimmen": tts.STIMMEN,
        "xlsx_ok": export.verfuegbar(),
        "min_password": security.MIN_PASSWORD_LENGTH,
    }


def _modelle(cfg) -> list[dict]:
    fest = models_for(cfg.llm_backend)
    if fest:
        return fest
    try:
        return ClaudeClient.from_config(cfg).list_models()
    except ClaudeError:
        return []


def _waehle(modelle: list[dict], teil: str) -> str:
    for m in modelle:
        if teil in m["id"].lower():
            return m["id"]
    return ""


@router.get("/setup", response_class=HTMLResponse)
def setup_form(request: Request):
    cfg = config.load_safe()
    modelle = _modelle(cfg) if cfg.has_credentials else []
    # Nach abgeschlossener Einrichtung IMMER die Einstellungsseite zeigen,
    # auch wenn die Zugangsdaten gerade fehlen (z. B. nach „Trennen“) — sonst
    # faellt die Seite zurueck auf den Einrichtungsassistenten und der Zugriff
    # auf alle anderen Einstellungen geht verloren. Die Claude-Karte dort
    # zeigt den fehlenden Zugang ohnehin schon mit einem Verbinden-Formular.
    schritt = "modell" if cfg.setup_complete or cfg.has_credentials else "start"
    return render(request, "setup.html", schritt=schritt,
                  **_setup_context(cfg, modelle))


@router.post("/setup/credentials", response_class=HTMLResponse)
def setup_credentials(request: Request, backend: str = Form("abo"),
                      token: str = Form(""), api_key: str = Form(""),
                      learner_name: str = Form(""), grade: str = Form("7"),
                      subject: str = Form("Mathematik")):
    cfg = config.load_safe()

    def zurueck_setup(meldung: str):
        return render(request, "setup.html", schritt="start", error=meldung,
                      status_code=400, **_setup_context(cfg))

    if backend not in BACKENDS:
        return zurueck_setup("Bitte einen Weg zum Modell auswählen.")

    entwurf = config.Config(
        llm_backend=backend,
        claude_oauth_token=token.strip(),
        anthropic_api_key=api_key.strip(),
    )
    if not entwurf.has_credentials:
        return zurueck_setup("Bitte die Zugangsdaten eintragen."
                       if backend == "api" else
                       'Bitte den Token aus "claude setup-token" eintragen.')

    try:
        pruefer = ClaudeClient.from_config(entwurf)
        modelle = _modelle(entwurf) or pruefer.list_models()
        if not modelle:
            return zurueck_setup("Es sind keine nutzbaren Modelle verfügbar.")
        pruefer.model_text = _waehle(modelle, "haiku") or modelle[0]["id"]
        pruefer.verify()
    except ClaudeError as exc:
        return zurueck_setup(str(exc))
    except Exception:
        return zurueck_setup("Beim Prüfen ist ein unerwarteter Fehler aufgetreten.")

    try:
        klasse = max(1, min(13, int(grade)))
    except ValueError:
        klasse = 7

    config.update(
        llm_backend=backend,
        claude_oauth_token=token.strip() if backend == "abo" else "",
        anthropic_api_key=api_key.strip() if backend == "api" else "",
        learner_name=learner_name.strip()[:60],
        learner_grade=klasse,
        subject=subject.strip()[:60] or "Mathematik",
        model_text=_waehle(modelle, "haiku") or modelle[0]["id"],
        model_vision=_waehle(modelle, "sonnet") or modelle[0]["id"],
    )
    return render(request, "setup.html", schritt="modell",
                  **_setup_context(config.load(), modelle))


@router.post("/setup/finish")
def setup_finish(request: Request, model_vision: str = Form(""),
                 model_text: str = Form(""), header_crop: str = Form("8"),
                 default_ausgabe: str = Form("html"),
                 tts_stimme: str = Form(""),
                 max_lernrunden: str = Form("4"),
                 recherche: str = Form(""),
                 drive_unterordner: str = Form(""),
                 material_db_path: str | None = Form(None),
                 password: str = Form(""), password2: str = Form(""),
                 child_password: str = Form(""), child_password2: str = Form("")):
    cfg = config.load()
    erstmalig = not cfg.setup_complete

    # Vor jeder Validierung erst den Entwurf aus dem Formular bilden: schlägt
    # eine Prüfung (z. B. das Passwort) fehl, zeigt die Seite genau das, was
    # gerade eingetippt war — nicht den alten, gespeicherten Stand. Sonst
    # wirkt es, als wäre die Eingabe bei jedem Fehler verworfen worden, auch
    # wenn tatsächlich nur das Passwortfeld das Problem war.
    gueltige = {m["id"] for m in _modelle(cfg)}
    try:
        crop = max(0, min(25, int(header_crop)))
    except ValueError:
        crop = cfg.header_crop_percent
    try:
        runden = max(1, min(8, int(max_lernrunden)))
    except ValueError:
        runden = cfg.max_lernrunden
    # Nie ".." oder eine fuehrende "/" zulassen — sonst koennte das Unterver-
    # zeichnis aus dem Drive-Ordner heraus zeigen (siehe config.drive_root()).
    unterordner = "/".join(
        teil for teil in drive_unterordner.strip().strip("/\\").split("/")
        if teil not in ("", ".", ".."))[:100]
    entwurf = dataclasses.replace(
        cfg,
        model_vision=model_vision if model_vision in gueltige else cfg.model_vision,
        model_text=model_text if model_text in gueltige else cfg.model_text,
        header_crop_percent=crop,
        default_ausgabe=(default_ausgabe
                        if default_ausgabe in {a.value for a in Ausgabe}
                        else cfg.default_ausgabe),
        tts_stimme=tts_stimme or cfg.tts_stimme,
        max_lernrunden=runden,
        recherche_erlaubt=recherche == "ja",
        drive_subdir=unterordner,
        material_db_path=(material_db_path.strip() if material_db_path is not None
                          else cfg.material_db_path),
    )

    def zurueck_setup(meldung: str):
        return render(request, "setup.html", schritt="modell", error=meldung,
                      invalid=True, status_code=400, cfg=entwurf.public_dict(),
                      **_setup_context(entwurf, _modelle(cfg)))

    if not cfg.has_credentials:
        return zurueck("/setup")

    if erstmalig and not password:
        return zurueck_setup("Bitte vergeben Sie ein Passwort für diese Instanz.")
    if password:
        if password != password2:
            return zurueck_setup("Die beiden Passwörter stimmen nicht überein.")
        if len(password) < security.MIN_PASSWORD_LENGTH:
            return zurueck_setup(f"Das Passwort muss mindestens "
                           f"{security.MIN_PASSWORD_LENGTH} Zeichen haben.")
    if child_password:
        if child_password != child_password2:
            return zurueck_setup("Die beiden Kind-Passwörter stimmen nicht überein.")
        if len(child_password) < security.MIN_PASSWORD_LENGTH:
            return zurueck_setup(f"Das Kind-Passwort muss mindestens "
                           f"{security.MIN_PASSWORD_LENGTH} Zeichen haben.")

    aenderungen = {
        "model_vision": entwurf.model_vision,
        "model_text": entwurf.model_text,
        "header_crop_percent": entwurf.header_crop_percent,
        "default_ausgabe": entwurf.default_ausgabe,
        "tts_stimme": entwurf.tts_stimme,
        "max_lernrunden": entwurf.max_lernrunden,
        "recherche_erlaubt": entwurf.recherche_erlaubt,
        "drive_subdir": entwurf.drive_subdir,
        "material_db_path": entwurf.material_db_path,
        "setup_complete": True,
    }
    if password:
        h, s = security.hash_password(password)
        aenderungen["app_password_hash"] = h
        aenderungen["app_password_salt"] = s
    if child_password:
        h2, s2 = security.hash_password(child_password)
        aenderungen["child_password_hash"] = h2
        aenderungen["child_password_salt"] = s2

    try:
        materials.einstellungen_speichern(aenderungen)
    except (ValueError, OSError, sqlite3.Error, teaching.TeachingError) as exc:
        return zurueck_setup(f"Materialdatenbank: {exc}")
    if not erstmalig:
        quizzes.alle_flaggen_neu()
    ingest.ensure_folders()
    jobs.start()
    request.session["auth"] = True
    request.session["role"] = "parent"

    meldung = "Einrichtung abgeschlossen." if erstmalig else "Einstellungen gespeichert."
    if aenderungen["default_ausgabe"] == Ausgabe.NOTEBOOKLM.value:
        from ..media import notebooklm
        ok, _ = notebooklm.verfuegbar()
        # Nur anbieten, wenn wirklich noch keine gueltige Anmeldung vorliegt —
        # sonst wuerde jedes Speichern (auch nur eines unabhaengigen Feldes
        # wie „Max. Runden") die Google-Anmeldung erneut aufreissen, obwohl
        # NotebookLM laengst verbunden ist.
        if not ok and notebooklm.login_start():
            flash(request, meldung + " Die NotebookLM-Anmeldung wird "
                           "vorbereitet — bitte auf dieser Seite anmelden.")
            return zurueck("/setup")
    flash(request, meldung)
    return zurueck("/setup" if not erstmalig else "/")


@router.post("/setup/claude/verbinden")
def setup_claude_verbinden(request: Request, backend: str = Form("abo"),
                           token: str = Form(""), api_key: str = Form("")):
    cfg = config.load()

    if backend not in BACKENDS:
        flash(request, "Bitte einen Weg zum Modell auswählen.", "err")
        return zurueck("/setup")

    entwurf = config.Config(
        llm_backend=backend,
        claude_oauth_token=token.strip(),
        anthropic_api_key=api_key.strip(),
    )
    if not entwurf.has_credentials:
        flash(request, "Bitte die Zugangsdaten eintragen."
                       if backend == "api" else
                       'Bitte den Token aus "claude setup-token" eintragen.',
                       "err")
        return zurueck("/setup")

    try:
        pruefer = ClaudeClient.from_config(entwurf)
        modelle = models_for(backend) or pruefer.list_models()
        if not modelle:
            flash(request, "Es sind keine nutzbaren Modelle verfügbar.", "err")
            return zurueck("/setup")
        pruefer.model_text = _waehle(modelle, "haiku") or modelle[0]["id"]
        pruefer.verify()
    except ClaudeError as exc:
        flash(request, str(exc), "err")
        return zurueck("/setup")
    except Exception:
        flash(request, "Beim Prüfen ist ein unerwarteter Fehler aufgetreten.", "err")
        return zurueck("/setup")

    gueltige = {m["id"] for m in modelle}
    aenderungen = {
        "llm_backend": backend,
        "claude_oauth_token": token.strip() if backend == "abo" else "",
        "anthropic_api_key": api_key.strip() if backend == "api" else "",
    }
    if backend != cfg.llm_backend or cfg.model_text not in gueltige:
        aenderungen["model_text"] = _waehle(modelle, "haiku") or modelle[0]["id"]
    if backend != cfg.llm_backend or cfg.model_vision not in gueltige:
        aenderungen["model_vision"] = _waehle(modelle, "sonnet") or modelle[0]["id"]

    config.update(**aenderungen)
    connections.status(config.load(), force=True)
    flash(request, "Claude ist verbunden.")
    return zurueck("/setup")


@router.post("/setup/claude/trennen")
def setup_claude_trennen(request: Request):
    config.update(claude_oauth_token="", anthropic_api_key="")
    connections.status(config.load(), force=True)
    flash(request, "Claude-Verbindung getrennt.")
    return zurueck("/setup")


@router.post("/setup/notebooklm/anmelden")
def setup_notebooklm_login(request: Request):
    from ..media import notebooklm
    if notebooklm.login_start():
        flash(request, "Die NotebookLM-Anmeldung wird vorbereitet — gleich "
                       "erscheint hier ein Anmeldefenster.")
    else:
        flash(request, "Die Anmeldung läuft schon oder die "
                       "NotebookLM-Kommandozeile ist nicht installiert.", "warn")
    return zurueck("/setup")


@router.get("/setup/notebooklm/status")
def setup_notebooklm_status() -> JSONResponse:
    from ..media import notebooklm
    return JSONResponse(notebooklm.login_status())


@router.post("/setup/notebooklm/trennen")
def setup_notebooklm_trennen(request: Request):
    from ..media import notebooklm
    try:
        notebooklm.trennen()
        flash(request, "NotebookLM-Verbindung getrennt.")
    except notebooklm.NotebookLmUnavailable as exc:
        flash(request, str(exc), "warn")
    connections.status(force=True)
    return zurueck("/setup")


@router.post("/setup/reset")
def setup_reset(request: Request):
    config.update(claude_oauth_token="", anthropic_api_key="",
                  model_vision="", model_text="", setup_complete=False)
    request.session.clear()
    return zurueck("/setup")
