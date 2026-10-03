"""Der Fulfillment-Loop: `lern_inhalt_anfrage` → Dienst → Import → erfuellt.

Eine Luecke, die ein Kind im Unterricht anstoesst, wird zur Bestellung beim
Lehrplan-Dienst; die gepruefte Lieferung wird importiert und schliesst die
Bestellung. Laueft der Dienst nicht, bleibt alles offen — der Unterricht
merkt davon nichts. Kein Netz, kein Modell: der HTTP-Aufruf ist gestellt.
"""
import pytest

from .test_lektion_erzeugung import _lektion


@pytest.fixture
def dienst(app_env, monkeypatch):
    """Eingerichtete, vertragstreue Verbindung — wie `bridge` in
    test_curriculum_bridge, nur fuer die Bestellstrecke."""
    monkeypatch.delenv("KARO_CURRICULUM_URL", raising=False)
    monkeypatch.delenv("KARO_CURRICULUM_KEY", raising=False)
    from app.adaptiv import curriculum_dienst as service, store
    app_env.db.init()
    store.init()
    app_env.config.update(curriculum_url="http://127.0.0.1:8088",
                          curriculum_key="kc_test_secret",
                          learner_name="Lena", learner_grade=6)
    monkeypatch.setattr(service, "meta", lambda cfg: {
        "contract_version": service.CONTRACT_VERSION, "git_sha": "test",
        "formats": [service.FORMAT_ID]})
    return service


def _ready(version=1):
    return {"status": "ready", "export_id": 17, "format": "karo-adaptiv-v1",
            "concept_id": "MA.GEO.WUERFEL", "concept_version": version,
            "subject": "mathematik",
            "classification": {"source": "approved_curriculum",
                               "first_contact_grade": 5, "target_grade": 7},
            "lesson": _lektion()}


def _anfrage(**kw):
    from app.adaptiv import store
    return store.inhalt_anfordern(
        kw.get("fach", "mathematik"), kw.get("key", "MA.GEO.WUERFEL"),
        kw.get("rolle", "aufgabe"), kw.get("grund", "erschoepft"),
        kontext=kw.get("kontext", {"klasse": 6, "niveau": 1}))


def test_neue_luecke_wird_bestellt_und_verknuepft(dienst, monkeypatch):
    """Erster Lauf: die Bestellung geht raus, die Auftragsnummer des
    Dienstes haengt am Datensatz — kein Kind wartet auf den Rückweg."""
    calls = []
    def antwort(cfg, method, path, body=None):
        calls.append((method, path, body))
        return {"status": "pending", "export_id": 17, "retry_after": 15}
    monkeypatch.setattr(dienst, "request", antwort)
    cfg = None
    import app.config as _c
    cfg = _c.load_safe()
    zeile = _anfrage()
    assert dienst.anfragen_bedienen(cfg) == {"bedient": 0}
    from app.adaptiv import store
    offen = store.inhalt_anfragen("offen")
    assert offen[0]["external_ref"] == "17"
    method, path, body = calls[0]
    assert (method, path) == ("POST", "/v1/lessons")
    assert body["topic"] == "MA.GEO.WUERFEL"
    assert body["subject"] == "mathematik"
    # Der Kontext bleibt fachlich: Rolle und Grund, kein Kindername.
    assert body["requested_role"] == "aufgabe"
    assert "Lena" not in str(body)


def test_laufende_bestellung_wird_nur_abgeholt(dienst, monkeypatch):
    """Zweiter Lauf: dieselbe Bestellung nicht noch einmal aufgeben,
    sondern ihren Stand fragen."""
    calls = []
    def antwort(cfg, method, path, body=None):
        calls.append((method, path))
        return {"status": "pending", "export_id": 17, "retry_after": 15}
    monkeypatch.setattr(dienst, "request", antwort)
    from app.adaptiv import store
    zeile = _anfrage()
    store.inhalt_anfrage_verknuepfen(zeile["id"], 17)
    import app.config as _c
    dienst.anfragen_bedienen(_c.load_safe())
    assert calls == [("GET", "/v1/lessons/17")]


def test_fertige_lieferung_schliesst_die_luecke(dienst, monkeypatch):
    """`ready` → Import → `erfuellt` mit dem neuen Konzept: die Bestellung
    ist abgeschlossen, das Material ist ab jetzt im Katalog."""
    monkeypatch.setattr(dienst, "request", lambda *a, **kw: _ready())
    from app.adaptiv import store
    zeile = _anfrage()
    store.inhalt_anfrage_verknuepfen(zeile["id"], 17)
    import app.config as _c
    assert dienst.anfragen_bedienen(_c.load_safe()) == {"bedient": 1}
    erfuellt = [z for z in store.inhalt_anfragen("erfuellt")
                if z["id"] == zeile["id"]]
    assert erfuellt and erfuellt[0]["konzept_id"]
    assert store.konzept(erfuellt[0]["konzept_id"])["quelle"] == "curriculum"


