"""Einlesen aus dem Drive-Ordner.

Der Google-Drive-Ordner ist Speicher und Archiv. Die App spricht nicht mit der
Google-API, sondern liest den Ordner, den der Drive-Desktop-Client ohnehin auf
den Rechner synchronisiert und der als Volume im Container haengt. Das spart
einen kompletten OAuth-Teil, und Drive bleibt trotzdem die einzige Wahrheit
fuer die Originaldokumente.

    Karo/
      01_Eingang/          <- Scans vom Handy
      02_Verarbeitet/      <- nach dem Einlesen, nach Monat sortiert
      03_Lernmaterial/     <- erzeugte Folien, Videos, Fragebogen
      04_Nicht_lesbar/     <- was sich nicht aufbereiten liess
      Lernstand.xlsx       <- Themen mit Flaggen, in Drive als Sheet öffenbar
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
import shutil
import unicodedata
import warnings
from datetime import date
from pathlib import Path

from PIL import Image, ImageOps

from . import config, db

log = logging.getLogger("karo.ingest")

# Bildbomben abwehren: eine 60000x60000-PNG wuerde sonst zehn Gigabyte
# anfordern und den Container abschiessen.
Image.MAX_IMAGE_PIXELS = 40_000_000
warnings.simplefilter("error", Image.DecompressionBombWarning)

try:                                   # iPhones fotografieren standardmaessig HEIC
    from pillow_heif import register_heif_opener

    register_heif_opener()
    HEIF_OK = True
except ImportError:                    # pragma: no cover
    HEIF_OK = False
    log.warning("pillow-heif fehlt — HEIC-Dateien können nicht gelesen werden")

INBOX = "01_Eingang"
DONE = "02_Verarbeitet"
SHEETS = "03_Lernmaterial"
BAD = "04_Nicht_lesbar"

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
if HEIF_OK:
    IMAGE_SUFFIXES |= {".heic", ".heif"}
PDF_SUFFIXES = {".pdf"}
ALL_SUFFIXES = IMAGE_SUFFIXES | PDF_SUFFIXES

MAX_EDGE = 1800
TARGET_BYTES = 4_400_000        # Sicherheitsabstand zur 5-MB-Grenze der API
MIN_QUALITY = 45
MAX_SOURCE_BYTES = 60 * 1024 * 1024
MAX_PDF_PAGES = 300              # schuetzt vor Endlos-Scans, nicht vor echten Heften


class IngestError(Exception):
    """Verstaendlicher Fehler beim Aufbereiten einer Datei."""


# --------------------------------------------------------------------------
# Ordner
# --------------------------------------------------------------------------

def ensure_folders() -> Path | None:
    """Legt die Unterordner an. None, wenn das nicht geht — nie eine Ausnahme."""
    try:
        root = config.drive_root()
        if not root.is_dir():
            return None
        for sub in (INBOX, DONE, SHEETS, BAD):
            (root / sub).mkdir(parents=True, exist_ok=True)
        return root
    except OSError as exc:
        log.warning("Drive-Ordner nicht nutzbar: %s", exc)
        return None


def drive_available() -> bool:
    """Wahr nur, wenn der Ordner da ist UND die App darin arbeiten kann."""
    return ensure_folders() is not None


def drive_writable() -> bool:
    root = ensure_folders()
    if root is None:
        return False
    probe = root / ".karo-schreibtest"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def inbox_path() -> Path:
    """Der Ordner, in den Scans gehoeren — Drive, sonst lokaler Ersatz."""
    root = ensure_folders()
    return (root / INBOX) if root else config.local_inbox()


# --------------------------------------------------------------------------
# Bildaufbereitung
# --------------------------------------------------------------------------

def _open_pdf(path: Path):
    """Oeffnet ein PDF und prueft die Seitenzahl. Ruft close() selbst im Fehlerfall."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:      # pragma: no cover
        raise IngestError("PDF-Unterstützung fehlt (PyMuPDF nicht installiert).") from exc
    try:
        doc = fitz.open(str(path))
    except Exception as exc:
        raise IngestError(f"Das PDF ließ sich nicht öffnen: {exc}") from None
    if doc.page_count == 0:
        doc.close()
        raise IngestError("Das PDF hat keine Seiten.")
    if doc.page_count > MAX_PDF_PAGES:
        doc.close()
        raise IngestError(
            f"Das PDF hat {doc.page_count} Seiten — mehr als die erlaubten "
            f"{MAX_PDF_PAGES}. Bitte in kleinere Teile aufteilen."
        )
    return doc


def _render_pdf_page(doc, index: int) -> Image.Image:
    pix = doc.load_page(index).get_pixmap(dpi=180)
    return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")


