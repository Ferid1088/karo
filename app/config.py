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
from dataclasses import asdict, dataclass, field, fields, replace
from functools import cache
from pathlib import Path
from zoneinfo import ZoneInfo

DATA_DIR = Path(os.environ.get("KARO_DATA_DIR", "/data"))
DRIVE_DIR = Path(os.environ.get("KARO_DRIVE_DIR", "/drive"))
CONFIG_PATH = DATA_DIR / "config.json"
_SESSION_SECRET_PATH = DATA_DIR / "session.key"

SECRET_FIELDS = ("curriculum_key",
                 "app_password_hash", "app_password_salt",
                 "child_password_hash", "child_password_salt")

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
    # --- KI-Anbieter --------------------------------------------------------
    # Welcher Adapter in `app.ai.registry.PROVIDERS` die allgemeinen
    # KI-Aufrufe bedient — die einzige Stelle, an der die Wahl steht.
    # Der Schlüssel steht niemals in dieser Datei: er kommt ausschließlich
    # aus der Umgebungsvariablen, die der Adapter benennt (z. B.
    # DEVIN_API_KEY, siehe .env.example).
    ai_provider: str = "devin"

    # Optionaler zentraler Inhaltsdienst. Kein stiller KI-Fallback bei Ausfall.
    curriculum_url: str = ""
    curriculum_key: str = ""

    # --- Zugang zur App ---------------------------------------------------
    app_password_hash: str = ""
    app_password_salt: str = ""
    child_password_hash: str = ""   # optional: eigenes Login fuers Kind
    child_password_salt: str = ""

    # --- Lernende Person ---------------------------------------------------
    learner_name: str = ""          # bleibt lokal, dient dem Schwärzen
    learner_grade: int = 7
    subject: str = "mathematik"     # Standardfach: ein Schluessel aus faecher.FAECHER

    # --- Ausgabe des Lernmaterials ----------------------------------------
    default_ausgabe: str = "html"   # html | mp4 | notebooklm
    tts_stimme: str = "de_DE-thorsten-medium"
    max_lernrunden: int = 4
    antworten_pruefen_kind: bool = False
    schulblaetter_kind: bool = False
    klassenarbeit_kind: bool = False

    # --- Recherche ---------------------------------------------------------
    recherche_erlaubt: bool = True
    recherche_freigabe_pflicht: bool = True
    recherche_quellen: list = field(
        default_factory=lambda: [dict(q) for q in RESEARCH_SOURCE_DEFAULTS])

    # --- Ablage ------------------------------------------------------------
    drive_subdir: str = ""
    material_db_path: str = ""  # leer: DATA_DIR / lernmaterialien.sqlite3
    header_crop_percent: int = 8
    #: IANA-Zeitzone für alle Tagesgrenzen („Heute", Streaks, Fristen).
    #: KARO_TIMEZONE bzw. TZ schlagen diesen Wert (siehe zeitzone()).
    timezone: str = "Europe/Berlin"

    # --- Regel für die Flaggen --------------------------------------------
    rule_gruen_richtige: int = 3
    rule_gruen_tage: int = 2
    rule_rot_konzeptfehler: int = 2
    rule_fenster: int = 5
    rule_min_evidenz: int = 2

    # --- Alter Erzeugungsweg ----------------------------------------------
    # `/lernzyklus` → teaching.py → media/: erzeugt pro Kind und Runde ein
    # Video bzw. einen Foliensatz. Das widerspricht §11 (offline erzeugen,
    # deterministisch ausliefern) und §12 („niemals pro Kind erzeugen") und
    # wird vom adaptiven Loop abgelöst. Bis dahin bleibt der Code liegen,
    # aber unerreichbar: aus, wie jeder Schalter aus §16.
    legacy_lesson_generation_enabled: bool = False

    # --- Adaptives Lernen -------------------------------------------------
    # Schalter aus 01_ARCHITECTURE.md §16: das neue System kann schrittweise
    # ausgeliefert werden, ohne die laufende App zu verändern. Alles aus.
    adaptive_learning_enabled: bool = False
    semantic_error_matching_enabled: bool = False
    llm_error_creation_enabled: bool = False
    content_experimentation_enabled: bool = False
    worksheet_ai_analysis_enabled: bool = False

    # Schwellen gehören in die Konfiguration, nicht als Zahl in den Code
    # (A5: endliche Wiederholungen, A8: Beherrschung wird verdient).
    adaptiv_max_lehrrunden: int = 3
    adaptiv_mastery_treffer: int = 2
    #: Wie oft eine Antwort unerkannt bleiben darf, bevor ein Mensch ran muss.
    #: Stand als 3 im Code — die einzige Schwelle des adaptiven Wegs, an der
    #: eine Familie nichts drehen konnte.
    adaptiv_unbekannte_antworten: int = 3
    #: Ab so vielen Einsaetzen wird die Wirkung einer Erklaerung zur Aussage.
    #: Darunter ist eine Quote Zufall (Z10).
    adaptiv_wirkung_ab: int = 10
    #: Darunter gilt eine Erklaerung als wirkungslos und wird gemeldet.
    adaptiv_wirkung_schwelle: float = 0.3
    #: Schneller beantwortet heisst geraten — solche Antworten zaehlen 0
    #: Sekunden aktive Zeit (Schritt 4a).
    adaptiv_mindest_sekunden: int = 3
    #: So lange ohne Eingabe, dann steht die Uhr. Das Kind ist dann nicht
    #: mehr an der Aufgabe, auch wenn die Seite noch offen ist.
    adaptiv_pause_sekunden: int = 120
    #: So viele zu schnelle Antworten hintereinander, dann gilt der Abschnitt
    #: als nicht ernsthaft. Keine Strafe — nur eine ehrliche Zahl.
    adaptiv_nicht_ernsthaft_serie: int = 3
    #: So viele neue Aufgaben hat eine Wiederholung (3 bis 5).
    adaptiv_wiederholung_aufgaben: int = 4
    adaptiv_aehnlichkeit_schwelle: float = 0.82

    setup_complete: bool = False

    def __repr__(self) -> str:  # pragma: no cover
        safe = {k: v for k, v in asdict(self).items() if k not in SECRET_FIELDS}
        safe["zugangsdaten"] = "<gesetzt>" if self.has_credentials else "<leer>"
        return f"Config({safe})"

    __str__ = __repr__

    @property
    def has_credentials(self) -> bool:
        # Der Schluessel lebt nur in der Umgebung — absichtlich live gelesen,
        # damit ein nachtraeglich gesetzter Wert ohne Neuschreiben gilt.
        # Welche Variable das ist, weiss allein der gewaehlte Adapter.
        from .ai import credentials_present
        return credentials_present(self)

    def public_dict(self) -> dict:
        """Alles, was gefahrlos in ein Template oder ins Protokoll darf."""
        d = {k: v for k, v in asdict(self).items() if k not in SECRET_FIELDS}
        d["has_credentials"] = self.has_credentials
        d["has_password"] = bool(self.app_password_hash)
        d["has_child_password"] = bool(self.child_password_hash)
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


