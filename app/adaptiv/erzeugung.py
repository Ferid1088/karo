"""Eine vorgeschlagene Lektion prüfen, schreiben und freigeben.

Schritt 2 der Erzeugung. Was hier hereinkommt, hat ein Modell vorgeschlagen
(§5 Modell A); was hier hinausgeht, ist ein Katalogeintrag wie jeder andere
und wird beim nächsten Kind ohne Modellaufruf ausgeliefert (§11, A3).

**Die Freigabe kommt zuletzt, und das trägt die Atomarität.** Die
Schreibvorgänge laufen über mehrere Transaktionen; bräche einer davon ab,
stünde eine halbe Lektion in der Datenbank. Weil aber alles ungeprüft
geschrieben und erst am Ende freigegeben wird, ist eine halbe Lektion für
ein Kind unsichtbar — die Sperre aus §11 erledigt das, wofür es sonst eine
umspannende Transaktion bräuchte.

**Freigegeben wird nach bestandener Prüfung, ohne Klick.** Ungeprüft heisst
weiterhin unsichtbar; die Sperre wartet nur nicht mehr auf einen Menschen.
Roher Modelltext erreicht damit nie ein Kind — aber auch kein Elternteil
muss zwischen Frage und Antwort treten.
"""

from __future__ import annotations

from .. import config
from . import inhalt_store, schemas, store
from .normalisierung import normalisiere

#: Herkunft dieser Einträge (§6: „creation source").
QUELLE = "erzeugt"

#: Eine ganze Lernreihe ist um ein Vielfaches länger als eine Fragerunde:
#: zwei bis vier Fehlvorstellungen mit je fünf Aufgaben, dazu Hilfe für
#: sechs Phasen und die FAQ. Mit der üblichen Vorgabe bricht die Antwort
#: mittendrin ab, und die Prüfung verwirft sie als unvollständig.
MAX_TOKENS = config.ops().llm_lektion_max_tokens

#: Der KI-Anbieter arbeitet asynchron — das Zeitlimit für eine Lektion
#: steht in ops.ai_max_run_seconds, nicht an einem einzelnen HTTP-Aufruf.

#: Welche Rolle als Auswahl gestellt wird statt als Rechnung.
_ALS_AUSWAHL = {"vorhersage", "transfer"}


def _aufgabe_schreiben(fehlertyp_id: int, rolle: str, aufgabe: dict,
                      quelle: str = QUELLE) -> None:
    inhalt_store.aufgabe_sichern(
        fehlertyp_id, rolle, aufgabe["frage"], aufgabe["loesung"],
        tipps=aufgabe.get("tipps"), schritte=aufgabe.get("schritte"),
        typischer_fehler=aufgabe.get("typischer_fehler"),
        antwort_art=(aufgabe.get("antwort_art")
                     or (inhalt_store.AUSWAHL if rolle in _ALS_AUSWAHL
                         else inhalt_store.BRUCH)),
        optionen=aufgabe.get("optionen"),
        aufloesung=aufgabe.get("aufloesung"),
        rubrik=aufgabe.get("rubrik"),
        # Sagt das Curriculum, wie lange die Aufgabe dauert, gilt das. Wer
        # sie geschrieben hat, weiss es besser als eine Schaetzung nach
        # Antwortart und Klasse (Schritt 4a).
        erwartete_sekunden=aufgabe.get("erwartete_sekunden"),
        quelle=quelle, geprueft=False)


