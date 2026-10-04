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


#: Woerter, die in fast jedem deutschen Themennamen stehen. Sie stiften
#: keine Verwandtschaft: „Volumen bei VERSCHIEDENEN Maßeinheiten" und
#: „Bruecke mit VERSCHIEDENEN Nennern addieren" haben nichts miteinander
#: zu tun.
FUELLWOERTER = frozenset({
    "und", "oder", "mit", "bei", "von", "der", "die", "das", "den", "dem",
    "ein", "eine", "einen", "einem", "im", "in", "zu", "zum", "zur", "auf",
    "fuer", "aus", "als", "am", "ist", "sind", "was", "wie",
    "verschiedenen", "verschiedene", "verschiedener",
    "eines", "einer", "ganzen", "ganze",
})


def bedeutungswoerter(text: str | None) -> list[str]:
    """Die Woerter eines Themennamens, die etwas bedeuten — in Reihenfolge."""
    return [w for w in normalisiere_thema(text).split()
            if len(w) > 2 and w not in FUELLWOERTER]


def _gleicher_stamm(a: str, b: str) -> bool:
    """Flexion ja, Wortfamilie nein.

    „ungleichnamige" und „ungleichnamig" sind dasselbe Wort. „zinsen" und
    „zinseszins" nicht, „pro" und „prozent" nicht — und Zahlen nie:
    „100" und „1000" sind zwei verschiedene Zahlenraeume.
    """
    if a == b:
        return True
    if any(z.isdigit() for z in a + b):
        return False
    kurz, lang = (a, b) if len(a) <= len(b) else (b, a)
    return len(lang) - len(kurz) <= 3 and lang.startswith(kurz)


def _deckt(kleine: list[str], grosse: list[str]) -> bool:
    """Jedes bedeutende Wort von `kleine` hat einen Stamm-Treffer in `grosse`."""
    return all(any(_gleicher_stamm(w, g) for g in grosse) for w in kleine)


def _gegenteil(a: str, b: str) -> bool:
    """Ein Wort mit Vorsilbe ist ein anderes Konzept.

    „ungleichnamig" enthaelt „gleichnamig" mit einer Vorsilbe — die Lektion
    zum einen darf die Anfrage nach dem anderen nicht beantworten, denn
    genau dieser Unterschied trennt die Konzepte.
    """
    if _gleicher_stamm(a, b) or len(a) < 4 or len(b) < 4:
        return False
    lang, kurz = (a, b) if len(a) >= len(b) else (b, a)
    for m in range(max(4, len(kurz) - 3), min(len(kurz) + 4, len(lang) - 1)):
        if _gleicher_stamm(lang[len(lang) - m:], kurz):
            return True
    return False


def treffergrad(gesucht: str, konzept: dict) -> int:
    """Wie genau gehoert das Konzept zum gesuchten Thema? 0 = gar nicht.

    Drei Wege fuehren zum Treffer, keiner davon ist eine blosse
    Teilzeichenkette:

    1. Gleich gewusst (Grad 3): identischer Text nach Normalisierung.
    2. Das Label deckt die Frage und die Frage nennt sein Kopfwort
       (Grad 2) — „Dichte" findet „Dichte — Masse pro Volumen", „Masse"
       findet sie nicht, obwohl das Wort im Label steht.
    3. Ein Stichwort steht vollstaendig in der Frage (Grad 1) — die
       kuerzere Seite braucht mindestens zwei bedeutende Woerter, damit
       „brueche addieren" in „Brueche addieren und subtrahieren" trifft,
       ein einzelnes Stichwort wie „masse" aber keine laengere Anfrage
       bedient. Als einziges Wort ist ein Stichwort nur das Kopfwort der
       Frage, und der Rest der Frage muss ebenfalls zum Konzept passen.

    Ein Suchwort, das mit Vorsilbe in einem Konzeptwort steckt, verweigert
    den Treffer: „gleichnamige" ist nicht „ungleichnamig". Ausgenommen, was
    Label oder das treffende Stichwort selbst deckt — „Brueche gleichnamig
    machen" findet das Stichwort „gleichnamig machen" trotzdem.
    """
    label = normalisiere_thema(konzept.get("label") or "")
    stichworte = [normalisiere_thema(w)
                  for w in konzept.get("stichworte") or ()]
    gesucht_w = bedeutungswoerter(gesucht)
    label_w = bedeutungswoerter(label)
    konzept_w = list(label_w)
    muster_ws = []
    for muster in stichworte:
        muster_w = bedeutungswoerter(muster)
        muster_ws.append((muster, muster_w))
        konzept_w += [w for w in muster_w if w not in konzept_w]

    def sauber(entschuldigt: list) -> bool:
        """Kein unentschuldigtes Suchwort ist ein Vorsilben-Gegenteil."""
        return not any(
            not any(_gleicher_stamm(s, e) for e in entschuldigt)
            and any(_gegenteil(s, k) for k in konzept_w)
            for s in gesucht_w)

    if gesucht == label or gesucht in stichworte:
        return 3
    if (gesucht_w and label_w and _deckt(gesucht_w, label_w)
            and any(_gleicher_stamm(label_w[0], w) for w in gesucht_w)
            and sauber(label_w)):
        return 2
    for muster, muster_w in muster_ws:
        if not muster_w:
            continue
        if len(muster.split()) == 1:
            if (gesucht_w and _gleicher_stamm(muster_w[0], gesucht_w[0])
                    and _deckt(gesucht_w[1:], konzept_w)
                    and sauber(muster_w)):
                return 1
            continue
        # „zinsen auf zinsen" bleibt ein einziges bedeutendes Wort —
        # Wiederholung zaehlt nicht doppelt.
        if (len(set(muster_w)) >= 2 and _deckt(muster_w, gesucht_w)
                and sauber(muster_w)):
            return 1
    return 0


def trifft_thema(gesucht: str, konzept: dict) -> bool:
    """Gehoert das Konzept zum gesuchten Thema?

    Stichworte benennen das **Konzept**, nicht das Thema: „brueche" traefe
    jedes Bruchthema und damit auch „Brueche kuerzen" — eine andere
    Fehlvorstellung als das Addieren.
    """
    return treffergrad(gesucht, konzept) > 0


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
