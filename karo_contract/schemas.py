"""Prüfung jedes Inhalts, bevor er in die Datenbank oder in ein Template geht.

Zwei Invarianten hängen an dieser Datei (03_INVARIANTS.md):

A1  Kein Modell-Erzeugnis wird je ausgeführt. Ein Modell wählt eine Komponente
    und füllt Parameter — es liefert niemals HTML, SVG, JS oder CSS.
A2  Jede Modellausgabe ist schemageprüft. Kaputtes JSON erreicht weder die
    Datenbank noch ein Template; ein Schemafehler führt zu einem definierten
    Rückfall, nicht zu einem 500er.

Bewusst im Stil der bestehenden `prompts.py`-Schemas gehalten (einfache
Strukturen statt einer zweiten Validierungsbibliothek).
"""

from __future__ import annotations

import re
from typing import Any

# §3: Das Register führt die Komponenten, ihre Parameter und den Rückfall.
# Diese Datei prüft nur noch den Lehrinhalt und reicht Darstellungen dorthin
# weiter — es gibt genau eine Stelle, an der eine Auswahl gültig wird.
from . import komponenten, rechnen

#: Sichere Rückfallkomponente, wenn eine Auswahl verworfen wird (§3, §15).
FALLBACK_VISUALISIERUNG = {"component": komponenten.FALLBACK.id,
                           "parameters": {}, "animation": "none"}

INHALT_FELDER = ("haken", "erkenntnis", "regel")
BILD_FELDER = ("zeigt", "bewegt", "bleibt_gleich")
AUFGABE_FELDER = ("frage", "loesung")

#: Markup, Skript oder Style — nichts davon darf je in einem Inhalt stehen.
_MARKUP = re.compile(
    # Ohne Leerzeichen hinter dem Zeichen: „<div" ist ein Element, „a < b"
    # ist ein Kleiner-als. Ein Browser liest „< div" nicht als Element —
    # vorher tat diese Pruefung es, und damit war jede Bedingung „a < b"
    # in einer Aufgabe oder Erklaerung verboten.
    r"</?[a-z!]"                # <div, </p, <svg, <!--
    r"|&lt;/?[a-z]"             # maskiertes Markup
    r"|javascript\s*:"
    r"|\bon(?:error|load|click)\s*="
    r"|@import\b|\burl\s*\(",
    re.IGNORECASE)


class InhaltUngueltig(ValueError):
    """Der Inhalt passt nicht zum Schema und wird nicht gespeichert."""


def enthaelt_markup(wert: Any) -> bool:
    """True, wenn irgendwo im Wert Markup/Skript/Style steckt."""
    if isinstance(wert, str):
        return bool(_MARKUP.search(wert))
    if isinstance(wert, dict):
        return any(enthaelt_markup(v) for v in wert.values())
    if isinstance(wert, (list, tuple)):
        return any(enthaelt_markup(v) for v in wert)
    return False


def _text(daten: dict, feld: str, pfad: str = "") -> str:
    wert = daten.get(feld)
    if not isinstance(wert, str) or not wert.strip():
        raise InhaltUngueltig(f"„{pfad or feld}“ fehlt oder ist leer.")
    return wert.strip()


def pruefe_inhalt(daten: Any) -> dict:
    """Prüft das Lehrinhalts-Format aus §4 und gibt es gesäubert zurück.

    Wirft `InhaltUngueltig`, statt Halbfertiges durchzulassen — der Aufrufer
    entscheidet dann über den Rückfall.
    """
    if not isinstance(daten, dict):
        raise InhaltUngueltig("Inhalt ist kein Objekt.")
    if enthaelt_markup(daten):
        raise InhaltUngueltig("Inhalt enthält Markup oder Skript (A1).")

    sauber: dict[str, Any] = {f: _text(daten, f) for f in INHALT_FELDER}

    bild = daten.get("bild")
    if not isinstance(bild, dict):
        raise InhaltUngueltig("„bild“ fehlt.")
    sauber["bild"] = {f: _text(bild, f, f"bild.{f}") for f in BILD_FELDER}

    aufgabe = daten.get("aufgabe")
    if not isinstance(aufgabe, dict):
        raise InhaltUngueltig("„aufgabe“ fehlt.")
    sauber["aufgabe"] = {f: _text(aufgabe, f, f"aufgabe.{f}")
                         for f in AUFGABE_FELDER}
    tipp = aufgabe.get("tipp")
    if isinstance(tipp, str) and tipp.strip():
        sauber["aufgabe"]["tipp"] = tipp.strip()
    return sauber


