"""Der Unterrichtsablauf: diagnostizieren, erklären, üben, messen.

Bildungslogik, getrennt von HTTP und Vorlagen (01_ARCHITECTURE.md §16) — der
Router reicht nur Antworten herein und bekommt einen fertigen Bildschirm
zurück. Alles hier ist Nachschlagen im Katalog; es gibt in dieser Datei
bewusst keinen Modellaufruf (§1, A3).
"""

from __future__ import annotations

from fractions import Fraction

from . import inhalt_store, katalog, sitzung as zustand, store
from .normalisierung import normalisiere

#: Schritte innerhalb von DIAGNOSING (§11: Anker, dann produktives Scheitern).
SCHRITT_ANKER = "anker"
SCHRITT_AUFGABE = "aufgabe"


def _daten(sitzung: dict) -> dict:
    return dict(sitzung.get("daten") or {})


def _merke(sitzung_id: int, sitzung: dict, **werte) -> dict:
    daten = _daten(sitzung)
    daten.update(werte)
    store.sitzung_aktualisieren(sitzung_id, daten=daten)
    return store.sitzung(sitzung_id)


# --------------------------------------------------------------------------
# Antworten vergleichen
# --------------------------------------------------------------------------

def als_bruch(text: str | None) -> Fraction | None:
    wert = normalisiere(text).replace(" ", "")
    if not wert:
        return None
    try:
        if "/" in wert:
            zaehler, _, nenner = wert.partition("/")
            return Fraction(int(zaehler), int(nenner))
        return Fraction(wert)
    except (ValueError, ZeroDivisionError):
        return None


def ist_richtig(antwort: str | None, loesung: str) -> bool:
    """6/8 ist dieselbe Antwort wie 3/4 — gekürzt oder nicht."""
    gegeben, gesucht = als_bruch(antwort), als_bruch(loesung)
    if gegeben is not None and gesucht is not None:
        return gegeben == gesucht
    return bool(antwort) and normalisiere(antwort) == normalisiere(loesung)


# --------------------------------------------------------------------------
# Sitzung beginnen und fortsetzen
# --------------------------------------------------------------------------

def starte(konzept_id: int, thema_text: str = "") -> dict:
    """Manuell eingetipptes Thema → normalisierte Eingabe → Diagnose (§13)."""
    eingabe_id = store.eingabe_anlegen("manuell", fach="Mathematik",
                                       thema_text=thema_text or None,
                                       konzept_id=konzept_id)
    s = zustand.starten(eingabe_id=eingabe_id, konzept_id=konzept_id)
    s = zustand.wechsle(s["id"], zustand.MATERIAL_ANALYZED, "Thema erkannt")
    s = zustand.wechsle(s["id"], zustand.DIAGNOSING, "Diagnose beginnt")
    return _merke(s["id"], s, schritt=SCHRITT_ANKER)


def laufende_oder_neue(konzept_id: int) -> dict:
    """A6: weiterlaufen, wo das Kind war — auch nach neuer Anmeldung."""
    return zustand.laufende() or starte(konzept_id)


def neu_starten(konzept_id: int) -> dict:
    """Von vorn. Die alte Sitzung wird abgeschlossen, nicht gelöscht — ihr
    Verlauf bleibt als Lernsignal erhalten (§8)."""
    offen = zustand.laufende()
    if offen:
        store.sitzung_aktualisieren(offen["id"], zustand=zustand.MASTERED)
        store.ereignis_schreiben(offen["id"], "vom Kind neu gestartet",
                                 nach_zustand=zustand.MASTERED)
    return starte(konzept_id)


# --------------------------------------------------------------------------
# Bildschirm zusammenstellen
# --------------------------------------------------------------------------

def _hilfe(konzept_id: int, phase: str | None) -> dict:
    """02 §5/§6: Hilfe ist ein Nachschlagen, in jeder Phase außer COMPLETE."""
    return {
        "erklaer_mehr": inhalt_store.hilfe_fuer_phase(konzept_id, phase) if phase else None,
        "faq": inhalt_store.faq(konzept_id),
    }


