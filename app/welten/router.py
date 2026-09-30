"""Routes for the private, deterministic "Meine Welt" area."""
from __future__ import annotations

import datetime as dt
import json
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from starlette.background import BackgroundTask
from starlette.status import HTTP_303_SEE_OTHER

from ..routers.shared import flash, render
from . import content as editorial
from . import media, store, world_db

router = APIRouter(prefix="/welten")

MOOD_LABELS = {
    "schoen": "😊 Schön",
    "lustig": "😂 Lustig",
    "besonders": "⭐ Besonders",
    "schwierig": "😤 Schwierig",
    "komisch": "🤔 Komisch",
}


def authenticated(request: Request):
    if not request.session.get("auth") or request.session.get("role") not in ("child", "parent"):
        raise HTTPException(403, "Bitte anmelden.")


def parent_only(request: Request):
    authenticated(request)
    if request.session.get("role") != "parent":
        raise HTTPException(403, "Das ist ein Eltern-Bereich.")


def child_only(request: Request):
    """„Meine Welt" gehoert dem Kind — mit dem Eltern-Passwort steht sie zu.

    Eltern verwalten den Bereich unter /welten/eltern (Freigabe, Pause,
    Export, Loeschen) und sehen die kindgerechte Erklaerung unter
    /welten/datenschutz. Wer hineinschauen will, schaltet die Sitzung im
    Elternbereich in den Kind-Modus; danach ist die Rolle "child" und der
    Weg zurueck geht nur ueber ein neues Login. Genau diese Huerde ist der
    Sinn: ein aufgeschlagenes Tagebuch ist kein Elternwerkzeug.
    """
    authenticated(request)
    if request.session.get("role") != "child":
        raise HTTPException(
            403, "„Meine Welt“ gehört dem Kind. Eltern verwalten sie unter "
                 "„Für Eltern → Meine Welt“.")


def _today_date() -> dt.date:
    return dt.date.fromisoformat(world_db.today())


def _world_access(request: Request) -> dict:
    cfg = store.settings()
    if request.session.get("role") == "child" and not cfg["enabled"]:
        raise HTTPException(403, "Meine Welt ist noch nicht von einem Elternteil freigegeben.")
    return cfg


def _view(request: Request, name: str, status_code: int = 200, **ctx):
    # Von "Meine Welt" erreichen Eltern nur ihre Verwaltungsseite und die
    # kindgerechte Erklaerung. Beide gehoeren in den Elternbereich: mit der
    # Unterzeile des Kinderbereichs zeigten sie auf Jahr und Zeitkapseln,
    # also auf Seiten, die Eltern gar nicht oeffnen duerfen.
    eltern = request.session.get("role") == "parent"
    basis = {
        "world_page": not eltern,
        "adult_page": eltern,
        "world_settings": store.settings(),
        "mood_labels": MOOD_LABELS,
    }
    response = render(
        request,
        f"welten/{name}.html",
        status_code=status_code,
        **{**basis, **ctx},
    )
    # "Meine Welt" has no third-party runtime dependencies. Keep its browser
    # policy stricter than legacy learning pages while those are migrated.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: blob:; media-src 'self' blob:; "
        "script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; font-src 'self'; object-src 'none'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    response.headers["Cache-Control"] = "private, no-store"
    return response


def _files(form, field: str) -> list[UploadFile]:
    result = []
    for item in form.getlist(field):
        # Starlette's multipart parser may return its base UploadFile class,
        # so use the file protocol instead of an isinstance check.
        if getattr(item, "filename", "") and callable(getattr(item, "read", None)):
            result.append(item)
    return result


def _file(form, field: str) -> UploadFile | None:
    item = form.get(field)
    if getattr(item, "filename", "") and callable(getattr(item, "read", None)):
        return item
    return None


def _duration(form) -> int:
    raw = str(form.get("audio_duration") or "0").strip()
    try:
        value = int(raw)
    except ValueError:
        raise ValueError("Die Aufnahmedauer ist ungültig.") from None
    return value