def schwachstellen(inhalt: dict) -> list[str]:
    """Qualitätssignale aus §4 — nicht jeder Mangel ist ein Schemafehler.

    `erkenntnis` und `bild.bleibt_gleich` tragen die Didaktik. Sind sie dünn,
    ist die Erklärung schwach: melden statt ausliefern.
    """
    mangel = []
    if len((inhalt.get("erkenntnis") or "").split()) < 4:
        mangel.append("erkenntnis ist zu vage")
    bleibt = (inhalt.get("bild") or {}).get("bleibt_gleich") or ""
    if len(bleibt.split()) < 4:
        mangel.append("bild.bleibt_gleich ist zu vage")
    return mangel


def pruefe_visualisierung(daten: Any) -> dict:
    """Prüft eine Komponentenauswahl gegen das Register (§3).

    Erlaubt ist ausschließlich: Komponenten-Id, Parameter, Animationsmodus.
    Unbekannte Id oder unpassende Parameter → `InhaltUngueltig`; der Aufrufer
    nimmt dann `FALLBACK_VISUALISIERUNG`.
    """
    if not isinstance(daten, dict):
        raise InhaltUngueltig("Visualisierung ist kein Objekt.")
    if enthaelt_markup(daten):
        raise InhaltUngueltig("Visualisierung enthält Markup oder Skript (A1).")
    try:
        return komponenten.pruefe_auswahl(daten)
    except komponenten.ParameterUngueltig as exc:
        raise InhaltUngueltig(str(exc)) from None


def visualisierung_oder_fallback(daten: Any) -> tuple[dict, str | None]:
    """Nie werfen, immer etwas Sicheres liefern (§15: degradieren, nicht ausfallen)."""
    try:
        return pruefe_visualisierung(daten), None
    except InhaltUngueltig as exc:
        return dict(FALLBACK_VISUALISIERUNG), str(exc)


# --------------------------------------------------------------------------
# Eine ganze Lektion, von Modell A vorgeschlagen (§5, §6 Tier 3)
# --------------------------------------------------------------------------
#
# Tier 3 in §6 erzeugt EINE Erklärung für EINEN unbekannten Fehler — Konzept
# und Fehler sind da schon bekannt, das Kind hat ein Signal geliefert. Hier
# entsteht eine ganze Lektion aus einem Themennamen: Konzept, Fehlertypen,
# Erklärungen, Bilder und alle Aufgaben.
#
# Deshalb ist die Prüfung strenger als bei einer einzelnen Erklärung. Der
# teuerste Fehler wäre Halbfertiges, das vollständig aussieht:
# `unterricht.bildschirm()` liest überall `(aufgabe or {})` und stürzt gerade
# NICHT ab — ein Kind liefe bis Phase vier und stünde vor einem leeren
# Schirm. Vollständigkeit ist hier ein Schemafehler.

#: Die fünf Rollen, die `unterricht.py` pro Fehlertyp liest.
AUFGABEN_ROLLEN = ("vorhersage", "beispiel", "gefuehrt", "selbststaendig",
                   "transfer")

#: Rollen, die eine Fehlvorhersage brauchen: an ihnen erkennt Tier 1 dieselbe
#: Fehlvorstellung wieder (`typischer_fehler` in `inhalte_brueche.py`).
ROLLEN_MIT_FEHLERVORHERSAGE = ("gefuehrt", "selbststaendig")

