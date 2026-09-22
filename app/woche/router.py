"""Meine Plaene plus geschuetzte Kompatibilitaetsrouten des Wochen-Piloten."""
import calendar
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from .. import config, db
from ..routers.shared import render, flash, zurueck
from . import pilot as rules, pilot_store as store
from . import plaene, plaene_store as plan_store


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
    # Bereits vorhandene Pilotvereinbarungen bleiben lesbar. Eine frische
    # Installation und jedes neue Zeitziel verwenden die neue Plaene-Ansicht.
    legacy = db.q1("SELECT COUNT(*) AS n FROM woche_plan")
    if legacy and legacy["n"] and not plan_store.goals(("active", "paused", "completed", "archived")):
        return page(request)
    return today_page(request)


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


# ---------------------------------------------------------------------------
# Meine Plaene: alle Kennzahlen kommen aus plaene.py, nicht aus den Templates.
# ---------------------------------------------------------------------------

def _days(value: str) -> str:
    return " · ".join(plaene.WEEKDAY_LABELS[int(day)] for day in value.split(",") if day)


def _goal_view(item: dict, on: date) -> dict:
    rows = plan_store.sessions(item["id"])
    stats = plaene.goal_statistics(rows, on)
    future = next((row for row in rows if row["scheduled_date"] >= str(on) and row["status"] == "planned"), None)
    return {**item, **stats, "days_label": _days(item["weekdays"]), "next": future,
            "sessions": rows,
            "history": [row for row in rows if row["scheduled_date"] <= str(on)],
            "total_sessions": len(rows)}


def _overall(items: list[dict], on: date) -> dict:
    rows = [row for item in items for row in plan_store.sessions(item["id"])]
    return plaene.goal_statistics(rows, on)


def _plans_render(request: Request, template: str, **context):
    context.setdefault("plan_day", plaene.today())
    context.setdefault("weekday_labels", plaene.WEEKDAY_LABELS)
    context.setdefault("show_nav", False)
    return render(request, template, **context)


def today_page(request: Request):
    current = plaene.today()
    plan_store.mark_missed(current)
    active = plan_store.goals(("active",))
    today_rows = [row for row in plan_store.sessions(start=current, end=current) if row["goal_status"] == "active"]
    missed = [row for row in plan_store.sessions(end=current - timedelta(days=1))
              if row["status"] == "missed" and row["goal_status"] == "active"]
    selected = request.query_params.get("abschluss")
    completion_notice = request.query_params.get("hinweis") == "kind"
    selected_session = None
    if selected:
        try:
            selected_session = plan_store.session(int(selected))
        except (ValueError, LookupError):
            raise HTTPException(404, "Diese Einheit ist nicht verfügbar.")
    overall = _overall(active, current)
    return _plans_render(request, "woche/plaene_heute.html", goals=active,
                         sessions=today_rows, missed=missed, overall=overall,
                         motivation=plaene.motivation(overall),
                         selected_session=selected_session,
                         completion_notice=completion_notice)


@router.get('/woche')
def week_page(request: Request):
    current = plaene.today()
    plan_store.mark_missed(current)
    start, end = plaene.week_bounds(current)
    goal_rows = []
    for item in plan_store.goals(("active", "paused")):
        rows = plan_store.sessions(item["id"], start, end)
        goal_rows.append({**item, **plaene.goal_statistics(rows, current),
                          "rows": rows})
    all_rows = [row for item in goal_rows for row in item["rows"]]
    counts = {status: sum(row["status"] == status for row in all_rows)
              for status in ("completed", "planned", "missed", "made_up")}
    days = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        day_rows = [row for row in all_rows if row["scheduled_date"] == str(day)]
        if day_rows and all(row["status"] in ("completed", "made_up") for row in day_rows):
            state = "done"
        elif any(row["status"] == "missed" for row in day_rows):
            state = "missed"
        else:
            state = "open"
        days.append({"date": day, "state": state})
    summary = plaene.goal_statistics(all_rows, current)
    return _plans_render(request, "woche/plaene_woche.html", start=start, end=end,
                         days=days, goal_rows=goal_rows, summary=summary, counts=counts,
                         motivation=plaene.motivation(summary))


