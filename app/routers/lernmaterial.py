"""Lernmaterial: ein Arbeitsblatt mit einer oder mehreren Seiten hochladen.

Die Seiten kommen als einzelne Bilder an — ein PDF hat der Browser schon in
Seiten zerlegt (`static/material-paket.js` + pdf.js). Jede Seite geht durch
`ingest.aufnehmen` in die `document`-Ablage; das Paket selbst steht in
`material_paket`/`material_seite` und wird von `app/material_paket.py`
geführt. Das fachliche Modell sieht davon nur geschwärzten Text.

Nur der Lernbereich läuft hier: bestätigte Themen werden Lernthemen. Das
Themenblatt einer Klassenarbeit hat seinen eigenen Router —
`routers/themenblatt.py` unter /klassenarbeit — und die Pakete beider
Seiten tauchen hier nicht auf. Eine alte Adresse mit `zweck=klassenarbeit`
wird nur noch dorthin umgeleitet, ohne dass Lernlogik läuft.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from .. import config, db, faecher, material_paket
from .shared import (aktives_fach, antwort, dateien_lesen, flash, render,
                     seiten_aus_formular, vorab_groesse, zurueck)

router = APIRouter()


def _lern_paket(paket_id: int) -> dict | None:
    """Das Paket dieses Routers — nur Lernpakete. Ein Themenblatt der
    Klassenarbeit gehört nie hierher; sein Weg liegt unter
    /klassenarbeit/themenblatt."""
    try:
        paket = material_paket.holen(paket_id)
    except material_paket.PaketFehler:
        return None
    return paket if paket["zweck"] == "lernen" else None


@router.get("/lernen/material", response_class=HTMLResponse)
def material_seite(request: Request):
    """Der Upload: Seiten sammeln, ordnen, einlesen lassen."""
    # Altadresse: der Klassenarbeits-Upload hat seine eigenen Routen unter
    # /klassenarbeit/themenblatt — hier läuft keine Lernlogik dafür.
    if str(request.query_params.get("zweck") or "") == "klassenarbeit":
        ziel = "/klassenarbeit/themenblatt"
        if "kamera" in request.query_params:
            ziel += "?kamera=1"
        return zurueck(ziel)
    fach = aktives_fach(request, request.query_params.get("fach"))
    return render(request, "learning_upload.html", fach=fach, zweck="lernen",
                  fach_name=faecher.NAMEN.get(fach, "deinem Fach"),
                  max_seiten=material_paket.MAX_SEITEN,
                  min_zeichen=material_paket.MIN_ZEICHEN,
                  max_bild_mb=material_paket.MAX_BILD_BYTES // 1_048_576,
                  max_pdf_mb=material_paket.MAX_PDF_BYTES // 1_048_576,
                  max_paket_mb=material_paket.MAX_PAKET_BYTES // 1_048_576,
                  ocr_max_seiten=config.ops().browser_ocr_max_seiten,
                  ocr_max_kante=config.ops().browser_ocr_max_kante,
                  ocr_min_konfidenz=config.ops().browser_ocr_min_konfidenz,
                  ocr_sprachen=config.ops().ocr_sprachen,
                  kopf_prozent=config.load_safe().header_crop_percent,
                  quelle=request.query_params.get("quelle", ""))


@router.post("/lernen/material/paket")
async def paket_anlegen(request: Request):
    """Neues Paket: die geordneten Seiten-Bilder plus Browser-Texte."""
    try:
        vorab_groesse(request)
    except material_paket.PaketFehler as exc:
        return JSONResponse({"fehler": str(exc)}, status_code=413)
    formular = await request.form()
    if str(formular.get("zweck") or "lernen") != "lernen":
        return JSONResponse(
            {"fehler": "Das Themenblatt einer Klassenarbeit läuft über "
                       "ihren eigenen Weg unter „Klassenarbeit“."},
            status_code=422)
    try:
        dateien, metadaten = seiten_aus_formular(formular)
        paket_id = material_paket.anlegen(
            zweck="lernen",
            subject=str(formular.get("fach") or ""),
            dateien=await dateien_lesen(dateien),
            metadaten=metadaten)
    except material_paket.PaketFehler as exc:
        return JSONResponse({"fehler": str(exc)}, status_code=422)
    return antwort(f"/lernen/material/{paket_id}", request)


@router.get("/lernen/material/{paket_id}", response_class=HTMLResponse)
def paket_stand(request: Request, paket_id: int):
    """Status- und Prüfseite — je nach Stand: Fortschritt oder Auswahl."""
    paket = _lern_paket(paket_id)
    if paket is None:
        # Altlink auf ein Themenblatt: einmal klar umleiten, sonst weg.
        roh = db.q1("SELECT zweck FROM material_paket WHERE id=?", paket_id)
        if roh and roh["zweck"] == "klassenarbeit":
            return zurueck(f"/klassenarbeit/themenblatt/{paket_id}")
        flash(request, "Dieses Material gibt es nicht (mehr).", "warn")
        return zurueck("/lernen/material")
    gelesen = sum(1 for s in paket["seiten"] if s["state"] == "gelesen")
    # Nur die drei echten Fächer: „andere" läuft durch `pflicht` in eine
    # Sackgasse — Themen dazu kann Karo ohnehin nicht anlegen.
    faecher_liste = [(k, faecher.NAMEN[k]) for k in faecher.FAECHER]
    fach_hint = paket["subject"] or "mathematik"
    return render(
        request, "material_pruefen.html", paket=paket,
        signatur=f"{paket['state']}:{len(paket['seiten'])}:{gelesen}",
        faecher_liste=faecher_liste,
        klasse=config.load_safe().learner_grade,
        paket_upload_url=f"/lernen/material?fach={fach_hint}")


@router.get("/lernen/material/{paket_id}/stand")
def paket_stand_json(paket_id: int):
    """Kleine JSON-Signatur für `karoAutoRefresh` — ändert sie sich, lädt die
    Seite neu. Kein Inhalt, nur Stand."""
    paket = db.q1("SELECT state FROM material_paket WHERE id=?", paket_id)
    if paket is None:
        return JSONResponse({"signatur": "weg"})
    seiten = db.q1(
        "SELECT COUNT(*) AS n, SUM(state='gelesen') AS g "
        "FROM material_seite WHERE paket_id=?", paket_id)
    signatur = f"{paket['state']}:{seiten['n']}:{seiten['g'] or 0}"
    return JSONResponse({"signatur": signatur})


@router.get("/lernen/material/{paket_id}/seite/{seite_id}.jpg")
def paket_seite_bild(request: Request, paket_id: int, seite_id: int):
    """Das gespeicherte Bild einer Paket-Seite — nur für das eigene Paket."""
    from fastapi.responses import FileResponse
    from pathlib import Path
    if _lern_paket(paket_id) is None:
        return HTMLResponse("Seite nicht gefunden.", status_code=404)
    seite = db.q1(
        """SELECT s.id, d.stored_path FROM material_seite s
             JOIN document d ON d.id = s.document_id
            WHERE s.id=? AND s.paket_id=?""", seite_id, paket_id)
    if seite is None or not Path(seite["stored_path"]).is_file():
        return HTMLResponse("Seite nicht gefunden.", status_code=404)
    return FileResponse(seite["stored_path"], media_type="image/jpeg")


@router.post("/lernen/material/{paket_id}/seiten")
async def paket_seiten(request: Request, paket_id: int):
    """Seiten nachträglich ergänzen — z. B. eine neu fotografierte."""
    if _lern_paket(paket_id) is None:
        return JSONResponse({"fehler": "Dieses Material gibt es hier nicht."},
                            status_code=404)
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
    return antwort(f"/lernen/material/{paket_id}", request)


@router.post("/lernen/material/{paket_id}/seite/{seite_id}/entfernen")
def paket_seite_entfernen(request: Request, paket_id: int, seite_id: int):
    if _lern_paket(paket_id) is None:
        flash(request, "Dieses Material gibt es hier nicht.", "warn")
        return zurueck("/lernen/material")
    try:
        bleibt = material_paket.seite_entfernen(paket_id, seite_id)
    except material_paket.PaketFehler as exc:
        flash(request, str(exc), "warn")
        return zurueck(f"/lernen/material/{paket_id}")
    if not bleibt:
        flash(request, "Die letzte Seite ist weg — das Paket auch.")
        return zurueck("/lernen/material")
    return zurueck(f"/lernen/material/{paket_id}")


@router.post("/lernen/material/{paket_id}/erneut")
def paket_erneut(request: Request, paket_id: int):
    if _lern_paket(paket_id) is None:
        flash(request, "Dieses Material gibt es hier nicht.", "warn")
        return zurueck("/lernen/material")
    try:
        material_paket.erneut_analysieren(paket_id)
    except material_paket.PaketFehler as exc:
        flash(request, str(exc), "warn")
    return zurueck(f"/lernen/material/{paket_id}")


@router.post("/lernen/material/{paket_id}/uebernehmen")
async def paket_uebernehmen(request: Request, paket_id: int):
    """Der Mensch hat entschieden: diese Themen stimmen."""
    formular = await request.form()
    paket = _lern_paket(paket_id)
    if paket is None:
        flash(request, "Dieses Material gibt es hier nicht (mehr).", "warn")
        return zurueck("/lernen/material")

    themen = [str(t) for t in formular.getlist("thema")]
    themen += [z.strip() for z in str(formular.get("extra") or "")
               .replace(",", "\n").splitlines() if z.strip()]
    fach = str(formular.get("fach") or "")
    try:
        klasse = int(formular.get("klasse") or 0) or None
    except (TypeError, ValueError):
        klasse = None
    if klasse is not None and not 1 <= klasse <= 13:
        klasse = None

    try:
        stand = material_paket.uebernehmen(paket_id, fach, themen, klasse)
    except (material_paket.PaketFehler, faecher.FachFehler) as exc:
        flash(request, str(exc), "warn")
        return zurueck(f"/lernen/material/{paket_id}")

    if stand["abgewiesen"]:
        fach_name = faecher.NAMEN.get(faecher.pflicht(fach), "diesem Fach")
        flash(request, f"{len(stand['angelegt'])} Themen übernommen. Nicht aus "
              f"{fach_name} und deshalb nicht dabei: "
              + ", ".join(stand["abgewiesen"]), "warn")
    else:
        flash(request, f"Material erkannt — {len(stand['angelegt'])} "
              f"{'Thema' if len(stand['angelegt']) == 1 else 'Themen'} "
              f"übernommen: {', '.join(stand['angelegt'])}")
    return zurueck(f"/lernen/{faecher.pflicht(fach)}")