#: Rollen, die als Auswahl gestellt werden statt als Rechnung.
ROLLEN_MIT_OPTIONEN = ("vorhersage", "transfer")

#: „Das habe ich nicht verstanden" ist in jeder Phase ausser COMPLETE
#: erreichbar (02 §5, B3). Erzeugt wird die Hilfe mit der Lektion — zur
#: Laufzeit nachzuladen waere ein Modellaufruf im Moment der Ratlosigkeit.
HILFE_PHASEN = ("HOOK", "RULE", "WORKED_EXAMPLE", "GUIDED_TASK",
                "INDEPENDENT_TASK", "ADAPTATION")

#: Felder, die eine WAHRE Aussage machen und deshalb nachgerechnet werden.
#: Bewusst NICHT dabei: `beschreibung`, `haken`, `typischer_fehler` und die
#: bekannten falschen Antworten — die beschreiben eine Fehlvorstellung.
#: „1/2 + 1/3 = 2/5" gehoert dort hin und ist als Rechnung natuerlich falsch.
_NACHZURECHNEN = ("regel", "erkenntnis", "aufloesung")


def _nachrechnen(text: Any, pfad: str) -> None:
    if rechnen.stimmt(text) is False:
        raise InhaltUngueltig(
            f"„{pfad}“ enthält eine Rechnung, die nachgerechnet nicht "
            f"aufgeht: {str(text)[:80]}")


def _vorlage_einsetzen(daten: dict, rolle: str, seed: str, fehler_key: str) -> dict:
    """Liegt eine Vorlage bei, rechnet der Code — statt zu glauben.

    Das Modell darf weiter eine Frage und eine Loesung mitschicken; sie
    werden ersetzt. Ein Sprachmodell formuliert gut und rechnet schlecht,
    und was gerechnet ist, kann nicht falsch behauptet sein.
    """
    muster = daten.get("vorlage")
    if not isinstance(muster, dict) or not muster.get("vorlage"):
        return daten
    from . import aufgaben
    try:
        gebaut = aufgaben.bauen(muster, seed=f"{seed}:{rolle}", fehler_key=fehler_key)
    except aufgaben.VorlageUnbrauchbar as fehler:
        raise InhaltUngueltig(f"„{rolle}.vorlage“ ergibt keine Aufgabe: {fehler}") from None
    ersetzt = {**daten, "frage": gebaut["frage"], "loesung": gebaut["loesung"]}
    if gebaut.get("typischer_fehler"):
        ersetzt["typischer_fehler"] = gebaut["typischer_fehler"]
    return ersetzt


def _aufgabe_pruefen(daten: Any, rolle: str, seed: str = "", fehler_key: str = "") -> dict:
    if not isinstance(daten, dict):
        raise InhaltUngueltig(f"Aufgabe „{rolle}“ fehlt.")
    daten = _vorlage_einsetzen(daten, rolle, seed, fehler_key)
    sauber = {f: _text(daten, f, f"{rolle}.{f}") for f in AUFGABE_FELDER}
    _nachrechnen(sauber["frage"], f"{rolle}.frage")
    if rechnen.loesung_stimmt(sauber["frage"], sauber["loesung"]) is False:
        raise InhaltUngueltig(
            f"„{rolle}“ hat eine Lösung, die nachgerechnet nicht zur Frage "
            f"passt: {sauber['frage']} → {sauber['loesung']}")

    if rolle in ROLLEN_MIT_FEHLERVORHERSAGE:
        fehler = _text(daten, "typischer_fehler", f"{rolle}.typischer_fehler")
        if fehler.strip() == sauber["loesung"].strip():
            raise InhaltUngueltig(
                f"„{rolle}.typischer_fehler“ ist gleich der Lösung — damit "
                "würde eine richtige Antwort als Fehler eingeordnet.")
        sauber["typischer_fehler"] = fehler

    if rolle in ROLLEN_MIT_OPTIONEN:
        optionen = daten.get("optionen")
        if not isinstance(optionen, list) or len(optionen) < 2:
            raise InhaltUngueltig(f"„{rolle}.optionen“ braucht zwei Auswahlen.")
        sauber["optionen"] = [str(o).strip() for o in optionen if str(o).strip()]
        if sauber["loesung"] not in sauber["optionen"]:
            raise InhaltUngueltig(
                f"„{rolle}.loesung“ steht nicht unter den Optionen.")
        sauber["aufloesung"] = _text(daten, "aufloesung", f"{rolle}.aufloesung")

    for feld in ("tipps", "schritte"):
        werte = daten.get(feld)
        if isinstance(werte, list):
            sauber[feld] = [str(w).strip() for w in werte if str(w).strip()]
    for schritt in sauber.get("schritte", []):
        _nachrechnen(schritt, f"{rolle}.schritte")
    _nachrechnen(sauber.get("aufloesung"), f"{rolle}.aufloesung")
    return sauber


