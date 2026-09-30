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

    if not getattr(config.load_safe(), "adaptive_learning_enabled", False):
        return 0
    angefordert = 0
    for t in exam_topics(exam_id):
        if lektionen.fuer_thema(t["label"], t["subject"], t.get("grade")):
            continue
        if erzeugung.anfordern(t["label"], t["subject"], t.get("grade")):
            angefordert += 1
    return angefordert


def inhalte_stand(exam_id: int) -> dict:
    """Wie viele Prüfungsthemen geprüfte Aufgaben haben — und was sonst ist.

    "fehlt" und "gescheitert" auseinanderzuhalten ist der ganze Punkt: bei
    "fehlt" hilft Warten, bei "gescheitert" nie. Eine Oberflaeche, die beides
    "wird gerade erstellt" nennt, schickt eine Familie ins Leere.
    """
    from .. import db
    from ..adaptiv import erzeugung, lektionen
    from .learning_hub import exam_topics

    bereit, laeuft, fehlt, gescheitert = 0, 0, 0, 0
    for t in exam_topics(exam_id):
        if lektionen.fuer_thema(t["label"], t["subject"], t.get("grade")):
            bereit += 1
        elif erzeugung.laeuft(t["label"], t["subject"], t.get("grade")):
            laeuft += 1
        else:
            # Ein gescheiterter Auftrag gibt seinen Schluessel wieder frei;
            # erkennbar ist er nur noch an der Nutzlast.
            schluessel = erzeugung.auftrag_schluessel(
                t["label"], t["subject"], t.get("grade"))
            frueher = db.q1(
                """SELECT last_error FROM job WHERE type='lektion_erzeugen'
                    AND state='fehler' AND payload LIKE ?
                    ORDER BY id DESC LIMIT 1""", f'%"{t["label"]}"%')
            if frueher and schluessel:
                gescheitert += 1
            else:
                fehlt += 1
    return {"bereit": bereit, "laeuft": laeuft, "fehlt": fehlt,
            "gescheitert": gescheitert, "offen": laeuft + fehlt + gescheitert,
            "gesamt": bereit + laeuft + fehlt + gescheitert}


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
