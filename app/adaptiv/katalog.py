"""Fehlertyp bestimmen und die passende Erklärung ausliefern (§1, §6).

Die Stufenfolge ist eine Kostenentscheidung, keine Stilfrage:

    Tier 1  exakter Abgleich bekannter falscher Antworten   kein Modell
    Tier 2  semantische Suche über Einbettungen             nur Einbettung
    Tier 3  unbekannter Fehler: Modell A analysiert         teuer

Meilenstein 1 implementiert Tier 1 vollständig. Tier 2 und 3 hängen hinter
Schaltern (`semantic_error_matching_enabled`, `llm_error_creation_enabled`)
und melden bis Meilenstein 4 ehrlich „nicht verfügbar“, statt heimlich ein
Modell zu rufen.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import config
from . import store
from .normalisierung import normalisiere


@dataclass(frozen=True)
class Treffer:
    """Ergebnis der Fehlererkennung."""

    fehlertyp: dict | None
    tier: int | None
    grund: str = ""

    @property
    def erkannt(self) -> bool:
        return self.fehlertyp is not None


def identifiziere(konzept_id: int, antwort: str, cfg=None) -> Treffer:
    """Ordnet eine falsche Antwort einem Fehlertyp zu — Tier 1 zuerst."""
    muster = normalisiere(antwort)
    if not muster:
        return Treffer(None, None, "leere Antwort")

    gefunden = store.fehlertyp_fuer_muster(konzept_id, muster)
    if gefunden:
        return Treffer(gefunden, 1, "bekannte falsche Antwort")

    cfg = cfg or config.load_safe()
    if getattr(cfg, "semantic_error_matching_enabled", False):
        # Meilenstein 4: Einbettung + Vektorsuche über der Schwelle aus der
        # Konfiguration. Bis dahin gibt es hier bewusst keinen Ersatzpfad.
        return Treffer(None, None, "Tier 2 noch nicht verfügbar")
    if getattr(cfg, "llm_error_creation_enabled", False):
        return Treffer(None, None, "Tier 3 noch nicht verfügbar")
    return Treffer(None, None, "unbekannter Fehler")


def fehlertyp_lernen(fehlertyp_id: int, antwort: str,
                     quelle: str = "beobachtet") -> None:
    """Eine weitere Schreibweise derselben Fehlvorstellung merken.

    Damit trifft Tier 1 beim nächsten Kind ohne Modell — genau der Weg, auf
    dem der Katalog wächst (§1: „Successful interventions become reusable
    content“). Es entsteht KEIN neuer Fehlertyp (A4).
    """
    store.alias_sichern(fehlertyp_id, normalisiere(antwort), quelle)


def erklaerung_fuer(fehlertyp_id: int, klasse: int,
                    hoechstens_schwierigkeit: int | None = None) -> dict | None:
    """Liefert die beste geprüfte Erklärung — reiner Lookup, kein Modellaufruf."""
    eintrag = store.beste_erklaerung(fehlertyp_id, klasse,
                                     hoechstens_schwierigkeit)
    if eintrag:
        store.erklaerung_ausgeliefert(eintrag["id"])
    return eintrag


def einfachere_erklaerung(fehlertyp_id: int, klasse: int,
                          bisherige_schwierigkeit: int) -> dict | None:
    """Nach einem Fehlversuch: eine Stufe einfacher, nicht dieselbe noch einmal (§1.7)."""
    if bisherige_schwierigkeit <= 1:
        return None
    return erklaerung_fuer(fehlertyp_id, klasse,
                           hoechstens_schwierigkeit=bisherige_schwierigkeit - 1)


def erstkontakt_fuer(konzept_id: int) -> dict | None:
    """Kein Fehlersignal vorhanden (§11): Anker, erste Aufgabe, Benennung."""
    return store.erstkontakt(konzept_id)
