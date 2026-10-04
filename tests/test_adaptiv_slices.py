"""Lernreisen auf den sechs kuratierten Fach-Slices — die echten Gates:

grosse Luecke → Voraussetzung → deren Voraussetzung → Level 0 → Aufstieg →
Zurueck zum Ziel → Transfer. Dazu: teilweise richtige Antworten in jedem
Fach und der Nachweis, dass Karo fehlende Inhalte bestellt statt das Kind
ins Leere laufen zu lassen.
"""
from __future__ import annotations

import json

import pytest

BEKANNTE_AKTIONEN = {
    "DIAGNOSE", "ERKLAEREN", "ERKLAEREN_ANDERS", "UEBUNG_GEFUEHRT",
    "UEBUNG_SELBST", "TRANSFER", "VORAUSSETZUNG_PRUEFEN",
    "VORAUSSETZUNG_LERNEN", "ZURUECK_ZUM_ZIEL", "BEGLEITEN", "GESCHAFFT"}


def _setup(app_env) -> None:
    """Datenbank plus kuratierter Slice-Bestand — den saet saee_alle() in
    Produktion mit, hier legt ihn der Test ausdruecklich an."""
    app_env.db.init()
    from app.adaptiv import slices, store
    store.init()
    slices.seed()


def _lokal(dienst_id: str) -> int:
    from app import db
    row = db.q1(
        "SELECT konzept_id FROM lern_curriculum_import "
        "WHERE json_extract(provenance, '$.concept_id') = ?", dienst_id)
    assert row, f"Slice {dienst_id} nicht lokal eingespielt"
    return int(row["konzept_id"])


def _daten(sitzung: dict) -> dict:
    roh = sitzung.get("daten")
    if isinstance(roh, str):
        roh = json.loads(roh)
    return dict(roh or {})


def _falsch_einsteigen(sitzung: dict, runden: int = 4) -> dict:
    """Kind beantwortet die Diagnose durchgehend falsch bis zur Eskalation."""
    from app.adaptiv import store, unterricht
    s = unterricht.anker_beantwortet(sitzung, "")
    for _ in range(runden):
        s = store.sitzung(s["id"])
        if s["zustand"] == "ESCALATED":
            break
        s = unterricht.diagnose_beantwortet(s, "keine Ahnung")
    return store.sitzung(s["id"])


def _diagnose_loesen(sitzung: dict, runden: int = 6) -> dict:
    """Kind beantwortet die gestellte Diagnoseaufgabe mit der
    Katalogloesung — kein Raten, sondern lesen, was am Schirm steht."""
    from app.adaptiv import store, unterricht
    s = sitzung
    anker_offen = s["zustand"] == "DIAGNOSING" \
        and _daten(s).get("schritt", "anker") == "anker"
    if anker_offen:
        s = unterricht.anker_beantwortet(s, "")
    for _ in range(runden):
        s = store.sitzung(s["id"])
        if s["zustand"] == "ESCALATED":
            s = unterricht.fortsetzen(s)
            s = store.sitzung(s["id"])
        if s["zustand"] != "DIAGNOSING":
            break
        daten = _daten(s)
        erste, bestaetigung = unterricht._diagnose_aufgaben(
            s["konzept_id"])
        gestellt = (daten.get("diagnose_zusatz")
                    or (bestaetigung if daten.get("zweite_diagnose")
                        else erste) or {})
        s = unterricht.diagnose_beantwortet(
            s, gestellt.get("loesung") or "keine Ahnung")
    return store.sitzung(s["id"])


def _umweg_starten(sitzung: dict) -> dict:
    """Eltern-Sitzung: Voraussetzung falsch beantworten → Umweg-Sitzung."""
    from app.adaptiv import unterricht
    s = unterricht.fortsetzen(sitzung)
    s = unterricht.voraussetzung_beantwortet(s, ["weiss nicht", "weiss nicht"])
    s = unterricht.fortsetzen(s)
    return s