def _fehlertyp_pruefen(daten: Any, nr: int, saat: str = "") -> dict:
    if not isinstance(daten, dict):
        raise InhaltUngueltig(f"Fehlertyp {nr} ist kein Objekt.")
    sauber = {f: _text(daten, f, f"fehlertyp[{nr}].{f}")
              for f in ("key", "label")}
    sauber["beschreibung"] = str(daten.get("beschreibung") or "").strip()

    antworten = daten.get("antworten")
    if not isinstance(antworten, list) or not any(
            str(a).strip() for a in antworten):
        raise InhaltUngueltig(
            f"„fehlertyp[{nr}].antworten“ fehlt. Ohne eine erkennbare falsche "
            "Antwort trifft Tier 1 nie, und der Eintrag schlägt bei keinem "
            "Kind je an.")
    sauber["antworten"] = [str(a).strip() for a in antworten if str(a).strip()]

    sauber["erklaerung"] = pruefe_inhalt(daten.get("erklaerung"))
    for feld in _NACHZURECHNEN:
        _nachrechnen(sauber["erklaerung"].get(feld),
                     f"fehlertyp[{nr}].erklaerung.{feld}")
    sauber["visualisierung"] = pruefe_visualisierung(daten.get("visualisierung"))
    alternativ = daten.get("visualisierung_alternativ")
    if alternativ is not None:
        geprueft = pruefe_visualisierung(alternativ)
        # B1: die Adaptation muss eine ANDERE Darstellung zeigen.
        if geprueft["component"] == sauber["visualisierung"]["component"]:
            raise InhaltUngueltig(
                f"„fehlertyp[{nr}].visualisierung_alternativ“ nimmt dieselbe "
                "Komponente — die Adaptation soll eine andere Darstellung "
                "zeigen, nicht dieselbe noch einmal.")
        sauber["visualisierung_alternativ"] = geprueft

    aufgaben = daten.get("aufgaben")
    if not isinstance(aufgaben, dict):
        raise InhaltUngueltig(f"„fehlertyp[{nr}].aufgaben“ fehlt.")
    # Der Seed haengt am Fehlertyp, nicht am Zufall: dieselbe Lektion hat
    # immer dieselben Zahlen. Sonst stuende in der Datenbank eine andere
    # Aufgabe als im Lernmaterial, und ein Fehlerbericht waere nicht
    # nachzustellen.
    seed = f"{saat}:{sauber['key']}"
    sauber["aufgaben"] = {
        rolle: _aufgabe_pruefen(aufgaben.get(rolle), rolle, seed, sauber["key"])
        for rolle in AUFGABEN_ROLLEN}
    return sauber


