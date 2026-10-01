"""Die Huelle einer Lieferung: alles ausser der Lektion selbst.

Fach, Format, Inhaltsversion, Klasseneinordnung und die Frage, ob die
Lektion ueberhaupt zum angefragten Thema gehoert. Darueber haben sich Karo
und der Lehrplan-Dienst geeinigt — deshalb steht es hier und nicht in
Karos `app/`, wo der Dienst es nicht lesen koennte.
"""
from __future__ import annotations

from . import schemas
from .faecher import schluessel
from .normalisierung import normalisiere_thema

#: Das Format, das Karo bestellt. Aendert sich daran etwas Gueltiges,
#: bekommt es einen neuen Namen — eine stille Aenderung waere eine Falle.
FORMAT_ID = "karo-adaptiv-v1"


class VertragVerletzt(schemas.InhaltUngueltig):
    """Nicht die Lektion ist falsch, sondern die Huelle der Antwort.

    Dagegen hilft kein neu geschriebener Text: das muss ein Mensch an der
    Schnittstelle richten. Deshalb wird es getrennt gemeldet und zaehlt beim
    Dienst nicht gegen das Thema.
    """


def trifft_thema(gesucht: str, konzept: dict) -> bool:
    """Gehoert das Konzept zum gesuchten Thema?

    Stichworte benennen das **Konzept**, nicht das Thema: „brueche" traefe
    jedes Bruchthema und damit auch „Brueche kuerzen" — eine andere
    Fehlvorstellung als das Addieren.
    """
    for wort in konzept.get("stichworte") or ():
        muster = normalisiere_thema(wort)
        if muster and (muster in gesucht or gesucht in muster):
            return True
    return gesucht in normalisiere_thema(konzept.get("label") or "")


def pruefe_huelle(antwort: dict, fach: str | None) -> None:
    """Fach, Format und Inhaltsversion. Wirft `VertragVerletzt`."""
    geliefert = antwort.get("subject")
    if fach and geliefert is not None and schluessel(geliefert) != schluessel(fach):
        # Eine Antwort aus einem anderen Fach wird nicht importiert, auch
        # wenn das Thema zufaellig passt.
        raise VertragVerletzt("Die Lernreihe gehört zu einem anderen Fach.")
    if (antwort.get("format") != FORMAT_ID or not antwort.get("concept_id")
            or not antwort.get("concept_version")):
        raise VertragVerletzt("Format oder Inhaltsversion fehlt.")


def voraussetzungen(antwort: dict) -> list[dict]:
    """Die Voraussetzungen aus der Lieferung — geprueft, nie geraten.

    Der Dienst fuehrt Voraussetzungsketten seit jeher; der Abnehmer konnte
    sie nicht sehen. Ohne sie bleibt bei einem Kind, das haengt, nur die
    Eskalation — auch wenn in Wahrheit nur eine Voraussetzung fehlt.

    Fehlt das Feld, ist die Antwort aelter als Vertrag 1.4. Das ist kein
    Fehler: dann gibt es eben keine Voraussetzungen, und Karo verhaelt sich
    wie vorher.
    """
    roh = antwort.get("prerequisites")
    if not isinstance(roh, list):
        return []
    sauber = []
    for eintrag in roh[:20]:
        if not isinstance(eintrag, dict):
            continue
        kid = str(eintrag.get("concept_id") or "").strip()[:120]
        if not kid:
            continue
        sauber.append({"concept_id": kid,
                       "title": str(eintrag.get("title") or "").strip()[:200]})
    return sauber


def pruefe_einordnung(antwort: dict) -> tuple[int, int]:
    """Die Klasseneinordnung der Huelle. Gibt (von, bis) zurueck.

    Fehlt das Feld, ist der Dienst zu alt — das ist kein Inhaltsfehler.
    Genau hier lag die Sackgasse: Karo meldete es als Inhaltsmangel, und
    nach zwei Meldungen gab der Dienst das Thema nicht mehr heraus.
    """
    einordnung = antwort.get("classification") or {}
    lo, hi = einordnung.get("first_contact_grade"), einordnung.get("target_grade")
    if (type(lo) is not int or type(hi) is not int or not 1 <= lo <= hi <= 13
            or einordnung.get("source") != "approved_curriculum"):
        raise VertragVerletzt("Die Klasseneinordnung fehlt oder kommt nicht "
                              "aus dem geprüften Curriculum.")
    return lo, hi


def pruefe_konzeptklasse(konzept: dict, lo: int, hi: int) -> None:
    """Huelle in Ordnung, aber die Lektion widerspricht ihr: Inhaltsfehler."""
    if (konzept.get("klasse_von"), konzept.get("klasse_bis")) != (lo, hi):
        raise schemas.InhaltUngueltig("Die Klasseneinordnung stimmt nicht mit "
                                      "dem geprüften Curriculum überein.")
