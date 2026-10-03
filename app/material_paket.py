"""Materialpakete: ein Arbeitsblatt kann viele Seiten haben.

Drei Wege führen Seiten in ein Paket: ein PDF (im Browser von pdf.js in seine
Seiten zerlegt), mehrere ausgewählte Bilder, mehrere Handyfotos. Auf dem
Server ist jede Seite ein normalisiertes Bild in `document` und eine Zeile in
`material_seite` — aber sie werden nie einzeln ausgewertet. Gelesen,
verstanden und zugeordnet wird das Paket als Ganzes.

Zum Modell geht dabei nur Text: die Seiten werden auf dem Gerät gelesen
(`static/blatt-lesen.js`, Tesseract als WASM) oder als Rückfall vom lokalen
Tesseract (`blatt_text.server_lesen`). Was in `material_seite.text` liegt,
ist bereits durch `blatt_text.kopf_entfernen` und `pii.scrub` gelaufen —
Namen, Klasse und Datum stehen dort nicht mehr drin.

Dieses Modul ist der geteilte technische Kern: Seiten speichern, lesen,
analysieren. `zweck` ist dabei nur der Ingest-Kontext, der die Analyse-
Rezepte und die Übernahme-Domäne wählt — danach sind die Wege getrennt:

    zweck 'lernen'         → `uebernehmen` legt Lernthemen an und ordnet
                             Seitentexte der Wissensbasis zu
    zweck 'klassenarbeit'  → `pruefinhalte_uebernehmen` gibt bestätigte
                             Prüfungsinhalte ans Formular der neuen Arbeit —
                             kein Lernthema, keine Wissensbasis
"""

from __future__ import annotations

import json
import logging
import time

from . import blatt_text, config, db, faecher, ingest, jobs, pii, prompts
from .adaptiv.normalisierung import normalisiere_thema
from .ai import AIPending

log = logging.getLogger("karo.material")

#: Ein Paket ist ein Blatt-Stapel, kein Ordner — mehr als zehn Seiten tippt
#: niemand mehr nach, und länger macht das Einlesen nur träge.
_OPS = config.ops()
MAX_SEITEN = _OPS.paket_max_seiten
#: Darunter ist ein Ergebnis kein Blatt, sondern Rauschen — dieselbe Grenze
#: wie in `static/blatt-lesen.js` und `blatt_text.server_lesen`.
MIN_ZEICHEN = _OPS.seite_min_zeichen
#: Getrennte Größengrenzen: ein Handyfoto ist selten über 15 MB, ein
#: gescanntes Skript kann größer sein, und das Paket insgesamt bleibt
#: unterhalb des Speicherfensters, das ein Upload belegen darf.
MAX_BILD_BYTES = _OPS.paket_max_bild_bytes
MAX_PDF_BYTES = _OPS.paket_max_pdf_bytes
MAX_PAKET_BYTES = _OPS.paket_max_bytes
MAX_TEXT_ZEICHEN = _OPS.paket_max_text_zeichen
MAX_THEMEN = _OPS.paket_max_themen

#: Bilder — auch die Kamera des Handys (HEIC). Kein PDF: die Seiten eines
#: PDFs zerlegt der Browser vor dem Hochladen, hier kommt keine PDF-Datei an.
SEITEN_ENDUNGEN = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}

ZWECKE = ("lernen", "klassenarbeit")

STATE_ANALYSE = "analyse"
STATE_BEREIT = "bereit"
STATE_UEBERNOMMEN = "uebernommen"
STATE_FEHLER = "fehler"


class PaketFehler(Exception):
    """Verständlicher Fehler im Upload-Ablauf — direkt anzeigbar."""


def _protokoll(ereignis: str, **felder) -> None:
    """Fachliche Logzeile — nie Seiteninhalte, nur Kennzahlen und IDs."""
    try:
        log.info(ereignis, extra={"fach": {"event": ereignis, **felder}})
    except Exception:                       # pragma: no cover
        pass


# ---------------------------------------------------------------------------
# Paket anlegen und pflegen
# ---------------------------------------------------------------------------