def begleiter_dir() -> Path:
    """Begleiter-Foto und Interessen-Sprachclips ("Meine Welt")."""
    return _ensure(DATA_DIR / "begleiter")


def profile_dir() -> Path:
    """Lokales Profilbild des Kindes."""
    return _ensure(DATA_DIR / "profil")


def drive_root() -> Path:
    sub = load_safe().drive_subdir
    return DRIVE_DIR / sub if sub else DRIVE_DIR


# --------------------------------------------------------------------------
# Ops — Betriebsparameter
# --------------------------------------------------------------------------
#
# Alles, was Betreiber, Deployment, Providerwahl, Kosten, Limits oder bewusstes
# Produktverhalten ändern können sollen, ohne /data/config.json der Familie
# anzufassen. Ein einziger Ort: jeder Wert hat hier genau einen Default und
# einen Environment-Override `KARO_<FELDNAME>` (Großschreibung). Zeiten sind
# Sekunden, Grössen Bytes. Ungültige Werte sind ein Startfehler, kein stiller
# Fallback — siehe ops().


class OpsInvalid(RuntimeError):
    """Ein KARO_*-Override ist ungültig — die App soll nicht halb starten."""


@dataclass(frozen=True)
class Ops:
    # --- HTTP / Sitzung -----------------------------------------------------
    #: Grösster Request-Body. Muss über paket_max_bytes + Overhead liegen,
    #: sonst erreicht ein legales Paket den Server nie (Validierung in ops()).
    max_body_bytes: int = 105 * 1024 * 1024
    #: Lebensdauer der Sitzungs-Cookies.
    session_max_age_seconds: int = 14 * 24 * 60 * 60
    #: Strict-Transport-Security, nur wenn https_only gesetzt ist.
    hsts_seconds: int = 31_536_000
    https_only: bool = False                  # KARO_HTTPS_ONLY=1
    log_level: str = "INFO"                   # KARO_LOG_LEVEL
    environment: str = "prod"                 # KARO_ENV

    # --- Datenbank ----------------------------------------------------------
    db_connect_timeout_seconds: float = 30.0
    db_busy_timeout_ms: int = 30_000

    # --- Hintergrund-Jobs ----------------------------------------------------
    jobs_max_attempts: int = 3
    jobs_poll_seconds: float = 3.0
    #: Wartezeiten vor dem 2. und 3. Versuch (Env: kommagetrennt, "60,300").
    jobs_retry_delays: tuple = (60, 300)
    #: Deferred-Jobs klemmen ihre Wartezeit in diesen Rahmen.
    jobs_defer_min_seconds: int = 5
    jobs_defer_max_seconds: int = 300
    jobs_stop_timeout_seconds: float = 10.0

    # --- Uploads -------------------------------------------------------------
    #: Einzel-Upload-Limit ausserhalb des Paketwegs (Lernmaterial, Profilbild).
    upload_max_bytes: int = 25 * 1024 * 1024
    passwort_min_laenge: int = 8

    # --- Material-Paket (Multi-Page-Upload) ----------------------------------
    paket_max_seiten: int = 10
    #: Weniger Zeichen OCR-/Textebenen-Ergebnis gilt nicht als gelesene Seite
    #: (Paket-Vorschau, Server-OCR, Browser-JS).
    seite_min_zeichen: int = 40
    paket_max_bild_bytes: int = 15 * 1024 * 1024
    paket_max_pdf_bytes: int = 50 * 1024 * 1024
    paket_max_bytes: int = 100 * 1024 * 1024
    #: Formular-/Multipart-Overhead, den der Router auf das Paketlimit legt.
    paket_overhead_bytes: int = 2 * 1024 * 1024
    paket_max_text_zeichen: int = 20_000
    paket_max_themen: int = 20

    # --- Dokument-Eingang (Drive-Inbox) --------------------------------------
    ingest_max_source_bytes: int = 60 * 1024 * 1024
    ingest_max_pdf_pages: int = 300
    ingest_max_edge: int = 1_800
    ingest_target_bytes: int = 4_400_000
    ingest_min_quality: int = 45
    ingest_max_image_pixels: int = 40_000_000

    #: Obergrenze für Config.header_crop_percent — mehr würde Inhalt abschneiden.
    kopfzeile_max_prozent: int = 25
    #: Abschnitte pro eingelesenem Blatt — länger schneidet niemand sinnvoll klein.
    blatt_max_abschnitte: int = 60
    #: Zeichendeckel pro Abschnitt.
    blatt_max_zeichen: int = 6_000

    # --- OCR (Tesseract, Server-Fallback) ------------------------------------
    ocr_timeout_seconds: int = 120
    ocr_sprachen: str = "deu+eng"
    #: Server-OCR zerlegt höchstens so viele PDF-Seiten.
    ocr_max_pdf_seiten: int = 20
    #: Browser-PDF-Render: höchstens so viele Seiten pro Dokument.
    browser_ocr_max_seiten: int = 20
    #: Browser-PDF-Render: Zielkante in Pixel — grösser bringt nichts.
    browser_ocr_max_kante: int = 2_000
    #: Browser-OCR: Konfidenz, unter der ein Wort als geraten gilt (0-100).
    browser_ocr_min_konfidenz: int = 60

    # --- KI-Anbieter (generisch) ----------------------------------------------
    #: Abstand, mit dem ein gestellter Auftrag seinen Lauf erneut abfragt.
    ai_poll_seconds: int = 300
    #: Danach wird ein laufender Auftrag aufgegeben und der Job schlägt fehl.
    ai_max_run_seconds: int = 7_200
    #: Zeitlimit für einen einzelnen HTTP-Aufruf zum Anbieter (nicht für den Lauf).
    ai_http_timeout_seconds: float = 60.0
    #: Wie oft ein gescheiterter/abgelaufener Lauf neu angelegt wird.
    ai_max_restarts: int = 1

    # --- Adapter-spezifisch (nur für den gewählten Anbieter relevant) ---------
    #: Leer = Standard des Adapters. Die API-URL gehört zum Provider-Wissen,
    #: hier steht nur der Override-Haken.
    ai_devin_base_url: str = ""
    #: ACU-Kostenrahmen pro Session; 0 = kein Limit.
    ai_devin_max_acu: int = 0
    ai_openrouter_base_url: str = ""
    #: Pflicht, wenn ai_provider="openrouter".
    ai_openrouter_model: str = ""
    llm_default_max_tokens: int = 8_192
    #: Ad-hoc-Fachprüfung beim Themeneinlesen.
    llm_fach_max_tokens: int = 64
    #: Lektions-Erzeugung ist der längste und teuerste Aufruf im System.
    llm_lektion_max_tokens: int = 32_000

    # --- Curriculum-Dienst -----------------------------------------------------
    curriculum_request_timeout_seconds: int = 8
    curriculum_max_wait_seconds: int = 24 * 60 * 60
    curriculum_max_response_bytes: int = 2_000_000
    #: Warten auf einen Export (Polling-Abstand) bzw. generischer Fehlerrückzug.
    curriculum_poll_seconds: int = 300
    curriculum_error_retry_seconds: int = 15

    # --- NotebookLM -----------------------------------------------------------
    notebooklm_login_browser_timeout_seconds: int = 300
    notebooklm_auth_check_timeout_seconds: int = 30
    notebooklm_short_timeout_seconds: int = 90
    notebooklm_generate_timeout_seconds: int = 2_700
    notebooklm_download_timeout_seconds: int = 300
    notebooklm_cancel_poll_seconds: int = 5
    notebooklm_attempts: int = 3
    notebooklm_generate_attempts: int = 2
    notebooklm_retry_base_seconds: int = 15
    notebooklm_vnc_rfb_port: int = 5_901
    notebooklm_novnc_port: int = 6_080
    notebooklm_vnc_display: str = ":99"
    notebooklm_vnc_ready_timeout_seconds: int = 15
    notebooklm_vnc_screen: str = "1280x800x24"
    notebooklm_novnc_dir: str = "/usr/share/novnc"

    # --- Medien-Erzeugung -------------------------------------------------------
    tts_timeout_seconds: int = 180
    video_timeout_seconds: int = 600
    profil_bild_pixel: int = 512
    #: Cache-Dauer des Profilbilds im Browser (Cache-Control max-age).
    profil_bild_cache_seconds: int = 86_400

    # --- Verbindungsstatus ------------------------------------------------------
    #: Die Modellliste darf so alt sein, bevor sie neu geholt wird.
    connections_cache_ttl_seconds: float = 100.0

    # --- Lernzeit-Messung ---------------------------------------------------------
    lernzeit_takt_seconds: int = 30
    lernzeit_anschluss_seconds: int = 90
    lernzeit_pause_seconds: int = 300
    lernzeit_gutschrift_seconds: int = 60
    lernzeit_tagesdeckel_seconds: int = 8 * 3_600

    # --- Adaptives Lernen (Produktverhalten, nicht Familien-Setup) -----------------
    #: Geschätzte Basisdauer einer Antwort je Interaktionsart.
    adaptiv_grundzeit_auswahl_seconds: int = 25
    adaptiv_grundzeit_bruch_seconds: int = 60
    adaptiv_grundzeit_text_seconds: int = 90
    #: Die Schätzung darf um diesen Faktor über/unter der Basis liegen.
    adaptiv_zeit_spanne_min: float = 0.6
    adaptiv_zeit_spanne_max: float = 1.8
    #: Wählbare Abstände (Tage) für eine Wiederholung.
    wiederholung_abstaende: tuple = (2, 3, 4, 5)
    voraussetzung_aufgaben: int = 2
    #: Gültigkeit des signierten Prüfhinweises im Voraussetzung-Umweg.
    hinweis_max_age_seconds: int = 1_800
    #: „Heute" gilt als gut gelaufen, wenn die Serie so viele Tage reicht.
    erfolg_tage: int = 14
    #: Neue Themen pro Tag im Familienkonto (KARO_FAMILY_DAILY_TOPICS).
    family_daily_topics: int = 5

    # --- Meine Woche (Verhaltensregeln) -------------------------------------------
    woche_fenster_tage: int = 28
    woche_gemieden_tage: int = 28
    woche_gemieden_min_stunden: int = 3
    #: Ab dieser Stunde schlägt die App nichts mehr vor.
    woche_schlafgrenze_stunde: int = 21
    #: Zähler-Schwellen der Wochenregeln (woche/regeln.py).
    woche_schlechter_tag_ab: int = 3
    woche_guter_tag_ab: int = 3
    woche_zu_schwer_ab: int = 2
    woche_abbruch_ab: int = 3
    woche_verkleinern_max: int = 2
    woche_schwierig_tage_ab: int = 3
    woche_nullzyklen_ab: int = 2
    woche_karten_schwelle: int = 2

    # --- Meine Welt ----------------------------------------------------------------
    welt_foto_source_bytes: int = 12 * 1024 * 1024
    welt_audio_bytes: int = 2_000_000
    welt_max_image_pixels: int = 25_000_000
    welt_max_image_edge: int = 1_800
    welt_thumb_edge: int = 360
    #: Tägliches Foto-Kontingent in „Meine Welt".
    welt_fotos_tag: int = 2
    #: Tägliches Hör-Kontingent für private Sprachclips.
    welt_audio_sekunden_tag: int = 60
    #: Zeitkapseln dürfen höchstens so weit in der Zukunft liegen.
    welt_kapsel_max_tage: int = 366 * 5

    # --- Suche und Eingabekappen -------------------------------------------------------
    #: Treffer der Themen-Volltextsuche.
    kb_suche_treffer: int = 12
    #: Lehrmaterial-Treffer pro Thema.
    kb_lehrmaterial_treffer: int = 10
    #: Treffer, aus denen die automatische Themen-Zuordnung wählt.
    themen_zuordnung_treffer: int = 30
    #: Ähnlichkeitsschwelle, ab der ein Thema als Dublette gilt.
    themen_duplikat_schwelle: float = 0.88
    #: Maximale Zeichen pro Antwort in einem Quiz-Entwurf.
    entwurf_antwort_zeichen: int = 2_000
    #: Maximale Zeichen pro Antwort in einer Klassenarbeit-Probe.
    probe_antwort_zeichen: int = 1_000

    # --- Recherche -------------------------------------------------------------------
    recherche_max_treffer: int = 8
    recherche_max_inhalt_zeichen: int = 6_000

    # --- Familien-Post / Formular-Deckel ----------------------------------------------
    post_max_text_zeichen: int = 200
    post_max_feier_zeichen: int = 60
    #: Eingabefeld „Lernwunsch" (gespeicherter Wert) vs. Anteil im Prompt.
    formular_wunsch_zeichen: int = 500
    prompt_wunsch_zeichen: int = 300


