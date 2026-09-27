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


def fuer_thema(thema_text: str | None, fach: str | None = None, klasse: int | None = None) -> dict | None:
    """Die passende Lektion — oder None, und dann wird das auch gesagt.

    Bewusst ein simpler Stichwortabgleich: eine echte Zuordnung beliebiger
    Themen braucht die Zerlegung aus Meilenstein 4. Was hier nicht trifft,
    darf nicht heimlich in der Bruchlektion landen.
    """
    gesucht = normalisiere_thema(thema_text)
    if not gesucht:
        return None
    for lektion in verfuegbar():
        if fach and normalisiere_thema(lektion['fach']) != normalisiere_thema(fach):
            continue
        konzept = store.konzept(lektion['konzept_id']) or {}
        if klasse and not konzept.get('klasse_von', 1) <= klasse <= konzept.get('klasse_bis', 13):
            continue
        if _trifft(gesucht, lektion):
            return lektion
    return None


#: Wörter, die in fast jedem deutschen Themennamen stehen. Sie stiften keine
#: Verwandtschaft: „Volumen bei VERSCHIEDENEN Maßeinheiten" und „Brüche mit
#: VERSCHIEDENEN Nennern addieren" haben nichts miteinander zu tun.
_FUELLWOERTER = frozenset({
    "und", "oder", "mit", "bei", "von", "der", "die", "das", "den", "dem",
    "ein", "eine", "einen", "einem", "im", "in", "zu", "zum", "zur", "auf",
    "fuer", "aus", "als", "am", "ist", "sind", "verschiedenen", "verschiedene",
    "verschiedener", "eines", "einer", "ganzen", "ganze",
})


def _sinnwoerter(text: str | None) -> set:
    """Die Wörter eines Themennamens, die etwas bedeuten."""
    return {w for w in normalisiere_thema(text).split()
            if len(w) > 2 and w not in _FUELLWOERTER}


def empfehlungen(thema_text: str | None, hoechstens: int = 3) -> list[dict]:
    """Verfasste Lektionen, die zum gefragten Thema gehören.

    Ein Vorschlag ist nur dann einer, wenn er mit der Frage zu tun hat.
    Vorher listete die Auswahlseite den gesamten Katalog — bei „Würfel:
    Volumen" also die Bruchlektion. Lieber gar kein Vorschlag als ein
    unpassender (§19: Fehlvorstellungen zählen mehr als Themenetiketten,
    und ein Etikett ohne Bezug zählt gar nichts).

    Bewusst ein Wortabgleich und keine Rangfolge nach Voraussetzungen: eine
    echte Voraussetzungskette gehört in den Katalog und nicht in eine
    Heuristik. Solange sie fehlt, ist „gemeinsames Stichwort" das Ehrlichste,
    was sich ohne Erfindung sagen lässt.
    """
    gesucht = _sinnwoerter(thema_text)
    if not gesucht:
        return []
    bewertet = []
    for lektion in verfuegbar():
        woerter = _sinnwoerter(lektion["label"])
        for wort in lektion.get("stichworte") or ():
            woerter |= _sinnwoerter(wort)
        gemeinsam = gesucht & woerter
        if gemeinsam:
            bewertet.append((len(gemeinsam), lektion["label"], lektion))
    bewertet.sort(key=lambda t: (-t[0], t[1]))
    return [lektion for _, _, lektion in bewertet[:hoechstens]]
