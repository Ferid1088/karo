"""Tests für den Abbruch eines laufenden NotebookLM-Aufrufs.

`abbrechen()` in app/teaching.py setzt bisher nur einen DB-Zustand — ohne
eine Möglichkeit, den laufenden `notebooklm generate`-Unterprozess (bis zu
45 Minuten) tatsächlich zu beenden, läuft er trotzdem bis zum Ende durch.
Diese Tests belegen, dass `_run_abbrechbar` den Unterprozess wirklich
beendet, sobald die übergebene Abbruchprüfung True liefert.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from app.media import notebooklm


@pytest.fixture(autouse=True)
def _daten_verzeichnis(tmp_path, monkeypatch):
    # Bewusst ueber die im notebooklm-Modul gebundene Referenz patchen, nicht
    # ueber einen frischen `from app import config`-Import: andere Tests im
    # selben Lauf laden `app.config` per `importlib.reload()` neu, wodurch
    # `sys.modules["app.config"]` ein anderes Objekt waere als das, auf das
    # `notebooklm.config` tatsaechlich zeigt.
    monkeypatch.setattr(notebooklm.config, "DATA_DIR", tmp_path)


def test_abbruch_beendet_den_laufenden_unterprozess(monkeypatch):
    """Ein Aufruf, der sonst lange liefe, wird beim naechsten Poll gekillt."""
    monkeypatch.setattr(notebooklm, "CANCEL_POLL_SECONDS", 0.05)

    # Ein Python-Ein-Zeiler, der viel laenger schlaeft als der Test warten soll.
    schlafbefehl = [sys.executable, "-c", "import time; time.sleep(30)"]
    monkeypatch.setattr(notebooklm, "CLI", schlafbefehl[0])

    aufrufe = {"n": 0}

    def abgebrochen() -> bool:
        aufrufe["n"] += 1
        return aufrufe["n"] >= 2

    with pytest.raises(notebooklm.Abgebrochen):
        notebooklm._run_abbrechbar(
            *schlafbefehl[1:], timeout=30, abgebrochen=abgebrochen)

    assert aufrufe["n"] >= 2


def test_ohne_abbruch_laeuft_der_aufruf_zu_ende(monkeypatch):
    monkeypatch.setattr(notebooklm, "CANCEL_POLL_SECONDS", 0.05)
    schlafbefehl = [sys.executable, "-c",
                    "import json; print(json.dumps({'status': 'completed'}))"]
    monkeypatch.setattr(notebooklm, "CLI", schlafbefehl[0])

    antwort = notebooklm._run_abbrechbar(
        *schlafbefehl[1:], timeout=5, abgebrochen=lambda: False)
    assert antwort.get("status") == "completed"
