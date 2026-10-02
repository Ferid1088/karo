"""Der Vertrag zum KI-Anbieter.

Alles oberhalb dieser Datei kennt nur `complete(...)` und bekommt entweder ein
schemakonformes Objekt, eine `AIPending` (der Anbieter arbeitet noch — der
Job wird zurückgestellt) oder eine Ausnahme mit einer Meldung, die man einer
Person zeigen kann.

Hier geht **Text** hin und sonst nichts. Es gab einmal einen `image_path`:
damit gingen Fotos von Schulblaettern und handschriftlich bearbeiteten
Fragebogen an ein Modell — mit allem, was zufaellig mit drauf war, vom Namen
in der Kopfzeile bis zum Kinderzimmer im Hintergrund. Ein Bild laesst sich
nicht saeubern wie ein Text, und was einmal draussen ist, kommt nicht zurueck.
Deshalb gibt es diesen Weg nicht mehr, und deshalb hat diese Schnittstelle
keinen Bildparameter: eine Regel, die sich nicht umgehen laesst, ist besser
als eine, an die sich alle erinnern muessen. Bilder werden auf dem
Geraet gelesen (siehe docs/Karo_Prompts_Schritt_fuer_Schritt.MD, Schritt 2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

_RATE = re.compile(r"(rate.?limit|429|too many requests|usage limit|quota|overloaded|529|"
                   r"limit reached|resets? at|credit balance)", re.I)
_TRANSIENT = re.compile(r"(timeout|timed out|connection|temporar|502|503|504|500|"
                        r"internal server|service unavailable|reset by peer|EOF)", re.I)


class AIError(Exception):
    """Basisklasse. Die Meldung ist immer deutsch und fuer Menschen lesbar.

    `retryable`/`rate_limited`/`retry_after` ordnen den Fehler fuer den
    Job-Worker ein: permanente Fehler duerfen nicht erneut versucht werden,
    voruebergehende schon.
    """

    def __init__(self, msg: str, *, retryable: bool | None = None,
                 rate_limited: bool | None = None,
                 retry_after: float | None = None):
        super().__init__(msg)
        self.rate_limited = (bool(_RATE.search(msg))
                             if rate_limited is None else rate_limited)
        self.retryable = ((self.rate_limited or bool(_TRANSIENT.search(msg)))
                          if retryable is None else retryable)
        self.retry_after = retry_after


class AIAuthError(AIError):
    """Zugangsdaten fehlen oder sind ungueltig. Niemals erneut versuchen."""

    def __init__(self, msg: str, **kw):
        super().__init__(msg, retryable=False, **kw)


class AIConnectionError(AIError):
    """Netzwerk, Zeitueberschreitung, Ueberlastung, Ratenbegrenzung."""


class AISchemaError(AIError):
    """Antwort kam an, war aber unvollstaendig oder passte nicht zum Schema."""


class AISetupError(AIError):
    """Der Anbieter selbst ist nicht einsatzbereit (z. B. Schluessel fehlt)."""

    def __init__(self, msg: str, **kw):
        super().__init__(msg, retryable=False, **kw)


class AIPending(Exception):
    """Der Anbieter arbeitet noch — der Auftrag wird zurückgestellt, nicht wiederholt.

    Devin ist asynchron: `POST /v1/sessions` liefert sofort eine Kennung,
    das Ergebnis kommt erst Minuten später. Diese Ausnahme ist kein Fehler:
    sie verbraucht keinen Auftragsversuch, sondern sagt dem Worker „lege den
    Auftrag zurück und frag mich in `wait_seconds` wieder". Beim nächsten
    Lauf findet derselbe Aufruf seine Session über den gespeicherten
    Fingerabdruck wieder.
    """

    def __init__(self, msg: str, *, wait_seconds: float | None = None,
                 session_id: str | None = None):
        super().__init__(msg)
        self.wait_seconds = wait_seconds
        self.session_id = session_id


@dataclass(frozen=True)
class RawResult:
    """Was ein Backend zurueckgibt, bevor protokolliert und geprueft wird."""

    data: dict[str, Any]
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float | None = None
    truncated: bool = False


class Backend(Protocol):
    """Ein Weg zum Anbieter. Genau eine Implementierung: `devin.py`."""

    name: str

    def verify(self) -> str:
        """Testet die Zugangsdaten mit einem billigen Abruf. Gibt den Anbieter zurück."""

    def call(
        self,
        prompt: str,
        schema: dict,
        *,
        model: str,
        system: str = "",
        max_tokens: int = 8192,
        web_search: bool = False,
        web_fetch: bool = False,
        purpose: str = "",
    ) -> RawResult:
        """Ein Aufruf mit erzwungener Antwortstruktur.

        Kann `AIPending` werfen: der asynchrone Anbieter hat eine Session
        angelegt oder sie laeuft noch — der Aufrufer (Job-Worker) stellt den
        Auftrag zurück und ruft spaeter erneut.

        `web_search`/`web_fetch`: Hinweis an den Anbieter, dass der Auftrag
        aus dem Netz antworten darf bzw. eine konkrete, freigegebene Quelle
        abrufen soll (`research.py`). Ob die Session das Netz nutzt,
        entscheidet der Anbieter.
        """
