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

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_303_SEE_OTHER

from . import config, db, jobs, security
from .config import ConfigUnreadable
from .routers import auth, eltern, kind, admin, dashboard, lernzyklus

security.configure_logging(os.environ.get("KARO_LOG_LEVEL", "INFO"))
log = logging.getLogger("karo")

BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / "templates"))

try:
    ASSET_VERSION = str(max(
        (BASE / "static" / name).stat().st_mtime_ns
        for name in ("karo.css", "simple.css", "simple.js")
    ))
except OSError:
    ASSET_VERSION = "0"

PUBLIC_EXACT = frozenset({"/health", "/login", "/logout", "/setup",
                          "/setup/credentials", "/setup/finish", "/setup/reset"})
PUBLIC_PREFIX = ("/static/",)

MAX_BODY_BYTES = 30 * 1024 * 1024
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    security.configure_logging(os.environ.get("KARO_LOG_LEVEL", "INFO"))
    if not security.selftest_redaction():
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

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(lernzyklus.router)
app.include_router(eltern.router)
app.include_router(kind.router)
app.include_router(admin.router)


class Gate:
    """Einrichtungsweiche, Anmeldung und CSRF-Abwehr."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope, receive)
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
            return await self._send(send, scope, self._zu_gross())

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
                return await self._send(send, scope, self._zu_gross())
        body = bytes(body)

        probe = Request(scope, self._replay(body))
        try:
            formular = await probe.form()
            gesendet = formular.get(security.CSRF_FIELD)
        except Exception:
            gesendet = None
        finally:
            try:
                await probe.close()
            except Exception:
                pass

        if not security.csrf_ok(request.session.get("csrf"), gesendet):
            return await self._send(send, scope, HTMLResponse(
                "<h1>Abgelehnt</h1><p>Das Formular ist abgelaufen oder stammt "
                "nicht von dieser Seite.</p>", status_code=403))

        await self.app(scope, self._replay(body), send)

    @staticmethod
    async def _send(send, scope, response) -> None:
        await response(scope, Gate._replay(b""), send)

    @staticmethod
    def _zu_gross() -> HTMLResponse:
        return HTMLResponse(
            "<h1>Zu groß</h1><p>Die gesendeten Daten überschreiten "
            f"{MAX_BODY_BYTES // 1_048_576} MB.</p>", status_code=413)

    @staticmethod
    def _replay(body: bytes):
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
    https_only=False,
)
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
