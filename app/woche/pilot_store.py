"""Pilot persistence. Legacy tables stay untouched; no guessed identity migration."""
from pathlib import Path
from .. import db
from . import pilot


class Conflict(ValueError):
    pass


def init():
    c = db.conn()
    c.executescript(Path(__file__).with_name('pilot.sql').read_text())
    with db.tx() as c:
        legacy = c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='woche_kind'").fetchone()
        c.execute('INSERT OR IGNORE INTO woche_migration VALUES (1,?)', (bool(legacy),))


def get(week=None):
    row = db.q1("SELECT * FROM woche_plan WHERE child_key='installation' AND week=?", str(week or pilot.monday()))
    return dict(row) if row else None


def by_id(plan_id):
    row = db.q1("SELECT * FROM woche_plan WHERE id=? AND child_key='installation'", plan_id)
    if not row:
        raise LookupError('Diese Vereinbarung ist nicht verfügbar.')
    return dict(row)


def save(week, values, version):
    with db.tx() as c:
        old = get(week)
        if (old['version'] if old else 0) != version:
            raise Conflict('Die Vereinbarung wurde inzwischen geändert. Bitte neu laden und gemeinsam prüfen.')
        if old:
            changed = any(old[k] != v for k, v in values.items())
            goal_changed = old['goal'] != values['goal']
            c.execute('UPDATE woche_plan SET ' + ','.join(f'{k}=?' for k in values) +
                      ',discussed_at=?,version=version+1,revision=revision+?,child_status=?,achieved=? WHERE id=?',
                      (*values.values(), db.now(), int(changed), 'offen' if changed else old['child_status'],
                       0 if goal_changed else old['achieved'], old['id']))
        else:
            c.execute('INSERT INTO woche_plan (week,discussed_at,' + ','.join(values) + ') VALUES (' +
                      ','.join('?' for _ in range(len(values)+2)) + ')', (str(week), db.now(), *values.values()))


def update(plan_id, version, values):
    allowed = {'child_status', 'paused', 'achieved', 'feeling', 'wish'}
    if not values or not set(values) <= allowed:
        raise ValueError('Ungültige Änderung.')
    with db.tx() as c:
        plan = by_id(plan_id)
        if all(plan[k] == v for k, v in values.items()):
            return
        if plan['version'] != version:
            raise Conflict('Die Woche wurde inzwischen geändert. Bitte neu laden.')
        c.execute('UPDATE woche_plan SET ' + ','.join(f'{k}=?' for k in values) + ',version=version+1 WHERE id=?',
                  (*values.values(), plan_id))


def feedback(plan):
    return {r['activity'] for r in db.q('SELECT activity FROM woche_feedback WHERE plan_id=? AND revision=? AND day=?',
                                       plan['id'], plan['revision'], str(pilot.today()))}


def complete(plan, activity):
    db.conn().execute('INSERT OR IGNORE INTO woche_feedback VALUES (?,?,?,?)',
                      (plan['id'], plan['revision'], activity, str(pilot.today())))


def helps(plan_id=None, open_only=False):
    where, args = ["p.child_key='installation'"], []
    if plan_id is not None:
        where.append('h.plan_id=?')
        args.append(plan_id)
    if open_only:
        where.append("h.status IN ('angefragt','zugesagt')")
    return [dict(r) for r in db.q('SELECT h.*,p.week FROM woche_help h JOIN woche_plan p ON p.id=h.plan_id WHERE ' +
                                ' AND '.join(where) + ' ORDER BY h.id DESC', *args)]


def request_help(plan, activity, kind, message):
    db.conn().execute('INSERT OR IGNORE INTO woche_help (plan_id,revision,activity,activity_text,kind,message) VALUES (?,?,?,?,?,?)',
                     (plan['id'], plan['revision'], activity, pilot.step_text(plan, activity), kind, message))


def help_update(help_id, version, status, reply='', appointment=''):
    with db.tx() as c:
        row = c.execute("SELECT h.* FROM woche_help h JOIN woche_plan p ON p.id=h.plan_id WHERE h.id=? AND p.child_key='installation'", (help_id,)).fetchone()
        if not row:
            raise LookupError('Diese Hilfeanfrage ist nicht verfügbar.')
        if row['status'] == status and (status != 'zugesagt' or (row['reply'], row['appointment']) == (reply, appointment)):
            return
        if row['version'] != version or row['status'] not in ('angefragt', 'zugesagt'):
            raise Conflict('Die Hilfeanfrage wurde inzwischen geändert. Bitte neu laden.')
        if status == 'erledigt' and row['status'] != 'zugesagt':
            raise ValueError('Bitte zuerst die Unterstützung zusagen.')
        c.execute('UPDATE woche_help SET status=?,reply=?,appointment=?,version=version+1 WHERE id=?',
                  (status, reply if status == 'zugesagt' else row['reply'],
                   appointment if status == 'zugesagt' else row['appointment'], help_id))


def parent_summary():
    # Deliberately no private session choices, reasons, or detailed feedback dates.
    plan = get()
    positive = [] if not plan else [r['activity'] for r in db.q('SELECT DISTINCT activity FROM woche_feedback WHERE plan_id=?', plan['id'])]
    return {'plan': plan, 'positive': positive, 'helps': helps(open_only=True)}
