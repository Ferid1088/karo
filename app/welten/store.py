"""Der persönliche Begleiter (Name/Bild/Farbe) und das Interessen-Tagebuch.

Beide sind Verlaufs-Tabellen: `add_companion`/`add_interest` fügen immer eine
neue Zeile ein, nie ein UPDATE. `current_*` liefert die neueste Zeile —
`None`, wenn noch nichts eingetragen wurde (dann bleibt es beim Karo-Logo).
"""
from pathlib import Path

from .. import db


def init():
    conn = db.conn()
    # Die alten "Meine Welt"-Tabellen (Café/Atelier/Station, Missionen,
    # Album) sind ersetzt — bewusst entfernt statt als totes Gewicht liegen
    # gelassen.
    conn.executescript(
        "DROP TABLE IF EXISTS welt_mission;"
        "DROP TABLE IF EXISTS welt_preference;"
        "DROP TABLE IF EXISTS welt_interest;"
    )
    conn.executescript(Path(__file__).with_name('schema.sql').read_text())


def current_companion():
    row = db.q1("SELECT * FROM begleiter_verlauf WHERE child_key='installation' "
               "ORDER BY id DESC LIMIT 1")
    return dict(row) if row else None


def companion_history():
    return [dict(r) for r in db.q(
        "SELECT * FROM begleiter_verlauf WHERE child_key='installation' ORDER BY id DESC")]


def add_companion(name, foto_pfad, farbe, spass_antwort):
    name = short(name, 40, 'Name', required=True)
    choice(farbe, FARBEN, 'eine Farbe')
    spass_antwort = short(spass_antwort, 200, 'Antwort')
    with db.tx() as c:
        return c.execute(
            'INSERT INTO begleiter_verlauf(name,foto_pfad,farbe,spass_antwort,created_at) '
            'VALUES (?,?,?,?,?)',
            (name, foto_pfad, farbe, spass_antwort, db.now())).lastrowid


def current_interest():
    row = db.q1("SELECT * FROM interesse_eintrag WHERE child_key='installation' "
               "ORDER BY id DESC LIMIT 1")
    return dict(row) if row else None


def interest_history(limit=20):
    return [dict(r) for r in db.q(
        "SELECT * FROM interesse_eintrag WHERE child_key='installation' "
        "ORDER BY id DESC LIMIT ?", limit)]


def add_interest(text, audio_pfad):
    text = short(text, 300, 'Dein Interesse')
    if not text and not audio_pfad:
        raise ValueError('Bitte etwas schreiben oder eine Sprachnachricht aufnehmen.')
    with db.tx() as c:
        return c.execute(
            'INSERT INTO interesse_eintrag(text,audio_pfad,created_at) VALUES (?,?,?)',
            (text, audio_pfad, db.now())).lastrowid


FARBEN = {'lila': 'Lila', 'ozean': 'Blau', 'wiese': 'Grün', 'sonne': 'Orange',
         'zuckerwatte': 'Rosa', 'lava': 'Rot', 'dunkel': 'Dunkel'}


def short(value, limit, label, required=False):
    value = str(value or '').strip()
    if len(value) > limit or (required and not value):
        raise ValueError(f'{label}: Bitte {"1 bis " if required else "höchstens "}{limit} Zeichen eingeben.')
    return value


def choice(value, choices, label):
    if value not in choices:
        raise ValueError(f'Bitte {label} auswählen.')
    return value
