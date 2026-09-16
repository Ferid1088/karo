#!/usr/bin/env python3
"""Haengt „Meine Woche" in app/main.py ein — zwei Zeilen, nichts sonst.

Aufruf im karo-Ordner:

    python3 einbau.py

Das Skript ist absichtlich stur und vorsichtig:

* Es aendert genau zwei Stellen: den Import und das include_router.
* Es laesst sich mehrfach aufrufen. Ist der Begleiter schon eingehaengt,
  passiert nichts.
* Es legt vorher eine Sicherung app/main.py.vorher an.
* Findet es die Stellen nicht, aendert es nichts und sagt, was von Hand zu
  tun ist. Lieber gar nichts als eine kaputte main.py.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

IMPORT_ZEILE = "from .woche import router as woche"
ROUTER_ZEILE = "app.include_router(woche.router)"
KOMMENTAR = ('# „Meine Woche" — eigenstaendiger Begleiter unter /woche. Legt sein\n'
             "# Schema beim ersten Aufruf selbst an und beruehrt keine Karo-Tabelle.")


def main() -> int:
    pfad = Path("app/main.py")
    if not pfad.is_file():
        print("Hier ist kein karo. Bitte im Ordner mit docker-compose.yml "
              "aufrufen.")
        return 1

    text = pfad.read_text(encoding="utf-8")

    if IMPORT_ZEILE in text and ROUTER_ZEILE in text:
        print("Schon eingehängt — nichts zu tun.")
        return 0

    zeilen = text.splitlines()

    # 1) Import direkt nach dem letzten „from .“-Import.
    letzter_import = None
    for i, z in enumerate(zeilen):
        if z.startswith("from .") or z.startswith("from . import"):
            letzter_import = i
    if letzter_import is None:
        print(hilfe_text())
        return 1

    # 2) include_router nach dem letzten bestehenden include_router.
    letzter_router = None
    for i, z in enumerate(zeilen):
        if z.strip().startswith("app.include_router("):
            letzter_router = i
    if letzter_router is None:
        print(hilfe_text())
        return 1

    shutil.copy2(pfad, pfad.with_suffix(".py.vorher"))

    # Von hinten nach vorn einfuegen, damit die Zeilennummern stimmen bleiben.
    if ROUTER_ZEILE not in text:
        zeilen.insert(letzter_router + 1, KOMMENTAR)
        zeilen.insert(letzter_router + 2, ROUTER_ZEILE)
    if IMPORT_ZEILE not in text:
        zeilen.insert(letzter_import + 1, IMPORT_ZEILE)

    pfad.write_text("\n".join(zeilen) + "\n", encoding="utf-8")

    print("Eingehängt:")
    print(f"  Zeile {letzter_import + 2}: {IMPORT_ZEILE}")
    print(f"  weiter unten:  {ROUTER_ZEILE}")
    print("Sicherung der alten Datei: app/main.py.vorher")
    print()
    print("Weiter mit:  make up        (baut neu und startet)")
    print("Dann:        http://127.0.0.1:8080/woche")
    return 0


def hilfe_text() -> str:
    return (
        "Die Stellen in app/main.py sind nicht eindeutig zu finden.\n"
        "Nichts geändert. Bitte von Hand zwei Zeilen ergänzen:\n\n"
        "  1. oben bei den anderen Importen:\n"
        f"       {IMPORT_ZEILE}\n\n"
        "  2. unten bei den anderen Routern:\n"
        f"       {ROUTER_ZEILE}\n")


if __name__ == "__main__":
    sys.exit(main())