#: Historische Env-Namen, die nicht dem KARO_<FELD>-Schema folgen.
_OPS_ENV_ALIASES = {
    "log_level": "KARO_LOG_LEVEL",
    "environment": "KARO_ENV",
    "https_only": "KARO_HTTPS_ONLY",
    "family_daily_topics": "KARO_FAMILY_DAILY_TOPICS",
}


def _ops_env_name(field_name: str) -> str:
    return _OPS_ENV_ALIASES.get(field_name, f"KARO_{field_name.upper()}")


def _ops_parse(field_name: str, raw: str):
    """String aus der Umgebung in den Feldtyp wandeln. Wirft OpsInvalid."""
    default = Ops.__dataclass_fields__[field_name].default
    try:
        if isinstance(default, bool):
            if raw.strip() in ("1", "true", "ja"):
                return True
            if raw.strip() in ("0", "false", "nein"):
                return False
            raise ValueError("erwarte 0/1")
        if isinstance(default, int):
            return int(raw)
        if isinstance(default, float):
            return float(raw)
        if isinstance(default, tuple):
            teile = [t.strip() for t in raw.split(",") if t.strip()]
            if not teile or not all(t.lstrip("-").isdigit() for t in teile):
                raise ValueError("erwarte kommagetrennte Ganzzahlen")
            return tuple(int(t) for t in teile)
        return raw
    except ValueError as exc:
        raise OpsInvalid(
            f"{_ops_env_name(field_name)}={raw!r} ist ungültig: {exc}"
        ) from None


