"""Der Lernzyklus.

Eine Lerneinheit gehört zu genau einem Thema und läuft in Runden, bis die
Flagge grün ist oder die Obergrenze erreicht wurde:

    Runde N
      1. Material sammeln   — Wissensbasis, dazu freigegebene Fundstellen
      2. Erklärung schreiben — Folien mit Sprechtext, verankert im Material
      3. GEGENPRÜFUNG       — passt die Erklärung zum Schulmaterial?
      4. Rendern            — HTML, MP4 oder NotebookLM (Wahl je Einheit)
      5. Kind lernt
      6. Verständnisfragen  — 3 bis 4 Fragen
      7. Freigabe und Flagge neu berechnen
         grün        -> fertig
         nicht grün  -> Runde N+1, eine Stufe einfacher erklärt

Schritt 3 ist der Grund, warum das Ganze überhaupt vertretbar ist. Ein
Sprachmodell erklärt Bruchrechnung gern mit dem Weg, den es für den besten
hält — und nicht mit dem, den die Lehrkraft verlangt. Ein Kind, das zwei
Wege gleichzeitig lernt, lernt keinen. Deshalb wird jede Erklärung gegen das
eigene Schulmaterial gehalten, und bei einem blockierenden Befund wird sie
verworfen, nicht angezeigt.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from . import config, db, ingest, jobs, kb, prompts, quizzes, research, topics
from .domain import (
    ERROR_LABELS,
    Ausgabe,
    Flag,
    Stufe,
    NEXT_STUFE,
)
from .llm import ClaudeClient, ClaudeError

log = logging.getLogger("karo.teaching")


def client() -> ClaudeClient:
    return ClaudeClient.from_config(config.load())


class TeachingError(Exception):
    """Verständlicher Fehler im Lernzyklus."""


# --------------------------------------------------------------------------
# Lerneinheit starten
# --------------------------------------------------------------------------

def starten(topic_id: int, ausgabe: str | None = None,
            prompt_wunsch: str | None = None, *, neue_einheit: bool = False) -> int:
    """Legt eine Lerneinheit an — wartet aber auf Bestätigung, bevor Runde 1
    beginnt.

    Bewusst kein sofortiger Start: bevor Karo irgendein Lernmaterial erzeugt,
    soll ein Mensch entscheiden dürfen, ob Karo dafür auch im Netz nach
    bekannten Quellen suchen soll (siehe `naechste_runde_bestaetigen()` und
    die Weboberfläche unter `/lernen/{id}`). Das gilt für jede Runde, nicht
    nur die erste — deshalb landet Runde 1 im selben `wartet`-Zustand wie
    jede weitere Runde nach einer Verständnisprüfung.
    """
    thema = topics.get(topic_id)
    if thema is None:
        raise TeachingError("Thema nicht gefunden.")
    if thema["state"] != topics.AKTIV:
        raise TeachingError("Dieses Thema ist noch nicht freigegeben.")

    cfg = config.load()
    ausgabe = ausgabe or cfg.default_ausgabe
    if ausgabe not in {a.value for a in Ausgabe}:
        raise TeachingError("Unbekannte Ausgabeart.")

    prompt_wunsch = (prompt_wunsch or "").strip()[:500] or None
    with db.tx() as c:
        offen = c.execute(
            """SELECT id, ausgabe FROM lesson WHERE topic_id=?
                 AND state NOT IN ('gelernt','abgebrochen') ORDER BY id DESC LIMIT 1""",
            (topic_id,)).fetchone()
        if offen is not None and not neue_einheit:
            # Suche und Anlage sind atomar, auch bei zwei Browserfenstern.
            # Fertiges Material bleibt erhalten; das Format gilt ab der nächsten Runde.
            if offen["ausgabe"] != ausgabe:
                c.execute("UPDATE lesson SET ausgabe=? WHERE id=?",
                          (ausgabe, offen["id"]))
            return offen["id"]
        cur = c.execute(
            """INSERT INTO lesson
                   (topic_id, ausgabe, state, max_runden, prompt_wunsch, created_at)
               VALUES (?, ?, 'wartet', ?, ?, ?)""",
            (topic_id, ausgabe, max(1, min(8, cfg.max_lernrunden)),
             prompt_wunsch, db.now()))
        lesson_id = cur.lastrowid

    return lesson_id


def runde_starten(lesson_id: int, stufe: str | None = None) -> int | None:
    """Legt die nächste Runde an und reiht das Erstellen ein."""
    lesson = db.q1("SELECT * FROM lesson WHERE id = ?", lesson_id)
    if lesson is None:
        raise TeachingError("Lerneinheit nicht gefunden.")
    if lesson["state"] in ("gelernt", "abgebrochen"):
        return None

    letzte = db.q1(
        "SELECT * FROM lesson_round WHERE lesson_id=? ORDER BY nr DESC LIMIT 1",
        lesson_id)
    if letzte and lesson['state'] == 'material':
        return letzte['id']
    nr = (letzte["nr"] + 1) if letzte else 1

    if nr > lesson["max_runden"]:
        abbrechen(lesson_id,
                  f"Nach {lesson['max_runden']} Runden hat es nicht gereicht. "
                  "Hier ist ein Mensch dran.")
        return None

    # Vorab prüfen statt einen Job anzustoßen, der garantiert scheitert: ohne
    # Material — eigenes oder eine freigegebene, bereits geholte Internet-
    # quelle — kann Karo nichts erklären. Bewusst ein Fehler statt eines
    # Abbruchs der ganzen Lerneinheit: die Familie kann jetzt im Netz suchen
    # und eine Quelle freigeben (siehe /lernen/{id}), ohne von vorn
    # anzufangen — die Lerneinheit bleibt im wartenden Zustand.
    thema = topics.get(lesson["topic_id"])
    if thema is None:
        abbrechen(lesson_id, "Das Thema wurde nicht gefunden.")
        return None
    if not kb.lehrmaterial(thema["id"], thema["label"], limit=1) \
            and not research.material_fuer(thema["id"]):
        raise TeachingError(
            "Zu diesem Thema liegt weder eigenes Material noch eine "
            "freigegebene Internetquelle vor. Bitte erst ein Erklärblatt "
            "einlesen, oder unten im Netz suchen und eine Quelle freigeben.")

    if stufe is None:
        stufe = NEXT_STUFE.get(letzte["stufe"], Stufe.GANZ_EINFACH.value) \
            if letzte else Stufe.NORMAL.value

    with db.tx() as c:
        current = c.execute('SELECT state FROM lesson WHERE id=?', (lesson_id,)).fetchone()
        latest = c.execute('SELECT id, nr FROM lesson_round WHERE lesson_id=? ORDER BY nr DESC LIMIT 1',
                           (lesson_id,)).fetchone()
        if current['state'] in ('gelernt', 'abgebrochen'):
            return None
        # Ein zweiter Start darf keine laufende oder gerade angelegte Runde ersetzen.
        if latest and (latest['nr'] >= nr or current['state'] == 'material'):
            return latest['id']
        cur = c.execute(
            """INSERT INTO lesson_round (lesson_id, nr, stufe, state, created_at)
               VALUES (?, ?, ?, 'offen', ?)""",
            (lesson_id, nr, stufe, db.now()))
        round_id = cur.lastrowid
        c.execute("UPDATE lesson SET state='material', runden=? WHERE id=?",
                  (nr, lesson_id))
        jobs.enqueue_in_transaction(c, "lesson_build", {"round_id": round_id},
                                    dedup_key=f"lesson_build:{round_id}")
    return round_id


def abbrechen(lesson_id: int, grund: str) -> None:
    with db.tx() as c:
        c.execute(
            """UPDATE lesson SET state='abgebrochen', finished_at=?,
                                 abbruch_grund=? WHERE id=?""",
            (db.now(), grund, lesson_id))
        c.execute(
            """UPDATE lesson_round SET state='fehler'
                WHERE lesson_id=? AND state IN ('offen','geprueft')""",
            (lesson_id,))
    log.info("Lerneinheit %s abgebrochen: %s", lesson_id, grund)


def _abgebrochen(lesson_id: int) -> bool:
    """Für Abbruchprüfungen in laufenden Erzeugungen — bewusst frisch aus der DB."""
    lesson = db.q1("SELECT state FROM lesson WHERE id = ?", lesson_id)
    return lesson is None or lesson["state"] == "abgebrochen"


# --------------------------------------------------------------------------
# Runde bauen: Material, Erklärung, Gegenprüfung, Rendern
# --------------------------------------------------------------------------

def _vorherige_folien(lesson_id: int, nr: int) -> list[dict] | None:
    """Folien der vorigen Runde — damit die nächste Erklärung nicht dieselbe ist."""
    if nr <= 1:
        return None
    vorige = db.q1("SELECT erklaerung FROM lesson_round WHERE lesson_id=? AND nr=?",
                   lesson_id, nr - 1)
    if vorige is None or not vorige["erklaerung"]:
        return None
    try:
        return (json.loads(vorige["erklaerung"]) or {}).get("folien") or None
    except json.JSONDecodeError:
        return None


@jobs.handler("lesson_build")
def job_lesson_build(payload: dict) -> None:
    round_id = int(payload["round_id"])
    runde = db.q1("SELECT * FROM lesson_round WHERE id = ?", round_id)
    if runde is None or runde["state"] != "offen":
        return
    lesson = db.q1("SELECT * FROM lesson WHERE id = ?", runde["lesson_id"])
    if lesson is None or lesson["state"] == "abgebrochen":
        return
    thema = topics.get(lesson["topic_id"])
    if thema is None:
        return

    cfg = config.load()

    # --- 1. Material sammeln --------------------------------------------
    # Freigegebene, inhaltlich geholte Internetquellen ergaenzen eigenes
    # Material — und stehen ganz an dessen Stelle, wenn keins vorliegt (siehe
    # research.material_fuer() und den Docstring oben in diesem Modul).
    quellen = kb.lehrmaterial(thema["id"], thema["label"], limit=10) \
        + research.material_fuer(thema["id"])
    if not quellen:
        raise TeachingError(
            "Zu diesem Thema liegt weder eigenes Material noch eine "
            "freigegebene Internetquelle vor. Bitte erst ein Erklärblatt "
            "einlesen, oder im Netz suchen und eine Quelle freigeben.")
    fundstellen = research.freigegebene(thema["id"])
    fehlerbild = ERROR_LABELS.get(thema.get("haupt_fehler") or "")
    vorherige_folien = _vorherige_folien(lesson["id"], runde["nr"])
    schwaechen = quizzes.schwaechen(thema["id"])

    # --- 2. Erklärung schreiben -----------------------------------------
    erklaerung = client().complete(
        purpose="lesson_write",
        prompt=prompts.lesson_prompt(
            cfg.learner_grade, cfg.subject, thema["label"],
            thema.get("beschreibung") or "", kb.geschwaerzt(quellen),
            runde["stufe"], fehlerbild, fundstellen,
            vorherige_folien=vorherige_folien, runde_nr=runde["nr"],
            schwaechen=schwaechen, wunsch=lesson["prompt_wunsch"]),
        schema=prompts.LESSON_SCHEMA,
        system=prompts.SYSTEM,
    ).data

    folien = erklaerung.get("folien") or []
    if len(folien) < 2:
        raise TeachingError("Die Erklärung hat zu wenige Folien.")

    # --- 3. Gegenprüfung -------------------------------------------------
    pruefung = client().complete(
        purpose="lesson_verify",
        prompt=prompts.verify_prompt(cfg.learner_grade, cfg.subject,
                                     thema["label"], kb.geschwaerzt(quellen),
                                     folien),
        schema=prompts.VERIFY_SCHEMA,
        system=prompts.SYSTEM,
    ).data

    blockierend = [b for b in (pruefung.get("befunde") or [])
                   if b.get("schwere") == "blockierend"]

    with db.tx() as c:
        c.execute(
            """UPDATE lesson_round
                  SET erklaerung=?, pruefung=?, quellen=?, state=?
                WHERE id=?""",
            (json.dumps(erklaerung, ensure_ascii=False),
             json.dumps(pruefung, ensure_ascii=False),
             json.dumps({"kb": [q["id"] for q in quellen],
                         "links": [f["url"] for f in fundstellen]},
                        ensure_ascii=False),
             "geprueft" if not blockierend else "verworfen",
             round_id))
        if not blockierend:
            jobs.enqueue_in_transaction(c, "lesson_render", {"round_id": round_id},
                                        dedup_key=f"lesson_render:{round_id}")

    if blockierend:
        # Verworfen heisst: neu schreiben, eine Stufe einfacher — nicht
        # anzeigen. Eine falsch gelernte Regel kostet Wochen.
        log.info("Runde %s verworfen: %s blockierende Befunde",
                 round_id, len(blockierend))
        with db.tx() as c:
            c.execute("UPDATE lesson SET state='offen' WHERE id=?",
                      (lesson["id"],))
        runde_starten(lesson["id"])
        return


def _render_material(ausgabe: str, titel: str, folien: list[dict], thema: dict,
                     basis: str, *, arbeit_id: str,
                     kernidee: str = "", hinweis: str = "",
                     abgebrochen=lambda: False,
                     quelle_bereit=lambda pfad: None,
                     ) -> tuple[str | None, str, str | None]:
    """Erzeugt die Ausgabedatei im gewählten Modus.

    NotebookLM-Fehler werden an die Lerneinheit weitergegeben, damit die
    Familie bewusst erneut versuchen oder ein anderes Format wählen kann.

    Gemeinsam genutzt von der normalen Runden-Erzeugung (`job_lesson_render`)
    und von manuell angeforderten Varianten (`job_lesson_variant`).

    `abgebrochen`: wird von langlaufenden Erzeugungen (NotebookLM) regelmäßig
    abgefragt, damit ein Abbruch von Hand nicht erst nach bis zu 45 Minuten
    wirkt, sondern den laufenden Vorgang tatsächlich beendet.

    `quelle_bereit`: wird sofort aufgerufen, sobald die .txt-Datei mit dem
    NotebookLM-Quelltext geschrieben ist — NOCH BEVOR `erzeugen()` startet.
    Damit kann der Aufrufer den Pfad sofort in der Datenbank sichtbar machen,
    statt bis zum Ende der (bis zu 45 Minuten dauernden) Video-Erzeugung zu
    warten. Ohne das wäre der Text erst lesbar, nachdem er längst verschickt
    wurde — zu spät, um ihn vorher zu prüfen.

    Gibt zusätzlich zu Pfad und Hinweis den Pfad dieser .txt-Datei zurück
    (`None`, wenn nicht NotebookLM gewählt war), zur weiteren Verwendung
    durch den Aufrufer (z. B. abschließendes UPDATE zusammen mit `pfad`).
    """
    from .media import notebooklm, slides, video

    gewaehlt = ausgabe
    notiz = ""
    pfad: str | None = None
    notebooklm_quelle_pfad: str | None = None

    if gewaehlt == Ausgabe.NOTEBOOKLM.value:
        text = notebooklm.quelle_text(titel, folien)
        notebooklm_quelle_pfad = ingest.write_material(
            f"{basis}_notebooklm-quelle.txt", text)
        if notebooklm_quelle_pfad:
            quelle_bereit(notebooklm_quelle_pfad)
        try:
            mp4_pfad = notebooklm.erzeugen(titel, folien, text, abgebrochen=abgebrochen)
            pfad = ingest.commit_material(Path(mp4_pfad))
        except notebooklm.NotebookLmUnavailable as exc:
            raise TeachingError(str(exc)) from exc
        except Exception as exc:                        # pragma: no cover
            # Bewusst kein stiller Rückfall mehr auf HTML: die Familie hat
            # NotebookLM ausgewählt, also muss sie erfahren, dass es nicht
            # geklappt hat, und selbst entscheiden — erneut versuchen oder
            # ein anderes Format wählen (siehe /lernen/{id}/ausgabe/erneut
            # und das Popup in lernen.html). Genau dieselbe Behandlung wie
            # bei NotebookLmUnavailable oben.
            raise TeachingError(f"NotebookLM ist fehlgeschlagen: {exc}") from exc

    if gewaehlt == Ausgabe.MP4.value:
        arbeit = config.media_dir() / f"bau-{arbeit_id}"
        ziel = config.media_dir() / f"{basis}.mp4"
        try:
            video.bauen(titel, folien, arbeit, ziel, thema["label"],
                        config.load_safe().tts_stimme)
            pfad = ingest.commit_material(ziel)
        except video.VideoUnavailable as exc:
            notiz = (notiz + " " if notiz else "") + str(exc)
            gewaehlt = Ausgabe.HTML.value
        except Exception as exc:                        # pragma: no cover
            log.exception("MP4-Bau fehlgeschlagen")
            notiz = (notiz + " " if notiz else "") + f"MP4 fehlgeschlagen: {exc}"
            gewaehlt = Ausgabe.HTML.value
        finally:
            shutil.rmtree(arbeit, ignore_errors=True)

    if pfad is None:
        html = slides.lerneinheit(titel, kernidee, folien, thema["label"], hinweis)
        pfad = ingest.write_material(f"{basis}.html", html)

    return pfad, notiz, notebooklm_quelle_pfad


@jobs.handler("lesson_render")
def job_lesson_render(payload: dict) -> None:
    """Erzeugt die Datei, die das Kind ansieht — im gewählten Modus."""
    round_id = int(payload["round_id"])
    runde = db.q1("SELECT * FROM lesson_round WHERE id = ?", round_id)
    if runde is None or runde["state"] != "geprueft":
        return
    lesson = db.q1("SELECT * FROM lesson WHERE id = ?", runde["lesson_id"])
    if lesson is None or lesson["state"] == "abgebrochen":
        return
    thema = topics.get(lesson["topic_id"]) if lesson else None
    if thema is None:
        return

    erklaerung = json.loads(runde["erklaerung"] or "{}")
    folien = erklaerung.get("folien") or []
    titel = erklaerung.get("titel") or thema["label"]
    from . import materials
    titel = materials.titel(thema['label'], titel, runde['nr'], round_id)
    basis = materials.dateiname(titel)

    def _quelle_sofort_speichern(quelle_pfad: str) -> None:
        with db.tx() as c:
            c.execute(
                "UPDATE lesson_round SET notebooklm_quelle_pfad=? WHERE id=?",
                (quelle_pfad, round_id))

    try:
        pfad, notiz, notebooklm_quelle_pfad = _render_material(
            lesson["ausgabe"], titel, folien, thema, basis, arbeit_id=str(round_id),
            kernidee=erklaerung.get("kernidee") or "",
            hinweis="" if runde["stufe"] == Stufe.NORMAL.value else
                    f"Erklärung: {runde['stufe'].replace('_', ' ')}.",
            abgebrochen=lambda: _abgebrochen(lesson["id"]),
            quelle_bereit=_quelle_sofort_speichern)
        materials.speichern("runde", round_id, titel, pfad)
    except TeachingError as exc:
        pruefung = json.loads(runde["pruefung"] or "{}")
        pruefung["ausgabe_hinweis"] = str(exc)
        with db.tx() as c:
            c.execute("UPDATE lesson_round SET state='fehler', pruefung=? WHERE id=?",
                      (json.dumps(pruefung, ensure_ascii=False), round_id))
            c.execute("UPDATE lesson SET state='bereit' WHERE id=?", (lesson["id"],))
        return

    if _abgebrochen(lesson["id"]):
        return

    with db.tx() as c:
        c.execute(
            """UPDATE lesson_round
                  SET material_pfad=?, state='bereit', notebooklm_quelle_pfad=?
                WHERE id=?""",
            (pfad, notebooklm_quelle_pfad, round_id))
        c.execute("UPDATE lesson SET state='bereit' WHERE id=?", (lesson["id"],))
        if notiz:
            # Der Hinweis gehört in die Prüfnotiz, damit die Lernbegleitung
            # sieht, warum es nicht der gewählte Modus wurde.
            p = json.loads(runde["pruefung"] or "{}")
            p["ausgabe_hinweis"] = notiz.strip()
            c.execute("UPDATE lesson_round SET pruefung=? WHERE id=?",
                      (json.dumps(p, ensure_ascii=False), round_id))


def ausgabe_erneut(lesson_id: int, ausgabe: str | None = None) -> None:
    """Startet die letzte Runde mit NotebookLM erneut oder anderem Format."""
    lesson = db.q1("SELECT * FROM lesson WHERE id = ?", lesson_id)
    runde = db.q1(
        "SELECT * FROM lesson_round WHERE lesson_id=? ORDER BY nr DESC LIMIT 1",
        lesson_id)
    if lesson is None or runde is None or runde["state"] != "fehler":
        raise TeachingError("Für diese Lerneinheit gibt es keinen Ausgabe-Fehler.")
    ausgabe = (ausgabe or lesson["ausgabe"]).strip()
    if ausgabe not in {a.value for a in Ausgabe}:
        raise TeachingError("Unbekanntes Ausgabeformat.")
    with db.tx() as c:
        c.execute("UPDATE lesson SET ausgabe=?, state='material' WHERE id=?",
                  (ausgabe, lesson_id))
        c.execute("UPDATE lesson_round SET state='geprueft' WHERE id=?",
                  (runde["id"],))
    jobs.enqueue("lesson_render", {"round_id": runde["id"]},
                 dedup_key=f"lesson_render:{runde['id']}")


# --------------------------------------------------------------------------
# Nach dem Lernen: Verständnisfragen
# --------------------------------------------------------------------------

def fragen_anfordern(lesson_id: int, modus: str = quizzes.BILDSCHIRM) -> int | None:
    """Startet die Verständnisprüfung nach einer Runde."""
    lesson = db.q1("SELECT * FROM lesson WHERE id = ?", lesson_id)
    if lesson is None:
        raise TeachingError("Lerneinheit nicht gefunden.")
    runde = db.q1(
        "SELECT * FROM lesson_round WHERE lesson_id=? ORDER BY nr DESC LIMIT 1",
        lesson_id)
    if runde is None or runde["state"] not in ("bereit", "gelernt"):
        raise TeachingError("Das Lernmaterial ist noch nicht fertig.")

    with db.tx() as c:
        c.execute("UPDATE lesson_round SET state='gelernt' WHERE id=?",
                  (runde["id"],))
    return quizzes.anfordern(lesson["topic_id"], anlass="lernrunde",
                             modus=modus, lesson_id=lesson_id,
                             round_nr=runde["nr"], anzahl=4)


def nach_freigabe(lesson_id: int, topic_id: int, *, auto_weiter: bool = True) -> dict:
    """Entscheidet nach einer Verständnisprüfung, wie es weitergeht.

    Wird von der Weboberfläche aufgerufen, nachdem die Lernbegleitung die
    Bewertung freigegeben hat. Die Flagge ist zu diesem Zeitpunkt bereits neu
    berechnet.

    `auto_weiter=False`: statt die nächste Runde sofort zu starten, wird die
    Lerneinheit auf `wartet` gesetzt — die Weboberfläche fragt dann erst, ob
    und mit welchen Quellen weitergemacht werden soll, siehe
    `naechste_runde_bestaetigen()`. Der Standardwert `True` erhält das alte
    Verhalten für Aufrufe, die keine Bestätigung durch einen Menschen wollen
    (z. B. Tests oder ein automatisierter Ablauf).
    """
    lesson = db.q1("SELECT * FROM lesson WHERE id = ?", lesson_id)
    if lesson is None:
        return {"weiter": False, "grund": "Lerneinheit nicht gefunden."}

    thema = topics.get(topic_id)
    flagge = (thema or {}).get("flag", Flag.WEISS.value)

    if flagge == Flag.GRUEN.value:
        with db.tx() as c:
            c.execute("UPDATE lesson SET state='gelernt', finished_at=? WHERE id=?",
                      (db.now(), lesson_id))
        return {"weiter": False, "erfolg": True,
                "grund": "Das Thema sitzt. Die Lerneinheit ist abgeschlossen."}

    if lesson["runden"] >= lesson["max_runden"]:
        grund = (f"Nach {lesson['max_runden']} Runden hat es nicht "
                "gereicht. Karo hört hier auf — an dieser Stelle "
                "hilft ein Mensch mehr als eine weitere Erklärung.")
        abbrechen(lesson_id, grund)
        return {"weiter": False, "erfolg": False, "grund": grund}

    if not auto_weiter:
        with db.tx() as c:
            c.execute("UPDATE lesson SET state='wartet' WHERE id=?", (lesson_id,))
        return {"weiter": True, "wartet_auf_bestaetigung": True,
                "grund": "Noch nicht sicher. Bereit für die nächste Runde?"}

    round_id = runde_starten(lesson_id)
    return {"weiter": True, "round_id": round_id,
            "grund": ("Noch nicht sicher. Karo erklärt es eine Stufe "
                      "einfacher und stellt danach neue Fragen.")}


def naechste_runde_bestaetigen(lesson_id: int) -> int | None:
    """Startet die naechste Runde (oder Runde 1), nachdem ein Mensch bestätigt hat.

    Die Recherche-Frage wird davor separat beantwortet — siehe
    `forschung_anfordern()` und die Freigabe unter `/lernen/{id}` bzw.
    `/recherche`. Bereits freigegebene Fundstellen fließen automatisch in
    diese und jede weitere Runde ein (`research.freigegebene()`), unabhängig
    davon, wann sie freigegeben wurden.
    """
    lesson = db.q1("SELECT * FROM lesson WHERE id = ?", lesson_id)
    if lesson is None:
        raise TeachingError("Lerneinheit nicht gefunden.")
    if lesson["state"] != "wartet":
        raise TeachingError("Diese Lerneinheit wartet nicht auf eine Bestätigung.")
    return runde_starten(lesson_id)


def forschung_anfordern(lesson_id: int) -> bool:
    """Stößt die Websuche für das Thema dieser Lerneinheit an.

    Getrennt von `naechste_runde_bestaetigen()`: die Familie soll die Funde
    sehen und einzeln freigeben können, bevor Karo überhaupt zu schreiben
    beginnt — nicht nur nebenbei im Hintergrund.
    """
    lesson = db.q1("SELECT * FROM lesson WHERE id = ?", lesson_id)
    if lesson is None:
        raise TeachingError("Lerneinheit nicht gefunden.")
    if lesson["state"] != "wartet":
        raise TeachingError("Diese Lerneinheit wartet nicht auf eine Bestätigung.")
    return research.anfordern(lesson["topic_id"])


# --------------------------------------------------------------------------
# Variante: dieselbe Runde nochmal, mit einem Gestaltungswunsch
# --------------------------------------------------------------------------

MAX_WUNSCH_LAENGE = 500


def variante_anfordern(round_id: int, wunsch: str, ausgabe: str | None = None) -> int:
    """Fordert eine weitere Ausspielung einer fertigen Runde an.

    Zählt bewusst NICHT als neue Runde: keine Flagge, kein Fortschritt, kein
    Verbrauch von max_runden. Der Wunsch (Freitext, ungeprüft) beeinflusst
    nur die Form der Erklärung — siehe die Absicherung in
    `prompts._wunsch_block()`. Wie jede Erklärung durchläuft auch diese
    Variante die Gegenprüfung, bevor sie angezeigt wird.

    `ausgabe`: Ausgabeart für diese eine Variante — leer/None übernimmt die
    Art der Lerneinheit. Damit lässt sich z. B. für eine Runde, die als
    Folien mit Stimme erzeugt wurde, trotzdem einmalig ein NotebookLM-Video
    anfordern, ohne die ganze Lerneinheit umzustellen.
    """
    runde = db.q1("SELECT * FROM lesson_round WHERE id = ?", round_id)
    if runde is None or runde["state"] != "bereit" or not runde["material_pfad"]:
        raise TeachingError("Zu dieser Runde gibt es noch kein fertiges Material.")

    wunsch = (wunsch or "").strip()
    if not wunsch:
        raise TeachingError("Bitte kurz beschreiben, was anders sein soll.")
    wunsch = wunsch[:MAX_WUNSCH_LAENGE]

    ausgabe = (ausgabe or "").strip() or None
    if ausgabe is not None and ausgabe not in {a.value for a in Ausgabe}:
        raise TeachingError("Unbekannte Ausgabeart.")

    with db.tx() as c:
        cur = c.execute(
            """INSERT INTO lesson_round_variant
                   (lesson_round_id, wunsch, ausgabe, state, created_at)
               VALUES (?, ?, ?, 'offen', ?)""",
            (round_id, wunsch, ausgabe, db.now()))
        variant_id = cur.lastrowid
        jobs.enqueue_in_transaction(c, "lesson_variant", {"variant_id": variant_id})
    return variant_id


@jobs.handler("lesson_variant")
def job_lesson_variant(payload: dict) -> None:
    variant_id = int(payload["variant_id"])
    variante = db.q1("SELECT * FROM lesson_round_variant WHERE id = ?", variant_id)
    if variante is None or variante["state"] != "offen":
        return
    runde = db.q1("SELECT * FROM lesson_round WHERE id = ?",
                  variante["lesson_round_id"])
    lesson = db.q1("SELECT * FROM lesson WHERE id = ?", runde["lesson_id"]) \
        if runde else None
    thema = topics.get(lesson["topic_id"]) if lesson else None
    if runde is None or lesson is None or thema is None:
        return

    def _fehlschlag(meldung: str) -> None:
        with db.tx() as c:
            c.execute(
                "UPDATE lesson_round_variant SET state='fehler', fehler=? WHERE id=?",
                (meldung, variant_id))

    cfg = config.load()
    try:
        quellen = kb.lehrmaterial(thema["id"], thema["label"], limit=10) \
            + research.material_fuer(thema["id"])
        if not quellen:
            _fehlschlag("Zu diesem Thema liegt kein Material mehr vor.")
            return
        fundstellen = research.freigegebene(thema["id"])
        fehlerbild = ERROR_LABELS.get(thema.get("haupt_fehler") or "")

        erklaerung = client().complete(
            purpose="lesson_write",
            prompt=prompts.lesson_prompt(
                cfg.learner_grade, cfg.subject, thema["label"],
                thema.get("beschreibung") or "", kb.geschwaerzt(quellen),
                runde["stufe"], fehlerbild, fundstellen,
                runde_nr=runde["nr"], wunsch=variante["wunsch"],
                schwaechen=quizzes.schwaechen(thema["id"])),
            schema=prompts.LESSON_SCHEMA,
            system=prompts.SYSTEM,
        ).data
        folien = erklaerung.get("folien") or []
        if len(folien) < 2:
            _fehlschlag("Die Erklärung hatte zu wenige Folien. Bitte erneut "
                       "versuchen, evtl. mit einem anderen Wunsch.")
            return

        # Dieselbe Gegenpruefung wie bei jeder normalen Runde — ein Wunsch
        # darf niemals ungeprueftes Material an das Kind ausliefern.
        pruefung = client().complete(
            purpose="lesson_verify",
            prompt=prompts.verify_prompt(cfg.learner_grade, cfg.subject,
                                         thema["label"], kb.geschwaerzt(quellen),
                                         folien),
            schema=prompts.VERIFY_SCHEMA,
            system=prompts.SYSTEM,
        ).data
        blockierend = [b for b in (pruefung.get("befunde") or [])
                       if b.get("schwere") == "blockierend"]
        if blockierend:
            _fehlschlag("Mit diesem Wunsch wäre die Erklärung vom "
                       "Schulmaterial abgewichen — deshalb wurde nichts "
                       "erzeugt. Gerne mit einem anderen Wunsch erneut "
                       "versuchen.")
            return

        titel = erklaerung.get("titel") or thema["label"]
        from . import materials
        titel = materials.titel(thema['label'], titel, runde['nr'],
                                 runde['id'], variant_id)
        basis = materials.dateiname(titel)

        def _quelle_sofort_speichern(quelle_pfad: str) -> None:
            with db.tx() as c:
                c.execute(
                    "UPDATE lesson_round_variant SET notebooklm_quelle_pfad=? "
                    "WHERE id=?", (quelle_pfad, variant_id))

        pfad, notiz, notebooklm_quelle_pfad = _render_material(
            variante["ausgabe"] or lesson["ausgabe"], titel, folien, thema, basis,
            arbeit_id=f"v{variant_id}", kernidee=erklaerung.get("kernidee") or "",
            abgebrochen=lambda: _abgebrochen(lesson["id"]),
            quelle_bereit=_quelle_sofort_speichern)

        materials.speichern("variante", variant_id, titel, pfad)

        if _abgebrochen(lesson["id"]):
            _fehlschlag("Abgebrochen.")
            return

        with db.tx() as c:
            c.execute(
                """UPDATE lesson_round_variant
                      SET state='bereit', material_pfad=?, fehler=?,
                          notebooklm_quelle_pfad=?
                    WHERE id=?""",
                (pfad, notiz.strip() or None, notebooklm_quelle_pfad, variant_id))
    except TeachingError as exc:
        _fehlschlag(str(exc))
    except Exception:                                        # pragma: no cover
        log.exception("Variante %s fehlgeschlagen", variant_id)
        _fehlschlag("Unerwarteter Fehler beim Erzeugen. Details stehen im "
                   "Protokoll des Containers.")


# --------------------------------------------------------------------------
# Lesen
# --------------------------------------------------------------------------

def holen(lesson_id: int) -> dict | None:
    lesson = db.q1("SELECT * FROM lesson WHERE id = ?", lesson_id)
    if lesson is None:
        return None
    d = dict(lesson)
    d["thema"] = topics.get(lesson["topic_id"])
    d["runden_liste"] = []
    for r in db.q("SELECT * FROM lesson_round WHERE lesson_id=? ORDER BY nr DESC",
                  lesson_id):
        runde = dict(r)
        runde["erklaerung"] = _json(runde.get("erklaerung"))
        runde["pruefung"] = _json(runde.get("pruefung"))
        runde["quellen"] = _json(runde.get("quellen"))
        runde["quiz"] = db.q1(
            """SELECT id, state, modus, finished_at FROM quiz
                WHERE lesson_id=? AND round_nr=? AND superseded_by IS NULL
                ORDER BY id DESC LIMIT 1""",
            lesson_id, runde["nr"])
        runde["quiz"] = dict(runde["quiz"]) if runde["quiz"] else None
        runde["varianten"] = [dict(v) for v in db.q(
            "SELECT * FROM lesson_round_variant WHERE lesson_round_id=? ORDER BY id",
            runde["id"])]
        # Ein Job, der alle Versuche verbraucht hat, aendert sonst nichts an
        # Runde oder Lerneinheit — ohne das hier bliebe die Seite fuer immer
        # bei "Karo arbeitet" stehen, ohne dass je ein Fehler sichtbar wuerde.
        fehlgeschlagen = db.q1(
            """SELECT last_error FROM job
                WHERE dedup_key IN (?, ?) AND state='fehler'
                ORDER BY id DESC LIMIT 1""",
            f"lesson_build:{runde['id']}", f"lesson_render:{runde['id']}")
        runde["job_fehler"] = fehlgeschlagen["last_error"] if fehlgeschlagen else None
        d["runden_liste"].append(runde)
    d["aktuelle"] = d["runden_liste"][0] if d["runden_liste"] else None
    return d


def materialien_fuer_thema(topic_id: int) -> list[dict]:
    """Alle je erzeugten Lernmaterialien zu einem Thema, neueste zuerst.

    Bewusst über alle Lerneinheiten hinweg, nicht nur die aktuell offene:
    „Mehr zum Thema“ beendet die bisherige Lerneinheit und legt eine neue
    an (siehe `starten()`/`abbrechen()` in kind.lernen_abbrechen) — ohne
    diese Übersicht verschwänden Folien und Videos früherer Runden aus der
    Oberfläche, obwohl sie in der Datenbank und im Drive-Ordner erhalten
    bleiben.
    """
    zeilen = db.q(
        """SELECT lr.id AS id, 'runde' AS art, lr.lesson_id AS lesson_id,
                  lr.nr AS round_nr, l.ausgabe AS lesson_ausgabe,
                  lr.material_pfad AS material_pfad,
                  lr.notebooklm_quelle_pfad AS notebooklm_quelle_pfad,
                  lr.erklaerung AS erklaerung, lr.stufe AS stufe,
                  lr.created_at AS created_at,
                  NULL AS variant_wunsch, NULL AS variant_ausgabe
             FROM lesson_round lr
             JOIN lesson l ON l.id = lr.lesson_id
            WHERE l.topic_id = ? AND lr.material_pfad IS NOT NULL
            UNION ALL
           SELECT lrv.id AS id, 'variante' AS art, lr.lesson_id AS lesson_id,
                  lr.nr AS round_nr, l.ausgabe AS lesson_ausgabe,
                  lrv.material_pfad AS material_pfad,
                  lrv.notebooklm_quelle_pfad AS notebooklm_quelle_pfad,
                  lr.erklaerung AS erklaerung, lr.stufe AS stufe,
                  lrv.created_at AS created_at,
                  lrv.wunsch AS variant_wunsch, lrv.ausgabe AS variant_ausgabe
             FROM lesson_round_variant lrv
             JOIN lesson_round lr ON lr.id = lrv.lesson_round_id
             JOIN lesson l ON l.id = lr.lesson_id
            WHERE l.topic_id = ? AND lrv.material_pfad IS NOT NULL
              AND lrv.state = 'bereit'
            ORDER BY created_at DESC, id DESC""",
        topic_id, topic_id)

    ergebnis = []
    for z in zeilen:
        m = dict(z)
        erklaerung = _json(m.pop("erklaerung"))
        ausgabe = m.pop("variant_ausgabe") or m.pop("lesson_ausgabe")
        wunsch = m.pop("variant_wunsch")
        if m["art"] == "variante":
            titel = f"Variante: {wunsch}" if wunsch else "Variante"
        else:
            titel = erklaerung.get("titel") or f"Runde {m['round_nr']}"
        m["titel"] = titel
        m["ausgabe"] = ausgabe
        m["oeffnen_url"] = (f"/material/{m['id']}" if m["art"] == "runde"
                            else f"/material/variante/{m['id']}")
        m["notebooklm_quelle_url"] = (
            (f"/material/{m['id']}/notebooklm-quelle" if m["art"] == "runde"
             else f"/material/variante/{m['id']}/notebooklm-quelle")
            if m["notebooklm_quelle_pfad"] else None)
        ergebnis.append(m)
    return ergebnis


def _json(text):
    if not text:
        return {}
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}


def offene() -> list[dict]:
    return [dict(r) for r in db.q(
        """SELECT l.*, t.label AS thema_label, t.code AS thema_code,
                  COALESCE(f.flag, 'weiss') AS flag
             FROM lesson l
             JOIN topic t ON t.id = l.topic_id
             LEFT JOIN topic_flag f ON f.topic_id = l.topic_id
            WHERE l.state NOT IN ('gelernt','abgebrochen')
            ORDER BY l.id DESC""")]


def verlauf(limit: int = 30) -> list[dict]:
    return [dict(r) for r in db.q(
        """SELECT l.*, t.label AS thema_label, t.code AS thema_code
             FROM lesson l JOIN topic t ON t.id = l.topic_id
            ORDER BY l.id DESC LIMIT ?""", limit)]
