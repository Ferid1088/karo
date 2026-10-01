"""DB-first bridge to Karo Curriculum; no learner history leaves this app.

The service owns content. Karo owns sessions, calendars and mastery. A pending
response parks the persistent job instead of blocking the worker or spending
its retry budget. Imported exports are immutable, locally checked snapshots.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import karo_contract
from karo_contract import VertragVerletzt

from .. import jobs, pii, prompts
from . import komponenten, schemas, store

FORMAT_ID = karo_contract.FORMAT_ID
MAX_WAIT_SECONDS = 24 * 60 * 60
MAX_RESPONSE_BYTES = 2_000_000


def settings(cfg) -> tuple[str, str]:
    return (os.environ.get("KARO_CURRICULUM_URL", cfg.curriculum_url).strip().rstrip("/"),
            os.environ.get("KARO_CURRICULUM_KEY", cfg.curriculum_key).strip())


#: Die Fassung des Vertrags mit dem Lehrplan-Dienst. Muss zu dessen
#: CONTRACT_VERSION passen. Laufen sie auseinander, wird ein Auftrag
#: zurueckgestellt — niemals abgelehnt: eine Ablehnung zaehlt beim Dienst
#: gegen das Thema und hat es schon einmal dauerhaft unlieferbar gemacht,
#: obwohl am Inhalt nichts falsch war. Steht in `karo_contract`, weil der
#: Dienst dieselbe Angabe braucht.
CONTRACT_VERSION = karo_contract.CONTRACT_VERSION


def betrieb_melden(text: str) -> None:
    """Haelt eine Betriebsstoerung fest, die ein Mensch sehen muss.

    Ein zurueckgestellter Auftrag sieht von aussen aus wie ein langsamer —
    ohne diese Meldung wartet eine Familie auf etwas, das nie kommt.
    """
    from .. import db
    with db.tx() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS betriebsmeldung (
            id INTEGER PRIMARY KEY, bereich TEXT NOT NULL, text TEXT NOT NULL,
            zuerst_am TEXT NOT NULL, zuletzt_am TEXT NOT NULL, anzahl INTEGER NOT NULL DEFAULT 1,
            UNIQUE(bereich, text))""")
        c.execute("""INSERT INTO betriebsmeldung(bereich,text,zuerst_am,zuletzt_am)
                     VALUES('lehrplan-dienst',?,?,?)
                     ON CONFLICT(bereich,text) DO UPDATE
                       SET zuletzt_am=excluded.zuletzt_am, anzahl=anzahl+1""",
                  (text, db.now(), db.now()))


def meta(cfg) -> dict:
    """Vertragsfassung und Stand des Dienstes. Ohne Schluessel abrufbar."""
    return request(cfg, "GET", "/v1/meta")


def vertrag_passt(cfg) -> tuple[bool, str]:
    """Reden beide dieselbe Fassung? Gibt (ja, Begruendung) zurueck."""
    try:
        angaben = meta(cfg)
    except Exception as exc:  # noqa: BLE001 - jede Stoerung heisst hier "noch nicht wissen"
        return False, f"Der Lehrplan-Dienst meldet seine Vertragsfassung nicht ({exc})."
    fremd = angaben.get("contract_version")
    if fremd == CONTRACT_VERSION:
        return True, ""
    return False, (f"Karo spricht {CONTRACT_VERSION}, der Lehrplan-Dienst {fremd or '(keine Angabe)'}"
                   f" (Stand {angaben.get('git_sha', 'unbekannt')}). Solange das so ist, nimmt Karo "
                   "keine Lieferungen an — der Dienst muss auf denselben Stand gebracht werden.")