def _remove_media_rows(rows: list[dict]) -> None:
    for row in rows:
        media.delete_keys(row.get("storage_key"), row.get("thumbnail_key"))


@router.get("", dependencies=[Depends(child_only)])
def home(request: Request):
    cfg = store.settings()
    if request.session.get("role") == "child" and not cfg["enabled"]:
        return _view(request, "locked")

    today = _today_date()
    discovery = editorial.daily_discovery(cfg["age_band"], today)
    reflection = editorial.daily_reflection(cfg["age_band"], today)
    usage = store.usage_today()
    moments = store.entries_for_year(today.year)
    saved = store.discoveries_for_year(today.year)
    return _view(
        request,
        "home",
        discovery=discovery,
        reflection=reflection,
        reflection_entry=store.reflection_for_day(),
        moment=store.moment_for_day(),
        usage=usage,
        year_count=len(moments) + len(saved),
        capsule_count=len(store.capsules()),
        needs_approval=not bool(cfg["enabled"]),
    )


@router.get("/datenschutz", dependencies=[Depends(authenticated)])
def privacy(request: Request):
    return _view(request, "privacy")


@router.get("/entdecken", dependencies=[Depends(child_only)])
def discover(request: Request):
    cfg = _world_access(request)
    article = editorial.daily_discovery(cfg["age_band"], _today_date())
    return _view(
        request,
        "discover",
        article=article,
        paragraphs=article.paragraphs(cfg["age_band"]),
        saved=store.discovery_is_saved(article.id),
    )


@router.post("/entdecken/merken", dependencies=[Depends(child_only)])
async def save_discovery(request: Request):
    cfg = _world_access(request)
    form = await request.form()
    article = editorial.by_id(str(form.get("article_id") or ""))
    if article is None:
        raise HTTPException(404, "Entdeckung nicht gefunden.")
    store.save_discovery(article.id, article.title)
    flash(request, "Für dein Jahr gemerkt.")
    return RedirectResponse("/welten/entdecken", status_code=HTTP_303_SEE_OTHER)


@router.post("/nachdenken", dependencies=[Depends(child_only)])
async def save_reflection(request: Request):
    cfg = _world_access(request)
    form = await request.form()
    expected = editorial.daily_reflection(cfg["age_band"], _today_date())
    if str(form.get("prompt_id") or "") != expected.id:
        return _view(
            request,
            "home",
            status_code=400,
            discovery=editorial.daily_discovery(cfg["age_band"], _today_date()),
            reflection=expected,
            reflection_entry=store.reflection_for_day(),
            moment=store.moment_for_day(),
            usage=store.usage_today(),
            year_count=len(store.entries_for_year(_today_date().year)) + len(store.discoveries_for_year(_today_date().year)),
            capsule_count=len(store.capsules()),
            needs_approval=False,
            error="Diese Tagesfrage ist nicht mehr aktuell.",
        )
    try:
        store.save_reflection(expected.id, form.get("text"))
    except ValueError as exc:
        flash(request, str(exc), "err")
    else:
        flash(request, "Dein Gedanke ist gespeichert.")
    return RedirectResponse("/welten", status_code=HTTP_303_SEE_OTHER)


@router.get("/festhalten", dependencies=[Depends(child_only)])
def hold_on(request: Request):
    _world_access(request)
    return _view(
        request,
        "moment",
        moment=store.moment_for_day(),
        usage=store.usage_today(),
    )


