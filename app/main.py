"""Karo — Web-Anwendung.

Startreihenfolge:
  1. Protokoll-Schwaerzung einschalten und selbst testen
  2. Datenbank anlegen oder oeffnen
  3. Konfiguration lesen. Fehlt sie, beantwortet die App jede Anfrage mit dem
     Einrichtungsschritt. Ist sie beschaedigt, zeigt die App das an, statt
     stillschweigend zu Standardwerten zurueckzufallen.
  4. Nach abgeschlossener Einrichtung: Job-Worker starten.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_303_SEE_OTHER

from . import (
    config,
    connections,
    db,
    export,
    ingest,
    jobs,
    kb,
    quizzes,
    research,
    security,
    teaching,
    topics,
)
from .config import ConfigUnreadable
from .domain import (
    AUSGABE_HINTS,
    AUSGABE_LABELS,
    DOC_STATE_HINTS,
    DOC_STATE_LABELS,
    ERROR_LABELS,
    FLAG_LABELS,
    FLAG_ORDER,
    STUFE_LABELS,
    Ausgabe,
    Flag,
)
from .llm import BACKENDS, ClaudeClient, ClaudeError, models_for
from .quizzes import QuizError
from .teaching import TeachingError

security.configure_logging(os.environ.get("KARO_LOG_LEVEL", "INFO"))
log = logging.getLogger("karo")

BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / "templates"))

#: Haengt an /static/... an, damit ein neues Image nicht die alte CSS/JS aus
#: dem Browser-Cache serviert bekommt (die Datei setzt keinen eigenen
#: Cache-Control-Header, also entscheidet der Browser selbst, wie lange er
#: sie behaelt — mit dieser Versionsnummer in der URL zaehlt das nicht mehr).
try:
    ASSET_VERSION = str(int((BASE / "static" / "karo.css").stat().st_mtime))
except OSError:                                            # pragma: no cover
    ASSET_VERSION = "0"

#: Pfade ohne Anmeldung. Exakte Treffer, kein Praefix — sonst waere
#: `/setup/finish` fuer immer offen.
PUBLIC_EXACT = frozenset({"/health", "/login", "/logout", "/setup",
                          "/setup/credentials", "/setup/finish", "/setup/reset"})
PUBLIC_PREFIX = ("/static/",)

MAX_BODY_BYTES = 30 * 1024 * 1024
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    security.configure_logging(os.environ.get("KARO_LOG_LEVEL", "INFO"))
    if not security.selftest_redaction():           # pragma: no cover
        raise RuntimeError("Schwärzung der Protokolle funktioniert nicht — Abbruch.")
    db.init()
    zurueck = jobs.recover_stuck()
    if zurueck:
        log.info("%s unterbrochene Vorgänge zurückgesetzt", zurueck)
    if config.load_safe().setup_complete:
        jobs.start()
    yield
    jobs.stop()


app = FastAPI(title="Karo", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)


# ==========================================================================
# Middleware
#
# Als reines ASGI-Middleware geschrieben, nicht als @app.middleware("http"):
# die CSRF-Pruefung muss den Formularinhalt lesen, und ein einmal gelesener
# Request-Body ist danach fuer den Handler leer. Hier wird er gepuffert und
# anschliessend erneut zugestellt.
# ==========================================================================

class Gate:
    """Einrichtungsweiche, Anmeldung und CSRF-Abwehr."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope, receive)
        # scope["path"] und NICHT request.url.path: letzteres wird aus dem
        # Host-Header zusammengesetzt und ist von aussen manipulierbar. Der
        # Router entscheidet nach scope["path"] — die Weiche muss denselben
        # Wert benutzen, sonst sind beide unterschiedlicher Meinung.
        root = scope.get("root_path", "")
        path = scope.get("path", "")
        if root and path.startswith(root):
            path = path[len(root):] or "/"

        if any(path.startswith(p) for p in PUBLIC_PREFIX):
            return await self.app(scope, receive, send)

        try:
            cfg = config.load()
        except ConfigUnreadable as exc:
            return await self._send(send, scope, HTMLResponse(
                f"<h1>Karo kann nicht starten</h1><p>{exc}</p>", status_code=500))

        authed = bool(request.session.get("auth"))
        oeffentlich = path in PUBLIC_EXACT

        if not cfg.setup_complete:
            if not path.startswith("/setup") and path != "/health":
                return await self._send(send, scope, RedirectResponse(
                    "/setup", HTTP_303_SEE_OTHER))
        else:
            # Nach der Einrichtung sind die Setup-Routen nicht mehr offen —
            # sonst koennte jede Person am Rechner Passwort und Zugangsdaten
            # ueberschreiben, ohne sich anzumelden.
            if path.startswith("/setup"):
                oeffentlich = False
            if not oeffentlich and not authed:
                return await self._send(send, scope, RedirectResponse(
                    "/login", HTTP_303_SEE_OTHER))

        if request.method in security.SAFE_METHODS:
            return await self.app(scope, receive, send)

        if not security.same_origin(request.headers,
                                    request.headers.get("host", "")):
            return await self._send(send, scope, HTMLResponse(
                "<h1>Abgelehnt</h1><p>Diese Anfrage kam von einer fremden "
                "Seite.</p>", status_code=403))

        try:
            angekuendigt = int(request.headers.get("content-length") or 0)
        except ValueError:
            angekuendigt = 0
        if angekuendigt > MAX_BODY_BYTES:
            return await self._send(send, scope, _zu_gross())

        body = bytearray()
        weiter = True
        while weiter:
            nachricht = await receive()
            if nachricht["type"] == "http.disconnect":
                return await self._send(send, scope, HTMLResponse(
                    "Verbindung abgebrochen.", status_code=400))
            body.extend(nachricht.get("body", b""))
            weiter = nachricht.get("more_body", False)
            if len(body) > MAX_BODY_BYTES:
                return await self._send(send, scope, _zu_gross())
        body = bytes(body)

        probe = Request(scope, _replay(body))
        try:
            formular = await probe.form()
            gesendet = formular.get(security.CSRF_FIELD)
        except Exception:
            gesendet = None
        finally:
            try:
                await probe.close()
            except Exception:                            # pragma: no cover
                pass

        if not security.csrf_ok(request.session.get("csrf"), gesendet):
            return await self._send(send, scope, HTMLResponse(
                "<h1>Abgelehnt</h1><p>Das Formular ist abgelaufen oder stammt "
                "nicht von dieser Seite. Bitte die Seite neu laden und erneut "
                "absenden.</p>", status_code=403))

        await self.app(scope, _replay(body), send)

    @staticmethod
    async def _send(send, scope, response) -> None:
        await response(scope, _replay(b""), send)


