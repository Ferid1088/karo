"""Der Unterrichtsablauf: diagnostizieren, erklären, üben, messen.

Bildungslogik, getrennt von HTTP und Vorlagen (01_ARCHITECTURE.md §16) — der
Router reicht nur Antworten herein und bekommt einen fertigen Bildschirm
zurück. Alles hier ist Nachschlagen im Katalog; es gibt in dieser Datei
bewusst keinen Modellaufruf (§1, A3).
"""

from __future__ import annotations

import datetime as dt
from fractions import Fraction

from . import inhalt_store, katalog, protokoll, sitzung as zustand, store
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

def starte(konzept_id: int, thema_text: str = "",
           topic_id: int | None = None) -> dict:
    """Manuell eingetipptes Thema → normalisierte Eingabe → Diagnose (§13).

    `topic_id` ist gesetzt, wenn der Einstieg von einer Themenkarte kam —
    daran erkennt die Lernuebersicht spaeter, woran gerade gearbeitet wird.
    """
    konzept = store.konzept(konzept_id) or {}
    eingabe_id = store.eingabe_anlegen("manuell", fach=konzept.get('fach', ''),
                                       thema_text=thema_text or None,
                                       konzept_id=konzept_id,
                                       topic_id=topic_id)
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
        # Starting again is not evidence of mastery. Preserve the unfinished session.
        return offen
    return starte(konzept_id)


# --------------------------------------------------------------------------
# Bildschirm zusammenstellen
# --------------------------------------------------------------------------

def _voraussetzungsaufgaben(konzept_id: int | None) -> list[dict]:
    if not konzept_id:
        return []
    from . import voraussetzung as vor
    return vor.diagnoseaufgaben(int(konzept_id))


def _hilfe(konzept_id: int, phase: str | None) -> dict:
    """02 §5/§6: Hilfe ist ein Nachschlagen, in jeder Phase außer COMPLETE."""
    return {
        "erklaer_mehr": inhalt_store.hilfe_fuer_phase(konzept_id, phase) if phase else None,
        "faq": inhalt_store.faq(konzept_id),
    }


#: Bildschirme, auf denen das Kind antwortet — nur fuer sie laeuft eine Uhr.
_MIT_AUFGABE = ("anker", "diagnose", "vorhersage", "aufgabe", "transfer",
                "voraussetzung", "wiederholung_waehlen")


def _kennung(sitzung: dict, schirm: dict) -> str:
    """Woran die Uhr erkennt, dass eine andere Aufgabe zu sehen ist."""
    if schirm.get("art") not in _MIT_AUFGABE:
        return ""
    aufgabe = schirm.get("aufgabe") or {}
    teile = [schirm["art"], str(schirm.get("phase") or ""),
             str(aufgabe.get("id") or schirm.get("frage") or
                 schirm.get("voraussetzung") or "")]
    return "|".join(teile)


def bildschirm(sitzung: dict) -> dict:
    """Was das Kind jetzt sieht — eine Frage, eine Handlung.

    Hier beginnt auch die Uhr (Schritt 4a): sichtbar werden und bearbeitet
    werden faengt an derselben Stelle an. `protokoll.gezeigt` ist idempotent,
    derselbe Bildschirm zweimal gerendert setzt sie also nicht zurueck.
    """
    schirm = _bildschirm(sitzung)
    protokoll.gezeigt(sitzung["id"], _kennung(sitzung, schirm))
    return schirm