def bildschirm(sitzung: dict) -> dict:
    """Was das Kind jetzt sieht — eine Frage, eine Handlung."""
    konzept_id = sitzung["konzept_id"]
    daten = _daten(sitzung)
    zustand_name = sitzung["zustand"]
    phase = sitzung["phase"]

    if zustand_name == zustand.ESCALATED:
        return {"art": "eskaliert", "hilfe": _hilfe(konzept_id, None),
                "phase": None}
    if zustand_name == zustand.MASTERED:
        return {"art": "geschafft", "hilfe": _hilfe(konzept_id, None),
                "phase": None}

    if zustand_name == zustand.DIAGNOSING:
        erstkontakt = katalog.erstkontakt_fuer(konzept_id) or {}
        if daten.get("schritt", SCHRITT_ANKER) == SCHRITT_ANKER:
            return {"art": "anker", "phase": "HOOK",
                    "text": erstkontakt.get("anker", ""),
                    "hilfe": _hilfe(konzept_id, "HOOK")}
        aufgabe = erstkontakt.get("erste_aufgabe") or {}
        if daten.get("zweite_diagnose"):
            aufgabe = {"frage": daten["zweite_diagnose"]}
        return {"art": "diagnose", "phase": "HOOK",
                "frage": aufgabe.get("frage", ""),
                "hinweis": aufgabe.get("hinweis", ""),
                "fehlerhinweis": daten.get("fehlerhinweis"),
                "hilfe": _hilfe(konzept_id, "HOOK")}

    erklaerung = (store.erklaerung(sitzung["erklaerung_id"])
                  if sitzung["erklaerung_id"] else None)
    inhalt = (erklaerung or {}).get("inhalt") or {}
    fehlertyp_id = sitzung["fehlertyp_id"]

    if phase == zustand.HOOK:
        vorhersage = inhalt_store.aufgabe(fehlertyp_id, inhalt_store.VORHERSAGE)
        if not daten.get("vorhergesagt"):
            # §19: Das Kind sagt voraus, BEVOR es eine Erklärung bekommt.
            return {"art": "vorhersage", "phase": phase, "inhalt": inhalt,
                    "aufgabe": vorhersage,
                    "bild": (vorhersage or {}).get("visualisierung"),
                    "hilfe": _hilfe(konzept_id, phase)}
        return {"art": "haken", "phase": phase, "inhalt": inhalt,
                "aufgabe": vorhersage,
                "vorhersage": daten.get("vorhergesagt"),
                # Der Widerspruch wird sichtbar, nicht nur behauptet.
                "bild": (vorhersage or {}).get("visualisierung"),
                "eigene_antwort": sitzung.get("letzte_antwort"),
                "hilfe": _hilfe(konzept_id, phase)}

    if phase == zustand.RULE:
        return {"art": "regel", "phase": phase, "inhalt": inhalt,
                "bild": (erklaerung or {}).get("visualisierung"),
                "hilfe": _hilfe(konzept_id, phase)}

    if phase == zustand.WORKED_EXAMPLE:
        return {"art": "beispiel", "phase": phase,
                "aufgabe": inhalt_store.aufgabe(fehlertyp_id, inhalt_store.BEISPIEL),
                "hilfe": _hilfe(konzept_id, phase)}

    if phase == zustand.INDEPENDENT_TASK and daten.get("gerechnet"):
        # Transfer: dieselbe Einsicht an einer anderen Struktur, ohne Rechnen.
        return {"art": "transfer", "phase": phase,
                "aufgabe": inhalt_store.aufgabe(fehlertyp_id,
                                                inhalt_store.TRANSFER),
                "fehlerhinweis": daten.get("fehlerhinweis"),
                "hilfe": _hilfe(konzept_id, phase)}

    if phase in (zustand.GUIDED_TASK, zustand.INDEPENDENT_TASK):
        rolle = (inhalt_store.GEFUEHRT if phase == zustand.GUIDED_TASK
                 else inhalt_store.SELBSTSTAENDIG)
        aufgabe = inhalt_store.aufgabe(fehlertyp_id, rolle)
        tipps = (aufgabe or {}).get("tipps") or []
        stufe = int(daten.get("tipp_stufe", 0))
        return {"art": "aufgabe", "phase": phase, "aufgabe": aufgabe,
                # B1: nur die geführte Aufgabe zeigt ihr Bild.
                "bild": (aufgabe or {}).get("visualisierung")
                        if phase == zustand.GUIDED_TASK else None,
                "tipps": tipps[:stufe], "tipp_offen": stufe < len(tipps),
                "fehlerhinweis": daten.get("fehlerhinweis"),
                "hilfe": _hilfe(konzept_id, phase)}

    if phase == zustand.ADAPTATION:
        return {"art": "anders", "phase": phase, "inhalt": inhalt,
                # B1: andere Darstellung, nicht derselbe Streifen noch einmal.
                "bild": (erklaerung or {}).get("visualisierung_alternativ"),
                "hilfe": _hilfe(konzept_id, phase)}

    return {"art": "geschafft", "phase": phase, "hilfe": _hilfe(konzept_id, None)}


