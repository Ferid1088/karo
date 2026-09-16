"""Der Begleiter (ersetzt "Karo" im Kind-Bereich) und das Interessen-Tagebuch."""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from .. import config, security
from ..routers.shared import render, flash, zurueck
from . import store

router = APIRouter(prefix='/welten')

BILD_ENDUNGEN = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
                 '.webp': 'image/webp', '.gif': 'image/gif'}
AUDIO_ENDUNGEN = {'.webm': 'audio/webm', '.ogg': 'audio/ogg', '.m4a': 'audio/mp4',
                  '.mp3': 'audio/mpeg', '.wav': 'audio/wav'}


def authenticated(request: Request):
    if not request.session.get('auth') or request.session.get('role') not in ('child', 'parent'):
        raise HTTPException(403, 'Bitte anmelden.')


async def _speichere_datei(datei: UploadFile | None, erlaubt: dict, verzeichnis: Path) -> str | None:
    """Liest eine Upload-Datei begrenzt ein und speichert sie unter zufälligem
    Namen. `None`, wenn keine Datei mitgeschickt wurde."""
    if datei is None or not getattr(datei, 'filename', ''):
        return None
    endung = Path(datei.filename).suffix.lower()
    if endung not in erlaubt:
        raise ValueError('Dieses Dateiformat wird nicht unterstützt.')
    puffer = bytearray()
    while stueck := await datei.read(1 << 20):
        puffer.extend(stueck)
        if len(puffer) > security.MAX_UPLOAD_BYTES:
            raise ValueError('Datei zu groß.')
    name = f'{uuid.uuid4().hex}{endung}'
    (verzeichnis / name).write_bytes(bytes(puffer))
    return name


def view(request, name='home', status_code=200, **ctx):
    return render(request, f'welten/{name}.html', status_code=status_code,
                  farben=store.FARBEN,
                  begleiter=store.current_companion(),
                  begleiter_verlauf=store.companion_history(),
                  interesse=store.current_interest(),
                  interesse_verlauf=store.interest_history(), **ctx)


@router.get('', dependencies=[Depends(authenticated)])
def home(request: Request):
    return view(request)


@router.post('/begleiter', dependencies=[Depends(authenticated)])
async def begleiter_speichern(request: Request):
    data = await request.form()
    try:
        foto = await _speichere_datei(data.get('foto'), BILD_ENDUNGEN, config.begleiter_dir())
        if foto is None:
            bisher = store.current_companion()
            foto = bisher['foto_pfad'] if bisher else None
        store.add_companion(data.get('name'), foto, data.get('farbe'), data.get('spass_antwort'))
        flash(request, 'Dein Begleiter ist gespeichert.')
    except ValueError as exc:
        return view(request, error=str(exc))
    return zurueck('/welten')


@router.post('/interesse', dependencies=[Depends(authenticated)])
async def interesse_speichern(request: Request):
    data = await request.form()
    try:
        audio = await _speichere_datei(data.get('audio'), AUDIO_ENDUNGEN, config.begleiter_dir())
        store.add_interest(data.get('text'), audio)
        flash(request, 'Dein Interesse ist gespeichert.')
    except ValueError as exc:
        return view(request, error=str(exc))
    return zurueck('/welten')


@router.get('/foto/{name}', dependencies=[Depends(authenticated)])
def foto(name: str):
    pfad = config.begleiter_dir() / name
    endung = Path(name).suffix.lower()
    if endung not in BILD_ENDUNGEN or not pfad.is_file():
        return HTMLResponse('Foto nicht gefunden.', status_code=404)
    return FileResponse(pfad, media_type=BILD_ENDUNGEN[endung])


@router.get('/clip/{name}', dependencies=[Depends(authenticated)])
def clip(name: str):
    pfad = config.begleiter_dir() / name
    endung = Path(name).suffix.lower()
    if endung not in AUDIO_ENDUNGEN or not pfad.is_file():
        return HTMLResponse('Aufnahme nicht gefunden.', status_code=404)
    return FileResponse(pfad, media_type=AUDIO_ENDUNGEN[endung])