def _bildschirm(sitzung: dict) -> dict:
    konzept_id = sitzung["konzept_id"]
    daten = _daten(sitzung)
    zustand_name = sitzung["zustand"]
    phase = sitzung["phase"]

    # Z3: Eine fehlende Voraussetzung sticht jede Phase. Sie wurde festgestellt,
    # bevor eskaliert wurde — weitermachen hiesse, an derselben Stelle noch
    # einmal zu scheitern.
    if daten.get("voraussetzung_offen"):
        lokal = daten.get("voraussetzung_lokal")
        titel = daten.get("voraussetzung_titel") or daten["voraussetzung_offen"]
        hilfe = _hilfe(lokal or konzept_id, None)
        if daten.get("voraussetzung_lernen"):
            # Der Umweg laeuft oder ist geschafft. Sitzt die Grundlage, geht
            # es an die Stelle zurueck, an der es hakte.
            from . import voraussetzung as vor
            sitzt = bool(lokal) and vor.sitzt(int(lokal))
            return {"art": "voraussetzung_zurueck" if sitzt
                    else "voraussetzung_lernen",
                    "phase": phase, "voraussetzung": titel,
                    "konzept_id": lokal, "hilfe": hilfe}
        return {"art": "voraussetzung", "phase": phase,
                "voraussetzung": titel,
                "konzept_id": lokal,
                "aufgaben": _voraussetzungsaufgaben(lokal),
                "fehlerhinweis": daten.get("fehlerhinweis"),
                "hilfe": hilfe}

    if zustand_name == zustand.ESCALATED:
        return {"art": "eskaliert", "hilfe": _hilfe(konzept_id, None),
                "phase": None}
    if zustand_name == zustand.MASTERED:
        # Z3: Ein geschaffter Umweg fuehrt erst zurueck an die Stelle, an der
        # es hakte — den Wiederholungstermin waehlt das Kind dort.
        if daten.get("voraussetzung_detour"):
            ziel = store.sitzung(daten["voraussetzung_detour"]) or {}
            konzept = store.konzept(ziel["konzept_id"]) if ziel.get("konzept_id") else None
            return {"art": "voraussetzung_geschafft", "phase": None,
                    "thema": (konzept or {}).get("label", ""),
                    "hilfe": _hilfe(konzept_id, None)}
        # Schritt 4a: verstanden ist der Anfang, nicht das Ende. Bevor das
        # Kind weitergeht, waehlt es selbst, wann es das noch einmal
        # anschaut — wer den Termin mitbestimmt, haelt ihn eher ein.
        from . import wiederholung as wdh
        termin = wdh.offen_fuer(konzept_id)
        if termin is None and not wdh.gefestigt(konzept_id):
            return {"art": "wiederholung_waehlen", "phase": None,
                    "auswahl": wdh.auswahl(konzept_id),
                    "hilfe": _hilfe(konzept_id, None)}
        wiederholung_am = (termin or {}).get("faellig_am")
        if wiederholung_am:
            from ..services.today import date_label
            try:
                wiederholung_am = date_label(
                    dt.date.fromisoformat(wiederholung_am))
            except ValueError:
                pass
        return {"art": "geschafft", "hilfe": _hilfe(konzept_id, None),
                "phase": None, "wiederholung_am": wiederholung_am}

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

def anker_beantwortet(sitzung: dict, antwort: str, cfg=None) -> dict:
    """§11: Der Anker wird nicht benotet — er weckt nur das Vorwissen."""
    _buchen(sitzung, protokoll.ANKER, antwort=antwort, richtig=None, cfg=cfg)
    store.sitzung_aktualisieren(sitzung["id"], letzte_antwort=antwort or None)
    store.ereignis_schreiben(sitzung["id"], "Anker beantwortet")
    return _merke(sitzung["id"], sitzung, schritt=SCHRITT_AUFGABE,
                  fehlerhinweis=None)


def _diagnose_aufgaben(konzept_id: int) -> tuple[dict, dict]:
    first = (katalog.erstkontakt_fuer(konzept_id) or {}).get("erste_aufgabe") or {}
    second = first.get("bestaetigung") or {}
    # Older generated lessons lacked a second diagnostic question. Reuse a
    # DIFFERENT checked task, never repeat the first question indefinitely.
    if not second.get("frage") or not second.get("loesung"):
        second = next((task for error in store.fehlertypen(konzept_id)
                       for task in inhalt_store.aufgaben(error["id"], inhalt_store.SELBSTSTAENDIG)
                       if task["frage"] != first.get("frage")), {})
    return first, second


