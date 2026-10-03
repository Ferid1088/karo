"""Themenblatt einer Klassenarbeit — eigener Upload-Weg unter /klassenarbeit.

Der Lernbereich liest sein Material unter /lernen/material
(`routers/lernmaterial.py`); dieser Router gehoert zur Klassenarbeit:
Seiten des Ankuendigungs- oder Themenblatts einlesen, die erkannten
Pruefungsinhalte pruefen und ins Formular der neuen Arbeit uebernehmen.

Geteilt wird nur die Technik: Paket-Ablage, Seitenbilder, Limits und der
Analyse-Job laufen ueber `material_paket`. Die Domain ist getrennt — hier
wird nie `learning_hub` gerufen und kein Lernthema angelegt; bestaetigte
Inhalte werden erst beim Anlegen der Arbeit zu Pruefungsthemen
(`exam.create_exam`). Dieser Router redirectet nie nach /lernen.
"""

from __future__ import annotations

import datetime as dt
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from .. import config, db, faecher, material_paket
from .shared import (antwort, dateien_lesen, flash, render,
                     seiten_aus_formular, vorab_groesse, zurueck)

router = APIRouter()

BASIS = "/klassenarbeit/themenblatt"


# ---------------------------------------------------------------------------
# Formularzustand der Klassenarbeit, der den Upload-Umweg ueberlebt
# ---------------------------------------------------------------------------

def _entwurf(request: Request, formular=None) -> dict:
    """Termin/Fach/Themen, die im Formular der neuen Arbeit schon standen.

    Kommen als Query-Parameter oder Formularfelder mit — so bleiben die
    eingetragenen Werte erhalten, waehrend das Themenblatt gelesen wird.
    """
    quelle = formular if formular is not None else request.query_params
    out: dict[str, str] = {}
    termin = str(quelle.get("termin") or "").strip()[:10]
    try:
        dt.date.fromisoformat(termin)
    except ValueError:
        termin = ""
    if termin:
        out["termin"] = termin
    fach = faecher.schluessel(quelle.get("fach"))
    if fach:
        out["fach"] = fach
    themen = str(quelle.get("themen") or "").strip()[:2000]
    if themen:
        out["themen"] = themen
    return out


def _neu_url(paket_id: int | None = None, entwurf: dict | None = None) -> str:
    params = dict(entwurf or {})
    if paket_id:
        params["material"] = str(paket_id)
    return "/klassenarbeit/neu" + (f"?{urlencode(params)}" if params else "")


def _detail_url(paket_id: int, entwurf: dict | None = None) -> str:
    return (f"{BASIS}/{paket_id}"
            + (f"?{urlencode(entwurf)}" if entwurf else ""))


def _themenblatt_paket(paket_id: int) -> dict | None:
    """Nur Pakete dieser Domain: ein Lernpaket ist hier ein Irrtum und wird
    nicht bedient — und der Weg fuehrt nie hinaus nach /lernen."""
    try:
        paket = material_paket.holen(paket_id)
    except material_paket.PaketFehler:
        return None
    return paket if paket["zweck"] == "klassenarbeit" else None


def _weg(request: Request, paket_id: int):
    """Einheitliche Abweisung: Paket nicht da oder fremde Domain."""
    paket = _themenblatt_paket(paket_id)
    if paket is not None:
        return paket
    roh = db.q1("SELECT zweck FROM material_paket WHERE id=?", paket_id)
    flash(request,
          "Dieses Material gehört zum Lernbereich — nicht hierher."
          if roh else "Dieses Material gibt es nicht (mehr).", "warn")
    return None


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@router.get(BASIS, response_class=HTMLResponse)
def themenblatt_seite(request: Request):
    """Das Themenblatt: Seiten sammeln, ordnen, einlesen lassen."""
    entwurf = _entwurf(request)
    fach = entwurf.get("fach", "")
    upload_url = f"{BASIS}/paket"
    if entwurf:
        upload_url += f"?{urlencode(entwurf)}"
    return render(
        request, "themenblatt_upload.html",
        adult_page=not config.load_safe().klassenarbeit_kind,
        entwurf=entwurf,
        zurueck_url=_neu_url(entwurf=entwurf),
        fach=fach,
        upload_url=upload_url,
        max_seiten=material_paket.MAX_SEITEN,
        min_zeichen=material_paket.MIN_ZEICHEN,
        max_bild_mb=material_paket.MAX_BILD_BYTES // 1_048_576,
        max_pdf_mb=material_paket.MAX_PDF_BYTES // 1_048_576,
        max_paket_mb=material_paket.MAX_PAKET_BYTES // 1_048_576,
        ocr_max_seiten=config.ops().browser_ocr_max_seiten,
        ocr_max_kante=config.ops().browser_ocr_max_kante,
        ocr_min_konfidenz=config.ops().browser_ocr_min_konfidenz,
        ocr_sprachen=config.ops().ocr_sprachen,
        kopf_prozent=config.load_safe().header_crop_percent)


