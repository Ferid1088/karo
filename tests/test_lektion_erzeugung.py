"""Schritt 1 der Erzeugung: Vertrag und Prüfung, noch ohne Auslöser.

Ein Modell darf eine ganze Lektion vorschlagen — aber nichts davon erreicht
ein Kind, bevor es geprüft ist. Diese Datei prüft den Vertrag selbst:

A1  kein Markup, keine Komponente außerhalb des Registers
A2  Unvollständiges wird abgewiesen, nicht halb gespeichert
§4  das Inhaltsformat gilt für erzeugte Erklärungen wie für verfasste

Der teuerste Fehler wäre eine Lektion, die vollständig *aussieht*: fehlt
eine der fünf Aufgabenrollen, läuft das Kind bis Phase vier und steht dann
vor einem leeren Schirm (`unterricht.bildschirm()` liest `(aufgabe or {})`
und stürzt gerade nicht ab). Deshalb ist Vollständigkeit hier ein
Schemafehler.
"""
import copy

import pytest

BILD = {"component": "GenericStepFlow",
        "parameters": {"schritte": ["Kante messen", "Mal sich selbst"]},
        "animation": "none"}

ERKLAERUNG = {
    "haken": "Du hast gesagt, das Volumen sei 12.",
    "erkenntnis": "Bei einem Würfel zählt nicht der Umfang, sondern wie viele "
                  "Einheitswürfel hineinpassen.",
    "regel": "Nimm die Kantenlänge dreimal mit sich selbst mal.",
    "bild": {"zeigt": "Ein Würfel aus kleinen Würfeln.",
             "bewegt": "Eine Schicht nach der anderen füllt sich.",
             "bleibt_gleich": "Die Kantenlänge bleibt in jeder Schicht dieselbe."},
    "aufgabe": {"frage": "Kante 3 cm — wie viele Würfelchen?", "loesung": "27"},
}


def _lektion() -> dict:
    return copy.deepcopy({
        "konzept": {
            "konzept_key": "wuerfel-volumen", "thema_key": "geometrie",
            "label": "Volumen eines Würfels",
            "klasse_von": 5, "klasse_bis": 7,
            "stichworte": ["wuerfel volumen", "volumen wuerfel"],
        },
        "erstkontakt": {
            "anker": "Wie viele Zuckerwürfel passen in eine Schachtel?",
            "erste_aufgabe": {"frage": "Kante 2 — wie viele?", "loesung": "8"},
            "benennung": "Das nennt man das Volumen.",
        },
        "hilfe": {
            phase: {"text": f"Andere Worte für {phase}: stell dir die Kiste "
                            "vor, die du Schicht für Schicht füllst.",
                    "visualisierung": BILD}
            for phase in ("HOOK", "RULE", "WORKED_EXAMPLE", "GUIDED_TASK",
                          "INDEPENDENT_TASK", "ADAPTATION")
        },
        "faq": [
            {"frage": "Was ist eine Kante?",
             "antwort": "Eine Kante ist eine der Linien, an denen zwei "
                        "Flächen des Würfels zusammenstoßen."},
            {"frage": "Wie tippe ich meine Antwort?",
             "antwort": "Schreib nur die Zahl, ohne Einheit."},
        ],
        "fehlertypen": [{
            "key": "kanten-addiert",
            "label": "Kantenlängen addiert statt multipliziert",
            "beschreibung": "3 cm Kante wird zu 3+3+3 = 9 statt 27.",
            "antworten": ["9", "3+3+3"],
            "erklaerung": ERKLAERUNG,
            "visualisierung": BILD,
            "visualisierung_alternativ": {
                "component": "AreaModel",
                "parameters": {"zeilen": 3, "spalten": 3, "markiert": 9},
                "animation": "none"},
            "aufgaben": {
                "vorhersage": {"frage": "Wird es mehr oder weniger als 12?",
                               "loesung": "mehr",
                               "optionen": ["mehr", "weniger"],
                               "aufloesung": "Mehr — es sind 27."},
                "beispiel": {"frage": "Kante 2 cm", "loesung": "8",
                             "schritte": ["2 mal 2 ist 4", "4 mal 2 ist 8"]},
                "gefuehrt": {"frage": "Kante 4 cm", "loesung": "64",
                             "tipps": ["Wie viele in einer Schicht?"],
                             "typischer_fehler": "12"},
                "selbststaendig": {"frage": "Kante 5 cm", "loesung": "125",
                                   "tipps": ["Erst die Schicht."],
                                   "typischer_fehler": "15"},
                "transfer": {"frage": "Gilt das auch für einen Quader?",
                             "loesung": "ja",
                             "optionen": ["ja", "nein"],
                             "aufloesung": "Ja, nur mit drei Kantenlängen."},
            },
        }],
    })


def test_eine_vollstaendige_lektion_wird_angenommen(app_env):
    from app.adaptiv import schemas

    sauber = schemas.pruefe_lektion(_lektion())

    assert sauber["konzept"]["konzept_key"] == "wuerfel-volumen"
    assert sauber["fehlertypen"][0]["aufgaben"]["gefuehrt"]["loesung"] == "64"
    assert sauber["fehlertypen"][0]["visualisierung"]["component"] == \
        "GenericStepFlow"


@pytest.mark.parametrize("rolle", ["vorhersage", "beispiel", "gefuehrt",
                                   "selbststaendig", "transfer"])
def test_eine_fehlende_aufgabenrolle_ist_ein_schemafehler(app_env, rolle):
    """Sonst läuft das Kind bis Phase vier und steht vor einem leeren Schirm."""
    from app.adaptiv import schemas
    daten = _lektion()
    del daten["fehlertypen"][0]["aufgaben"][rolle]

    with pytest.raises(schemas.InhaltUngueltig, match=rolle):
        schemas.pruefe_lektion(daten)


