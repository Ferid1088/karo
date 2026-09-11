"""Konfiguration und Zugangsdaten.

Grundsatz: Zugangsdaten leben ausschliesslich in /data/config.json auf dem
Rechner der Kaeuferin oder des Kaeufers. Sie stehen nie im Image, nie im
Quellcode, nie in Git, nie in Logs, und sie werden an keinen Server des
Herstellers uebertragen.

Zweiter Grundsatz: eine unlesbare Konfiguration ist ein Fehler, kein Anlass,
zu Standardwerten zurueckzufallen. Sonst kostet ein voruebergehender Lesefehler
das Passwort und alle Einstellungen.
"""

from __future__ import annotations

import json
import os
import secrets
import tempfile
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

DATA_DIR = Path(os.environ.get("KARO_DATA_DIR", "/data"))
DRIVE_DIR = Path(os.environ.get("KARO_DRIVE_DIR", "/drive"))
CONFIG_PATH = DATA_DIR / "config.json"
_SESSION_SECRET_PATH = DATA_DIR / "session.key"

SECRET_FIELDS = ("anthropic_api_key", "claude_oauth_token",
                 "app_password_hash", "app_password_salt")

RESEARCH_SOURCE_DEFAULTS = [
    {"domain": "studyflix.de", "label": "Studyflix"},
    {"domain": "simpleclub.com", "label": "simpleclub"},
    {"domain": "serlo.org", "label": "Serlo"},
    {"domain": "mathe-lerntipps.de", "label": "Mathe-Lerntipps"},
    {"domain": "bettermarks.com", "label": "bettermarks"},
    {"domain": "schlaukopf.de", "label": "Schlaukopf"},
    {"domain": "grundschulkoenig.de", "label": "Grundschulkönig"},
    {"domain": "planet-schule.de", "label": "Planet Schule"},
    {"domain": "br.de", "label": "BR (alpha Lernen)"},
    {"domain": "youtube.com", "label": "YouTube (nur die Kanäle unten)"},
]


class ConfigUnreadable(RuntimeError):
    """Die Datei ist da, laesst sich aber nicht lesen oder ist beschaedigt."""


@dataclass(frozen=True)
class Config:
    # --- Welcher Weg zum Modell -------------------------------------------
    llm_backend: str = "abo"        # 'abo' (20-€-Abo) oder 'api' (Schlüssel)

    # --- Zugangsdaten (geheim) --------------------------------------------
    claude_oauth_token: str = ""    # aus `claude setup-token`
    anthropic_api_key: str = ""

    # --- Zugang zur App ---------------------------------------------------
    app_password_hash: str = ""
    app_password_salt: str = ""

    # --- Lernende Person ---------------------------------------------------
    learner_name: str = ""          # bleibt lokal, dient dem Schwärzen
    learner_grade: int = 7
    subject: str = "Mathematik"

    # --- Modellwahl --------------------------------------------------------
    model_vision: str = ""
    model_text: str = ""

    # --- Ausgabe des Lernmaterials ----------------------------------------
    default_ausgabe: str = "html"   # html | mp4 | notebooklm
    tts_stimme: str = "de_DE-thorsten-medium"
    max_lernrunden: int = 4

    # --- Recherche ---------------------------------------------------------
    recherche_erlaubt: bool = True
    recherche_freigabe_pflicht: bool = True
    recherche_quellen: list = field(
        default_factory=lambda: [dict(q) for q in RESEARCH_SOURCE_DEFAULTS])

    # --- Ablage ------------------------------------------------------------
    drive_subdir: str = ""
    header_crop_percent: int = 8

    # --- Regel für die Flaggen --------------------------------------------
    rule_gruen_richtige: int = 3
    rule_gruen_tage: int = 2
    rule_rot_konzeptfehler: int = 2
    rule_fenster: int = 5
    rule_min_evidenz: int = 2

    setup_complete: bool = False

    def __repr__(self) -> str:  # pragma: no cover
        safe = {k: v for k, v in asdict(self).items() if k not in SECRET_FIELDS}
        safe["zugangsdaten"] = "<gesetzt>" if self.has_credentials else "<leer>"
        return f"Config({safe})"

    __str__ = __repr__

    @property
    def has_credentials(self) -> bool:
        if self.llm_backend == "abo":
            return bool(self.claude_oauth_token)
        return bool(self.anthropic_api_key)

    def public_dict(self) -> dict:
        """Alles, was gefahrlos in ein Template oder ins Protokoll darf."""
        d = {k: v for k, v in asdict(self).items() if k not in SECRET_FIELDS}
        d["has_credentials"] = self.has_credentials
        d["has_password"] = bool(self.app_password_hash)
        return d