def speichern(rohdaten: dict, fach: str, *, quelle: str = QUELLE) -> int:
    """Prüft den Vorschlag und schreibt ihn in den Katalog. Gibt die
    Konzept-Id zurück.

    Wirft `schemas.InhaltUngueltig`, bevor irgendetwas geschrieben wurde —
    ein abgewiesener Vorschlag hinterlässt keinen halben Eintrag.
    """
    from ..faecher import pflicht
    fach = pflicht(fach)
    lektion = schemas.pruefe_lektion(rohdaten)
    konzept = lektion["konzept"]
    existing = store.konzept_nach_key(fach, konzept['thema_key'], konzept['konzept_key'])
    concept_key = konzept['konzept_key']
    if existing and (existing['quelle'] != quelle or
            (existing['klasse_von'], existing['klasse_bis']) !=
            (konzept['klasse_von'], konzept['klasse_bis'])):
        # A generated grade-specific variant must not overwrite curated
        # content or leave its old grade limits in place and become unfindable.
        concept_key += f"-erzeugt-{konzept['klasse_von']}-{konzept['klasse_bis']}"

    konzept_id = store.konzept_sichern(
        fach, konzept["thema_key"], concept_key, konzept["label"],
        konzept["klasse_von"], konzept["klasse_bis"],
        stichworte=konzept["stichworte"], quelle=quelle, geprueft=False)

    fehlertyp_ids = []
    for fehler in lektion["fehlertypen"]:
        fehlertyp_id = store.fehlertyp_sichern(
            konzept_id, fehler["key"], fehler["label"],
            fehler["beschreibung"], quelle=quelle, geprueft=False)
        fehlertyp_ids.append(fehlertyp_id)

        for antwort in fehler["antworten"]:
            store.alias_sichern(fehlertyp_id, normalisiere(antwort), quelle)

        if not store.beste_erklaerung(fehlertyp_id, konzept["klasse_bis"]):
            store.erklaerung_anlegen(
                fehlertyp_id, konzept["klasse_bis"], fehler["erklaerung"],
                visualisierung=fehler["visualisierung"],
                visualisierung_alternativ=fehler.get(
                    "visualisierung_alternativ"),
                quelle=quelle, geprueft=False)

        for rolle, aufgabe in fehler["aufgaben"].items():
            _aufgabe_schreiben(fehlertyp_id, rolle, aufgabe, quelle)

    for phase, hilfe in lektion["hilfe"].items():
        inhalt_store.hilfe_sichern(
            konzept_id, inhalt_store.HILFE_PHASE, phase, hilfe["text"],
            visualisierung=hilfe.get("visualisierung"), geprueft=False)
    for i, eintrag in enumerate(lektion["faq"]):
        inhalt_store.hilfe_sichern(
            konzept_id, inhalt_store.HILFE_FAQ, eintrag["frage"],
            eintrag["antwort"], sortierung=i, geprueft=False)

    erstkontakt = lektion.get("erstkontakt")
    if erstkontakt and not store.erstkontakt(konzept_id):
        store.erstkontakt_anlegen(
            konzept_id, erstkontakt["anker"], erstkontakt["erste_aufgabe"],
            erstkontakt["benennung"], quelle=quelle, geprueft=False)

    _freigeben(konzept_id, fehlertyp_ids)
    return konzept_id


def _freigeben(konzept_id: int, fehlertyp_ids: list) -> None:
    """Erst jetzt wird die Lektion sichtbar — und zwar in einem Zug."""
    for fehlertyp_id in fehlertyp_ids:
        store.fehlertyp_freigeben(fehlertyp_id)
        for erklaerung in store.erklaerungen(fehlertyp_id):
            store.erklaerung_freigeben(erklaerung["id"])
        inhalt_store.aufgaben_freigeben(fehlertyp_id)
    inhalt_store.hilfe_freigeben(konzept_id)
    store.erstkontakt_freigeben(konzept_id)
    store.konzept_freigeben(konzept_id)


# --------------------------------------------------------------------------
# Auf Anfrage erzeugen (§5 Modell A, §6 Tier 3, §15 Latenz)
# --------------------------------------------------------------------------

def auftrag_schluessel(thema: str, fach: str, klasse: int | None = None) -> str:
    """Ein Thema, ein Auftrag. Zweimal klicken erzeugt nicht zweimal.

    Der Schluessel loest die Klasse immer zur Profilklasse auf, wenn der
    Aufrufer keine nennt — schreibende (`anfordern`) und lesende
    (`thema_stand`) Seite muessen denselben Schluessel berechnen, sonst
    sieht eine Familie den laufenden Auftrag als „fehlt".
    """
    if not klasse:
        from .. import config
        klasse = config.load_safe().learner_grade
    return f"lektion:{normalisiere(thema)}" + (f':{normalisiere(fach or "")}:{klasse}' if fach or klasse else '')


