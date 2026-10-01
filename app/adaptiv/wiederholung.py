"""Wiederholung mit Abstand (Z4, Schritt 4a).

Nach `MASTERED` passierte bisher nichts mehr: kein Termin, keine
Auffrischung, keine Vergessenskurve. Die Flagge blieb gruen, bis zufaellig
wieder geuebt wurde.

Drei Entscheidungen stecken hier drin:

* **Das Kind waehlt den Tag.** Zwei bis fuenf Tage, es entscheidet. Wer den
  Termin mitbestimmt, haelt ihn eher ein als einen, der ihm gestellt wurde.
* **Verpasstes verfaellt nicht.** Eine Wiederholung bleibt offen stehen, bis
  sie gemacht ist — sie rutscht nicht lautlos aus dem Plan.
* **Kein Minus.** Nicht bestanden heisst: kurze Auffrischung, neuer Termin.
  Niemand verliert etwas, das er schon konnte.
"""

from __future__ import annotations

import datetime as dt
import json

from .. import db
from .store import CHILD_KEY, _json, _zeile

#: Zur Auswahl stehende Abstaende in Tagen.
ABSTAENDE = (2, 3, 4, 5)

OFFEN = "offen"
BESTANDEN = "bestanden"
NICHT_BESTANDEN = "nicht_bestanden"


def _heute() -> dt.date:
    from ..woche import plaene
    return plaene.today()


def vorschlag(konzept_id: int | None = None, heute: dt.date | None = None) -> int:
    """Welcher Abstand vorgeschlagen wird — in der Regel die Mitte.

    Steht eine Klassenarbeit an, faellt der Vorschlag auf den Tag davor,
    solange der in der Auswahl liegt. Am Tag der Arbeit selbst zu wiederholen
    waere zu spaet, und eine Woche vorher zu frueh.
    """
    tag = heute or _heute()
    zeile = db.q1(
        """SELECT exam_date FROM exam
            WHERE deleted_at IS NULL AND purged_at IS NULL
              AND exam_date >= ? ORDER BY exam_date LIMIT 1""", str(tag))
    if zeile:
        try:
            arbeit = dt.date.fromisoformat(zeile["exam_date"])
        except (TypeError, ValueError):
            arbeit = None
        if arbeit:
            davor = (arbeit - dt.timedelta(days=1) - tag).days
            if davor in ABSTAENDE:
                return davor
    return 3


def auswahl(konzept_id: int | None = None, heute: dt.date | None = None) -> list[dict]:
    """Die vier Moeglichkeiten, wie das Kind sie sieht."""
    from ..services.today import date_label
    tag = heute or _heute()
    empfohlen = vorschlag(konzept_id, tag)
    return [{"tage": n, "datum": str(ziel := tag + dt.timedelta(days=n)),
             "datum_label": date_label(ziel),
             "empfohlen": n == empfohlen} for n in ABSTAENDE]


