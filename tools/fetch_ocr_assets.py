#!/usr/bin/env python3
"""Holt die Browser-Dateien fuer OCR und PDF — in festen Fassungen, geprueft.

Karo liest Blaetter auf dem Geraet statt sie an ein Modell zu schicken. Dafuer
braucht der Browser Tesseract (WASM), die Sprachdaten deu+eng, pdf.js und
heic2any. Zusammen rund 25 MB — die gehoeren nicht in ein Repository, in dem
sonst nur Quelltext steht.

Also holt dieses Skript sie beim Image-Bau. Zwei Bedingungen, beide ohne
Ausnahme:

  * **Feste Fassungen.** Kein „latest": was heute geprueft wurde, soll morgen
    dasselbe sein.
  * **Jede Datei gegen eine eingecheckte SHA-256.** Stimmt eine nicht, bricht
    der Bau ab. Ein stillschweigend anderes WASM-Modul im Browser einer
    Familie waere genau die Art Vorfall, gegen die der ganze Schritt 1 war.

Zur Laufzeit laedt der Browser alles nur von diesem Server. Kein CDN: sonst
wuesste ein fremder Dienst bei jedem Blatt, dass hier gerade ein Kind lernt.

    python3 tools/fetch_ocr_assets.py [--ziel app/static] [--offline-ok]

`--offline-ok` ist fuer den Entwicklungsrechner ohne Netz: fehlende Dateien
werden dann gemeldet statt erzwungen. Im Image-Bau nie setzen.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
LISTE = WURZEL / "tools" / "ocr-assets.json"
NPM = "https://registry.npmjs.org/{name}/-/{kurz}-{version}.tgz"
TESSDATA = "https://github.com/{repo}/raw/{tag}/{datei}"
ZEITLIMIT = 300


class PruefsummeFalsch(SystemExit):
    """Abbruch: die geholte Datei ist nicht die erwartete."""


def _holen(url: str) -> bytes:
    print(f"  hole {url}")
    with urllib.request.urlopen(url, timeout=ZEITLIMIT) as antwort:
        return antwort.read()


def _pruefen(daten: bytes, erwartet: str, was: str) -> None:
    ist = hashlib.sha256(daten).hexdigest()
    if ist != erwartet:
        raise PruefsummeFalsch(
            f"ABBRUCH: {was} hat die Pruefsumme {ist},\n"
            f"         erwartet war {erwartet}.\n"
            "         Entweder wurde die Fassung veroeffentlicht veraendert, oder\n"
            "         jemand liefert etwas anderes aus. In beiden Faellen wird hier\n"
            "         nichts gebaut. Fassung pruefen und tools/ocr-assets.json\n"
            "         bewusst aktualisieren.")


def _schreiben(ziel: Path, daten: bytes) -> None:
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_bytes(daten)
    print(f"    -> {ziel.relative_to(WURZEL)} ({len(daten) // 1024} KB)")


def npm_paket(paket: dict, ziel: Path) -> None:
    kurz = paket["name"].split("/")[-1]
    url = NPM.format(name=paket["name"], kurz=kurz, version=paket["version"])
    roh = _holen(url)
    _pruefen(roh, paket["sha256"], f"{paket['name']}@{paket['version']}")
    with tarfile.open(fileobj=io.BytesIO(roh), mode="r:gz") as archiv:
        for drin, raus in paket["dateien"].items():
            glied = archiv.extractfile(drin)
            if glied is None:
                raise SystemExit(f"ABBRUCH: {drin} fehlt in {paket['name']}.")
            _schreiben(ziel / raus, glied.read())


def sprachdaten(abschnitt: dict, ziel: Path) -> None:
    for datei, angabe in abschnitt["sprachen"].items():
        url = TESSDATA.format(repo=abschnitt["repo"], tag=abschnitt["tag"], datei=datei)
        roh = _holen(url)
        _pruefen(roh, angabe["sha256"], f"{datei} ({abschnitt['tag']})")
        _schreiben(ziel / angabe["ziel"], roh)


def vollstaendig(plan: dict, ziel: Path) -> list[str]:
    """Welche Zieldateien fehlen."""
    erwartet = [r for p in plan["npm"] for r in p["dateien"].values()]
    erwartet += [a["ziel"] for a in plan["tessdata"]["sprachen"].values()]
    return [r for r in erwartet if not (ziel / r).is_file()]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--ziel", default=str(WURZEL / "app" / "static"))
    p.add_argument("--offline-ok", action="store_true",
                   help="ohne Netz nicht scheitern (nur fuer die Entwicklung)")
    p.add_argument("--nur-pruefen", action="store_true",
                   help="nichts holen, nur sagen, was fehlt")
    args = p.parse_args(argv)

    plan = json.loads(LISTE.read_text(encoding="utf-8"))
    ziel = Path(args.ziel)

    if args.nur_pruefen:
        fehlt = vollstaendig(plan, ziel)
        print("\n".join(f"fehlt: {f}" for f in fehlt) or "vollstaendig")
        return 1 if fehlt else 0

    try:
        for paket in plan["npm"]:
            print(f"{paket['name']}@{paket['version']}")
            npm_paket(paket, ziel)
        print(f"tessdata_fast@{plan['tessdata']['tag']}")
        sprachdaten(plan["tessdata"], ziel)
    except (urllib.error.URLError, TimeoutError, OSError) as fehler:
        if args.offline_ok:
            print(f"Kein Netz ({fehler}). Ohne die Dateien liest der Browser nicht; "
                  "die Serverseite bleibt als Rueckfall.", file=sys.stderr)
            return 0
        raise SystemExit(f"ABBRUCH: {fehler}") from None

    fehlt = vollstaendig(plan, ziel)
    if fehlt:
        raise SystemExit("ABBRUCH: nach dem Holen fehlen noch: " + ", ".join(fehlt))
    groesse = sum(f.stat().st_size for r in ("ocr", "pdfjs")
                  for f in (ziel / r).rglob("*") if f.is_file())
    print(f"Fertig. {groesse // 1024 // 1024} MB unter {ziel}/ocr und {ziel}/pdfjs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