def pruefe_lektion(daten: Any) -> dict:
    """Prüft eine vorgeschlagene Lektion vollständig und gibt sie gesäubert
    zurück. Wirft `InhaltUngueltig`, sobald irgendetwas fehlt oder nicht
    zum Register passt — der Aufrufer speichert dann nichts.
    """
    if not isinstance(daten, dict):
        raise InhaltUngueltig("Lektion ist kein Objekt.")
    if enthaelt_markup(daten):
        raise InhaltUngueltig("Lektion enthält Markup oder Skript (A1).")

    konzept = daten.get("konzept")
    if not isinstance(konzept, dict):
        raise InhaltUngueltig("„konzept“ fehlt.")
    sauber_konzept = {f: _text(konzept, f, f"konzept.{f}")
                      for f in ("konzept_key", "thema_key", "label")}
    sauber_konzept["klasse_von"] = int(konzept.get("klasse_von") or 1)
    sauber_konzept["klasse_bis"] = int(konzept.get("klasse_bis") or 13)
    stichworte = konzept.get("stichworte")
    sauber_konzept["stichworte"] = [
        str(w).strip() for w in (stichworte or []) if str(w).strip()]

    fehlertypen = daten.get("fehlertypen")
    if not isinstance(fehlertypen, list) or not fehlertypen:
        raise InhaltUngueltig("„fehlertypen“ fehlt — ein Fehlertyp ist die "
                              "Einheit des Inhalts (§2).")
    # Die Saat kommt aus dem Konzept: dieselbe Lektion, dieselben Zahlen.
    saat = sauber_konzept.get("konzept_key") or sauber_konzept.get("label") or ""
    geprueft = [_fehlertyp_pruefen(f, i, saat) for i, f in enumerate(fehlertypen)]
    schluessel = [f["key"] for f in geprueft]
    doppelt = {k for k in schluessel if schluessel.count(k) > 1}
    if doppelt:
        raise InhaltUngueltig(
            f"Fehlertyp doppelt vergeben: {', '.join(sorted(doppelt))}.")

    hilfe = daten.get("hilfe")
    if not isinstance(hilfe, dict):
        raise InhaltUngueltig(
            "„hilfe“ fehlt. „Das habe ich nicht verstanden“ ist in jeder "
            "Phase erreichbar; ohne Eintrag ginge der Knopf ins Leere.")
    sauber_hilfe = {}
    for phase in HILFE_PHASEN:
        eintrag = hilfe.get(phase)
        if not isinstance(eintrag, dict):
            raise InhaltUngueltig(f"„hilfe.{phase}“ fehlt.")
        gesaeubert = {"text": _text(eintrag, "text", f"hilfe.{phase}.text")}
        _nachrechnen(gesaeubert["text"], f"hilfe.{phase}.text")
        bild = eintrag.get("visualisierung")
        if bild is not None:
            gesaeubert["visualisierung"] = pruefe_visualisierung(bild)
        sauber_hilfe[phase] = gesaeubert

    faq = daten.get("faq")
    sauber_faq = []
    for i, eintrag in enumerate(faq if isinstance(faq, list) else []):
        if not isinstance(eintrag, dict):
            continue
        sauber_faq.append({
            "frage": _text(eintrag, "frage", f"faq[{i}].frage"),
            "antwort": _text(eintrag, "antwort", f"faq[{i}].antwort"),
        })
    if len(sauber_faq) < 2:
        raise InhaltUngueltig(
            "„faq“ braucht mindestens zwei Einträge — „Ich habe eine andere "
            "Frage“ ist sonst eine leere Tür.")

    erstkontakt = daten.get("erstkontakt")
    sauber = {"konzept": sauber_konzept, "fehlertypen": geprueft,
              "hilfe": sauber_hilfe, "faq": sauber_faq}
    if isinstance(erstkontakt, dict):
        sauber["erstkontakt"] = {
            "anker": _text(erstkontakt, "anker", "erstkontakt.anker"),
            "erste_aufgabe": _aufgabe_pruefen(
                erstkontakt.get("erste_aufgabe"), "erstkontakt.erste_aufgabe"),
            "benennung": _text(erstkontakt, "benennung",
                               "erstkontakt.benennung"),
        }
    return sauber
