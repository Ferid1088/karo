"""Materialpakete: ein Arbeitsblatt mit einer oder mehreren Seiten hochladen.

Die Seiten kommen als einzelne Bilder an — ein PDF hat der Browser schon in
Seiten zerlegt (`static/material-paket.js` + pdf.js). Jede Seite geht durch
`ingest.aufnehmen` in die `document`-Ablage; das Paket selbst steht in
`material_paket`/`material_seite` und wird von `app/material_paket.py`
geführt. Das fachliche Modell sieht davon nur geschwärzten Text.

Zwei Zwecke teilen sich denselben Weg:

  zweck=lernen         → bestätigte Themen werden Lernthemen
  zweck=klassenarbeit  → bestätigte Themen füllen das Formular der neuen
                         Klassenarbeit; Termin und Anlegen bleiben dort
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from .. import config, db, faecher, material_paket
from .shared import aktives_fach, flash, render, zurueck

router = APIRouter()


def _seiten_aus_formular(formular) -> tuple[list, list[dict]]:
    """Dateien und ihre Metadaten aus dem mehrteiligen Formular.

    `seite` sind die Bilddateien in Seitenfolge, `seiten` ein JSON-Array
    derselben Länge mit {name, text, konfidenz, art} — die Reihenfolge ist
    die, die das Kind in der Vorschau angeordnet hat.
    """
    try:
        metadaten = json.loads(str(formular.get("seiten") or "[]"))
    except json.JSONDecodeError:
        raise material_paket.PaketFehler("Die Seitenangaben sind beschädigt.")
    if not isinstance(metadaten, list):
        raise material_paket.PaketFehler("Die Seitenangaben sind beschädigt.")
    dateien = [d for d in formular.getlist("seite")
               if getattr(d, "filename", "")]
    return dateien, metadaten


def _vorab_groesse(request: Request) -> None:
    """Content-Length prüfen, bevor der mehrteilige Rumpf gelesen wird —
    ein zu großer Upload wird abgelehnt, ohne dass er im Speicher landet."""
    try:
        angekuendigt = int(request.headers.get("content-length") or 0)
    except ValueError:
        angekuendigt = 0
    # Zwei MB Luft für die Formularrahmen der Seiten.
    if angekuendigt > material_paket.MAX_PAKET_BYTES + 2_000_000:
        raise material_paket.PaketFehler(
            f"Der Upload ist zu groß — ein Paket darf höchstens "
            f"{material_paket.MAX_PAKET_BYTES // 1_048_576} MB haben.")


async def _dateien_lesen(dateien) -> list[tuple[str, bytes]]:
    gelesen = []
    for i, datei in enumerate(dateien, 1):
        # Das größte Einzellimit (PDF) deckelt den Leseaufruf — welches der
        # getrennten Limits greift, entscheidet material_paket am Dateityp.
        daten = await datei.read(material_paket.MAX_PDF_BYTES + 1)
        if not daten:
            raise material_paket.PaketFehler(f"Seite {i} kam leer an.")
        gelesen.append((datei.filename or f"seite-{i}.jpg", daten))
    return gelesen


def _antwort(weiter: str, request: Request):
    """fetch() bekommt JSON; ein abgeschicktes Formular den nächsten Schritt."""
    if "text/html" in (request.headers.get("accept") or ""):
        return zurueck(weiter)
    return JSONResponse({"weiter": weiter})


@router.get("/lernen/material", response_class=HTMLResponse)
def material_seite(request: Request):
    """Der Upload: Seiten sammeln, ordnen, einlesen lassen."""
    zweck = str(request.query_params.get("zweck") or "lernen")
    if zweck not in material_paket.ZWECKE:
        zweck = "lernen"
    fach = aktives_fach(request, request.query_params.get("fach"))
    return render(request, "learning_upload.html", fach=fach, zweck=zweck,
                  fach_name=faecher.NAMEN.get(fach, "deinem Fach"),
                  max_seiten=material_paket.MAX_SEITEN,
                  max_bild_mb=material_paket.MAX_BILD_BYTES // 1_048_576,
                  max_pdf_mb=material_paket.MAX_PDF_BYTES // 1_048_576,
                  max_paket_mb=material_paket.MAX_PAKET_BYTES // 1_048_576,
                  kopf_prozent=config.load_safe().header_crop_percent,
                  quelle=request.query_params.get("quelle", ""))


@router.post("/lernen/material/paket")
async def paket_anlegen(request: Request):
    """Neues Paket: die geordneten Seiten-Bilder plus Browser-Texte."""
    try:
        _vorab_groesse(request)
    except material_paket.PaketFehler as exc:
        return JSONResponse({"fehler": str(exc)}, status_code=413)
    formular = await request.form()
    try:
        dateien, metadaten = _seiten_aus_formular(formular)
        paket_id = material_paket.anlegen(
            zweck=str(formular.get("zweck") or ""),
            subject=str(formular.get("fach") or ""),
            dateien=await _dateien_lesen(dateien),
            metadaten=metadaten)
    except material_paket.PaketFehler as exc:
        return JSONResponse({"fehler": str(exc)}, status_code=422)
    return _antwort(f"/lernen/material/{paket_id}", request)


@router.get("/lernen/material/{paket_id}", response_class=HTMLResponse)
def paket_stand(request: Request, paket_id: int):
    """Status- und Prüfseite — je nach Stand: Fortschritt oder Auswahl."""
    try:
        paket = material_paket.holen(paket_id)
    except material_paket.PaketFehler:
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
        paket_upload_url=(
            "/lernen/material?zweck=klassenarbeit&fach=" + fach_hint
            if paket["zweck"] == "klassenarbeit"
            else f"/lernen/material?fach={fach_hint}"))


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
    try:
        _vorab_groesse(request)
    except material_paket.PaketFehler as exc:
        return JSONResponse({"fehler": str(exc)}, status_code=413)
    formular = await request.form()
    try:
        dateien, metadaten = _seiten_aus_formular(formular)
        material_paket.anhaengen(paket_id, await _dateien_lesen(dateien),
                                 metadaten)
    except material_paket.PaketFehler as exc:
        return JSONResponse({"fehler": str(exc)}, status_code=422)
    return _antwort(f"/lernen/material/{paket_id}", request)


@router.post("/lernen/material/{paket_id}/seite/{seite_id}/entfernen")
def paket_seite_entfernen(request: Request, paket_id: int, seite_id: int):
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
    try:
        material_paket.erneut_analysieren(paket_id)
    except material_paket.PaketFehler as exc:
        flash(request, str(exc), "warn")
    return zurueck(f"/lernen/material/{paket_id}")


@router.post("/lernen/material/{paket_id}/uebernehmen")
async def paket_uebernehmen(request: Request, paket_id: int):
    """Der Mensch hat entschieden: diese Themen stimmen."""
    formular = await request.form()
    try:
        paket = material_paket.holen(paket_id)
    except material_paket.PaketFehler:
        flash(request, "Dieses Material gibt es nicht (mehr).", "warn")
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

    if paket["zweck"] == "klassenarbeit":
        flash(request, f"{len(stand['angelegt'])} erkannte Themen übernommen — "
                       "prüfe sie unten noch einmal.")
        return zurueck(f"/klassenarbeit/neu?material={paket_id}")

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