def _zu_gross() -> HTMLResponse:
    return HTMLResponse(
        "<h1>Zu groß</h1><p>Die gesendeten Daten überschreiten "
        f"{MAX_BODY_BYTES // 1_048_576} MB.</p>", status_code=413)


def _replay(body: bytes):
    """receive-Kanal, der den gepufferten Body genau einmal liefert."""
    gesendet = False

    async def receive():
        nonlocal gesendet
        if not gesendet:
            gesendet = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    return receive


app.add_middleware(Gate)
app.add_middleware(
    SessionMiddleware,
    secret_key=config.session_secret().hex(),
    session_cookie="karo_session",
    max_age=60 * 60 * 24 * 14,
    same_site="strict",
    https_only=False,        # die Instanz laeuft an 127.0.0.1, nicht ueber TLS
)
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


# ==========================================================================
# Gemeinsame Helfer
# ==========================================================================

def render(request: Request, name: str, status_code: int = 200,
           **ctx) -> HTMLResponse:
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
    request.session["flash"] = text
    request.session["flash_kind"] = art


def _zurueck(ziel: str) -> RedirectResponse:
    return RedirectResponse(ziel, status_code=HTTP_303_SEE_OTHER)


async def _datei_lesen(datei: UploadFile) -> bytes:
    puffer = bytearray()
    while stueck := await datei.read(1 << 20):
        puffer.extend(stueck)
        if len(puffer) > MAX_UPLOAD_BYTES:
            raise ValueError("zu groß")
    return bytes(puffer)


# ==========================================================================
# Gesundheit
# ==========================================================================

@app.get("/health")
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


@app.get("/verbindungen/status")
def verbindungen_status() -> JSONResponse:
    """Fuer das Status-Widget in jeder Seite: Claude und NotebookLM."""
    return JSONResponse(connections.status())


# ==========================================================================
# Einrichtung
# ==========================================================================

def _setup_context(cfg, modelle=None) -> dict:
    from .llm.cli_backend import CliBackend
    from .media import notebooklm, tts, video

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


@app.get("/setup", response_class=HTMLResponse)
def setup_form(request: Request):
    cfg = config.load_safe()
    modelle = _modelle(cfg) if cfg.has_credentials else []
    schritt = "modell" if cfg.has_credentials else "start"
    return render(request, "setup.html", schritt=schritt,
                  **_setup_context(cfg, modelle))


def _modelle(cfg) -> list[dict]:
    """Modelliste. Beim Abo eine feste Liste, bei der API die des Kontos."""
    fest = models_for(cfg.llm_backend)
    if fest:
        return fest
    try:
        return ClaudeClient.from_config(cfg).list_models()
    except ClaudeError as exc:
        log.warning("Modelliste nicht abrufbar: %s", exc)
        return []


@app.post("/setup/credentials", response_class=HTMLResponse)
def setup_credentials(request: Request, backend: str = Form("abo"),
                      token: str = Form(""), api_key: str = Form(""),
                      learner_name: str = Form(""), grade: str = Form("7"),
                      subject: str = Form("Mathematik")):
    cfg = config.load_safe()

    def zurueck(meldung: str):
        return render(request, "setup.html", schritt="start", error=meldung,
                      status_code=400, **_setup_context(cfg))

    if backend not in BACKENDS:
        return zurueck("Bitte einen Weg zum Modell auswählen.")

    entwurf = config.Config(
        llm_backend=backend,
        claude_oauth_token=token.strip(),
        anthropic_api_key=api_key.strip(),
    )
    if not entwurf.has_credentials:
        return zurueck("Bitte die Zugangsdaten eintragen."
                       if backend == "api" else
                       "Bitte den Token aus „claude setup-token“ eintragen.")

    try:
        pruefer = ClaudeClient.from_config(entwurf)
        modelle = _modelle(entwurf) or pruefer.list_models()
        if not modelle:
            return zurueck("Es sind keine nutzbaren Modelle verfügbar.")
        pruefer.model_text = _waehle(modelle, "haiku") or modelle[0]["id"]
        pruefer.verify()
    except ClaudeError as exc:
        return zurueck(str(exc))
    except Exception:                                    # pragma: no cover
        log.exception("Unerwarteter Fehler beim Prüfen der Zugangsdaten")
        return zurueck("Beim Prüfen ist ein unerwarteter Fehler aufgetreten. "
                       "Details stehen im Protokoll des Containers.")

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


def _waehle(modelle: list[dict], teil: str) -> str:
    for m in modelle:
        if teil in m["id"].lower():
            return m["id"]
    return ""


