"""Neue Spalten erreichen auch eine bestehende Datenbank.

`CREATE TABLE IF NOT EXISTS` legt in einer vorhandenen Tabelle keine neue
Spalte an. `app/db.py` zieht deshalb seit jeher Spalten einzeln nach
(`_ADDED_COLUMNS`) — die Tabellen des adaptiven Lernens waren daran aber
nie angeschlossen.

Folge auf einer echten Installation: die Lektion wurde vor
`visualisierung_alternativ` angelegt, `saeen()` schrieb die Spalte, und
`/lernen/adaptiv` antwortete mit 500 statt mit der ersten Frage.
"""
import pytest

#: Spalten, die nach der ersten Fassung des adaptiven Schemas dazukamen.
SPAETER_DAZU = [
    ("lern_erklaerung", "visualisierung_alternativ"),
    ("lern_aufgabe", "typischer_fehler"),
    ("lern_aufgabe", "antwort_art"),
    ("lern_aufgabe", "optionen"),
    ("lern_aufgabe", "aufloesung"),
]


def _spalten(app_env, tabelle):
    return {r["name"] for r in app_env.db.q(f"PRAGMA table_info({tabelle})")}


@pytest.mark.parametrize("tabelle,spalte", SPAETER_DAZU)
def test_fehlende_spalte_wird_nachgezogen(client, fake_llm, fake_cli, app_env,
                                          tabelle, spalte):
    from app.adaptiv import store
    with app_env.db.tx() as c:
        c.execute(f"ALTER TABLE {tabelle} DROP COLUMN {spalte}")
    assert spalte not in _spalten(app_env, tabelle)

    store.init()

    assert spalte in _spalten(app_env, tabelle)


def test_die_lektion_laesst_sich_danach_wieder_saeen(client, fake_llm,
                                                     fake_cli, app_env):
    """Der eigentliche Schaden: ohne die Spalte bricht `saeen()` ab."""
    from app.adaptiv import lektionen, store
    with app_env.db.tx() as c:
        c.execute("ALTER TABLE lern_erklaerung "
                  "DROP COLUMN visualisierung_alternativ")

    store.init()
    lektionen.saee_alle()

    assert lektionen.fuer_thema("Brüche addieren") is not None


def test_topic_id_wird_in_bestehender_datenbank_nachgezogen(
        client, fake_llm, fake_cli, app_env):
    """`lern_eingabe.topic_id` kam nach dem ersten Schema dazu."""
    from app.adaptiv import store
    with app_env.db.tx() as c:
        c.execute("ALTER TABLE lern_eingabe DROP COLUMN topic_id")
    assert "topic_id" not in _spalten(app_env, "lern_eingabe")

    store.init()

    assert "topic_id" in _spalten(app_env, "lern_eingabe")