def wirkung_melden(cfg) -> int:
    """Wirkungslose Erklaerungen dem Lehrplan-Dienst melden (Z10).

    Es geht ausschliesslich um Zahlen: welches Konzept, welche Fehlvorstellung,
    welche Erklaerungs-ID, wie oft ausgeliefert und wie oft danach eine
    richtige Antwort kam. Kein Name, kein Thema eines Kindes, keine Antwort —
    der Dienst braucht das nicht, um eine Erklaerung neu zu schreiben, und
    was er nicht braucht, bekommt er nicht.

    Gibt zurueck, wie viele gemeldet wurden.
    """
    from . import store
    if not configured(cfg):
        return 0
    befunde = store.wirkungslose_erklaerungen(cfg)
    if not befunde:
        return 0
    passt, grund = vertrag_passt(cfg)
    if not passt:
        betrieb_melden(grund)
        return 0
    try:
        request(cfg, "POST", "/v1/explanations/feedback",
                {"format": FORMAT_ID, "befunde": befunde})
    except Exception as fehler:          # noqa: BLE001 - eine Meldung darf nichts aufhalten
        betrieb_melden(f"Wirkungsmeldung an den Lehrplan-Dienst nicht moeglich: {fehler}")
        return 0
    store.wirkung_gemeldet([b["erklaerung_id"] for b in befunde])
    return len(befunde)


def configured(cfg) -> bool:
    # Incomplete configuration must fail closed, never silently generate locally.
    return any(settings(cfg))


def format_spec() -> dict:
    # Stable across topics/grades: these are request fields, not format versions.
    return {"id": FORMAT_ID, "schema": prompts.LEKTION_SCHEMA,
            "registry": komponenten.fuer_modell(),
            "instructions": prompts.lektion_prompt(
                grade=None, subject="aus der Anfrage",
                thema="das angefragte Konzept")}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward the API key to another host.


def request(cfg, method: str, path: str, body: dict | None = None) -> dict:
    url, key = settings(cfg)
    parsed = urlsplit(url)
    if (not key.startswith("kc_") or not key.isascii() or any(c.isspace() for c in key)
            or parsed.scheme not in ("http", "https") or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise jobs.PermanentFailure("Curriculum-Verbindung ist nicht vollständig eingerichtet.")
    if parsed.scheme == "http" and parsed.hostname not in (
            "localhost", "127.0.0.1", "::1", "curriculum-api"):
        raise jobs.PermanentFailure("Der externe Curriculum-Dienst benötigt HTTPS.")
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = Request(url + path, data=data, method=method, headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json",
        "Accept": "application/json"})
    try:
        with build_opener(_NoRedirect()).open(req, timeout=8) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise jobs.PermanentFailure("Curriculum-Antwort ist zu groß.")
        result = json.loads(raw)
    except HTTPError as exc:
        if exc.code in (408, 429) or exc.code >= 500:
            raise RuntimeError("Curriculum-Dienst ist vorübergehend nicht erreichbar.") from None
        raise jobs.PermanentFailure(f"Curriculum-Anfrage abgewiesen (HTTP {exc.code}).") from None
    except (URLError, TimeoutError, OSError):
        raise RuntimeError("Curriculum-Dienst ist vorübergehend nicht erreichbar.") from None
    except (ValueError, UnicodeError):
        raise jobs.PermanentFailure("Curriculum-Dienst liefert kein gültiges JSON.") from None
    if not isinstance(result, dict):
        raise jobs.PermanentFailure("Curriculum-Antwort hat ein ungültiges Format.")
    return result


def _export_id(result: dict) -> int:
    value = result.get("export_id")
    if type(value) is not int or value <= 0:
        raise jobs.PermanentFailure("Curriculum-Antwort enthält keine gültige Auftragsnummer.")
    return value


def _checked(result: dict, thema: str, grade: int, fach: str) -> dict:
    """Die Pruefung, die auch der Lehrplan-Dienst faehrt.

    Sie stand frueher hier — und eine zweite, etwas andere beim Dienst. Der
    gab frei, Karo lehnte ab, und nach zwei Ablehnungen war das Thema
    dauerhaft leer. Jetzt ist es dieselbe Funktion aus `karo_contract`, die
    der Dienst installiert und aufruft, bevor eine Lektion „fertig" wird.
    """
    return karo_contract.pruefe(result, thema=thema, fach=fach)