def _load_image_file(path: Path) -> Image.Image:
    suffix = path.suffix.lower()
    if suffix in (".heic", ".heif") and not HEIF_OK:
        raise IngestError(
            "HEIC-Dateien werden von dieser Installation nicht unterstützt. "
            "Am iPhone unter Einstellungen › Kamera › Formate auf "
            "„Maximale Kompatibilität“ stellen."
        )

    try:
        img = Image.open(path)
        img = ImageOps.exif_transpose(img) or img   # Handyfotos stehen sonst quer
        return img.convert("RGB")
    except Image.DecompressionBombWarning:
        raise IngestError("Das Bild ist unplausibel groß und wurde abgelehnt.") from None
    except Image.DecompressionBombError:
        raise IngestError("Das Bild ist unplausibel groß und wurde abgelehnt.") from None
    except OSError as exc:
        raise IngestError(f"Die Datei ließ sich nicht als Bild öffnen: {exc}") from None


def _load_any(path: Path) -> Image.Image:
    """Einzelbild oder erste PDF-Seite — fuer Aufrufer, die nur ein Blatt kennen."""
    if path.suffix.lower() in PDF_SUFFIXES:
        with _open_pdf(path) as doc:
            return _render_pdf_page(doc, 0)
    return _load_image_file(path)


def _encode_image(img: Image.Image, dest: Path, header_crop_percent: int = 0) -> dict:
    """Erzeugt ein JPEG, das sicher unter die API-Grenze passt.

    Schneidet optional den oberen Rand ab — dort steht auf deutschen
    Arbeitsblaettern verlaesslich der Name.
    """
    original_size = img.size

    crop_px = 0
    if header_crop_percent > 0:
        crop_px = int(img.height * min(header_crop_percent, 25) / 100)
        if 0 < crop_px < img.height:
            img = img.crop((0, crop_px, img.width, img.height))
        else:
            crop_px = 0

    img.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)

    quality, data = 85, b""
    while quality >= MIN_QUALITY:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
        data = buf.getvalue()
        if len(data) <= TARGET_BYTES:
            break
        quality -= 10

    if len(data) > TARGET_BYTES:
        raise IngestError(
            "Der Scan lässt sich nicht klein genug rechnen. Bitte mit geringerer "
            "Auflösung neu einlesen."
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return {"bytes": len(data), "size": img.size, "original_size": original_size,
            "cropped_px": crop_px, "quality": quality}


def normalize(src: Path, dest: Path, header_crop_percent: int = 0) -> dict:
    """Einzelbild oder erste PDF-Seite in ein passendes JPEG umwandeln."""
    return _encode_image(_load_any(src), dest, header_crop_percent)


# --------------------------------------------------------------------------
# Ordner abtasten
# --------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_name(name: str) -> str:
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return (name or "scan")[:120]


_DATE_IN_NAME = re.compile(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})")


def _guess_date(name: str, path: Path) -> str:
    m = _DATE_IN_NAME.search(name)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
        except ValueError:
            pass
    try:
        return date.fromtimestamp(path.stat().st_mtime).isoformat()
    except OSError:
        return db.today()


def scan_inbox(limit: int = 25) -> list[dict]:
    """Liest neue Dateien ein. Idempotent ueber den sha256-Index."""
    inbox = inbox_path()
    if not inbox.is_dir():
        return []

    cfg = config.load_safe()
    results: list[dict] = []

    try:
        entries = [p for p in inbox.iterdir()
                   if p.is_file() and not p.name.startswith(".")]
    except OSError as exc:
        log.warning("Eingangsordner nicht lesbar: %s", exc)
        return []

    for src in sorted(entries, key=lambda p: p.name)[:limit]:
        if src.suffix.lower() not in ALL_SUFFIXES:
            results.append({"name": src.name, "status": "fehler",
                            "error": "Dateityp wird nicht unterstützt"})
            _move(src, BAD)
            continue
        try:
            size = src.stat().st_size
            if size == 0:
                continue                    # Drive synchronisiert noch
            if size > MAX_SOURCE_BYTES:
                results.append({"name": src.name, "status": "fehler",
                                "error": f"Datei zu groß ({size // 1_048_576} MB)"})
                _move(src, BAD)
                continue
        except OSError as exc:
            log.warning("Datei %s nicht lesbar: %s", src.name, exc)
            continue

        if src.suffix.lower() in PDF_SUFFIXES:
            page_results = _ingest_pdf(src, cfg)
            results.extend(page_results)
            if any(r["status"] == "fehler" for r in page_results) and \
               not any(r["status"] in ("neu", "doppelt") for r in page_results):
                _move(src, BAD)
            else:
                _move(src, DONE)
            continue

        try:
            digest = _sha256(src)
        except OSError as exc:
            log.warning("Datei %s nicht lesbar: %s", src.name, exc)
            continue

        existing = db.q1("SELECT id FROM document WHERE sha256 = ?", digest)
        if existing:
            _move(src, DONE, digest)
            results.append({"name": src.name, "status": "doppelt",
                            "document_id": existing["id"]})
            continue

        stored = config.scans_dir() / f"{digest}.jpg"
        try:
            info = normalize(src, stored, cfg.header_crop_percent)
        except IngestError as exc:
            log.warning("Scan %s nicht aufbereitbar: %s", src.name, exc)
            results.append({"name": src.name, "status": "fehler", "error": str(exc)})
            _move(src, BAD)
            continue
        except Exception as exc:                                # pragma: no cover
            log.warning("Scan %s: unerwarteter Fehler: %s", src.name, exc)
            results.append({"name": src.name, "status": "fehler",
                            "error": "Unerwarteter Fehler beim Aufbereiten"})
            _move(src, BAD)
            continue

        with db.tx() as c:
            cur = c.execute(
                """INSERT INTO document
                       (sha256, source_name, stored_path, mime, rolle,
                        captured_on, state, created_at)
                   VALUES (?, ?, ?, 'image/jpeg', 'wissen', ?, 'neu', ?)""",
                (digest, src.name[:200], str(stored),
                 _guess_date(src.name, src), db.now()),
            )
            doc_id = cur.lastrowid

        _move(src, DONE, digest)
        results.append({"name": src.name, "status": "neu",
                        "document_id": doc_id, **info})
    return results


