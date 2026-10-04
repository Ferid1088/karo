"""Vor der Eskalation: liegt es am Konzept — oder an einer Voraussetzung?

Karo hat bei einem Kind, das dreimal hängenblieb, einen Menschen geholt. Das
ist richtig, wenn das Konzept selbst zu schwer ist. Es ist falsch, wenn in
Wahrheit eine Voraussetzung fehlt: wer Brüche nicht erweitern kann, scheitert
beim Addieren an etwas, das zwei Schritte davor liegt. Eine Erklärung zum
Addieren hilft dort nicht, und ein Mensch zu holen ist zu viel für ein
Problem, das Karo selbst lösen kann.

Also wird vorher kurz nachgesehen. Die Diagnose ist dieselbe wie sonst: zwei
geprüfte Aufgaben zum Voraussetzungskonzept, nicht mehr. Fällt sie aus, lernt
das Kind erst die Voraussetzung und kommt danach zurück. Sitzt sie, war es
nicht die Voraussetzung — dann eskaliert Karo wie bisher.

Was hier NICHT passiert: raten. Steht keine Voraussetzung in der Lieferung,
wird sie als Inhaltsanfrage bestellt (siehe `inhalt_anfordern`) und die
Sitzung geht in die Begleitung statt ins Leere — das Thema bleibt offen.

Der Graph ist rekursiv: der Umweg ist eine ganz normale Sitzung. Scheitert
er, wird auch er nach fehlenden Voraussetzungen gefragt — so entsteht die
Kette Ziel → Voraussetzung → deren Voraussetzung bis zu einem tragfähigen
Stand, ohne dass der Code die Tiefe kennt oder begrenzt.
"""
from __future__ import annotations

from .. import config
from . import inhalt_store, store

#: So viele geprüfte Aufgaben entscheiden, ob eine Voraussetzung sitzt.
#: Dieselbe Zahl wie bei der Ersteinschätzung: eine Aufgabe belegt nichts.
AUFGABEN = config.ops().voraussetzung_aufgaben


def detour_vorfahren(sitzung: dict) -> set[int]:
    """Konzept-IDs der wartenden Sitzungen oberhalb dieses Umwegs.

    Jeder Umweg traegt in `daten["voraussetzung_detour"]` die Sitzung, die
    auf ihn wartet. Der Kette nach oben zu folgen zeigt, welche Konzepte
    gerade auf eine Voraussetzung warten — eine Voraussetzung, die dort
    schon steht, ist ein Zyklus im Graph und darf keinen neuen Umweg
    starten: sonst warten A auf B und B auf A im Kreis.
    """
    gefunden: set[int] = set()
    aktuell = sitzung
    for _ in range(50):                      # Schutz gegen kaputte Ketten
        daten = dict(aktuell.get("daten") or {})
        oben_id = daten.get("voraussetzung_detour")
        if not oben_id:
            break
        oben = store.sitzung(int(oben_id))
        if oben is None:
            break
        if oben.get("konzept_id"):
            gefunden.add(int(oben["konzept_id"]))
        aktuell = oben
    return gefunden


def offene(konzept_id: int, child_key: str = store.CHILD_KEY,
           ohne: set[int] | None = None) -> list[dict]:
    """Voraussetzungen, die Karo unterrichten kann und die noch nicht sitzen.

    Nur solche mit `lokal`: eine Voraussetzung, die Karo nicht hat, kann es
    auch nicht beibringen — sie wird als Inhaltsanfrage bestellt, nicht als
    Lernweg ins Leere. `ohne` schliesst Konzepte aus, die diese Sitzung
    schon erledigt hat oder die in der Umweg-Kette oberhalb warten
    (Zyklusschutz).
    """
    ausgenommen = {int(k) for k in (ohne or set())}
    offen = []
    for v in store.voraussetzungen(konzept_id):
        lokal = v.get("lokal")
        if not lokal or int(lokal) in ausgenommen:
            continue
        if sitzt(int(lokal), child_key):
            continue
        offen.append(v)
    return offen


def fehlende_ohne_lektion(konzept_id: int) -> list[dict]:
    """Voraussetzungen, die Karo gar nicht unterrichten kann.

    Die stehen in der Meldung an den Menschen: ohne diese Angabe sucht er
    den Grund beim Kind.
    """
    return [v for v in store.voraussetzungen(konzept_id) if not v.get("lokal")]


def sitzt(konzept_id: int, child_key: str = store.CHILD_KEY) -> bool:
    """Gilt dieses Konzept als verstanden?

    Verstanden heißt: jede Fehlvorstellung des Konzepts steht im Fortschritt
    auf „sicher". Eine davon offen genügt, um es nicht als sicher zu zählen —
    die Fehlvorstellung ist die Einheit, nicht das Konzept. Daneben gilt
    eine abgeschlossene Sitzung auf dem Konzept selbst als Beleg: wer die
    Leiter bis zum Transfer durchlaufen hat, sitzt — auch wenn der Weg nicht
    jede Fehlvorstellung einzeln besucht hat.
    """
    stand_konzept = store.fortschritt(konzept_id, None,
                                      child_key=child_key) or {}
    if stand_konzept.get("mastery") == "sicher":
        return True
    fehlertypen = store.fehlertypen(konzept_id)
    if not fehlertypen:
        return False
    for f in fehlertypen:
        stand = store.fortschritt(konzept_id, f["id"], child_key=child_key) or {}
        if stand.get("mastery") != "sicher":
            return False
    return True


def diagnoseaufgaben(konzept_id: int) -> list[dict]:
    """Zwei geprüfte Aufgaben zum Voraussetzungskonzept — keine neuen."""
    gefunden = []
    for fehlertyp in store.fehlertypen(konzept_id):
        for aufgabe in inhalt_store.aufgaben(fehlertyp["id"], inhalt_store.SELBSTSTAENDIG):
            if aufgabe.get("frage") and aufgabe.get("loesung"):
                gefunden.append(aufgabe)
            if len(gefunden) >= AUFGABEN:
                return gefunden
    return gefunden


def pruefen(antworten: list[str], aufgaben: list[dict]) -> bool:
    """Sitzt die Voraussetzung? Nur wenn ALLE Aufgaben stimmen.

    Dieselbe Strenge wie bei der Ersteinschätzung: eine von zwei richtig ist
    ein Anfang, keine Sicherheit — und auf einer halben Voraussetzung baut
    das nächste Konzept nicht.
    """
    from .antwortvergleich import check_answer
    if not aufgaben or len(antworten) < len(aufgaben):
        return False
    return all(check_answer(antworten[i], a["loesung"],
                          a.get("antwort_art"), a.get("rubrik"))
               for i, a in enumerate(aufgaben))
