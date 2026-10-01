"""Der Weg eines Blatt-Textes in die Wissensbasis — ohne dass ein Bild hinausgeht.

Seit Schritt 1 schickt Karo keine Fotos mehr an ein Modell. Damit füllte sich
die Wissensbasis nicht mehr, und ohne eigenes Material kann Karo nichts
erklären. Diese Datei ist die Brücke: **Text** statt Bild.

Heute tippt oder kopiert ein Mensch den Text beim Hochladen ein. Ab Schritt 2
liest der Browser das Blatt auf dem Gerät und schickt denselben Text an
dieselbe Stelle — `POST /blatt/text`. Deshalb steht die ganze Verarbeitung
hier und nicht im Formular-Handler: es soll genau ein Weg sein, der
inzwischen erprobt ist, wenn das OCR dazukommt. Nicht zwei, von denen einer
erst am Tag der Umstellung zum ersten Mal läuft.

Was hier passiert, in dieser Reihenfolge:

  1. Kopfzeilen weg (Name, Klasse, Datum, Schule stehen fast immer oben)
  2. `pii.scrub()` über den Rest
  3. in Abschnitte zerlegen und nach Art einordnen — mit Regeln, nicht mit
     einem Modell: Abschnitte einzuordnen ist keine Aufgabe, für die sich ein
     Modellaufruf lohnt, und ein falsch einsortierter Abschnitt ist weniger
     schlimm als ein Blatt, das gar nicht ankommt
  4. Thema vorschlagen, ebenfalls aus dem Katalog statt aus einem Modell
  5. Ein Mensch bestätigt — das ist der Schritt, der über die Zuordnung
     entscheidet, nicht die Reihenfolge der Vorschläge
"""
from __future__ import annotations

import re

from . import db, faecher, pii, topics
from .adaptiv.normalisierung import normalisiere_thema

#: Abschnitte länger als das schneidet niemand mehr sinnvoll klein.
MAX_ABSCHNITTE = 60
MAX_ZEICHEN = 6000

#: Wie viele Vorschläge zurückgehen. Drei, weil eine Liste mit zehn Einträgen
#: keine Bestätigung mehr ist, sondern eine Suche.
TOP = 3

#: Zeilen, die oben auf einem Schulblatt stehen und niemanden etwas angehen.
_KOPFZEILE = re.compile(
    r"^\s*(name|vorname|nachname|klasse|kurs|datum|schule|schuljahr|lehrer(in)?|"
    r"fach|note|punkte)\s*[:_.\-]", re.IGNORECASE)

#: Eine Zeile, die nur aus Unterstrichen/Punkten besteht: ein Ausfüllfeld.
_LEERFELD = re.compile(r"^[\s_.\-–—]{3,}$")

_BEISPIEL = re.compile(r"^\s*(beispiel|bsp\.?|zum beispiel|so geht|musterl(ö|oe)sung)\b",
                       re.IGNORECASE)
_AUFGABE = re.compile(r"^\s*(aufgabe|übung|uebung|a\)|b\)|c\)|\d+[.)]\s)", re.IGNORECASE)
_REGEL = re.compile(r"^\s*(regel|merke|wichtig|definition|satz)\b", re.IGNORECASE)
_LOESUNG = re.compile(r"^\s*(l(ö|oe)sung|ergebnis|antwort)\b", re.IGNORECASE)


def kopf_entfernen(text: str, zeilen: int = 8) -> str:
    """Nimmt Namensfeld, Klasse und Datum oben weg.

    Nur aus den ersten `zeilen` Zeilen und nur, was wie eine Kopfzeile
    aussieht: blind die ersten Zeilen abzuschneiden würde bei abgetipptem
    Text die Überschrift und damit das Thema mitnehmen.
    """
    alle = text.splitlines()
    behalten = []
    for i, zeile in enumerate(alle):
        if i < zeilen and (_KOPFZEILE.match(zeile) or _LEERFELD.match(zeile)):
            continue
        behalten.append(zeile)
    return "\n".join(behalten)


def _art(absatz: str) -> str:
    """Was für ein Abschnitt das ist — nach Regeln, nicht nach Modell."""
    if _LOESUNG.match(absatz):
        return "loesung"
    if _BEISPIEL.match(absatz):
        return "beispiel"
    if _REGEL.match(absatz):
        return "regel"
    if _AUFGABE.match(absatz):
        return "aufgabe"
    # Kurz und mit Rechenzeichen: eher eine Aufgabe als eine Erklärung.
    if len(absatz) < 120 and re.search(r"[=+\-*/:×÷]", absatz) and "?" not in absatz:
        return "aufgabe"
    return "erklaerung"


def zerlegen(text: str) -> list[dict]:
    """Text in Abschnitte, an Leerzeilen. Leeres fällt weg."""
    roh = re.split(r"\n\s*\n+", text)
    abschnitte = []
    for stueck in roh:
        sauber = "\n".join(z.rstrip() for z in stueck.splitlines()).strip()
        if len(sauber) < 3:
            continue
        abschnitte.append({"art": _art(sauber), "text": sauber[:MAX_ZEICHEN]})
        if len(abschnitte) >= MAX_ABSCHNITTE:
            break
    return abschnitte


def _woerter(text: str) -> set[str]:
    # Kurze Wörter tragen nichts zur Unterscheidung bei ("der", "und", "3").
    return {w for w in normalisiere_thema(text).split() if len(w) > 3}


