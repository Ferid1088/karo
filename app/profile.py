"""Lokales Kind-Profilbild: pruefen, vereinheitlichen und atomar speichern."""
from __future__ import annotations

import io
import os
import tempfile
import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from . import config, security

try:  # iPhones liefern je nach Kameraeinstellung HEIC/HEIF.
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:  # pragma: no cover - optionale Komfortunterstuetzung
    pass


PROFILE_SIZE = config.ops().profil_bild_pixel
Image.MAX_IMAGE_PIXELS = config.ops().ingest_max_image_pixels


def photo_path() -> Path:
    return config.profile_dir() / "kind.jpg"


def photo_url() -> str | None:
    """URL mit Dateiversion, damit ein geaendertes Bild sofort sichtbar ist."""
    path = photo_path()
    try:
        return f"/profilbild?v={path.stat().st_mtime_ns}"
    except OSError:
        return None


def prepare_photo(data: bytes) -> bytes:
    """Validiert ein Bild anhand seines Inhalts und erzeugt ein kleines JPEG.

    Das Neuschreiben entfernt Metadaten (insbesondere Standort/EXIF), richtet
    Handyfotos korrekt aus und verhindert, dass aktive oder unerwartete
    Dateiinhalte unveraendert ausgeliefert werden.
    """
    if not data:
        raise ValueError("Bitte ein Bild auswählen.")
    if len(data) > security.MAX_UPLOAD_BYTES:
        raise ValueError("Das Bild ist zu groß.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                source.load()
                image = ImageOps.exif_transpose(source)
                if getattr(image, "is_animated", False):
                    image.seek(0)
                image = image.convert("RGB")
                image = ImageOps.fit(
                    image,
                    (PROFILE_SIZE, PROFILE_SIZE),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                )
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValueError("Die Datei ist kein lesbares Bild.") from None
    except (Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise ValueError("Das Bild ist unplausibel groß und wurde abgelehnt.") from None

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=88, optimize=True, progressive=True)
    return output.getvalue()


def save_photo(data: bytes) -> None:
    """Ersetzt das Profilbild atomar; Leser sehen nie eine halbe Datei."""
    target = photo_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        dir=str(target.parent), prefix=".kind-", suffix=".jpg")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def remove_photo() -> None:
    photo_path().unlink(missing_ok=True)