@app.post("/setup/finish")
def setup_finish(request: Request, model_vision: str = Form(""),
                 model_text: str = Form(""), header_crop: str = Form("8"),
                 default_ausgabe: str = Form("html"),
                 tts_stimme: str = Form(""),
                 max_lernrunden: str = Form("4"),
                 recherche: str = Form(""),
                 password: str = Form(""), password2: str = Form("")):
    cfg = config.load()
    erstmalig = not cfg.setup_complete

    def zurueck(meldung: str):
        return render(request, "setup.html", schritt="modell", error=meldung,
                      status_code=400, **_setup_context(cfg, _modelle(cfg)))

    if not cfg.has_credentials:
        return _zurueck("/setup")

    # Beim ersten Mal ist ein Passwort Pflicht: ohne waere jede andere Person
    # am selben Rechner in den Daten des Kindes.
    if erstmalig and not password:
        return zurueck("Bitte vergeben Sie ein Passwort für diese Instanz.")
    if password:
        if password != password2:
            return zurueck("Die beiden Passwörter stimmen nicht überein.")
        if len(password) < security.MIN_PASSWORD_LENGTH:
            return zurueck(f"Das Passwort muss mindestens "
                           f"{security.MIN_PASSWORD_LENGTH} Zeichen haben.")

    gueltige = {m["id"] for m in _modelle(cfg)}
    try:
        crop = max(0, min(25, int(header_crop)))
    except ValueError:
        crop = cfg.header_crop_percent
    try:
        runden = max(1, min(8, int(max_lernrunden)))
    except ValueError:
        runden = cfg.max_lernrunden

    aenderungen = {
        "model_vision": model_vision if model_vision in gueltige else cfg.model_vision,
        "model_text": model_text if model_text in gueltige else cfg.model_text,
        "header_crop_percent": crop,
        "default_ausgabe": (default_ausgabe
                            if default_ausgabe in {a.value for a in Ausgabe}
                            else cfg.default_ausgabe),
        "tts_stimme": tts_stimme or cfg.tts_stimme,
        "max_lernrunden": runden,
        "recherche_erlaubt": recherche == "ja",
        "setup_complete": True,
    }
    if password:
        h, s = security.hash_password(password)
        aenderungen["app_password_hash"] = h
        aenderungen["app_password_salt"] = s

    config.update(**aenderungen)
    if not erstmalig:
        quizzes.alle_flaggen_neu()       # die Schwellen können sich geändert haben
    ingest.ensure_folders()
    jobs.start()
    request.session["auth"] = True

    meldung = "Einrichtung abgeschlossen." if erstmalig else "Einstellungen gespeichert."
    if aenderungen["default_ausgabe"] == Ausgabe.NOTEBOOKLM.value:
        from .media import notebooklm
        ok, _ = notebooklm.verfuegbar()
        if not ok and notebooklm.login_start():
            flash(request, meldung + " Die NotebookLM-Anmeldung wird "
                           "vorbereitet — bitte auf dieser Seite anmelden.")
            return _zurueck("/setup")
    flash(request, meldung)
    return _zurueck("/")


@app.post("/setup/claude/verbinden")
def setup_claude_verbinden(request: Request, backend: str = Form("abo"),
                           token: str = Form(""), api_key: str = Form("")):
    """Claude-Zugangsdaten neu setzen, ohne den Rest der Einstellungen
    anzufassen — anders als `/setup/credentials`, das nur beim allerersten
    Einrichten läuft und danach nicht mehr erreichbar ist.
    """
    cfg = config.load()

    if backend not in BACKENDS:
        flash(request, "Bitte einen Weg zum Modell auswählen.", "err")
        return _zurueck("/setup")

    entwurf = config.Config(
        llm_backend=backend,
        claude_oauth_token=token.strip(),
        anthropic_api_key=api_key.strip(),
    )
    if not entwurf.has_credentials:
        flash(request, "Bitte die Zugangsdaten eintragen."
                       if backend == "api" else
                       "Bitte den Token aus „claude setup-token“ eintragen.",
                       "err")
        return _zurueck("/setup")

    try:
        pruefer = ClaudeClient.from_config(entwurf)
        modelle = models_for(backend) or pruefer.list_models()
        if not modelle:
            flash(request, "Es sind keine nutzbaren Modelle verfügbar.", "err")
            return _zurueck("/setup")
        pruefer.model_text = _waehle(modelle, "haiku") or modelle[0]["id"]
        pruefer.verify()
    except ClaudeError as exc:
        flash(request, str(exc), "err")
        return _zurueck("/setup")
    except Exception:                                    # pragma: no cover
        log.exception("Unerwarteter Fehler beim Verbinden mit Claude")
        flash(request, "Beim Prüfen ist ein unerwarteter Fehler aufgetreten. "
                       "Details stehen im Protokoll des Containers.", "err")
        return _zurueck("/setup")

    gueltige = {m["id"] for m in modelle}
    aenderungen = {
        "llm_backend": backend,
        "claude_oauth_token": token.strip() if backend == "abo" else "",
        "anthropic_api_key": api_key.strip() if backend == "api" else "",
    }
    # Nur bei einem Backend-Wechsel neu waehlen — sonst bleibt die bisherige
    # Modellauswahl unangetastet, auch wenn sie in der Liste weiter unten steht.
    if backend != cfg.llm_backend or cfg.model_text not in gueltige:
        aenderungen["model_text"] = _waehle(modelle, "haiku") or modelle[0]["id"]
    if backend != cfg.llm_backend or cfg.model_vision not in gueltige:
        aenderungen["model_vision"] = _waehle(modelle, "sonnet") or modelle[0]["id"]

    config.update(**aenderungen)
    connections.status(config.load(), force=True)   # Widget zeigt sofort "verbunden"
    flash(request, "Claude ist verbunden.")
    return _zurueck("/setup")


