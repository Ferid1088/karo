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
from . import varianten
from .antwortvergleich import check_answer
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


def ist_richtig(antwort: str | None, loesung: str,
                antwort_art: str | None = None) -> bool:
    """6/8 ist dieselbe Antwort wie 3/4 — und 2x+6 wie 2(x+3).

    Der eigentliche Vergleich lebt in `antwortvergleich.check_answer` und
    wertet je nach `antwort_art` der Aufgabe aus; ohne Angabe versucht er
    nacheinander Gleichung, Term, Zahl und Zeichenkette.
    """
    return check_answer(antwort, loesung, antwort_art)


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
    """Was diesen Bildschirm genau meint — art und Phase allein reichen
    nicht: gefuehrte und selbststaendige Aufgabe oder beide Diagnose-Fragen
    teilen sich denselben Bildschirm. Erst die Aufgabe dahinter macht ein
    abgeschicktes Formular eindeutig."""
    aufgabe = schirm.get("aufgabe") or {}
    teile = [schirm["art"], str(schirm.get("phase") or ""),
             str(aufgabe.get("id") or aufgabe.get("frage")
                 or schirm.get("frage") or schirm.get("voraussetzung") or "")]
    return "|".join(teile)


def bildschirm(sitzung: dict) -> dict:
    """Was das Kind jetzt sieht — eine Frage, eine Handlung.

    Hier beginnt auch die Uhr (Schritt 4a): sichtbar werden und bearbeitet
    werden faengt an derselben Stelle an. `protokoll.gezeigt` ist idempotent,
    derselbe Bildschirm zweimal gerendert setzt sie also nicht zurueck.
    """
    if (sitzung["zustand"] == zustand.TEACHING
            and sitzung["phase"] == zustand.COMPLETE):
        # Altlast aus der Zeit, als COMPLETE ein Parkplatz war: die Sitzung
        # ist offen und nicht beherrscht — sie bekommt ihre naechste Runde,
        # statt „verstanden" vorzugaukeln.
        sitzung = _naechste_uebungsrunde(sitzung)
    schirm = _bildschirm(sitzung)
    # Eine Aufgabe, die der Katalog nicht hergibt, darf kein leeres Formular
    # werden: keine Antwortmoeglichkeit ist ein Dead End. Besser ehrlich —
    # die generische Seite sagt, dass ein Mensch helfen soll.
    if (schirm["art"] in ("vorhersage", "transfer", "aufgabe")
            and not schirm.get("aufgabe")):
        schirm = {"art": "inhalt_fehlt", "phase": sitzung.get("phase"),
                  "hilfe": _hilfe(sitzung["konzept_id"],
                                  sitzung.get("phase"))}
    # Die Kennung wandert mit ins Formular: beim naechsten POST erkennt der
    # Router daran, ob die Antwort noch zu dieser Aufgabe gehoert. Nur ein
    # Bildschirm mit sichtbarer Aufgabe darf die Uhr anstellen.
    schirm["kennung"] = _kennung(sitzung, schirm)
    protokoll.gezeigt(sitzung["id"],
                      schirm["kennung"]
                      if schirm["art"] in _MIT_AUFGABE else "")
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
            sitzt = (bool(lokal)
                     and vor.sitzt(int(lokal),
                                   child_key=store.fortschritt_scope(sitzung)))
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
        scope = store.fortschritt_scope(sitzung)
        termin = wdh.offen_fuer(konzept_id, child_key=scope)
        if termin is None and not wdh.gefestigt(konzept_id, child_key=scope):
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
        if daten.get("diagnose_zusatz"):
            # Der allgemeine Pfad nach einer unbekannten Antwort: eine
            # andere gepruefte Aufgabe desselben Konzepts.
            aufgabe = daten["diagnose_zusatz"]
        elif daten.get("zweite_diagnose"):
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
                "aufgabe": _transfer_aufgabe(sitzung),
                "fehlerhinweis": daten.get("fehlerhinweis"),
                "hilfe": _hilfe(konzept_id, phase)}

    if phase in (zustand.GUIDED_TASK, zustand.INDEPENDENT_TASK):
        aufgabe = _uebungsaufgabe(sitzung, phase)
        tipps = (aufgabe or {}).get("tipps") or []
        stufe = int(daten.get("tipp_stufe", 0))
        return {"art": "aufgabe", "phase": phase, "aufgabe": aufgabe,
                # B1: nur die geführte Aufgabe zeigt ihr Bild.
                "bild": (aufgabe or {}).get("visualisierung")
                        if phase == zustand.GUIDED_TASK else None,
                "tipps": tipps[:stufe], "tipp_offen": stufe < len(tipps),
                "fehlerhinweis": daten.get("fehlerhinweis"),
                "aufmunterung": daten.get("aufmunterung"),
                "hilfe": _hilfe(konzept_id, phase)}

    if phase == zustand.ADAPTATION:
        return {"art": "anders", "phase": phase, "inhalt": inhalt,
                # B1: andere Darstellung, nicht derselbe Streifen noch einmal.
                "bild": (erklaerung or {}).get("visualisierung_alternativ"),
                "hilfe": _hilfe(konzept_id, phase)}

    # Jede andere Kombination ist nicht vorgesehen: lieber ein ehrlicher
    # „Karo weiss nicht weiter"-Bildschirm als ein falsches „geschafft".
    return {"art": "unbekannt", "phase": phase, "hilfe": _hilfe(konzept_id, None)}


