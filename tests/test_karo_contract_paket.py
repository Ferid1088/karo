"""`karo_contract` muss ohne Karo laufen — sonst kann der Dienst es nicht nutzen.

Die Pruefung, die Karo beim Import faehrt, lag in `app/`. Der Lehrplan-Dienst
konnte sie nicht importieren und hatte eine eigene, etwas andere: er gab eine
Lektion frei, Karo lehnte sie ab, und nach zwei Ablehnungen war das Thema
dauerhaft leer. Jetzt ist es ein installierbares Paket. Diese Datei haelt fest,
dass es das auch bleibt.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent


def test_paket_importiert_nichts_aus_app():
    """Ein Import aus `app` waere im Dienst ein ImportError."""
    quelle = " ".join(p.read_text(encoding="utf-8")
                      for p in sorted((WURZEL / "karo_contract").glob("*.py")))
    for verboten in ("from app", "import app", "from .. import", "from ..adaptiv"):
        assert verboten not in quelle, f"{verboten} steht in karo_contract"


def test_laeuft_in_einem_prozess_ohne_karo_auf_dem_pfad():
    """Ohne das Repo im Pfad: nur das Paket, sonst nichts."""
    programm = (
        "import sys, json;"
        "sys.path.insert(0, %r);"
        "import karo_contract as kc;"
        "print(json.dumps([kc.CONTRACT_VERSION, kc.FORMAT_ID,"
        " kc.befunde({'format': 'karo-adaptiv-v1'})]))" % str(WURZEL))
    fertig = subprocess.run([sys.executable, "-c", programm], capture_output=True,
                            text=True, cwd="/", env={"PATH": "/usr/bin:/bin"})
    assert fertig.returncode == 0, fertig.stderr
    fassung, format_id, befunde = __import__("json").loads(fertig.stdout)
    assert fassung.startswith("karo-adaptiv-") and format_id == "karo-adaptiv-v1"
    assert befunde == ["Format oder Inhaltsversion fehlt."]


def test_pyproject_liefert_nur_das_paket_aus():
    text = (WURZEL / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "karo-contract"' in text
    assert 'include = ["karo_contract*"]' in text
    assert "dependencies = []" in text      # keine App, keine Datenbank, kein Web


def test_karo_prueft_ueber_dasselbe_paket():
    """Karos Import ruft `karo_contract.pruefe` — nicht eine zweite Kopie."""
    import karo_contract
    from app.adaptiv import curriculum_dienst as cd
    assert cd.CONTRACT_VERSION == karo_contract.CONTRACT_VERSION
    assert cd.FORMAT_ID == karo_contract.FORMAT_ID
    gerufen = []
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(karo_contract, "pruefe",
                   lambda a, **kw: gerufen.append(kw) or {"konzept": {}})
        cd._checked({"x": 1}, "Würfel: Volumen", 6, "mathematik")
    assert gerufen == [{"thema": "Würfel: Volumen", "fach": "mathematik"}]


def test_befunde_statt_ausnahme_fuer_den_dienst():
    """Der Dienst will eine Liste, keine Ausnahme: sie geht an den Autor."""
    import karo_contract
    from .test_lektion_erzeugung import _lektion
    gut = {"status": "ready", "format": "karo-adaptiv-v1", "subject": "Mathematik",
           "concept_id": "MA.GEO.WUERFEL", "concept_version": 1,
           "classification": {"source": "approved_curriculum",
                              "first_contact_grade": 5, "target_grade": 7},
           "lesson": _lektion()}
    assert karo_contract.befunde(gut, thema="Würfel: Volumen", fach="mathematik") == []
    ohne_einordnung = {**gut, "classification": {}}
    assert karo_contract.befunde(ohne_einordnung, thema="Würfel: Volumen",
                                 fach="mathematik") == [
        "Die Klasseneinordnung fehlt oder kommt nicht aus dem geprüften Curriculum."]