def _ingest_pdf(src: Path, cfg) -> list[dict]:
    """Zerlegt ein mehrseitiges PDF in ein Arbeitsblatt je Seite.

    Jede Seite bekommt ihren eigenen Digest (aus dem gerenderten Bild, nicht
    aus der PDF-Datei) — so bleibt das Einlesen seitenweise idempotent, auch
    wenn dieselbe Datei versehentlich zweimal im Eingang landet.
    """
    try:
        doc = _open_pdf(src)
    except IngestError as exc:
        log.warning("PDF %s nicht aufbereitbar: %s", src.name, exc)
        return [{"name": src.name, "status": "fehler", "error": str(exc)}]

    results: list[dict] = []
    try:
        page_count = doc.page_count
        for i in range(page_count):
            seiten_name = f"{src.name} (Seite {i + 1}/{page_count})"
            try:
                img = _render_pdf_page(doc, i)
            except Exception as exc:
                log.warning("Seite %d von %s nicht lesbar: %s", i + 1, src.name, exc)
                results.append({"name": seiten_name, "status": "fehler",
                                "error": "Seite ließ sich nicht rendern"})
                continue

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            digest = hashlib.sha256(buf.getvalue()).hexdigest()

            existing = db.q1("SELECT id FROM document WHERE sha256 = ?", digest)
            if existing:
                results.append({"name": seiten_name, "status": "doppelt",
                                "document_id": existing["id"]})
                continue

            stored = config.scans_dir() / f"{digest}.jpg"
            try:
                info = _encode_image(img, stored, cfg.header_crop_percent)
            except IngestError as exc:
                results.append({"name": seiten_name, "status": "fehler", "error": str(exc)})
                continue

            with db.tx() as c:
                cur = c.execute(
                    """INSERT INTO document
                           (sha256, source_name, stored_path, mime, rolle,
                            captured_on, state, created_at)
                       VALUES (?, ?, ?, 'image/jpeg', 'wissen', ?, 'neu', ?)""",
                    (digest, seiten_name[:200], str(stored),
                     _guess_date(src.name, src), db.now()),
                )
                doc_id = cur.lastrowid

            results.append({"name": seiten_name, "status": "neu",
                            "document_id": doc_id, **info})
    finally:
        doc.close()

    return results


def _move(src: Path, folder: str, digest: str = "") -> None:
    """Verschiebt das Original weg, damit der Eingang leer bleibt.

    Auch ohne Drive-Ordner: sonst blieben im Ersatz-Eingang alle Dateien liegen
    und wuerden bei jedem Einlesen erneut gehasht und als Dublette gemeldet.
    """
    root = ensure_folders()
    if root is None:
        root = config.DATA_DIR
        folder = {DONE: "verarbeitet", BAD: "nicht_lesbar",
                  SHEETS: "uebungsblaetter"}.get(folder, folder)
    target_dir = root / folder / (db.today()[:7] if folder in (DONE, "verarbeitet") else "")
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / safe_name(src.name)
        if target.exists():
            suffix = digest[:8] or db.now()[-8:].replace(":", "")
            target = target_dir / f"{target.stem}_{suffix}{target.suffix}"
        shutil.move(str(src), str(target))
    except OSError as exc:
        log.warning("Original %s konnte nicht verschoben werden: %s", src.name, exc)


