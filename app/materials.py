"""Dauerhaftes Materialarchiv: Metadaten und Dateiinhalt in einer SQLite-Datei."""
from __future__ import annotations

import dataclasses
import hashlib
import os
import sqlite3
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path

from . import config, db

_lock = threading.RLock()


def pfad(wert: str | None = None) -> Path:
    wert = config.load().material_db_path if wert is None else wert
    return Path(wert).expanduser().resolve() if wert else config.DATA_DIR / "lernmaterialien.sqlite3"


@contextmanager
def verbindung():
    # Hintergrundjobs und Pfadwechsel benutzen dieselbe Sperre. Verbindungen
    # werden nicht gecacht, damit jeder Zugriff den aktuellen Pfad verwendet.
    with _lock:
        ziel = pfad()
        ziel.parent.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(str(ziel), timeout=30)
        c.row_factory = sqlite3.Row
        try:
            c.execute("""CREATE TABLE IF NOT EXISTS material (
                art TEXT NOT NULL, referenz INTEGER NOT NULL,
                titel TEXT NOT NULL, dateiname TEXT NOT NULL,
                mime TEXT NOT NULL, inhalt BLOB NOT NULL, created_at TEXT NOT NULL,
                PRIMARY KEY (art, referenz))""")
            with c:
                yield c
        finally:
            c.close()


def titel(thema: str, erklaerung: str, runde: int, referenz: int,
          variante: int | None = None) -> str:
    name = " ".join(erklaerung.split())[:100] or thema
    if thema.casefold() not in name.casefold():
        name = f"{thema[:80]} – {name}"
    suffix = f" · Variante {variante}" if variante is not None else ""
    return f"{name} · {db.today()} · Runde {runde} · Material {referenz}{suffix}"


def dateiname(name: str) -> str:
    from .ingest import safe_name
    return safe_name(name[:75]) + "_" + hashlib.sha256(name.encode()).hexdigest()[:12]


def speichern(art: str, referenz: int, name: str, datei: str | None) -> None:
    from .teaching import TeachingError
    try:
        if not datei:
            raise OSError("Keine Materialdatei vorhanden.")
        quelle = Path(datei)
        mime = "video/mp4" if quelle.suffix.lower() == ".mp4" else "text/html"
        with verbindung() as c:
            c.execute("""INSERT INTO material VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(art, referenz) DO UPDATE SET titel=excluded.titel,
                dateiname=excluded.dateiname, mime=excluded.mime, inhalt=excluded.inhalt""",
                (art, referenz, name, dateiname(name) + quelle.suffix.lower(),
                 mime, quelle.read_bytes(), db.now()))
    except (OSError, sqlite3.Error) as exc:
        raise TeachingError(f"Lernmaterial konnte nicht in der Materialdatenbank gespeichert werden: {exc}") from exc


def holen(art: str, referenz: int) -> dict | None:
    with verbindung() as c:
        row = c.execute("SELECT * FROM material WHERE art=? AND referenz=?",
                        (art, referenz)).fetchone()
        return dict(row) if row else None


def bestand_uebernehmen() -> None:
    """Vorhandene Dateien einmal übernehmen; archivierte Inhalte behalten."""
    with verbindung() as c:
        vorhanden = {(r[0], r[1]) for r in c.execute("SELECT art, referenz FROM material")}
    for art, table, join in (
        ("runde", "lesson_round", "JOIN lesson l ON l.id=r.lesson_id"),
        ("variante", "lesson_round_variant", "JOIN lesson_round lr ON lr.id=r.lesson_round_id JOIN lesson l ON l.id=lr.lesson_id"),
    ):
        for row in db.q(f"SELECT r.*, t.label FROM {table} r {join} JOIN topic t ON t.id=l.topic_id WHERE r.material_pfad IS NOT NULL"):
            if (art, row["id"]) not in vorhanden and Path(row["material_pfad"]).is_file():
                name = f"{row['label']} · {row['created_at'][:10]} · {art.title()} {row['id']}"
                speichern(art, row["id"], name, row["material_pfad"])


def einstellungen_speichern(aenderungen: dict) -> None:
    """Archiv kopieren und erst nach Erfolg die Einstellung umstellen.

    Die bisherige Datei bleibt als Sicherung liegen. Ein bestehendes Ziel
    wird niemals überschrieben (auch keine fremde SQLite-Datenbank).
    """
    with _lock:
        cfg = config.load()
        wert = aenderungen.get("material_db_path", cfg.material_db_path).strip()
        if wert and (not Path(wert).expanduser().is_absolute()
                     or Path(wert).suffix.lower() not in (".db", ".sqlite", ".sqlite3")):
            raise ValueError("Bitte einen absoluten Dateipfad mit .db, .sqlite oder .sqlite3 angeben.")
        ziel, quelle = pfad(wert), pfad()
        entwurf = dataclasses.replace(cfg, **{**aenderungen, "material_db_path": str(ziel) if wert else ""})
        if ziel == quelle:
            config.save(entwurf)
            return
        if ziel.exists():
            raise ValueError("Am neuen Pfad existiert bereits eine Datei. Bitte einen freien Dateinamen wählen; bestehende Daten werden nicht überschrieben.")
        bestand_uebernehmen()
        ziel.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix=".material-", suffix=".sqlite3", dir=ziel.parent)
        os.close(fd)
        angelegt = False
        try:
            with verbindung() as source:
                dest = sqlite3.connect(temp)
                try:
                    source.backup(dest)
                    if dest.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise ValueError("Die kopierte Materialdatenbank ist beschädigt.")
                finally:
                    dest.close()
            os.link(temp, ziel)  # atomar, schlägt bei vorhandenem Ziel fehl
            angelegt = True
            config.save(entwurf)
        except BaseException:
            if angelegt:
                ziel.unlink()
            raise
        finally:
            Path(temp).unlink(missing_ok=True)
