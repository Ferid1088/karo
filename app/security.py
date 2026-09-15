"""Zugangsschutz, CSRF-Abwehr und Schwaerzung von Geheimnissen im Protokoll.

Der API-Schluessel darf unter keinen Umstaenden in einer Logdatei landen.
Die Schwaerzung sitzt deshalb nicht in einem Filter, sondern im Formatter:
ein Filter sieht `record.msg`, aber nicht den Traceback, den der Formatter
anschliessend anhaengt — und genau dort taucht ein Schluessel auf, wenn eine
HTTP-Bibliothek ihn in eine Fehlermeldung schreibt.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
from urllib.parse import urlsplit

# --- Uploads ---------------------------------------------------------------

#: Einzige Quelle der Wahrheit fuer die Obergrenze eines Datei-Uploads —
#: vorher als Literal `25 * 1024 * 1024` in admin.py, services/workflow.py
#: und services/preparation.py dupliziert, und in main.py als eigene,
#: nie referenzierte Konstante (change.txt Abschnitt 9/13).
MAX_UPLOAD_BYTES = 25 * 1024 * 1024

# --- Passwort ------------------------------------------------------------

_ITERATIONS = 240_000
MIN_PASSWORD_LENGTH = 8


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS
    )
    return dk.hex(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    if not (password and stored_hash and salt):
        return False
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, stored_hash)


# --- CSRF ----------------------------------------------------------------

CSRF_FIELD = "_csrf"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_ok(session_token, submitted) -> bool:
    """Vergleicht den Token. Alles, was kein einfacher ASCII-Text ist, faellt
    durch — compare_digest wuerde sonst eine Ausnahme werfen und die Pruefung
    damit in einen Serverfehler statt in eine Ablehnung laufen lassen."""
    if not isinstance(session_token, str) or not isinstance(submitted, str):
        return False
    if not session_token or not submitted:
        return False
    if not (session_token.isascii() and submitted.isascii()):
        return False
    return hmac.compare_digest(session_token, submitted)


def same_origin(request_headers, host: str) -> bool:
    """Prueft Origin bzw. Referer gegen den eigenen Host.

    Zusammen mit dem Token die zweite Sperre gegen fremde Seiten, die im selben
    Browser ein Formular an 127.0.0.1 abschicken.
    """
    fetch_site = request_headers.get("sec-fetch-site")
    if fetch_site in ("same-origin", "none"):
        return True
    if fetch_site in ("cross-site", "same-site"):
        return False

    origin = request_headers.get("origin")
    if origin:
        return origin.split("://")[-1].rstrip("/") == host
    referer = request_headers.get("referer")
    if referer:
        return referer.split("://")[-1].split("/")[0] == host
    # Weder Sec-Fetch-Site noch Origin noch Referer: alter Browser oder curl.
    # Der Token entscheidet dann allein.
    return True


def eigene_seite(referer: str | None, host: str) -> str | None:
    """Pfad (inkl. Query) der aufrufenden Seite, wenn sie zur eigenen App
    gehoert — damit ein Formular zur aktuellen Seite zurueckkehren kann
    (Refresh), statt immer auf eine feste Uebersicht zu springen."""
    if not referer:
        return None
    teile = urlsplit(referer)
    if teile.netloc and teile.netloc != host:
        return None
    pfad = teile.path or "/"
    return f"{pfad}?{teile.query}" if teile.query else pfad


# --- Schwaerzung ----------------------------------------------------------

REDACTED = "***redigiert***"

_PATTERNS = [
    # Anthropic
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"),
    # OpenAI-artige und generische lange Schluessel
    re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}"),
    # AWS und Google, fuer den Fall eines spaeteren Anbieterwechsels
    re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bya29\.[A-Za-z0-9_\-]{10,}"),
    # Header und Zuweisungen
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}"),
    re.compile(r"(?i)\b(api[_-]?key|apikey|authorization|x-api-key|auth[_-]?token|"
               r"secret|password|passwort)\b\s*[:=]\s*[\"']?[^\s\"',;]{6,}"),
    # Alles, was wie ein sehr langes undurchsichtiges Token aussieht
    re.compile(r"\b[A-Za-z0-9_\-]{12,}-[A-Za-z0-9_\-]{24,}\b"),
]


def redact(text: str) -> str:
    if not text:
        return text or ""
    out = str(text)
    for pattern in _PATTERNS:
        out = pattern.sub(REDACTED, out)
    return out


class RedactingFormatter(logging.Formatter):
    """Schwaerzt die fertige Zeile — einschliesslich Traceback und Stack."""

    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s  %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Ersetzt jede Formatter-Instanz durch die schwaerzende Variante.

    Deckt auch die Handler ab, die uvicorn ueber dictConfig anlegt, und wird
    beim Start nach dem Aufbau von uvicorn erneut aufgerufen.
    """
    fmt = RedactingFormatter(LOG_FORMAT)

    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        root.addHandler(handler)
    root.setLevel(level.upper())

    seen: set[int] = set()
    for name in [None] + list(logging.root.manager.loggerDict.keys()):
        logger = logging.getLogger(name) if name else root
        if not isinstance(logger, logging.Logger):
            continue
        for handler in logger.handlers:
            if id(handler) in seen:
                continue
            seen.add(id(handler))
            handler.setFormatter(fmt)


def selftest_redaction() -> bool:
    """Wird beim Start ausgefuehrt. Schlaegt sie fehl, startet die App nicht."""
    probe = "x sk-ant-api03-AAAABBBBCCCCDDDD y"
    return "sk-ant" not in redact(probe)