#: Felder, bei denen 0 eine eigene Bedeutung trägt (hier: „kein Limit").
_OPS_ZERO_OK = {"family_daily_topics", "ai_devin_max_acu"}

#: Felder, die leer sein dürfen (hier: nur nötig, wenn der Anbieter gewählt
#: ist — die Pflicht meldet der Adapter selbst, siehe providers/openrouter).
_OPS_LEER_OK = {"ai_openrouter_model", "ai_devin_base_url",
                "ai_openrouter_base_url"}


def _ops_validate(o: "Ops") -> None:
    """Wertebereiche prüfen — Fehlkonfiguration heisst klare Fehlermeldung."""
    probleme = []
    for f in fields(Ops):
        wert = getattr(o, f.name)
        if isinstance(wert, bool):
            continue
        if isinstance(wert, (int, float)) and wert <= 0 \
                and f.name not in _OPS_ZERO_OK:
            probleme.append(f"{f.name} = {wert} — erwartet wird ein positiver Wert")
        if isinstance(wert, str) and not wert.strip() \
                and f.name not in _OPS_LEER_OK:
            probleme.append(f"{f.name} darf nicht leer sein")
        if isinstance(wert, tuple) and not wert:
            probleme.append(f"{f.name} darf nicht leer sein")
    if o.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
        probleme.append(f"log_level {o.log_level!r} — DEBUG|INFO|WARNING|ERROR")
    if not (1 <= o.notebooklm_vnc_rfb_port <= 65535):
        probleme.append("notebooklm_vnc_rfb_port ausserhalb 1-65535")
    if not (1 <= o.notebooklm_novnc_port <= 65535):
        probleme.append("notebooklm_novnc_port ausserhalb 1-65535")
    paket_plus_overhead = o.paket_max_bytes + o.paket_overhead_bytes
    if o.max_body_bytes < paket_plus_overhead:
        probleme.append(
            f"max_body_bytes ({o.max_body_bytes}) < paket_max_bytes + Overhead "
            f"({paket_plus_overhead}) — grösste Pakete kämen nie an")
    if o.paket_max_pdf_bytes > o.paket_max_bytes:
        probleme.append("paket_max_pdf_bytes > paket_max_bytes")
    if o.paket_max_bild_bytes > o.paket_max_bytes:
        probleme.append("paket_max_bild_bytes > paket_max_bytes")
    if o.jobs_defer_min_seconds > o.jobs_defer_max_seconds:
        probleme.append("jobs_defer_min_seconds > jobs_defer_max_seconds")
    for feld in ("ai_devin_base_url", "ai_openrouter_base_url"):
        wert = getattr(o, feld)
        if wert and not wert.startswith(("https://", "http://")):
            probleme.append(f"{feld} muss eine http(s)-URL sein")
    if o.ai_poll_seconds > o.jobs_defer_max_seconds:
        probleme.append(
            "ai_poll_seconds > jobs_defer_max_seconds — gestellte Aufträge "
            "würden später abgefragt als das Parken erlaubt")
    if o.adaptiv_zeit_spanne_min > o.adaptiv_zeit_spanne_max:
        probleme.append("adaptiv_zeit_spanne_min > adaptiv_zeit_spanne_max")
    if o.woche_schlafgrenze_stunde > 23:
        probleme.append("woche_schlafgrenze_stunde > 23")
    if probleme:
        raise OpsInvalid(
            "Betriebskonfiguration ungültig:\n  - " + "\n  - ".join(probleme))