def test_markup_irgendwo_wird_abgewiesen(app_env):
    """A1: ein Modell liefert Text und Auswahl, niemals Darstellung."""
    from app.adaptiv import schemas
    daten = _lektion()
    daten["fehlertypen"][0]["erklaerung"]["regel"] = "<b>Mal dich selbst</b>"

    with pytest.raises(schemas.InhaltUngueltig):
        schemas.pruefe_lektion(daten)


def test_komponente_ausserhalb_des_registers_wird_abgewiesen(app_env):
    """A1: keine erfundene Komponente, auch nicht mit hübschen Parametern."""
    from app.adaptiv import schemas
    daten = _lektion()
    daten["fehlertypen"][0]["visualisierung"] = {
        "component": "CubeRenderer3D", "parameters": {}, "animation": "spin"}

    with pytest.raises(schemas.InhaltUngueltig):
        schemas.pruefe_lektion(daten)


def test_ein_typischer_fehler_darf_nicht_die_loesung_sein(app_env):
    """`typischer_fehler` ist das, woran Tier 1 die Fehlvorstellung
    wiedererkennt. Gleich der Lösung wäre er nicht nur nutzlos, sondern
    würde eine richtige Antwort als Fehler einordnen."""
    from app.adaptiv import schemas
    daten = _lektion()
    daten["fehlertypen"][0]["aufgaben"]["gefuehrt"]["typischer_fehler"] = "64"

    with pytest.raises(schemas.InhaltUngueltig, match="typischer_fehler"):
        schemas.pruefe_lektion(daten)


def test_ohne_erkennbare_falsche_antwort_ist_der_fehlertyp_wertlos(app_env):
    """Ohne `antworten` trifft Tier 1 nie — die Lektion wäre ein Katalog-
    eintrag, der bei keinem Kind je anschlägt."""
    from app.adaptiv import schemas
    daten = _lektion()
    daten["fehlertypen"][0]["antworten"] = []

    with pytest.raises(schemas.InhaltUngueltig, match="antworten"):
        schemas.pruefe_lektion(daten)


def test_zwei_gleiche_fehlerschluessel_werden_abgewiesen(app_env):
    from app.adaptiv import schemas
    daten = _lektion()
    daten["fehlertypen"].append(copy.deepcopy(daten["fehlertypen"][0]))

    with pytest.raises(schemas.InhaltUngueltig, match="kanten-addiert"):
        schemas.pruefe_lektion(daten)


# --------------------------------------------------------------------------
# Der Auftrag an Modell A
# --------------------------------------------------------------------------

def test_der_auftrag_nennt_thema_aber_keine_profilklasse(app_env):
    from app import prompts

    text = prompts.lektion_prompt(grade=6, subject="Mathematik",
                                  thema="Würfel: Volumen")

    assert "Würfel: Volumen" in text
    assert "Kind der Klasse 6" not in text
    assert "bestimmt NICHT die Einordnung" in text
    assert text == prompts.lektion_prompt(grade=1, subject='Mathematik', thema='Würfel: Volumen')


def test_der_auftrag_zeigt_nur_metadaten_der_komponenten(app_env):
    """§3: Das auswählende Modell sieht Bezeichnung, Zweck und Parameter —
    niemals, wie gezeichnet wird. Sonst versucht es, es selbst zu tun."""
    from app import prompts
    from app.adaptiv import komponenten

    text = prompts.lektion_prompt(grade=6, subject="Mathematik",
                                  thema="Würfel: Volumen")

    for k in komponenten.alle():
        assert k.id in text, k.id
        assert k.renderer not in text, f"{k.id} verrät seinen Renderer"
    assert "<" not in text.replace("<=", "")       # kein Markup im Auftrag


def test_der_auftrag_verlangt_alle_aufgabenrollen(app_env):
    from app import prompts
    from app.adaptiv import schemas

    text = prompts.lektion_prompt(grade=6, subject="Mathematik", thema="X")

    for rolle in schemas.AUFGABEN_ROLLEN:
        assert rolle in text, rolle


def test_das_schema_verlangt_dieselben_rollen_wie_die_pruefung(app_env):
    """Auftrag und Prüfung dürfen nicht auseinanderlaufen — sonst erzeugt
    das Modell brav etwas, das die Prüfung anschließend verwirft."""
    from app import prompts
    from app.adaptiv import schemas

    aufgaben = (prompts.LEKTION_SCHEMA["properties"]["fehlertypen"]["items"]
                ["properties"]["aufgaben"])

    assert tuple(aufgaben["required"]) == schemas.AUFGABEN_ROLLEN


def test_das_schema_verlangt_dieselben_hilfephasen_wie_die_pruefung(app_env):
    """Sonst erzeugt das Modell eine Lektion ohne Hilfe, und die Prüfung
    verwirft sie — teuer und vermeidbar."""
    from app import prompts
    from app.adaptiv import schemas

    hilfe = prompts.LEKTION_SCHEMA["properties"]["hilfe"]

    assert tuple(hilfe["required"]) == schemas.HILFE_PHASEN
    assert set(hilfe["properties"]) == set(schemas.HILFE_PHASEN)


def test_der_auftrag_verlangt_hilfe_und_richtiges_rechnen(app_env):
    from app import prompts

    text = prompts.lektion_prompt(grade=6, subject="Mathematik", thema="X")

    assert "Das habe ich nicht verstanden" in text
    assert "faq" in text
    assert "nachgerechnet" in text