def _seite_speichern(daten: bytes, name: str,
                     subject: str | None) -> tuple[int, bool]:
    """Eine Seite als `document` ablegen. Gibt (id, neu angelegt) zurück —
    „neu" heißt: Datei und Zeile gehören diesem Paket und dürfen bei einem
    Abbruch wieder weggeräumt werden. Wirft PaketFehler, wenn die Datei
    sich nicht als Bild lesen lässt."""
    endung = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if endung not in SEITEN_ENDUNGEN:
        raise PaketFehler(
            f"„{name[:60]}“ ist keine Bildseite. Erlaubt sind PDF, JPG und PNG — "
            "ein PDF zerlegt Karo vorher im Browser in seine Seiten.")
    if len(daten) > MAX_BILD_BYTES:
        raise PaketFehler(
            f"„{name[:60]}“ ist mit {len(daten) // 1_048_576} MB zu groß — "
            f"ein Bild darf höchstens {MAX_BILD_BYTES // 1_048_576} MB haben.")
    try:
        aufnahme = ingest.aufnehmen(
            daten, endung, rolle="material",
            themenname="", subject=faecher.schluessel(subject))
    except ingest.IngestError as exc:
        raise PaketFehler(f"„{name[:60]}“: {exc}") from None
    return aufnahme["document_id"], aufnahme["status"] == "neu"


def _pdf_zerlegen(daten: bytes, name: str,
                  subject: str | None) -> list[tuple[int, bool]]:
    """Ein hochgeladenes PDF in Seiten-Dokumente zerlegen.

    Der Normalweg zerlegt das PDF schon im Browser (pdf.js, siehe
    `static/material-paket.js`) — dieser Weg ist der Rückfall für einen
    Browser ohne JavaScript, der die Datei als Ganzes schickt. Jede Seite
    wird wie in `ingest._ingest_pdf` über den Digest ihres gerenderten
    Bildes dedupliziert. Gibt (document_id, neu angelegt)-Paare zurück.
    """
    import hashlib
    import io
    import tempfile
    from pathlib import Path

    if len(daten) > MAX_PDF_BYTES:
        raise PaketFehler(
            f"„{name[:60]}“ ist mit {len(daten) // 1_048_576} MB zu groß — "
            f"ein PDF darf höchstens {MAX_PDF_BYTES // 1_048_576} MB haben.")

    tmp = Path(tempfile.mkdtemp(prefix="karo-paket-")) / "blatt.pdf"
    tmp.write_bytes(daten)
    try:
        try:
            doc = ingest._open_pdf(tmp)
        except ingest.IngestError as exc:
            raise PaketFehler(f"„{name[:60]}“: {exc}") from None
        dokumente = []
        cfg = config.load_safe()
        try:
            if doc.page_count > MAX_SEITEN:
                raise PaketFehler(
                    f"„{name[:60]}“ hat {doc.page_count} Seiten — ein Paket "
                    f"darf höchstens {MAX_SEITEN} haben. Bitte teile es auf.")
            for i in range(doc.page_count):
                bild = doc.seite(i)
                puffer = io.BytesIO()
                bild.save(puffer, format="PNG")
                digest = hashlib.sha256(puffer.getvalue()).hexdigest()
                bestehend = db.q1("SELECT id FROM document WHERE sha256=?",
                                  digest)
                if bestehend is not None:
                    dokumente.append((bestehend["id"], False))
                    continue
                ziel = config.scans_dir() / f"{digest}.jpg"
                try:
                    ingest._encode_image(bild, ziel, cfg.header_crop_percent)
                except ingest.IngestError as exc:
                    raise PaketFehler(
                        f"„{name[:60]}“, Seite {i + 1}: {exc}") from None
                with db.tx() as c:
                    cur = c.execute(
                        """INSERT INTO document
                               (sha256, source_name, stored_path, mime, rolle,
                                captured_on, state, subject, created_at)
                           VALUES (?, ?, ?, 'image/jpeg', 'material', ?,
                                   'neu', ?, ?)""",
                        (digest, f"{ingest.safe_name(name)[:180]} s{i + 1}",
                         str(ziel), db.today(),
                         faecher.schluessel(subject), db.now()))
                    dokumente.append((cur.lastrowid, True))
        finally:
            doc.close()
        return dokumente
    finally:
        try:
            tmp.unlink(missing_ok=True)
            tmp.parent.rmdir()
        except OSError:
            pass


def _dokumente_wegraumen(document_ids: list[int]) -> None:
    """Dokumente entfernen, die ein abgebrochener Upload neu angelegt hat —
    Zeile und Datei. Deduplizierte Fundstücke bleiben: sie gehörten schon
    wem anders."""
    from pathlib import Path

    for did in document_ids:
        zeile = db.q1("SELECT stored_path FROM document WHERE id=?", did)
        if zeile is None:
            continue
        try:
            Path(zeile["stored_path"]).unlink(missing_ok=True)
        except OSError:
            pass
        with db.tx() as c:
            c.execute("DELETE FROM document WHERE id=?", (did,))