def diagnose_beantwortet(sitzung: dict, antwort: str, cfg=None) -> dict:
    """Produktives Scheitern auswerten: Fehlertyp bestimmen oder Erfolg buchen."""
    konzept_id = sitzung["konzept_id"]
    daten = _daten(sitzung)
    erste, bestaetigung = _diagnose_aufgaben(konzept_id)
    loesung = (bestaetigung if daten.get("zweite_diagnose") else erste).get(
        "loesung", "")

    if not (antwort or '').strip() or (als_bruch(loesung) is not None and als_bruch(antwort) is None):
        return _merke(sitzung["id"], sitzung,
                      fehlerhinweis="Schreib bitte eine Antwort ins Feld. Bei einer Rechnung "
                                    "nutze eine Zahl, zum Beispiel 2 oder 5/6.")

    richtig = ist_richtig(antwort, loesung)
    _buchen(sitzung, protokoll.DIAGNOSE, antwort=antwort, richtig=richtig,
            cfg=cfg)
    if richtig:
        ergebnis = zustand.antwort_richtig(sitzung["id"], antwort, cfg=cfg,
                                           darf_abschliessen=bool(daten.get('zweite_diagnose')))
        if ergebnis["zustand"] == zustand.MASTERED:
            return ergebnis
        # Eine richtige Antwort ist keine Beherrschung (A8): noch eine Aufgabe.
        if not bestaetigung:
            return _merke(sitzung["id"], ergebnis,
                          fehlerhinweis="Die zweite Kontrollaufgabe fehlt noch. Bitte lass dir helfen.")
        return _merke(sitzung["id"], ergebnis,
                      zweite_diagnose=bestaetigung.get("frage", ""),
                      fehlerhinweis=None)

    treffer = katalog.identifiziere(konzept_id, antwort, cfg=cfg)
    if not treffer.erkannt:
        # A4: keine Fehlvorstellung erfinden, nur weil die Zahl unbekannt ist.
        store.ereignis_schreiben(sitzung["id"], "Fehler nicht im Katalog",
                                 nutzdaten={"antwort": antwort})
        attempts = int(daten.get('unbekannte_antworten', 0)) + 1
        if attempts >= zustand.unbekannte_antworten(cfg):
            return zustand.eskalieren(sitzung['id'])
        return _merke(sitzung["id"], sitzung,
                      unbekannte_antworten=attempts,
                      fehlerhinweis="Interessant. Probier es noch einmal — "
                                    "oder schau unter „Das habe ich nicht "
                                    "verstanden“ nach.")

    fehlertyp = treffer.fehlertyp
    ergebnis = zustand.fehler_erkannt(sitzung["id"], fehlertyp["id"], antwort)
    entry = store.eingabe(sitzung.get("eingabe_id")) or {}
    from .. import topics
    topic = topics.get(entry["topic_id"]) if entry.get("topic_id") else {}
    grade = (topic or {}).get("grade") or _klasse(cfg)
    erklaerung = katalog.erklaerung_fuer(fehlertyp["id"], grade)
    ergebnis = zustand.unterricht_beginnen(
        sitzung["id"], (erklaerung or {}).get("id"), phase=zustand.HOOK)
    return _merke(sitzung["id"], ergebnis, fehlerhinweis=None, tipp_stufe=0)


def _herkunft(sitzung: dict, cfg=None) -> tuple[str | None, int]:
    """Fach und Klasse zu dieser Sitzung — fuer die Zeile im Protokoll."""
    konzept = store.konzept(sitzung.get("konzept_id")) or {}
    return konzept.get("fach"), konzept.get("klasse_bis") or _klasse(cfg)


def _buchen(sitzung: dict, rolle: str, *, aufgabe: dict | None = None,
            antwort: str | None = None, richtig: bool | None = None,
            cfg=None) -> None:
    """Eine beantwortete Aufgabe festhalten (Schritt 4a).

    Hier und nicht im Router: eine Antwort ist eine Antwort, auch wenn sie
    ueber einen anderen Weg hereinkommt.
    """
    fach, klasse = _herkunft(sitzung, cfg)
    protokoll.antwort_buchen(sitzung, rolle, aufgabe=aufgabe, antwort=antwort,
                             richtig=richtig, fach=fach, klasse=klasse, cfg=cfg)


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
    _buchen(sitzung, protokoll.VORHERSAGE,
            aufgabe=inhalt_store.aufgabe(sitzung["fehlertyp_id"],
                                         inhalt_store.VORHERSAGE),
            antwort=antwort, richtig=None)
    store.ereignis_schreiben(sitzung["id"], "Vorhersage abgegeben",
                             nutzdaten={"wahl": antwort})
    return _merke(sitzung["id"], sitzung, vorhergesagt=antwort or "unbekannt")


