"""HTTP adapter for the weekly agreement pilot, protected by Gate and role checks."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from .. import config, db
from ..routers.shared import render, flash, zurueck
from . import pilot as rules, pilot_store as store


def authorized(request: Request):
    if not request.session.get('auth') or request.session.get('role') not in ('parent', 'child'):
        raise HTTPException(403, 'Bitte anmelden.')
    # There is one configured child, no selectable child identity in this installation.
    if 'child_id' in request.query_params or 'kind_id' in request.query_params:
        raise HTTPException(403, 'Dieses Kind ist nicht verfügbar.')


def parent(request: Request):
    if request.session.get('role') != 'parent':
        raise HTTPException(403, 'Das ist ein Eltern-Bereich.')


router = APIRouter(prefix='/woche', dependencies=[Depends(authorized)])


def number(data, key):
    try:
        return int(data.get(key, ''))
    except (TypeError, ValueError):
        raise ValueError('Das Formular ist unvollständig. Bitte neu laden.') from None


async def form(request):
    data = await request.form()
    if 'child_id' in data or 'kind_id' in data:
        raise HTTPException(403, 'Dieses Kind ist nicht verfügbar.')
    return data


def transient(request, plan):
    saved = request.session.get('woche_day', {})
    key = f"{plan['id']}:{plan['revision']}:{rules.today()}" if plan else ''
    if saved.get('key') == key:
        return saved
    request.session.pop('woche_day', None)
    return {'key': key, 'hidden': [], 'easier': []}


def page(request, status_code=200, **extra):
    plan = store.get()
    state = transient(request, plan)
    helps = store.helps(plan['id']) if plan else []
    action = rules.next_action(plan, store.feedback(plan) if plan else set(), helps, state['hidden'])
    return render(request, 'woche/pilot_child.html', status_code=status_code,
                  plan=plan, action=action, helps=helps, older_helps=[h for h in store.helps() if not plan or h['plan_id'] != plan['id']],
                  hidden=state['hidden'], easier=state['easier'],
                  day=str(rules.today()), limits=rules.LIMITS, days=rules.DAYS, help_kinds=rules.HELP, statuses=rules.STATUS, **extra)


def error(request, exc, adult=False, **ctx):
    status = 409 if isinstance(exc, store.Conflict) else 404 if isinstance(exc, LookupError) else 400
    if adult:
        return edit_page(request, status_code=status, error=str(exc), **ctx)
    return page(request, status_code=status, error=str(exc))


@router.get('')
def child_page(request: Request):
    return page(request)


def edit_page(request, week=None, draft=None, status_code=200, **extra):
    week = week or rules.monday()
    plan = store.get(week)
    return render(request, 'woche/pilot_parent.html', status_code=status_code, adult_page=True,
                  plan=plan, values=draft or plan or {}, week=str(week), next_week=str(rules.monday()+timedelta(days=7)),
                  days=rules.DAYS, limits=rules.LIMITS, suggestions=rules.suggestions(config.load().learner_grade),
                  previous=store.get(rules.monday()-timedelta(days=7)),
                  summary=store.parent_summary(), help_kinds=rules.HELP, statuses=rules.STATUS,
                  response_status=status_code, **extra)


@router.get('/eltern', dependencies=[Depends(parent)])
def parent_page(request: Request, week: str = '', copy: int | None = None):
    try:
        target = rules.week(week) if week else rules.monday()
        if target not in (rules.monday(), rules.monday()+timedelta(days=7)):
            raise ValueError('Hier können Sie diese oder nächste Woche vereinbaren.')
        draft = store.by_id(copy) if copy is not None else None
        if draft and target != rules.week(draft['week']) + timedelta(days=7):
            raise ValueError('Übernehmen ist für die folgende Woche möglich.')
        return edit_page(request, target, draft if not store.get(target) else None)
    except (ValueError, LookupError) as exc:
        return error(request, exc, adult=True)


@router.post('/eltern/plan', dependencies=[Depends(parent)])
async def save_plan(request: Request):
    data = await form(request)
    target = rules.monday()
    try:
        target = rules.week(str(data.get('week', '')))
        if target not in (rules.monday(), rules.monday()+timedelta(days=7)):
            raise ValueError('Diese Woche kann nicht mehr bearbeitet werden.')
        values = rules.agreement(data, data.getlist('days'))
        store.save(target, values, number(data, 'version'))
        flash(request, 'Die gemeinsam besprochene Vereinbarung ist gespeichert.')
        return zurueck('/woche/eltern?week='+str(target))
    except (ValueError, LookupError) as exc:
        draft = dict(data)
        draft['days'] = ','.join(data.getlist('days'))
        # On conflicts require an explicit reload, rather than retrying with a fresh version.
        return error(request, exc, adult=True, week=target, draft=draft,
                     submitted_version=data.get('version', '0'))


def current(data):
    plan = store.by_id(number(data, 'plan_id'))
    if plan['week'] != str(rules.monday()):
        raise store.Conflict('Diese Woche ist vorbei. Bitte öffne die aktuelle Woche.')
    return plan


def activity_form(data, plan):
    activity = data.get('activity')
    if (data.get('day') != str(rules.today()) or number(data, 'revision') != plan['revision']):
        raise store.Conflict('Dieser Schritt hat sich geändert. Bitte neu laden.')
    if activity not in ('goal', 'routine') or not plan[activity]:
        raise ValueError('Dieser Schritt ist nicht verfügbar.')
    if plan['paused'] or (activity == 'goal' and plan['achieved']):
        raise ValueError('Dieser Schritt ist gerade pausiert oder abgeschlossen.')
    if activity == 'routine' and str(rules.today().isoweekday()) not in plan['days'].split(','):
        raise ValueError('Diese Routine steht heute nicht an.')
    return activity


@router.post('/aktivitaet')
async def activity(request: Request):
    if request.session['role'] != 'child':
        raise HTTPException(403, 'Für Rückmeldungen bitte den Kind-Modus verwenden.')
    data = await form(request)
    try:
        with db.tx():
            plan = current(data)
            selected = activity_form(data, plan)
            command = data.get('action')
            state = transient(request, plan)
            if command in ('start', 'difficult', 'help'):
                return page(request, panel=command, selected=selected, text=rules.step_text(plan, selected))
            if command == 'done':
                store.complete(plan, selected)
                flash(request, 'Du hast diesen Schritt als geschafft gemeldet. Du kannst freiwillig selbst weiterarbeiten.')
            elif command in ('skip', 'undo'):
                hidden = set(state['hidden'])
                hidden.add(selected) if command == 'skip' else hidden.discard(selected)
                state['hidden'] = sorted(hidden)
                request.session['woche_day'] = state
                flash(request, 'Für heute ausgeblendet. Du kannst dich umentscheiden.' if command == 'skip' else 'Du kannst wieder loslegen.')
            elif command == 'reason':
                reason = data.get('reason')
                if reason not in ('schwer', 'zeit', 'anfang', 'anders'):
                    raise ValueError('Bitte eine der Möglichkeiten auswählen.')
                rules.short(data, 'message')  # Optional private text is validated, never retained or forwarded.
                if reason == 'zeit':
                    state['hidden'] = sorted(set(state['hidden']) | {selected})
                    request.session['woche_day'] = state
                    flash(request, 'Für heute beendet. Es gibt nichts nachzuholen.')
                else:
                    simplified = reason in ('schwer', 'anfang') and selected not in state['easier']
                    if simplified:
                        state['easier'].append(selected)
                        request.session['woche_day'] = state
                    return page(request, panel='support', selected=selected,
                                text=rules.easier(rules.step_text(plan, selected)) if simplified else '', simplified=simplified)
            elif command == 'send_help':
                kind = data.get('kind')
                if kind not in rules.HELP or data.get('share') != 'ja':
                    raise ValueError('Bitte Hilfe auswählen und bestätigen, was deine Eltern sehen.')
                store.request_help(plan, selected, kind, rules.short(data, 'message'))
                flash(request, 'Deine Hilfeanfrage ist für deine Eltern sichtbar.')
            else:
                raise ValueError('Diese Aktion ist nicht verfügbar.')
        return zurueck('/woche')
    except (ValueError, LookupError) as exc:
        return error(request, exc)


@router.post('/status')
async def status(request: Request):
    data = await form(request)
    try:
        plan = current(data)
        command = data.get('action')
        mapping = {'pause': {'paused': 1}, 'resume': {'paused': 0},
                   'agree': {'child_status': 'passt'}, 'change': {'child_status': 'aendern'},
                   'achieved': {'achieved': 1}, 'unachieved': {'achieved': 0}}
        if command == 'review':
            feeling, wish = data.get('feeling'), data.get('wish')
            if feeling not in ('gut', 'mittel', 'schwierig') or wish not in ('lassen', 'leichter', 'anders') or data.get('together') != 'ja':
                raise ValueError('Bitte die gemeinsame Rückmeldung mit beiden Antworten bestätigen.')
            values = {'feeling': feeling, 'wish': wish}
        elif command in mapping:
            if command in ('achieved', 'unachieved') and not plan['goal']:
                raise ValueError('Es ist kein Wochenziel vereinbart.')
            values = mapping[command]
        else:
            raise ValueError('Diese Aktion ist nicht verfügbar.')
        if request.session['role'] == 'parent' and command not in ('pause', 'resume', 'review'):
            raise HTTPException(403, 'Diese Selbstauskunft gehört dem Kind. Bitte den Kind-Modus verwenden.')
        store.update(plan['id'], number(data, 'version'), values)
        flash(request, 'Deine Rückmeldung ist gespeichert.')
        return zurueck('/woche/eltern' if request.session['role'] == 'parent' else '/woche')
    except (ValueError, LookupError) as exc:
        return error(request, exc)


@router.post('/hilfe/{help_id}/zuruecknehmen')
async def cancel_help(request: Request, help_id: int):
    if request.session['role'] != 'child':
        raise HTTPException(403, 'Nur das Kind kann seine Hilfeanfrage zurücknehmen.')
    data = await form(request)
    try:
        store.help_update(help_id, number(data, 'version'), 'zurueckgenommen')
        flash(request, 'Deine Hilfeanfrage ist zurückgenommen.')
        return zurueck('/woche')
    except (ValueError, LookupError) as exc:
        return error(request, exc)


@router.post('/eltern/hilfe/{help_id}', dependencies=[Depends(parent)])
async def parent_help(request: Request, help_id: int):
    data = await form(request)
    try:
        status = data.get('status')
        if status not in ('zugesagt', 'erledigt'):
            raise ValueError('Bitte Unterstützung zusagen oder als erledigt markieren.')
        appointment = str(data.get('appointment', ''))
        if appointment:
            try:
                parsed = datetime.strptime(appointment, '%Y-%m-%dT%H:%M')
                if parsed.strftime('%Y-%m-%dT%H:%M') != appointment:
                    raise ValueError
            except ValueError:
                raise ValueError('Bitte einen gültigen Termin angeben.') from None
        store.help_update(help_id, number(data, 'version'), status, rules.short(data, 'reply'), appointment)
        flash(request, 'Die Hilfeantwort ist gespeichert.')
        return zurueck('/woche/eltern')
    except (ValueError, LookupError) as exc:
        return error(request, exc, adult=True)
