"""Wie viel Zeit die Klassenarbeit braucht — und wofür.

Drei Schritte, in dieser Reihenfolge:

1. **Vorwissen prüfen.** Zu jedem Prüfungsthema sucht Karo, was das Kind
   dazu schon gezeigt hat. Ein Prüfungsthema ist eine eigene Zeile in der
   Datenbank und startet ohne Belege — die Erfahrung steckt in den eigenen
   Themen des Kindes, die oft leicht anders heissen ("Klammern auflösen" vs.
   "Klammern auflösen und ausmultiplizieren"). Deshalb derselbe Abgleich wie
   in `topics.passende`: Teilstring in beide Richtungen.

   Wichtig: Das zaehlt nur fuer die **Schaetzung**. Als Beleg fuer Koennen
   gilt es nicht — dafuer bleibt es bei der Regel aus
   `adaptiv/store.fortschritt_scope`: derselbe Lehrplan ist noch nicht
   derselbe Nachweis. Ein Thema, das aus einem eigenen Thema als "gruen"
   geschaetzt wird, steht in der Prüfung trotzdem auf "neu", bis das Kind es
   dort gezeigt hat.

2. **Minuten schaetzen.** Je Thema eine Spanne konzentrierter Minuten, die
   sich nach dem Vorwissen richtet. Auf jede Spanne kommt still ein
   Zuschlag (`ZUSCHLAG`): Lernzeit wird von allen unterschaetzt, von Kindern
   besonders. Die Zahl, die das Kind sieht, ist die aufgeschlagene — vom
   Zuschlag selbst steht nirgends etwas, sonst rechnet man ihn wieder heraus.

3. **Themen auf die Tage verteilen.** Das Kind waehlt Tage und Minuten; Karo
   fuellt die gewaehlten Tage der Reihe nach. Die Reihenfolge der Themen ist
   die angekuendigte (`exam_topic.position`) — sie traegt die
   Voraussetzungen, denn "Probe durchfuehren" steht nicht ohne Grund hinter
   "Gleichungen loesen". Ein Thema darf ueber mehrere Tage laufen.
"""
from __future__ import annotations

import datetime as dt

from .. import db, topics

#: Konzentrierte Minuten je Thema, nach Vorwissen — vor dem Zuschlag.
#: "weiss" heisst: noch nichts gezeigt. Das braucht weniger als ein Thema,
#: bei dem schon Fehler belegt sind, aber mehr als eines, das schon sitzt.
MINUTEN = {
    "rot":   (20, 28),
    "weiss": (16, 22),
    "gelb":  (10, 15),
    "gruen": (4, 6),
}
#: Stiller Aufschlag auf jede Schaetzung. Nirgends in der Oberflaeche.
ZUSCHLAG = 1.2
#: Anzeige in Fuenferschritten: "mindestens 63 Minuten" liest sich wie eine
#: Messung, "mindestens 65" wie das, was es ist — eine Schaetzung.
STUFE = 5


def _runden(minuten: float) -> int:
    return max(STUFE, int(round(minuten / STUFE)) * STUFE)


def _vorwissen(label: str, eigene: list[dict]) -> tuple[str, str]:
    """Flagge und Herkunft — oder ("weiss", "") ohne Beleg.

    Der Abgleich laeuft ueber Namensaehnlichkeit (wie `topics.passende`).
    Das ist ein Indiz, kein Beweis: "Grundwert" traefe auch "Grundwertsatz".
    Deshalb wandert die Quelle mit nach oben, damit die Oberflaeche sagen
    kann, worauf die Einschaetzung beruht — und ein Fehltreffer auffaellt.
    """
    gesucht = label.lower()
    treffer = [t for t in eigene
               if t["label"].lower() in gesucht or gesucht in t["label"].lower()]
    if not treffer:
        return "weiss", ""
    # Das unsicherste passende Thema entscheidet: wer bei einer Schreibweise
    # Fehler macht, ist beim Prüfungsthema nicht fertig.
    reihenfolge = ("rot", "weiss", "gelb", "gruen")
    bester = min(treffer, key=lambda t: reihenfolge.index(t["flag"]))
    return bester["flag"], bester["label"]


