"""Welche Lektionen es wirklich gibt.

Bis ein Thema automatisch in Konzepte und Fehlertypen zerlegt wird
(01_ARCHITECTURE.md §2, Tier 3 in §6 — Meilenstein 4), kann Karo nur das
unterrichten, was jemand von Hand verfasst hat.

Diese Datei macht genau das sichtbar. Vorher hat die Route still immer die
Bruchlektion geliefert, egal welches Thema jemand meinte — das sah nach
einem allgemeinen System aus und war keines. Lieber ehrlich sagen, was da
ist, als so tun, als sei alles da.
"""

from __future__ import annotations

from . import inhalte_brueche, store
from .normalisierung import normalisiere_thema

#: Verfasste Lektionen. Sie saeen ihren Inhalt in den Katalog — gefunden
#: wird danach ueber den Katalog, nicht ueber diese Liste.
MODULE = (inhalte_brueche,)


def saee_alle() -> None:
    """Idempotent — darf bei jedem Aufruf laufen."""
    for modul in MODULE:
        modul.saeen()


def verfuegbar() -> list[dict]:
    """Alle auslieferbaren Lektionen — aus dem Katalog, nicht aus `MODULE`.

    `MODULE` sagt nur noch, was gesaet wird. Was es *gibt*, steht in
    `lern_konzept`: sonst waere eine Lektion, die niemand als Python-Modul
    geschrieben hat, grundsaetzlich unauffindbar.
    """
    saee_alle()
    return [{"konzept_id": k["id"], "label": k["label"], "fach": k["fach"],
             "konzept_key": k["konzept_key"], "stichworte": k["stichworte"]}
            for k in store.konzepte_verfuegbar()]


def _trifft(gesucht: str, lektion: dict) -> bool:
    """Stichworte gehoeren zum Konzept, nicht in eine Tabelle daneben.

    Sie benennen das **Konzept**, nicht das Thema: „brueche" oder „nenner"
    traefe jedes Bruchthema und damit auch „Brueche kuerzen" — eine andere
    Fehlvorstellung als das Addieren (01_ARCHITECTURE.md §2).
    """
    for wort in lektion.get("stichworte") or ():
        muster = normalisiere_thema(wort)
        if muster and (muster in gesucht or gesucht in muster):
            return True
    return gesucht in normalisiere_thema(lektion["label"])


def fuer_thema(thema_text: str | None) -> dict | None:
    """Die passende Lektion — oder None, und dann wird das auch gesagt.

    Bewusst ein simpler Stichwortabgleich: eine echte Zuordnung beliebiger
    Themen braucht die Zerlegung aus Meilenstein 4. Was hier nicht trifft,
    darf nicht heimlich in der Bruchlektion landen.
    """
    gesucht = normalisiere_thema(thema_text)
    if not gesucht:
        return None
    for lektion in verfuegbar():
        if _trifft(gesucht, lektion):
            return lektion
    return None
