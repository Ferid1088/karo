"""Sprachausgabe für den MP4-Modus: Piper.

Piper läuft offline, kostenlos und braucht kein Konto. Die Stimmdateien sind
rund 60 MB und liegen nicht im Image, sondern im Datenverzeichnis — so bleibt
das Image klein und ein Nutzer, der nur den HTML-Modus benutzt, lädt nie etwas
herunter.

Fehlt Piper oder die Stimme, sagt diese Datei das klar und die Anwendung
schaltet auf den HTML-Modus zurück, statt einen Fehler zu zeigen.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import wave
from pathlib import Path

from .. import config

log = logging.getLogger("karo.tts")

#: Stimmen, die Karo kennt. Der Nutzer waehlt im Setup.
STIMMEN = {
    "de_DE-thorsten-medium": "Thorsten (männlich, ruhig)",
    "de_DE-eva_k-x_low": "Eva (weiblich, schnell und klein)",
    "de_DE-kerstin-low": "Kerstin (weiblich)",
}

DEFAULT_STIMME = "de_DE-thorsten-medium"


class TtsUnavailable(RuntimeError):
    """Piper oder die Stimmdatei fehlt. Die Meldung ist fuer Menschen gedacht."""


def piper_binary() -> str | None:
    return shutil.which("piper")


def stimm_pfad(name: str) -> Path:
    return config.voices_dir() / f"{name}.onnx"


def verfuegbar(name: str | None = None) -> tuple[bool, str]:
    """(nutzbar, Begruendung) — fuer die Anzeige im Setup."""
    if piper_binary() is None:
        return False, ("Piper ist nicht installiert. Der MP4-Modus braucht es; "
                       "der HTML-Modus funktioniert ohne.")
    name = name or config.load_safe().tts_stimme or DEFAULT_STIMME
    pfad = stimm_pfad(name)
    if not pfad.is_file():
        return False, (f"Die Stimmdatei {name}.onnx fehlt in /data/stimmen. "
                       "Sie wird beim ersten MP4 automatisch geladen — dafür "
                       "braucht der Container einmal Internetzugang.")
    if not shutil.which("ffmpeg"):
        return False, ("ffmpeg ist nicht installiert. Der MP4-Modus braucht es; "
                       "der HTML-Modus funktioniert ohne.")
    return True, f"Piper mit {STIMMEN.get(name, name)} ist einsatzbereit."


def sprechen(text: str, ziel: Path, stimme: str | None = None) -> Path:
    """Erzeugt eine WAV-Datei aus Text. Wirft TtsUnavailable, wenn es nicht geht."""
    binary = piper_binary()
    if binary is None:
        raise TtsUnavailable("Piper ist in diesem Container nicht installiert.")
    stimme = stimme or config.load_safe().tts_stimme or DEFAULT_STIMME
    modell = stimm_pfad(stimme)
    if not modell.is_file():
        raise TtsUnavailable(
            f"Die Stimmdatei {stimme}.onnx fehlt in /data/stimmen.")

    ziel.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [binary, "--model", str(modell), "--output_file", str(ziel)],
            input=text, text=True, capture_output=True, timeout=180, check=False)
    except subprocess.TimeoutExpired:
        raise TtsUnavailable("Die Sprachausgabe hat zu lange gedauert.") from None
    except OSError as exc:
        raise TtsUnavailable(f"Piper ließ sich nicht starten: {exc}") from None

    if proc.returncode != 0 or not ziel.is_file() or ziel.stat().st_size == 0:
        raise TtsUnavailable(
            "Piper hat keine Audiodatei erzeugt: "
            + ((proc.stderr or "").strip()[:200] or "keine Meldung"))
    return ziel


def dauer_sekunden(wav: Path) -> float:
    """Länge einer WAV-Datei — nötig, damit die Folie so lange stehen bleibt."""
    try:
        with wave.open(str(wav), "rb") as f:
            rate = f.getframerate() or 22050
            return round(f.getnframes() / rate, 3)
    except (wave.Error, OSError) as exc:
        log.warning("Dauer von %s nicht lesbar: %s", wav.name, exc)
        return 6.0
