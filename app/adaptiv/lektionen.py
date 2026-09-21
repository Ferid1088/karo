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
from .normalisierung import normalisiere

#: Jede Lektion ist ein Modul mit FACH/THEMA/KONZEPT und `saeen()`.
MODULE = (inhalte_brueche,)

#: Wonach ein Kind suchen könnte, damit „Brüche“ auch „Bruchrechnung“ findet.
STICHWORTE = {
    inhalte_brueche.KONZEPT: ("brueche", "bruch", "bruchrechnung",
                              "brueche addieren", "bruecheaddieren",
                              "ungleichnamig", "nenner"),
}


def saee_alle() -> None:
    """Idempotent — darf bei jedem Aufruf laufen."""
    for modul in MODULE:
        modul.saeen()


def verfuegbar() -> list[dict]:
    """Die verfassten Lektionen, mit ihrer Konzept-Id."""
    saee_alle()
    lektionen = []
    for modul in MODULE:
        konzept = store.konzept_nach_key(modul.FACH, modul.THEMA, modul.KONZEPT)
        if konzept:
            lektionen.append({"konzept_id": konzept["id"],
                              "label": konzept["label"],
                              "fach": konzept["fach"],
                              "konzept_key": konzept["konzept_key"]})
    return lektionen


def fuer_thema(thema_text: str | None) -> dict | None:
    """Die passende Lektion — oder None, und dann wird das auch gesagt.

    Bewusst ein simpler Stichwortabgleich: eine echte Zuordnung beliebiger
    Themen braucht die Zerlegung aus Meilenstein 4. Was hier nicht trifft,
    darf nicht heimlich in der Bruchlektion landen.
    """
    gesucht = normalisiere(thema_text)
    if not gesucht:
        return None
    for lektion in verfuegbar():
        stichworte = STICHWORTE.get(lektion["konzept_key"], ())
        if any(wort in gesucht or gesucht in wort for wort in stichworte):
            return lektion
        if gesucht in normalisiere(lektion["label"]):
            return lektion
    return None
