"""Register der Darstellungen (01_ARCHITECTURE.md §3).

Ein Modell darf ausschließlich auswählen und Parameter füllen:

    {"component": "FractionStrip", "parameters": {...}, "animation": "..."}

Es liefert niemals HTML, SVG, Canvas, JS oder Animationscode — weder zur
Laufzeit noch im Hintergrundjob noch „nur zur Ansicht“ (A1). Alles, was
gezeichnet werden kann, steht hier; die Zeichnung selbst liegt als Makro im
Template und wird über `renderer` benannt, nicht geliefert.

Was ein Modell zu sehen bekommt, ist `fuer_modell()` — Bezeichnung, Zweck,
Parameter, erlaubte Animationen. Nie die Umsetzung.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

BRUCH = "bruch"
GANZZAHL = "ganzzahl"
TEXT = "text"
LISTE_BRUCH = "liste[bruch]"
LISTE_TEXT = "liste[text]"


class ParameterUngueltig(ValueError):
    """Parameter passen nicht zum Schema — wird verworfen, nie gezeichnet."""


@dataclass(frozen=True)
class Komponente:
    id: str
    version: int
    zweck: str
    faecher: tuple[str, ...]
    parameter: dict[str, dict]
    animationen: tuple[str, ...]
    #: Name des Jinja-Makros. Ein Name, kein Code — siehe Modulkopf.
    renderer: str
    #: Wie die Darstellung vorgelesen wird, wenn niemand sie sehen kann.
    barrierefreiheit: str
    konzepte: tuple[str, ...] = field(default=())

    def dient(self, fach: str, konzept_key: str = "") -> bool:
        if fach and self.faecher and fach not in self.faecher:
            return False
        if konzept_key and self.konzepte and konzept_key not in self.konzepte:
            return False
        return True


_REGISTER: dict[str, Komponente] = {}


def _eintragen(komponente: Komponente) -> Komponente:
    _REGISTER[komponente.id] = komponente
    return komponente


FRACTION_STRIP = _eintragen(Komponente(
    id="FractionStrip", version=1,
    zweck="Zwei gleich breite Ganze, unterschiedlich geteilt — zeigt, dass "
          "sich beim Umrechnen die Stückzahl ändert, nicht die Menge.",
    faecher=("mathematik",),
    parameter={
        "a": {"typ": BRUCH, "pflicht": True, "zweck": "erster Bruch"},
        "b": {"typ": BRUCH, "zweck": "zweiter Bruch"},
        "gemeinsam": {"typ": GANZZAHL, "min": 1,
                      "zweck": "gemeinsamer Nenner, auf den umgerechnet wird"},
    },
    animationen=("none", "cut_then_slide"),
    renderer="fraction_strip",
    barrierefreiheit="je Streifen: „{gefuellt} von {gesamt} gleich großen Stücken“",
))

NUMBER_LINE = _eintragen(Komponente(
    id="NumberLine", version=1,
    zweck="Brüche als Orte auf einer Linie — zeigt Größenverhältnisse, wo "
          "Streifen schon einmal nicht geholfen haben.",
    faecher=("mathematik",),
    parameter={
        "marken": {"typ": LISTE_BRUCH, "pflicht": True,
                   "zweck": "Brüche, die markiert werden"},
        "bis": {"typ": BRUCH, "zweck": "rechtes Ende der Linie"},
        "schritte": {"typ": GANZZAHL, "min": 1, "zweck": "Teilstriche"},
    },
    animationen=("none", "walk"),
    renderer="number_line",
    barrierefreiheit="„Zahlenstrahl mit {anzahl} Marken“",
))

AREA_MODEL = _eintragen(Komponente(
    id="AreaModel", version=1,
    zweck="Ein Rechteck in Zeilen und Spalten — für Anteile und später für "
          "das Multiplizieren von Brüchen.",
    faecher=("mathematik",),
    parameter={
        "spalten": {"typ": GANZZAHL, "pflicht": True, "min": 1, "max": 20},
        "zeilen": {"typ": GANZZAHL, "pflicht": True, "min": 1, "max": 20},
        "markiert": {"typ": GANZZAHL, "min": 0,
                     "zweck": "wie viele Felder gefüllt sind"},
    },
    animationen=("none", "split"),
    renderer="area_model",
    barrierefreiheit="„{markiert} von {gesamt} Feldern“",
))

BALANCE = _eintragen(Komponente(
    id="Balance", version=1,
    zweck="Eine Waage — für Gleichungen und Vergleiche, bei denen es um "
          "„gleich viel“ geht, nicht um Anteile.",
    faecher=("mathematik",),
    parameter={
        "links": {"typ": BRUCH, "pflicht": True},
        "rechts": {"typ": BRUCH, "pflicht": True},
    },
    animationen=("none", "tip"),
    renderer="balance",
    barrierefreiheit="„Waage: links {links}, rechts {rechts}“",
))

GENERIC_STEP_FLOW = _eintragen(Komponente(
    id="GenericStepFlow", version=1,
    zweck="Nummerierte Schritte in Worten. Trägt jedes Fach und dient als "
          "Rückfall, wenn eine Auswahl verworfen wurde.",
    faecher=(),                      # leer: jedes Fach
    parameter={"schritte": {"typ": LISTE_TEXT, "zweck": "Schritte in Worten"}},
    animationen=("none",),
    renderer="step_flow",
    barrierefreiheit="„{anzahl} Schritte“",
))

#: §3/§15: Wird eine Auswahl verworfen, wird NICHTS gezeichnet außer diesem.
FALLBACK = GENERIC_STEP_FLOW


def alle() -> tuple[Komponente, ...]:
    return tuple(_REGISTER.values())


def hole(komponenten_id: str) -> Komponente | None:
    return _REGISTER.get(komponenten_id)


def ids() -> tuple[str, ...]:
    return tuple(_REGISTER)


#: Wie ein Wert dieses Typs aussieht — in Worten und als Beispiel.
#:
#: Ohne das ist „typ: bruch" für ein Modell nicht zu erraten. Auf der
#: Testinstallation scheiterte die Erzeugung reihenweise an „„a" muss ein
#: Bruch [Zähler, Nenner] mit Nenner > 0 sein": das Register verlangte eine
#: Form, die es dem Modell nie mitgeteilt hatte.
FORM = {
    BRUCH: ("[Zähler, Nenner]", [1, 2]),
    GANZZAHL: ("ganze Zahl", 3),
    TEXT: ("Text", "…"),
    LISTE_BRUCH: ("Liste von [Zähler, Nenner]", [[1, 2], [1, 3]]),
    LISTE_TEXT: ("Liste von Texten", ["erster Schritt", "zweiter Schritt"]),
}


def fuer_modell(fach: str = "", konzept_key: str = "") -> list[dict]:
    """Was das auswählende Modell sieht: Metadaten, niemals die Umsetzung.

    Bewusst ohne `renderer` — ein Modell soll nicht einmal erfahren, wie
    gezeichnet wird, damit es gar nicht erst versucht, es selbst zu tun.
    """
    return [{
        "component": k.id,
        "version": k.version,
        "zweck": k.zweck,
        "parameter": {name: _parameter_fuer_modell(regel)
                      for name, regel in k.parameter.items()},
        "animationen": list(k.animationen),
    } for k in alle() if k.dient(fach, konzept_key)]


def _parameter_fuer_modell(regel: dict) -> dict:
    form, beispiel = FORM.get(regel.get("typ", TEXT), FORM[TEXT])
    return ({s: w for s, w in regel.items() if s != "pflicht"}
            | {"pflicht": bool(regel.get("pflicht")),
               "form": form, "beispiel": beispiel})


# --------------------------------------------------------------------------
# Parameter prüfen
# --------------------------------------------------------------------------

def _ist_bruch(wert: Any) -> bool:
    return (isinstance(wert, (list, tuple)) and len(wert) == 2
            and all(isinstance(z, int) and not isinstance(z, bool) for z in wert)
            and wert[1] > 0)


def _pruefe_wert(name: str, wert: Any, regel: dict) -> Any:
    typ = regel.get("typ", TEXT)
    if typ == BRUCH:
        if not _ist_bruch(wert):
            raise ParameterUngueltig(
                f"„{name}“ muss ein Bruch [Zähler, Nenner] mit Nenner > 0 sein.")
        return [int(wert[0]), int(wert[1])]
    if typ == GANZZAHL:
        if not isinstance(wert, int) or isinstance(wert, bool):
            raise ParameterUngueltig(f"„{name}“ muss eine ganze Zahl sein.")
        if "min" in regel and wert < regel["min"]:
            raise ParameterUngueltig(f"„{name}“ ist kleiner als {regel['min']}.")
        if "max" in regel and wert > regel["max"]:
            raise ParameterUngueltig(f"„{name}“ ist größer als {regel['max']}.")
        return wert
    if typ == LISTE_BRUCH:
        if not isinstance(wert, (list, tuple)) or not wert:
            raise ParameterUngueltig(f"„{name}“ muss eine Liste von Brüchen sein.")
        if not all(_ist_bruch(e) for e in wert):
            raise ParameterUngueltig(f"„{name}“ enthält einen ungültigen Bruch.")
        return [[int(e[0]), int(e[1])] for e in wert]
    if typ == LISTE_TEXT:
        if not isinstance(wert, (list, tuple)):
            raise ParameterUngueltig(f"„{name}“ muss eine Liste von Texten sein.")
        return [str(e) for e in wert]
    if not isinstance(wert, str):
        raise ParameterUngueltig(f"„{name}“ muss Text sein.")
    return wert


def pruefe_auswahl(auswahl: Any) -> dict:
    """Prüft eine Komponentenauswahl gegen das Register.

    Unbekannte Id oder unpassende Parameter → `ParameterUngueltig`. Der
    Aufrufer nimmt dann den Rückfall; gezeichnet wird ungeprüftes nie.
    """
    if not isinstance(auswahl, dict):
        raise ParameterUngueltig("Auswahl ist kein Objekt.")

    komponente = hole(auswahl.get("component"))
    if komponente is None:
        raise ParameterUngueltig(
            f"Unbekannte Komponente: {auswahl.get('component')!r}")

    roh = auswahl.get("parameters", {})
    if not isinstance(roh, dict):
        raise ParameterUngueltig("„parameters“ ist kein Objekt.")

    unbekannt = set(roh) - set(komponente.parameter)
    if unbekannt:
        raise ParameterUngueltig(
            f"Unbekannte Parameter: {', '.join(sorted(unbekannt))}")

    geprueft = {}
    for name, regel in komponente.parameter.items():
        if name not in roh or roh[name] is None:
            if regel.get("pflicht"):
                raise ParameterUngueltig(f"„{name}“ fehlt.")
            continue
        geprueft[name] = _pruefe_wert(name, roh[name], regel)

    animation = auswahl.get("animation", "none")
    if animation not in komponente.animationen:
        raise ParameterUngueltig(
            f"„{animation}“ ist für {komponente.id} nicht erlaubt.")

    return {"component": komponente.id, "parameters": geprueft,
            "animation": animation}


def auswahl_oder_fallback(auswahl: Any) -> tuple[dict, str | None]:
    """Nie werfen, immer etwas Sicheres liefern (§15: degradieren)."""
    try:
        return pruefe_auswahl(auswahl), None
    except ParameterUngueltig as exc:
        return ({"component": FALLBACK.id, "parameters": {}, "animation": "none"},
                str(exc))