@app.post("/setup/notebooklm/anmelden")
def setup_notebooklm_login(request: Request):
    from .media import notebooklm

    if notebooklm.login_start():
        flash(request, "Die NotebookLM-Anmeldung wird vorbereitet — gleich "
                       "erscheint hier ein Anmeldefenster. Falls nicht: "
                       "diese Seite in ein paar Sekunden neu laden.")
    else:
        flash(request, "Die Anmeldung läuft schon, oder die "
                       "NotebookLM-Kommandozeile ist nicht installiert "
                       "(siehe README, Abschnitt „NotebookLM“).", "warn")
    return _zurueck("/setup")


@app.post("/setup/reset")
def setup_reset(request: Request):
    config.update(claude_oauth_token="", anthropic_api_key="",
                  model_vision="", model_text="", setup_complete=False)
    request.session.clear()
    return _zurueck("/setup")


# ==========================================================================
# Anmeldung
# ==========================================================================

@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if not config.load_safe().setup_complete:
        return _zurueck("/setup")
    return render(request, "login.html")


@app.post("/login")
def login(request: Request, password: str = Form("")):
    cfg = config.load()
    if security.verify_password(password, cfg.app_password_hash,
                               cfg.app_password_salt):
        token = request.session.get("csrf")
        request.session.clear()              # Session-Fixierung vermeiden
        request.session["auth"] = True
        request.session["csrf"] = token or security.new_csrf_token()
        return _zurueck("/")
    return render(request, "login.html", error="Passwort stimmt nicht.",
                  status_code=401)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return _zurueck("/login")


# ==========================================================================
# Übersicht
# ==========================================================================

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    themen = topics.liste(topics.AKTIV)
    themen.sort(key=lambda t: (FLAG_ORDER.index(t["flag"])
                               if t["flag"] in FLAG_ORDER else 9, t["sort"]))
    zaehler = {f: sum(1 for t in themen if t["flag"] == f) for f in FLAG_ORDER}
    return render(
        request, "dashboard.html",
        themen=themen, zaehler=zaehler,
        kb_stat=kb.statistik(),
        offene_quizze=quizzes.offene(),
        offene_lessons=teaching.offene(),
        fehler=[dict(r) for r in db.q(
            "SELECT * FROM job WHERE state='fehler' ORDER BY id DESC LIMIT 20")],
        counts=jobs.counts(),
        einig=quizzes.uebereinstimmung(),
    )


# ==========================================================================
# Wissensbasis
# ==========================================================================

@app.get("/wissen", response_class=HTMLResponse)
def wissen(request: Request):
    blaetter = [dict(r) for r in db.q(
        """SELECT d.*, (SELECT COUNT(*) FROM kb_chunk k WHERE k.document_id=d.id)
                  AS abschnitte
             FROM document d WHERE d.rolle='wissen'
            ORDER BY d.id DESC LIMIT 60""")]
    return render(request, "wissen.html", blaetter=blaetter,
                  kb_stat=kb.statistik(), counts=jobs.counts(),
                  drive_ok=ingest.drive_available(),
                  inbox_path=_lesbarer_eingang())


def _lesbarer_eingang() -> str:
    host = os.environ.get("KARO_DRIVE_PATH")
    if host and ingest.drive_available():
        return f"{host.rstrip('/')}/{ingest.INBOX}"
    if ingest.drive_available():
        return f"Ihr Karo-Ordner in Google Drive → {ingest.INBOX}"
    return "Hochladen in dieser Anwendung (kein Drive eingehängt)"


def _einlesen(request: Request) -> None:
    ergebnisse = ingest.scan_inbox()
    neu = [r for r in ergebnisse if r["status"] == "neu"]
    doppelt = sum(1 for r in ergebnisse if r["status"] == "doppelt")
    fehler = [r for r in ergebnisse if r["status"] == "fehler"]
    for r in neu:
        jobs.enqueue("kb_extract", {"document_id": r["document_id"]},
                     dedup_key=f"kb:{r['document_id']}")
    teile = [f"{len(neu)} neu"]
    if doppelt:
        teile.append(f"{doppelt} bereits bekannt")
    if fehler:
        teile.append(f"{len(fehler)} nicht lesbar: "
                     + "; ".join(f"{r['name']} – {r['error']}" for r in fehler[:3]))
    flash(request, "Eingelesen: " + ", ".join(teile), "warn" if fehler else "ok")


@app.post("/wissen/einlesen")
def wissen_einlesen(request: Request):
    _einlesen(request)
    return _zurueck("/wissen")


@app.post("/wissen/upload")
async def wissen_upload(request: Request, datei: UploadFile | None = None):
    formular = await request.form()
    datei = datei or formular.get("datei")
    if datei is None or not getattr(datei, "filename", ""):
        flash(request, "Es wurde keine Datei ausgewählt.", "err")
        return _zurueck("/wissen")

    themenname = str(formular.get("themenname") or "").strip()
    if not themenname:
        flash(request, "Bitte einen Themennamen angeben — Karo zerlegt das "
                       "Blatt dann in die Unterthemen darunter.", "err")
        return _zurueck("/wissen")

    endung = Path(datei.filename).suffix.lower()
    if endung not in ingest.ALL_SUFFIXES:
        flash(request, f"Dateityp {endung or '(ohne)'} wird nicht unterstützt.",
              "err")
        return _zurueck("/wissen")

    try:
        daten = await _datei_lesen(datei)
    except ValueError:
        flash(request, f"Die Datei ist größer als "
                       f"{MAX_UPLOAD_BYTES // 1_048_576} MB.", "err")
        return _zurueck("/wissen")

    def verarbeiten():
        aufnahme = ingest.aufnehmen(daten, endung, rolle="wissen",
                                    themenname=themenname)
        if aufnahme["status"] == "neu":
            jobs.enqueue("kb_extract", {"document_id": aufnahme["document_id"]},
                         dedup_key=f"kb:{aufnahme['document_id']}")
        return aufnahme

    try:
        aufnahme = await run_in_threadpool(verarbeiten)
    except ingest.IngestError as exc:
        flash(request, str(exc), "err")
        return _zurueck("/wissen")

    flash(request, f"Blatt aufgenommen, wird jetzt für „{themenname}“ gelesen."
          if aufnahme["status"] == "neu" else "Dieses Blatt ist schon bekannt.")
    return _zurueck("/wissen")