@cache
def ops() -> Ops:
    """Die Betriebsparameter — Defaults mit KARO_*-Overrides, einmal geprüft.

    Wird beim App-Start aufgerufen (main) und von den Modulen, die ihre
    Konstanten hierher legen. Env-Overrides greifen beim ersten Aufruf.
    """
    overrides = {}
    for f in fields(Ops):
        roh = os.environ.get(_ops_env_name(f.name))
        if roh is not None and roh.strip() != "":
            overrides[f.name] = _ops_parse(f.name, roh)
    o = Ops(**overrides)
    _ops_validate(o)
    return o


# --------------------------------------------------------------------------
# Zeitzone — eine Quelle für alle Tagesgrenzen
# --------------------------------------------------------------------------

def zeitzone(cfg: "Config | None" = None) -> ZoneInfo:
    """KARO_TIMEZONE > TZ > config.timezone > Europe/Berlin.

    Früher las jede Stelle selbst: pilot.py nur die Umgebung, die Dienste
    ein Config-Feld, das es gar nicht gab, world_db.py eine Konstante.
    """
    name = (os.environ.get("KARO_TIMEZONE") or os.environ.get("TZ")
            or (cfg or load_safe()).timezone or "Europe/Berlin")
    try:
        return ZoneInfo(name)
    except Exception:  # noqa: BLE001 - unbekannter Zonenname, nie crashen
        return ZoneInfo("Europe/Berlin")