@router.post("/festhalten", dependencies=[Depends(child_only)])
async def save_moment(request: Request):
    cfg = _world_access(request)
    form = await request.form()
    photos = _files(form, "photos")
    audio = _file(form, "audio")
    try:
        duration = _duration(form) if audio else 0
        usage = store.usage_today()
        if photos and not cfg["allow_photos"]:
            raise ValueError("Fotos sind in Meine Welt nicht freigegeben.")
        if audio and not cfg["allow_audio"]:
            raise ValueError("Audio ist in Meine Welt nicht freigegeben.")
        if len(photos) > usage["photos_left"]:
            raise ValueError(f"Für heute sind noch {usage['photos_left']} Foto(s) frei.")
        if audio and duration > usage["audio_seconds_left"]:
            raise ValueError(f"Für heute sind noch {usage['audio_seconds_left']} Audio-Sekunden frei.")

        entry_id = store.create_moment(
            form.get("mood"),
            form.get("text"),
            has_media=bool(photos or audio),
        )
        stored_files = []
        try:
            for upload in photos:
                saved = await media.save_photo(upload)
                stored_files.append(saved)
                store.add_media(
                    entry_id=entry_id, capsule_id=None, media_type="photo",
                    storage_key=saved.storage_key, thumbnail_key=saved.thumbnail_key,
                    mime_type=saved.mime_type, byte_size=saved.byte_size,
                )
            if audio:
                saved = await media.save_audio(audio, duration)
                stored_files.append(saved)
                store.add_media(
                    entry_id=entry_id, capsule_id=None, media_type="audio",
                    storage_key=saved.storage_key, thumbnail_key=None,
                    mime_type=saved.mime_type, byte_size=saved.byte_size,
                    duration_seconds=duration,
                )
        except BaseException:
            _remove_media_rows(store.delete_entry(entry_id))
            for saved in stored_files:
                media.delete_keys(saved.storage_key, saved.thumbnail_key)
            raise
    except ValueError as exc:
        return _view(
            request, "moment", status_code=400,
            moment=store.moment_for_day(), usage=store.usage_today(), error=str(exc),
        )

    flash(request, "Dein Moment ist sicher gespeichert.")
    return RedirectResponse("/welten", status_code=HTTP_303_SEE_OTHER)


@router.get("/jahr", dependencies=[Depends(child_only)])
def year(request: Request, year: int | None = None):
    _world_access(request)
    current_year = _today_date().year
    selected = year or current_year
    if selected < 2000 or selected > current_year + 1:
        raise HTTPException(400, "Ungültiges Jahr.")

    timeline = []
    entries = store.entries_for_year(selected)
    for item in entries:
        item["media"] = store.media_for_entry(item["id"])
        item["timeline_date"] = item["entry_date"]
        item["timeline_kind"] = item["kind"]
        timeline.append(item)
    discoveries = store.discoveries_for_year(selected)
    for item in discoveries:
        item["timeline_date"] = item["saved_date"]
        item["timeline_kind"] = "discovery"
        timeline.append(item)
    timeline.sort(key=lambda item: (item["timeline_date"], item.get("id", 0)), reverse=True)

    media_rows = [m for item in entries for m in item["media"]]
    stats = {
        "moments": sum(1 for item in entries if item["kind"] == "moment"),
        "thoughts": sum(1 for item in entries if item["kind"] == "reflection"),
        "discoveries": len(discoveries),
        "photos": sum(1 for row in media_rows if row["media_type"] == "photo"),
        "audio": sum(1 for row in media_rows if row["media_type"] == "audio"),
    }

    one_year_ago = None
    try:
        old_date = _today_date().replace(year=_today_date().year - 1).isoformat()
    except ValueError:
        old_date = (_today_date() - dt.timedelta(days=365)).isoformat()
    old = [item for item in store.entries_for_year(_today_date().year - 1)
           if item["entry_date"] == old_date]
    if old:
        one_year_ago = old[0]
        one_year_ago["media"] = store.media_for_entry(one_year_ago["id"])

    return _view(
        request, "year", timeline=timeline, stats=stats, selected_year=selected,
        current_year=current_year, one_year_ago=one_year_ago,
    )


@router.get("/zeitkapseln", dependencies=[Depends(child_only)])
def time_capsules(request: Request):
    _world_access(request)
    items = store.capsules()
    today = _today_date()
    closed, opened = [], []
    for item in items:
        target = dt.date.fromisoformat(item["opens_on"])
        item["days_left"] = max(0, (target - today).days)
        (opened if store.capsule_is_open(item) else closed).append(item)
    return _view(
        request, "capsules", closed=closed, opened=opened,
        usage=store.usage_today(), today=today.isoformat(),
        month_date=(today + dt.timedelta(days=30)).isoformat(),
        year_date=(today + dt.timedelta(days=365)).isoformat(),
    )