@app.get("/scan/{doc_id}.jpg")
def scan_bild(doc_id: int):
    doc = db.q1("SELECT stored_path FROM document WHERE id = ?", doc_id)
    if doc is None or not Path(doc["stored_path"]).is_file():
        return JSONResponse({"error": "nicht gefunden"}, status_code=404)
    return FileResponse(doc["stored_path"], media_type="image/jpeg")


@app.get("/wissen/{doc_id}", response_class=HTMLResponse)
def wissen_blatt(request: Request, doc_id: int):
    doc = db.q1("SELECT * FROM document WHERE id = ?", doc_id)
    if doc is None:
        flash(request, "Blatt nicht gefunden.", "err")
        return _zurueck("/wissen")
    abschnitte = [dict(r) for r in db.q(
        """SELECT k.*, t.label AS thema_label FROM kb_chunk k
             LEFT JOIN topic t ON t.id = k.topic_id
            WHERE k.document_id=? ORDER BY k.position""", doc_id)]
    return render(request, "wissen_blatt.html", doc=dict(doc),
                  abschnitte=abschnitte)


# ==========================================================================
# Themen
# ==========================================================================

@app.get("/themen", response_class=HTMLResponse)
def themen(request: Request):
    aktive = topics.liste(topics.AKTIV)
    aktive.sort(key=lambda t: (FLAG_ORDER.index(t["flag"])
                               if t["flag"] in FLAG_ORDER else 9, t["sort"]))
    for t in aktive:
        t["verlauf"] = quizzes.verlauf(t["id"])
    return render(request, "themen.html",
                  vorschlaege=topics.liste(topics.VORSCHLAG),
                  aktive=aktive, einig=quizzes.uebereinstimmung())


@app.post("/themen/entscheiden")
async def themen_entscheiden(request: Request):
    formular = await request.form()
    entscheidungen = []
    for schluessel in formular.keys():
        if not schluessel.startswith("aktion_"):
            continue
        roh = schluessel[7:]
        if not roh.isdigit():
            continue
        entscheidungen.append({
            "id": int(roh),
            "aktion": formular.get(schluessel),
            "label": formular.get(f"label_{roh}", ""),
        })
    ergebnis = topics.entscheiden(entscheidungen)
    if ergebnis["angenommen"] or ergebnis["abgelehnt"]:
        flash(request, f"{ergebnis['angenommen']} übernommen, "
                       f"{ergebnis['abgelehnt']} verworfen"
                       + (f", {ergebnis['umbenannt']} umbenannt"
                          if ergebnis["umbenannt"] else "") + ".")
    else:
        flash(request, "Es wurde nichts entschieden.", "warn")
    return _zurueck("/themen")


@app.post("/themen/neu")
def themen_neu(request: Request, label: str = Form(""),
               beschreibung: str = Form("")):
    neu = topics.anlegen(label, beschreibung)
    if neu is None:
        flash(request, "Dieses Thema gibt es schon oder der Name ist leer.",
              "warn")
    else:
        flash(request, "Thema angelegt.")
    return _zurueck("/themen")


# ==========================================================================
# Fragerunden
# ==========================================================================

@app.post("/themen/{topic_id}/pruefen")
def quiz_starten(request: Request, topic_id: int, modus: str = Form("bildschirm")):
    try:
        quiz_id = quizzes.anfordern(topic_id, anlass="evaluation", modus=modus)
    except QuizError as exc:
        flash(request, str(exc), "err")
        return _zurueck("/themen")
    flash(request, "Die Fragen werden erstellt.")
    return _zurueck(f"/quiz/{quiz_id}")


@app.get("/quiz/{quiz_id}", response_class=HTMLResponse)
def quiz_seite(request: Request, quiz_id: int):
    quiz = quizzes.holen(quiz_id)
    if quiz is None:
        flash(request, "Fragerunde nicht gefunden.", "err")
        return _zurueck("/")
    return render(request, "quiz.html", quiz=quiz, counts=jobs.counts())


@app.post("/quiz/{quiz_id}/antworten")
async def quiz_antworten(request: Request, quiz_id: int):
    formular = await request.form()
    antworten: dict[int, str] = {}
    for schluessel in formular.keys():
        if not schluessel.startswith("antwort_"):
            continue
        roh = schluessel[8:]
        if roh.isdigit():
            antworten[int(roh)] = str(formular.get(schluessel) or "")
    try:
        n = quizzes.antworten_speichern(quiz_id, antworten)
    except QuizError as exc:
        flash(request, str(exc), "err")
        return _zurueck(f"/quiz/{quiz_id}")
    flash(request, f"{n} Antworten aufgenommen. Die Auswertung läuft.")
    return _zurueck(f"/quiz/{quiz_id}")


@app.post("/quiz/{quiz_id}/blatt")
async def quiz_blatt(request: Request, quiz_id: int,
                     datei: UploadFile | None = None):
    formular = await request.form()
    datei = datei or formular.get("datei")
    if datei is None or not getattr(datei, "filename", ""):
        flash(request, "Es wurde keine Datei ausgewählt.", "err")
        return _zurueck(f"/quiz/{quiz_id}")

    endung = Path(datei.filename).suffix.lower()
    try:
        daten = await _datei_lesen(datei)
    except ValueError:
        flash(request, f"Die Datei ist größer als "
                       f"{MAX_UPLOAD_BYTES // 1_048_576} MB.", "err")
        return _zurueck(f"/quiz/{quiz_id}")

    try:
        await run_in_threadpool(quizzes.blatt_hochladen, quiz_id, daten, endung)
    except (QuizError, ingest.IngestError) as exc:
        flash(request, str(exc), "err")
        return _zurueck(f"/quiz/{quiz_id}")

    flash(request, "Antwortblatt aufgenommen. Karo liest es jetzt ab.")
    return _zurueck(f"/quiz/{quiz_id}")


