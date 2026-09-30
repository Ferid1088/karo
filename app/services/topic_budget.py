"""Wie viele neue Themen Karo an einem Tag beim Lehrplan-Dienst bestellt.

Der Dienst bekommt keine Familien- oder Kinderkennung und kann deshalb gar
nicht wissen, wer wie viel bestellt. Die Grenze muss also hier stehen, wo die
Familie sitzt — und nicht dort, wo man dafuer wissen muesste, wer sie ist.

Der Anlass: siebzehn Pruefungsthemen auf einmal eingetragen. Der Dienst hat
sie alle angenommen und das Tageskontingent an Modellaufrufen an einem
Nachmittag verbraucht. Danach bekam niemand mehr etwas — auch nicht die
Familien, die nur ein einziges Thema wollten.

Was nicht gezaehlt wird: ein Thema, das der Dienst schon fertig hat. Das
kostet ihn nichts, und eine Grenze dafuer waere reine Schikane. Deshalb wird
erst gebucht und sofort wieder freigegeben, wenn die Antwort „fertig" lautet.

Ein Thema zaehlt einmal pro Tag, egal wie oft der Auftrag es erneut versucht:
sonst verbraucht ein einziges haengendes Thema das ganze Budget.
"""
from __future__ import annotations

import os

from .. import db

#: Neue Themen pro Tag. Fuenf, weil eine Klassenarbeit selten mehr als fuenf
#: wirklich neue Themen bringt — der Rest ist meist schon da.
STANDARD = 5


def grenze() -> int:
    """0 heisst: keine Grenze."""
    wert = os.environ.get("KARO_FAMILY_DAILY_TOPICS", "").strip()
    try:
        return max(0, int(wert)) if wert else STANDARD
    except ValueError:
        return STANDARD


def _tabelle(c) -> None:
    c.execute("""CREATE TABLE IF NOT EXISTS curriculum_tagesbudget (
        tag TEXT NOT NULL, schluessel TEXT NOT NULL, gebucht_am TEXT NOT NULL,
        PRIMARY KEY (tag, schluessel))""")


def verbraucht(tag: str | None = None) -> int:
    with db.tx() as c:
        _tabelle(c)
        return c.execute("SELECT count(*) AS n FROM curriculum_tagesbudget WHERE tag=?",
                         (tag or db.today(),)).fetchone()["n"]


def rest(tag: str | None = None) -> int | None:
    """Wie viele neue Themen heute noch gehen. None heisst: keine Grenze."""
    g = grenze()
    return None if not g else max(0, g - verbraucht(tag))


def gebucht(schluessel: str, tag: str | None = None) -> bool:
    with db.tx() as c:
        _tabelle(c)
        return bool(c.execute("SELECT 1 FROM curriculum_tagesbudget WHERE tag=? AND schluessel=?",
                              (tag or db.today(), schluessel)).fetchone())


def buchen(schluessel: str) -> bool:
    """Platz fuer dieses Thema nehmen. False heisst: heute ist Schluss.

    Ein Thema, das heute schon gebucht ist, geht immer durch — sonst
    verbraucht ein einziger haengender Auftrag mit jedem Versuch einen Platz.
    """
    g = grenze()
    if not g:
        return True
    heute = db.today()
    with db.tx() as c:
        _tabelle(c)
        if c.execute("SELECT 1 FROM curriculum_tagesbudget WHERE tag=? AND schluessel=?",
                     (heute, schluessel)).fetchone():
            return True
        belegt = c.execute("SELECT count(*) AS n FROM curriculum_tagesbudget WHERE tag=?",
                           (heute,)).fetchone()["n"]
        if belegt >= g:
            return False
        c.execute("INSERT INTO curriculum_tagesbudget(tag, schluessel, gebucht_am) VALUES (?,?,?)",
                  (heute, schluessel, db.now()))
        return True


def freigeben(schluessel: str) -> None:
    """Platz zurueckgeben: der Dienst hatte das Thema schon fertig."""
    with db.tx() as c:
        _tabelle(c)
        c.execute("DELETE FROM curriculum_tagesbudget WHERE tag=? AND schluessel=?",
                  (db.today(), schluessel))
