"""„Meine Woche" — der Begleiter.

Ein eigenstaendiges Modul neben Karo, nicht in Karo. Es teilt sich mit der
Hauptanwendung nur die Infrastruktur — Datenbankverbindung, Sitzung, CSRF —
und beruehrt weder Themen noch Flaggen, Quizze, Lernzyklus oder Sprachmodell.
Karo prueft den Wissensstand; der Begleiter hilft beim Anfangen. Zwei
Aufgaben, zwei Module.

Einbinden in `app/main.py` — eine Zeile:

    from .woche import router as woche
    app.include_router(woche.router)

Das Schema legt sich beim ersten Aufruf selbst an (`store.ensure()`), damit
`main.py` nichts weiter wissen muss. Alle Tabellen tragen das Praefix
`woche_`; ein DROP dieser Tabellen entfernt den Begleiter rueckstandsfrei.

Der Leitsatz, gegen den hier jede Zeile geprueft wurde:

    Ein Plan, der scheitern kann, macht dieses Kind kaputt.
    Also darf es keinen Plan geben, der scheitern kann.

Deshalb gibt es im ganzen Modul kein „offen", kein „nicht erledigt", keine
Quote, keine Punkte, keine Streak und keine Benachrichtigung, die ein
schlechtes Gewissen erzeugt.
"""

from . import regeln, router, store, vorschlaege   # noqa: F401

__all__ = ["regeln", "router", "store", "vorschlaege"]
