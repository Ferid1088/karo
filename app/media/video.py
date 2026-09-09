"""Ausgabemodus „mp4": eine echte Videodatei.

Weg: Folie als PNG rendern (Pillow, keine Browser-Engine im Image), Sprechtext
mit Piper vertonen, beides mit ffmpeg zu einem MP4 zusammensetzen. Die Datei
liegt danach im Drive-Ordner und läuft auf jedem Gerät, auch am Fernseher.

Wenn Piper oder ffmpeg fehlen, wirft dieses Modul `VideoUnavailable` mit einer
lesbaren Meldung — die Anwendung fällt dann auf den HTML-Modus zurück, statt
eine Fehlerseite zu zeigen.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .tts import TtsUnavailable, dauer_sekunden, sprechen

log = logging.getLogger("karo.video")

BREITE, HOEHE = 1280, 720
GRUND = (16, 19, 26)
KARTE = (25, 30, 40)
LINIE = (43, 50, 66)
TEXT = (238, 241, 246)
GEDAEMPFT = (152, 162, 181)
AKZENT = (139, 163, 255)
TAFELTEXT = (98, 196, 143)

_FONT_KANDIDATEN = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
_MONO_KANDIDATEN = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]


class VideoUnavailable(RuntimeError):
    """ffmpeg oder die Sprachausgabe fehlt."""


def _font(groesse: int, mono: bool = False, fett: bool = False):
    kandidaten = _MONO_KANDIDATEN if mono else _FONT_KANDIDATEN
    if fett:
        kandidaten = [k for k in kandidaten if "Bold" in k] + kandidaten
    for pfad in kandidaten:
        if Path(pfad).is_file():
            try:
                return ImageFont.truetype(pfad, groesse)
            except OSError:
                continue
    return ImageFont.load_default()


def verfuegbar() -> tuple[bool, str]:
    if not shutil.which("ffmpeg"):
        return False, ("ffmpeg ist nicht installiert. Ohne ffmpeg gibt es keine "
                       "MP4-Ausgabe — der HTML-Modus funktioniert weiter.")
    from .tts import verfuegbar as tts_verfuegbar

    return tts_verfuegbar()


# --------------------------------------------------------------------------
# Folie als Bild
# --------------------------------------------------------------------------

def folie_png(folie: dict, ziel: Path, nr: int, gesamt: int,
              thema: str = "") -> Path:
    bild = Image.new("RGB", (BREITE, HOEHE), GRUND)
    d = ImageDraw.Draw(bild)

    rand = 64
    d.rounded_rectangle([rand, rand, BREITE - rand, HOEHE - rand - 26],
                        radius=18, fill=KARTE, outline=LINIE, width=2)

    x = rand + 46
    y = rand + 40

    if thema:
        d.text((x, y), thema[:70], font=_font(20), fill=GEDAEMPFT)
        y += 34

    titel = str(folie.get("titel") or "")
    f_titel = _font(42, fett=True)
    for zeile in textwrap.wrap(titel, width=34)[:2]:
        d.text((x, y), zeile, font=f_titel, fill=TEXT)
        y += 52
    y += 14

    f_punkt = _font(27)
    for punkt in (folie.get("punkte") or [])[:5]:
        for i, zeile in enumerate(textwrap.wrap(str(punkt), width=54)[:2]):
            praefix = "•  " if i == 0 else "    "
            d.text((x, y), praefix + zeile, font=f_punkt, fill=TEXT)
            y += 38
        y += 4

    tafel = folie.get("tafel")
    if tafel:
        kasten_oben = max(y + 16, HOEHE - rand - 200)
        d.rounded_rectangle([x - 14, kasten_oben, BREITE - rand - 32,
                             HOEHE - rand - 60],
                            radius=12, fill=(12, 15, 21), outline=LINIE, width=1)
        f_mono = _font(34, mono=True)
        ty = kasten_oben + 22
        for zeile in str(tafel).splitlines()[:4]:
            for teil in textwrap.wrap(zeile, width=42)[:2] or [""]:
                d.text((x + 6, ty), teil, font=f_mono, fill=TAFELTEXT)
                ty += 42

    # Fortschritt
    bahn_y = HOEHE - 20
    d.line([rand, bahn_y, BREITE - rand, bahn_y], fill=LINIE, width=4)
    breite = (BREITE - 2 * rand) * nr / max(gesamt, 1)
    d.line([rand, bahn_y, rand + breite, bahn_y], fill=AKZENT, width=4)
    d.text((BREITE - rand - 74, HOEHE - rand - 46), f"{nr}/{gesamt}",
           font=_font(20), fill=GEDAEMPFT)

    ziel.parent.mkdir(parents=True, exist_ok=True)
    bild.save(ziel, "PNG", optimize=True)
    return ziel


# --------------------------------------------------------------------------
# Video zusammensetzen
# --------------------------------------------------------------------------

def bauen(titel: str, folien: list[dict], arbeit: Path, ziel: Path,
          thema: str = "", stimme: str | None = None) -> Path:
    """Baut das MP4. Wirft VideoUnavailable, wenn Werkzeuge fehlen."""
    if not shutil.which("ffmpeg"):
        raise VideoUnavailable("ffmpeg ist in diesem Container nicht installiert.")
    if not folien:
        raise VideoUnavailable("Es gibt keine Folien zum Vertonen.")

    arbeit.mkdir(parents=True, exist_ok=True)
    teile: list[Path] = []

    try:
        for i, folie in enumerate(folien, start=1):
            png = folie_png(folie, arbeit / f"folie{i:02d}.png", i, len(folien),
                            thema)
            wav = arbeit / f"stimme{i:02d}.wav"
            try:
                sprechen(str(folie.get("sprechtext") or folie.get("titel") or ""),
                         wav, stimme)
            except TtsUnavailable as exc:
                raise VideoUnavailable(str(exc)) from None

            dauer = max(2.5, dauer_sekunden(wav) + 0.6)
            teil = arbeit / f"teil{i:02d}.mp4"
            _ffmpeg([
                "-loop", "1", "-i", str(png), "-i", str(wav),
                "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k", "-shortest",
                "-t", f"{dauer:.2f}", "-r", "12", str(teil),
            ])
            teile.append(teil)

        liste = arbeit / "teile.txt"
        liste.write_text(
            "".join(f"file '{t.name}'\n" for t in teile), encoding="utf-8")
        ziel.parent.mkdir(parents=True, exist_ok=True)
        _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(liste),
                 "-c", "copy", str(ziel)], cwd=arbeit)
    finally:
        for muster in ("folie*.png", "stimme*.wav", "teil*.mp4", "teile.txt"):
            for datei in arbeit.glob(muster):
                try:
                    datei.unlink()
                except OSError:
                    pass

    if not ziel.is_file() or ziel.stat().st_size == 0:
        raise VideoUnavailable("ffmpeg hat keine Videodatei erzeugt.")
    return ziel


def _ffmpeg(args: list[str], cwd: Path | None = None) -> None:
    befehl = ["ffmpeg", "-y", "-loglevel", "error", *args]
    try:
        proc = subprocess.run(befehl, capture_output=True, text=True,
                              timeout=600, cwd=str(cwd) if cwd else None,
                              check=False)
    except subprocess.TimeoutExpired:
        raise VideoUnavailable("ffmpeg hat zu lange gebraucht.") from None
    if proc.returncode != 0:
        raise VideoUnavailable(
            "ffmpeg ist fehlgeschlagen: "
            + ((proc.stderr or "").strip()[:300] or "keine Meldung"))