@router.post(f"{BASIS}/paket")
async def themenblatt_paket(request: Request):
    """Neues Themenblatt-Paket: die geordneten Seiten plus Browser-Texte."""
    try:
        vorab_groesse(request)
    except material_paket.PaketFehler as exc:
        return JSONResponse({"fehler": str(exc)}, status_code=413)
    formular = await request.form()
    # Der Formularzustand reist mit: per Query (fetch/data-url) oder als
    # versteckte Felder (Formular ohne JavaScript).
    entwurf = {**_entwurf(request), **_entwurf(request, formular)}
    try:
        dateien, metadaten = seiten_aus_formular(formular)
        paket_id = material_paket.anlegen(
            zweck="klassenarbeit",
            subject=entwurf.get("fach") or str(formular.get("fach") or ""),
            dateien=await dateien_lesen(dateien),
            metadaten=metadaten)
    except material_paket.PaketFehler as exc:
        return JSONResponse({"fehler": str(exc)}, status_code=422)
    return antwort(_detail_url(paket_id, entwurf), request)


# ---------------------------------------------------------------------------
# Stand und Prüfung — alles bleibt unter /klassenarbeit
# ---------------------------------------------------------------------------

@router.get(f"{BASIS}/{{paket_id}}", response_class=HTMLResponse)
def themenblatt_stand(request: Request, paket_id: int):
    """Status- und Prüfseite — je nach Stand: Fortschritt oder Auswahl."""
    paket = _weg(request, paket_id)
    if paket is None:
        return zurueck(BASIS)
    entwurf = _entwurf(request)
    gelesen = sum(1 for s in paket["seiten"] if s["state"] == "gelesen")
    return render(
        request, "themenblatt_pruefen.html",
        adult_page=not config.load_safe().klassenarbeit_kind,
        paket=paket, entwurf=entwurf,
        signatur=f"{paket['state']}:{len(paket['seiten'])}:{gelesen}",
        faecher_liste=[(k, faecher.NAMEN[k]) for k in faecher.FAECHER],
        zurueck_url=_neu_url(entwurf=entwurf),
        neu_url=_neu_url(paket_id=paket_id, entwurf=entwurf),
        upload_url=BASIS + (f"?{urlencode(entwurf)}" if entwurf else ""))


@router.get(f"{BASIS}/{{paket_id}}/stand")
def themenblatt_stand_json(paket_id: int):
    """Kleine JSON-Signatur für `karoAutoRefresh` — kein Inhalt, nur Stand."""
    paket = db.q1("SELECT state FROM material_paket WHERE id=? "
                  "AND zweck='klassenarbeit'", paket_id)
    if paket is None:
        return JSONResponse({"signatur": "weg"})
    seiten = db.q1(
        "SELECT COUNT(*) AS n, SUM(state='gelesen') AS g "
        "FROM material_seite WHERE paket_id=?", paket_id)
    signatur = f"{paket['state']}:{seiten['n']}:{seiten['g'] or 0}"
    return JSONResponse({"signatur": signatur})


@router.get(f"{BASIS}/{{paket_id}}/seite/{{seite_id}}.jpg")
def themenblatt_seite_bild(paket_id: int, seite_id: int):
    """Das gespeicherte Bild einer Seite — nur für das eigene Paket."""
    from fastapi.responses import FileResponse
    from pathlib import Path
    if _themenblatt_paket(paket_id) is None:
        return HTMLResponse("Seite nicht gefunden.", status_code=404)
    seite = db.q1(
        """SELECT s.id, d.stored_path FROM material_seite s
             JOIN document d ON d.id = s.document_id
            WHERE s.id=? AND s.paket_id=?""", seite_id, paket_id)
    if seite is None or not Path(seite["stored_path"]).is_file():
        return HTMLResponse("Seite nicht gefunden.", status_code=404)
    return FileResponse(seite["stored_path"], media_type="image/jpeg")


