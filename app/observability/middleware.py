"""ASGI-Middleware: eine ID und eine Messung pro Anfrage.

Pro Request entsteht genau eine `request_id` (aus `X-Request-Id`, wenn sie
sauber aussieht, sonst neu), die in jede Logzeile dieser Anfrage wandert —
bis in Domain- und Datenbankcode hinein. Am Ende gibt es eine Zeile
`request_completed` mit Methode, Pfad, Status und Dauer.

Ein ungefangener Fehler wird genau einmal geloggt — hier, mit Request-
Kontext — und nicht noch einmal von der ServerErrorMiddleware ohne Kontext.
Das Logging selbst darf die Anfrage nie brechen: Fehler beim Schreiben
werden geschluckt, die Antwort geht trotzdem raus.
"""

import logging
import time

from starlette.responses import HTMLResponse

from . import context

log = logging.getLogger("karo.http")

# Gesundheitspruefung und Assets jede Minute: nuetzlich, aber rauschen —
# sie bekommen ihre ID trotzdem, nur keine eigene Zeile.
_LEISE = ("/health", "/static/", "/favicon")


class RequestObservability:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        eingehend = None
        for name, wert in scope.get("headers", []):
            if name == b"x-request-id":
                eingehend = wert.decode("latin-1")
                break
        token = context.beginne(eingehend)
        rid = context.aktuell()
        start = time.monotonic()
        status = [500]
        begonnen = [False]

        async def sende(message):
            if message["type"] == "http.response.start":
                begonnen[0] = True
                status[0] = message["status"]
                message["headers"] = list(message.get("headers", [])) + [
                    (b"x-request-id", rid.encode())]
            await send(message)

        pfad = scope.get("path", "")
        methode = scope.get("method", "")
        try:
            await self.app(scope, receive, sende)
        except Exception as exc:
            self._logge(log.error, "request_failed", pfad, methode,
                        status[0], start, exc=exc)
            self._festhalten(methode, pfad, exc)
            if begonnen[0]:
                raise      # Antwort laeuft schon — nur noch melden
            try:
                await HTMLResponse(
                    "<h1>Etwas ist schiefgelaufen.</h1><p>Der Fehler wurde "
                    "festgehalten. Bitte einmal neu laden — haelt es an, "
                    "meldet die Elternansicht es.</p>",
                    status_code=500)(scope, receive, sende)
            except Exception:
                pass
        else:
            if not any(pfad.startswith(p) for p in _LEISE):
                self._logge(log.info, "request_completed", pfad, methode,
                            status[0], start)
        finally:
            context.ende(token)

    @staticmethod
    def _festhalten(methode: str, pfad: str, exc: Exception) -> None:
        """Ungefangene 500er ueberleben die Logrotation: betriebsmeldung
        dedupliziert nach Weg und Fehlertyp. Bewusst nur der Typ — die
        Fehlermeldung koennte Inhalte des Kindes enthalten."""
        try:
            from ..adaptiv.curriculum_dienst import betrieb_melden
            betrieb_melden(f"{methode} {pfad}: {type(exc).__name__}",
                           bereich="http-500")
        except Exception:
            pass

    @staticmethod
    def _logge(schreiber, event, pfad, methode, status, start, exc=None):
        """Loggen darf nie die Anfrage brechen — ein defekter Logger schweigt."""
        try:
            schreiber("%s %s -> %s", methode, pfad, status,
                      exc_info=exc, extra={"fach": {
                          "event": event, "method": methode, "path": pfad,
                          "status_code": status,
                          "duration_ms": round((time.monotonic() - start)
                                               * 1000, 1)}})
        except Exception:
            pass