def vorschlaege(text: str, fach: str, themenname: str = "") -> list[dict]:
    """Die wahrscheinlichsten Themen zu diesem Text — aus dem eigenen Katalog.

    Kein Modell: ein Wortabgleich gegen die Themen, die es in diesem Fach
    schon gibt. Was er nicht trifft, trägt der Mensch selbst ein — das ist
    derselbe Weg wie bisher und nicht schlechter, nur ehrlicher.
    """
    vorhanden = [dict(r) for r in db.q(
        "SELECT id, label FROM topic WHERE subject=? AND state != ? ORDER BY sort",
        fach, topics.ABGELEHNT)]
    aus_text = _woerter(text[:4000])
    aus_name = _woerter(themenname)
    bewertet = []
    for t in vorhanden:
        thema = _woerter(t["label"])
        if not thema:
            continue
        # Der eingetippte Name wiegt schwerer als der Fließtext: er ist die
        # Angabe eines Menschen, der Text nur das, was zufällig draufsteht.
        punkte = len(thema & aus_text) + 3 * len(thema & aus_name)
        if punkte:
            bewertet.append({**t, "punkte": punkte})
    bewertet.sort(key=lambda t: (-t["punkte"], t["label"]))
    return bewertet[:TOP]


def aufnehmen(text: str, fach: str, *, document_id: int | None = None,
              themenname: str = "", ocr_konfidenz: float | None = None) -> dict:
    """Ein Blatt als Text: säubern, ablegen, Thema vorschlagen.

    Gibt zurück, was die Oberfläche zeigen muss: wie viele Abschnitte
    entstanden sind und welche Themen infrage kommen. Zugeordnet wird erst
    mit `zuordnen()`, nachdem ein Mensch bestätigt hat.
    """
    fach = faecher.pflicht(fach)
    from . import config
    sauber = pii.scrub(kopf_entfernen(text), config.load_safe().learner_name)
    abschnitte = zerlegen(sauber)
    if document_id is not None and abschnitte:
        with db.tx() as c:
            # Ein Blatt wird neu eingelesen: der alte Stand geht, sonst stünde
            # derselbe Text zweimal in der Wissensbasis.
            c.execute("DELETE FROM kb_chunk WHERE document_id=?", (document_id,))
            for i, a in enumerate(abschnitte, start=1):
                c.execute(
                    """INSERT INTO kb_chunk (document_id, position, art, titel, text,
                                             thema_hinweis, created_at)
                       VALUES (?,?,?,NULL,?,?,?)""",
                    (document_id, i, a["art"], a["text"], themenname or None, db.now()))
            hinweis = f"{len(abschnitte)} Abschnitte aus eingefügtem Text"
            if ocr_konfidenz is not None:
                hinweis += f" · Lesesicherheit {round(ocr_konfidenz * 100)} %"
            c.execute("UPDATE document SET state='erschlossen', note=? WHERE id=?",
                      (hinweis, document_id))
    return {"abschnitte": len(abschnitte),
            "arten": sorted({a["art"] for a in abschnitte}),
            "vorschlaege": vorschlaege(sauber, fach, themenname)}


def zuordnen(document_id: int, topic_id: int) -> int:
    """Die Abschnitte dieses Blatts gehören zu diesem Thema.

    Erst hier entsteht die Verbindung — nach der Bestätigung eines Menschen.
    """
    with db.tx() as c:
        cur = c.execute("UPDATE kb_chunk SET topic_id=? WHERE document_id=?",
                        (topic_id, document_id))
        return cur.rowcount


# --------------------------------------------------------------------------
# Rückfall: lesen auf dem Server
# --------------------------------------------------------------------------
#
# Der Normalfall ist das Lesen im Browser — dann bleibt das Blatt auf dem
# Gerät. Ein alter Browser ohne WASM kann das nicht. Statt diese Familien
# auszuschließen, liest Karo dann hier: auf **ihrem eigenen** Server, im
# Container auf ihrem Rechner. Das Bild wird sofort danach gelöscht.
#
# Das ist ein anderer Handel als vorher und ein ehrlicher: vorher ging das
# Foto an einen fremden Dienst und blieb dort. Hier bleibt es im Haushalt und
# überlebt die Anfrage nicht. Gesagt wird es trotzdem vorher.

TESSERACT = "tesseract"


def server_lesen_moeglich() -> bool:
    import shutil
    return shutil.which(TESSERACT) is not None


def _bild_lesen(pfad, sprachen: str = "deu+eng") -> str:
    import subprocess
    try:
        fertig = subprocess.run(
            [TESSERACT, str(pfad), "stdout", "-l", sprachen],
            capture_output=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return fertig.stdout.decode("utf-8", "replace") if fertig.returncode == 0 else ""


def server_lesen(pfad, *, seiten_grenze: int = 20) -> str:
    """Liest eine Datei auf dem Server. Der Aufrufer löscht sie danach.

    Bild: Tesseract. PDF: erst die Textebene (schneller und fehlerfrei), für
    Seiten ohne Textebene die gerenderte Seite durch Tesseract — dieselbe
    Entscheidung wie im Browser, damit beide Wege dasselbe liefern.
    """
    from pathlib import Path

    from . import ingest

    pfad = Path(pfad)
    if pfad.suffix.lower() != ".pdf":
        return _bild_lesen(pfad)

    doc = ingest._open_pdf(pfad)
    try:
        teile = []
        for i in range(min(doc.page_count, seiten_grenze)):
            text = doc.text(i)
            if len(text) >= 40:
                teile.append(text)
                continue
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
                doc.seite(i).save(tmp.name)
                teile.append(_bild_lesen(tmp.name))
        return "\n\n".join(t for t in teile if t.strip())
    finally:
        doc.close()