def themen(exam_id: int) -> list[dict]:
    """Prüfungsthemen mit Vorwissen und geschaetzter Zeit, in Lernreihenfolge."""
    from . import exam_placement
    from .learning_hub import exam_topics

    eigene = [t for t in topics.liste(topics.AKTIV)
              if t.get("learning_visible", 1) and not t.get("deleted_at")]
    # Die Einstufung schlaegt alles andere: sie ist der einzige Beleg, der zu
    # genau diesem Thema und genau diesem Kind erhoben wurde. Danach kommt,
    # was in dieser Prüfung schon gezeigt wurde, und erst zuletzt der
    # Namensabgleich mit eigenen Themen.
    eingestuft = exam_placement.ergebnis(exam_id)
    zeilen = []
    for t in exam_topics(exam_id):
        if t["id"] in eingestuft:
            flagge, quelle = eingestuft[t["id"]], "in der Einstufung gezeigt"
        elif t["learning_status"] == "sicher":
            flagge, quelle = "gruen", "in dieser Prüfung gezeigt"
        else:
            flagge, herkunft = _vorwissen(t["label"], eigene)
            quelle = f"aus deinem Thema „{herkunft}“" if herkunft else ""
        unten, oben = MINUTEN[flagge]
        zeilen.append({
            "topic_id": t["id"],
            "label": t["label"],
            "learning_status": t["learning_status"],
            "vorwissen": flagge,
            "quelle": quelle,
            # Gerundet wird nur, was angezeigt wird. Die Summe rechnet mit den
            # ungerundeten Werten, sonst summieren sich die Rundungen auf.
            "min": _runden(unten * ZUSCHLAG),
            "max": _runden(oben * ZUSCHLAG),
            "min_roh": unten * ZUSCHLAG,
            "max_roh": oben * ZUSCHLAG,
            "sicher": t["learning_status"] == "sicher",
        })
    return zeilen


def inhalte_anfordern(exam_id: int) -> int:
    """Fehlende Lerninhalte für die Prüfungsthemen einreihen.

    Ohne geprüfte Aufgaben kann Karo weder einstufen noch üben — es hat
    schlicht nichts zu fragen. Fuer jedes Thema ohne Lektion entsteht hier
    ein Auftrag; doppelte verhindert `erzeugung.anfordern` selbst. Das ist
    der Vorgang, der bisher beim Eintragen der Themen fehlte.
    """
    from .. import config
    from ..adaptiv import erzeugung, lektionen
    from .learning_hub import exam_topics

    from .. import db

    if not getattr(config.load_safe(), "adaptive_learning_enabled", False):
        return 0
    # Das Datum der Arbeit geht mit: der Lehrplan-Dienst arbeitet die Themen
    # danach ab. Ohne das wartet die Arbeit am Freitag hinter der in drei
    # Wochen, und das faellt erst am Freitag auf.
    arbeit = db.q1("SELECT exam_date FROM exam WHERE id=?", exam_id)
    termin = arbeit["exam_date"] if arbeit else None
    angefordert = 0
    for t in exam_topics(exam_id):
        if lektionen.fuer_thema(t["label"], t["subject"], t.get("grade")):
            continue
        if erzeugung.anfordern(t["label"], t["subject"], t.get("grade"), gebraucht_am=termin):
            angefordert += 1
    return angefordert


