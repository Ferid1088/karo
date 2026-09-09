"""Export des Lernstands als Tabelle in den Drive-Ordner.

Der Wunsch war ein Google Sheet mit farbigen Flaggen je Thema. Karo schreibt
dafür eine .xlsx-Datei in den Drive-Ordner — Google synchronisiert sie, und
in Drive lässt sie sich mit einem Klick als Google Sheet öffnen und
bearbeiten.

Der Umweg über die Datei statt über die Google-API ist Absicht: er spart einen
vollständigen OAuth-Teil samt Google-Verifizierung, funktioniert offline und
ist an einen Freund weitergebbar, ohne dass der ein Google-Cloud-Projekt
anlegen muss.
"""

from __future__ import annotations

import logging

from . import config, db, ingest, quizzes, topics
from .domain import ERROR_LABELS, FLAG_LABELS, FLAG_ORDER, Flag

log = logging.getLogger("karo.export")

#: Füllfarben der Flaggen — bewusst kräftig, damit man sie auf dem Handy sieht.
FARBEN = {
    Flag.GRUEN.value: "C6E7D2",
    Flag.GELB.value: "FBEED6",
    Flag.ROT.value: "FBE4E1",
    Flag.WEISS.value: "F0F2F7",
}
SCHRIFT = {
    Flag.GRUEN.value: "1A5C38",
    Flag.GELB.value: "7A4C05",
    Flag.ROT.value: "8F241A",
    Flag.WEISS.value: "6F7889",
}

DATEINAME = "Lernstand.xlsx"


def _bedeutung(flag: str) -> str:
    """Was die Flagge fuer die Lernbegleitung heisst — in einem Satz."""
    return {
        Flag.GRUEN.value: "sitzt — nur noch kurz wiederholen",
        Flag.GELB.value: "wackelig — weiter üben",
        Flag.ROT.value: "Verständnislücke — erklären lassen",
        Flag.WEISS.value: "noch nicht geprüft",
    }.get(flag, "")


def verfuegbar() -> bool:
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        return False
    return True


def schreiben() -> str | None:
    """Schreibt die Tabelle. None, wenn openpyxl fehlt oder Drive nicht da ist."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
    except ImportError:                                  # pragma: no cover
        log.info("openpyxl fehlt — kein Tabellenexport")
        return None

    cfg = config.load_safe()
    zeilen = [t for t in topics.liste(topics.AKTIV)]
    zeilen.sort(key=lambda t: (FLAG_ORDER.index(t["flag"])
                               if t["flag"] in FLAG_ORDER else 9, t["sort"]))

    wb = Workbook()

    # --- Blatt 1: Lernstand ---------------------------------------------
    ws = wb.active
    ws.title = "Lernstand"
    kopf = ["Thema", "Flagge", "Bedeutung", "richtig", "Antworten",
            "häufigster Fehler", "zuletzt geübt", "Begründung", "Code"]
    ws.append(kopf)
    for zelle in ws[1]:
        zelle.font = Font(bold=True, size=10)
        zelle.fill = PatternFill("solid", fgColor="E8EBF2")
        zelle.alignment = Alignment(vertical="center")

    for t in zeilen:
        ws.append([
            t["label"],
            FLAG_LABELS.get(t["flag"], t["flag"]),
            _bedeutung(t["flag"]),
            t["richtig"],
            t["antworten"],
            ERROR_LABELS.get(t.get("haupt_fehler") or "", ""),
            t.get("letzte_uebung") or "",
            t.get("begruendung") or "",
            t["code"],
        ])
        zeile = ws[ws.max_row]
        farbe = FARBEN.get(t["flag"], FARBEN[Flag.WEISS.value])
        for zelle in zeile[:3]:
            zelle.fill = PatternFill("solid", fgColor=farbe)
        zeile[1].font = Font(bold=True,
                             color=SCHRIFT.get(t["flag"], "000000"))

    for i, breite in enumerate([44, 14, 30, 9, 11, 24, 15, 52, 22], start=1):
        ws.column_dimensions[get_column_letter(i)].width = breite
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:I{max(ws.max_row, 1)}"

    # --- Blatt 2: Verlauf -----------------------------------------------
    vs = wb.create_sheet("Verlauf")
    vs.append(["Datum", "Thema", "richtig", "Fehlertyp", "bewertet von"])
    for zelle in vs[1]:
        zelle.font = Font(bold=True, size=10)
        zelle.fill = PatternFill("solid", fgColor="E8EBF2")
    for r in db.q(
        """SELECT a.beantwortet_am, t.label, a.richtig, a.fehlertyp, a.quelle
             FROM answer_log a JOIN topic t ON t.id = a.topic_id
            ORDER BY a.id DESC LIMIT 2000"""):
        vs.append([r["beantwortet_am"], r["label"],
                   "ja" if r["richtig"] else "nein",
                   ERROR_LABELS.get(r["fehlertyp"] or "", ""),
                   "Mensch" if r["quelle"] == "lernbegleitung" else "Modell"])
    for i, breite in enumerate([12, 44, 9, 24, 14], start=1):
        vs.column_dimensions[get_column_letter(i)].width = breite
    vs.freeze_panes = "A2"

    # --- Blatt 3: Hinweise ----------------------------------------------
    hs = wb.create_sheet("Hinweise")
    einig = quizzes.uebereinstimmung()
    quote = (f"{round(einig['quote'] * 100)} % bei den letzten "
             f"{einig['gesamt']} Antworten") if einig["quote"] is not None \
        else "noch keine Daten"
    for text in [
        [f"Lernstand {cfg.subject}, Klassenstufe {cfg.learner_grade}"],
        [f"Erzeugt von Karo am {db.today()}"],
        [],
        ["Diese Datei wird bei jeder Freigabe neu geschrieben."],
        ["Änderungen darin gehen beim nächsten Export verloren — die Wahrheit"],
        ["steht in Karo, nicht in dieser Tabelle."],
        [],
        ["Wie die Flaggen entstehen:"],
        ["  Lücke (rot)      2× derselbe Verständnisfehler in den letzten 5 Antworten"],
        ["  wackelig (gelb)  gemischtes Bild — der Normalzustand beim Lernen"],
        ["  sitzt (grün)     die letzten 2 Übungstage fehlerfrei, mind. 3× richtig"],
        ["  noch nicht geprüft (weiß)  weniger als 2 verwertbare Antworten"],
        [],
        ["Ein Rechenfehler oder eine Flüchtigkeit löst nie eine Lücke aus —"],
        ["das sind keine Wissensprobleme."],
        [],
        [f"Übereinstimmung Modell / Lernbegleitung: {quote}"],
        ["Je niedriger dieser Wert, desto vorsichtiger sind die Flaggen zu lesen."],
    ]:
        hs.append(text)
    hs.column_dimensions["A"].width = 96

    ziel = config.media_dir() / DATEINAME
    wb.save(ziel)
    return ingest.commit_material(ziel, unterordner=None) or str(ziel)


def nach_freigabe() -> str | None:
    """Wird nach jeder Freigabe aufgerufen. Ein Fehler hier darf nichts stoppen."""
    try:
        return schreiben()
    except Exception as exc:                             # pragma: no cover
        log.warning("Tabellenexport fehlgeschlagen: %s", exc)
        return None
