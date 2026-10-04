"""Thema zu Lektion: Wortverwandtschaft ist keine Konzeptverwandtschaft.

`trifft_thema` traf früher jede Teilzeichenkette in beide Richtungen:
„zinsen" steckt in „zinsen auf zinsen", „100" in „1000", „masse" im Label
der Dichte-Lektion. Der Katalog-Audit zeigte, was das anrichtet: „Zinsen"
bekam die Zinseszins-Lektion, „Dichte — Masse pro Volumen" traf die
Lektionen zu Masse, Volumen und „Pro", „Was Pflanzen brauchen" traf
„Pflanzen sind Lebewesen". Das Kind bekam ein anderes Konzept, nur weil
die Wörter verwandt klingen.

Die Regeln jetzt:

1. Gleich gewusst trifft — identischer Text nach Normalisierung.
2. Das Label deckt die Frage, wenn sein Kopfwort genannt wird:
   „Dichte" findet „Dichte — Masse pro Volumen", „Masse" nicht.
3. Ein Stichwort steht vollständig in der Frage — ab zwei bedeutenden
   Wörtern, damit „masse" allein keine Dichte-Anfrage bedient.

Stammgleichheit erlaubt Flexion („ungleichnamige" ↔ „ungleichnamig"),
aber keine Wortfamilien („zinsen" ≠ „zinseszins", „pro" ≠ „prozent",
„100" ≠ „1000") und keine Vorsilben-Gegenteile („gleichnamig" ≠
„ungleichnamig").
"""
from karo_contract.huelle import trifft_thema
from karo_contract.normalisierung import normalisiere_thema

#: Label und Stichworte wie im Katalog — je ein Tupel pro Lektion.
UNGLEICHNAMIG = ("Brüche addieren – ungleichnamig",
                 "ungleichnamig", "brueche addieren")
ZINSESZINS = ("Zinseszins über mehrere Jahre berechnen",
              "zinsen auf zinsen", "zinseszins")
DICHTE = ("Dichte — Masse pro Volumen", "dichte")
MASSE = ("Masse — wie schwer etwas ist", "masse")
VOLUMEN = ("Volumen — der Platz eines Körpers", "volumen")
PRO_EINHEIT = ("„Pro“ — pro Einheit vergleichen", "pro einheit")


def _trifft(thema: str, konzept: tuple) -> bool:
    label, *stichworte = konzept
    return trifft_thema(normalisiere_thema(thema),
                        {"label": label, "stichworte": stichworte})


# ---------------------------------------------------------------------------
# Was treffen muss: dieselbe Lektion unter anderen Worten
# ---------------------------------------------------------------------------

def test_das_label_traegt_die_anfrage():
    assert _trifft("Dichte", DICHTE)
    assert _trifft("Masse", MASSE)
    assert _trifft("Prisma", ("Prisma Volumen", "prisma"))
    assert _trifft("Rechnen bis 100",
                   ("Rechnen bis 100", "rechnen bis 100"))


def test_die_frage_darf_kuerzer_sein_als_das_label():
    """Das Kopfwort wird genannt — der Rest des Labels erklärt es nur."""
    assert _trifft("Zinseszins", ZINSESZINS)
    assert _trifft("Brüche addieren", UNGLEICHNAMIG)


def test_flexion_und_wortstellung_bleiben_gleich():
    assert _trifft("ungleichnamige Brüche", UNGLEICHNAMIG)
    assert _trifft("Ungleichnamige Brüche addieren", UNGLEICHNAMIG)
    assert _trifft("Würfel: Volumen",
                   ("Volumen eines Würfels", "wuerfel volumen"))


def test_ein_stichwort_steht_vollstaendig_in_der_frage():
    assert _trifft("Brüche addieren und subtrahieren", UNGLEICHNAMIG)


# ---------------------------------------------------------------------------
# Was nicht treffen darf: die Kollisionen aus dem Katalog-Audit
# ---------------------------------------------------------------------------

def test_zinsen_ist_nicht_zinseszins():
    """Der teuerste Treffer: „zinsen" steckt in „zinsen auf zinsen"."""
    assert not _trifft("Zinsen", ZINSESZINS)
    assert not _trifft("Zinsen", ("Einfache Zinsen", "zinsen auf zinsen"))
    assert not _trifft("Prozentrechnung", ZINSESZINS)


def test_einzelne_stichworte_tragen_keine_laengere_frage():
    """„masse" ist ein Stichwort der Masse-Lektion — nicht der Dichte-Frage."""
    assert not _trifft("Dichte — Masse pro Volumen", MASSE)
    assert not _trifft("Dichte — Masse pro Volumen", VOLUMEN)
    assert not _trifft("Dichte — Masse pro Volumen", PRO_EINHEIT)


def test_nicht_kopfwort_findet_das_label_nicht():
    """„Masse" steht im Dichte-Label, heisst aber anderswo."""
    assert not _trifft("Masse", DICHTE)
    assert not _trifft("Volumen", DICHTE)


def test_zahlen_sind_exakt():
    assert not _trifft("Rechnen bis 100",
                       ("Rechnen bis 1000", "rechnen bis 1000"))
    assert not _trifft("Rechnen bis 1000",
                       ("Rechnen bis 100", "rechnen bis 100"))