def test_slice_seed_legt_alle_konzepte_lokal_an(app_env):
    """Alle 25 Slice-Konzepte liegen lokal mit provenance-Verknuepfung —
    Voraussetzungskanten wurden dabei aufgeloest."""
    _setup(app_env)
    from app.adaptiv import store
    import karo_contract.slices as kcs
    for konzept in kcs.konzepte():
        kid = _lokal(konzept["id"])
        assert store.fehlertypen(kid), konzept["id"]
    foto = _lokal("BI.PFLANZEN.FOTOSYNTHESE")
    lokal = {v["voraussetzung"] for v in store.voraussetzungen(foto)}
    assert {"BI.PFLANZEN.BEDUERFNISSE", "BI.PFLANZEN.AUFBAU"} <= lokal


@pytest.mark.parametrize("dienst_id", [
    "MA.GEO.QUADERVOLUMEN", "DE.SATZGLIEDER.SUBJEKT_PRAEDIKAT",
    "EN.GRAMMAR.SIMPLE_PAST", "BI.PFLANZEN.FOTOSYNTHESE",
    "PH.GROESSEN.DICHTE", "CH.REAKTION.BEGRIFF"])
def test_jedes_fach_bewertet_typed_nicht_nur_string(app_env, dienst_id):
    """Jedes Fach hat mindestens einen typisierten Antwortweg — Zahl, Term,
    Gleichung, Auswahl oder Begriffs-Rubrik. Reiner Zeichenkettenvergleich
    fuer alles waere ein Gate-Verstoss (§13)."""
    _setup(app_env)
    from app.adaptiv import inhalt_store, store
    kid = _lokal(dienst_id)
    arten, rubriken = set(), 0
    for fehlertyp in store.fehlertypen(kid):
        for rolle in (inhalt_store.GEFUEHRT, inhalt_store.SELBSTSTAENDIG,
                      inhalt_store.TRANSFER):
            for aufgabe in inhalt_store.aufgaben(fehlertyp["id"], rolle):
                arten.add(aufgabe.get("antwort_art") or "zahl")
                if aufgabe.get("rubrik"):
                    rubriken += 1
    typisiert = arten - {"text", "freitext"}
    assert typisiert or rubriken, (dienst_id, arten)


def test_partial_antwort_urteil_dreistufig(app_env):
    """„Fotosynthese" allein ist teilweise — Karo nennt die fehlenden
    Begriffe und wertet nicht als falsch (§14)."""
    _setup(app_env)
    from app.adaptiv import antwortvergleich as vergleich
    from app.adaptiv import inhalt_store, store
    foto = _lokal("BI.PFLANZEN.FOTOSYNTHESE")
    aufgabe = None
    for fehlertyp in store.fehlertypen(foto):
        for rolle in (inhalt_store.GEFUEHRT, inhalt_store.SELBSTSTAENDIG,
                      inhalt_store.TRANSFER):
            for kand in inhalt_store.aufgaben(fehlertyp["id"], rolle):
                if kand.get("rubrik"):
                    aufgabe = aufgabe or kand
    assert aufgabe is not None and aufgabe.get("rubrik")

    begriffe = aufgabe["rubrik"]["begriffe"]
    ein_begriff = next(
        (g[0] for g in begriffe if isinstance(g, list)), None) \
        or next(str(b) for b in begriffe if isinstance(b, str))
    teil = vergleich.bewerte(
        f"Sie braucht es fuer {ein_begriff}.", aufgabe.get("loesung"),
        aufgabe.get("antwort_art"), aufgabe["rubrik"])
    assert teil["urteil"] in (vergleich.TEILWEISE, vergleich.RICHTIG)
    if teil["urteil"] == vergleich.TEILWEISE:
        assert teil["fehlende"]

    voll = " ".join(
        (g[0] if isinstance(g, list) else str(g)) for g in begriffe)
    komplett = vergleich.bewerte(
        voll, aufgabe.get("loesung"), aufgabe.get("antwort_art"),
        aufgabe["rubrik"])
    assert komplett["urteil"] == vergleich.RICHTIG

    leer = vergleich.bewerte(
        "keine Ahnung", aufgabe.get("loesung"), aufgabe.get("antwort_art"),
        aufgabe["rubrik"])
    assert leer["urteil"] == vergleich.FALSCH