# --------------------------------------------------------------------------
# Antworten verarbeiten
# --------------------------------------------------------------------------

def anker_beantwortet(sitzung: dict, antwort: str) -> dict:
    """§11: Der Anker wird nicht benotet — er weckt nur das Vorwissen."""
    store.sitzung_aktualisieren(sitzung["id"], letzte_antwort=antwort or None)
    store.ereignis_schreiben(sitzung["id"], "Anker beantwortet")
    return _merke(sitzung["id"], sitzung, schritt=SCHRITT_AUFGABE,
                  fehlerhinweis=None)


def diagnose_beantwortet(sitzung: dict, antwort: str, cfg=None) -> dict:
    """Produktives Scheitern auswerten: Fehlertyp bestimmen oder Erfolg buchen."""
    konzept_id = sitzung["konzept_id"]
    daten = _daten(sitzung)
    erste = (katalog.erstkontakt_fuer(konzept_id) or {}).get("erste_aufgabe") or {}
    bestaetigung = erste.get("bestaetigung") or {}
    loesung = (bestaetigung if daten.get("zweite_diagnose") else erste).get(
        "loesung", "")

    if als_bruch(antwort) is None:
        return _merke(sitzung["id"], sitzung,
                      fehlerhinweis="Das kann ich nicht als Bruch lesen. "
                                    "Schreib es zum Beispiel so: 5/6")

    if ist_richtig(antwort, loesung):
        ergebnis = zustand.antwort_richtig(sitzung["id"], antwort, cfg=cfg)
        if ergebnis["zustand"] == zustand.MASTERED:
            return ergebnis
        # Eine richtige Antwort ist keine Beherrschung (A8): noch eine Aufgabe.
        return _merke(sitzung["id"], ergebnis,
                      zweite_diagnose=bestaetigung.get("frage", ""),
                      fehlerhinweis=None)

    treffer = katalog.identifiziere(konzept_id, antwort, cfg=cfg)
    if not treffer.erkannt:
        # A4: keine Fehlvorstellung erfinden, nur weil die Zahl unbekannt ist.
        store.ereignis_schreiben(sitzung["id"], "Fehler nicht im Katalog",
                                 nutzdaten={"antwort": antwort})
        return _merke(sitzung["id"], sitzung,
                      fehlerhinweis="Interessant. Probier es noch einmal — "
                                    "oder schau unter „Das habe ich nicht "
                                    "verstanden“ nach.")

    fehlertyp = treffer.fehlertyp
    ergebnis = zustand.fehler_erkannt(sitzung["id"], fehlertyp["id"], antwort)
    erklaerung = katalog.erklaerung_fuer(fehlertyp["id"], _klasse(cfg))
    ergebnis = zustand.unterricht_beginnen(
        sitzung["id"], (erklaerung or {}).get("id"), phase=zustand.HOOK)
    return _merke(sitzung["id"], ergebnis, fehlerhinweis=None, tipp_stufe=0)


def _klasse(cfg=None) -> int:
    from .. import config
    return int(getattr(cfg or config.load_safe(), "learner_grade", 6) or 6)


def weiter(sitzung: dict) -> dict:
    """Ein Schritt im Lehrablauf, ohne Eingabe (HOOK → RULE → Beispiel → Übung)."""
    folge = {zustand.HOOK: zustand.RULE,
             zustand.RULE: zustand.WORKED_EXAMPLE,
             zustand.WORKED_EXAMPLE: zustand.GUIDED_TASK}
    naechste = folge.get(sitzung["phase"])
    if naechste is None:
        return sitzung
    return zustand.wechsle_phase(sitzung["id"], naechste)


def vorhersage_beantwortet(sitzung: dict, antwort: str) -> dict:
    """Die Vorhersage wird nicht benotet — sie macht den Widerspruch sichtbar."""
    store.ereignis_schreiben(sitzung["id"], "Vorhersage abgegeben",
                             nutzdaten={"wahl": antwort})
    return _merke(sitzung["id"], sitzung, vorhergesagt=antwort or "unbekannt")


