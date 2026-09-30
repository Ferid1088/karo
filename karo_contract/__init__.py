"""Was Karo und der Lehrplan-Dienst gemeinsam ueber eine Lektion wissen.

Vorher prueften zwei Stellen dasselbe: der Dienst gab eine Lektion frei,
Karo lehnte sie beim Import ab, und nach zwei Ablehnungen war das Thema
dauerhaft unlieferbar. Nicht weil die Lektion schlecht war, sondern weil
die zweite Pruefung strenger war als die erste — und niemand konnte das
sehen, weil sie in zwei Repositories lagen.

Jetzt ist es eine Pruefung. Der Dienst installiert dieses Paket

    pip install "karo-contract @ git+https://github.com/Ferid1088/karo.git"

und ruft `pruefe()`, bevor eine Lektion „fertig" wird. Was hier durchfaellt,
geht als Befund an den Autor zurueck, statt beim Abnehmer als Ablehnung zu
landen. Das Paket haengt an nichts aus `app/` und an keiner Datenbank.
"""
from __future__ import annotations

from . import faecher, huelle, komponenten, normalisierung, rechnen, schemas
from .huelle import FORMAT_ID, VertragVerletzt
from .schemas import InhaltUngueltig

#: Muss auf beiden Seiten gleich sein. Karo prueft das vor jedem Auftrag
#: gegen `GET /v1/meta` des Dienstes.
CONTRACT_VERSION = "karo-adaptiv-v1.1"

__all__ = ["CONTRACT_VERSION", "FORMAT_ID", "InhaltUngueltig", "VertragVerletzt",
           "faecher", "huelle", "komponenten", "normalisierung", "pruefe",
           "pruefe_lektion", "rechnen", "schemas"]


def pruefe_lektion(lektion, thema: str | None = None) -> dict:
    """Die Lektion selbst: Schema, Register, Rechenwege, Aufgaben.

    Gibt sie gesaeubert zurueck oder wirft `InhaltUngueltig`.
    """
    geprueft = schemas.pruefe_lektion(lektion)
    if "erstkontakt" not in geprueft:
        raise InhaltUngueltig("Einstieg in die Lernreihe fehlt.")
    _pruefe_thema_und_aufgaben(geprueft, thema)
    return geprueft


def _pruefe_thema_und_aufgaben(geprueft: dict, thema: str | None) -> None:
    if thema and not huelle.trifft_thema(normalisierung.normalisiere_thema(thema),
                                         geprueft["konzept"]):
        raise InhaltUngueltig("Die Lernreihe passt nicht zum angefragten Thema.")
    # Immer wieder dieselbe Zahlenuebung macht sichtbaren Erfolg bedeutungslos.
    for fehlertyp in geprueft["fehlertypen"]:
        fragen = [normalisierung.normalisiere_thema(fehlertyp["aufgaben"][rolle]["frage"])
                  for rolle in ("beispiel", "gefuehrt", "selbststaendig")]
        if len(set(fragen)) != len(fragen):
            raise InhaltUngueltig("Beispiel und Übungsaufgaben müssen verschieden sein.")


def pruefe(antwort: dict, *, thema: str | None = None, fach: str | None = None) -> dict:
    """Eine ganze Lieferung pruefen — Huelle und Lektion.

    Gibt die gesaeuberte Lektion zurueck. Wirft `VertragVerletzt`, wenn die
    Huelle nicht stimmt (kein neuer Text hilft), sonst `InhaltUngueltig`.
    """
    # Erst die Huelle, ganz. Ein fehlendes Pflichtfeld darf nicht hinter
    # einer Beschwerde ueber den Inhalt verschwinden — es heisst etwas
    # anderes und hat andere Folgen.
    huelle.pruefe_huelle(antwort, fach)
    von, bis = huelle.pruefe_einordnung(antwort)
    geprueft = schemas.pruefe_lektion(antwort.get("lesson"))
    if "erstkontakt" not in geprueft:
        raise InhaltUngueltig("Einstieg in die Lernreihe fehlt.")
    huelle.pruefe_konzeptklasse(geprueft["konzept"], von, bis)
    _pruefe_thema_und_aufgaben(geprueft, thema)
    return geprueft


def befunde(antwort: dict, *, thema: str | None = None, fach: str | None = None) -> list[str]:
    """Dasselbe, aber als Liste statt als Ausnahme.

    Fuer den Lehrplan-Dienst: er gibt die Befunde dem Autor der Lektion
    weiter, statt sie als Ablehnung beim Abnehmer entstehen zu lassen.
    Leere Liste heisst: Karo wuerde diese Lieferung annehmen.
    """
    try:
        pruefe(antwort, thema=thema, fach=fach)
    except InhaltUngueltig as fehler:
        return [str(fehler)]
    except (ValueError, TypeError, KeyError) as fehler:
        return [f"Die Lieferung ist nicht lesbar: {fehler}"]
    return []