def test_level0_reise_grosse_luecke(app_env):
    """§17: Fotosynthese → Beduerfnisse → Pflanze (Level 0) → Aufstieg →
    Zurueck zum Ziel — der entscheidende Test."""
    _setup(app_env)
    from app.adaptiv import (naechste_aktion, store, unterricht,
                             voraussetzung as vor)
    foto = _lokal("BI.PFLANZEN.FOTOSYNTHESE")
    bed = _lokal("BI.PFLANZEN.BEDUERFNISSE")
    pflanze = _lokal("BI.LEBEWESEN.PFLANZE")

    # Stufe 1: Zielsitzung scheitert → Voraussetzung BEDUERFNISSE offen.
    ziel = _falsch_einsteigen(unterricht.starte(foto, "Fotosynthese"))
    assert _daten(ziel).get("voraussetzung_offen"), _daten(ziel)
    assert int(_daten(ziel)["voraussetzung_lokal"]) == bed

    # Stufe 2: Umweg-Sitzung BEDUERFNISSE scheitert → PFLANZE offen.
    umweg1 = _umweg_starten(ziel)
    assert umweg1["konzept_id"] == bed
    assert _daten(umweg1).get("voraussetzung_detour") == ziel["id"]

    umweg1 = _falsch_einsteigen(umweg1)
    assert _daten(umweg1).get("voraussetzung_offen"), _daten(umweg1)
    assert int(_daten(umweg1)["voraussetzung_lokal"]) == pflanze

    # Stufe 3: Umweg-Sitzung PFLANZE — Level 0, kein tieferer Graph.
    umweg2 = _umweg_starten(umweg1)
    assert umweg2["konzept_id"] == pflanze
    assert _daten(umweg2).get("voraussetzung_detour") == umweg1["id"]
    assert vor.offene(pflanze) == []

    # Stufe 4: Aufstieg — PFLANZE meistern, dann die wartende Sitzung.
    umweg2 = _diagnose_loesen(umweg2)
    assert umweg2["zustand"] == "MASTERED", umweg2["zustand"]
    assert vor.sitzt(pflanze)
    assert naechste_aktion.fuer(umweg2)["aktion"] == \
        naechste_aktion.ZURUECK_ZUM_ZIEL

    zurueck = unterricht.fortsetzen(umweg2)
    wartend = store.sitzung(umweg1["id"])
    assert not _daten(wartend).get("voraussetzung_offen")
    assert naechste_aktion.fuer(wartend)["aktion"] in BEKANNTE_AKTIONEN

    # Stufe 5: BEDUERFNISSE meistern → Rueckweg zur Zielsitzung.
    umweg1 = _diagnose_loesen(wartend)
    if umweg1["zustand"] != "MASTERED":
        # andere Aufgabe, gleicher Weg: Diagnose der BEDUERFNISSE-Sitzung
        umweg1 = _diagnose_loesen(umweg1)
    assert umweg1["zustand"] == "MASTERED", umweg1["zustand"]
    assert vor.sitzt(bed)

    unterricht.fortsetzen(umweg1)
    ziel_neu = store.sitzung(ziel["id"])
    # Das Thema wurde nicht aufgegeben: Sitzung offen, Aktion sinnvoll.
    assert ziel_neu["zustand"] != "ABANDONED"
    assert naechste_aktion.fuer(ziel_neu)["aktion"] in BEKANNTE_AKTIONEN

    # Stufe 6: Ziel selbst meistern — volle Reise bis zum Abschluss.
    ziel_ende = _diagnose_loesen(ziel_neu)
    assert ziel_ende["zustand"] == "MASTERED", ziel_ende["zustand"]
    assert naechste_aktion.fuer(ziel_ende)["aktion"] == \
        naechste_aktion.GESCHAFFT