def transfer_beantwortet(sitzung: dict, antwort: str, cfg=None) -> dict:
    """Derselbe Gedanke an einer anderen Struktur — ohne Rechnen."""
    aufgabe = inhalt_store.aufgabe(sitzung["fehlertyp_id"],
                                   inhalt_store.TRANSFER)
    if aufgabe is None:
        return zustand.wechsle_phase(sitzung["id"], zustand.COMPLETE)

    if (antwort or "").strip() == aufgabe["loesung"]:
        ergebnis = zustand.antwort_richtig(sitzung["id"], antwort, cfg=cfg)
        if ergebnis["zustand"] == zustand.MASTERED:
            return ergebnis
        return zustand.wechsle_phase(sitzung["id"], zustand.COMPLETE)

    ergebnis = zustand.runde_gescheitert(sitzung["id"], antwort, cfg=cfg)
    if ergebnis["zustand"] == zustand.ESCALATED:
        return ergebnis
    return _merke(sitzung["id"], ergebnis,
                  fehlerhinweis="Überleg noch einmal: Etwas dazubekommen kann "
                                "nie weniger werden.")


def tipp(sitzung: dict) -> dict:
    """Stufenweise mehr verraten — die Hilfe selbst verrät nie die Lösung."""
    daten = _daten(sitzung)
    stufe = int(daten.get("tipp_stufe", 0)) + 1
    store.ereignis_schreiben(sitzung["id"], "Tipp angefordert",
                             nutzdaten={"stufe": stufe})
    return _merke(sitzung["id"], sitzung, tipp_stufe=stufe)


def aufgabe_beantwortet(sitzung: dict, antwort: str, cfg=None) -> dict:
    """Die eigentliche Messung: Wirkte die Erklärung? (§19)"""
    phase = sitzung["phase"]
    rolle = (inhalt_store.GEFUEHRT if phase == zustand.GUIDED_TASK
             else inhalt_store.SELBSTSTAENDIG)
    aufgabe = inhalt_store.aufgabe(sitzung["fehlertyp_id"], rolle)
    if aufgabe is None:
        return sitzung

    if als_bruch(antwort) is None:
        return _merke(sitzung["id"], sitzung,
                      fehlerhinweis="Das kann ich nicht als Bruch lesen. "
                                    "Schreib es zum Beispiel so: 3/4")

    if ist_richtig(antwort, aufgabe["loesung"]):
        # Die Rechnung allein beendet die selbstständige Phase nicht — der
        # Transfer danach gehört dazu.
        ergebnis = zustand.antwort_richtig(
            sitzung["id"], antwort, cfg=cfg,
            darf_abschliessen=phase != zustand.INDEPENDENT_TASK)
        if ergebnis["zustand"] == zustand.MASTERED:
            return ergebnis
        ergebnis = _merke(sitzung["id"], ergebnis, tipp_stufe=0,
                          fehlerhinweis=None)
        if phase == zustand.GUIDED_TASK:
            return zustand.wechsle_phase(sitzung["id"], zustand.INDEPENDENT_TASK)
        return _merke(sitzung["id"], ergebnis, gerechnet=True)

    # Falsch: Runde zählen (A5 — das eskaliert notfalls selbst).
    ergebnis = zustand.runde_gescheitert(sitzung["id"], antwort, cfg=cfg)
    if ergebnis["zustand"] == zustand.ESCALATED:
        return ergebnis

    # Wieder dieselbe Fehlvorstellung? Verglichen wird mit dem Fehler, den
    # genau dieser Fehlertyp bei genau dieser Aufgabe erzeugt — die Aliasliste
    # ist auf die Diagnoseaufgabe geeicht und passt hier nicht.
    gleiche_fehlvorstellung = bool(
        aufgabe.get("typischer_fehler")
        and ist_richtig(antwort, aufgabe["typischer_fehler"]))
    if gleiche_fehlvorstellung or phase == zustand.INDEPENDENT_TASK:
        ergebnis = _merke(
            sitzung["id"], ergebnis, tipp_stufe=0, fehlerhinweis=None,
            war_selbststaendig=phase == zustand.INDEPENDENT_TASK)
        return zustand.wechsle_phase(sitzung["id"], zustand.ADAPTATION)

    daten = _daten(ergebnis)
    return _merke(sitzung["id"], ergebnis,
                  tipp_stufe=int(daten.get("tipp_stufe", 0)) + 1,
                  fehlerhinweis="Noch nicht. Schau dir das Bild noch einmal an.")


def weiter_nach_adaptation(sitzung: dict) -> dict:
    """Nach der anderen Darstellung zurück an die Aufgabe (§1.7)."""
    ziel = (zustand.INDEPENDENT_TASK
            if _daten(sitzung).get("war_selbststaendig") else zustand.GUIDED_TASK)
    return zustand.wechsle_phase(sitzung["id"], ziel)
