#!/usr/bin/env python3
"""Misst, wie gut Karo Blätter liest — ausschliesslich lokal.

Die Frage, an der Schritt 2 haengt: trifft die Themenzuordnung aus dem
gelesenen Text das Thema, das fuer dieses Blatt schon bestaetigt in der
Datenbank steht? Zielwert 90 % in den Top 3.

Gemessen wird an echten Blaettern dieser Familie. Die bleiben hier:

  * Gelesen wird aus einem Ordner, den `.gitignore` ausschliesst.
  * Kein Blatt und kein Text daraus geht ins Repository, in die CI oder an
    eine KI. Diese Datei ruft kein Modell — sie kann es nicht.
  * Ins Repository kommt nur die Kennzahl, und die traegt keinen Inhalt.

    python3 tools/ocr_report.py --quelle ~/karo-ocr-proben --db /pfad/karo.db

Ohne `--quelle` nimmt das Skript `ocr-proben/` neben dem Repository.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

BILD = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
TOP = 3
ZIEL = 0.90


def arten(pfad: Path, doc) -> str:
    """Foto, PDF mit Textebene oder gescanntes PDF — getrennt ausgewiesen.

    Zusammengerechnet saehe eine gute Zahl fuer PDFs mit Textebene wie eine
    gute Zahl fuers Fotografieren aus. Das waere die falsche Beruhigung.
    """
    if pfad.suffix.lower() != ".pdf":
        return "foto"
    if doc and any(len(doc.text(i)) >= 40 for i in range(min(doc.page_count, 3))):
        return "pdf-text"
    return "pdf-scan"


def lesen(pfad: Path) -> tuple[str, str]:
    """Text und Art. Benutzt denselben Serverweg wie der Rueckfall im Browser."""
    from app import blatt_text, ingest
    doc = None
    try:
        if pfad.suffix.lower() == ".pdf":
            doc = ingest._open_pdf(pfad)
        art = arten(pfad, doc)
    finally:
        if doc:
            doc.close()
    return blatt_text.server_lesen(pfad), art


def erwartet(db: sqlite3.Connection, name: str) -> list[str]:
    """Das Thema, das fuer dieses Blatt schon bestaetigt in der Datenbank steht."""
    db.row_factory = sqlite3.Row
    zeilen = db.execute(
        """SELECT DISTINCT coalesce(t.label, d.themenname) AS label
             FROM document d
             LEFT JOIN kb_chunk k ON k.document_id = d.id
             LEFT JOIN topic t ON t.id = k.topic_id
            WHERE d.source_name = ? AND coalesce(t.label, d.themenname) IS NOT NULL""",
        (name,)).fetchall()
    return [z["label"] for z in zeilen]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--quelle", default=str(WURZEL / "ocr-proben"))
    p.add_argument("--db", default=str(Path.home() / "karo-data" / "data" / "karo.db"))
    p.add_argument("--bericht", default=str(WURZEL / "docs" / "OCR_TREFFERQUOTE.md"))
    args = p.parse_args(argv)

    quelle = Path(args.quelle).expanduser()
    if not quelle.is_dir():
        print(f"Kein Probenordner unter {quelle}.\n"
              "Lege dort Blaetter ab (sie bleiben dort) oder gib --quelle an.")
        return 2

    from app import blatt_text, config
    if not blatt_text.server_lesen_moeglich():
        print("tesseract fehlt auf diesem Rechner. Im Container ist es dabei:\n"
              "  docker compose exec karo python tools/ocr_report.py ...")
        return 2
    config.load_safe()

    db = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    dateien = sorted(f for f in quelle.rglob("*")
                     if f.is_file() and (f.suffix.lower() in BILD or f.suffix.lower() == ".pdf"))
    if not dateien:
        print(f"Keine Blaetter in {quelle}.")
        return 2

    zaehler = defaultdict(lambda: {"gesamt": 0, "treffer": 0, "ohne_erwartung": 0,
                                   "zu_wenig_text": 0})
    for pfad in dateien:
        try:
            text, art = lesen(pfad)
        except Exception as fehler:            # noqa: BLE001 - eine kaputte Datei stoppt nichts
            print(f"  ! {pfad.name}: {fehler}")
            continue
        topf = zaehler[art]
        topf["gesamt"] += 1
        if len(text.strip()) < 40:
            topf["zu_wenig_text"] += 1
            continue
        soll = erwartet(db, pfad.name)
        if not soll:
            topf["ohne_erwartung"] += 1
            continue
        vorschlaege = blatt_text.vorschlaege(text, "mathematik")[:TOP]
        namen = {v["label"].lower() for v in vorschlaege}
        if any(s.lower() in namen for s in soll):
            topf["treffer"] += 1

    print(f"\n{len(dateien)} Blaetter aus {quelle}\n")
    zeilen = []
    for art in ("foto", "pdf-text", "pdf-scan"):
        t = zaehler.get(art)
        if not t or not t["gesamt"]:
            zeilen.append((art, None, 0))
            print(f"  {art:<9} keine Proben")
            continue
        bewertbar = t["gesamt"] - t["ohne_erwartung"]
        quote = (t["treffer"] / bewertbar) if bewertbar else 0.0
        zeilen.append((art, quote, bewertbar))
        print(f"  {art:<9} {t['treffer']}/{bewertbar} = {quote:.0%}"
              f"   (ohne hinterlegtes Thema: {t['ohne_erwartung']}, "
              f"zu wenig Text: {t['zu_wenig_text']})")

    bericht = Path(args.bericht)
    bericht.parent.mkdir(parents=True, exist_ok=True)
    bericht.write_text(
        "# Trefferquote beim Lesen von Blättern\n\n"
        "Gemessen lokal mit `make ocr-report` an echten Blättern dieser Familie.\n"
        "Die Blätter und ihr Text bleiben auf dem Rechner — hier steht nur die Zahl.\n"
        f"Zielwert: richtiges Thema unter den Top {TOP} in ≥ {ZIEL:.0%}.\n\n"
        "| Art | bewertbare Blätter | Trefferquote |\n|---|---|---|\n"
        + "".join(f"| {a} | {n} | {('%.0f %%' % (q * 100)) if q is not None else '— keine Proben'} |\n"
                 for a, q, n in zeilen),
        encoding="utf-8")
    print(f"\nKennzahl geschrieben: {bericht.relative_to(WURZEL)}")

    gemessen = [q for _, q, n in zeilen if q is not None and n]
    if gemessen and min(gemessen) < ZIEL:
        print(f"Unter dem Zielwert von {ZIEL:.0%}.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
