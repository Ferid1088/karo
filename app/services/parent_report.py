"""Read-only parent reporting. Observations, self-reports and plans never mix.

No inferred timers, generated content, private reflections, focus ratings, or
mutations. Calendar boundaries use the same local timezone as Ziele planen.
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from .. import config, db, faecher
from ..adaptiv import store as learning_store
from ..woche import plaene, plaene_store

MODES = {'monat': 'Lernmonat', 'woche': 'Lernwoche', 'tag': 'Lerntag'}
ANSWER_EVENTS = {'Antwort richtig': True, 'Fehlertyp erkannt': False,
                 'Lehrrunde ohne Erfolg': False, 'Fehler nicht im Katalog': False}
ACTIVE_EVENTS = set(ANSWER_EVENTS) | {'Anker beantwortet', 'Vorhersage abgegeben', 'Tipp angefordert'}
# Traffic-light levels for the at-a-glance overview. 'off' means "no evidence",
# never a failure: missing reports are not judged. Only an exam that is close
# and mostly unprepared may turn red.
LEVELS = ('off', 'good', 'warn', 'crit')
HEADS = {'monat': ('Guter Monat', 'Gemischter Monat'), 'woche': ('Gute Woche', 'Gemischte Woche'),
         'tag': ('Guter Lerntag', 'Gemischter Tag')}


def _zone() -> ZoneInfo:
    return ZoneInfo(getattr(config.load_safe(), 'timezone', None) or 'Europe/Berlin')


def local_day(stamp: str | None) -> date | None:
    if not stamp:
        return None
    try:
        if len(stamp) == 10:
            return date.fromisoformat(stamp)
        parsed = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).astimezone(_zone()).date()
    except (ValueError, TypeError):
        return None


def _utc(day: date) -> str:
    return datetime.combine(day, time.min, _zone()).astimezone(timezone.utc).isoformat()


def _date(raw: str, fallback: date) -> date:
    try:
        value = date.fromisoformat(raw) if raw else fallback
        if not date(2000, 1, 1) <= value <= date(2100, 12, 31):
            raise ValueError
        return value
    except (ValueError, TypeError):
        raise ValueError('Bitte ein gültiges Datum zwischen 2000 und 2100 wählen.') from None


def link(mode: str, day: date, back: str = '', base: date | None = None) -> str:
    args = {'ansicht': mode, 'datum': day.isoformat()}
    if back:
        args.update(zurueck=back, basis=(base or day).isoformat())
    return '/eltern?' + urlencode(args)


def _days(start: date, end: date):
    for offset in range((end - start).days + 1):
        yield start + timedelta(days=offset)


def _worst(levels) -> str:
    return max(levels, key=LEVELS.index, default='off')


def _heat(answers: int, active: bool) -> int:
    """Calendar shade from rated answers; activity without answers stays visible."""
    if not answers:
        return 1 if active else 0
    return 1 if answers < 5 else 2 if answers < 10 else 3 if answers < 20 else 4


def exam_verdict(total: int, safe: int, practicing: int, days: int) -> dict:
    """Plain-language readiness from stored mastery, not a predicted grade."""
    if days < 0:
        return {'level': 'off', 'text': 'Vorbei'}
    if not total:
        return {'level': 'warn', 'text': 'Themen fehlen'}
    ready = (safe + .5 * practicing) / total
    if ready >= .75:
        return {'level': 'good', 'text': 'Auf Kurs'}
    if days > 14:
        return {'level': 'off', 'text': 'Noch Zeit'}
    if ready >= .4 or days > 7:
        return {'level': 'warn', 'text': 'Knapp'}
    return {'level': 'crit', 'text': 'Wenig Zeit'}


def build(mode: str = 'monat', raw_date: str = '', back: str = 'monat', base: str = '') -> dict:
    if mode not in MODES or back not in ('monat', 'woche'):
        raise ValueError('Bitte Monat, Woche oder Tag auswählen.')
    today = plaene.today()
    anchor = _date(raw_date, today)
    base_date = _date(base, anchor)
    month_start = anchor.replace(day=1)
    month_end = anchor.replace(day=calendar.monthrange(anchor.year, anchor.month)[1])
    if mode == 'monat':
        start, end = month_start, month_end
        previous = (month_start - timedelta(days=1)).replace(day=1)
        following = (month_end + timedelta(days=1))
    elif mode == 'woche':
        start = anchor - timedelta(days=anchor.weekday())
        end = start + timedelta(days=6)
        previous, following = anchor - timedelta(days=7), anchor + timedelta(days=7)
    else:
        start = end = anchor
        previous, following = anchor - timedelta(days=1), anchor + timedelta(days=1)
    week_start = anchor - timedelta(days=anchor.weekday())
    window_start = min(start, month_start, week_start)
    window_end = max(end, month_end, week_start + timedelta(days=6))
    cutoff_day = min(end, today)
    cutoff = _utc(cutoff_day + timedelta(days=1))
    observation_end = _utc(min(window_end, today) + timedelta(days=1))

    # No inspection of content libraries or seeding as a side effect of a report.
    topics = {r['id']: dict(r) for r in db.q(f'''SELECT id, subject, label,
        learning_visible, created_at FROM topic WHERE subject IN {faecher.SQL_FAECHER}
        AND state='aktiv' AND deleted_at IS NULL AND purged_at IS NULL AND merged_into IS NULL''')}
    exams = {r['id']: dict(r) for r in db.q(f'''SELECT id,subject,exam_date,titel,created_at
        FROM exam WHERE deleted_at IS NULL AND purged_at IS NULL
        AND subject IN {faecher.SQL_FAECHER}''')}
    owners = defaultdict(set)
    for row in db.q('SELECT exam_id,topic_id FROM exam_topic'):
        owners[row['topic_id']].add(row['exam_id'])
    for topic_id in list(topics):
        t = topics[topic_id]
        owned = owners[topic_id]
        if t['learning_visible'] and not owned:
            t['scope'], t['exam_id'] = 'personal', None
        elif not t['learning_visible'] and len(owned) == 1 and next(iter(owned)) in exams:
            t['scope'], t['exam_id'] = 'exam', next(iter(owned))
        else:
            del topics[topic_id]  # Ambiguous legacy ownership is not cross-attributed.

    daily = defaultdict(lambda: {'answers': [], 'active': set(), 'checks': [],
                                  'goals': [], 'plans': [], 'exams': []})
    first_mastery = {}
    for event in learning_store.parent_report_events(_utc(window_start), observation_end):
        t = topics.get(event['topic_id'])
        day = local_day(event['created_at'])
        if not t or day is None or day > today:
            continue
        if event['nach_zustand'] == 'MASTERED':
            first_mastery[t['id']] = min(first_mastery.get(t['id'], day), day)
        if window_start <= day <= window_end:
            if event['anlass'] in ACTIVE_EVENTS or event['nach_zustand'] == 'MASTERED':
                daily[day]['active'].add(t['id'])
            if event['anlass'] in ANSWER_EVENTS:
                daily[day]['answers'].append({'topic': t, 'right': ANSWER_EVENTS[event['anlass']]})
    for topic_id, first in first_mastery.items():
        if window_start <= first <= window_end:
            daily[first]['checks'].append(topics[topic_id])

    # Latest approved answer per question as of the report window. Revisions are
    # not additional attempts. Never count unapproved model suggestions.
    for row in db.q('''SELECT a.topic_id,a.beantwortet_am,a.richtig FROM answer_log a
        WHERE a.id=(SELECT MAX(b.id) FROM answer_log b WHERE b.question_id=a.question_id
                    AND julianday(b.created_at)<julianday(?))''', cutoff):
        t, day = topics.get(row['topic_id']), local_day(row['beantwortet_am'])
        if t and day and window_start <= day <= min(window_end, today):
            daily[day]['answers'].append({'topic': t, 'right': bool(row['richtig'])})
            daily[day]['active'].add(t['id'])

    sessions, completions = plaene_store.parent_report_rows()
    session_map = {s['id']: s for s in sessions}
    reported = {c['planned_session_id'] for c in completions
                if (d := local_day(c['completed_at'])) is not None and d <= min(today, window_end)}
    goal_stats = {}
    def goal_row(s):
        return goal_stats.setdefault(s['goal_id'], {'id': s['goal_id'], 'label': s['statement'],
            'planned': 0, 'planned_minutes': 0, 'reports': 0, 'minutes': 0, 'makeups': 0,
            'sessions': []})
    for s in sessions:
        day = local_day(s['scheduled_date'])
        if day is None or s['status'] == 'cancelled':
            continue
        if window_start <= day <= window_end:
            daily[day]['plans'].append(s)
        if start <= day <= end:
            g = goal_row(s)
            g['planned'] += 1
            g['planned_minutes'] += s['planned_minutes']
            done = day <= today and (s['id'] in reported or s['status'] in ('completed', 'made_up'))
            g['sessions'].append({'date': day.isoformat(), 'minutes': s['planned_minutes'],
                'label': f"{plaene.WEEKDAY_LABELS[day.isoweekday()]} {day:%d.%m.}",
                'state': 'done' if done else 'planned' if day > today else 'open' if day == today else 'missed',
                'href': link('tag', day, back if mode == 'tag' else mode, base_date if mode == 'tag' else anchor)})
    for c in completions:
        s, day = session_map.get(c['planned_session_id']), local_day(c['completed_at'])
        if not s or day is None or day > today:
            continue
        if window_start <= day <= window_end:
            daily[day]['goals'].append({**c, 'label': s['statement'], 'goal_id': s['goal_id']})
        if start <= day <= end:
            g = goal_row(s)
            g['reports'] += 1
            g['minutes'] += c['actual_minutes']
            g['makeups'] += c['is_makeup']

    for r in db.q('SELECT exam_id,study_date,minutes FROM exam_schedule_day WHERE minutes>0'):
        if r['exam_id'] in exams and (day := local_day(r['study_date'])) and window_start <= day <= window_end:
            daily[day]['exams'].append({'id': r['exam_id'], 'minutes': r['minutes'],
                                        'subject': exams[r['exam_id']]['subject']})
    for exam in exams.values():
        day = local_day(exam['exam_date'])
        if day and window_start <= day <= window_end:
            daily[day]['exams'].append({'id': exam['id'], 'minutes': 0, 'subject': exam['subject'], 'exam_day': True})

    selected = [daily[d] for d in _days(start, end)]
    answers = [a for d in selected for a in d['answers']]
    checks = [t for d in selected for t in d['checks'] if t['scope'] == 'personal']
    personal_answers = [a for a in answers if a['topic']['scope'] == 'personal']
    subject_rows = []
    for subject in faecher.FAECHER:
        a = [r for r in personal_answers if r['topic']['subject'] == subject]
        subject_rows.append({'key': subject, 'name': faecher.NAMEN[subject], 'answers': len(a),
            'right': sum(r['right'] for r in a), 'secure': sum(t['subject'] == subject for t in checks)})

    states = learning_store.parent_report_states(cutoff)
    # Show the actual topics behind the counts, not an inferred school grade.
    worked_ids = set().union(*(d['active'] for d in selected))
    topic_rows = []
    for tid in worked_ids:
        t = topics[tid]
        attempted = [a for a in answers if a['topic']['id'] == tid]
        topic_rows.append({**t, 'answers': len(attempted),
            'right': sum(a['right'] for a in attempted),
            'retry': sum(not a['right'] for a in attempted),
            'safe': states.get(tid) == 'MASTERED'})
    topic_rows.sort(key=lambda t: (-t['answers'], t['label'], t['id']))
    order = ('sicher', 'uebt', 'offen')
    # Practised in the window counts as "übt noch" even without an adaptive state (e.g. quiz answers).
    seen = set().union(*(daily[d]['active'] for d in list(daily) if d <= cutoff_day))
    def topic_state(tid):
        state = states.get(tid)
        return 'sicher' if state == 'MASTERED' else 'uebt' if state or tid in seen else 'offen'
    for row in subject_rows:
        row['topics'] = [t for t in topic_rows if t['scope'] == 'personal' and t['subject'] == row['key']]
        row['percent'] = round(row['right'] / row['answers'] * 100) if row['answers'] else None
        row['ten'] = round(row['right'] / row['answers'] * 10) if row['answers'] else None
        known = [t for t in topics.values() if t['scope'] == 'personal' and t['subject'] == row['key']
                 and (local_day(t['created_at']) or cutoff_day) <= cutoff_day]
        row['mastery'] = sorted((topic_state(t['id']) for t in known), key=order.index)
        row['mastery_rows'] = sorted(({'label': t['label'], 'state': topic_state(t['id'])} for t in known),
                                     key=lambda r: (order.index(r['state']), r['label']))
        row['safe_total'] = row['mastery'].count('sicher')
    exam_rows = []
    for e in exams.values():
        created, exam_day = local_day(e['created_at']), local_day(e['exam_date'])
        if not created or created > cutoff_day or not exam_day or exam_day < start:
            continue
        et = [t for t in topics.values() if t['exam_id'] == e['id']
              and (local_day(t['created_at']) or cutoff_day) <= cutoff_day]
        safe = sum(states.get(t['id']) == 'MASTERED' for t in et)
        practicing = sum(topic_state(t['id']) == 'uebt' for t in et)
        days_left = (exam_day-cutoff_day).days
        exam_rows.append({**e, 'total': len(et), 'safe': safe, 'percent': round(safe/len(et)*100) if et else 0,
            'days': days_left, 'date_label': exam_day.strftime('%d.%m.'),
            'weekday': plaene.WEEKDAY_LABELS[exam_day.isoweekday()], 'practicing': practicing,
            'verdict': exam_verdict(len(et), safe, practicing, days_left),
            'topic_rows': sorted(({'label': t['label'], 'state': topic_state(t['id'])} for t in et),
                                 key=lambda r: (order.index(r['state']), r['label'])),
            'answers': sum(a['topic']['exam_id'] == e['id'] for a in answers)})
    exam_rows.sort(key=lambda e: (e['days'] < 0, e['exam_date'], e['id']))

    groups = []
    if mode == 'monat':
        for d in _days(start, end):
            if d == start or d.weekday() == 0:
                groups.append({'start': d, 'end': min(d+timedelta(days=6-d.weekday()), end)})
    elif mode == 'woche':
        groups = [{'start': d, 'end': d} for d in _days(start, end)]
    for g in groups:
        group_answers = [a for d in _days(g['start'],g['end']) for a in daily[d]['answers']]
        g.update(total=len(group_answers), label=(f"{g['start'].day}–{g['end'].day}" if mode=='monat'
                 else f"{plaene.WEEKDAY_LABELS[g['start'].isoweekday()]} {g['start'].day}"),
                 href=link('woche',g['start']) if mode=='monat' else link('tag',g['start'],'woche',anchor),
                 values=[{'key': s, 'value': sum(a['topic']['subject']==s for a in group_answers)} for s in faecher.FAECHER])
        records = [daily[d] for d in _days(g['start'], g['end'])]
        g.update(right=sum(a['right'] for a in group_answers),
                 checks=sum(len(d['checks']) for d in records),
                 goal_minutes=sum(c['actual_minutes'] for d in records for c in d['goals']),
                 exam_minutes=sum(e['minutes'] for d in records for e in d['exams']),
                 future=g['start'] > today)
        g['percent'] = round(g['right'] / g['total'] * 100) if g['total'] else None
        for v in g['values']:
            v['right'] = sum(a['right'] for a in group_answers if a['topic']['subject'] == v['key'])
            v['retry'] = v['value'] - v['right']
    ceiling = max([g['total'] for g in groups]+[1])
    ceiling += ceiling % 2  # Integer axis ticks for counts, never half an answer.
    for g in groups:
        for v in g['values']:
            v['height'] = round(v['value']/ceiling*100, 4)
            v['retry_height'] = round(v['retry']/v['value']*100, 4) if v['value'] else 0

    right = sum(a['right'] for a in answers)
    all_checks = [t for d in selected for t in d['checks']]
    needs_practice = [t for t in topic_rows if t['retry'] and not t['safe']]
    needs_practice.sort(key=lambda t: (-t['retry'], t['label']))
    if start > today:
        insights = [
            {'tone': 'blue', 'title': 'Der Zeitraum liegt vor uns', 'text': 'Hier sehen Sie die gespeicherte Planung. Aktivitäten erscheinen erst, wenn sie erfasst wurden.'},
            {'tone': 'green', 'title': 'Noch keine Ergebnisse', 'text': 'Geplante Minuten und Termine sind keine erledigten Lernschritte.'},
            {'tone': 'amber', 'title': 'Gemeinsam vorbereiten', 'text': 'Passen die geplanten Tage gut in den Alltag Ihres Kindes?'}]
    else:
        def topic_label(t):
            return t['label'] + (' (Prüfung)' if t['scope'] == 'exam' else ' (eigenes Thema)')
        labels = ', '.join(topic_label(t) for t in topic_rows[:2])
        success = ', '.join(topic_label(t) for t in all_checks[:2])
        next_exam = next((e for e in exam_rows if 0 <= e['days'] <= 7 and e['safe'] < e['total']), None)
        if next_exam:
            next_title = 'Prüfung steht bevor'
            next_text = f"{faecher.NAMEN[next_exam['subject']]} am {next_exam['date_label']}: {next_exam['total'] - next_exam['safe']} Prüfungsthemen noch nicht sicher. Lernplan gemeinsam ansehen."
        elif needs_practice:
            t = needs_practice[0]
            next_title = 'Hier lohnt sich ein Blick'
            next_text = f"{t['label']}: {t['retry']} von {t['answers']} Antworten noch nicht richtig. Fragen Sie, welcher Schritt schwierig war."
        else:
            next_title = 'Im Gespräch bleiben'
            next_text = 'Fragen Sie: Was kannst du jetzt besser erklären?' if worked_ids else 'Noch keine Lernaktivität erfasst. Fragen Sie, womit Ihr Kind beginnen möchte.'
        insights = [
            {'tone': 'blue', 'title': f'{len(worked_ids)} Themen bearbeitet', 'text': labels + (' und weitere.' if len(topic_rows) > 2 else '.') if labels else 'Noch keine Themenaktivität erfasst. Zielmeldungen werden separat angezeigt.'},
            {'tone': 'green', 'title': f'{len(all_checks)} Lernchecks erstmals bestanden', 'text': success + (' und weitere.' if len(all_checks) > 2 else '.') if success else 'Noch kein erster bestandener Lerncheck im Zeitraum. Üben ist bereits ein wichtiger Schritt.'},
            {'tone': 'amber', 'title': next_title, 'text': next_text}]

    calendar_days = []
    for d in _days(month_start,month_end):
        data = daily[d]
        activity = bool(data['active'] or data['goals'])
        planned = bool(data['plans'] or data['exams'])
        calendar_days.append({'day':d.day,'iso':d.isoformat(),'today':d==today,'selected':mode=='tag' and d==anchor,
            'in_range':start<=d<=end,'active':activity,'planned':planned,
            'checks':bool(data['checks']), 'answers':len(data['answers']),
            'label':f"{d.strftime('%d.%m.%Y')}: {len(data['answers'])} Antworten, {len(data['goals'])} Zielmeldungen"+(', Planung vorhanden' if planned else ''),
            'href':link('tag',d,back if mode=='tag' else mode,base_date if mode=='tag' else anchor)})
    day_items = []
    if mode == 'tag':
        current = daily[anchor]
        for tid in sorted(current['active']):
            t=topics[tid]
            a=[r for r in current['answers'] if r['topic']['id']==tid]
            day_items.append({'label':t['label'],'kind':('Prüfungsvorbereitung' if t['scope']=='exam' else 'Eigenes Thema')+' · '+faecher.NAMEN[t['subject']],
                'value':f"{sum(x['right'] for x in a)}/{len(a)} richtig" if a else 'Aktivität',
                'note':'Lerncheck erstmals bestanden' if t in current['checks'] else ''})
        for g in current['goals']:
            day_items.append({'label':g['label'],'kind':'Ziele planen · Selbstauskunft',
                              'value':f"{g['actual_minutes']} Min. gemeldet",'note':'Nachgeholt' if g['is_makeup'] else ''})
        for s in current['plans']:
            day_items.append({'label':s['statement'],'kind':'Zielplanung', 'value':f"{s['planned_minutes']} Min. geplant",'note':''})
        for e in current['exams']:
            day_items.append({'label':faecher.NAMEN[e['subject']], 'kind':'Klassenarbeit' if e.get('exam_day') else 'Prüfungsvorbereitung',
                              'value':'Prüfungstag' if e.get('exam_day') else f"{e['minutes']} Min. geplant",'note':''})

    # ---- Visual overview: everything below only re-reads the evidence above. ----
    def day_info(d: date) -> dict:
        data = daily[d]
        active = bool(data['active'] or data['goals'])
        return {'iso': d.isoformat(), 'day': d.day, 'weekday': plaene.WEEKDAY_LABELS[d.isoweekday()],
            'label': f"{plaene.WEEKDAY_LABELS[d.isoweekday()]} {d:%d.%m.}", 'today': d == today,
            'future': d > today, 'selected': mode == 'tag' and d == anchor, 'active': active,
            'planned': bool(data['plans'] or data['exams']),
            'missed': not active and bool(data['plans']) and d < today,
            'answers': len(data['answers']), 'right': sum(a['right'] for a in data['answers']),
            'checks': len(data['checks']), 'goal_minutes': sum(c['actual_minutes'] for c in data['goals']),
            'exam_day': any(e.get('exam_day') for e in data['exams']),
            'heat': _heat(len(data['answers']), active),
            'href': link('tag', d, back if mode == 'tag' else mode, base_date if mode == 'tag' else anchor)}
    strip_start, strip_end = (week_start, week_start + timedelta(days=6)) if mode == 'tag' else (start, end)
    strip = [day_info(d) for d in _days(strip_start, strip_end)]
    calendar_rows = []
    if mode == 'monat':
        cells = {d['iso']: d for d in strip}
        for g in groups:
            row = [None] * 7
            for d in _days(g['start'], g['end']):
                row[d.weekday()] = cells[d.isoformat()]
            calendar_rows.append({'days': row, 'week': g['start'].isocalendar()[1], 'total': g['total'],
                                  'href': g['href'], 'future': g['future']})
    check_rows = [{'label': t['label'], 'subject': t['subject'], 'scope': t['scope'], 'date': d.strftime('%d.%m.')}
                  for d in _days(start, end) for t in daily[d]['checks']]

    for g in goal_stats.values():
        due = [x for x in g['sessions'] if x['state'] in ('done', 'missed')]
        g.update(due=len(due), done=sum(x['state'] == 'done' for x in due),
                 due_minutes=sum(x['minutes'] for x in due))
    goal_list = list(goal_stats.values())
    goal_due, goal_done = sum(g['due'] for g in goal_list), sum(g['done'] for g in goal_list)
    elapsed_days = sum(1 for d in _days(start, end) if d <= today)
    active_days = sum(bool(d['active'] or d['goals']) for d in selected)
    answer_ten = round(right / len(answers) * 10) if answers else None

    lamps = []
    if not elapsed_days:
        lamps.append({'key': 'days', 'label': 'Regelmäßigkeit', 'level': 'off', 'value': 'noch offen', 'dialog': 'pr-d-days'})
    elif mode == 'tag':
        today_info = day_info(anchor)
        lamps.append({'key': 'days', 'label': 'Regelmäßigkeit', 'dialog': 'pr-d-days',
            'level': 'good' if today_info['active'] else 'warn' if today_info['missed'] else 'off',
            'value': 'Lerntag' if today_info['active'] else 'Plan nicht geschafft' if today_info['missed'] else 'kein Lerntag'})
    else:
        lamps.append({'key': 'days', 'label': 'Regelmäßigkeit', 'dialog': 'pr-d-days',
            'level': 'good' if active_days / elapsed_days >= .55 else 'warn' if active_days else 'off',
            'value': f'{active_days} von {elapsed_days} Tagen'})
    lamps.append({'key': 'answers', 'label': 'Richtig gelöst', 'dialog': 'pr-d-answers',
        'level': 'off' if answer_ten is None else 'good' if answer_ten >= 7 else 'warn',
        'value': 'keine Antworten' if answer_ten is None else f'{answer_ten} von 10 richtig'})
    soon = [e for e in exam_rows if 0 <= e['days'] <= 21]
    if soon:
        worst = max(soon, key=lambda e: LEVELS.index(e['verdict']['level']))
        lamps.append({'key': 'exams', 'label': 'Prüfungen', 'dialog': f"pr-d-exam-{worst['id']}",
            'level': 'good' if worst['verdict']['level'] == 'off' else worst['verdict']['level'],
            'value': f"{faecher.NAMEN[worst['subject']]}: {worst['verdict']['text'].lower()}"})
    else:
        lamps.append({'key': 'exams', 'label': 'Prüfungen', 'level': 'off', 'value': 'keine in 3 Wochen', 'dialog': ''})
    lamps.append({'key': 'goals', 'label': 'Ziele', 'dialog': 'pr-d-goals',
        'level': 'off' if not goal_due else 'good' if goal_done / goal_due >= .8 else 'warn',
        'value': f'{goal_done} von {goal_due} Einheiten' if goal_due else 'nichts fällig'})
    level = _worst(l['level'] for l in lamps)
    learning = _worst(l['level'] for l in lamps if l['key'] != 'exams')
    if start > today:
        head, line = 'Vorschau', 'Geplant ist noch nicht erledigt'
    else:
        if not active_days and not answers:
            head = 'Noch nichts erfasst'
        else:
            head = HEADS[mode][0 if learning in ('good', 'off') else 1]
        attention = [l['label'] for l in lamps if l['level'] == level and level in ('warn', 'crit')]
        line = (f"{'Jetzt unterstützen' if level == 'crit' else 'Im Blick'}: {', '.join(attention)}" if attention
                else 'Alles im grünen Bereich' if level == 'good' else 'Keine Meldung ist kein Misserfolg')
    conversation = ('Dieser Zeitraum liegt noch vor uns. Geplant bedeutet nicht erledigt.' if start > today
                    else 'Keine Meldung ist kein Misserfolg. Gemeinsame Gespräche sagen mehr als eine Zahl.'
                    if not active_days else 'Ein guter Gesprächseinstieg: „Was ist dir diesmal leichter gefallen?“')
    period_short = (f'KW {start.isocalendar()[1]}' if mode == 'woche' else plaene.MONTH_LABELS[anchor.month]
                    if mode == 'monat' else f"{plaene.WEEKDAY_LABELS[anchor.isoweekday()]}, {anchor:%d.%m.}")

    return {'mode':mode,'title':MODES[mode],'anchor':anchor.isoformat(),
        'range_label':f'{plaene.MONTH_LABELS[anchor.month]} {anchor.year}' if mode=='monat' else
                      anchor.strftime('%d.%m.%Y') if mode=='tag' else f'{start:%d.%m.} – {end:%d.%m.%Y}',
        'month_label':f'{plaene.MONTH_LABELS[anchor.month]} {anchor.year}', 'today':today.isoformat(),
        'as_of':cutoff_day.strftime('%d.%m.%Y'),'start':start.isoformat(),'end':end.isoformat(),
        'previous':link(mode,previous,back if mode=='tag' else '',base_date) if previous>=date(2000,1,1) else None,
        'next':link(mode,following,back if mode=='tag' else '',base_date) if following<=date(2100,12,31) else None,
        'month_link':link('monat',anchor),'week_link':link('woche',anchor),'today_link':link(mode,today),
        'back_link':link(back,base_date),'answers':len(answers),'personal_answers':len(personal_answers),
        'right':right,'retry':len(answers)-right,'answer_percent':round(right/len(answers)*100) if answers else None,
        'worked_topics':len(worked_ids),'all_checks':len(all_checks),'insights':insights,
        'exam_answers':len(answers)-len(personal_answers),'active_days':active_days,
        'new_secure':len(checks),'goal_reports':sum(g['reports'] for g in goal_stats.values()),
        'goal_minutes':sum(g['minutes'] for g in goal_stats.values()),'goals':list(goal_stats.values()),
        'goal_planned':sum(g['planned'] for g in goal_stats.values()), 'subjects':subject_rows,
        'exams':exam_rows,'exam_minutes':sum(e['minutes'] for d in selected for e in d['exams']),
        'groups':groups,'chart_max':ceiling,'calendar':calendar_days,'calendar_offset':month_start.weekday(),
        'day_items':day_items,'future':start>today,
        'day_link':link('tag',min(max(today,start),end) if mode!='tag' else anchor),
        'status':{'level':level,'head':head,'line':line,'lamps':lamps},'conversation':conversation,
        'period_short':period_short,'elapsed_days':elapsed_days,'answer_ten':answer_ten,
        'strip':strip,'strip_offset':strip_start.weekday() if mode=='monat' else 0,
        'calendar_rows':calendar_rows,'check_rows':check_rows,'goal_due':goal_due,'goal_done':goal_done,
        'goal_due_minutes':sum(g['due_minutes'] for g in goal_list),
        'practice':[{'label':t['label'],'subject':t['subject'],'scope':t['scope'],'retry':t['retry'],
                     'answers':t['answers'],'ten':round(t['right']/t['answers']*10) if t['answers'] else None}
                    for t in needs_practice[:5]],
        'upcoming':[e for e in exam_rows if e['days']>=0]}
