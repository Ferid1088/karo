"""Schritt 3: kein Katalogtreffer → erzeugen → prüfen → freigeben → wiederverwenden.

Der erste echte Modellaufruf des adaptiven Lernens. Er läuft im Hintergrund,
nicht im Klick des Kindes: eine Lektion zu schreiben dauert, und §15
verlangt, dass niemand vor einem Spinner sitzt. Das Kind sieht, dass Karo
arbeitet, und bekommt die Lektion, sobald sie geprüft ist.

Und genau einmal. Danach ist es ein Katalogtreffer wie jeder andere — das
ist der ganze Kostenpunkt von §6.
"""
import pytest

from .conftest import csrf_from, run_jobs
from .test_app import einrichten, kind_modus_aktivieren
from .test_lektion_erzeugung import _lektion

PFAD = "/lernen/adaptiv"
THEMA = "Würfel: Volumen"


def _kind(client, fake_llm, app_env, *, erzeugen: bool):
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True,
                          llm_error_creation_enabled=erzeugen)
    fake_llm.responses["lektion"] = _lektion()
    kind_modus_aktivieren(client)
    token = csrf_from(client.get(PFAD).text)
    fake_llm.calls.clear()      # die Einrichtung hat schon gerufen
    return token


def _waehle(client, token, thema=THEMA):
    return client.post(f"{PFAD}/start", data={"_csrf": token, "thema": thema})


def test_ohne_schalter_bleibt_es_bei_der_ehrlichen_antwort(client, fake_llm,
                                                           app_env):
    token = _kind(client, fake_llm, app_env, erzeugen=False)

    seite = _waehle(client, token)

    assert "noch keine Lernreihe" in seite.text
    assert app_env.db.q("SELECT id FROM job WHERE type='lektion_erzeugen'") == []
    assert fake_llm.calls == []


def test_ein_unbekanntes_thema_loest_die_erzeugung_aus(client, fake_llm,
                                                       app_env):
    token = _kind(client, fake_llm, app_env, erzeugen=True)

    seite = _waehle(client, token)

    assert "bereitet" in seite.text.lower()
    assert THEMA in seite.text
    auftraege = app_env.db.q("SELECT * FROM job WHERE type='lektion_erzeugen'")
    assert len(auftraege) == 1
    # Noch keine Sitzung: das Kind wartet, es lernt noch nicht.
    assert app_env.db.q("SELECT id FROM lern_sitzung") == []


def test_der_auftrag_erzeugt_prueft_und_gibt_frei(client, fake_llm,
                                                  app_env):
    from app.adaptiv import lektionen, store
    token = _kind(client, fake_llm, app_env, erzeugen=True)
    _waehle(client, token)

    run_jobs(app_env, fake_llm)

    lektion = lektionen.fuer_thema(THEMA, "mathematik")
    assert lektion is not None
    konzept = store.konzept(lektion["konzept_id"])
    assert konzept["quelle"] == "erzeugt"
    assert konzept["geprueft_am"], "ohne Freigabe erreicht es kein Kind"
    assert len(fake_llm.calls) == 2  # Author plus independent class review.


def test_danach_ist_es_ein_treffer_ohne_modell(client, fake_llm,
                                               app_env):
    """§6: genau der Punkt der ganzen Übung."""
    token = _kind(client, fake_llm, app_env, erzeugen=True)
    _waehle(client, token)
    run_jobs(app_env, fake_llm)
    fake_llm.calls.clear()

    seite = _waehle(client, token)

    assert "bereitet" not in seite.text.lower()
    assert app_env.db.q1("SELECT zustand FROM lern_sitzung "
                         "ORDER BY id DESC LIMIT 1")["zustand"] == "DIAGNOSING"
    assert fake_llm.calls == []


def test_zweimal_klicken_erzeugt_nicht_zweimal(client, fake_llm,
                                               app_env):
    token = _kind(client, fake_llm, app_env, erzeugen=True)

    _waehle(client, token)
    _waehle(client, token)

    offen = app_env.db.q("SELECT id FROM job WHERE type='lektion_erzeugen' "
                         "AND state IN ('wartend','laeuft')")
    assert len(offen) == 1


