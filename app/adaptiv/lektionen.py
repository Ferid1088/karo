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

import threading

from karo_contract.huelle import (bedeutungswoerter, treffergrad,
                                  trifft_thema)

from . import inhalte_brueche, store
from .normalisierung import normalisiere_thema

#: Verfasste Lektionen. Sie saeen ihren Inhalt in den Katalog — gefunden
#: wird danach ueber den Katalog, nicht ueber diese Liste.
MODULE = (inhalte_brueche,)


def saee_alle() -> None:
    """Idempotent — darf bei jedem Aufruf laufen."""
    for modul in MODULE:
        modul.saeen()
    # Die kuratierten Fach-Slices aller sechs Faecher (karo_contract.slices):
    # derselbe Bestand, den der Lehrplan-Dienst saet — geht bei Karo durch
    # denselben geprueften Importpfad wie eine Lieferung. Der Schalter laesst
    # Fixture-Kataloge bewusst ohne den Slice-Bestand laufen.
    from .. import config
    if config.ops().curated_slices_enabled:
        from . import slices
        slices.seed()


_saat_lock = threading.Lock()
_module_gesaet = False
_slices_gesaet = False


def _saat_sicherstellen() -> None:
    """Die statischen Saaten einmal je Prozess.

    `saee_alle()` bleibt für Aufrufer, die wirklich nachsaen wollen —
    `verfuegbar()` fragte frueher bei jedem einzelnen Thema nach und
    schrieb dabei Hunderte Male denselben Bestand: ein Dashboard-Aufruf
    lief damit minutenlang nur Saat-Schleifen. Lieferungen landen auf
    ihrem eigenen Importpfad im Katalog und brauchen diese Saat nicht;
    der Lesezugriff danach bleibt live. Geht der Slice-Schalter erst
    spaeter an, zieht der naechste Aufruf die Slices nach.
    """
    global _module_gesaet, _slices_gesaet
    from .. import config
    if _module_gesaet and (_slices_gesaet
                           or not config.ops().curated_slices_enabled):
        return
    with _saat_lock:
        if not _module_gesaet:
            for modul in MODULE:
                modul.saeen()
            _module_gesaet = True
        if config.ops().curated_slices_enabled and not _slices_gesaet:
            from . import slices
            slices.seed()
            _slices_gesaet = True


def verfuegbar(fach: str | None = None) -> list[dict]:
    """Alle auslieferbaren Lektionen — aus dem Katalog, nicht aus `MODULE`.

    `MODULE` sagt nur noch, was gesaet wird. Was es *gibt*, steht in
    `lern_konzept`: sonst waere eine Lektion, die niemand als Python-Modul
    geschrieben hat, grundsaetzlich unauffindbar.
    """
    from ..faecher import pflicht
    _saat_sicherstellen()
    nur = pflicht(fach) if fach else None
    return [{"konzept_id": k["id"], "label": k["label"], "fach": k["fach"],
             "konzept_key": k["konzept_key"], "stichworte": k["stichworte"]}
            for k in store.konzepte_verfuegbar()
            if nur is None or k["fach"] == nur]


def _trifft(gesucht: str, lektion: dict) -> bool:
    """Stichworte gehoeren zum Konzept, nicht in eine Tabelle daneben.

    Liegt in `karo_contract`: der Lehrplan-Dienst muss dieselbe Frage
    gleich beantworten, sonst liefert er etwas, das Karo verwirft.
    """
    return trifft_thema(gesucht, lektion)


def fuer_thema(thema_text: str | None, fach: str | None, klasse: int | None = None) -> dict | None:
    """Die passende Lektion — oder None, und dann wird das auch gesagt.

    Bewusst ein simpler Stichwortabgleich: eine echte Zuordnung beliebiger
    Themen braucht die Zerlegung aus Meilenstein 4. Was hier nicht trifft,
    darf nicht heimlich in der Bruchlektion landen.

    Treffen mehrere Lektionen, gewinnt die genaueste (`treffergrad`): die
    Lektion, die so heisst wie das Thema, schlägt eine, die es nur über
    ein lose passendes Stichwort erwischt — sonst bekäme „Brüche mit
    verschiedenen Nennern addieren" die Gleichnamig-Lektion, weil beide
    das Stichwort „brueche addieren" teilen.
    """
    from ..faecher import schluessel
    gesucht = normalisiere_thema(thema_text)
    # Ohne Fach gibt es keine Lektion: sonst fände „Brüche“ aus Englisch
    # heraus die Mathematiklektion.
    if not gesucht or not schluessel(fach):
        return None
    bester, bester_grad = None, 0
    for lektion in verfuegbar(fach):
        konzept = store.konzept(lektion['konzept_id']) or {}
        if klasse and not konzept.get('klasse_von', 1) <= klasse <= konzept.get('klasse_bis', 13):
            continue
        grad = treffergrad(gesucht, lektion)
        if grad > bester_grad:
            bester, bester_grad = lektion, grad
    return bester


def _sinnwoerter(text: str | None) -> set:
    """Die Wörter eines Themennamens, die etwas bedeuten.

    Dieselbe Liste wie `trifft_thema` — sonst faenden Vorschlaege Worte
    bedeutungsvoll, die die Zuordnung ignoriert (oder umgekehrt).
    """
    return set(bedeutungswoerter(text))


def empfehlungen(thema_text: str | None, fach: str, hoechstens: int = 3) -> list[dict]:
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
    from ..faecher import schluessel
    gesucht = _sinnwoerter(thema_text)
    if not gesucht or not schluessel(fach):
        return []
    bewertet = []
    for lektion in verfuegbar(fach):
        woerter = _sinnwoerter(lektion["label"])
        for wort in lektion.get("stichworte") or ():
            woerter |= _sinnwoerter(wort)
        gemeinsam = gesucht & woerter
        if gemeinsam:
            bewertet.append((len(gemeinsam), lektion["label"], lektion))
    bewertet.sort(key=lambda t: (-t[0], t[1]))
    return [lektion for _, _, lektion in bewertet[:hoechstens]]
