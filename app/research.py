"""Web-Recherche nach Lernmaterial.

Drei Regeln, weil hier ein Kind am Ende der Kette steht:

  1. **Kanalliste.** Gesucht wird nur auf Seiten, die für deutschen
     Schulunterricht gemacht sind. Kein offenes Web, kein „irgendein Video“.
  2. **Freigabe.** Ein Fund wird nie automatisch benutzt. Er erscheint als
     Vorschlag, ein Erwachsener hakt ihn ab. Der Inhalt einer Quelle wird
     ERST NACH der Freigabe geholt (`job_research_fetch()`) — nie vorher.
  3. **Anregung, außer es gibt nichts anderes.** Solange eigenes
     Schulmaterial vorliegt, geht ein freigegebener Fund nur als Titel in
     die Erklärung ein — die Fakten kommen aus dem Schulmaterial, siehe
     teaching.py. Gibt es für ein Thema KEIN eigenes Material, darf eine
     freigegebene, inhaltlich geholte Quelle stattdessen selbst zur
     Faktengrundlage werden (`material_fuer()`) — dann prüft die
     Gegenprüfung die Erklärung gegen genau diese Quelle, nicht gegen ein
     Schulblatt, das es nicht gibt.

Ohne Websuche funktioniert Karo vollständig; die Recherche ist ein Zusatz.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from . import config, db, jobs, prompts, topics
from .domain import ERROR_LABELS
from .llm import ClaudeClient, ClaudeError

log = logging.getLogger("karo.research")

VORSCHLAG = "vorschlag"
FREIGEGEBEN = "freigegeben"
ABGELEHNT = "abgelehnt"

#: Seiten, auf denen für deutschen Schulunterricht gesucht werden darf.
#: Bewusst eine Liste und keine Sperrliste: was hier nicht steht, kommt nicht
#: vor. Erweitern ist eine Codeänderung — das ist Absicht.
ERLAUBTE_QUELLEN = {
    "youtube.com": "YouTube (nur die Kanäle unten)",
    "youtu.be": "YouTube (nur die Kanäle unten)",
    "www.youtube.com": "YouTube (nur die Kanäle unten)",
    "studyflix.de": "Studyflix",
    "www.studyflix.de": "Studyflix",
    "simpleclub.com": "simpleclub",
    "www.simpleclub.com": "simpleclub",
    "serlo.org": "Serlo (gemeinnützig, offene Lernplattform)",
    "de.serlo.org": "Serlo (gemeinnützig, offene Lernplattform)",
    "mathe-lerntipps.de": "Mathe-Lerntipps",
    "bettermarks.com": "bettermarks",
    "de.bettermarks.com": "bettermarks",
    "schlaukopf.de": "Schlaukopf",
    "www.schlaukopf.de": "Schlaukopf",
    "grundschulkoenig.de": "Grundschulkönig",
    "www.grundschulkoenig.de": "Grundschulkönig",
    "planet-schule.de": "Planet Schule (SWR/WDR)",
    "www.planet-schule.de": "Planet Schule (SWR/WDR)",
    "br.de": "BR (alpha Lernen)",
    "www.br.de": "BR (alpha Lernen)",
}


def erlaubte_quellen() -> dict[str, str]:
    """Gibt nur die aktivierten Domains für die Recherche zurück."""
    cfg = config.load_safe()
    quellen = cfg.recherche_quellen or config.RESEARCH_SOURCE_DEFAULTS
    ergebnis = {}
    for quelle in quellen:
        if quelle.get("active", True) is not True:
            continue
        domain = str(quelle.get("domain", "")).lower().strip().removeprefix("www.")
        label = str(quelle.get("label", domain)).strip() or domain
        if domain:
            ergebnis[domain] = label
    return ergebnis


def quellen_liste() -> list[dict]:
    """Alle gespeicherten Quellen inklusive ihres Aktivierungszustands."""
    cfg = config.load_safe()
    quellen = cfg.recherche_quellen or config.RESEARCH_SOURCE_DEFAULTS
    return [{"domain": str(q.get("domain", "")).lower().strip().removeprefix("www."),
             "label": str(q.get("label", q.get("domain", ""))).strip(),
             "active": q.get("active", True) is True}
            for q in quellen if q.get("domain")]


def quellen_vorschlaege(grade: int, subject: str) -> list[dict]:
    """Altersgerechte Vorschläge für den persönlichen Quellenkatalog."""
    grundschule = grade <= 4
    vorschlaege = [
        {"domain": "grundschulkoenig.de", "label": "Grundschulkönig",
         "hinweis": "Grundschule"},
        {"domain": "serlo.org", "label": "Serlo",
         "hinweis": "Klassen 5–13"},
        {"domain": "studyflix.de", "label": "Studyflix",
         "hinweis": "Klassen 5–13"},
        {"domain": "planet-schule.de", "label": "Planet Schule",
         "hinweis": "Alle Klassen"},
        {"domain": "simpleclub.com", "label": "simpleclub",
         "hinweis": f"{subject}, Klassen 5–13"},
    ]
    return [q for q in vorschlaege if not grundschule or q["domain"] != "simpleclub.com"]

#: YouTube-Kanäle, die für deutschen Schulunterricht bekannt und geeignet sind.
#: Ein YouTube-Treffer wird nur vorgeschlagen, wenn einer dieser Namen im Titel
#: oder Kanal auftaucht.
ERLAUBTE_KANAELE = (
    "lehrerschmidt", "mathe by daniel jung", "daniel jung", "studyflix",
    "simpleclub", "simple club", "the simple maths", "the simple club",
    "mathegym", "kapiert.de", "sofatutor", "alpha lernen", "planet schule",
    "musstewissen", "mathenachhilfe", "gerd anders",
)

MAX_TREFFER = 8


def client() -> ClaudeClient:
    return ClaudeClient.from_config(config.load())


# --------------------------------------------------------------------------
# Prüfung eines Treffers
# --------------------------------------------------------------------------

def quelle_erlaubt(url: str) -> tuple[bool, str]:
    """(erlaubt, Kanalname) — die einzige Stelle, die über Zulassung entscheidet."""
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False, ""
    if not host:
        return False, ""
    host = host.removeprefix("www.")
    for erlaubt, name in erlaubte_quellen().items():
        if host == erlaubt.removeprefix("www."):
            return True, name
    return False, ""


def youtube_kanal_erlaubt(titel: str, kanal: str | None) -> bool:
    text = f"{titel} {kanal or ''}".lower()
    return any(k in text for k in ERLAUBTE_KANAELE)


def _zulassen(url: str, titel: str, kanal: str | None) -> tuple[bool, str]:
    erlaubt, quelle = quelle_erlaubt(url)
    if not erlaubt:
        return False, ""
    if "youtu" in url.lower() and not youtube_kanal_erlaubt(titel, kanal):
        return False, ""
    return True, kanal or quelle


# --------------------------------------------------------------------------
# Suchen
# --------------------------------------------------------------------------

def anfordern(topic_id: int) -> bool:
    cfg = config.load_safe()
    if not cfg.recherche_erlaubt:
        return False
    if topics.get(topic_id) is None:
        return False
    return jobs.enqueue("research", {"topic_id": topic_id},
                        dedup_key=f"research:{topic_id}:{db.today()}") is not None


@jobs.handler("research")
def job_research(payload: dict) -> None:
    """Sucht Lernmaterial und legt die Funde als Vorschlag ab.

    Die Suche selbst läuft über das Modell: es hat Zugriff auf Websuche und
    kennt die Kanalliste aus dem Prompt. Danach filtert dieser Code noch
    einmal hart — dem Modell wird nicht geglaubt, wo es um die Zulassung geht.
    """
    topic_id = int(payload["topic_id"])
    thema = topics.get(topic_id)
    if thema is None:
        return
    cfg = config.load()
    if not cfg.recherche_erlaubt:
        return

    fehlerbild = ERROR_LABELS.get(thema.get("haupt_fehler") or "")

    begriffe = client().complete(
        purpose="research_terms",
        prompt=prompts.search_prompt(cfg.learner_grade, cfg.subject,
                                     thema["label"], fehlerbild),
        schema=prompts.SEARCH_SCHEMA,
        system=prompts.SYSTEM,
    ).data.get("suchbegriffe") or []

    if not begriffe:
        return

    roh = _suchen(begriffe, cfg.learner_grade)
    if not roh:
        log.info("Recherche zu %s: keine Treffer auf erlaubten Seiten",
                 thema["label"])
        return

    bewertet = client().complete(
        purpose="research_rank",
        prompt=prompts.rank_prompt(cfg.learner_grade, thema["label"], roh),
        schema=prompts.RANK_SCHEMA,
        system=prompts.SYSTEM,
    ).data.get("bewertungen") or []

    gespeichert = 0
    with db.tx() as c:
        for t in bewertet:
            if not t.get("passt"):
                continue
            url = (t.get("url") or "").strip()
            titel = (t.get("titel") or "").strip()
            if not url or not titel:
                continue
            # Zweite, harte Prüfung: das Modell darf keine Quelle einschmuggeln.
            ok, kanal = _zulassen(url, titel, t.get("kanal"))
            if not ok:
                log.info("Fund verworfen (Quelle nicht zugelassen): %s", url)
                continue
            c.execute(
                """INSERT OR IGNORE INTO research_hit
                       (topic_id, titel, url, kanal, warum, state, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (topic_id, titel[:300], url[:600], (kanal or "")[:120] or None,
                 (t.get("warum") or "")[:400] or None, VORSCHLAG, db.now()))
            gespeichert += 1
            if gespeichert >= MAX_TREFFER:
                break


