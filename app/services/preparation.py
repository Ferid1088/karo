"""Vorbereitung: Schulmaterial, Themen, Recherche.

Frueher hatte nur `eltern.py` diese Logik, und `vorbereitung.py` rief die
eltern.py-Routenfunktionen direkt auf (Router ruft Router). Jetzt lebt die
Logik hier; `/wissen`+`/themen`+`/recherche` (eltern.py) und
`/vorbereitung/*` rufen beide dieselben Funktionen auf
(KaroRefactoring_Plan.md Abschnitt 10; change.txt Aufgabe 2/6).
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import Request, UploadFile
from starlette.concurrency import run_in_threadpool

from .. import (blatt_text, config, db, faecher, ingest, jobs, kb, quizzes, research,
                security, topics)
from ..domain import FLAG_ORDER
from ..routers.shared import aktives_fach, flash, render, zurueck


# --- Schulmaterial -----------------------------------------------------------

def _wissen_ziel(fach: str) -> str:
    return f"/wissen?fach={fach}"


def render_wissen(request: Request):
    """Schulblätter nur des aktiven Fachs."""
    fach = aktives_fach(request, request.query_params.get("fach"))
    docu = [dict(r) for r in db.q(
        """SELECT d.*, (SELECT COUNT(*) FROM kb_chunk k
                   WHERE k.document_id=d.id) AS abschnitte
           FROM document d WHERE d.rolle='wissen' AND d.subject=?
           ORDER BY d.created_at DESC LIMIT 50""", fach)]
    return render(request, "wissen.html", blaetter=docu, counts=jobs.counts(), fach=fach,
                  kb_stat=kb.statistik(), drive_ok=ingest.drive_available(),
                  adult_page=not config.load().schulblaetter_kind,
                  inbox_path=ingest.inbox_path())


async def handle_wissen_einlesen(request: Request, quelle: str):
    formular = await request.form()
    fach = aktives_fach(request, formular.get("fach"))
    if quelle == "drive":
        try:
            ergebnisse = await run_in_threadpool(ingest.scan_inbox)
            for ergebnis in ergebnisse:
                if ergebnis.get("status") == "neu":
                    doc_id = ergebnis["document_id"]
                    # Eingelesen im Fach-Reiter: das Blatt gehört zu diesem Fach.
                    with db.tx() as c:
                        c.execute("UPDATE document SET subject=? WHERE id=? AND subject IS NULL",
                                  (fach, doc_id))
                    jobs.enqueue("kb_extract", {"document_id": doc_id},
                                 dedup_key=f"kb_extract:{doc_id}")
        except ingest.IngestError as exc:
            flash(request, str(exc), "err")
        else:
            flash(request, "Drive wird gelesen." if ergebnisse else
                  "Kein Drive-Ordner eingerichtet oder nichts Neues darin.")
    return zurueck(_wissen_ziel(fach))


async def handle_wissen_upload(request: Request, rolle: str,
                               datei: UploadFile | None):
    if request.session.get("role") == "child":
        rolle = "wissen"
    formular = await request.form()
    # Das Fach kommt aus dem Reiter, in dem hochgeladen wird — nie geraten.
    fach = faecher.schluessel(formular.get("fach"))
    if fach is None:
        flash(request, f"Bitte zuerst ein Fach wählen: {faecher.faecher_text()}.", "err")
        return zurueck("/wissen")
    aktives_fach(request, fach)
    ziel = _wissen_ziel(fach)
    datei = datei or formular.get("datei")
    themenname = str(formular.get("themenname") or "").strip()[:200]
    if datei is None or not getattr(datei, "filename", ""):
        flash(request, "Es wurde keine Datei ausgewählt.", "err")
        return zurueck(ziel)
    try:
        faecher.pruefe(themenname, fach)
    except faecher.SubjectMismatch as exc:
        flash(request, str(exc), "err")
        return zurueck(ziel)
    if not themenname:
        flash(request, "Bitte einen Themennamen angeben.", "err")
        return zurueck(ziel)

    endung = Path(datei.filename).suffix.lower()
    puffer = bytearray()
    while stueck := await datei.read(1 << 20):
        puffer.extend(stueck)
        if len(puffer) > security.MAX_UPLOAD_BYTES:
            flash(request, "Datei zu groß.", "err")
            return zurueck(ziel)

    # Optional: der Text des Blatts, abgetippt oder eingefügt. Ab Schritt 2
    # füllt das Browser-OCR dasselbe Feld — deshalb läuft es hier durch
    # dieselbe Funktion wie `POST /blatt/text` und nicht durch eine zweite,
    # die erst am Tag der Umstellung zum ersten Mal liefe.
    blatt_text_roh = str(formular.get("blatt_text") or "").strip()

    try:
        ergebnis = await run_in_threadpool(
            ingest.aufnehmen, bytes(puffer), endung, rolle, themenname, fach)
        if ergebnis["status"] == "neu":
            jobs.enqueue("kb_extract", {"document_id": ergebnis["document_id"]},
                         dedup_key=f"kb_extract:{ergebnis['document_id']}")
    except ingest.IngestError as exc:
        flash(request, str(exc), "err")
        return zurueck(ziel)

    if blatt_text_roh:
        stand = await run_in_threadpool(
            blatt_text.aufnehmen, blatt_text_roh, fach,
            document_id=ergebnis["document_id"], themenname=themenname)
        flash(request, f"Blatt aufgenommen, {stand['abschnitte']} Abschnitte in der "
                       "Wissensbasis. Bitte unten das Thema bestätigen.")
        return zurueck(f"/wissen/{ergebnis['document_id']}")

    flash(request, "Dieses Blatt ist bereits in der Sammlung." if
          ergebnis["status"] == "doppelt" else
          f"Blatt abgelegt für „{themenname}“.")
    return zurueck(ziel)


async def handle_blatt_text(request: Request):
    """`POST /blatt/text` — Text eines Blatts, nie ein Bild.

    Ab Schritt 2 ruft das hier das Browser-OCR auf; heute das Textfeld beim
    Hochladen. Antwortet mit JSON, damit beides denselben Vertrag hat.
    """
    from fastapi.responses import JSONResponse

    formular = await request.form()
    fach = faecher.schluessel(formular.get("fach"))
    text = str(formular.get("text") or "").strip()
    if fach is None:
        return JSONResponse({"fehler": "Bitte zuerst ein Fach wählen."}, status_code=422)
    if not text:
        return JSONResponse({"fehler": "Es kam kein Text an."}, status_code=422)
    doc_id = formular.get("document_id")
    konfidenz = formular.get("ocr_konfidenz")
    try:
        stand = await run_in_threadpool(
            blatt_text.aufnehmen, text, fach,
            document_id=int(doc_id) if doc_id else None,
            themenname=str(formular.get("themenname") or "").strip()[:200],
            ocr_konfidenz=float(konfidenz) if konfidenz else None)
    except (ValueError, TypeError):
        return JSONResponse({"fehler": "Die Angaben zum Blatt sind unvollständig."},
                            status_code=422)
    # Dasselbe Ergebnis, zwei Leser: das Browser-OCR (Schritt 2) will JSON,
    # ein abgeschicktes Formular will die nächste Seite sehen.
    if doc_id and "text/html" in (request.headers.get("accept") or ""):
        flash(request, f"{stand['abschnitte']} Abschnitte übernommen. "
                       "Bitte das Thema bestätigen.")
        return zurueck(f"/wissen/{int(doc_id)}#blatt-thema")
    return JSONResponse(stand)


async def handle_blatt_serverseitig(request: Request):
    """Rückfall: der Browser kann nicht lesen, also liest der Server.

    Auf dem Rechner der Familie, nicht bei einem fremden Dienst — und die
    Datei wird sofort nach dem Lesen gelöscht. Das steht vorher in der
    Oberfläche; eine Familie, die das nicht will, tippt den Text ein.
    """
    import tempfile
    from pathlib import Path

    from fastapi.responses import JSONResponse

    formular = await request.form()
    fach = faecher.schluessel(formular.get("fach"))
    datei = formular.get("datei")
    if fach is None or datei is None or not getattr(datei, "filename", ""):
        return JSONResponse({"fehler": "Fach und Datei werden gebraucht."}, status_code=422)
    if not blatt_text.server_lesen_moeglich():
        return JSONResponse(
            {"fehler": "Auf diesem Server ist keine Lesehilfe installiert. "
                       "Bitte den Text vom Blatt eintippen."}, status_code=503)

    roh = await datei.read(security.MAX_UPLOAD_BYTES + 1)
    if len(roh) > security.MAX_UPLOAD_BYTES:
        return JSONResponse({"fehler": "Die Datei ist zu groß."}, status_code=422)

    endung = Path(datei.filename).suffix.lower() or ".bin"
    tmp = Path(tempfile.mkdtemp(prefix="karo-lesen-")) / f"blatt{endung}"
    try:
        tmp.write_bytes(roh)
        text = await run_in_threadpool(blatt_text.server_lesen, tmp)
    finally:
        # Sofort weg — auch wenn das Lesen scheiterte. Eine Datei, die niemand
        # mehr braucht, soll nicht herumliegen, bis jemand aufräumt.
        try:
            tmp.unlink(missing_ok=True)
            tmp.parent.rmdir()
        except OSError:
            pass

    if len(text.strip()) < 40:
        return JSONResponse(
            {"fehler": "Auf dem Blatt war zu wenig lesbar. Neu fotografieren — "
                       "flach hinlegen, von oben, ohne Schatten — oder den Text eintippen."},
            status_code=422)
    doc_id = formular.get("document_id")
    stand = await run_in_threadpool(
        blatt_text.aufnehmen, text, fach,
        document_id=int(doc_id) if doc_id else None,
        themenname=str(formular.get("themenname") or "").strip()[:200])
    return JSONResponse({**stand, "text": text})


async def handle_blatt_thema(request: Request, doc_id: int):
    """Die Bestätigung eines Menschen: dieses Blatt gehört zu diesem Thema."""
    formular = await request.form()
    doc = db.q1("SELECT * FROM document WHERE id=?", doc_id)
    if doc is None:
        flash(request, "Blatt nicht gefunden.", "err")
        return zurueck("/wissen")
    fach = faecher.schluessel(doc["subject"])
    gewaehlt = str(formular.get("topic_id") or "").strip()
    eigenes = str(formular.get("label") or "").strip()[:200]
    if gewaehlt.isdigit():
        topic_id = int(gewaehlt)
        thema = db.q1("SELECT id, subject FROM topic WHERE id=?", topic_id)
        # Ein Thema aus einem anderen Fach darf dieses Blatt nicht bekommen.
        if not thema or faecher.schluessel(thema["subject"]) != fach:
            flash(request, "Dieses Thema gehört zu einem anderen Fach.", "err")
            return zurueck(f"/wissen/{doc_id}")
    elif eigenes:
        try:
            faecher.pruefe(eigenes, fach, modell=False)
        except faecher.SubjectMismatch as exc:
            flash(request, str(exc), "err")
            return zurueck(f"/wissen/{doc_id}")
        topic_id = topics.anlegen(eigenes, subject=fach)
    else:
        flash(request, "Bitte ein Thema auswählen oder eintragen.", "err")
        return zurueck(f"/wissen/{doc_id}")
    n = blatt_text.zuordnen(doc_id, topic_id)
    flash(request, f"{n} Abschnitte gehören jetzt zu diesem Thema." if n
          else "Zu diesem Blatt liegt noch kein Text vor.")
    return zurueck(f"/wissen/{doc_id}")


def render_wissen_detail(request: Request, doc_id: int):
    doc = db.q1("SELECT * FROM document WHERE id = ?", doc_id)
    if doc is None or (request.session.get("role") == "child" and doc["rolle"] != "wissen"):
        flash(request, "Blatt nicht gefunden.", "err")
        return zurueck("/wissen")
    abschnitte = [dict(r) for r in db.q(
        """SELECT k.*, t.label AS thema_label FROM kb_chunk k
             LEFT JOIN topic t ON t.id = k.topic_id
            WHERE k.document_id=? ORDER BY k.position""", doc_id)]
    # Vorschläge nur, solange das Blatt noch keinem Thema gehört: danach ist
    # die Frage beantwortet und eine Auswahl daneben nur noch verwirrend.
    vorschlaege = []
    if abschnitte and not any(a["topic_id"] for a in abschnitte):
        text = "\n\n".join(a["text"] for a in abschnitte[:20])
        vorschlaege = blatt_text.vorschlaege(
            text, faecher.schluessel(doc["subject"]) or "", doc["themenname"] or "")
    return render(request, "wissen_blatt.html", doc=dict(doc), abschnitte=abschnitte,
                  vorschlaege=vorschlaege,
                  adult_page=not config.load().schulblaetter_kind)


# --- Themen genehmigen ---------------------------------------------------------

def render_themen(request: Request):
    aktive = topics.liste(topics.AKTIV)
    aktive.sort(key=lambda t: (FLAG_ORDER.index(t["flag"])
                               if t["flag"] in FLAG_ORDER else 9, t["sort"]))
    for t in aktive:
        t["verlauf"] = quizzes.verlauf(t["id"])
    return render(request, "themen.html",
                  vorschlaege=topics.liste(topics.VORSCHLAG),
                  aktive=aktive, einig=quizzes.uebereinstimmung())


async def handle_themen_entscheiden(request: Request):
    formular = await request.form()
    entscheidungen = []
    for schluessel in formular.keys():
        if not schluessel.startswith("aktion_"):
            continue
        roh = schluessel[7:]
        if not roh.isdigit():
            continue
        entscheidungen.append({
            "id": int(roh),
            "aktion": formular.get(schluessel),
            "label": formular.get(f"label_{roh}", ""),
        })
    ergebnis = topics.entscheiden(entscheidungen)
    if ergebnis["angenommen"] or ergebnis["abgelehnt"]:
        flash(request, f"{ergebnis['angenommen']} übernommen, "
                       f"{ergebnis['abgelehnt']} verworfen"
                       + (f", {ergebnis['umbenannt']} umbenannt"
                          if ergebnis["umbenannt"] else "") + ".")
    else:
        flash(request, "Es wurde nichts entschieden.", "warn")
    return zurueck("/themen")


def handle_themen_neu(request: Request, label: str, beschreibung: str, fach: str = ""):
    try:
        neu = topics.anlegen(label, beschreibung, subject=fach)
    except faecher.FachFehler as exc:
        flash(request, str(exc), "err")
        return zurueck("/themen")
    if neu is None:
        flash(request, "Dieses Thema gibt es schon oder der Name ist leer.", "warn")
    else:
        flash(request, "Thema angelegt.")
    return zurueck("/themen")


def handle_recherche_starten(request: Request, topic_id: int):
    if research.anfordern(topic_id):
        flash(request, "Karo sucht auf den zugelassenen Seiten.")
    else:
        flash(request, "Die Recherche ist ausgeschaltet oder läuft schon.", "warn")
    return zurueck("/recherche")


# --- Recherche / Quellen -------------------------------------------------------

def render_recherche(request: Request):
    cfg = config.load_safe()
    quellen = research.erlaubte_quellen()
    return render(request, "recherche.html",
                  vorschlaege=research.vorschlaege(),
                  erlaubte=sorted(set(quellen.values())),
                  quellen=research.quellen_liste(),
                  quellen_vorschlaege=research.quellen_vorschlaege(
                      cfg.learner_grade, cfg.subject),
                  kanaele=research.ERLAUBTE_KANAELE,
                  aktiv=cfg.recherche_erlaubt)


async def handle_recherche_quelle_hinzufuegen(request: Request):
    formular = await request.form()
    domain = str(formular.get("domain") or formular.get("domain_manual") or "") \
        .strip().lower()
    label = str(formular.get("label") or "").strip()[:120]
    domain = domain.removeprefix("https://").removeprefix("http://").split("/", 1)[0]
    cfg = config.load()
    quellen = [q for q in cfg.recherche_quellen if q.get("domain") != domain]
    if not domain or "." not in domain or any(ch in domain for ch in " <>\"'"):
        flash(request, "Bitte eine gültige Domain eingeben.", "err")
    else:
        quellen.append({"domain": domain, "label": label or domain, "active": True})
        config.update(recherche_quellen=quellen)
        flash(request, "Quelle hinzugefügt.")
    return zurueck("/recherche#recherche-quellen")


async def handle_recherche_quelle_aktivieren(request: Request):
    formular = await request.form()
    domain = str(formular.get("domain") or "").strip().lower()
    active = str(formular.get("active") or "") == "1"
    cfg = config.load()
    quellen = [dict(q) for q in cfg.recherche_quellen]
    for quelle in quellen:
        if quelle.get("domain", "").lower().removeprefix("www.") == domain:
            quelle["active"] = active
    config.update(recherche_quellen=quellen)
    flash(request, "Quelle aktiviert." if active else "Quelle deaktiviert.")
    return zurueck("/recherche#recherche-quellen")


async def handle_recherche_entscheiden(request: Request):
    formular = await request.form()
    entscheidungen: dict[int, str] = {}
    for schluessel in formular.keys():
        if not schluessel.startswith("hit_"):
            continue
        roh = schluessel[4:]
        if roh.isdigit():
            entscheidungen[int(roh)] = str(formular.get(schluessel) or "")
    ergebnis = research.entscheiden(entscheidungen)
    flash(request, f"{ergebnis['freigegeben']} freigegeben, "
                   f"{ergebnis['abgelehnt']} abgelehnt.")
    ziel = str(formular.get("zurueck") or "")
    if re.match(r"^/lernen/\d+$", ziel):
        return zurueck(ziel)
    return zurueck("/recherche")
