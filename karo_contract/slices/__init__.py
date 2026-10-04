"""Kuratierte vertikale Curriculum-Slices — die gemeinsame Wahrheit beider
Repositories.

Jede Datei hier beschreibt für ein Fach einen vollständigen vertikalen
Schnitt: vom Zielkonzept über seine Voraussetzungen bis zu einem fachlich
sinnvollen Level 0 (der elementarsten Stufe, die das Kind sicher beherrschen
muss). Beide Seiten lesen dieselbe Quelle:

* karo-curriculum-team säät daraus `curriculum.concepts`, Kanten,
  Misconceptions und Diagnose-/Abschlussaufgaben (`kcteam.slices`).
* Karo säät daraus seine lokale Lernbibliothek über den echten
  Importpfad (`app.adaptiv.slices` → `erzeugung.speichern`).

Jedes Konzept trägt zwei Sichten auf denselben Stoff:

* die Dienst-Metadaten (`levels`, `can_do`, `difficulty_parameters`,
  `anchor_items`, `boundary_items`, `diagnostics`) — sie machen den
  Level-Graph und die Diagnose des Curriculum-Dienstes aus;
* die `lektion` im Format `karo-adaptiv-v1` — der Lehrkörper mit
  Fehlvorstellungen, Erklärvarianten, Aufgaben und Rubriken, den Karo
  validiert und unterrichtet.

Kuratiert heißt: jedes Wort steht hier mit Absicht. Wer einen Slice ändert,
ändert beide Seiten zugleich — darum hängt ein Test an diesem Paket.
"""

from __future__ import annotations

from typing import Any

from . import biologie, chemie, deutsch, englisch, mathematik, physik

#: Fach (Karo-Schlüssel) -> Slice-Definition.
SLICES: dict[str, dict[str, Any]] = {
    "mathematik": mathematik.SLICE,
    "deutsch": deutsch.SLICE,
    "englisch": englisch.SLICE,
    "biologie": biologie.SLICE,
    "physik": physik.SLICE,
    "chemie": chemie.SLICE,
}


for _k in (k for s in SLICES.values() for b in s["blocks"] for k in b["concepts"]):
    # Die Einordnung des Konzepts gilt, die der Lektion spiegelt sie nur —
    # sonst laufen beide auseinander und die Hüllenprüfung lehnt zu Recht ab.
    _k["lektion"]["konzept"]["klasse_von"] = _k["first_contact_grade"]
    _k["lektion"]["konzept"]["klasse_bis"] = _k["target_grade"]


def konzepte() -> list[dict[str, Any]]:
    """Alle Konzepte aller Slices, in der Reihenfolge ihrer Dateien."""
    return [k for s in SLICES.values()
            for b in s["blocks"] for k in b["concepts"]]


def konzept(concept_id: str) -> dict[str, Any] | None:
    """Ein Konzept über seine Dienst-Id finden (``MA.GEO.QUADERVOLUMEN``)."""
    return next((k for k in konzepte() if k["id"] == concept_id), None)



from ._bauen import aufgabe, auswahl, choice, item, number, text

__all__ = ["SLICES", "konzepte", "konzept",
           "aufgabe", "auswahl", "choice", "item", "number", "text"]