def transfer_beantwortet(sitzung: dict, antwort: str, cfg=None) -> dict:
    """Derselbe Gedanke an einer anderen Struktur — ohne Rechnen."""
    aufgabe = inhalt_store.aufgabe(sitzung["fehlertyp_id"],
                                   inhalt_store.TRANSFER)
    if aufgabe is None:
        return zustand.wechsle_phase(sitzung["id"], zustand.COMPLETE)

    richtig = ist_richtig(antwort, aufgabe["loesung"])
    _buchen(sitzung, protokoll.TRANSFER, aufgabe=aufgabe, antwort=antwort,
            richtig=richtig, cfg=cfg)
    if richtig:
        ergebnis = zustand.antwort_richtig(sitzung["id"], antwort, cfg=cfg)
        if ergebnis["zustand"] == zustand.MASTERED:
            return ergebnis
        return zustand.wechsle_phase(sitzung["id"], zustand.COMPLETE)

    ergebnis = zustand.runde_gescheitert(sitzung["id"], antwort, cfg=cfg)
    if ergebnis["zustand"] == zustand.ESCALATED:
        return ergebnis
    return _merke(sitzung["id"], ergebnis,
                  fehlerhinweis="Schau dir die Frage noch einmal in Ruhe an. "
                                "Welche Regel hilft dir hier?")


def tipp(sitzung: dict) -> dict:
    """Stufenweise mehr verraten — die Hilfe selbst verrät nie die Lösung."""
    daten = _daten(sitzung)
    stufe = int(daten.get("tipp_stufe", 0)) + 1
    # Ein Tipp ist eine Eingabe: die Uhr laeuft weiter, und die Zeile der
    # Antwort haelt fest, dass Hilfe im Spiel war.
    protokoll.tipp_genutzt(sitzung["id"])
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

    if not (antwort or '').strip() or (als_bruch(aufgabe['loesung']) is not None and als_bruch(antwort) is None):
        return _merke(sitzung["id"], sitzung,
                      fehlerhinweis="Schreib bitte eine Antwort ins Feld. Bei einer Rechnung "
                                    "nutze eine Zahl, zum Beispiel 2 oder 3/4.")

    richtig = ist_richtig(antwort, aufgabe["loesung"])
    _buchen(sitzung, protokoll.AUFGABE, aufgabe=aufgabe, antwort=antwort,
            richtig=richtig, cfg=cfg)
    if richtig:
        # Die Rechnung allein beendet die selbstständige Phase nicht — der
        # Transfer danach gehört dazu.
        ergebnis = zustand.antwort_richtig(
            sitzung["id"], antwort, cfg=cfg,
            darf_abschliessen=False)
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


def voraussetzung_beantwortet(sitzung: dict, antworten: list[str], cfg=None) -> dict:
    """Die kurze Diagnose zur Voraussetzung auswerten (Z3).

    Sitzt sie, war sie nicht der Grund — dann eskaliert Karo wie bisher.
    Sitzt sie nicht, lernt das Kind erst sie; die Sitzung wird dafuer auf das
    Voraussetzungskonzept umgestellt und kommt danach hierher zurueck.
    """
    from . import sitzung as zustand_modul, voraussetzung as vor

    daten = _daten(sitzung)
    lokal = daten.get("voraussetzung_lokal")
    aufgaben = _voraussetzungsaufgaben(lokal)
    if not aufgaben:
        # Ohne Aufgaben laesst sich nichts feststellen: dann wie bisher.
        _merke(sitzung["id"], sitzung, voraussetzung_offen=None,
               voraussetzung_lokal=None, voraussetzung_titel=None)
        return zustand_modul.eskalieren(sitzung["id"], cfg=cfg)

    # Jede Aufgabe der kurzen Diagnose bekommt ihre eigene Zeile.
    for aufgabe, antwort in zip(aufgaben, list(antworten) + [""] * len(aufgaben)):
        _buchen(sitzung, protokoll.VORAUSSETZUNG, aufgabe=aufgabe,
                antwort=antwort,
                richtig=ist_richtig(antwort, aufgabe.get("loesung", "")),
                cfg=cfg)

    if vor.pruefen(list(antworten), aufgaben):
        store.ereignis_schreiben(sitzung["id"], "Voraussetzung sitzt — es lag nicht daran")
        _merke(sitzung["id"], sitzung, voraussetzung_offen=None,
               voraussetzung_lokal=None, voraussetzung_titel=None)
        return zustand_modul.eskalieren(store.sitzung(sitzung["id"])["id"], cfg=cfg)

    store.ereignis_schreiben(sitzung["id"], "Voraussetzung fehlt — wird zuerst gelernt",
                             nutzdaten={"konzept_id": lokal})
    return _merke(sitzung["id"], sitzung, voraussetzung_lernen=True)


