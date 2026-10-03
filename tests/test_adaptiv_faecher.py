"""Sechs Fächer, ein Lernweg: der Kompetenzgraph ist nicht an Mathe gebunden.

Jedes Fach bekommt hier eine dreistufige Kette — Ziel, Vorstufe,
Vorstufe der Vorstufe — mit der Antwortart, die das Fach braucht:
Zahlen in Physik, Auswahl in Englisch, Text in Deutsch und Biologie.
Die Reise ist in jedem Fach dieselbe: scheitern → Voraussetzung prüfen →
um eine Stufe tiefer lernen → wieder scheitern → noch eine Stufe tiefer →
meistern → zurück → meistern → zurück → Ziel schaffen.
"""
import json

import pytest

# Je Fach: Ziel-, Zwischen- und Basiskonzept plus die Antwortart der
# Aufgaben. Fachlich wie Karo sie im Katalog führen würde.
FAECHER = {
    "mathematik": {
        "kette": [("MA.LIN_GLEICHUNG", "Lineare Gleichungen"),
                  ("MA.NEGATIVE_ZAHLEN", "Negative Zahlen"),
                  ("MA.ZAHLEN_STRICHLISTE", "Zählen und abziehen")],
        "antwort_art": "zahl", "falsch": "99", "loesungen": ["2", "3"],
    },
    "deutsch": {
        "kette": [("DE.SATZGLIEDER", "Satzglieder bestimmen"),
                  ("DE.KASUS", "Kasus erkennen"),
                  ("DE.WORTART", "Wortarten unterscheiden")],
        "antwort_art": "text", "falsch": "keine Ahnung",
        "loesungen": ["dativ", "akkusativ"],
    },
    "englisch": {
        "kette": [("EN.PRESENT_PERFECT", "Present perfect"),
                  ("EN.SIMPLE_PAST", "Simple past"),
                  ("EN.VERB_SATZ", "Verb im Satz erkennen")],
        "antwort_art": "auswahl", "falsch": "x",
        "loesungen": ["went", "has gone"],
    },
    "biologie": {
        "kette": [("BIO.FOTOSYNTHESE", "Fotosynthese"),
                  ("BIO.ZELLE", "Die Zelle"),
                  ("BIO.LEBEWESEN", "Lebewesen erkennen")],
        "antwort_art": "text", "falsch": "erde",
        "loesungen": ["lichtenergie", "chlorophyll"],
    },
    "physik": {
        "kette": [("PHYS.DICHTE", "Dichte berechnen"),
                  ("PHYS.VOLUMEN", "Volumen messen"),
                  ("PHYS.EINHEITEN", "Einheiten verstehen")],
        "antwort_art": "zahl", "falsch": "42", "loesungen": ["100", "50"],
    },
    "chemie": {
        "kette": [("CHE.REAKTION", "Chemische Reaktionen"),
                  ("CHE.ATOMBAU", "Aufbau der Atome"),
                  ("CHE.STOFF_TEILCHEN", "Stoffe und Teilchen")],
        "antwort_art": "auswahl", "falsch": "weg",
        "loesungen": ["teilchen", "reaktionsgleichung"],
    },
}


def _konzept(key: str, titel: str, fach: str, antwort_art: str,
             loesungen: list[str]):
    """Ein geprueftes Konzept dieses Fachs mit Diagnoseaufgaben seiner
    Antwortart — so, wie der Import sie aus der Lieferung anlegt."""
    from app import db
    from app.adaptiv import inhalt_store, store
    kid = store.konzept_sichern(fach, "reise", key, titel, geprueft=True)
    ft = store.fehlertyp_sichern(kid, f"{key}-fehler", f"{titel} falsch",
                                 geprueft=True)
    for pos, loesung in enumerate(loesungen):
        inhalt_store.aufgabe_sichern(
            ft, inhalt_store.SELBSTSTAENDIG, f"{titel} — Aufgabe {pos + 1}",
            loesung, schwierigkeit=pos + 1, position=pos,
            antwort_art=antwort_art)
    with db.tx() as c:
        c.execute("""INSERT OR IGNORE INTO lern_curriculum_import
                       (fingerprint, konzept_id, provenance, created_at)
                     VALUES (?,?,?,?)""",
                  (f"fp-{key}", kid, json.dumps({"concept_id": key}),
                   db.now()))
    return kid


def _haengen(sitzung_id: int):
    from app.adaptiv import sitzung as zustand, store
    for _ in range(4):
        zustand.runde_gescheitert(sitzung_id, "falsch")
    return store.sitzung(sitzung_id)