def _suchen(begriffe: list[str], grade: int) -> list[dict]:
    """Websuche über das Modell, danach Vorfilter auf erlaubte Seiten.

    Steht keine Websuche zur Verfügung — etwa weil der Container kein Netz
    hat oder das Backend sie nicht anbietet — gibt die Funktion eine leere
    Liste zurück. Karo funktioniert dann ohne Recherche weiter.
    """
    schema = {
        "type": "object",
        "properties": {
            "treffer": {
                "type": "array", "maxItems": 20,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "kanal": {"type": ["string", "null"]},
                    },
                    "required": ["title", "url", "kanal"],
                },
            }
        },
        "required": ["treffer"],
    }
    erlaubte = ", ".join(sorted(set(erlaubte_quellen().values())))
    kanaele = ", ".join(ERLAUBTE_KANAELE[:12])
    prompt = f"""Suche im Netz nach deutschem Lernmaterial für Klassenstufe
{grade} zu: {', '.join(begriffe[:3])}

Gib nur Treffer von diesen Seiten zurück: {erlaubte}
Bei YouTube nur diese Kanäle: {kanaele}

Nenne Titel, vollständige URL und, wenn erkennbar, den Kanal. Erfinde keine
URLs — gib nur zurück, was du tatsächlich gefunden hast. Findest du nichts
auf diesen Seiten, gib eine leere Liste zurück."""

    try:
        daten = client().complete(purpose="research_search", prompt=prompt,
                                  schema=schema, system=prompts.SYSTEM,
                                  web_search=True).data
    except ClaudeError as exc:
        log.info("Websuche nicht möglich: %s", exc)
        return []

    heraus = []
    for t in daten.get("treffer") or []:
        url = (t.get("url") or "").strip()
        titel = (t.get("title") or "").strip()
        if not url or not titel:
            continue
        ok, _ = _zulassen(url, titel, t.get("kanal"))
        if ok:
            heraus.append({"title": titel, "url": url, "kanal": t.get("kanal")})
    return heraus[:12]