@router.post("/zeitkapseln", dependencies=[Depends(child_only)])
async def create_time_capsule(request: Request):
    cfg = _world_access(request)
    form = await request.form()
    photos = _files(form, "photos")
    audio = _file(form, "audio")
    try:
        duration = _duration(form) if audio else 0
        usage = store.usage_today()
        if photos and not cfg["allow_photos"]:
            raise ValueError("Fotos sind in Meine Welt nicht freigegeben.")
        if audio and not cfg["allow_audio"]:
            raise ValueError("Audio ist in Meine Welt nicht freigegeben.")
        if len(photos) > usage["photos_left"]:
            raise ValueError(f"Für heute sind noch {usage['photos_left']} Foto(s) frei.")
        if audio and duration > usage["audio_seconds_left"]:
            raise ValueError(f"Für heute sind noch {usage['audio_seconds_left']} Audio-Sekunden frei.")

        capsule_id = store.create_capsule(
            form.get("title"), form.get("text"), form.get("opens_on"),
            has_media=bool(photos or audio),
        )
        stored_files = []
        try:
            for upload in photos:
                saved = await media.save_photo(upload)
                stored_files.append(saved)
                store.add_media(
                    entry_id=None, capsule_id=capsule_id, media_type="photo",
                    storage_key=saved.storage_key, thumbnail_key=saved.thumbnail_key,
                    mime_type=saved.mime_type, byte_size=saved.byte_size,
                )
            if audio:
                saved = await media.save_audio(audio, duration)
                stored_files.append(saved)
                store.add_media(
                    entry_id=None, capsule_id=capsule_id, media_type="audio",
                    storage_key=saved.storage_key, thumbnail_key=None,
                    mime_type=saved.mime_type, byte_size=saved.byte_size,
                    duration_seconds=duration,
                )
        except BaseException:
            _remove_media_rows(store.delete_capsule(capsule_id))
            for saved in stored_files:
                media.delete_keys(saved.storage_key, saved.thumbnail_key)
            raise
    except ValueError as exc:
        flash(request, str(exc), "err")
        return RedirectResponse("/welten/zeitkapseln", status_code=HTTP_303_SEE_OTHER)

    flash(request, "Zeitkapsel geschlossen.")
    return RedirectResponse("/welten/zeitkapseln", status_code=HTTP_303_SEE_OTHER)


@router.get("/zeitkapseln/{capsule_id}", dependencies=[Depends(child_only)])
def time_capsule(request: Request, capsule_id: int):
    _world_access(request)
    item = store.capsule(capsule_id)
    if not item:
        raise HTTPException(404, "Zeitkapsel nicht gefunden.")
    if not store.capsule_is_open(item):
        # Never place the locked text or media list in the template context.
        return _view(request, "capsule", locked=True, capsule={
            "id": item["id"], "title": item["title"], "opens_on": item["opens_on"],
            "created_at": item["created_at"],
        })
    store.mark_capsule_opened(capsule_id)
    item = store.capsule(capsule_id)
    return _view(
        request, "capsule", locked=False, capsule=item,
        capsule_media=store.media_for_capsule(capsule_id),
    )


@router.post("/eintrag/{entry_id}/loeschen", dependencies=[Depends(child_only)])
async def delete_entry(request: Request, entry_id: int):
    _world_access(request)
    rows = store.delete_entry(entry_id)
    if not rows and not store.entry(entry_id):
        # The entry may legitimately have no media; reaching here after delete
        # is still successful, so no information leak is useful.
        pass
    _remove_media_rows(rows)
    flash(request, "Eintrag gelöscht.")
    return RedirectResponse("/welten/jahr", status_code=HTTP_303_SEE_OTHER)


