"""Ordnerauswahl innerhalb der dauerhaften Karo-Speicherorte."""
import os
from pathlib import Path

from .. import config, materials


def roots(kind: str) -> dict[str, Path]:
    if kind == "material":
        return {"drive": config.DRIVE_DIR.resolve()}
    if kind == "database":
        return {"data": config.DATA_DIR.resolve(), "drive": config.DRIVE_DIR.resolve()}
    raise ValueError("Unbekannter Speicherort.")


def directory(kind: str, root: str, relative: str) -> Path:
    base = roots(kind).get(root)
    if base is None:
        raise ValueError("Unbekannter Speicherort.")
    target = (base / relative).resolve()
    if not target.is_relative_to(base):
        raise ValueError("Dieser Ordner liegt außerhalb des Speicherorts.")
    if not target.is_dir():
        raise ValueError("Der Ordner ist nicht verfügbar.")
    return target


def browse(kind: str, root: str = "", relative: str = "") -> dict:
    available = roots(kind)
    if not root:
        cfg = config.load()
        current = (config.DRIVE_DIR / cfg.drive_subdir if kind == "material"
                   else materials.pfad().parent).resolve()
        root = next((key for key, base in available.items()
                     if current.is_relative_to(base)), next(iter(available)))
        base = available[root]
        relative = str(current.relative_to(base)) if current.is_relative_to(base) else ""
        if not (base / relative).is_dir():
            relative = ""
    target = directory(kind, root, relative)
    base = available[root]
    children = []
    for item in target.iterdir():
        if item.name.startswith("."):
            continue
        try:
            if item.is_dir() and item.resolve().is_relative_to(base):
                children.append(item.name)
        except OSError:
            continue
    rel = target.relative_to(base).as_posix()
    return {"root": root, "relative": "" if rel == "." else rel,
            "path": str(target), "folders": sorted(children, key=str.casefold),
            "roots": [{"id": key, "label": "Karo-Daten" if key == "data" else "Drive"}
                      for key in available]}


def select(kind: str, root: str, relative: str, filename: str = "") -> str:
    target = directory(kind, root, relative)
    if not os.access(target, os.W_OK | os.X_OK):
        raise ValueError("Der Ordner ist nicht beschreibbar.")
    if kind == "material":
        value = target.relative_to(config.DRIVE_DIR.resolve()).as_posix()
        return "" if value == "." else value
    filename = filename.strip()
    if (not filename or Path(filename).name != filename or "\\" in filename
            or Path(filename).suffix.lower() not in (".db", ".sqlite", ".sqlite3")):
        raise ValueError("Bitte einen Dateinamen mit .db, .sqlite oder .sqlite3 angeben.")
    path = target / filename
    if path.exists() and path.resolve() != materials.pfad().resolve():
        raise ValueError("Diese Datei existiert bereits. Bitte einen anderen Namen wählen.")
    return str(path)