_KNOWN = set(Config.__dataclass_fields__)


def _atomic_write(path: Path, payload: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load() -> Config:
    """Laedt die Konfiguration.

    Fehlt die Datei, ist das der Normalzustand vor der Einrichtung. Ist sie da,
    aber unlesbar, wird eine Ausnahme geworfen — nicht stillschweigend auf
    Standardwerte zurueckgefallen.
    """
    if not CONFIG_PATH.exists():
        return Config()
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigUnreadable(
            f"/data/config.json ist beschädigt (Zeile {exc.lineno}). Bitte aus "
            "einer Sicherung wiederherstellen oder die Datei löschen, um die "
            "Einrichtung neu zu starten.") from None
    except UnicodeDecodeError:
        raise ConfigUnreadable(
            "/data/config.json ist nicht als Text lesbar (beschädigte Datei). "
            "Bitte aus einer Sicherung wiederherstellen oder die Datei löschen."
        ) from None
    except OSError as exc:
        raise ConfigUnreadable(
            f"/data/config.json ist nicht lesbar: {exc.strerror}.") from None
    if not isinstance(raw, dict):
        raise ConfigUnreadable("/data/config.json enthält kein Objekt.")
    return Config(**{k: v for k, v in raw.items() if k in _KNOWN})


def load_safe() -> Config:
    """Wie load(), faellt bei Fehlern aber auf Standardwerte zurueck.

    Nur fuer Stellen, die nicht scheitern duerfen — etwa die Fehlerseite selbst.
    Niemals als Grundlage fuer ein save().
    """
    try:
        return load()
    except ConfigUnreadable:
        return Config()


def save(cfg: Config) -> None:
    _atomic_write(CONFIG_PATH, json.dumps(asdict(cfg), indent=2, ensure_ascii=False))


def update(**changes) -> Config:
    """Aendert einzelne Felder. Wirft, wenn die bestehende Datei unlesbar ist —
    sonst fielen alle nicht uebergebenen Felder auf Standardwerte."""
    unbekannt = set(changes) - _KNOWN
    if unbekannt:
        raise ValueError(f"Unbekannte Konfigurationsfelder: {sorted(unbekannt)}")
    cfg = replace(load(), **changes)
    save(cfg)
    return cfg


SESSION_SECRET_BYTES = 32


def session_secret() -> bytes:
    """Stabiler Schluessel fuer signierte Cookies, ueber Neustarts hinweg.

    O_EXCL auf der Zieldatei: genau ein Prozess gewinnt, alle anderen lesen
    anschliessend genau diesen Schluessel. Mit einer temporaeren Datei plus
    os.replace koennten zwei Prozesse verschiedene Schluessel benutzen und
    sich die Sitzungen gegenseitig entwerten. Eine zu kurze Datei gilt nie als
    Schluessel — ein leerer Signaturschluessel wuerde akzeptiert und jede
    Sitzung waere faelschbar.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for _ in range(3):
        try:
            vorhanden = _SESSION_SECRET_PATH.read_bytes()
        except OSError:
            vorhanden = b""
        if len(vorhanden) >= SESSION_SECRET_BYTES:
            return vorhanden
        if _SESSION_SECRET_PATH.exists():
            try:
                _SESSION_SECRET_PATH.unlink()
            except OSError:
                pass
        try:
            fd = os.open(str(_SESSION_SECRET_PATH),
                         os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        with os.fdopen(fd, "wb") as fh:
            fh.write(secrets.token_bytes(SESSION_SECRET_BYTES))
            fh.flush()
            os.fsync(fh.fileno())
        return _SESSION_SECRET_PATH.read_bytes()
    raise RuntimeError("Sitzungsschlüssel konnte nicht angelegt werden.")


# --------------------------------------------------------------------------
# Verzeichnisse
# --------------------------------------------------------------------------

def _ensure(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def scans_dir() -> Path:
    return _ensure(DATA_DIR / "scans")


def local_inbox() -> Path:
    """Ersatz-Eingang, wenn kein Drive-Ordner eingehaengt ist."""
    return _ensure(DATA_DIR / "eingang")


def media_dir() -> Path:
    """Erzeugtes Lernmaterial, bevor es in Drive kopiert wird."""
    return _ensure(DATA_DIR / "material")


def voices_dir() -> Path:
    """Sprachdateien fuer die MP4-Ausgabe."""
    return _ensure(DATA_DIR / "stimmen")


def drive_root() -> Path:
    sub = load_safe().drive_subdir
    return DRIVE_DIR / sub if sub else DRIVE_DIR