def thema_stand(thema: str, fach: str, klasse: int | None) -> dict:
    """Ein Thema, ein Stand — mit Schaetzung, wenn der Dienst eine nennt.

    „Wird vorbereitet" ohne Zahl ist fuer Eltern nicht von „haengt" zu
    unterscheiden. Gibt der Dienst einen Platz in der Schlange und eine
    Dauer an, steht das hier; sonst wird nichts erfunden.
    """
    import json

    from .. import db
    from ..adaptiv import erzeugung, lektionen

    if lektionen.fuer_thema(thema, fach, klasse):
        return {"thema": thema, "stand": "bereit"}
    schluessel = erzeugung.auftrag_schluessel(thema, fach, klasse)
    auftrag = db.q1("""SELECT state, payload, last_error FROM job
                       WHERE type='lektion_erzeugen' AND dedup_key=?
                       ORDER BY id DESC LIMIT 1""", schluessel) if schluessel else None
    if not auftrag:
        # Ein gescheiterter Auftrag gibt seinen Schluessel wieder frei;
        # erkennbar ist er nur noch an der Nutzlast.
        frueher = db.q1("""SELECT last_error FROM job WHERE type='lektion_erzeugen'
                           AND state='fehler' AND payload LIKE ? ORDER BY id DESC LIMIT 1""",
                        f'%"{thema}"%')
        if frueher:
            return {"thema": thema, "stand": "gescheitert", "grund": frueher["last_error"]}
        return {"thema": thema, "stand": "fehlt"}
    if auftrag["state"] == "fehler":
        return {"thema": thema, "stand": "gescheitert", "grund": auftrag["last_error"]}
    try:
        nutzlast = json.loads(auftrag["payload"] or "{}")
    except (ValueError, TypeError):
        nutzlast = {}
    if nutzlast.get("budget_wartet"):
        # Nicht der Dienst haengt, sondern Karo haelt zurueck: mehr als
        # KARO_FAMILY_DAILY_TOPICS neue Themen am Tag bestellt es nicht.
        # Das als „wird erstellt" anzuzeigen waere eine Luege — es passiert
        # heute nichts mehr.
        return {"thema": thema, "stand": "morgen"}
    stand = {"thema": thema, "stand": "laeuft"}
    for feld, name in (("curriculum_position", "platz"), ("curriculum_waiting", "warten"),
                       ("curriculum_seconds", "sekunden")):
        if type(nutzlast.get(feld)) is int:
            stand[name] = nutzlast[feld]
    # Der Lehrplan-Dienst hat sein Tageskontingent aufgebraucht und nennt eine
    # Uhrzeit. Die gehoert hin: sonst sieht es aus wie „gleich fertig".
    if nutzlast.get("curriculum_pausiert_bis"):
        stand["ab"] = str(nutzlast["curriculum_pausiert_bis"])
    return stand


def inhalte_stand(exam_id: int) -> dict:
    """Wie viele Prüfungsthemen geprüfte Aufgaben haben — und was sonst ist.

    "fehlt" und "gescheitert" auseinanderzuhalten ist der ganze Punkt: bei
    "fehlt" hilft Warten, bei "gescheitert" nie. Eine Oberflaeche, die beides
    "wird gerade erstellt" nennt, schickt eine Familie ins Leere.
    """
    from .. import db
    from ..adaptiv import erzeugung, lektionen
    from .learning_hub import exam_topics

    zeilen = [thema_stand(t["label"], t["subject"], t.get("grade")) for t in exam_topics(exam_id)]
    zaehlen = {"bereit": 0, "laeuft": 0, "fehlt": 0, "gescheitert": 0, "morgen": 0}
    for z in zeilen:
        zaehlen[z["stand"]] += 1
    # Die laengste Schaetzung zaehlt: fertig ist die Familie erst, wenn das
    # letzte Thema da ist.
    dauer = [z["sekunden"] for z in zeilen if type(z.get("sekunden")) is int]
    return {**zaehlen, "offen": (zaehlen["laeuft"] + zaehlen["fehlt"]
                                + zaehlen["gescheitert"] + zaehlen["morgen"]),
            "gesamt": len(zeilen), "themen": zeilen,
            "sekunden": max(dauer) if dauer else None}


def bedarf(exam_id: int) -> dict:
    """Gesamtbedarf der Klassenarbeit, so wie das Kind ihn zu sehen bekommt."""
    zeilen = themen(exam_id)
    unten = _runden(sum(z["min_roh"] for z in zeilen)) if zeilen else 0
    oben = _runden(sum(z["max_roh"] for z in zeilen)) if zeilen else 0
    # Wie viele Themen ueberhaupt auf einem Beleg stehen. Ohne diese Zahl
    # klingt jede Schaetzung nach Wissen; "weiss" heisst aber: noch nie
    # gesehen, und Karo rechnet dann nur vorsichtshalber mit dem vollen
    # Aufwand. Die Oberflaeche muss diesen Unterschied sagen duerfen.
    belegt = sum(1 for z in zeilen if z["vorwissen"] != "weiss")
    eingestuft = sum(1 for z in zeilen if z["quelle"] == "in der Einstufung gezeigt")
    return {"min": unten, "max": oben, "themen": zeilen,
            "offen": sum(1 for z in zeilen if not z["sicher"]),
            "belegt": belegt, "ohne_beleg": len(zeilen) - belegt,
            "eingestuft": eingestuft}


