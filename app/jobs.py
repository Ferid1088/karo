"""Job-Warteschlange.

Kein Redis, kein Celery: eine Tabelle und ein Hintergrund-Thread. Jobs stehen
in der Datenbank und ueberleben deshalb einen Neustart des Containers.

Wiederholungen laufen mit wachsendem Abstand. Ohne das verbraucht eine
Ratenbegrenzung von Anthropic — deren Meldung lautet "in ein paar Minuten
erneut versuchen" — alle drei Versuche innerhalb von Millisekunden.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import threading
from typing import Callable

from . import config, db

log = logging.getLogger("karo.jobs")

HANDLERS: dict[str, Callable[[dict], None]] = {}
_OPS = config.ops()
MAX_ATTEMPTS = _OPS.jobs_max_attempts
POLL_SECONDS = _OPS.jobs_poll_seconds
RETRY_DELAYS = _OPS.jobs_retry_delays  # Sekunden vor dem 2. und 3. Versuch

_stop = threading.Event()
_thread: threading.Thread | None = None


class Deferred(Exception):
    """Externer Auftrag läuft noch: dauerhaft parken, keinen Versuch verbrauchen."""

    def __init__(self, payload: dict, seconds: int = 15):
        self.payload = payload
        self.seconds = max(_OPS.jobs_defer_min_seconds,
                           min(int(seconds), _OPS.jobs_defer_max_seconds))


class PermanentFailure(Exception):
    """Erneutes automatisches Probieren würde denselben gesperrten Auftrag wiederholen."""


def _defer(job_id: int, deferred: Deferred) -> None:
    with db.tx() as c:
        c.execute("UPDATE job SET state='wartend', payload=?, not_before=?, "
                  "attempts=MAX(0, attempts-1), last_error=NULL WHERE id=?",
                  (json.dumps(deferred.payload, ensure_ascii=False),
                   _in(deferred.seconds), job_id))


def _fail_permanently(job_id: int, error: str) -> None:
    with db.tx() as c:
        c.execute("UPDATE job SET state='fehler', last_error=?, finished_at=?, "
                  "not_before=NULL WHERE id=?", (error[:500], db.now(), job_id))


def handler(job_type: str):
    def deco(fn):
        HANDLERS[job_type] = fn
        return fn
    return deco


def _in(seconds: int) -> str:
    return (dt.datetime.now(dt.timezone.utc)
            + dt.timedelta(seconds=seconds)).isoformat(timespec="seconds")


def enqueue(job_type: str, payload: dict | None = None,
            dedup_key: str | None = None) -> int | None:
    with db.tx() as c:
        return enqueue_in_transaction(c, job_type, payload, dedup_key)


def enqueue_in_transaction(c, job_type: str, payload: dict | None = None,
                           dedup_key: str | None = None) -> int | None:
    """Job und zugehörige Zustandsänderung gemeinsam dauerhaft speichern."""
    if job_type not in HANDLERS:
        raise ValueError(f"Unbekannter Job-Typ: {job_type}")
    payload = payload or {}
    if dedup_key:
        row = c.execute(
            "SELECT id, state FROM job WHERE dedup_key = ?", (dedup_key,)
        ).fetchone()
        if row is not None:
            if row["state"] in ("wartend", "laeuft"):
                return None
            c.execute("UPDATE job SET dedup_key = NULL WHERE id = ?", (row["id"],))
    cur = c.execute(
        """INSERT INTO job (type, payload, state, dedup_key, created_at)
           VALUES (?, ?, 'wartend', ?, ?)""",
        (job_type, json.dumps(payload, ensure_ascii=False), dedup_key, db.now()),
    )
    return cur.lastrowid

def _claim() -> dict | None:
    with db.tx() as c:
        row = c.execute(
            """SELECT * FROM job
                WHERE state = 'wartend'
                  AND (not_before IS NULL OR not_before <= ?)
                ORDER BY id LIMIT 1""",
            (db.now(),),
        ).fetchone()
        if row is None:
            return None
        c.execute(
            "UPDATE job SET state='laeuft', attempts=attempts+1, started_at=? WHERE id=?",
            (db.now(), row["id"]),
        )
        return dict(row)


def _finish(job_id: int, error: str | None) -> None:
    with db.tx() as c:
        row = c.execute("SELECT attempts FROM job WHERE id = ?", (job_id,)).fetchone()
        attempts = row["attempts"] if row else MAX_ATTEMPTS
        if error is None:
            c.execute(
                "UPDATE job SET state='fertig', last_error=NULL, finished_at=?, "
                "not_before=NULL WHERE id=?",
                (db.now(), job_id),
            )
        elif attempts >= MAX_ATTEMPTS:
            c.execute(
                "UPDATE job SET state='fehler', last_error=?, finished_at=? WHERE id=?",
                (error, db.now(), job_id),
            )
        else:
            delay = RETRY_DELAYS[min(attempts - 1, len(RETRY_DELAYS) - 1)]
            c.execute(
                "UPDATE job SET state='wartend', last_error=?, not_before=? WHERE id=?",
                (error, _in(delay), job_id),
            )


def run_once() -> bool:
    """Verarbeitet hoechstens einen Job. True, wenn etwas getan wurde."""
    job = _claim()
    if job is None:
        return False

    fn = HANDLERS.get(job["type"])
    if fn is None:
        _finish(job["id"], f"Unbekannter Job-Typ: {job['type']}")
        return True
    try:
        payload = json.loads(job["payload"] or "{}")
    except json.JSONDecodeError:
        _finish(job["id"], "Payload ist kein gültiges JSON")
        return True

    try:
        _laufe(job["id"], fn, payload)
    except Deferred as deferred:
        _defer(job["id"], deferred)
    except PermanentFailure as exc:
        _fail_permanently(job["id"], str(exc))
    except Exception as exc:
        _fehlerlog(job["id"], job["type"], job["attempts"] + 1, exc)
        _finish(job["id"], f"{type(exc).__name__}: {exc}"[:500])
    else:
        _finish(job["id"], None)
    return True


def _laufe(job_id: int, fn, payload: dict):
    """Handler unter der Job-Identitaet laufen lassen: jede Logzeile darin
    traegt `job_id`, abgehende Dienst-Aufrufe `job-<id>` als Korrelation."""
    from .observability import context
    token = context.job_beginne(job_id)
    try:
        return fn(payload)
    finally:
        context.job_ende(token)


def _fehlerlog(job_id: int, job_type: str, attempts: int, exc: Exception) -> None:
    """Ein Eintrag, der in Produktion voll zaehlt: Typ, Versuch und der
    komplette Traceback stehen in derselben Zeile — nicht auf DEBUG."""
    try:
        log.warning("Job %s (%s) fehlgeschlagen: %s", job_id, job_type, exc,
                    exc_info=exc,
                    extra={"fach": {"event": "job_failed", "job_id": job_id,
                                    "job_type": job_type,
                                    "attempts": attempts}})
    except Exception:
        pass


def _loop() -> None:
    log.info("Job-Worker gestartet")
    while not _stop.is_set():
        try:
            worked = run_once()
        except Exception:                        # pragma: no cover
            log.exception("Worker-Schleife: unerwarteter Fehler")
            worked = False
        if not worked:
            _stop.wait(POLL_SECONDS)
    log.info("Job-Worker beendet")


def start() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="karo-jobs", daemon=True)
    _thread.start()


def stop(timeout: float = _OPS.jobs_stop_timeout_seconds) -> None:
    _stop.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=timeout)


def recover_stuck() -> int:
    """Setzt Jobs zurueck, die beim letzten Absturz auf 'laeuft' stehen blieben."""
    with db.tx() as c:
        cur = c.execute(
            """UPDATE job
                  SET state = CASE WHEN attempts >= ? THEN 'fehler' ELSE 'wartend' END,
                      last_error = COALESCE(last_error, 'Beim Neustart unterbrochen'),
                      not_before = NULL
                WHERE state = 'laeuft'""",
            (MAX_ATTEMPTS,),
        )
        return cur.rowcount


def run_now(job_id: int) -> tuple[str, object]:
    """Verarbeitet einen bestimmten Job sofort, im aufrufenden Thread, mit
    denselben Erfolgs-/Fehler-/Backoff-Regeln wie `run_once()`.

    Fuer Faelle, in denen eine laufende Anfrage die Arbeit lieber gleich
    selbst erledigt (bessere Rueckmeldung, kein Warten auf den naechsten
    Umlauf) statt sie dem Hintergrund-Worker zu ueberlassen — siehe
    quizzes.freigeben()/services/workflow.py, change.txt Aufgabe P2. Der
    Job bleibt trotzdem die alleinige Quelle der Wahrheit: stuerzt der
    Aufrufer ab, bevor er hier ankommt, findet der Hintergrund-Worker den
    Job unveraendert in 'wartend' vor (oder 'laeuft', das `recover_stuck()`
    beim naechsten Start zuruecksetzt) und erledigt ihn stattdessen.

    Gibt (status, ergebnis) zurueck. status ist:
      'done'    — erfolgreich verarbeitet; `ergebnis` ist der Rueckgabewert
                  des Handlers.
      'pending' — externer Auftrag läuft; nächster Abruf ist dauerhaft geplant.
      'failed'  — der Handler hat eine Ausnahme geworfen (oder Payload/Typ
                  waren ungueltig); der Job wurde wie ueblich fuer eine
                  spaetere Wiederholung vorgemerkt. `ergebnis` ist None.
      'skipped' — der Job stand nicht mehr auf 'wartend' (z. B. weil der
                  Hintergrund-Worker ihn gerade in diesem Moment schon
                  beansprucht hat). `ergebnis` ist None.
    """
    with db.tx() as c:
        row = c.execute(
            "SELECT * FROM job WHERE id=? AND state='wartend'", (job_id,)
        ).fetchone()
        if row is None:
            return ("skipped", None)
        c.execute(
            "UPDATE job SET state='laeuft', attempts=attempts+1, started_at=? WHERE id=?",
            (db.now(), job_id),
        )
        job = dict(row)

    fn = HANDLERS.get(job["type"])
    if fn is None:
        _finish(job_id, f"Unbekannter Job-Typ: {job['type']}")
        return ("failed", None)
    try:
        payload = json.loads(job["payload"] or "{}")
    except json.JSONDecodeError:
        _finish(job_id, "Payload ist kein gültiges JSON")
        return ("failed", None)

    try:
        ergebnis = _laufe(job_id, fn, payload)
    except Deferred as deferred:
        _defer(job_id, deferred)
        return ("pending", None)
    except PermanentFailure as exc:
        _fail_permanently(job_id, str(exc))
        return ("failed", None)
    except Exception as exc:
        _fehlerlog(job_id, job["type"], job["attempts"] + 1, exc)
        _finish(job_id, f"{type(exc).__name__}: {exc}"[:500])
        return ("failed", None)
    _finish(job_id, None)
    return ("done", ergebnis)


def retry(job_id: int) -> bool:
    with db.tx() as c:
        cur = c.execute(
            """UPDATE job SET state='wartend', attempts=0, not_before=NULL
                WHERE id=? AND state='fehler'""",
            (job_id,),
        )
        return cur.rowcount > 0


def counts() -> dict[str, int]:
    return {r["state"]: r["n"]
            for r in db.q("SELECT state, COUNT(*) AS n FROM job GROUP BY state")}


def fehlgeschlagen(limit: int = 20) -> list[dict]:
    """Zuletzt endgueltig gescheiterte Jobs — fuer die Eltern-Uebersicht,
    die daneben einen "Erneut versuchen"-Knopf anbietet (siehe retry())."""
    return [dict(r) for r in db.q(
        "SELECT * FROM job WHERE state='fehler' ORDER BY id DESC LIMIT ?", limit)]
