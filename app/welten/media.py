"""Private media handling for "Meine Welt".

Images are decoded and re-encoded before storage, which strips EXIF/GPS metadata
and also prevents serving arbitrary uploaded bytes as an image. Audio is kept
private and is never sent to speech recognition or AI services.
"""
from __future__ import annotations

import io
import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from .. import config
from PIL import Image, ImageOps, UnidentifiedImageError

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:  # pragma: no cover - dependency is part of the app image
    pass

from . import world_db

_OPS = config.ops()
MAX_PHOTO_SOURCE_BYTES = _OPS.welt_foto_source_bytes
MAX_AUDIO_BYTES = _OPS.welt_audio_bytes
MAX_IMAGE_PIXELS = _OPS.welt_max_image_pixels
MAX_IMAGE_EDGE = _OPS.welt_max_image_edge
THUMB_EDGE = _OPS.welt_thumb_edge


@dataclass(frozen=True)
class StoredMedia:
    storage_key: str
    thumbnail_key: str | None
    mime_type: str
    byte_size: int


def _media_root() -> Path:
    root = world_db.private_dir() / "media"
    for path in (root, root / "photos", root / "thumbs", root / "audio"):
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(path, 0o700)
        except OSError:
            pass
    return root


def _atomic_private_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name("." + path.name + ".tmp-" + secrets.token_hex(6))
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


async def _read_limited(upload: UploadFile, maximum: int) -> bytes:
    data = bytearray()
    while chunk := await upload.read(1 << 20):
        data.extend(chunk)
        if len(data) > maximum:
            raise ValueError("Die Datei ist zu groß.")
    if not data:
        raise ValueError("Die Datei ist leer.")
    return bytes(data)


async def save_photo(upload: UploadFile) -> StoredMedia:
    raw = await _read_limited(upload, MAX_PHOTO_SOURCE_BYTES)
    try:
        with Image.open(io.BytesIO(raw)) as original:
            if getattr(original, "n_frames", 1) != 1:
                raise ValueError("Animierte Bilder werden nicht unterstützt.")
            original.load()
            if original.width * original.height > MAX_IMAGE_PIXELS:
                raise ValueError("Das Foto hat zu viele Bildpunkte.")
            image = ImageOps.exif_transpose(original).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Das Foto konnte nicht sicher gelesen werden.") from exc

    image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
    full = io.BytesIO()
    image.save(full, "WEBP", quality=82, method=6)
    full_bytes = full.getvalue()
    if len(full_bytes) > 2_500_000:
        raise ValueError("Das komprimierte Foto ist noch zu groß.")

    thumb_image = image.copy()
    thumb_image.thumbnail((THUMB_EDGE, THUMB_EDGE), Image.Resampling.LANCZOS)
    thumb = io.BytesIO()
    thumb_image.save(thumb, "WEBP", quality=72, method=4)

    stem = secrets.token_hex(24)
    storage_key = f"photos/{stem}.webp"
    thumbnail_key = f"thumbs/{stem}.webp"
    root = _media_root()
    _atomic_private_write(root / storage_key, full_bytes)
    try:
        _atomic_private_write(root / thumbnail_key, thumb.getvalue())
    except BaseException:
        try:
            (root / storage_key).unlink()
        except OSError:
            pass
        raise

    return StoredMedia(storage_key, thumbnail_key, "image/webp", len(full_bytes))


def _audio_format(raw: bytes) -> tuple[str, str]:
    if raw.startswith(b"\x1aE\xdf\xa3"):
        return "webm", "audio/webm"
    if raw.startswith(b"OggS"):
        return "ogg", "audio/ogg"
    if len(raw) >= 12 and raw[4:8] == b"ftyp":
        return "m4a", "audio/mp4"
    raise ValueError("Diese Aufnahme hat kein unterstütztes Audioformat.")


async def save_audio(upload: UploadFile, duration_seconds: int) -> StoredMedia:
    if not 1 <= duration_seconds <= 60:
        raise ValueError("Eine Aufnahme darf höchstens 60 Sekunden lang sein.")
    raw = await _read_limited(upload, MAX_AUDIO_BYTES)
    extension, mime = _audio_format(raw)
    storage_key = f"audio/{secrets.token_hex(24)}.{extension}"
    _atomic_private_write(_media_root() / storage_key, raw)
    return StoredMedia(storage_key, None, mime, len(raw))


def path_for(key: str) -> Path:
    root = _media_root().resolve()
    candidate = (root / key).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise FileNotFoundError("Ungültiger Medienpfad.") from None
    if not candidate.is_file():
        raise FileNotFoundError("Medium nicht gefunden.")
    return candidate


def delete_keys(*keys: str | None) -> None:
    root = _media_root().resolve()
    for key in keys:
        if not key:
            continue
        try:
            candidate = (root / key).resolve()
            candidate.relative_to(root)
            candidate.unlink(missing_ok=True)
        except (OSError, ValueError):
            pass
