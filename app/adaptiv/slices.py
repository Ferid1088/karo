"""Kuratierte Fach-Slices in die lokale Lernbibliothek saeen.

Die Quelle liegt in `karo_contract.slices` — derselbe Bestand, den der
Lehrplan-Dienst in seine Datenbank schreibt. Karo liest ihn ueber denselben
geprueften Pfad wie jede gelieferte Lektion (`erzeugung.speichern`), damit
lokale und importierte Inhalte nicht auseinanderlaufen.

Zwei Dinge machen das Saeen mehr als ein Kopieren:

* `lern_curriculum_import` bekommt pro Konzept eine Herkunftszeile mit der
  Dienst-ID — so findet `voraussetzungen()` die Voraussetzung spaeter als
  lokale Konzept-ID wieder, und der Umweg kann zurueckkehren.
* `lern_voraussetzung` bekommt die Kanten des Slice-Graphen — derselbe
  Graph, den eine Lieferung aus dem Dienst mitbringen wuerde.

Idempotent: `erzeugung.speichern` ist ueber (fach, thema_key, konzept_key,
Klasse) eindeutig, die Herkunftszeile ueber ihren Fingerabdruck.
"""

from __future__ import annotations

import hashlib
import json

import karo_contract.slices as kuratiert

from .. import db


def _fingerprint(service_id: str, lektion: dict) -> str:
    provenance = {"service": "kuratiert", "concept_id": service_id,
                  "lesson": lektion}
    return hashlib.sha256(json.dumps(provenance, sort_keys=True,
                                     ensure_ascii=False).encode()).hexdigest()


def seed(faecher: set[str] | None = None) -> dict:
    """Schreibt die kuratierten Slices ins lokale Lernangebot.

    Gibt je Fach die Zahl der neu angelegten Konzepte zurueck.
    """
    from . import erzeugung, store
    gezaehlt: dict[str, int] = {}
    titel = {}
    for fach, slice_ in kuratiert.SLICES.items():
        if faecher and fach not in faecher:
            continue
        for block in slice_["blocks"]:
            for konzept in block["concepts"]:
                titel[konzept["id"]] = konzept["title"]
                vorher = store.konzept_nach_key(
                    fach, konzept["lektion"]["konzept"]["thema_key"],
                    konzept["lektion"]["konzept"]["konzept_key"])
                konzept_id = erzeugung.speichern(
                    konzept["lektion"], fach, quelle="kuratiert")
                provenance = {
                    "service": "kuratiert",
                    "concept_id": konzept["id"],
                    "version": 1,
                    "classification": {
                        "source": "approved_curriculum",
                        "first_contact_grade": konzept["first_contact_grade"],
                        "target_grade": konzept["target_grade"]},
                    "subject": fach, "format": "karo-adaptiv-v1.5"}
                store.curriculum_import_sichern(
                    _fingerprint(konzept["id"], konzept["lektion"]),
                    konzept_id, provenance)
                store.voraussetzungen_sichern(
                    konzept_id,
                    [{"concept_id": v, "title": titel.get(v)}
                     for v in konzept.get("prerequisites") or []])
                if not vorher:
                    gezaehlt[fach] = gezaehlt.get(fach, 0) + 1
    return gezaehlt


def gezaehlt() -> dict:
    """Wie viele Slice-Konzepte je Fach bereits lokal stehen."""
    return {r["fach"]: r["n"] for r in db.q(
        """SELECT k.fach, count(*) AS n
             FROM lern_curriculum_import i
             JOIN lern_konzept k ON k.id = i.konzept_id
            WHERE json_extract(i.provenance, '$.service') = 'kuratiert'
            GROUP BY k.fach""")}