def test_wortfamilien_sind_keine_stammgleichheit():
    assert not _trifft("Prozent", PRO_EINHEIT)
    assert not _trifft("Prozentrechnung", PRO_EINHEIT)


def test_vorsilben_sind_ein_anderes_konzept():
    """„gleichnamig" ist nicht „ungleichnamig" — die Vorsilbe dreht den
    Unterschied um, mit dem beide Lektionen getrennt werden."""
    assert not _trifft("Gleichnamige Brüche addieren", UNGLEICHNAMIG)
    gleichnamig = ("Brüche addieren – gleichnamig",
                   "gleichnamig", "brueche addieren")
    assert not _trifft("Ungleichnamige Brüche addieren", gleichnamig)


#: Die echten Stichworte des Slice-Katalogs: „gleichnamig machen" ist ein
#: Verfahrenswort der Ungleichnamig-Lektion, kein Konzeptname.
UNGLEICHNAMIG_SLICE = ("Ungleichnamige Brüche addieren",
                       "ungleichnamige brüche", "brüche addieren",
                       "hauptnenner", "gleichnamig machen")


def test_verfahrenswort_entschuldigt_kein_gegenteil():
    """Das Stichwort „gleichnamig machen" deckt „gleichnamige" nur ab,
    wenn es selbst trifft — sonst wäre die Anfrage eine andere Lektion."""
    assert not _trifft("Gleichnamige Brüche addieren", UNGLEICHNAMIG_SLICE)
    # …aber die Verfahrensanfrage findet ihr Stichwort weiterhin:
    assert _trifft("Brüche gleichnamig machen", UNGLEICHNAMIG_SLICE)


def test_anfrage_ist_kein_teil_eines_stichworts():
    """„Negative Zahlen" steckt im Stichwort „negative zahlen malnehmen" —
    das Anwendungsthema bedient aber keine Grundlagenanfrage."""
    assert not _trifft("Negative Zahlen",
                       ("Rationale Zahlen malnehmen", "rationale zahlen",
                        "minus mal minus", "negative zahlen malnehmen"))


def test_voraussetzungen_sind_nicht_das_thema():
    """Der Audit-Fund: Voraussetzungs-Lektionen lösten das Thema aus."""
    assert not _trifft("Was Pflanzen brauchen",
                       ("Pflanzen sind Lebewesen", "pflanzen lebewesen"))
    assert not _trifft("Aufbau der Pflanze",
                       ("Pflanzen sind Lebewesen", "pflanzen lebewesen"))
    assert not _trifft("Alle Satzglieder bestimmen",
                       ("Subjekt und Prädikat", "subjekt praedikat"))
    assert not _trifft("Alle Satzglieder bestimmen",
                       ("Der Satz als Sinneinheit", "satz sinneinheit"))
    assert not _trifft("Halbschriftlich malnehmen",
                       ("Kleines Einmaleins", "einmaleins"))
    assert not _trifft("Negative Zahlen",
                       ("Rationale Zahlen malnehmen", "zahlen malnehmen"))
    assert not _trifft("Dezimalzahlen teilen",
                       ("Dezimalzahlen ordnen", "dezimalzahlen ordnen"))


def test_fremde_bruchthemen_bleiben_ohnm_lektion():
    """Gegenprobe zum verfassten Bestand — deckt sich mit
    `test_lektionen_zuordnung`."""
    for thema in ("Brüche kürzen", "Brüche vergleichen",
                  "Brüche multiplizieren", "Zähler und Nenner",
                  "Photosynthese"):
        assert not _trifft(thema, UNGLEICHNAMIG), thema


# ---------------------------------------------------------------------------
# Rangfolge: die genau benannte Lektion schlägt den Stichwort-Nebentreffer
# ---------------------------------------------------------------------------

def test_die_genaueste_lektion_gewinnt(client, fake_llm, app_env):
    """Zwei Lektionen teilen das Stichwort „brueche addieren". Die Anfrage
    „Gleichnamige Brüche addieren" trifft beide — aber nur eine heisst so."""
    from .test_app import einrichten
    from app.adaptiv import lektionen, store
    einrichten(client, fake_llm)
    lektionen.saee_alle()
    gleichnamig_id = store.konzept_sichern(
        "mathematik", "brueche", "gleichnamig-addieren",
        "Gleichnamige Brüche addieren", 5, 6,
        stichworte=("brueche addieren", "gleichnamig"), geprueft=True)

    treffer = lektionen.fuer_thema("Gleichnamige Brüche addieren",
                                   "mathematik")

    assert treffer is not None
    assert treffer["konzept_id"] == gleichnamig_id

    # Die genau benannte Lektion schlägt den Stichwort-Nebentreffer:
    # „brueche addieren" passt auch zu gleichnamig-addieren — aber das
    # eigene Label trifft exakt.
    treffer = lektionen.fuer_thema(
        "Brüche mit verschiedenen Nennern addieren", "mathematik")
    assert treffer is not None
    assert treffer["konzept_key"] == "ungleichnamig-addieren"