@router.get('/monat')
def month_page(request: Request, month: str = ""):
    current = plaene.today()
    plan_store.mark_missed(current)
    try:
        chosen = date.fromisoformat((month or current.strftime("%Y-%m")) + "-01")
    except ValueError:
        raise HTTPException(400, "Bitte einen gültigen Monat wählen.")
    start, end = plaene.month_bounds(chosen)
    goal_rows = []
    month_rows = []
    for item in plan_store.goals(("active", "paused", "completed")):
        rows = plan_store.sessions(item["id"], start, end)
        if rows:
            goal_rows.append({**item, **plaene.goal_statistics(rows, current)})
            month_rows.extend(rows)
    weeks, cursor = [], start
    while cursor <= end:
        week_end = min(end, cursor + timedelta(days=6-cursor.weekday()))
        rows = [row for row in plan_store.sessions(start=cursor, end=week_end)
                if row["goal_status"] in ("active", "paused", "completed")]
        weeks.append({"start": cursor, "end": week_end,
                      **plaene.goal_statistics(rows, current)})
        cursor = week_end + timedelta(days=1)
    previous = (start - timedelta(days=1)).strftime("%Y-%m")
    following = (end + timedelta(days=1)).strftime("%Y-%m")
    summary = plaene.goal_statistics(month_rows, current)
    return _plans_render(request, "woche/plaene_monat.html", chosen=chosen, start=start, end=end,
                         goal_rows=goal_rows, weeks=weeks, summary=summary,
                         motivation=plaene.motivation(summary),
                         previous=previous, following=following)


@router.get('/ziele')
def goals_page(request: Request):
    current = plaene.today()
    plan_store.mark_missed(current)
    active = [_goal_view(item, current) for item in plan_store.goals(("active", "paused", "completed"))]
    overall = _overall(active, current)
    return _plans_render(request, "woche/plaene_ziele.html", goals=active, overall=overall,
                         motivation=plaene.motivation(overall))


def _wizard_values(request: Request) -> dict:
    return dict(request.session.get("plan_wizard") or {})


def _wizard_summary(values: dict) -> dict | None:
    try:
        start = date.fromisoformat(values["start_date"])
        end = date.fromisoformat(values["end_date"]) if values["duration"] == "custom" else start + timedelta(days=int(values["duration"]) - 1)
        dates = plaene.schedule_dates(start, end, values["weekdays"])
        return {"start": start, "end": end, "count": len(dates),
                "total": len(dates) * int(values["minutes"]),
                "days": " · ".join(plaene.WEEKDAY_LABELS[int(day)] for day in values["weekdays"])}
    except (KeyError, TypeError, ValueError):
        return None


@router.get('/ziele/neu')
def wizard_page(request: Request, step: int = 1):
    if step not in range(1, 6):
        step = 1
    values = _wizard_values(request)
    return _plans_render(request, "woche/plaene_wizard.html", step=step, values=values,
                         wizard_summary=_wizard_summary(values))


@router.post('/ziele/neu')
async def wizard_save(request: Request):
    data = await form(request)
    values = _wizard_values(request)
    try:
        step = number(data, "step")
        if step == 1:
            statement = " ".join(str(data.get("statement", "")).split())
            if not statement or len(statement) > 180:
                raise ValueError("Bitte beschreibe dein Ziel in einem kurzen Satz.")
            values["statement"] = statement
        elif step == 2:
            try:
                start = date.fromisoformat(str(data.get("start_date", "")))
            except ValueError:
                raise ValueError("Bitte wähle ein gültiges Startdatum.") from None
            if start < plaene.today():
                raise ValueError("Das Startdatum darf nicht vor heute liegen.")
            duration = str(data.get("duration", ""))
            if duration not in ("7", "14", "28", "90", "custom"):
                raise ValueError("Bitte wähle einen Zeitraum.")
            values["start_date"] = str(start)
            values["duration"] = duration
            if duration == "custom":
                try:
                    end = date.fromisoformat(str(data.get("end_date", "")))
                except ValueError:
                    raise ValueError("Bitte wähle ein gültiges Enddatum.") from None
                if end < start:
                    raise ValueError("Das Enddatum liegt vor dem Start.")
                values["end_date"] = str(end)
        elif step == 3:
            values["weekdays"] = list(map(str, plaene.parse_weekdays(data.getlist("weekdays"))))
        elif step == 4:
            minutes = number(data, "minutes")
            if not 1 <= minutes <= 60:
                raise ValueError("Bitte wähle 1 bis 60 Minuten.")
            values["minutes"] = minutes
        elif step == 5:
            required = ("statement", "start_date", "duration", "weekdays", "minutes")
            if any(key not in values for key in required):
                raise ValueError("Der Plan ist noch nicht vollständig.")
            start = date.fromisoformat(values["start_date"])
            if start < plaene.today():
                raise ValueError("Das Startdatum darf nicht vor heute liegen.")
            end = date.fromisoformat(values["end_date"]) if values["duration"] == "custom" else start + timedelta(days=int(values["duration"]) - 1)
            goal_id = plan_store.create_goal(values["statement"], start, end, int(values["minutes"]), values["weekdays"])
            request.session.pop("plan_wizard", None)
            flash(request, "Dein Plan ist fertig. Los geht’s!")
            return zurueck(f"/woche/ziele/{goal_id}")
        else:
            raise ValueError("Dieser Schritt ist nicht verfügbar.")
        request.session["plan_wizard"] = values
        return zurueck(f"/woche/ziele/neu?step={step + 1}")
    except (ValueError, KeyError) as exc:
        return _plans_render(request, "woche/plaene_wizard.html", status_code=400,
                             step=max(1, min(5, int(data.get("step", 1) or 1))), values={**values, **dict(data)},
                             wizard_summary=_wizard_summary(values), error=str(exc))


