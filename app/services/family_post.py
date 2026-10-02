"""Post von zu Hause: kurze Nachrichten der Eltern an das Kind.

Leitplanken (bewusst im Code, nicht nur in der Oberfläche):
- nur freundliche Emojis, keine Daumen-runter- oder Enttäuschungs-Symbole;
- Vorschläge loben Einsatz und laden zum Erklären ein, sie nennen nie Fehlerzahlen;
- Feiern hängen am eigenen Ziel des Kindes und seiner Feier-Idee, nie an Ampel,
  Trefferquote oder Noten;
- das Kind sieht nur die Nachricht, nie den Bericht dahinter;
- Eltern können eine Nachricht zurückziehen, solange sie ungelesen ist.
Der Elternbericht liest hier nur (keine Schreibzugriffe beim Anzeigen).
"""
from __future__ import annotations

from datetime import date

from .. import config, db
from ..woche import plaene

PARENT_EMOJIS = ('💪', '⭐', '👏', '❤️', '🤗', '🙌', '🎉')
CHILD_REACTIONS = {'😊': '😊', '❤️': '❤️', '👍': '👍', '🤗': '🤗',
                   'danke': 'Danke!', 'reden': 'Lass uns reden'}
KINDS = {'nachricht': 'Nachricht', 'ueberraschung': 'Überraschung', 'feier': 'Feier'}
_OPS = config.ops()
MAX_TEXT = _OPS.post_max_text_zeichen
MAX_CELEBRATION = _OPS.post_max_feier_zeichen


class PostError(ValueError):
    """Eine Eingabe, die nicht verschickt werden kann (Meldung für Menschen)."""


def _clean(text: str | None) -> str:
    return ' '.join(str(text or '').split())


def _table_exists(name: str) -> bool:
    return bool(db.q1("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", name))


def _row(row) -> dict:
    item = dict(row)
    stamp = item.get('created_at') or ''
    day = plaene.today()
    try:
        created = date.fromisoformat(stamp[:10])
        item['when'] = ('heute' if created == day else 'gestern' if (day - created).days == 1
                        else created.strftime('%d.%m.'))
    except ValueError:
        item['when'] = ''
    item['kind_label'] = KINDS.get(item['kind'], 'Nachricht')
    item['reaction_label'] = CHILD_REACTIONS.get(item.get('reaction') or '', '')
    return item


# ---- Eltern ----------------------------------------------------------------

def send(text: str | None, emoji: str | None, kind: str = 'nachricht', goal_id: int | None = None) -> int:
    text, emoji = _clean(text), (emoji or '').strip() or None
    if kind not in KINDS:
        raise PostError('Unbekannte Art der Nachricht.')
    if emoji is not None and emoji not in PARENT_EMOJIS:
        raise PostError('Bitte eines der freundlichen Emojis wählen.')
    if not text and not emoji:
        raise PostError('Bitte schreiben Sie ein paar Worte oder wählen Sie ein Emoji.')
    if len(text) > MAX_TEXT:
        raise PostError(f'Bitte höchstens {MAX_TEXT} Zeichen – eine Nachricht, kein Brief.')
    if kind == 'feier' and goal_id is None:
        raise PostError('Eine Feier gehört zu einem Ziel.')
    with db.tx() as c:
        if kind == 'feier' and c.execute("""SELECT 1 FROM family_message WHERE kind='feier'
                AND goal_id=? AND withdrawn_at IS NULL""", (goal_id,)).fetchone():
            raise PostError('Zu diesem Ziel ist die Feier schon verabredet.')
        cursor = c.execute('''INSERT INTO family_message(kind,text,emoji,goal_id,created_at)
                              VALUES(?,?,?,?,?)''', (kind, text, emoji, goal_id, db.now()))
        return int(cursor.lastrowid)


def withdraw(message_id: int) -> None:
    with db.tx() as c:
        row = c.execute('SELECT read_at, withdrawn_at FROM family_message WHERE id=?', (message_id,)).fetchone()
        if row is None or row['withdrawn_at']:
            raise PostError('Diese Nachricht gibt es nicht mehr.')
        if row['read_at']:
            raise PostError('Diese Nachricht wurde schon gelesen und bleibt stehen.')
        c.execute('UPDATE family_message SET withdrawn_at=? WHERE id=?', (db.now(), message_id))


def recent(limit: int = 6) -> list[dict]:
    """Zuletzt verschickte Nachrichten mit Lesestatus und Antwort des Kindes."""
    return [_row(r) for r in db.q('''SELECT * FROM family_message WHERE withdrawn_at IS NULL
                                     ORDER BY id DESC LIMIT ?''', limit)]


def celebrate(goal_id: int) -> int:
    item = next((g for g in celebrations_due() if g['id'] == goal_id), None)
    if item is None:
        raise PostError('Für dieses Ziel gibt es gerade keine Feier-Idee zum Zusagen.')
    text = f"Du hast dein Ziel „{item['statement']}“ geschafft! Deine Feier-Idee machen wir: {item['celebration']}"
    return send(text[:MAX_TEXT], '🎉', 'feier', goal_id)