# --------------------------------------------------------------------------
# Antworten verarbeiten
# --------------------------------------------------------------------------

def _uebungsaufgabe(sitzung: dict, phase: str) -> dict | None:
    """Welche Uebungsaufgabe diese Runde stellt.

    Die gefuehrte ist immer die erste gepruefte. Die selbststaendige ist in
    der ersten Runde ebenfalls die erste gepruefte; eine Extra-Runde nach
    richtigem Transfer zeigt die Aufgabe, die dafuer ausgewaehlt und in der
    Sitzung festgehalten wurde — sie bleibt ueber Neuladen dieselbe.
    """
    rolle = (inhalt_store.GEFUEHRT if phase == zustand.GUIDED_TASK
             else inhalt_store.SELBSTSTAENDIG)
    if rolle == inhalt_store.SELBSTSTAENDIG:
        gespeichert = _daten(sitzung).get("selbst_aufgabe")
        if gespeichert:
            return gespeichert
    return inhalt_store.aufgabe(sitzung["fehlertyp_id"], rolle)


def _transfer_aufgabe(sitzung: dict) -> dict | None:
    """Die Transferfrage der Runde — nach einer Runde, die sass, die
    naechste gepruefte, nicht noch einmal dieselbe."""
    gezeigt = set(_daten(sitzung).get("transfer_gezeigt") or [])
    kandidaten = inhalt_store.aufgaben(sitzung["fehlertyp_id"],
                                       inhalt_store.TRANSFER)
    for aufgabe in kandidaten:
        if aufgabe["frage"] not in gezeigt:
            return aufgabe
    return kandidaten[0] if kandidaten else None


def _neue_selbstaufgabe(sitzung: dict) -> dict | None:
    """Eine selbststaendige Aufgabe, die diese Sitzung noch nicht gestellt
    hat: erst eine ungestellte gepruefte aus dem Katalog, dann eine
    nachgerechnete Variante des Generators. Erst wenn beides versagt — zum
    Beispiel eine Aufgabenart, die der Generator nicht nachbauen kann — kommt
    die erste noch einmal: lieber bekannt als ein Dead End.
    """
    gezeigt = set(_daten(sitzung).get("selbst_gezeigt") or [])
    # Was das Kind schon beantwortet hat, zaehlt auch ohne Marker — eine
    # Altsitzung aus der Parkplatz-Zeit kennt `selbst_gezeigt` nicht.
    gesehen = protokoll.gesehene_aufgaben(
        sitzung["konzept_id"], store.fortschritt_scope(sitzung))
    kandidaten = inhalt_store.aufgaben(sitzung["fehlertyp_id"],
                                       inhalt_store.SELBSTSTAENDIG)
    frisch = [a for a in kandidaten
              if a["frage"] not in gezeigt and a["id"] not in gesehen]
    if frisch:
        return frisch[0]
    for vorlage in kandidaten:
        for variante in varianten.varianten(vorlage, 8):
            if variante["frage"] not in gezeigt:
                return variante
    return kandidaten[0] if kandidaten else None


def _naechste_uebungsrunde(sitzung: dict) -> dict:
    """Richtig, aber noch nicht sicher genug: noch eine selbststaendige
    Runde mit einer neuen Aufgabe — „verstanden" gibt es erst bei MASTERED.
    """
    neu = _neue_selbstaufgabe(sitzung)
    gezeigt = list(_daten(sitzung).get("selbst_gezeigt") or [])
    if neu and neu.get("frage"):
        gezeigt.append(neu["frage"])
    _merke(sitzung["id"], sitzung,
           gerechnet=None, tipp_stufe=0, fehlerhinweis=None,
           selbst_aufgabe=neu, selbst_gezeigt=gezeigt,
           aufmunterung="Fast geschafft — eine neue Aufgabe wartet noch.")
    return zustand.wechsle_phase(sitzung["id"], zustand.INDEPENDENT_TASK)


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