def import_lesson(cfg, result: dict, thema: str, fach: str, grade: int) -> int:
    from . import erzeugung
    lesson = _checked(result, thema, grade, fach)
    eid = _export_id(result)
    provenance = {"service": settings(cfg)[0], "export_id": eid,
                  "concept_id": result["concept_id"], "version": result["concept_version"],
                  "classification": result['classification'],
                  "subject": fach, "format": FORMAT_ID, "lesson": lesson}
    fingerprint = hashlib.sha256(json.dumps(provenance, sort_keys=True,
                                            ensure_ascii=False).encode()).hexdigest()
    previous = store.curriculum_import(fingerprint)
    if previous:
        return previous["konzept_id"]
    # Different content/version never overwrites an active session's material.
    lesson = copy.deepcopy(lesson)
    lesson["konzept"]["konzept_key"] = "curriculum-" + fingerprint
    concept_id = erzeugung.speichern(lesson, fach=fach, quelle="curriculum")
    store.curriculum_import_sichern(fingerprint, concept_id, provenance)
    # Voraussetzungen kommen mit der Lieferung (Vertrag 1.4, Z3). Ohne sie
    # bleibt bei einem Kind, das haengt, nur die Eskalation — auch wenn in
    # Wahrheit nur eine Voraussetzung fehlt.
    store.voraussetzungen_sichern(concept_id, karo_contract.voraussetzungen(result))
    return concept_id