def planen(konzept_id: int, tage: int, *, sitzung_id: int | None = None,
           heute: dt.date | None = None, child_key: str = CHILD_KEY) -> dict:
    """Einen Termin setzen. Ein offener Termin je Konzept reicht."""
    if int(tage) not in ABSTAENDE:
        raise ValueError(f"{tage} Tage stehen nicht zur Auswahl.")
    tag = heute or _heute()
    faellig = str(tag + dt.timedelta(days=int(tage)))
    jetzt = db.now()
    with db.tx() as c:
        offen = c.execute(
            "SELECT id FROM lern_wiederholung WHERE child_key=? AND konzept_id=?"
            " AND status=? ORDER BY id DESC LIMIT 1",
            (child_key, konzept_id, OFFEN)).fetchone()
        if offen:
            c.execute("UPDATE lern_wiederholung SET faellig_am=?, gewaehlt_am=?,"
                      " sitzung_id=COALESCE(?, sitzung_id), updated_at=? WHERE id=?",
                      (faellig, str(tag), sitzung_id, jetzt, offen["id"]))
            neu = offen["id"]
        else:
            neu = c.execute(
                """INSERT INTO lern_wiederholung (child_key, konzept_id, sitzung_id,
                       faellig_am, gewaehlt_am, status, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (child_key, konzept_id, sitzung_id, faellig, str(tag), OFFEN,
                 jetzt, jetzt)).lastrowid
    return eintrag(neu)


def eintrag(wiederholung_id: int) -> dict | None:
    zeile = _zeile(db.q1("SELECT * FROM lern_wiederholung WHERE id=?",
                         wiederholung_id))
    if zeile:
        zeile["ergebnis"] = _json(zeile.get("ergebnis"), {})
    return zeile


def offene(child_key: str = CHILD_KEY, bis: dt.date | str | None = None) -> list[dict]:
    """Faellige Wiederholungen, aelteste zuerst.

    Verpasste stehen weiter drin: `faellig_am <= heute` schliesst gestern mit
    ein. Was man vergessen hat, verschwindet nicht dadurch, dass der Tag
    vorbei ist.
    """
    grenze = str(bis or _heute())
    zeilen = db.q(
        """SELECT w.*, k.label AS konzept_label, k.fach AS fach
             FROM lern_wiederholung w JOIN lern_konzept k ON k.id = w.konzept_id
            WHERE w.child_key=? AND w.status=? AND w.faellig_am <= ?
            ORDER BY w.faellig_am, w.id""", child_key, OFFEN, grenze)
    ergebnis = []
    for zeile in zeilen:
        eintr = _zeile(zeile)
        eintr["ergebnis"] = _json(eintr.get("ergebnis"), {})
        eintr["verpasst"] = eintr["faellig_am"] < grenze
        ergebnis.append(eintr)
    return ergebnis


def offen_fuer(konzept_id: int, child_key: str = CHILD_KEY) -> dict | None:
    zeile = db.q1(
        "SELECT id FROM lern_wiederholung WHERE child_key=? AND konzept_id=?"
        " AND status=? ORDER BY id DESC LIMIT 1", child_key, konzept_id, OFFEN)
    return eintrag(zeile["id"]) if zeile else None


def abschliessen(wiederholung_id: int, *, bestanden_: bool,
                 ergebnis_daten: dict | None = None) -> dict:
    """Bestanden oder nicht — beides ist ein Ergebnis, keines ist ein Urteil."""
    eintr = eintrag(wiederholung_id)
    daten = dict((eintr or {}).get("ergebnis") or {})
    daten.update(ergebnis_daten or {})     # die gestellten Aufgaben bleiben
    jetzt = db.now()
    with db.tx() as c:
        c.execute(
            "UPDATE lern_wiederholung SET status=?, ergebnis=?, erledigt_am=?,"
            " updated_at=? WHERE id=?",
            (BESTANDEN if bestanden_ else NICHT_BESTANDEN,
             json.dumps(daten, ensure_ascii=False),
             jetzt, jetzt, wiederholung_id))
    return eintrag(wiederholung_id)


def gefestigt(konzept_id: int, child_key: str = CHILD_KEY) -> bool:
    """Hat das Kind dieses Konzept nach Abstand noch einmal gekonnt?

    Erst dann zaehlt es fuer „Thema sicher". Einmal verstanden ist der
    Anfang, nicht das Ende — das ist der ganze Grund fuer die Wiederholung.
    """
    return bool(db.q1(
        "SELECT 1 AS da FROM lern_wiederholung WHERE child_key=? AND konzept_id=?"
        " AND status=? LIMIT 1", child_key, konzept_id, BESTANDEN))


def check_beginnen(wiederholung_id: int) -> dict | None:
    """Die Aufgaben des Checks einmal festlegen — dann bleiben sie stehen.

    Neuladen darf dem Kind nicht andere Aufgaben zeigen als die, die es
    gerade beantwortet: die Auswahl liegt in `ergebnis`, nicht im Zufall.
    """
    eintr = eintrag(wiederholung_id)
    if eintr is None or eintr["status"] != OFFEN:
        return eintr
    if not eintr["ergebnis"].get("aufgaben"):
        daten = dict(eintr["ergebnis"])
        daten["aufgaben"] = pruefaufgaben(eintr["konzept_id"],
                                          child_key=eintr["child_key"])
        with db.tx() as c:
            c.execute("UPDATE lern_wiederholung SET ergebnis=?, updated_at=?"
                      " WHERE id=?",
                      (json.dumps(daten, ensure_ascii=False), db.now(),
                       wiederholung_id))
        eintr = eintrag(wiederholung_id)
    return eintr


def check_aufgaben(wiederholung_id: int) -> list[dict]:
    eintr = check_beginnen(wiederholung_id)
    return (eintr or {}).get("ergebnis", {}).get("aufgaben", [])


def fuer_tag(tag: dt.date | None = None,
             child_key: str = CHILD_KEY) -> list[dict]:
    """Was heute auf den Plan des Kindes gehoert: Faelliges zuerst, dann was
    heute schon geschafft wurde — die Liste loescht nichts, sie haekt ab.

    Verpasste bleiben dabei einfach stehen (`offene` liest `faellig_am <=
    heute`): was nicht gemacht wurde, verschwindet nicht lautlos.
    """
    from ..services.today import local_day
    heute = tag or _heute()
    eintraege = [{**e, "erledigt": False} for e in offene(child_key, heute)]
    for zeile in db.q(
            """SELECT w.*, k.label AS konzept_label, k.fach AS fach
                 FROM lern_wiederholung w JOIN lern_konzept k
                   ON k.id = w.konzept_id
                WHERE w.child_key=? AND w.status=? ORDER BY w.erledigt_am""",
            child_key, BESTANDEN):
        eintr = _zeile(zeile)
        if local_day(eintr["erledigt_am"]) == heute:
            eintr["ergebnis"] = _json(eintr.get("ergebnis"), {})
            eintr["erledigt"] = True
            eintraege.append(eintr)
    return eintraege


# --------------------------------------------------------------------------
# Der kurze Check: neue Aufgaben, nicht dieselben
# --------------------------------------------------------------------------

def anzahl_aufgaben(cfg=None) -> int:
    from .. import config
    return min(5, max(3, int(getattr(cfg or config.load_safe(),
                                     "adaptiv_wiederholung_aufgaben", 4))))


def pruefaufgaben(konzept_id: int, *, child_key: str = CHILD_KEY, cfg=None,
                  zufall=None) -> list[dict]:
    """Drei bis fuenf **neue** Aufgaben auf Zielniveau.

    Zuerst geprueft und noch nie gestellt — das ist das Beste, was es gibt.
    Reicht das nicht, rechnet der Generator Varianten aus (Mathematik), und
    erst wenn auch das nichts hergibt, kommt eine bekannte Aufgabe wieder.
    Lieber eine bekannte Aufgabe als gar keine Wiederholung; eine erfundene
    mit falscher Loesung waere schlimmer als beides.
    """
    from . import inhalt_store, protokoll, store, varianten
    gewuenscht = anzahl_aufgaben(cfg)
    gesehen = protokoll.gesehene_aufgaben(konzept_id, child_key)
    auf_zielniveau = [a for fehlertyp in store.fehlertypen(konzept_id)
                      for a in inhalt_store.aufgaben(fehlertyp["id"])
                      if a["rolle"] in (inhalt_store.SELBSTSTAENDIG,
                                        inhalt_store.GEFUEHRT)]
    neue = [a for a in auf_zielniveau if a["id"] not in gesehen]
    gewaehlt = neue[:gewuenscht]

    if len(gewaehlt) < gewuenscht and auf_zielniveau:
        for vorlage in auf_zielniveau:
            if len(gewaehlt) >= gewuenscht:
                break
            gewaehlt += varianten.varianten(
                vorlage, gewuenscht - len(gewaehlt), zufall=zufall)

    if len(gewaehlt) < gewuenscht:
        fehlend = [a for a in auf_zielniveau if a not in gewaehlt]
        gewaehlt += fehlend[:gewuenscht - len(gewaehlt)]
    return gewaehlt[:gewuenscht]


def auswerten(aufgaben: list[dict], antworten: list[str]) -> dict:
    """Bestanden ist, wer alle neuen Aufgaben richtig hat.

    Derselbe Massstab wie bei der Ersteinschaetzung und der Voraussetzung:
    eine Luecke ist eine Luecke, auch wenn drei andere sassen.
    """
    from .unterricht import ist_richtig
    gegeben = list(antworten) + [""] * len(aufgaben)
    einzeln = [{"frage": a.get("frage"), "antwort": gegeben[i],
                "richtig": bool(ist_richtig(gegeben[i], a.get("loesung", "")))}
               for i, a in enumerate(aufgaben)]
    return {"aufgaben": einzeln,
            "richtig": sum(1 for e in einzeln if e["richtig"]),
            "gesamt": len(einzeln),
            "bestanden": bool(einzeln) and all(e["richtig"] for e in einzeln)}


def auffrischung(konzept_id: int, *, child_key: str = CHILD_KEY,
                 cfg=None) -> dict:
    """Kurz auffrischen, nachdem eine Wiederholung nicht gesessen hat.

    Eine **andere** Erklaerung als beim letzten Mal und eine gefuehrte
    Aufgabe. Nicht die ganze Einheit noch einmal: das Kind hat das Thema
    schon verstanden, es ist ihm nur entfallen.
    """
    from . import inhalt_store, store
    letzte = db.q1(
        """SELECT fehlertyp_id, erklaerung_id FROM lern_sitzung
            WHERE child_key=? AND konzept_id=? AND fehlertyp_id IS NOT NULL
            ORDER BY id DESC LIMIT 1""", child_key, konzept_id) or {}
    fehlertyp_id = letzte["fehlertyp_id"] if letzte else None
    if fehlertyp_id is None:
        fehlertypen = store.fehlertypen(konzept_id)
        fehlertyp_id = fehlertypen[0]["id"] if fehlertypen else None
    if fehlertyp_id is None:
        return {"erklaerung": None, "aufgabe": None}

    vorhandene = store.erklaerungen(fehlertyp_id)
    vorher = letzte.get("erklaerung_id") if letzte else None
    andere = [e for e in vorhandene if e["id"] != vorher]
    aufgabe = (inhalt_store.aufgabe(fehlertyp_id, inhalt_store.GEFUEHRT)
               or inhalt_store.aufgabe(fehlertyp_id, inhalt_store.SELBSTSTAENDIG))
    return {"erklaerung": (andere or vorhandene or [None])[0],
            "aufgabe": aufgabe, "fehlertyp_id": fehlertyp_id}