def _diagnose_zusatz(konzept_id: int, daten: dict,
                     erste: dict) -> dict | None:
    """Eine andere gepruefte Aufgabe zum selben Konzept — aus dem Katalog,
    nicht aus einem Modell."""
    gezeigt = set(daten.get("zusatz_gezeigt") or [])
    gezeigt.add(erste.get("frage"))
    for fehlertyp in store.fehlertypen(konzept_id):
        for rolle in (inhalt_store.GEFUEHRT, inhalt_store.SELBSTSTAENDIG):
            for aufgabe in inhalt_store.aufgaben(fehlertyp["id"], rolle):
                if aufgabe.get("loesung") and aufgabe["frage"] not in gezeigt:
                    return aufgabe
    return None


def _zerlege_hinweis(aufgabe: dict) -> str:
    tipp = ((aufgabe.get("tipps") or [None])[0]
            or "Was ist gegeben, was ist gesucht? Zerlege sie in Schritte.")
    return f"Schauen wir uns die Aufgabe genauer an: {tipp}"


def _schrittweg(aufgabe: dict) -> str | None:
    schritte = aufgabe.get("schritte") or []
    if schritte:
        return "So geht es Schritt für Schritt: " + " → ".join(
            str(s) for s in schritte)
    if aufgabe.get("aufloesung"):
        return "So geht es: " + str(aufgabe["aufloesung"])
    return None


def _zwischenschritt(aufgabe: dict) -> str:
    schritte = aufgabe.get("schritte") or []
    if schritte:
        return f"Fast! Der nächste Schritt ist: {schritte[0]}"
    if aufgabe.get("aufloesung"):
        return "Schau genau hin: " + str(aufgabe["aufloesung"])
    return "Noch nicht ganz. Geh die Schritte der Reihe nach durch."


def _unbekannte_diagnose(sitzung: dict, daten: dict, erste: dict,
                         cfg=None) -> dict:
    """Falsch ohne Katalogtreffer: allgemeiner unterrichten statt aufgeben.

    Ein Fehlertyp-Alias ist eine Abkuerzung zur passenden Erklaerung, keine
    Eintrittskarte in den Unterricht. Dieselbe Aufgabe bekommt erst einen
    Hinweis, dann ihren Loesungsweg; danach kommt eine andere gepruefte
    Aufgabe. Jede Antwort trifft also eine neue Intervention — erst wenn
    das Material ausgeht oder die Versuche `unbekannte_antworten`
    ueberschreiten, hilft ein Mensch, und `eskalieren` prueft dabei wie
    immer die Voraussetzungen.
    """
    versuche = int(daten.get("unbekannte_antworten", 0)) + 1
    aktuell = daten.get("diagnose_zusatz") or erste
    stufe = int(daten.get("unbekannt_stufe", 0)) + 1

    merk: dict = {"unbekannte_antworten": versuche}
    weiter_moeglich = True
    if stufe == 1:
        merk.update(unbekannt_stufe=1, fehlerhinweis=_zerlege_hinweis(aktuell))
    elif stufe == 2 and _schrittweg(aktuell):
        merk.update(unbekannt_stufe=2, fehlerhinweis=_schrittweg(aktuell))
    else:
        neu = _diagnose_zusatz(sitzung["konzept_id"], daten, erste)
        if neu is not None:
            gezeigt = list(daten.get("zusatz_gezeigt") or [])
            gezeigt.append(neu["frage"])
            merk.update(unbekannt_stufe=1, diagnose_zusatz=neu,
                        zusatz_gezeigt=gezeigt,
                        fehlerhinweis=_zerlege_hinweis(neu))
        else:
            weiter_moeglich = False

    if not weiter_moeglich or versuche >= zustand.unbekannte_antworten(cfg):
        return zustand.eskalieren(sitzung["id"])
    return _merke(sitzung["id"], sitzung, **merk)


