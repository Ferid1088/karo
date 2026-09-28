"""Post von zu Hause: Eltern schreiben aus dem Bericht, das Kind liest und antwortet.

Reine HTTP-Schicht; Regeln und SQL liegen in `services/family_post.py`.
/eltern/... ist Elternsache (Gate), /post gehört zum Kinderbereich.
"""
from urllib.parse import urlsplit

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from .. import config
from ..services import family_post
from .shared import flash, render, zurueck

router = APIRouter()


def _back(target: str) -> str:
    """Nur zurück in den Elternbereich derselben Seite, nie auf fremde Adressen."""
    parts = urlsplit(target or '')
    if parts.scheme or parts.netloc or not parts.path.startswith('/eltern'):
        return '/eltern'
    return parts.path + ('?' + parts.query if parts.query else '')


def _name() -> str:
    return getattr(config.load_safe(), 'learner_name', '') or 'Ihr Kind'


@router.post('/eltern/post')
def post_senden(request: Request, text: str = Form(''), vorschlag: str = Form(''),
                emoji: str = Form(''), art: str = Form('nachricht'), zurueck_zu: str = Form('/eltern')):
    try:
        if art not in ('nachricht', 'ueberraschung'):
            raise family_post.PostError('Bitte Nachricht oder Überraschung wählen.')
        family_post.send(text.strip() or vorschlag, emoji, art)
        flash(request, f'Ihre {"Überraschung" if art == "ueberraschung" else "Nachricht"} ist unterwegs zu {_name()}.')
    except family_post.PostError as exc:
        flash(request, str(exc), 'err')
    return zurueck(_back(zurueck_zu))


@router.post('/eltern/post/{message_id}/zurueckziehen')
def post_zurueckziehen(request: Request, message_id: int, zurueck_zu: str = Form('/eltern')):
    try:
        family_post.withdraw(message_id)
        flash(request, 'Die Nachricht ist zurückgezogen.')
    except family_post.PostError as exc:
        flash(request, str(exc), 'err')
    return zurueck(_back(zurueck_zu))


@router.post('/eltern/post/feier/{goal_id}')
def post_feier(request: Request, goal_id: int, zurueck_zu: str = Form('/eltern')):
    try:
        family_post.celebrate(goal_id)
        flash(request, f'Zugesagt! {_name()} findet die Nachricht im Postfach.')
    except family_post.PostError as exc:
        flash(request, str(exc), 'err')
    return zurueck(_back(zurueck_zu))


@router.get('/post', response_class=HTMLResponse)
def postfach(request: Request):
    messages = family_post.inbox()
    fresh = {m['id'] for m in messages if not m['read_at']}
    if request.session.get('role') == 'child':
        family_post.mark_read(sorted(fresh))  # Eltern, die mitlesen, lösen kein "gelesen" aus
    return render(request, 'post.html', messages=messages, fresh=fresh,
                  reactions=family_post.CHILD_REACTIONS)


@router.post('/post/{message_id}/antwort')
def post_antwort(request: Request, message_id: int, antwort: str = Form('')):
    if request.session.get('role') != 'child':
        flash(request, 'Antworten kann nur dein Kind – im Kinderbereich.', 'err')
        return zurueck('/post')
    try:
        family_post.react(message_id, antwort)
        flash(request, 'Deine Antwort ist angekommen.')
    except family_post.PostError as exc:
        flash(request, str(exc), 'err')
    return zurueck(f'/post#post-{message_id}')