@router.post('/sitzung/{session_id}/abschluss')
async def finish_session(request: Request, session_id: int):
    if request.session.get("role") != "child":
        return zurueck(f"/woche?abschluss={session_id}&hinweis=kind")
    data = await form(request)
    try:
        actual = number(data, "actual_minutes")
        plan_store.complete(session_id, actual, number(data, "focus_percent"))
        flash(request, "Deine Lernzeit ist gespeichert." if actual else "Die Einheit wurde mit 0 Minuten gespeichert.")
        return zurueck("/woche")
    except (ValueError, LookupError) as exc:
        flash(request, str(exc), "err")
        return zurueck(f"/woche?abschluss={session_id}")


@router.post('/ziele/{goal_id}/start')
async def start_goal(request: Request, goal_id: int):
    await form(request)
    try:
        session_id = plan_store.start_session(goal_id, plaene.today())
        return zurueck(f"/woche?abschluss={session_id}")
    except (ValueError, LookupError) as exc:
        flash(request, str(exc), "err")
        return zurueck(f"/woche/ziele/{goal_id}")


@router.get('/ziele/{goal_id}')
def goal_detail(request: Request, goal_id: int, month: str = ""):
    current = plaene.today()
    plan_store.mark_missed(current)
    item = _goal_view(plan_store.goal(goal_id), current)
    try:
        selected = plaene.selected_goal_month(
            date.fromisoformat(item["start_date"]),
            date.fromisoformat(item["end_date"]), current, month)
        calendar_view = plaene.goal_calendar(item["sessions"], selected)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    return _plans_render(request, "woche/plaene_detail.html", goal=item,
                         motivation=plaene.motivation(item),
                         goal_calendar=calendar_view)


@router.post('/ziele/{goal_id}/bearbeiten')
async def edit_goal(request: Request, goal_id: int):
    data = await form(request)
    try:
        plan_store.update_future(goal_id, str(data.get("statement", "")),
                                 date.fromisoformat(str(data.get("end_date", ""))),
                                 number(data, "minutes"), data.getlist("weekdays"), plaene.today() + timedelta(days=1))
        flash(request, "Dein Ziel ist angepasst. Vergangene Einheiten bleiben unverändert.")
    except (ValueError, LookupError) as exc:
        flash(request, str(exc), "err")
    return zurueck(f"/woche/ziele/{goal_id}")


@router.post('/ziele/{goal_id}/aktion')
async def goal_action(request: Request, goal_id: int):
    data = await form(request)
    action = str(data.get("action", ""))
    try:
        mapping = {"pause": "paused", "resume": "active", "restore": "active",
                   "complete": "completed", "archive": "archived"}
        if action in mapping:
            plan_store.set_status(goal_id, mapping[action])
        elif action == "delete" and data.get("confirm") == "yes":
            plan_store.delete(goal_id)
            flash(request, "Das Ziel wurde gelöscht.")
            return zurueck("/woche/ziele")
        elif action == "repeat":
            new_id = plan_store.repeat(goal_id, plaene.today())
            flash(request, "Das Ziel ist wieder als neuer Plan da.")
            return zurueck(f"/woche/ziele/{new_id}")
        else:
            raise ValueError("Bitte bestätige diese Aktion.")
        flash(request, "Dein Ziel wurde aktualisiert.")
        return zurueck("/woche/schatzkiste" if action == "archive" else f"/woche/ziele/{goal_id}")
    except (ValueError, LookupError) as exc:
        flash(request, str(exc), "err")
        return zurueck(f"/woche/ziele/{goal_id}")


@router.get('/schatzkiste')
def treasure_page(request: Request):
    current = plaene.today()
    archived = [_goal_view(item, current) for item in plan_store.goals(("archived",))]
    overall = _overall(archived, current)
    return _plans_render(request, "woche/plaene_schatzkiste.html", goals=archived,
                         motivation=plaene.motivation(overall))