@router.post(f"{BASIS}/{{paket_id}}/seiten")
async def themenblatt_seiten(request: Request, paket_id: int):
    """Seiten nachträglich ergänzen — danach läuft die Analyse erneut."""
    if _themenblatt_paket(paket_id) is None:
        return JSONResponse({"fehler": "Dieses Material gibt es hier nicht."},
                            status_code=404)
    entwurf = _entwurf(request)
    try:
        vorab_groesse(request)
    except material_paket.PaketFehler as exc:
        return JSONResponse({"fehler": str(exc)}, status_code=413)
    formular = await request.form()
    try:
        dateien, metadaten = seiten_aus_formular(formular)
        material_paket.anhaengen(paket_id, await dateien_lesen(dateien),
                                 metadaten)
    except material_paket.PaketFehler as exc:
        return JSONResponse({"fehler": str(exc)}, status_code=422)
    return antwort(_detail_url(paket_id, entwurf), request)


@router.post(f"{BASIS}/{{paket_id}}/seite/{{seite_id}}/entfernen")
def themenblatt_seite_entfernen(request: Request, paket_id: int,
                              seite_id: int):
    if _themenblatt_paket(paket_id) is None:
        flash(request, "Dieses Material gibt es hier nicht.", "warn")
        return zurueck(BASIS)
    entwurf = _entwurf(request)
    try:
        bleibt = material_paket.seite_entfernen(paket_id, seite_id)
    except material_paket.PaketFehler as exc:
        flash(request, str(exc), "warn")
        return zurueck(_detail_url(paket_id, entwurf))
    if not bleibt:
        flash(request, "Die letzte Seite ist weg — das Paket auch.")
        return zurueck(_neu_url(entwurf=entwurf))
    return zurueck(_detail_url(paket_id, entwurf))


@router.post(f"{BASIS}/{{paket_id}}/erneut")
def themenblatt_erneut(request: Request, paket_id: int):
    if _themenblatt_paket(paket_id) is None:
        flash(request, "Dieses Material gibt es hier nicht.", "warn")
        return zurueck(BASIS)
    entwurf = _entwurf(request)
    try:
        material_paket.erneut_analysieren(paket_id)
    except material_paket.PaketFehler as exc:
        flash(request, str(exc), "warn")
    return zurueck(_detail_url(paket_id, entwurf))


@router.post(f"{BASIS}/{{paket_id}}/uebernehmen")
async def themenblatt_uebernehmen(request: Request, paket_id: int):
    """Der Mensch hat entschieden: diese Prüfungsinhalte stimmen.

    Das Ergebnis fuellt das Formular der neuen Arbeit — angelegt wird dort
    und nur dort. Kein Lernthema entsteht hier, keinerlei Weg nach /lernen.
    """
    formular = await request.form()
    paket = _themenblatt_paket(paket_id)
    if paket is None:
        flash(request, "Dieses Material gibt es hier nicht (mehr).", "warn")
        return zurueck(BASIS)
    entwurf = {**_entwurf(request), **_entwurf(request, formular)}

    themen = [str(t) for t in formular.getlist("thema")]
    themen += [z.strip() for z in str(formular.get("extra") or "")
               .replace(",", "\n").splitlines() if z.strip()]
    fach = str(formular.get("fach") or "")
    try:
        stand = material_paket.pruefinhalte_uebernehmen(paket_id, fach, themen)
    except (material_paket.PaketFehler, faecher.FachFehler) as exc:
        flash(request, str(exc), "warn")
        return zurueck(_detail_url(paket_id, entwurf))

    entwurf["fach"] = stand["fach"]
    # Erkannter Termin nur als Vorschlag — ein eingetragener gewinnt.
    if not entwurf.get("termin"):
        ergebnis = paket["ergebnis"]
        if ergebnis.get("termin"):
            entwurf["termin"] = ergebnis["termin"]
    flash(request, f"{len(stand['inhalte'])} erkannte Prüfungsinhalte "
                   "übernommen — prüfe sie unten noch einmal.")
    return zurueck(_neu_url(paket_id, entwurf))