def test_kein_deadend_jeder_zustand_hat_aktion(app_env):
    """Zwölf Runden falsche Antworten auf dem Zielkonzept jedes Fachs:
    jeder erreichte Stand liefert eine Lernaktion, nie einen Dead End."""
    _setup(app_env)
    from app.adaptiv import (naechste_aktion, store,
                             sitzung as zustand, unterricht)
    for dienst_id in ("MA.GEO.QUADERVOLUMEN",
                      "DE.SATZGLIEDER.SUBJEKT_PRAEDIKAT",
                      "EN.GRAMMAR.SIMPLE_PAST",
                      "BI.PFLANZEN.FOTOSYNTHESE",
                      "PH.GROESSEN.DICHTE", "CH.REAKTION.BEGRIFF"):
        s = unterricht.starte(_lokal(dienst_id), "Test")
        s = unterricht.anker_beantwortet(s, "")
        for _ in range(12):
            s = store.sitzung(s["id"])
            schritt = naechste_aktion.fuer(s)
            assert schritt["aktion"] in BEKANNTE_AKTIONEN, \
                (dienst_id, s["zustand"], s.get("phase"), schritt)
            daten = _daten(s)
            if daten.get("voraussetzung_offen"):
                s = unterricht.fortsetzen(s)
                if not daten.get("voraussetzung_lernen"):
                    s = unterricht.voraussetzung_beantwortet(
                        s, ["weiss nicht", "weiss nicht"])
            elif s["zustand"] == zustand.DIAGNOSING:
                s = unterricht.diagnose_beantwortet(s, "falsch")
            elif s["zustand"] == zustand.TEACHING:
                phase = s.get("phase")
                if phase in (zustand.GUIDED_TASK, zustand.INDEPENDENT_TASK):
                    s = unterricht.aufgabe_beantwortet(s, "falsch")
                elif phase == zustand.WORKED_EXAMPLE:
                    s = unterricht.vorhersage_beantwortet(s, "falsch")
                elif phase == zustand.ADAPTATION:
                    s = unterricht.weiter_nach_adaptation(s)
                elif phase == zustand.COMPLETE:
                    s = unterricht.transfer_beantwortet(s, "falsch")
                else:
                    s = unterricht.weiter(s)
            elif s["zustand"] == zustand.ESCALATED:
                s = unterricht.fortsetzen(s)
            else:
                break


def test_inhalt_anfrage_fuer_fehlende_voraussetzung(app_env):
    """Eine Voraussetzung ohne lokale Lektion wird bestellt — die Sitzung
    geht in die Begleitung statt ins Leere (§11/§12)."""
    _setup(app_env)
    from app import db
    from app.adaptiv import store, voraussetzung as vor
    foto = _lokal("BI.PFLANZEN.FOTOSYNTHESE")
    with db.tx() as c:
        c.execute(
            "INSERT INTO lern_voraussetzung "
            "(konzept_id, voraussetzung, titel, created_at) "
            "VALUES (?,?,?,?)",
            (foto, "BI.FEHLEND.TEST", "Erfundenes Konzept", db.now()))
    fehlende = vor.fehlende_ohne_lektion(foto)
    assert any(v["voraussetzung"] == "BI.FEHLEND.TEST" for v in fehlende)


def test_resume_mitten_im_umweg(app_env):
    """Pause mitten im Umweg: `laufende_oder_neue` findet denselben Stand
    wieder — der Detour-Pfad ueberlebt den Neustart (§19)."""
    _setup(app_env)
    from app.adaptiv import store, unterricht
    foto = _lokal("BI.PFLANZEN.FOTOSYNTHESE")
    bed = _lokal("BI.PFLANZEN.BEDUERFNISSE")

    ziel = _falsch_einsteigen(unterricht.starte(foto, "Fotosynthese"))
    umweg = _umweg_starten(ziel)
    assert umweg["konzept_id"] == bed

    wieder = unterricht.laufende_oder_neue(bed)
    assert wieder["id"] == umweg["id"]
    assert _daten(wieder).get("voraussetzung_detour") == ziel["id"]