@router.post("/zeitkapseln/{capsule_id}/loeschen", dependencies=[Depends(child_only)])
async def delete_capsule(request: Request, capsule_id: int):
    _world_access(request)
    rows = store.delete_capsule(capsule_id)
    _remove_media_rows(rows)
    flash(request, "Zeitkapsel gelöscht.")
    return RedirectResponse("/welten/zeitkapseln", status_code=HTTP_303_SEE_OTHER)


@router.get("/media/{token}", dependencies=[Depends(child_only)])
def private_media(request: Request, token: str, thumb: int = 0):
    _world_access(request)
    row = store.media_by_token(token)
    if not row:
        raise HTTPException(404, "Medium nicht gefunden.")
    if row.get("capsule_id") and str(row.get("opens_on") or "") > world_db.today():
        raise HTTPException(404, "Medium nicht gefunden.")
    key = row["thumbnail_key"] if thumb and row["thumbnail_key"] else row["storage_key"]
    try:
        path = media.path_for(key)
    except FileNotFoundError:
        raise HTTPException(404, "Medium nicht gefunden.") from None
    mime = "image/webp" if thumb and row["thumbnail_key"] else row["mime_type"]
    return FileResponse(
        path,
        media_type=mime,
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/eltern", dependencies=[Depends(parent_only)])
def parent_settings(request: Request):
    return _view(request, "parent", export_ready=bool(store.export_snapshot()["entries"] or store.export_snapshot()["capsules"]))


@router.post("/eltern/freigabe", dependencies=[Depends(parent_only)])
async def parent_approve(request: Request):
    form = await request.form()
    try:
        store.approve(
            str(form.get("age_band") or ""),
            allow_photos=form.get("allow_photos") == "1",
            allow_audio=form.get("allow_audio") == "1",
        )
    except ValueError as exc:
        return _view(request, "parent", status_code=400, export_ready=False, error=str(exc))
    flash(request, "Meine Welt ist für das Kind freigegeben.")
    return RedirectResponse("/welten/eltern", status_code=HTTP_303_SEE_OTHER)


@router.post("/eltern/deaktivieren", dependencies=[Depends(parent_only)])
async def parent_disable(request: Request):
    store.disable()
    flash(request, "Meine Welt ist für das Kind pausiert. Gespeicherte Daten bleiben erhalten.")
    return RedirectResponse("/welten/eltern", status_code=HTTP_303_SEE_OTHER)


@router.get("/eltern/export.zip", dependencies=[Depends(parent_only)])
def parent_export(request: Request):
    snapshot = store.export_snapshot()
    handle = tempfile.NamedTemporaryFile(prefix="karo-meine-welt-", suffix=".zip", delete=False)
    tmp_path = Path(handle.name)
    handle.close()
    try:
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "meine-welt.json",
                json.dumps(snapshot, indent=2, ensure_ascii=False),
            )
            for row in snapshot["media"]:
                try:
                    path = media.path_for(row["storage_key"])
                except FileNotFoundError:
                    continue
                suffix = path.suffix.lower()
                archive.write(path, arcname=f"medien/{row['token']}{suffix}")
        return FileResponse(
            tmp_path,
            media_type="application/zip",
            filename="karo-meine-welt-export.zip",
            headers={"Cache-Control": "private, no-store"},
            background=BackgroundTask(lambda: tmp_path.unlink(missing_ok=True)),
        )
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


@router.post("/eltern/alles-loeschen", dependencies=[Depends(parent_only)])
async def parent_delete_all(request: Request):
    form = await request.form()
    if str(form.get("confirm") or "").strip() != "ALLES LÖSCHEN":
        return _view(
            request, "parent", status_code=400,
            export_ready=bool(store.export_snapshot()["entries"] or store.export_snapshot()["capsules"]),
            error="Bitte exakt „ALLES LÖSCHEN“ eingeben.",
        )
    rows = store.delete_everything()
    _remove_media_rows(rows)
    flash(request, "Alle Daten aus Meine Welt wurden gelöscht und die Freigabe entfernt.")
    return RedirectResponse("/welten/eltern", status_code=HTTP_303_SEE_OTHER)