def celebrations_due() -> list[dict]:
    """Eigene Ziele des Kindes mit Feier-Idee, die geschafft und noch nicht zugesagt sind.

    Geschafft heißt: als erledigt markiert oder alle geplanten Minuten gelernt.
    Nur lesend; legt keine Tabellen an (Eltern haben "Ziele planen" evtl. nie geöffnet).
    """
    if not _table_exists('plan_goal') or not any(
            r['name'] == 'celebration' for r in db.q("PRAGMA table_info(plan_goal)")):
        return []
    rows = db.q('''SELECT g.id, g.statement, g.celebration, g.status, g.completed_at,
            (SELECT COALESCE(SUM(s.planned_minutes),0) FROM plan_session s
              WHERE s.goal_id=g.id AND s.status!='cancelled') AS planned,
            (SELECT COALESCE(SUM(c.actual_minutes),0) FROM plan_completion c
              JOIN plan_session s ON s.id=c.planned_session_id WHERE s.goal_id=g.id) AS actual
        FROM plan_goal g
        WHERE g.child_key='installation' AND TRIM(COALESCE(g.celebration,''))!=''
          AND NOT EXISTS (SELECT 1 FROM family_message m WHERE m.kind='feier'
                          AND m.goal_id=g.id AND m.withdrawn_at IS NULL)
        ORDER BY g.id''')
    due = []
    for r in rows:
        done = r['status'] in ('completed', 'archived') and r['completed_at']
        full = r['planned'] > 0 and r['actual'] >= r['planned']
        if done or full:
            due.append({'id': r['id'], 'statement': r['statement'].rstrip(' .!'), 'celebration': r['celebration']})
    return due


def suggestions(report: dict, name: str) -> list[dict]:
    """Bis zu drei Textvorschläge aus dem Bericht: Einsatz loben, zum Erklären einladen.

    Nie Fehlerzahlen, nie Vergleiche, nie Bedingungen ("wenn du ... dann ...").
    """
    items: list[dict] = []
    def add(text, emoji):
        if text and all(text != s['text'] for s in items):
            items.append({'text': text[:MAX_TEXT], 'emoji': emoji})
    checks = report.get('check_rows') or []
    if checks:
        add(f"„{checks[-1]['label']}“ sitzt jetzt – ich bin stolz auf dich!", '⭐')
    days = report.get('active_days') or 0
    if report.get('mode') != 'tag' and days >= 2:
        add(f'Du hast {days} Tage geübt. Stark, dass du drangeblieben bist!', '💪')
    elif report.get('mode') == 'tag' and days:
        add('Schön, dass du heute gelernt hast!', '👏')
    topics = [t for s in report.get('subjects') or [] for t in s.get('topics') or []]
    if topics:
        add(f"Erklärst du mir heute Abend „{topics[0]['label']}“? Ich bin neugierig.", '🤗')
    if report.get('goal_done'):
        add('Du hältst dich an deinen eigenen Plan. Das ist richtig gut!', '🙌')
    upcoming = [e for e in report.get('upcoming') or [] if 0 <= e['days'] <= 14]
    if upcoming:
        add(f"Für die Arbeit am {upcoming[0]['date_label']}: Ich helfe dir gern beim Üben.", '💪')
    add(f'Ich hab dich lieb, {name}. Wenn du Hilfe brauchst, sag einfach Bescheid.' if name
        else 'Ich hab dich lieb. Wenn du Hilfe brauchst, sag einfach Bescheid.', '❤️')
    return items[:3]


def parent_view(report: dict, name: str) -> dict:
    """Alles, was der Bericht für "Post von zu Hause" zeigt – nur lesend."""
    if not _table_exists('family_message'):
        return {'suggestions': suggestions(report, name), 'recent': [], 'celebrations': [],
                'emojis': PARENT_EMOJIS, 'max_text': MAX_TEXT}
    return {'suggestions': suggestions(report, name), 'recent': recent(),
            'celebrations': celebrations_due(), 'emojis': PARENT_EMOJIS, 'max_text': MAX_TEXT}


# ---- Kind ------------------------------------------------------------------

def inbox(limit: int = 20) -> list[dict]:
    return [_row(r) for r in db.q('''SELECT * FROM family_message WHERE withdrawn_at IS NULL
                                     ORDER BY id DESC LIMIT ?''', limit)]


def unread() -> list[dict]:
    if not _table_exists('family_message'):
        return []
    return [_row(r) for r in db.q('''SELECT * FROM family_message WHERE withdrawn_at IS NULL
                                     AND read_at IS NULL ORDER BY id DESC''')]


def mark_read(ids: list[int]) -> None:
    if not ids:
        return
    with db.tx() as c:
        c.executemany('UPDATE family_message SET read_at=? WHERE id=? AND read_at IS NULL',
                      [(db.now(), i) for i in ids])


def react(message_id: int, reaction: str) -> None:
    if reaction not in CHILD_REACTIONS:
        raise PostError('Diese Antwort gibt es nicht.')
    with db.tx() as c:
        row = c.execute('SELECT withdrawn_at FROM family_message WHERE id=?', (message_id,)).fetchone()
        if row is None or row['withdrawn_at']:
            raise PostError('Diese Nachricht gibt es nicht mehr.')
        now = db.now()
        c.execute('''UPDATE family_message SET reaction=?, reacted_at=?, read_at=COALESCE(read_at,?)
                     WHERE id=?''', (reaction, now, now, message_id))
