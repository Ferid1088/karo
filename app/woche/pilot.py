"""Validation and deterministic rules. No learning data or model calls."""
from datetime import date, datetime, timedelta
import re

from .. import config

ZONE = config.zeitzone()
LIMITS = {'goal': 160, 'step': 240, 'routine': 160, 'promise': 240, 'message': 240, 'reply': 240}
DAYS = {'1': 'Montag', '2': 'Dienstag', '3': 'Mittwoch', '4': 'Donnerstag', '5': 'Freitag', '6': 'Samstag', '7': 'Sonntag'}
HELP = {'erklaeren': 'Erklären', 'zusammen': 'Zusammen anfangen', 'sprechen': 'Kurz sprechen'}
STATUS = {'angefragt': 'Hilfe angefragt', 'zugesagt': 'Hilfe zugesagt', 'erledigt': 'Hilfe erledigt', 'zurueckgenommen': 'Hilfe zurückgenommen'}


def today(now=None):
    return (now or datetime.now(ZONE)).astimezone(ZONE).date()


def monday(day=None):
    day = day or today()
    return day - timedelta(days=day.weekday())


def week(value):
    try:
        result = date.fromisoformat(value)
        if result.isoformat() != value or result.weekday() != 0:
            raise ValueError
        return result
    except (ValueError, TypeError):
        raise ValueError('Bitte eine gültige Woche auswählen.') from None


def short(data, field):
    text = str(data.get(field, '')).strip()
    if len(text) > LIMITS[field]:
        raise ValueError(f'Der Text darf höchstens {LIMITS[field]} Zeichen haben.')
    return text


def agreement(data, selected_days):
    values = {key: short(data, key) for key in ('goal', 'step', 'routine', 'promise')}
    days = sorted(set(selected_days))
    if any(day not in DAYS for day in days):
        raise ValueError('Bitte gültige Wochentage auswählen.')
    if values['routine'] and not days:
        raise ValueError('Bitte mindestens einen Tag für die Routine auswählen.')
    if values['step'] and not values['goal']:
        raise ValueError('Ein erster Schritt braucht ein Wochenziel.')
    if not any(values.values()):
        raise ValueError('Legt gemeinsam ein Ziel, eine Routine oder eine Zusage fest.')
    if data.get('discussed') != 'ja':
        raise ValueError('Bitte bestätigen: Mit meinem Kind besprochen.')
    day, time = str(data.get('promise_day', '')), str(data.get('promise_time', ''))
    if day and day not in DAYS or time and not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', time):
        raise ValueError('Bitte einen gültigen Zusagetermin angeben.')
    if (day or time) and not values['promise'] or time and not day:
        raise ValueError('Ein Termin braucht eine Zusage und einen Tag.')
    return dict(values, days=','.join(days) if values['routine'] else '', promise_day=day, promise_time=time)


def step_text(plan, activity):
    if activity == 'routine':
        return plan['routine']
    return plan['step'] or 'Lies dein Wochenziel und wähle eine kleine Handlung, mit der du anfangen möchtest.'


def next_action(plan, feedback, helps, hidden=(), day=None):
    day = day or today()
    if not plan or plan['paused']:
        return None
    for item in helps:
        if item['revision'] == plan['revision'] and item['status'] in ('angefragt', 'zugesagt'):
            return {'kind': 'help', 'help': item}
    for activity in ('routine', 'goal'):
        if not plan[activity] or activity in feedback or activity in hidden:
            continue
        if activity == 'routine' and str(day.isoweekday()) not in plan['days'].split(','):
            continue
        if activity == 'goal' and plan['achieved']:
            continue
        return {'kind': 'activity', 'activity': activity, 'text': step_text(plan, activity)}
    return None


def easier(text):
    # Works for custom content too: inspect the actual action once, without inventing subject matter.
    return f'Lies nur diese Handlung und zeige auf die Stelle, bei der du anfangen könntest: „{text}“'


def suggestions(grade):
    if grade and 3 <= grade <= 5:
        return [('Ein kurzes Buchstück erzählen.', 'Schlag eine Seite auf und lies den ersten Satz laut.'),
                ('Eine eigene Bastelidee ausprobieren.', 'Leg ein Blatt und einen Stift bereit.')]
    if grade and 6 <= grade <= 8:
        return [('Meinen Referatseinstieg sicher erzählen.', 'Öffne deine Notizen und lies den ersten Satz laut.'),
                ('Eine Mathefrage klären, bei der ich gerade hänge.', 'Such eine Aufgabe aus und markiere die unklare Stelle.')]
    if grade and 9 <= grade <= 10:
        return [('Ein eigenes Projekt ein Stück voranbringen.', 'Öffne deine Projektnotizen und markiere eine Idee.'),
                ('Meine nächste Präsentation vorbereiten.', 'Öffne deine Notizen und lies die Überschrift laut.')]
    return [('Etwas für mein eigenes Vorhaben ausprobieren.', 'Leg eine Sache bereit, die du dafür brauchst.')]