@app.get("/quiz/{quiz_id}/drucken", response_class=HTMLResponse)
def quiz_drucken(quiz_id: int, loesungen: str = ""):
    from .media import sheets

    quiz = quizzes.holen(quiz_id)
    if quiz is None:
        return HTMLResponse("<p>Nicht gefunden.</p>", status_code=404)
    titel = (quiz["thema"] or {}).get("label", "Übung")
    if loesungen == "ja":
        return HTMLResponse(sheets.loesungsblatt(titel, quiz["fragen"]))
    return HTMLResponse(sheets.aufgabenblatt(titel, quiz["fragen"]))


@app.post("/quiz/{quiz_id}/freigabe")
async def quiz_freigabe(request: Request, quiz_id: int):
    formular = await request.form()
    frage_ids = [int(v) for v in formular.getlist("frage_id")
                 if str(v).isdigit()]
    entscheidungen = []
    for frage_id in frage_ids:
        urteil = formular.get(f"urteil_{frage_id}")
        if urteil is None:
            continue
        vorschlag = formular.get(f"v_urteil_{frage_id}", "")
        fehler = formular.get(f"fehler_{frage_id}") or None
        v_fehler = formular.get(f"v_fehler_{frage_id}") or None
        call_roh = str(formular.get(f"call_{frage_id}") or "")
        entscheidungen.append({
            "frage_id": frage_id,
            "skip": urteil == "skip",
            "richtig": urteil == "ja",
            "fehlertyp": None if urteil == "ja" else fehler,
            "begruendung": formular.get(f"grund_{frage_id}", "")[:1000],
            "konfidenz": None,
            "llm_call_id": int(call_roh) if call_roh.isdigit() else None,
            "geaendert": urteil != vorschlag or fehler != v_fehler,
        })

    try:
        ergebnis = quizzes.freigeben(quiz_id, entscheidungen)
    except QuizError as exc:
        flash(request, str(exc), "err")
        return _zurueck(f"/quiz/{quiz_id}")

    if ergebnis["bereits"]:
        flash(request, "Diese Fragerunde war bereits freigegeben.", "warn")
        return _zurueck("/themen")

    await run_in_threadpool(export.nach_freigabe)

    n = ergebnis["geschrieben"]
    meldung = f"{n} Antwort bewertet" if n == 1 else f"{n} Antworten bewertet"
    if ergebnis["uebersprungen"]:
        meldung += f", {ergebnis['uebersprungen']} übersprungen"

    # Kam die Runde aus einer Lerneinheit, entscheidet der Zyklus weiter.
    if ergebnis.get("lesson_id") and ergebnis.get("anlass") == "lernrunde":
        weiter = teaching.nach_freigabe(ergebnis["lesson_id"],
                                        ergebnis["topic_id"],
                                        auto_weiter=False)
        flash(request, f"{meldung}. {weiter['grund']}",
              "ok" if weiter.get("erfolg") or weiter.get("weiter") else "warn")
        return _zurueck(f"/lernen/{ergebnis['lesson_id']}")

    thema = topics.get(ergebnis["topic_id"])
    flagge = (thema or {}).get("flag")
    if flagge in (Flag.ROT.value, Flag.GELB.value):
        flash(request, f"{meldung}. Flagge: {FLAG_LABELS.get(flagge)} — "
                       "eine Lerneinheit wäre jetzt sinnvoll.", "warn")
    else:
        flash(request, f"{meldung}. Flagge: {FLAG_LABELS.get(flagge, '–')}.")
    return _zurueck("/themen")


# ==========================================================================
# Lerneinheiten
# ==========================================================================

@app.post("/themen/{topic_id}/lernen")
def lernen_starten(request: Request, topic_id: int, ausgabe: str = Form("html")):
    try:
        lesson_id = teaching.starten(topic_id, ausgabe)
    except TeachingError as exc:
        flash(request, str(exc), "err")
        return _zurueck("/themen")
    flash(request, "Bevor Karo schreibt: soll auch im Netz nach bekannten "
                   "Lernquellen gesucht werden?")
    return _zurueck(f"/lernen/{lesson_id}")


@app.get("/lernen/{lesson_id}", response_class=HTMLResponse)
def lernen_seite(request: Request, lesson_id: int):
    lesson = teaching.holen(lesson_id)
    if lesson is None:
        flash(request, "Lerneinheit nicht gefunden.", "err")
        return _zurueck("/themen")
    thema = lesson.get("thema") or {}
    hat_material = bool(
        kb.lehrmaterial(lesson["topic_id"], thema.get("label", ""), limit=1)
        or research.material_fuer(lesson["topic_id"]))
    return render(request, "lernen.html", lesson=lesson, counts=jobs.counts(),
                  funde=research.freigegebene(lesson["topic_id"]),
                  vorschlaege=research.vorschlaege(lesson["topic_id"]),
                  recherche_erlaubt=config.load_safe().recherche_erlaubt,
                  hat_material=hat_material)


@app.post("/lernen/{lesson_id}/fragen")
def lernen_fragen(request: Request, lesson_id: int,
                  modus: str = Form("bildschirm")):
    try:
        quiz_id = teaching.fragen_anfordern(lesson_id, modus)
    except (TeachingError, QuizError) as exc:
        flash(request, str(exc), "err")
        return _zurueck(f"/lernen/{lesson_id}")
    flash(request, "Die Verständnisfragen werden erstellt.")
    return _zurueck(f"/quiz/{quiz_id}")