def prepare(cfg, payload: dict, thema: str, fach: str, grade: int) -> dict:
    from ..faecher import pflicht
    fach = pflicht(fach)
    payload = dict(payload)
    payload.update(fach=fach, klasse=grade)
    # Pin routing for resumed jobs. A configuration change cannot send an old ID
    # to a different server (nor switch it to the local generator).
    url = settings(cfg)[0]
    if payload.get("curriculum_service", url) != url:
        raise jobs.PermanentFailure("Curriculum-Verbindung wurde während der Vorbereitung geändert.")
    payload["curriculum_service"] = url
    payload.setdefault("curriculum_started", time.time())
    if time.time() - payload["curriculum_started"] > MAX_WAIT_SECONDS:
        raise jobs.PermanentFailure("Die Vorbereitung dauert zu lange. Bitte später erneut starten.")
    # Vor jedem Auftrag: reden beide dieselbe Vertragsfassung? Wenn nicht,
    # wird zurueckgestellt statt geliefert und abgelehnt. Eine Ablehnung
    # zaehlt beim Dienst gegen das Thema, und zwei davon machen es dauerhaft
    # unlieferbar — ein Versionsunterschied darf das nicht ausloesen.
    passt, grund = vertrag_passt(cfg)
    if not passt:
        betrieb_melden(grund)
        raise jobs.Deferred(payload, 300)
    safe_topic = pii.scrub(thema, cfg.learner_name)
    if payload.get("curriculum_export"):
        result = request(cfg, "GET", f"/v1/lessons/{int(payload['curriculum_export'])}")
    else:
        # Wie viele neue Themen diese Familie heute bestellt. Der Dienst
        # bekommt keine Familienkennung und koennte das gar nicht wissen —
        # die Grenze gehoert deshalb hierher. Siehe services/topic_budget.py.
        from ..services import topic_budget
        schluessel = f"{fach}:{grade}:{safe_topic}"
        if not topic_budget.buchen(schluessel):
            payload["budget_wartet"] = True
            raise jobs.Deferred(payload, 300)
        payload["budget_schluessel"] = schluessel
        payload.pop("budget_wartet", None)
        anfrage = {
            # Nur der Schlüssel des aktiven Fachs: der Dienst sucht in genau
            # diesem Curriculum. Mehr verlässt die App nicht.
            "subject": fach, "grade": grade, "topic": safe_topic, "format": format_spec()}
        if payload.get("gebraucht_am"):
            # Das Datum der Klassenarbeit — kein Kinderdatum, nur ein Tag.
            # Der Dienst sortiert danach seine Schlange: sonst wartet das
            # Thema fuer die Arbeit am Freitag hinter dem fuer die Arbeit in
            # drei Wochen.
            anfrage["needed_by"] = payload["gebraucht_am"]
        result = request(cfg, "POST", "/v1/lessons", anfrage)
    status = result.get("status")
    if status == "ready" and payload.get("budget_schluessel"):
        # Der Dienst hatte es schon fertig. Das kostet ihn nichts, also
        # zaehlt es auch nicht gegen die Familie.
        from ..services import topic_budget
        topic_budget.freigeben(payload.pop("budget_schluessel"))
    if status == "unavailable":
        # "Nicht verfuegbar" heisst meistens "gerade nicht": der Dienst
        # drosselt, wenn viele Themen auf einmal kommen. Das als endgueltig
        # zu behandeln hat bei siebzehn Prüfungsthemen die ersten vier
        # Auftraege sofort getoetet, obwohl Sekunden spaeter wieder
        # ausgeliefert wurde. Endgueltig ist nur, was der Dienst auch so
        # nennt: was Karo selbst abgelehnt hat, bekommt es nicht wieder.
        # Die Gesamtdauer deckelt MAX_WAIT_SECONDS weiter oben.
        if result.get("reason_code") == "rejected_by_client":
            raise jobs.PermanentFailure(
                "Für dieses Thema hat der Lehrplan-Dienst nichts Geprüftes mehr: "
                "Karos Prüfung hat das gelieferte Material abgelehnt.")
        payload.pop("curriculum_export", None)
        raise jobs.Deferred(payload, result.get("retry_after")
                            if type(result.get("retry_after")) is int else 60)
    eid = _export_id(result)
    payload["curriculum_export"] = eid
    if status == "pending":
        # Platz in der Schlange und Schaetzung mitnehmen: die Eltern sehen
        # sonst nur „wird vorbereitet" und koennen das nicht von „haengt"
        # unterscheiden.
        for feld in ("position", "waiting", "seconds"):
            if type(result.get(feld)) is int:
                payload[f"curriculum_{feld}"] = result[feld]
        # Der Dienst sagt, ab wann es weitergeht, wenn sein Kontingent
        # erschoepft ist. „Wird vorbereitet" ohne diese Angabe hiesse fuer
        # eine Familie: alle 15 Sekunden nachsehen, bis morgen frueh.
        if isinstance(result.get("paused_until"), str):
            payload["curriculum_pausiert_bis"] = result["paused_until"][:19]
        delay = result.get("retry_after", 15)
        raise jobs.Deferred(payload, delay if type(delay) is int else 15)
    if status != "ready":
        raise jobs.PermanentFailure("Unbekannter Curriculum-Auftragsstatus.")
    try:
        cid = import_lesson(cfg, result, safe_topic, fach, grade)
    except VertragVerletzt as verstoss:
        # Die Huelle passt nicht. Das dem Dienst als Inhaltsmangel zu melden
        # war der Fehler: zwei solche Meldungen und das Thema war fuer Karo
        # dauerhaft tot, obwohl an der Lektion nie etwas falsch war. Jetzt
        # geht es als Vertragsverstoss hin, zaehlt dort nicht, und hier
        # sieht ein Mensch, dass jemand die Schnittstelle richten muss.
        betrieb_melden(f"Der Lehrplan-Dienst liefert eine Antwort, die nicht zum Vertrag passt: {verstoss}")
        request(cfg, "POST", f"/v1/lessons/{eid}/reject",
                {"reason": f"Vertrag {CONTRACT_VERSION}: {verstoss}", "reason_code": "contract"})
        raise jobs.Deferred(payload, 300) from None
    except (schemas.InhaltUngueltig, ValueError, TypeError, KeyError):
        # Stable, non-sensitive reason; no child text or model payload in logs.
        if payload.get("curriculum_rejections", 0) >= 2:
            raise jobs.PermanentFailure("Das Material braucht eine fachliche Überprüfung.") from None
        revised = request(cfg, "POST", f"/v1/lessons/{eid}/reject", {
            "reason": "Lokale Karo-Prüfung fehlgeschlagen: Schema, Einstieg, Klasse, "
                      "Themenzuordnung, Rechenlösung oder getrennte Übungsaufgaben prüfen.",
            "reason_code": "content"})
        if revised.get("status") == "unavailable":
            raise jobs.PermanentFailure("Das Material braucht eine fachliche Überprüfung.") from None
        payload["curriculum_export"] = _export_id(revised)
        payload["curriculum_rejections"] = payload.get("curriculum_rejections", 0) + 1
        raise jobs.Deferred(payload) from None
    return {"konzept_id": cid, "thema": thema, "quelle": "curriculum"}