def _meistern(sitzung_id: int):
    from app.adaptiv import sitzung as zustand, store
    s = store.sitzung(sitzung_id)
    ft = store.fehlertypen(s["konzept_id"])[0]["id"]
    if s["zustand"] == zustand.DIAGNOSING:
        zustand.fehler_erkannt(sitzung_id, ft, "falsch")
        zustand.unterricht_beginnen(sitzung_id)
    for _ in range(zustand.mastery_treffer()):
        s = zustand.antwort_richtig(sitzung_id, "richtig")
    assert s["zustand"] == zustand.MASTERED
    return s


@pytest.mark.parametrize("fach", sorted(FAECHER))
def test_vertikale_reise_durch_drei_ebenen(app_env, fach):
    """Profil C: das Ziel ist zu schwer, die Vorstufe auch — Karo geht bis
    zur Basis, meistert dort und baut Stufe für Stufe wieder auf."""
    from app.adaptiv import sitzung as zustand, store, unterricht
    app_env.db.init()
    store.init()

    profil = FAECHER[fach]
    (ziel_key, ziel_titel), (mitte_key, mitte_titel), (basis_key, basis_titel) = \
        profil["kette"]
    ziel = _konzept(ziel_key, ziel_titel, fach, profil["antwort_art"],
                    profil["loesungen"])
    mitte = _konzept(mitte_key, mitte_titel, fach, profil["antwort_art"],
                     profil["loesungen"])
    basis = _konzept(basis_key, basis_titel, fach, profil["antwort_art"],
                     profil["loesungen"])
    store.voraussetzungen_sichern(ziel, [{"concept_id": mitte_key,
                                          "title": mitte_titel}])
    store.voraussetzungen_sichern(mitte, [{"concept_id": basis_key,
                                           "title": basis_titel}])

    # Überfordert am Ziel → Vorstufe fehlt → Umweg auf die Mitte.
    sz = unterricht.starte(ziel, ziel_titel)
    sz = _haengen(sz["id"])
    assert dict(sz["daten"] or {})["voraussetzung_lokal"] == mitte
    sz = unterricht.voraussetzung_beantwortet(sz, [profil["falsch"]] * 2)
    sm = unterricht.voraussetzung_lernen_starten(sz)
    assert sm["konzept_id"] == mitte

    # Auch die Mitte ist zu schwer → eine Stufe tiefer zur Basis.
    sm = _haengen(sm["id"])
    assert dict(sm["daten"] or {})["voraussetzung_lokal"] == basis
    sm = unterricht.voraussetzung_beantwortet(sm, [profil["falsch"]] * 2)
    sb = unterricht.voraussetzung_lernen_starten(sm)
    assert sb["konzept_id"] == basis

    # Basis meistern → zurück zur Mitte → meistern → zurück zum Ziel.
    sb = _meistern(sb["id"])
    assert unterricht.bildschirm(sb)["art"] == "voraussetzung_geschafft"
    sm2 = unterricht.voraussetzung_weiter_zum_thema(sb)
    assert sm2["id"] == sm["id"]

    sm2 = _meistern(sm2["id"])
    sz2 = unterricht.voraussetzung_weiter_zum_thema(sm2)
    assert sz2["id"] == sz["id"]

    # Am Ziel geht es weiter, wo es hakte — und diesmal klappt es.
    sz2 = _meistern(sz2["id"])
    stand = store.fortschritt(ziel, sz2["fehlertyp_id"])
    assert stand["mastery"] == "sicher"


@pytest.mark.parametrize("fach,art,paare", [
    ("mathematik", "bruch", [("1/2", "2/4"), ("0,5", "1/2")]),
    ("mathematik", "term", [("2x+6", "2(x+3)"), ("x - 4", "-4+x")]),
    ("mathematik", "gleichung", [("x = 5", "5 = x")]),
    ("physik", "zahl", [("100", "100,0"), ("3:2", "1,5")]),
    ("deutsch", "text", [("Dativ", "dativ")]),
    ("englisch", "auswahl", [("Went", "went")]),
    ("biologie", "text", [("Lichtenergie", "lichtenergie")]),
    ("chemie", "auswahl", [("Teilchen", "teilchen")]),
])
def test_antwortvergleich_fachuebergreifend(app_env, fach, art, paare):
    """Die Bewertung folgt der deklarierten Antwortart, nicht dem String:
    Wertgleichheit in den Rechnungsarten, normalisierter Text im Rest."""
    app_env.db.init()
    from app.adaptiv.antwortvergleich import check_answer
    for gegeben, erwartet in paare:
        assert check_answer(gegeben, erwartet, art), \
            f"{fach}/{art}: {gegeben!r} sollte {erwartet!r} entsprechen"
    # Und eine falsche Antwort bleibt falsch — egal welches Fach.
    assert not check_answer("etwas anderes", paare[0][1], art)