def test_dienst_offen_bleibt_offen_bei_ausfall(dienst, monkeypatch):
    """Ausfall ist ein Betriebszustand, kein Ergebnis: die Bestellung
    bleibt offen und der Lauf endet ohne Fehler nach oben."""
    monkeypatch.setattr(dienst, "request",
                        lambda *a, **kw: (_ for _ in ()).throw(
                            RuntimeError("nicht erreichbar")))
    zeile = _anfrage()
    import app.config as _c
    assert dienst.anfragen_bedienen(_c.load_safe()) == {"bedient": 0}
    from app.adaptiv import store
    assert store.inhalt_anfragen("offen")[0]["id"] == zeile["id"]


def test_drosselung_loest_die_verknuepfung(dienst, monkeypatch):
    """`unavailable` ohne Endverweis: der Dienst drosselt — naechster
    Lauf bestellt neu statt eine tote Nummer zu befragen."""
    monkeypatch.setattr(dienst, "request", lambda *a, **kw:
                        {"status": "unavailable"})
    from app.adaptiv import store
    zeile = _anfrage()
    store.inhalt_anfrage_verknuepfen(zeile["id"], 17)
    import app.config as _c
    dienst.anfragen_bedienen(_c.load_safe())
    offen = store.inhalt_anfragen("offen")[0]
    assert offen["external_ref"] is None


def test_endgueltige_ablehnung_verwirft(dienst, monkeypatch):
    """Was Karos eigene Pruefung abgelehnt hat, liefert der Dienst nicht
    wieder: verworfen statt endlos gepollt."""
    monkeypatch.setattr(dienst, "request", lambda *a, **kw:
                        {"status": "unavailable",
                         "reason_code": "rejected_by_client"})
    zeile = _anfrage()
    import app.config as _c
    dienst.anfragen_bedienen(_c.load_safe())
    from app.adaptiv import store
    assert store.inhalt_anfragen("verworfen")[0]["id"] == zeile["id"]


def test_kaputte_lieferung_wird_abgelehnt_und_verworfen(dienst, monkeypatch):
    """Eine Lieferung, die Karos Pruefung nicht besteht, geht als
    Befund zurueck und schliesst die Luecke nicht still."""
    schlecht = _ready()
    del schlecht["lesson"]["erstkontakt"]
    calls = []
    def antwort(cfg, method, path, body=None):
        calls.append(path)
        return ({"status": "pending", "export_id": 18}
                if path.endswith("/reject") else schlecht)
    monkeypatch.setattr(dienst, "request", antwort)
    from app.adaptiv import store
    zeile = _anfrage()
    store.inhalt_anfrage_verknuepfen(zeile["id"], 17)
    import app.config as _c
    dienst.anfragen_bedienen(_c.load_safe())
    assert "/v1/lessons/17/reject" in calls
    assert store.inhalt_anfragen("verworfen")[0]["id"] == zeile["id"]
    assert not app_env_db_konzepte(dienst)


def app_env_db_konzepte(dienst):
    from app import db
    return db.q("SELECT id FROM lern_konzept WHERE quelle='curriculum'")


def test_erneute_luecke_oeffnet_erfuellte_bestellung(dienst):
    """Trifft das Material die Luecke nicht, stellt ein erneutes Anfallen
    wieder eine offene Bestellung — kein dauerhaftes „erledigt"-Label."""
    from app.adaptiv import store
    zeile = _anfrage()
    store.inhalt_erfuellt(zeile["id"])
    wieder = _anfrage()
    assert wieder["id"] == zeile["id"]
    assert wieder["status"] == "offen"
    assert wieder["external_ref"] is None
    assert wieder["anzahl"] == 2


def test_bestellung_loest_hintergrundlauf_aus(dienst):
    """Jede neue Lueckenmeldung stellt den Bestelljob — sonst waere die
    Anfrage eine Zeile, die niemand liest."""
    _anfrage()
    from app import db
    jobs = db.q("SELECT type, dedup_key FROM job WHERE type='inhalt_anfragen'")
    assert jobs and jobs[0]["dedup_key"] == "inhalt_anfragen"