# --------------------------------------------------------------------------
# Freigabe
# --------------------------------------------------------------------------

def vorschlaege(topic_id: int | None = None) -> list[dict]:
    sql = """SELECT r.*, t.label AS thema_label FROM research_hit r
               JOIN topic t ON t.id = r.topic_id
              WHERE r.state = ?"""
    params: list = [VORSCHLAG]
    if topic_id:
        sql += " AND r.topic_id = ?"
        params.append(topic_id)
    sql += " ORDER BY r.id DESC LIMIT 40"
    return [dict(r) for r in db.q(sql, *params)]


def freigegebene(topic_id: int) -> list[dict]:
    return [dict(r) for r in db.q(
        """SELECT * FROM research_hit WHERE topic_id=? AND state=?
            ORDER BY id LIMIT 6""", topic_id, FREIGEGEBEN)]


def entscheiden(entscheidungen: dict[int, str]) -> dict:
    frei = weg = 0
    neu_freigegeben: list[int] = []
    with db.tx() as c:
        for hit_id, aktion in entscheidungen.items():
            if aktion not in (FREIGEGEBEN, ABGELEHNT):
                continue
            cur = c.execute(
                "UPDATE research_hit SET state=? WHERE id=? AND state=?",
                (aktion, int(hit_id), VORSCHLAG))
            if cur.rowcount:
                if aktion == FREIGEGEBEN:
                    frei += 1
                    neu_freigegeben.append(int(hit_id))
                else:
                    weg += 1
    # Erst NACH der Transaktion: jobs.enqueue() oeffnet selbst eine, und
    # Verschachtelung ist nicht erlaubt (siehe db.tx()). Den Inhalt holen wir
    # ohnehin erst jetzt, nie vor der Freigabe.
    for hit_id in neu_freigegeben:
        jobs.enqueue("research_fetch", {"hit_id": hit_id},
                     dedup_key=f"research_fetch:{hit_id}")
    return {"freigegeben": frei, "abgelehnt": weg}