def material_dir() -> Path:
    """Wohin erzeugtes Lernmaterial gehoert — Drive, sonst lokaler Ersatz."""
    root = ensure_folders()
    if root is not None:
        return root / SHEETS
    ziel = config.DATA_DIR / "material_ausgabe"
    ziel.mkdir(parents=True, exist_ok=True)
    return ziel


def write_material(filename: str, inhalt: str) -> str | None:
    """Schreibt eine Textdatei (HTML) ins Lernmaterial."""
    try:
        ziel = material_dir() / safe_name(filename)
        ziel.write_text(inhalt, encoding="utf-8")
        return str(ziel)
    except OSError as exc:
        log.warning("Lernmaterial konnte nicht geschrieben werden: %s", exc)
        return None


def commit_material(quelle: Path, unterordner: str | None = SHEETS) -> str | None:
    """Kopiert eine fertige Datei (MP4, XLSX) an ihren Platz.

    Kopiert statt verschiebt: die Quelle liegt im Datenverzeichnis und bleibt
    dort, damit ein fehlgeschlagener Drive-Sync nichts vernichtet.
    """
    if not quelle.is_file():
        return None
    try:
        root = ensure_folders()
        if root is not None:
            ziel_dir = (root / unterordner) if unterordner else root
        else:
            ziel_dir = config.DATA_DIR / "material_ausgabe"
        ziel_dir.mkdir(parents=True, exist_ok=True)
        ziel = ziel_dir / safe_name(quelle.name)
        shutil.copy2(quelle, ziel)
        return str(ziel)
    except OSError as exc:
        log.warning("Datei %s konnte nicht abgelegt werden: %s", quelle.name, exc)
        return None


# --------------------------------------------------------------------------
# Antwortblatt zu einer Fragerunde
# --------------------------------------------------------------------------

def aufnehmen(daten: bytes, endung: str, rolle: str = "wissen",
              themenname: str = "") -> dict:
    """Nimmt ein einzelnes Bild auf, ohne den Eingangsordner zu benutzen.

    Fuer den Papierweg: das Foto des Antwortblattes wird direkt auf der Seite
    der Fragerunde hochgeladen und ist damit eindeutig zugeordnet — kein
    Erkennen eines Codes auf dem Blatt, kein Zuordnen im Nachhinein, keine
    Verwechslung zweier Bloetter.

    `themenname`: nur beim Wissensbasis-Upload gesetzt — der von der Familie
    vorgegebene Rahmen, unter dem die KI dieses Blatt in Unterthemen zerlegt
    (siehe `kb.job_kb_extract()` und `topics.job_topic_propose()`). Der
    unbeaufsichtigte Drive-Ordner-Weg (`scan_inbox()`) kennt keinen Themen-
    namen je Datei und laesst dieses Feld leer.
    """
    import hashlib as _h

    if endung.lower() not in ALL_SUFFIXES:
        raise IngestError(f"Dateityp {endung or '(ohne)'} wird nicht unterstützt.")
    if len(daten) > MAX_SOURCE_BYTES:
        raise IngestError(
            f"Die Datei ist mit {len(daten) // 1_048_576} MB zu groß.")

    digest = _h.sha256(daten).hexdigest()
    bestehend = db.q1("SELECT * FROM document WHERE sha256 = ?", digest)
    if bestehend is not None:
        return {"document_id": bestehend["id"], "status": "doppelt",
                "stored_path": bestehend["stored_path"]}

    roh = config.DATA_DIR / "tmp" / f"{digest}{endung.lower()}"
    roh.parent.mkdir(parents=True, exist_ok=True)
    roh.write_bytes(daten)
    stored = config.scans_dir() / f"{digest}.jpg"
    try:
        cfg = config.load_safe()
        # Antwortblaetter werden NICHT beschnitten: der Name steht dort nicht
        # oben, und ein Zuschnitt koennte die erste Antwort abschneiden.
        crop = 0 if rolle == "bearbeitet" else cfg.header_crop_percent
        info = normalize(roh, stored, crop)
    finally:
        try:
            roh.unlink()
        except OSError:
            pass

    with db.tx() as c:
        cur = c.execute(
            """INSERT INTO document
                   (sha256, source_name, stored_path, mime, rolle, captured_on,
                    state, themenname, created_at)
               VALUES (?, ?, ?, 'image/jpeg', ?, ?, 'neu', ?, ?)""",
            (digest, f"upload{endung.lower()}", str(stored), rolle,
             db.today(), themenname.strip()[:200] or None, db.now()))
        doc_id = cur.lastrowid

    return {"document_id": doc_id, "status": "neu",
            "stored_path": str(stored), **info}
