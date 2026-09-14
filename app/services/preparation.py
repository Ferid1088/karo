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

from .. import config, db, ingest, jobs, kb, quizzes, research, security, topics
from ..domain import FLAG_ORDER
from ..routers.shared import flash, render, zurueck


# --- Schulmaterial -----------------------------------------------------------

def render_wissen(request: Request):
    docu = [dict(r) for r in db.q(
        """SELECT d.*, (SELECT COUNT(*) FROM kb_chunk k
                   WHERE k.document_id=d.id) AS abschnitte
           FROM document d WHERE d.rolle='wissen'
           ORDER BY d.created_at DESC LIMIT 50""")]
    return render(request, "wissen.html", blaetter=docu, counts=jobs.counts(),
                  kb_stat=kb.statistik(), drive_ok=ingest.drive_available(),
                  inbox_path=ingest.inbox_path())


async def handle_wissen_einlesen(request: Request, quelle: str):
    if quelle == "drive":
        try:
            ergebnisse = await run_in_threadpool(ingest.scan_inbox)
            for ergebnis in ergebnisse:
                if ergebnis.get("status") == "neu":
                    doc_id = ergebnis["document_id"]
                    jobs.enqueue("kb_extract", {"document_id": doc_id},
                                 dedup_key=f"kb_extract:{doc_id}")
        except ingest.IngestError as exc:
            flash(request, str(exc), "err")
        else:
            flash(request, "Drive wird gelesen." if ergebnisse else
                  "Kein Drive-Ordner eingerichtet oder nichts Neues darin.")
    return zurueck("/wissen")


async def handle_wissen_upload(request: Request, rolle: str,
                               datei: UploadFile | None):
    formular = await request.form()
    datei = datei or formular.get("datei")
    themenname = str(formular.get("themenname") or "").strip()[:200]
    if datei is None or not getattr(datei, "filename", ""):
        flash(request, "Es wurde keine Datei ausgewählt.", "err")
        return zurueck("/wissen")
    if not themenname:
        flash(request, "Bitte einen Themennamen angeben.", "err")
        return zurueck("/wissen")

    endung = Path(datei.filename).suffix.lower()
    puffer = bytearray()
    while stueck := await datei.read(1 << 20):
        puffer.extend(stueck)
        if len(puffer) > security.MAX_UPLOAD_BYTES:
            flash(request, "Datei zu groß.", "err")
            return zurueck("/wissen")

    try:
        ergebnis = await run_in_threadpool(
            ingest.aufnehmen, bytes(puffer), endung, rolle, themenname)
        if ergebnis["status"] == "neu":
            jobs.enqueue("kb_extract", {"document_id": ergebnis["document_id"]},
                         dedup_key=f"kb_extract:{ergebnis['document_id']}")
    except ingest.IngestError as exc:
        flash(request, str(exc), "err")
    else:
        flash(request, "Dieses Blatt ist bereits in Ihrer Sammlung." if
              ergebnis["status"] == "doppelt" else
              f"Datei eingereicht — sie wird jetzt für „{themenname}“ gelesen.")
    return zurueck("/wissen")


def render_wissen_detail(request: Request, doc_id: int):
    doc = db.q1("SELECT * FROM document WHERE id = ?", doc_id)
    if doc is None:
        flash(request, "Blatt nicht gefunden.", "err")
        return zurueck("/wissen")
    abschnitte = [dict(r) for r in db.q(
        """SELECT k.*, t.label AS thema_label FROM kb_chunk k
             LEFT JOIN topic t ON t.id = k.topic_id
            WHERE k.document_id=? ORDER BY k.position""", doc_id)]
    return render(request, "wissen_blatt.html", doc=dict(doc), abschnitte=abschnitte)


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


def handle_themen_neu(request: Request, label: str, beschreibung: str):
    neu = topics.anlegen(label, beschreibung)
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