def verteilung(exam_id: int, tage: list[dt.date]) -> dict[str, list[dict]]:
    """Themen auf die gewaehlten Lerntage, nach Minuten und Reihenfolge.

    `tage` sind die Lerntage mit ihren Minuten, schon ohne Generalprobe und
    Prüfungstag. Ein Thema darf ueber mehrere Tage laufen; ist die Zeit vor
    den Themen alle, bleibt der Rest unverteilt — der Kalender sagt das dann.
    """
    offen = [dict(z) for z in themen(exam_id) if not z["sicher"]]
    plan: dict[str, list[dict]] = {}
    rest = list(offen)
    uebrig = rest.pop(0) if rest else None
    uebrig_minuten = uebrig["min"] if uebrig else 0
    for tag, minuten in tage:
        frei = int(minuten)
        plan[str(tag)] = []
        while uebrig and frei > 0:
            anteil = min(frei, uebrig_minuten)
            plan[str(tag)].append({"topic_id": uebrig["topic_id"],
                                   "label": uebrig["label"], "minuten": anteil})
            frei -= anteil
            uebrig_minuten -= anteil
            if uebrig_minuten <= 0:
                uebrig = rest.pop(0) if rest else None
                uebrig_minuten = uebrig["min"] if uebrig else 0
    return plan


def gewaehlte_minuten(exam_id: int) -> int:
    """Summe der Minuten, die das Kind im Kalender eingetragen hat."""
    row = db.q1("""SELECT COALESCE(SUM(minutes), 0) AS n FROM exam_schedule_day
                    WHERE exam_id=? AND minutes > 0""", exam_id)
    return int(row["n"] if row else 0)


def lage(exam_id: int) -> dict:
    """Bedarf, gewaehlte Zeit und ob beides zusammenpasst.

    Reicht die gewaehlte Zeit nicht, sagt Karo es — entscheiden darf das Kind
    trotzdem selbst. Ein Plan, den ein Kind nicht gewaehlt hat, wird nicht
    eingehalten.
    """
    stand = bedarf(exam_id)
    gewaehlt = gewaehlte_minuten(exam_id)
    return {**stand, "gewaehlt": gewaehlt,
            "fehlend": max(0, stand["min"] - gewaehlt),
            "reicht": gewaehlt >= stand["min"]}


def vorbereitung_uebersicht() -> list[dict]:
    """Was Karo fuer die kommenden Arbeiten gerade vorbereitet — fuer Eltern.

    Eltern sahen bisher nur „wird vorbereitet", fuer alle Themen zusammen und
    ohne Zahl. Ob etwas laeuft oder haengt, war daran nicht zu erkennen; ein
    gescheitertes Thema sah genauso aus wie eins, das gleich fertig ist.
    Hier steht es pro Thema, mit dem, was der Lehrplan-Dienst an Schaetzung
    hergibt — und nichts, was er nicht hergibt.
    """
    from .. import db, faecher

    arbeiten = db.q(f"""SELECT id, subject, exam_date FROM exam
                        WHERE exam_date >= ? AND deleted_at IS NULL AND purged_at IS NULL
                          AND subject IN {faecher.SQL_FAECHER}
                        ORDER BY exam_date""", db.today())
    uebersicht = []
    for a in arbeiten:
        stand = inhalte_stand(a["id"])
        if not stand["gesamt"]:
            continue
        uebersicht.append({"exam_id": a["id"], "fach": faecher.name(a["subject"]),
                           "datum": a["exam_date"], **stand})
    return uebersicht


def budget_stand() -> dict:
    """Wie viele neue Themen heute noch gehen — fuer die Elternansicht."""
    from . import topic_budget
    return {"grenze": topic_budget.grenze(), "verbraucht": topic_budget.verbraucht(),
            "rest": topic_budget.rest()}