def _datei_als_seiten(daten: bytes, name: str,
                      subject: str | None) -> list[tuple[int, str, bool]]:
    """Eine Datei zu ihren Seiten-Dokumenten: ein Bild ist eine Seite, ein
    PDF so viele, wie es hat. Gibt (document_id, art, neu)-Tripel zurück."""
    endung = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if endung == ".pdf":
        return [(dokument, "pdf", neu) for dokument, neu in
                _pdf_zerlegen(daten, name, subject)]
    dokument, neu = _seite_speichern(daten, name, subject)
    return [(dokument, "foto", neu)]


def _seitentext(meta: dict) -> tuple[str, str]:
    """Geschwärzten Text und Seiten-Status aus den Browser-Angaben ableiten."""
    roh = str(meta.get("text") or "")[:MAX_TEXT_ZEICHEN]
    sauber = pii.scrub(blatt_text.kopf_entfernen(roh),
                       config.load_safe().learner_name)
    if len(sauber.strip()) < MIN_ZEICHEN:
        return "", "offen"
    return sauber, "gelesen"


def _pruefe_liste(dateien: list, metadaten: list[dict], vorhanden: int,
                  bisher_bytes: int = 0) -> None:
    if not dateien:
        raise PaketFehler("Es wurde keine Seite ausgewählt.")
    # Ohne JavaScript kommen nur Dateien — die Metadaten fehlen dann ganz.
    if metadaten and len(dateien) != len(metadaten):
        raise PaketFehler("Die Seitenangaben passen nicht zu den Dateien.")
    if vorhanden + len(dateien) > MAX_SEITEN:
        raise PaketFehler(
            f"Ein Paket darf höchstens {MAX_SEITEN} Seiten haben — "
            f"es sind schon {vorhanden} darin.")
    gesamt = bisher_bytes + sum(len(daten) for _, daten in dateien)
    if gesamt > MAX_PAKET_BYTES:
        raise PaketFehler(
            f"Zusammen sind die Seiten zu groß — ein Paket darf höchstens "
            f"{MAX_PAKET_BYTES // 1_048_576} MB haben.")


def _seiten_abladen(dateien: list[tuple[str, bytes]], metadaten: list[dict],
                    subject: str | None) -> list[tuple[int, str, dict, bool]]:
    """Jede Datei zu ihren Seiten-Dokumenten — eigene Transaktionen darin.

    Gibt (document_id, art, meta, neu) je Seite zurück. Eine Datei kann
    mehrere Seiten ergeben (PDF ohne Browser-Zerlegung); der Browser-Text
    aus `metadaten` gilt nur, wenn die Datei genau eine Seite war — sonst
    würde ein Seitentext auf fremde Seiten fallen. Scheitert eine Datei,
    werden die neu angelegten Dokumente wieder entfernt.
    """
    seiten = []
    eigene = []
    try:
        for i, (name, daten) in enumerate(dateien):
            meta = dict(metadaten[i]) if i < len(metadaten) else {}
            meta.setdefault("name", name)
            for dokument, art, neu in _datei_als_seiten(daten, name, subject):
                if neu:
                    eigene.append(dokument)
                seiten.append(
                    (dokument, art,
                     {"name": meta["name"]} if art == "pdf" else meta, neu))
        return seiten
    except Exception:
        _dokumente_wegraumen(eigene)
        raise