def diagnose_beantwortet(sitzung: dict, antwort: str, cfg=None) -> dict:
    """Produktives Scheitern auswerten: Fehlertyp bestimmen oder Erfolg buchen."""
    konzept_id = sitzung["konzept_id"]
    daten = _daten(sitzung)
    erste, bestaetigung = _diagnose_aufgaben(konzept_id)
    # Was am Schirm steht, entscheidet die Loesung: eine Zusatzaufgabe aus
    # dem allgemeinen Pfad, die Kontrollfrage oder die erste Aufgabe.
    gestellt = (daten.get("diagnose_zusatz")
                or (bestaetigung if daten.get("zweite_diagnose") else erste)
                or {})
    loesung = gestellt.get("loesung", "")

    if not (antwort or '').strip() or (als_bruch(loesung) is not None and als_bruch(antwort) is None):
        return _merke(sitzung["id"], sitzung,
                      fehlerhinweis="Schreib bitte eine Antwort ins Feld. Bei einer Rechnung "
                                    "nutze eine Zahl, zum Beispiel 2 oder 5/6.")

    richtig = ist_richtig(antwort, loesung, gestellt.get("antwort_art"))
    _buchen(sitzung, protokoll.DIAGNOSE,
            aufgabe=gestellt if gestellt.get("id") else None,
            antwort=antwort, richtig=richtig, cfg=cfg)
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
                      diagnose_zusatz=None, unbekannt_stufe=0,
                      fehlerhinweis=None)

    treffer = katalog.identifiziere(konzept_id, antwort, cfg=cfg)
    if not treffer.erkannt:
        # A4: keine Fehlvorstellung erfinden, nur weil die Zahl unbekannt ist.
        # Falsch heisst lernen, nicht Dead End — der allgemeine Pfad
        # unterrichtet weiter, ohne einen Fehlertyp zu raten.
        store.ereignis_schreiben(sitzung["id"], "Fehler nicht im Katalog",
                                 nutzdaten={"antwort": antwort})
        return _unbekannte_diagnose(sitzung, daten, erste, cfg=cfg)

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
    aufgabe = _transfer_aufgabe(sitzung)
    if aufgabe is None:
        return _naechste_uebungsrunde(sitzung)

    richtig = ist_richtig(antwort, aufgabe["loesung"],
                        aufgabe.get("antwort_art"))
    _buchen(sitzung, protokoll.TRANSFER, aufgabe=aufgabe, antwort=antwort,
            richtig=richtig, cfg=cfg)
    if richtig:
        ergebnis = zustand.antwort_richtig(sitzung["id"], antwort, cfg=cfg)
        if ergebnis["zustand"] == zustand.MASTERED:
            return ergebnis
        # Richtig, aber noch nicht sicher: der gestellte Transfer zaehlt als
        # gesehen, dann folgt die naechste Runde — COMPLETE ist kein
        # Parkplatz.
        gezeigt = list(_daten(sitzung).get("transfer_gezeigt") or [])
        gezeigt.append(aufgabe["frage"])
        sitzung = _merke(sitzung["id"], ergebnis, transfer_gezeigt=gezeigt)
        return _naechste_uebungsrunde(sitzung)

    ergebnis = zustand.runde_gescheitert(sitzung["id"], antwort, cfg=cfg)
    if ergebnis["zustand"] == zustand.ESCALATED:
        return ergebnis
    # Falscher Transfer heisst nicht „noch einmal dieselbe Frage": zurueck
    # zur Regel in anderer Darstellung, dann gefuehrt weiter — und der
    # naechste Transfer ist eine neue Frage, diese hier gilt als gesehen.
    gezeigt = list(_daten(sitzung).get("transfer_gezeigt") or [])
    gezeigt.append(aufgabe["frage"])
    ergebnis = _merke(sitzung["id"], ergebnis, tipp_stufe=0,
                      fehlerhinweis=None, transfer_gezeigt=gezeigt,
                      war_selbststaendig=False)
    return zustand.wechsle_phase(sitzung["id"], zustand.ADAPTATION)


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
    aufgabe = _uebungsaufgabe(sitzung, phase)
    if aufgabe is None:
        return sitzung

    if not (antwort or '').strip() or (als_bruch(aufgabe['loesung']) is not None and als_bruch(antwort) is None):
        return _merke(sitzung["id"], sitzung,
                      fehlerhinweis="Schreib bitte eine Antwort ins Feld. Bei einer Rechnung "
                                    "nutze eine Zahl, zum Beispiel 2 oder 3/4.")

    richtig = ist_richtig(antwort, aufgabe["loesung"],
                        aufgabe.get("antwort_art"))
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
                          fehlerhinweis=None, gefuehrt_fehler=0)
        if phase == zustand.GUIDED_TASK:
            daten = _daten(sitzung)
            if daten.get("war_selbststaendig"):
                # Zurueck aus der Adaptation: die naechste selbststaendige
                # Aufgabe ist eine neue, nicht die gescheiterte.
                naechste = _neue_selbstaufgabe(sitzung)
                gezeigt = list(daten.get("selbst_gezeigt") or [])
                if naechste and naechste.get("frage"):
                    gezeigt.append(naechste["frage"])
                _merke(sitzung["id"], ergebnis,
                       selbst_aufgabe=naechste, selbst_gezeigt=gezeigt,
                       war_selbststaendig=None)
            else:
                # Die erste selbststaendige Aufgabe gilt ab jetzt als
                # gestellt — die Extra-Runde danach muss eine andere waehlen.
                naechste = inhalt_store.aufgabe(
                    sitzung["fehlertyp_id"], inhalt_store.SELBSTSTAENDIG)
                _merke(sitzung["id"], ergebnis,
                       selbst_gezeigt=[(naechste or {}).get("frage") or ""])
            return zustand.wechsle_phase(sitzung["id"], zustand.INDEPENDENT_TASK)
        return _merke(sitzung["id"], ergebnis, gerechnet=True)

    # Falsch: Runde zählt nur, wenn die Intervention sich aendert — und
    # `runde_gescheitert` eskaliert notfalls selbst (A5).
    ergebnis = zustand.runde_gescheitert(sitzung["id"], antwort, cfg=cfg)
    if ergebnis["zustand"] == zustand.ESCALATED:
        return ergebnis

    # Wieder dieselbe Fehlvorstellung? Verglichen wird mit dem Fehler, den
    # genau dieser Fehlertyp bei genau dieser Aufgabe erzeugt — die Aliasliste
    # ist auf die Diagnoseaufgabe geeicht und passt hier nicht.
    gleiche_fehlvorstellung = bool(
        aufgabe.get("typischer_fehler")
        and ist_richtig(antwort, aufgabe["typischer_fehler"],
                        aufgabe.get("antwort_art")))

    if phase == zustand.INDEPENDENT_TASK:
        # Die selbststaendige Aufgabe hat nicht gesessen: andere Darstellung,
        # dann gefuehrt, dann eine NEUE selbststaendige — nicht dieselbe.
        daten = _daten(sitzung)
        gezeigt = list(daten.get("selbst_gezeigt") or [])
        if aufgabe.get("frage"):
            gezeigt.append(aufgabe["frage"])
        ergebnis = _merke(sitzung["id"], ergebnis, tipp_stufe=0,
                          fehlerhinweis=None, war_selbststaendig=True,
                          selbst_gezeigt=gezeigt, gefuehrt_fehler=0)
        return zustand.wechsle_phase(sitzung["id"], zustand.ADAPTATION)

    # Gefuehrt: dieselbe Fehlvorstellung oder drei Versuche fuehren zur
    # anderen Darstellung; davor steigt die Hilfe stufenweise.
    fehler = int(_daten(sitzung).get("gefuehrt_fehler", 0)) + 1
    if gleiche_fehlvorstellung or fehler >= 3:
        ergebnis = _merke(sitzung["id"], ergebnis, tipp_stufe=0,
                          fehlerhinweis=None, war_selbststaendig=False,
                          gefuehrt_fehler=0)
        return zustand.wechsle_phase(sitzung["id"], zustand.ADAPTATION)

    daten = _daten(ergebnis)
    hinweis = ("Noch nicht. Schau dir das Bild noch einmal an."
               if fehler == 1 else _zwischenschritt(aufgabe))
    return _merke(sitzung["id"], ergebnis,
                  tipp_stufe=int(daten.get("tipp_stufe", 0)) + 1,
                  gefuehrt_fehler=fehler, fehlerhinweis=hinweis)


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
                richtig=ist_richtig(antwort, aufgabe.get("loesung", ""),
                                    aufgabe.get("antwort_art")),
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
    wdh.planen(sitzung["konzept_id"], int(tage), sitzung_id=sitzung["id"],
               child_key=store.fortschritt_scope(sitzung))
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
        # Auch ein weitergefuehrter Umweg braucht den Rueckweg-Marker —
        # sonst landet er bei MASTERED auf der Terminwahl und die wartende
        # Sitzung findet nie mehr den Weg zurueck.
        return _merke(letzte["id"], letzte, voraussetzung_detour=sitzung["id"])
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
    """Nach der anderen Darstellung geht es kleinschrittig weiter (§1.7).

    Frueher kehrte ein gescheiterter Selbstversuch direkt zur selben
    Aufgabe zurueck. Jetzt gilt fuer jeden Fehler dieselbe Kette: andere
    Darstellung → gefuehrte Aufgabe → neue selbststaendige Aufgabe →
    neuer Transfer. `war_selbststaendig` merkt dabei nur, dass die
    naechste selbststaendige Aufgabe eine neue sein muss.
    """
    return zustand.wechsle_phase(sitzung["id"], zustand.GUIDED_TASK)