def test_eine_unbrauchbare_ausgabe_hinterlaesst_nichts(client, fake_llm,
                                                       app_env):
    """Die Prüfung greift auch hier: lieber keine Lektion als eine falsche."""
    from app.adaptiv import lektionen
    token = _kind(client, fake_llm, app_env, erzeugen=True)
    kaputt = _lektion()
    kaputt["fehlertypen"][0]["aufgaben"]["gefuehrt"]["loesung"] = "999"
    kaputt["fehlertypen"][0]["aufgaben"]["gefuehrt"]["frage"] = "2 + 2 = ?"
    fake_llm.responses["lektion"] = kaputt
    _waehle(client, token)

    run_jobs(app_env, fake_llm)

    # Was zählt, ist nicht der Auftragszustand — Wiederholungen sind
    # Sache der Warteschlange —, sondern dass nichts davon ein Kind
    # erreicht und der Grund festgehalten ist.
    assert lektionen.fuer_thema(THEMA, "mathematik") is None
    assert app_env.db.q("SELECT id FROM lern_konzept WHERE quelle='erzeugt'") == []
    auftrag = app_env.db.q1("SELECT * FROM job WHERE type='lektion_erzeugen'")
    assert auftrag["state"] != "fertig"
    assert "nachgerechnet" in (auftrag["last_error"] or "")


def test_das_wartende_kind_bekommt_eine_auskunft(client, fake_llm,
                                                 app_env):
    token = _kind(client, fake_llm, app_env, erzeugen=True)
    _waehle(client, token)

    noch_nicht = client.get(f"{PFAD}/status", params={"thema": THEMA}).json()
    run_jobs(app_env, fake_llm)
    fertig = client.get(f"{PFAD}/status", params={"thema": THEMA}).json()

    assert noch_nicht["fertig"] is False
    assert fertig["fertig"] is True


# --------------------------------------------------------------------------
# §5: die Lektion geht als eigene Session an den Anbieter
# --------------------------------------------------------------------------

def test_die_lektion_geht_als_lauf_an_den_anbieter(client, fake_llm,
                                                   app_env):
    """Der Anbieter schreibt die Didaktik — als eigener Lauf mit dem
    Lektions-Schema. Eine Modellwahl gibt es im Code nicht; die
    Qualitaetssicherung liegt in `schemas.pruefe_lektion` und der
    Klassenpruefung hinterher."""
    token = _kind(client, fake_llm, app_env, erzeugen=True)
    _waehle(client, token)

    run_jobs(app_env, fake_llm)

    auftraege = [p.get("title", "") for p in fake_llm.devin.created]
    assert any("lektion_erzeugen" in t for t in auftraege), auftraege


def test_die_lektion_bekommt_mehr_luft_als_ein_quiz(app_env):
    """Eine ganze Lernreihe ist um ein Vielfaches laenger als eine Fragerunde
    — mit der Vorgabe von 8192 Token bricht die Antwort mittendrin ab. Und
    weil der Anbieter asynchron antwortet, bekommt der Lauf deutlich mehr Zeit
    als ein synchroner Aufruf je haette."""
    from app import config
    from app.adaptiv import erzeugung

    assert erzeugung.MAX_TOKENS > 8192
    assert config.ops().ai_max_run_seconds > 300


def test_exam_auftrag_ohne_klasse_ist_fuer_das_wartende_kind_sichtbar(app_env):
    """Der Klassenarbeits-Weg ruft `anfordern` ohne Klassenstufe (das Konzept
    bestimmt sie, nicht das Profil). Der Dedup-Schluessel darf trotzdem nicht
    ohne Klasse gebaut werden — sonst sieht `/lernen/adaptiv/status` den
    laufenden Auftrag nicht und das Kind wartet blind."""
    from app.adaptiv import erzeugung
    app_env.config.update(adaptive_learning_enabled=True,
                          llm_error_creation_enabled=True)
    app_env.db.init()

    erzeugung.anfordern("Geschwindigkeit", "physik", None, gebraucht_am="2026-10-15")

    klasse = app_env.config.load().learner_grade
    assert erzeugung.laeuft("Geschwindigkeit", "physik", klasse) is True
    # Und eine zweite Anfrage auf dem Lernweg dedupliziert dagegen:
    assert erzeugung.anfordern("Geschwindigkeit", "physik", klasse) is None
