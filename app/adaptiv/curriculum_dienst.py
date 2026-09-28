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

from .. import jobs, pii, prompts
from . import komponenten, schemas, store

FORMAT_ID = "karo-adaptiv-v1"
MAX_WAIT_SECONDS = 24 * 60 * 60
MAX_RESPONSE_BYTES = 2_000_000


def settings(cfg) -> tuple[str, str]:
    return (os.environ.get("KARO_CURRICULUM_URL", cfg.curriculum_url).strip().rstrip("/"),
            os.environ.get("KARO_CURRICULUM_KEY", cfg.curriculum_key).strip())


def configured(cfg) -> bool:
    # Incomplete configuration must fail closed, never silently generate locally.
    return any(settings(cfg))


def format_spec() -> dict:
    # Stable across topics/grades: these are request fields, not format versions.
    return {"id": FORMAT_ID, "schema": prompts.LEKTION_SCHEMA,
            "registry": komponenten.fuer_modell(),
            "instructions": prompts.lektion_prompt(
                grade="aus der Anfrage", subject="aus der Anfrage",
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


def _checked(result: dict, thema: str, grade: int) -> dict:
    from . import lektionen
    from .normalisierung import normalisiere_thema
    if result.get("format") != FORMAT_ID or not result.get("concept_id") or not result.get("concept_version"):
        raise schemas.InhaltUngueltig("Format oder Inhaltsversion fehlt.")
    lesson = schemas.pruefe_lektion(result.get("lesson"))
    if "erstkontakt" not in lesson:
        raise schemas.InhaltUngueltig("Einstieg in die Lernreihe fehlt.")
    concept = lesson["konzept"]
    if not 1 <= concept["klasse_von"] <= grade <= concept["klasse_bis"] <= 13:
        raise schemas.InhaltUngueltig("Die Lernreihe passt nicht zur Klassenstufe.")
    if not lektionen._trifft(normalisiere_thema(thema), concept):
        raise schemas.InhaltUngueltig("Die Lernreihe passt nicht zum angefragten Thema.")
    # Repeated numerical practice would make apparent success meaningless.
    for fault in lesson["fehlertypen"]:
        questions = [normalisiere_thema(fault["aufgaben"][role]["frage"])
                     for role in ("beispiel", "gefuehrt", "selbststaendig")]
        if len(set(questions)) != len(questions):
            raise schemas.InhaltUngueltig("Beispiel und Übungsaufgaben müssen verschieden sein.")
    return lesson


def import_lesson(cfg, result: dict, thema: str, fach: str, grade: int) -> int:
    from . import erzeugung
    lesson = _checked(result, thema, grade)
    eid = _export_id(result)
    provenance = {"service": settings(cfg)[0], "export_id": eid,
                  "concept_id": result["concept_id"], "version": result["concept_version"],
                  "grade": grade, "subject": fach, "format": FORMAT_ID, "lesson": lesson}
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
    return concept_id


def prepare(cfg, payload: dict, thema: str, fach: str, grade: int) -> dict:
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
    safe_topic = pii.scrub(thema, cfg.learner_name)
    if payload.get("curriculum_export"):
        result = request(cfg, "GET", f"/v1/lessons/{int(payload['curriculum_export'])}")
    else:
        result = request(cfg, "POST", "/v1/lessons", {
            "subject": pii.scrub(fach, cfg.learner_name), "grade": grade,
            "topic": safe_topic, "format": format_spec()})
    status = result.get("status")
    if status == "unavailable":
        raise jobs.PermanentFailure("Das Material ist noch nicht freigegeben oder derzeit nicht verfügbar.")
    eid = _export_id(result)
    payload["curriculum_export"] = eid
    if status == "pending":
        delay = result.get("retry_after", 15)
        raise jobs.Deferred(payload, delay if type(delay) is int else 15)
    if status != "ready":
        raise jobs.PermanentFailure("Unbekannter Curriculum-Auftragsstatus.")
    try:
        cid = import_lesson(cfg, result, safe_topic, fach, grade)
    except (schemas.InhaltUngueltig, ValueError, TypeError, KeyError):
        # Stable, non-sensitive reason; no child text or model payload in logs.
        if payload.get("curriculum_rejections", 0) >= 2:
            raise jobs.PermanentFailure("Das Material braucht eine fachliche Überprüfung.") from None
        revised = request(cfg, "POST", f"/v1/lessons/{eid}/reject", {
            "reason": "Lokale Karo-Prüfung fehlgeschlagen: Schema, Einstieg, Klasse, "
                      "Themenzuordnung, Rechenlösung oder getrennte Übungsaufgaben prüfen."})
        if revised.get("status") == "unavailable":
            raise jobs.PermanentFailure("Das Material braucht eine fachliche Überprüfung.") from None
        payload["curriculum_export"] = _export_id(revised)
        payload["curriculum_rejections"] = payload.get("curriculum_rejections", 0) + 1
        raise jobs.Deferred(payload) from None
    return {"konzept_id": cid, "thema": thema, "quelle": "curriculum"}