def wiederholung_gewaehlt(sitzung: dict, tage: int) -> dict:
    """Das Kind hat seinen Tag gewaehlt (Schritt 4a)."""
    from . import wiederholung as wdh
    wdh.planen(sitzung["konzept_id"], int(tage), sitzung_id=sitzung["id"])
    store.ereignis_schreiben(sitzung["id"], "Wiederholung geplant",
                             nutzdaten={"tage": int(tage)})
    return store.sitzung(sitzung["id"])


def zurueck_von_voraussetzung(sitzung: dict) -> dict:
    """Nach der Voraussetzung zurueck an die Stelle, an der es hakte."""
    daten = _daten(sitzung)
    if not daten.get("voraussetzung_offen"):
        return sitzung
    store.ereignis_schreiben(sitzung["id"], "Zurueck vom Voraussetzungskonzept")
    return _merke(sitzung["id"], sitzung, voraussetzung_offen=None,
                  voraussetzung_lokal=None, voraussetzung_titel=None,
                  voraussetzung_lernen=None, tipp_stufe=0, fehlerhinweis=None)


def voraussetzung_lernen_starten(sitzung: dict) -> dict:
    """Der Umweg (Z3): erst die fehlende Grundlage lernen, dann zurueck.

    Die wartende Sitzung bleibt offen; die Grundlage laeuft als eigene
    Lernrunde im selben Thema, damit das Resume sie findet. Laeuft sie
    schon, wird sie nicht verdoppelt. Trug auch sie nicht, hilft ein
    Mensch statt eines zweiten Umwegs.
    """
    daten = _daten(sitzung)
    lokal = daten.get("voraussetzung_lokal")
    if not daten.get("voraussetzung_offen") or not lokal:
        return sitzung
    eintrag = store.eingabe(sitzung.get("eingabe_id")) or {}
    letzte = store.letzte_fuer_thema(eintrag.get("topic_id"), int(lokal))
    if letzte and letzte["zustand"] not in zustand.ENDZUSTAENDE:
        return letzte                                   # laeuft bereits
    if letzte and letzte["zustand"] == zustand.ESCALATED:
        # Trug auch die Grundlage nicht, hilft ein Mensch. Erst die
        # Merker loeschen — eskaliert darf nicht noch offen wirken.
        ziel = zurueck_von_voraussetzung(sitzung)
        return zustand.eskalieren(ziel["id"])
    if letzte and letzte["zustand"] == zustand.MASTERED:
        return zurueck_von_voraussetzung(sitzung)       # geschafft genug
    store.ereignis_schreiben(sitzung["id"], "Voraussetzung wird gelernt",
                             nutzdaten={"konzept_id": int(lokal)})
    umweg = starte(int(lokal), daten.get("voraussetzung_titel") or "",
                   topic_id=eintrag.get("topic_id"))
    return _merke(umweg["id"], umweg, voraussetzung_detour=sitzung["id"])


def voraussetzung_weiter_zum_thema(sitzung: dict) -> dict:
    """Vom geschafften Umweg zurueck an die Stelle, an der es hakte (Z3)."""
    ziel_id = _daten(sitzung).get("voraussetzung_detour")
    ziel = store.sitzung(ziel_id) if ziel_id else None
    if ziel is None:
        return sitzung
    return zurueck_von_voraussetzung(ziel)


def weiter_nach_adaptation(sitzung: dict) -> dict:
    """Nach der anderen Darstellung zurück an die Aufgabe (§1.7)."""
    ziel = (zustand.INDEPENDENT_TASK
            if _daten(sitzung).get("war_selbststaendig") else zustand.GUIDED_TASK)
    return zustand.wechsle_phase(sitzung["id"], ziel)