def anfordern(thema: str, fach: str, klasse: int | None = None,
              gebraucht_am: str | None = None) -> int | None:
    """Reiht die Erzeugung ein. Gibt None zurück, wenn schon eine läuft.

    Nur mit Fach: der Curriculum-Agent und das Modell bekommen ausschließlich
    das aktive Fach, nie einen Vorgabewert aus den Einstellungen.

    `gebraucht_am` ist das Datum der Klassenarbeit. Der Lehrplan-Dienst
    sortiert seine Schlange danach: sonst wartet das Thema fuer die Arbeit am
    Freitag hinter dem fuer die Arbeit in drei Wochen. Das Datum steuert nur
    die Reihenfolge, nie den Inhalt.
    """
    import time
    from .. import config, jobs
    from ..faecher import pflicht
    from . import curriculum_dienst
    cfg = config.load()
    fach = pflicht(fach)
    # Der Klassenarbeits-Weg ruft ohne Klasse — das Konzept bestimmt sie,
    # nicht das Profil. Der Dedup-Schluessel braucht sie trotzdem aufgeloest:
    # sonst sucht `/lernen/adaptiv/status` unter der Profilklasse und sieht
    # den laufenden Auftrag nicht.
    klasse = klasse or cfg.learner_grade
    payload = {"thema": thema, 'fach': fach, 'klasse': klasse}
    if gebraucht_am:
        payload["gebraucht_am"] = gebraucht_am
    if curriculum_dienst.configured(cfg):
        payload.update(curriculum_service=curriculum_dienst.settings(cfg)[0],
                       curriculum_started=time.time())
    return jobs.enqueue("lektion_erzeugen", payload,
                        dedup_key=auftrag_schluessel(thema, fach, klasse))


def laeuft(thema: str, fach: str | None, klasse: int | None = None) -> bool:
    from .. import db
    return bool(db.q1(
        "SELECT 1 FROM job WHERE dedup_key=? AND state IN ('wartend','laeuft')",
        auftrag_schluessel(thema, fach, klasse)))


def _handler_anmelden():
    """Erst beim Import von `jobs` registrieren — sonst zieht diese Datei
    die halbe Anwendung in die adaptive Schicht, nur um geladen zu werden."""
    from .. import config, jobs, pii, prompts
    from ..ai.client import AIClient

    @jobs.handler("lektion_erzeugen")
    def job_lektion_erzeugen(payload: dict) -> dict:
        """Der erste echte Modellaufruf des adaptiven Lernens.

        Im Hintergrund, nicht im Klick des Kindes: eine Lektion zu schreiben
        dauert, und §15 verlangt, dass niemand vor einem Spinner sitzt.

        Schlägt die Prüfung fehl, wirft `speichern()` — der Auftrag landet
        auf „fehler", und es bleibt nichts Halbes zurück. Lieber keine
        Lektion als eine falsche.
        """
        thema = str(payload.get("thema") or "").strip()
        if not thema:
            return {"uebersprungen": "kein Thema"}
        cfg = config.load()
        from ..faecher import NAMEN, schluessel
        fach = schluessel(payload.get('fach'))
        if fach is None:
            raise jobs.PermanentFailure("Ohne Fach wird keine Lernreihe erzeugt.")
        klasse = payload.get('klasse') or cfg.learner_grade
        from . import lektionen
        existing = lektionen.fuer_thema(thema, fach)
        if existing:
            return {'konzept_id': existing['konzept_id'], 'thema': thema}
        from . import curriculum_dienst
        if curriculum_dienst.configured(cfg) or "curriculum_service" in payload:
            return curriculum_dienst.prepare(cfg, payload, thema, fach, klasse)
        # §5: der Anbieter schreibt die Didaktik — die Qualitätssicherung
        # liegt in `schemas.pruefe_lektion` und `klassenpruefung.pruefen`
        # hinterher, nicht in einer Modellwahl im Code.
        ergebnis = AIClient.from_config(cfg).complete(
            purpose="lektion_erzeugen",
            max_tokens=MAX_TOKENS,
            prompt=prompts.lektion_prompt(
                None, NAMEN[fach],
                pii.scrub(thema, cfg.learner_name)),
            schema=prompts.LEKTION_SCHEMA,
            system=prompts.SYSTEM,
        )
        checked = schemas.pruefe_lektion(ergebnis.data)
        # A second, independent classification sees the concept/tasks but never
        # the child's profile class or the author's proposed grade labels.
        from . import klassenpruefung
        klassenpruefung.pruefen(checked, fach, cfg)
        from .normalisierung import normalisiere_thema
        if not lektionen._trifft(normalisiere_thema(thema), checked['konzept']):
            raise schemas.InhaltUngueltig('Die Lernreihe passt nicht zum angefragten Thema.')
        konzept_id = speichern(checked, fach=fach)
        return {"konzept_id": konzept_id, "thema": thema}

    return job_lektion_erzeugen


job_lektion_erzeugen = _handler_anmelden()