def anzahl_vorschlaege() -> int:
    row = db.q1("SELECT COUNT(*) AS n FROM research_hit WHERE state=?", VORSCHLAG)
    return row["n"] if row else 0


# --------------------------------------------------------------------------
# Inhalt einer freigegebenen Quelle holen — nur, wenn eigenes Material fehlt
# --------------------------------------------------------------------------

FETCH_SCHEMA = {
    "type": "object",
    "properties": {
        "erreichbar": {"type": "boolean"},
        "inhalt": {
            "type": "string",
            "description": "Der fachliche Lerninhalt der Seite in eigenen "
                           "Worten auf Deutsch — Erklärungen, Merkregeln, "
                           "Rechenwege, Beispiele. Keine Navigation, keine "
                           "Werbung, keine Kommentare. Leerer Text, wenn "
                           "nicht erreichbar oder ohne brauchbaren Inhalt.",
        },
    },
    "required": ["erreichbar", "inhalt"],
}

MAX_INHALT_LAENGE = 6000


@jobs.handler("research_fetch")
def job_research_fetch(payload: dict) -> None:
    """Holt den Lerninhalt einer bereits freigegebenen Quelle.

    Läuft nur für Quellen, die ein Mensch schon abgehakt hat (`entscheiden()`
    stößt diesen Job an) — nie für einen bloßen Vorschlag. Der geholte Inhalt
    macht die Quelle zur echten Faktengrundlage, wenn für das Thema kein
    eigenes Schulmaterial vorliegt — siehe `material_fuer()`.
    """
    hit_id = int(payload["hit_id"])
    hit = db.q1("SELECT * FROM research_hit WHERE id = ?", hit_id)
    if hit is None or hit["state"] != FREIGEGEBEN or hit["inhalt"]:
        return

    cfg = config.load()
    prompt = f"""Rufe die folgende Seite auf und gib ihren fachlichen
Lerninhalt wieder — Klassenstufe {cfg.learner_grade} in Deutschland, Fach
{cfg.subject}:

{hit['url']}

Gib den Inhalt in eigenen Worten auf Deutsch wieder: Erklärungen,
Merkregeln, Rechenwege, Beispiele. Keine Navigation, keine Werbung, keine
Kommentare, keine Beschreibung der Seite selbst — nur den fachlichen Inhalt.
Ist die Seite nicht erreichbar oder ohne brauchbaren Lerninhalt, setze
erreichbar auf false und inhalt auf einen leeren Text. Erfinde nichts."""

    try:
        ergebnis = client().complete(
            purpose="research_fetch", prompt=prompt, schema=FETCH_SCHEMA,
            system=prompts.SYSTEM, web_fetch=True).data
    except ClaudeError as exc:
        log.info("Abrufen von %s nicht möglich: %s", hit["url"], exc)
        return

    inhalt = (ergebnis.get("inhalt") or "").strip()[:MAX_INHALT_LAENGE]
    if not ergebnis.get("erreichbar") or not inhalt:
        log.info("Quelle %s ohne brauchbaren Inhalt", hit["url"])
        return

    with db.tx() as c:
        c.execute(
            "UPDATE research_hit SET inhalt=?, inhalt_geholt_am=? WHERE id=?",
            (inhalt, db.now(), hit_id))


def material_fuer(topic_id: int) -> list[dict]:
    """Freigegebene, inhaltlich bereits geholte Quellen — aufbereitet wie
    Wissensbasis-Abschnitte, für den Fall, dass kein eigenes Material
    vorliegt (siehe `teaching.job_lesson_build()`). Negative IDs, damit sie
    nicht mit echten kb_chunk-IDs kollidieren, wenn beide zusammen die
    Quellenliste einer Erklärung füllen.
    """
    rows = db.q(
        """SELECT * FROM research_hit WHERE topic_id=? AND state=?
            AND inhalt IS NOT NULL ORDER BY id LIMIT 6""", topic_id, FREIGEGEBEN)
    return [{"id": -r["id"], "art": "erklaerung", "titel": r["titel"],
            "text": r["inhalt"], "herkunft": "web", "quelle_url": r["url"]}
           for r in rows]
