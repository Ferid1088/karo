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

#: Anzeige auf der Lernstand-Seite in Karo — eigene, ausfuehrlichere Worte
#: fuer dieselben vier Flaggen. Die Flaggen selbst (Werte, Regel, Reihenfolge)
#: bleiben ueberall sonst in der App unveraendert; das hier ist nur Text.
STATUS_EMOJI = {
    Flag.GRUEN.value: "🟢",
    Flag.GELB.value: "🟡",
    Flag.ROT.value: "🔴",
    Flag.WEISS.value: "⚪",
}
STATUS_LABEL = {
    Flag.GRUEN.value: "sicher (mehrfach unabhängig richtig gemacht)",
    Flag.GELB.value: "relativ sicher",
    Flag.ROT.value: "unsicher",
    Flag.WEISS.value: "noch nicht genug Beweise",
}
NAECHSTER_SCHRITT = {
    Flag.GRUEN.value: "kurz wiederholen",
    Flag.GELB.value: "weiter üben",
    Flag.ROT.value: "erklären lassen",
    Flag.WEISS.value: "prüfen",
}


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


def lernstand_zeilen() -> list[dict]:
    """Der Lernstand als Zeilen — Grundlage sowohl fuer die Ansicht in Karo
    selbst als auch fuer den Tabellenexport, damit beide nie auseinanderlaufen.
    """
    zeilen = [t for t in topics.liste(topics.AKTIV)]
    zeilen.sort(key=lambda t: (FLAG_ORDER.index(t["flag"])
                               if t["flag"] in FLAG_ORDER else 9, t["sort"]))

    geuebt = {r["topic_id"]: r["summe"] for r in db.q(
        "SELECT topic_id, SUM(runden) AS summe FROM lesson GROUP BY topic_id")}

    for t in zeilen:
        t["flag_label"] = FLAG_LABELS.get(t["flag"], t["flag"])
        t["bedeutung"] = _bedeutung(t["flag"])
        t["haupt_fehler_label"] = ERROR_LABELS.get(t.get("haupt_fehler") or "", "")
        t["geuebte_runden"] = geuebt.get(t["id"]) or 0
        t["status_emoji"] = STATUS_EMOJI.get(t["flag"], "")
        t["status_label"] = STATUS_LABEL.get(t["flag"], t["flag"])
        t["naechster_schritt"] = NAECHSTER_SCHRITT.get(t["flag"], "")
        # Dieselben Farben wie auf der Themenseite: gruen = richtig,
        # orange = Verstaendnisfehler, rot = anderer Fehler.
        t["verlauf"] = quizzes.verlauf(t["id"])
    return zeilen


def verlauf_zeilen(limit: int = 200) -> list[dict]:
    """Die juengsten Eintraege im Antwortverlauf, fuers Verlaufs-Blatt und
    die Ansicht in Karo."""
    zeilen = []
    for r in db.q(
        """SELECT a.beantwortet_am, t.label, a.richtig, a.fehlertyp, a.quelle
             FROM answer_log a JOIN topic t ON t.id = a.topic_id
            ORDER BY a.id DESC LIMIT ?""", limit):
        zeilen.append({
            "datum": r["beantwortet_am"],
            "label": r["label"],
            "richtig": bool(r["richtig"]),
            "fehlertyp_label": ERROR_LABELS.get(r["fehlertyp"] or "", ""),
            "quelle": "Mensch" if r["quelle"] == "lernbegleitung" else "Modell",
        })
    return zeilen


def schreiben() -> str | None:
    """Schreibt die Tabelle als .xlsx in den Drive-Ordner — der optionale
    Weg zum Google Sheet. None, wenn openpyxl fehlt oder Drive nicht da ist.
    Die Werte selbst leben unabhaengig davon in Karos Datenbank (siehe
    `lernstand_zeilen()`) und lassen sich dort jederzeit ansehen.
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
    except ImportError:                                  # pragma: no cover
        log.info("openpyxl fehlt — kein Tabellenexport")
        return None

    cfg = config.load_safe()
    zeilen = lernstand_zeilen()

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
    for r in verlauf_zeilen(limit=2000):
        vs.append([r["datum"], r["label"], "ja" if r["richtig"] else "nein",
                   r["fehlertyp_label"], r["quelle"]])
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