@app.post("/lernen/{lesson_id}/abbrechen")
def lernen_abbrechen(request: Request, lesson_id: int):
    teaching.abbrechen(lesson_id, "von Hand beendet")
    flash(request, "Lerneinheit beendet. Ein noch laufender Vorgang stoppt "
                   "innerhalb weniger Sekunden.")
    return _zurueck("/themen")


@app.post("/lernen/{lesson_id}/runde/weiter")
def lernen_naechste_runde(request: Request, lesson_id: int):
    try:
        teaching.naechste_runde_bestaetigen(lesson_id)
    except TeachingError as exc:
        flash(request, str(exc), "err")
    return _zurueck(f"/lernen/{lesson_id}")


@app.post("/lernen/{lesson_id}/forschen")
def lernen_forschen(request: Request, lesson_id: int):
    try:
        ok = teaching.forschung_anfordern(lesson_id)
    except TeachingError as exc:
        flash(request, str(exc), "err")
        return _zurueck(f"/lernen/{lesson_id}")
    if ok:
        flash(request, "Karo sucht auf den zugelassenen Seiten. Diese Seite "
                       "in ein bis zwei Minuten neu laden.")
    else:
        flash(request, "Die Recherche ist ausgeschaltet oder läuft schon "
                       "für heute.", "warn")
    return _zurueck(f"/lernen/{lesson_id}")


@app.post("/lernen/{lesson_id}/runde/{round_id}/variante")
def lernen_variante(request: Request, lesson_id: int, round_id: int,
                    wunsch: str = Form(""), ausgabe: str = Form("")):
    try:
        teaching.variante_anfordern(round_id, wunsch, ausgabe or None)
    except TeachingError as exc:
        flash(request, str(exc), "err")
    else:
        flash(request, "Karo erzeugt eine weitere Version — das dauert etwas.")
    return _zurueck(f"/lernen/{lesson_id}")


def _material_antwort(
        pfad_text: str | None) -> HTMLResponse | PlainTextResponse | FileResponse:
    """Liefert eine Material- oder Variantendatei aus.

    Der Pfad kommt aus der Datenbank, nicht aus der Anfrage — deshalb kann
    hier kein fremder Pfad untergeschoben werden.
    """
    if not pfad_text:
        return HTMLResponse("<p>Noch kein Material vorhanden.</p>",
                            status_code=404)
    pfad = Path(pfad_text)
    if not pfad.is_file():
        return HTMLResponse("<p>Die Datei ist nicht mehr da.</p>",
                            status_code=404)
    if pfad.suffix.lower() == ".mp4":
        return FileResponse(pfad, media_type="video/mp4", filename=pfad.name)
    if pfad.suffix.lower() == ".txt":
        # Als Klartext, nicht als HTMLResponse: der Text enthält Sprechtext
        # aus einer Erklärung und könnte zufällig "<" oder "&" enthalten,
        # was als HTMLResponse falsch dargestellt würde.
        return PlainTextResponse(pfad.read_text(encoding="utf-8"))
    return HTMLResponse(pfad.read_text(encoding="utf-8"))


@app.get("/material/{round_id}", response_class=HTMLResponse)
def material(round_id: int):
    runde = db.q1("SELECT material_pfad FROM lesson_round WHERE id = ?", round_id)
    return _material_antwort(runde["material_pfad"] if runde else None)


@app.get("/material/{round_id}/notebooklm-quelle", response_class=PlainTextResponse)
def material_notebooklm_quelle(round_id: int):
    runde = db.q1(
        "SELECT notebooklm_quelle_pfad FROM lesson_round WHERE id = ?", round_id)
    return _material_antwort(runde["notebooklm_quelle_pfad"] if runde else None)


@app.get("/material/variante/{variant_id}", response_class=HTMLResponse)
def material_variante(variant_id: int):
    v = db.q1("SELECT material_pfad FROM lesson_round_variant WHERE id = ?",
             variant_id)
    return _material_antwort(v["material_pfad"] if v else None)


@app.get("/material/variante/{variant_id}/notebooklm-quelle",
         response_class=PlainTextResponse)
def material_variante_notebooklm_quelle(variant_id: int):
    v = db.q1(
        "SELECT notebooklm_quelle_pfad FROM lesson_round_variant WHERE id = ?",
        variant_id)
    return _material_antwort(v["notebooklm_quelle_pfad"] if v else None)


# ==========================================================================
# Recherche
# ==========================================================================

@app.get("/recherche", response_class=HTMLResponse)
def recherche(request: Request):
    return render(request, "recherche.html",
                  vorschlaege=research.vorschlaege(),
                  erlaubte=sorted(set(research.ERLAUBTE_QUELLEN.values())),
                  kanaele=research.ERLAUBTE_KANAELE,
                  aktiv=config.load_safe().recherche_erlaubt)


_ZUEL_ZURUECK = re.compile(r"^/lernen/\d+$")


@app.post("/recherche/entscheiden")
async def recherche_entscheiden(request: Request):
    formular = await request.form()
    entscheidungen: dict[int, str] = {}
    for schluessel in formular.keys():
        if not schluessel.startswith("hit_"):
            continue
        roh = schluessel[4:]
        if roh.isdigit():
            entscheidungen[int(roh)] = str(formular.get(schluessel) or "")
    ergebnis = research.entscheiden(entscheidungen)
    flash(request, f"{ergebnis['freigegeben']} freigegeben, "
                   f"{ergebnis['abgelehnt']} abgelehnt.")
    # Von der Lerneinheit aus aufgerufen: dorthin zurück, nicht zur
    # allgemeinen Recherche-Seite. `zurueck` ist Nutzereingabe — nur ein
    # exakt passender eigener Pfad wird akzeptiert, sonst der übliche Weg.
    ziel = str(formular.get("zurueck") or "")
    if _ZUEL_ZURUECK.match(ziel):
        return _zurueck(ziel)
    return _zurueck("/recherche")