def _seiten_eintragen(c, paket_id: int, start: int,
                      seiten: list[tuple[int, str, dict, bool]]) -> int:
    """Legt die Seiten-Zeilen an — nur DB, die Dateien liegen schon."""
    for i, (dokument, art, meta, _neu) in enumerate(seiten, 1):
        text, stand = _seitentext(meta)
        c.execute(
            """INSERT INTO material_seite
                   (paket_id, position, document_id, quell_name, art, text,
                    konfidenz, state, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (paket_id, start + i, dokument,
             str(meta.get("name") or "")[:200] or None,
             str(meta.get("art") or art)[:20],
             text or None,
             meta.get("konfidenz") if isinstance(meta.get("konfidenz"),
                                                 (int, float)) else None,
             stand, db.now()))
    return len(seiten)


def anlegen(zweck: str, subject: str | None, dateien: list[tuple[str, bytes]],
            metadaten: list[dict]) -> int:
    """Ein neues Paket aus Seiten-Bildern. Gibt die Paket-ID zurück.

    `dateien` und `metadaten` laufen parallel — die Reihenfolge ist die
    Seitenfolge, die das Kind in der Vorschau festgelegt hat.
    """
    if zweck not in ZWECKE:
        raise PaketFehler("Unbekannter Verwendungszweck.")
    _pruefe_liste(dateien, metadaten, 0)
    fach = faecher.schluessel(subject)
    seiten = _seiten_abladen(dateien, metadaten, fach)

    jetzt = db.now()
    try:
        with db.tx() as c:
            cur = c.execute(
                """INSERT INTO material_paket
                       (zweck, subject, state, original_bytes,
                        created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (zweck, fach, STATE_ANALYSE,
                 sum(len(d) for _, d in dateien), jetzt, jetzt))
            paket_id = cur.lastrowid
            seiten_anzahl = _seiten_eintragen(c, paket_id, 0, seiten)
    except Exception:
        _dokumente_wegraumen([d for d, _, _, neu in seiten if neu])
        raise

    jobs.enqueue("material_analyse", {"paket_id": paket_id},
                 dedup_key=f"material_analyse:{paket_id}")
    _protokoll("material_upload_created", upload_id=paket_id,
               page_count=seiten_anzahl, purpose=zweck)
    return paket_id


def anhaengen(paket_id: int, dateien: list[tuple[str, bytes]],
              metadaten: list[dict]) -> int:
    """Weitere Seiten in ein bestehendes Paket — z. B. eine neu fotografierte
    Seite nach „schwer lesbar". Danach läuft die Analyse erneut."""
    paket = _paket(paket_id)
    if paket["state"] == STATE_UEBERNOMMEN:
        raise PaketFehler("Dieses Material ist bereits übernommen.")
    vorhanden = db.q1(
        "SELECT COUNT(*) AS n FROM material_seite WHERE paket_id=?",
        paket_id)["n"]
    _pruefe_liste(dateien, metadaten, vorhanden,
                  int(paket["original_bytes"] or 0))

    seiten = _seiten_abladen(dateien, metadaten, paket["subject"])
    jetzt = db.now()
    try:
        with db.tx() as c:
            start = c.execute(
                "SELECT COALESCE(MAX(position), 0) AS m FROM material_seite "
                "WHERE paket_id=?", (paket_id,)).fetchone()["m"]
            seiten_anzahl = _seiten_eintragen(c, paket_id, start, seiten)
            c.execute("UPDATE material_paket SET state=?, fehler=NULL, "
                      "original_bytes=original_bytes+?, updated_at=? "
                      "WHERE id=?",
                      (STATE_ANALYSE, sum(len(d) for _, d in dateien),
                       jetzt, paket_id))
    except Exception:
        _dokumente_wegraumen([d for d, _, _, neu in seiten if neu])
        raise
    jobs.enqueue("material_analyse", {"paket_id": paket_id},
                 dedup_key=f"material_analyse:{paket_id}")
    _protokoll("material_page_added", upload_id=paket_id,
               page_count=seiten_anzahl)
    return paket_id


def seite_entfernen(paket_id: int, seite_id: int) -> bool:
    """Eine Seite aus dem Paket nehmen. False = Paket ist damit leer und weg."""
    paket = _paket(paket_id)
    if paket["state"] == STATE_UEBERNOMMEN:
        raise PaketFehler("Dieses Material ist bereits übernommen.")
    with db.tx() as c:
        c.execute("DELETE FROM material_seite WHERE id=? AND paket_id=?",
                  (seite_id, paket_id))
        rest = [r["id"] for r in c.execute(
            "SELECT id FROM material_seite WHERE paket_id=? ORDER BY position",
            (paket_id,))]
        if not rest:
            c.execute("DELETE FROM material_paket WHERE id=?", (paket_id,))
            _protokoll("material_page_removed", upload_id=paket_id,
                       page_count=0)
            return False
        # Nummern wieder lückenlos, damit „Seite n" in der Anzeige stimmt.
        for position, zeilen_id in enumerate(rest, 1):
            c.execute("UPDATE material_seite SET position=? WHERE id=?",
                      (position, zeilen_id))
        c.execute("UPDATE material_paket SET state=?, fehler=NULL, updated_at=? "
                  "WHERE id=?", (STATE_ANALYSE, db.now(), paket_id))
    jobs.enqueue("material_analyse", {"paket_id": paket_id},
                 dedup_key=f"material_analyse:{paket_id}")
    _protokoll("material_page_removed", upload_id=paket_id,
               page_count=len(rest))
    return True


def erneut_analysieren(paket_id: int) -> None:
    """„Noch einmal versuchen" — dieselben Texte, derselbe Ablauf."""
    paket = _paket(paket_id)
    if paket["state"] not in (STATE_FEHLER, STATE_BEREIT):
        raise PaketFehler("Dieses Material wird gerade schon gelesen.")
    with db.tx() as c:
        c.execute("UPDATE material_paket SET state=?, fehler=NULL, updated_at=? "
                  "WHERE id=?", (STATE_ANALYSE, db.now(), paket_id))
    jobs.enqueue("material_analyse", {"paket_id": paket_id},
                 dedup_key=f"material_analyse:{paket_id}")
    _protokoll("material_processing_started", upload_id=paket_id)


# ---------------------------------------------------------------------------
# Anzeige
# ---------------------------------------------------------------------------

def _paket(paket_id: int) -> dict:
    paket = db.q1("SELECT * FROM material_paket WHERE id=?", paket_id)
    if paket is None:
        raise PaketFehler("Dieses Material gibt es nicht (mehr).")
    return dict(paket)


def holen(paket_id: int) -> dict:
    """Paket mit Seiten und aufbereitetem Ergebnis für die Anzeige."""
    paket = _paket(paket_id)
    paket["seiten"] = [dict(r) for r in db.q(
        "SELECT * FROM material_seite WHERE paket_id=? ORDER BY position",
        paket_id)]
    try:
        ergebnis = json.loads(paket["ergebnis"] or "{}")
    except json.JSONDecodeError:
        ergebnis = {}
    ergebnis.setdefault("themen", [])
    ergebnis.setdefault("fach", paket["subject"])
    paket["ergebnis"] = ergebnis
    return paket


# ---------------------------------------------------------------------------
# Analyse-Job: lesen, verstehen, vorschlagen — aber nichts anlegen
# ---------------------------------------------------------------------------

def _seite_nachlesen(seite: dict) -> None:
    """Rückfall für eine Seite ohne Browser-Text: lokaler Tesseract auf dem
    Familienserver. Die Datei bleibt — sie gehört zum Paket."""
    dokument = db.q1("SELECT * FROM document WHERE id=?", seite["document_id"])
    if dokument is None or not blatt_text.server_lesen_moeglich():
        stand, fehler = "fehler", "Auf diesem Gerät gibt es keine Lesehilfe."
    else:
        from pathlib import Path
        pfad = Path(dokument["stored_path"])
        roh = blatt_text.server_lesen(pfad) if pfad.is_file() else ""
        text = pii.scrub(blatt_text.kopf_entfernen(roh),
                         config.load_safe().learner_name)
        if len(text.strip()) >= MIN_ZEICHEN:
            stand, fehler = "gelesen", None
            with db.tx() as c:
                c.execute("UPDATE material_seite SET text=?, art='server', "
                          "state=?, fehler=NULL WHERE id=?",
                          (text[:MAX_TEXT_ZEICHEN], stand, seite["id"]))
            return
        stand, fehler = "fehler", "Auf dieser Seite war zu wenig lesbar."
    with db.tx() as c:
        c.execute("UPDATE material_seite SET state=?, fehler=? WHERE id=?",
                  (stand, fehler, seite["id"]))


def _modell_aufruf(paket_id: int, fach_hint: str | None, purpose: str,
                   seiten_anzahl: int, prompt: str, schema: dict) -> dict:
    """Das Modell liest geschwärzten Seitentext — nie ein Bild.

    Der Text darf zum Modell, aber er bleibt nicht dauerhaft im Audit:
    `audit_prompt` sorgt dafür, dass in `llm_call` nur Metadaten und der
    Hash des tatsächlichen Prompts liegen — an dem Hash erkennt man später,
    ob es derselbe Modellinput war, ohne den Inhalt zu kennen.

    Wirft AIError; der Aufrufer entscheidet über den Umgang."""
    import hashlib

    from .ai import AIClient
    cfg = config.load_safe()
    audit = (
        "[MATERIAL_ANALYSE_REDACTED]\n"
        f"upload_id={paket_id}\n"
        f"page_count={seiten_anzahl}\n"
        f"subject={faecher.schluessel(fach_hint) or '-'}\n"
        f"input_chars={len(prompt)}\n"
        f"prompt_hash=sha256:"
        f"{hashlib.sha256(prompt.encode('utf-8')).hexdigest()}")
    ergebnis = AIClient.from_config(cfg).complete(
        purpose=purpose, prompt=prompt, schema=schema,
        system=prompts.SYSTEM, audit_prompt=audit)
    return ergebnis.data if isinstance(ergebnis.data, dict) else {}


def _analyse_lernen(paket_id: int, fach_hint: str | None,
                    seiten_texte: list[str]) -> dict:
    """Lernmaterial: das Modell liest die Unterrichtsthemen des Blatts."""
    cfg = config.load_safe()
    nummern = "\n\n".join(
        f"=== Seite {i} ===\n{text}" for i, text in enumerate(seiten_texte, 1))
    prompt = prompts.material_prompt(cfg.learner_grade, fach_hint, nummern)
    daten = _modell_aufruf(paket_id, fach_hint, "material_analyse",
                           len(seiten_texte), prompt, prompts.MATERIAL_SCHEMA)
    return _ergebnis_pruefen(daten, len(seiten_texte))


def _analyse_klassenarbeit(paket_id: int, fach_hint: str | None,
                           seiten_texte: list[str]) -> dict:
    """Themenblatt: das Modell liest die Prüfungsinhalte der Arbeit.

    Eigenes Schema, eigener Prompt (`prompts.EXAM_MATERIAL_SCHEMA` /
    `themenblatt_prompt`) — das Ergebnis ist kein Lernvorschlag, sondern
    füllt nur das Formular der neuen Klassenarbeit.
    """
    cfg = config.load_safe()
    nummern = "\n\n".join(
        f"=== Seite {i} ===\n{text}" for i, text in enumerate(seiten_texte, 1))
    prompt = prompts.themenblatt_prompt(cfg.learner_grade, fach_hint, nummern)
    daten = _modell_aufruf(paket_id, fach_hint, "themenblatt_analyse",
                           len(seiten_texte), prompt,
                           prompts.EXAM_MATERIAL_SCHEMA)
    ergebnis = _ergebnis_pruefen(
        {"fach": daten.get("fach"),
         "themen": daten.get("pruefungsinhalte")}, len(seiten_texte))
    ergebnis["hinweise"] = [
        " ".join(str(h).split())[:200]
        for h in (daten.get("hinweise") or [])[:10]
        if str(h or "").strip()][:10]
    termin = str(daten.get("termin") or "").strip()
    try:
        import datetime as _dt
        _dt.date.fromisoformat(termin)
    except ValueError:
        termin = ""
    ergebnis["termin"] = termin or None
    return ergebnis


#: Welches Rezept der Analyse-Job fährt — der Ingest-Kontext waehlt, die
#: Domain entscheidet nicht mehr mit.
_ANALYSE = {"lernen": _analyse_lernen,
            "klassenarbeit": _analyse_klassenarbeit}


def _ergebnis_pruefen(daten: dict, seiten_anzahl: int) -> dict:
    """Maschinelle Antwort an die Form binden. Ungültiges wird verworfen,
    nicht repariert."""
    themen = []
    for roh in (daten.get("themen") or [])[:MAX_THEMEN]:
        if not isinstance(roh, dict):
            continue
        titel = " ".join(str(roh.get("titel") or "").split())[:200]
        if not titel:
            continue
        seiten = sorted({int(s) for s in (roh.get("seiten") or [])
                         if isinstance(s, int) and 1 <= s <= seiten_anzahl})
        konfidenz = roh.get("konfidenz")
        themen.append({
            "titel": titel, "seiten": seiten,
            "konfidenz": round(float(konfidenz), 2)
            if isinstance(konfidenz, (int, float)) else None})
    fach = faecher.schluessel(daten.get("fach"))
    return {"fach": fach, "themen": themen, "automatisch": True}


def _analyse_ohne_modell(fach: str | None, gesamt: str) -> dict:
    """Regel-Fallback: Themen aus dem eigenen Katalog per Wortabgleich.

    Ohne Modell erfindet Karo keine Themennamen — es schlägt nur vor, was
    schon im Fach existiert, und sagt ehrlich, dass der Rest Handarbeit ist.
    """
    vorschlaege = blatt_text.vorschlaege(gesamt, fach) if fach else []
    return {"fach": fach, "automatisch": False,
            "themen": [{"titel": v["label"], "seiten": [], "konfidenz": None,
                        "vorhanden": v["id"]} for v in vorschlaege]}


@jobs.handler("material_analyse")
def job_material_analyse(payload: dict) -> None:
    paket_id = int(payload["paket_id"])
    paket = db.q1("SELECT * FROM material_paket WHERE id=?", paket_id)
    if paket is None or paket["state"] != STATE_ANALYSE:
        return
    begonnen = time.monotonic()
    _protokoll("material_processing_started", upload_id=paket_id,
               purpose=paket["zweck"])

    seiten = [dict(r) for r in db.q(
        "SELECT * FROM material_seite WHERE paket_id=? ORDER BY position",
        paket_id)]
    for seite in seiten:
        if seite["state"] == "offen":
            _seite_nachlesen(seite)

    seiten = [dict(r) for r in db.q(
        "SELECT * FROM material_seite WHERE paket_id=? ORDER BY position",
        paket_id)]
    gelesen = [s for s in seiten if s["state"] == "gelesen" and s["text"]]
    unleserlich = len(seiten) - len(gelesen)
    _protokoll("material_ocr_completed", upload_id=paket_id,
               page_count=len(seiten), readable=len(gelesen),
               unreadable=unleserlich)

    def fehler(text: str) -> None:
        with db.tx() as c:
            c.execute("UPDATE material_paket SET state=?, fehler=?, "
                      "updated_at=? WHERE id=?",
                      (STATE_FEHLER, text[:300], db.now(), paket_id))
        _protokoll("material_processing_failed", upload_id=paket_id,
                   error_type="unleserlich" if not gelesen else "analyse")

    if not gelesen:
        fehler("Auf den Seiten war nichts sicher lesbar. Bitte flach "
               "hinlegen, von oben und ohne Schatten neu fotografieren.")
        return

    gesamt = "\n\n".join(s["text"] for s in gelesen)
    fach_hint = (faecher.name(paket["subject"]) if paket["subject"]
                 else None)
    try:
        ergebnis = _ANALYSE[paket["zweck"]](
            paket_id, fach_hint, [s["text"] for s in gelesen])
    except AIPending:
        raise                           # der Anbieter arbeitet noch — Job parken
    except Exception as exc:                # noqa: BLE001 - Meldung steht in fehler
        from .ai import AIError
        if not isinstance(exc, AIError):
            log.warning("Material-Analyse unerwartet fehlgeschlagen",
                        exc_info=True)
        fehler(str(exc) if isinstance(exc, AIError)
               else "Die Analyse ist fehlgeschlagen. Bitte erneut versuchen.")
        return

    fach = ergebnis["fach"] or faecher.erkenne(gesamt) or paket["subject"]
    if fach:
        # Das erkannte Fach gilt für das Paket und seine Blätter — der Mensch
        # kann es in der Prüfansicht noch korrigieren.
        with db.tx() as c:
            c.execute("UPDATE material_paket SET subject=? WHERE id=? "
                      "AND subject IS NULL", (fach, paket_id))
            for seite in gelesen:
                c.execute("UPDATE document SET subject=? WHERE id=? "
                          "AND subject IS NULL", (fach, seite["document_id"]))
    if not ergebnis["themen"] and fach:
        ergebnis = _analyse_ohne_modell(fach, gesamt)
        ergebnis["automatisch"] = False
    # Unsicher, wenn das erkannte Fach vom aktiven abweicht — die Prüfansicht
    # bittet dann ausdrücklich um einen zweiten Blick.
    ergebnis["fach_unsicher"] = bool(
        paket["subject"] and ergebnis["fach"]
        and ergebnis["fach"] != paket["subject"])

    with db.tx() as c:
        c.execute("UPDATE material_paket SET state=?, ergebnis=?, fehler=NULL, "
                  "updated_at=? WHERE id=?",
                  (STATE_BEREIT,
                   json.dumps(ergebnis, ensure_ascii=False), db.now(), paket_id))
    _protokoll("material_analysis_completed", upload_id=paket_id,
               page_count=len(seiten), topics=len(ergebnis["themen"]),
               duration_ms=int((time.monotonic() - begonnen) * 1000))
    _protokoll("material_review_ready", upload_id=paket_id)


# ---------------------------------------------------------------------------
# Übernehmen: erst jetzt entsteht etwas — nach der Bestätigung, je Domain
# ---------------------------------------------------------------------------

def _namen_pruefen(themen: list[str], was: str) -> list[str]:
    namen = list(dict.fromkeys(
        " ".join(t.split()) for t in themen if t and t.strip()))
    namen = [n for n in namen if len(n) <= 200][:MAX_THEMEN]
    if not namen:
        raise PaketFehler(f"Bitte mindestens {was} auswählen oder eintragen.")
    return namen


def _abschliessen(paket: dict, ergebnis: dict, fach: str,
                  gewaehlt: list[str], abgewiesen: list[str]) -> None:
    """Paket auf übernommen stellen — die geteilte technische Buchung."""
    ergebnis["gewaehlt"] = gewaehlt + abgewiesen
    with db.tx() as c:
        c.execute("UPDATE material_paket SET state=?, subject=?, ergebnis=?, "
                  "updated_at=? WHERE id=?",
                  (STATE_UEBERNOMMEN, fach,
                   json.dumps(ergebnis, ensure_ascii=False), db.now(),
                   paket["id"]))
    _protokoll("material_import_completed", upload_id=paket["id"],
               purpose=paket["zweck"], topics=len(gewaehlt),
               rejected=len(abgewiesen))


def uebernehmen(paket_id: int, fach: str, themen: list[str],
                klasse: int | None = None) -> dict:
    """Lernen: die bestätigten Themen werden Lernthemen.

    Jedes Thema läuft durch denselben Weg wie ein von Hand eingetragenes —
    `learning_hub.create_topic` mit seiner Fachprüfung. Seiteninhalte, die
    zu einem übernommenen Thema gehören, werden in der Wissensbasis diesem
    Thema zugeordnet. Nur für Pakete des Lernbereichs.
    """
    paket = _paket(paket_id)
    if paket["zweck"] != "lernen":
        raise PaketFehler("Dieses Paket gehört zu einer Klassenarbeit.")
    if paket["state"] != STATE_BEREIT:
        raise PaketFehler("Dieses Material ist nicht bereit zum Übernehmen.")
    fach = faecher.pflicht(fach)
    namen = _namen_pruefen(themen, "ein Thema")

    aktuell = holen(paket_id)
    ergebnis = aktuell["ergebnis"]
    quell_seiten = {normalisiere_thema(t["titel"]): t.get("seiten") or []
                    for t in ergebnis.get("themen", [])}

    # Text der Seiten in die Wissensbasis — jetzt, wo das Fach endgültig ist.
    from .services import learning_hub
    seiten_dokumente: dict[int, int] = {}
    for seite in aktuell["seiten"]:
        if seite["state"] == "gelesen" and seite["text"] \
                and seite["document_id"]:
            blatt_text.aufnehmen(seite["text"], fach,
                                 document_id=seite["document_id"])
        if seite["document_id"]:
            seiten_dokumente[int(seite["position"])] = seite["document_id"]

    angelegt, abgewiesen = [], []
    for name in namen:
        try:
            topic_id = learning_hub.create_topic(
                name, fach, klasse, modell=False)
        except faecher.SubjectMismatch:
            abgewiesen.append(name)
            continue
        angelegt.append(name)
        # Seiten mit diesem Thema bekommen ihre Abschnitte zugeordnet —
        # eine Seite geht an das erste Thema, das sie beansprucht.
        for pos in quell_seiten.get(normalisiere_thema(name), []):
            dokument = seiten_dokumente.get(int(pos))
            if dokument and not db.q1(
                    "SELECT 1 FROM kb_chunk WHERE document_id=? "
                    "AND topic_id IS NOT NULL", dokument):
                blatt_text.zuordnen(dokument, topic_id)

    _abschliessen(paket, ergebnis, fach, angelegt, abgewiesen)
    return {"angelegt": angelegt, "abgewiesen": abgewiesen}


def pruefinhalte_uebernehmen(paket_id: int, fach: str,
                             themen: list[str]) -> dict:
    """Klassenarbeit: die bestätigten Prüfungsinhalte für das Formular.

    Legt absichtlich **nichts** an: kein Lernthema (`learning_hub` wird nie
    gerufen), kein Eintrag in der Wissensbasis. Die Prüfungsthemen
    entstehen erst beim Anlegen der Arbeit (`exam.create_exam`) — hier
    wird nur gemerkt, was der Mensch auf dem Themenblatt bestätigt hat.
    """
    paket = _paket(paket_id)
    if paket["zweck"] != "klassenarbeit":
        raise PaketFehler("Dieses Paket gehört zum Lernbereich.")
    if paket["state"] != STATE_BEREIT:
        raise PaketFehler("Dieses Material ist nicht bereit zum Übernehmen.")
    fach = faecher.pflicht(fach)
    namen = _namen_pruefen(themen, "einen Prüfungsinhalt")

    _abschliessen(paket, holen(paket_id)["ergebnis"], fach, namen, [])
    return {"inhalte": namen, "fach": fach}


def gewaehlte_pruefinhalte(paket_id: int) -> dict:
    """Das abgeschlossene Themenblatt-Ergebnis für das Klassenarbeitsformular:
    `themen`, `fach`, `termin` — leer, wenn das Paket nicht dazu gehört oder
    noch nicht übernommen wurde."""
    paket = _paket(paket_id)
    if paket["zweck"] != "klassenarbeit" or paket["state"] != STATE_UEBERNOMMEN:
        return {}
    try:
        ergebnis = json.loads(paket["ergebnis"] or "{}")
    except json.JSONDecodeError:
        return {}
    return {"themen": list(ergebnis.get("gewaehlt") or []),
            "fach": paket["subject"],
            "termin": ergebnis.get("termin")}