@app.post("/themen/{topic_id}/recherche")
def recherche_starten(request: Request, topic_id: int):
    if research.anfordern(topic_id):
        flash(request, "Karo sucht auf den zugelassenen Seiten.")
    else:
        flash(request, "Die Recherche ist ausgeschaltet oder läuft schon.",
              "warn")
    return _zurueck("/recherche")


# ==========================================================================
# Klassenarbeit
# ==========================================================================

@app.get("/klassenarbeit", response_class=HTMLResponse)
def klassenarbeit(request: Request):
    zeilen = [dict(r) for r in db.q(
        "SELECT * FROM exam ORDER BY exam_date DESC LIMIT 20")]
    for e in zeilen:
        try:
            e["themen_liste"] = json.loads(e["themen"] or "[]")
        except json.JSONDecodeError:
            e["themen_liste"] = []
        e["kalibrierung"] = _kalibrierung(e["id"])
    return render(request, "klassenarbeit.html", zeilen=zeilen)


def _kalibrierung(exam_id: int) -> dict:
    zeilen = [dict(r) for r in db.q(
        """SELECT p.topic_id, p.prognose, p.tatsaechlich, t.label, t.code
             FROM prediction p JOIN topic t ON t.id = p.topic_id
            WHERE p.exam_id=? ORDER BY t.sort""", exam_id)]
    bewertet = [z for z in zeilen if z["tatsaechlich"]]
    treffer = sum(1 for z in bewertet if z["prognose"] == z["tatsaechlich"])
    return {"zeilen": zeilen, "bewertet": len(bewertet), "treffer": treffer,
            "quote": round(treffer / len(bewertet), 2) if bewertet else None}


@app.post("/klassenarbeit")
def klassenarbeit_neu(request: Request, exam_date: str = Form(...),
                      themen: str = Form("")):
    try:
        dt.date.fromisoformat(exam_date)
    except ValueError:
        flash(request, "Ungültiges Datum.", "err")
        return _zurueck("/klassenarbeit")
    liste = [t.strip()[:120] for t in themen.split(",") if t.strip()][:20]
    cfg = config.load_safe()
    with db.tx() as c:
        cur = c.execute(
            "INSERT INTO exam (subject, exam_date, themen, created_at) "
            "VALUES (?,?,?,?)",
            (cfg.subject, exam_date, json.dumps(liste, ensure_ascii=False),
             db.now()))
        exam_id = cur.lastrowid
        n = 0
        for t in topics.liste(topics.AKTIV):
            if t["flag"] == Flag.WEISS.value:
                continue
            cur2 = c.execute(
                """INSERT INTO prediction (exam_id, topic_id, prognose, frozen_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(exam_id, topic_id) DO NOTHING""",
                (exam_id, t["id"], t["flag"], db.now()))
            n += cur2.rowcount
    flash(request, f"Prognose für {n} Themen eingefroren.")
    return _zurueck("/klassenarbeit")


@app.post("/klassenarbeit/{exam_id}/ergebnis")
async def klassenarbeit_ergebnis(request: Request, exam_id: int):
    formular = await request.form()
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
    flash(request, f"{n} Ergebnis eingetragen." if n == 1
          else f"{n} Ergebnisse eingetragen.")
    return _zurueck("/klassenarbeit")


# ==========================================================================
# Protokoll
# ==========================================================================

@app.get("/protokoll", response_class=HTMLResponse)
def protokoll(request: Request):
    zeilen = [dict(r) for r in db.q(
        """SELECT id, purpose, backend, model, had_image, schema_ok, error,
                  tokens_in, tokens_out, cost_usd, duration_ms, created_at
             FROM llm_call ORDER BY id DESC LIMIT 120""")]
    gesamt = dict(db.q1(
        "SELECT COUNT(*) AS n, COALESCE(SUM(cost_usd),0) AS c FROM llm_call"))
    monat = dict(db.q1(
        "SELECT COUNT(*) AS n, COALESCE(SUM(cost_usd),0) AS c FROM llm_call "
        "WHERE created_at >= ?", dt.date.today().replace(day=1).isoformat()))
    return render(request, "protokoll.html", zeilen=zeilen, gesamt=gesamt,
                  monat=monat, backend=config.load_safe().llm_backend)


@app.get("/protokoll/{call_id}", response_class=HTMLResponse)
def protokoll_detail(request: Request, call_id: int):
    zeile = db.q1("SELECT * FROM llm_call WHERE id = ?", call_id)
    if zeile is None:
        return HTMLResponse("<p>Nicht gefunden.</p>", status_code=404)
    return render(request, "protokoll_detail.html", zeile=dict(zeile))


@app.post("/vorgang/{job_id}/erneut")
def vorgang_erneut(request: Request, job_id: int):
    if jobs.retry(job_id):
        flash(request, "Vorgang wird erneut versucht.")
    else:
        flash(request, "Dieser Vorgang läuft bereits oder ist abgeschlossen.",
              "warn")
    return _zurueck("/")


@app.post("/export")
async def export_jetzt(request: Request):
    pfad = await run_in_threadpool(export.nach_freigabe)
    if pfad:
        flash(request, f"Lernstand als Tabelle geschrieben: "
                       f"{Path(pfad).name}")
    else:
        flash(request, "Der Tabellenexport ist nicht verfügbar "
                       "(openpyxl fehlt oder kein Drive-Ordner).", "warn")
    return _zurueck("/")
