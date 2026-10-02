"""Die Regeln des Begleiters — Zaehlen statt Verstehen.

Alles, was die App „ueber das Kind weiss", entsteht hier: aus Zaehlern ueber
`woche_ereignis`, aus einer festen Tabelle und aus dem, was das Kind selbst
gesagt hat. Kein Modell, keine Vorhersage, keine Aussage ueber die Person.

Jede Regel ist als Konstante oben sichtbar, damit sie nachlesbar und
aenderbar bleibt — und damit im Eltern-Dashboard steht, wie ein Zustand
zustande kommt.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

from .. import config, db
from . import bruecke, store, vorschlaege

# --------------------------------------------------------------------------
# Die Schwellen. Alle an einer Stelle.
# --------------------------------------------------------------------------

_OPS = config.ops()
FENSTER_TAGE = _OPS.woche_fenster_tage                # Beobachtungsfenster der Zaehler
SCHLECHTER_TAG_AB = _OPS.woche_schlechter_tag_ab      # x nichts an diesem Wochentag
GUTER_TAG_AB = _OPS.woche_guter_tag_ab                # x abgeschlossen an diesem Wochentag
GEMIEDEN_TAGE = _OPS.woche_gemieden_tage              # so lange kein einziges Mal gewaehlt
GEMIEDEN_MIN_STUNDEN = _OPS.woche_gemieden_min_stunden  # Kunst zu meiden ist kein Problem fuer eine App
ZU_SCHWER_AB = _OPS.woche_zu_schwer_ab                # x „zu schwer" -> kleinere Stufe wird Standard
ABBRUCH_AB = _OPS.woche_abbruch_ab                    # x abgebrochen -> kuerzerer Block
VERKLEINERN_MAX = _OPS.woche_verkleinern_max          # Untergrenze: danach Strategiewechsel
SCHWIERIG_TAGE_AB = _OPS.woche_schwierig_tage_ab      # so viele schwierige Tage -> die Woche auf eine Sache
NULLZYKLEN_AB = _OPS.woche_nullzyklen_ab              # so viele Zyklen ohne Ereignis -> fragen statt zusammenfassen
KARTEN_SCHWELLE = _OPS.woche_karten_schwelle          # x „gut" auf dasselbe Fach -> Karte anbieten
SCHLAFGRENZE = _OPS.woche_schlafgrenze_stunde         # ab dieser Stunde schlaegt die App nichts mehr vor

GRUND_LABELS = {
    "zu_schwer": "zu schwer",
    "keine_zeit": "keine Zeit",
    "keine_lust": "keine Lust",
    "konzentration": "konnte mich nicht konzentrieren",
}

GRUND_ANTWORT = {
    "zu_schwer": "Dann machen wir den nächsten Schritt kleiner.",
    "keine_zeit": "Wann passt es dir besser?",
    "keine_lust": "Willst du morgen nur anfangen — zwei Minuten?",
    "konzentration": "Kürzerer Block? 8 statt 15 Minuten.",
}


def _seit(tage: int) -> str:
    return (dt.date.today() - dt.timedelta(days=tage)).isoformat()


# --------------------------------------------------------------------------
# Zaehler
# --------------------------------------------------------------------------

def zaehler() -> dict:
    """Alles, was gezaehlt wird. Eine Abfrage pro Zeile, nichts Geheimes."""
    store.ensure()
    seit = _seit(FENSTER_TAGE)

    gemacht_je_tag = {z["tag"]: z["n"] for z in db.q(
        "SELECT tag, COUNT(*) AS n FROM woche_ereignis "
        "WHERE art='einstieg' AND wert='gemacht' AND created_at >= ? "
        "GROUP BY tag", seit)}
    nicht_je_tag = {z["tag"]: z["n"] for z in db.q(
        "SELECT tag, COUNT(*) AS n FROM woche_ereignis "
        "WHERE art='einstieg' AND wert='nicht' AND created_at >= ? "
        "GROUP BY tag", seit)}

    gruende = {z["wert"]: z["n"] for z in db.q(
        "SELECT wert, COUNT(*) AS n FROM woche_ereignis WHERE art='grund' "
        "AND created_at >= ? GROUP BY wert", seit)}

    formen = {z["form"]: z["n"] for z in db.q(
        "SELECT s.form AS form, COUNT(*) AS n FROM woche_ereignis e "
        "JOIN woche_schritt s ON s.id=e.schritt_id "
        "WHERE e.art='einstieg' AND e.wert='gemacht' AND e.created_at >= ? "
        "GROUP BY s.form", seit)}

    hilfe = db.q1("SELECT COUNT(*) AS n FROM woche_ereignis WHERE art='hilfe' "
                  "AND created_at >= ?", seit)["n"]

    schwierig_zuletzt = [z["wert"] for z in db.q(
        "SELECT wert FROM woche_ereignis WHERE art='rueckmeldung' "
        "ORDER BY id DESC LIMIT ?", SCHWIERIG_TAGE_AB)]

    bestzeit = db.q1(
        "SELECT MIN(CAST(wert AS INTEGER)) AS t FROM woche_ereignis "
        "WHERE art='bestzeit'")

    return {
        "gemacht_je_tag": gemacht_je_tag,
        "nicht_je_tag": nicht_je_tag,
        "schlechte_tage": sorted(
            t for t in range(1, 8)
            if nicht_je_tag.get(t, 0) >= SCHLECHTER_TAG_AB
            and gemacht_je_tag.get(t, 0) == 0),
        "gute_tage": sorted(t for t in range(1, 8)
                            if gemacht_je_tag.get(t, 0) >= GUTER_TAG_AB),
        "gruende": gruende,
        "zu_schwer": gruende.get("zu_schwer", 0),
        "abbrueche": gruende.get("konzentration", 0),
        "formen": formen,
        "lieblingsform": max(formen, key=formen.get) if formen else None,
        "hilfe_geholt": hilfe,
        "schwierig_serie": (len(schwierig_zuletzt) >= SCHWIERIG_TAGE_AB
                            and all(w == "schwierig" for w in schwierig_zuletzt)),
        "bestzeit": bestzeit["t"] if bestzeit else None,
    }


def standardgroesse() -> str:
    """Welche Schrittgroesse ist gerade der Standard?"""
    z = zaehler()
    if z["zu_schwer"] >= ZU_SCHWER_AB or z["abbrueche"] >= ABBRUCH_AB:
        return "klein"
    if z["gute_tage"]:
        return "mittel"
    return "klein"


def gemiedene_faecher() -> list[sqlite3.Row]:
    """Faecher ab drei Wochenstunden, die vier Wochen nicht vorkamen."""
    store.ensure()
    seit = _seit(GEMIEDEN_TAGE)
    benutzt = {z["fach_id"] for z in db.q(
        "SELECT DISTINCT fach_id FROM woche_ereignis "
        "WHERE fach_id IS NOT NULL AND created_at >= ?", seit)}
    weggelassen = {z["wert"] for z in db.q(
        "SELECT wert FROM woche_ereignis WHERE art='weglassen' "
        "AND created_at >= ?", seit)}
    # Ohne Zyklushistorie ist „gemieden" bedeutungslos.
    if not db.q("SELECT id FROM woche_zyklus WHERE created_at < ?", seit):
        return []
    return [f for f in store.faecher()
            if f["id"] not in benutzt
            and f["name"] not in weggelassen
            and (f["stunden"] or 0) >= GEMIEDEN_MIN_STUNDEN]


def nullzyklen() -> int:
    """Wie viele abgeschlossene Zyklen in Folge ohne ein einziges Ereignis?"""
    store.ensure()
    n = 0
    for z in db.q("SELECT id FROM woche_zyklus WHERE status='fertig' "
                  "ORDER BY id DESC LIMIT 5"):
        treffer = db.q1(
            "SELECT 1 AS da FROM woche_ereignis WHERE zyklus_id=? "
            "AND art='einstieg' AND wert='gemacht' LIMIT 1", z["id"])
        if treffer:
            break
        n += 1
    return n


# --------------------------------------------------------------------------
# Horizont: 3, 7 oder 14 Tage
# --------------------------------------------------------------------------

def horizont() -> int:
    """Kuerzere Zyklen heissen mehr Neustarts — die wichtigste Funktion."""
    z = zaehler()
    if z["schwierig_serie"] or nullzyklen() >= 1:
        return 3
    letzter = db.q1("SELECT wunsch FROM woche_zyklus WHERE status='fertig' "
                    "ORDER BY id DESC LIMIT 1")
    if letzter and letzter["wunsch"] == "mehr":
        return 14
    if letzter and letzter["wunsch"] == "leichter":
        return 3
    return 7


# --------------------------------------------------------------------------
# Anlass: warum steht dieses Fach gerade an?
# --------------------------------------------------------------------------

ARBEITSWOERTER = ("arbeit", "test", "klausur", "prüfung", "pruefung", "ka",
                  "vokabeltest", "referat")


def passt_zum_fokus(fach_name: str, fokus: str) -> bool:
    """„Mathearbeit" meint Mathematik.

    Ein reines `in` scheitert daran: „mathematik" steckt nicht in
    „mathearbeit". Deshalb wird über den Wortstamm verglichen — das ist die
    Art Tippfehler, die ein Kind beim Wochenstart ständig produziert.
    """
    fach = (fach_name or "").strip().lower()
    text = (fokus or "").strip().lower()
    if not fach or not text:
        return False
    if fach in text or text in fach:
        return True
    stamm = fach[:4]
    return len(stamm) >= 4 and stamm in text


def anlass_fuer(fach: sqlite3.Row, fokus: str) -> str:
    name = (fach["name"] or "").lower()

    # Weiß Karo von einer eingetragenen Arbeit, zählt das Datum — es ist
    # härter als das, was das Kind in den Fokus getippt hat. Ist die Brücke
    # aus oder kennt Karo dieses Fach nicht, kommt None und es bleibt bei
    # der eigenen Logik.
    von_karo = bruecke.anlass(fach["name"])
    if von_karo:
        return von_karo

    if passt_zum_fokus(name, fokus):
        if any(w in (fokus or "").lower() for w in ARBEITSWOERTER):
            return "arbeit_nah"
        return "arbeit_fern"
    if fach["id"] in {f["id"] for f in gemiedene_faecher()}:
        return "gemieden"
    if store.faecher_am_tag(store.wochentag()) and fach["id"] in {
            f["id"] for f in store.faecher_am_tag(store.wochentag())}:
        return "hausaufgaben"
    return "normal"


# --------------------------------------------------------------------------
# Angebot bauen — nie mehr als drei Dinge
# --------------------------------------------------------------------------

def angebot_bauen(zyklus_id: int, fokus: str, fach_ids: list[int] | None = None,
                  max_schritte: int = 3) -> int:
    """Legt die Schritte des Zyklus an. Gibt die Anzahl zurueck."""
    store.ensure()
    k = store.kind()
    klasse = k["klasse"] if k else 6
    d = store.ding()
    form = d["form"] if d else "einfach"
    groesse = standardgroesse()

    if zaehler()["schwierig_serie"]:
        max_schritte = 1        # „Diese Woche machen wir nur eine Sache."

    kandidaten = list(store.faecher())
    if fach_ids:
        kandidaten = [f for f in kandidaten if f["id"] in set(fach_ids)]
    # Das Fach aus dem Fokus zuerst.
    if fokus:
        kandidaten.sort(key=lambda f: 0 if passt_zum_fokus(f["name"], fokus) else 1)

    gemieden_ids = {f["id"] for f in gemiedene_faecher()}
    gemieden_verwendet = False
    angelegt = 0

    for f in kandidaten:
        if angelegt >= max_schritte:
            break
        anlass = anlass_fuer(f, fokus)
        if anlass == "gemieden":
            # Hoechstens ein gemiedenes Fach pro Zyklus, immer am kleinsten.
            if gemieden_verwendet:
                continue
            gemieden_verwendet = True
            stufe = "klein"
        else:
            stufe = groesse
        a = store.anker(zyklus_id, f["id"])
        v = vorschlaege.vorschlag(f["name"], anlass, stufe, klasse,
                                  a["text"] if a else None)
        # Kennt Karo eine Lücke in diesem Fach, wird aus „das schwierigste
        # Thema üben" der Name des Themas. Der Schritt bleibt derselbe — er
        # wird nur konkret.
        luecke = bruecke.titelzusatz(f["name"])
        if luecke and anlass in ("arbeit_nah", "arbeit_fern", "morgen"):
            v["titel"] = f"{luecke} — {v['titel']}"
        store.schritt_anlegen(zyklus_id, f["id"], v["titel"], v["einstieg"],
                              stufe, anlass,
                              form if f["id"] not in gemieden_ids else "einfach")
        angelegt += 1

    if angelegt == 0:
        store.schritt_anlegen(zyklus_id, None, fokus or "eine Sache",
                              "Nimm das Heft raus und schlag es auf.",
                              "klein", "normal", "einfach")
        angelegt = 1
    return angelegt


def heute_schritt(zyklus_id: int) -> sqlite3.Row | None:
    """Die eine Sache fuer heute.

    Reihenfolge: was heute Unterricht hatte, dann der Rest. An einem
    schlechten Wochentag schlaegt die App nichts vor."""
    tag = store.wochentag()
    if tag in zaehler()["schlechte_tage"]:
        return None
    alle = [s for s in store.schritte(zyklus_id) if not store.heute_schon(s["id"])]
    if not alle:
        return None
    heute_faecher = {f["id"] for f in store.faecher_am_tag(tag)}
    alle.sort(key=lambda s: 0 if s["fach_id"] in heute_faecher else 1)
    return alle[0]


# --------------------------------------------------------------------------
# Anpassung mit Untergrenze
# --------------------------------------------------------------------------

def anpassen(s: sqlite3.Row, grund: str) -> dict:
    """Antwort auf 😣. Verkleinert hoechstens zweimal, dann Strategiewechsel."""
    k = store.kind()
    klasse = k["klasse"] if k else 6
    fach_name = s["fach_name"] or "das Thema"

    if s["verkleinert"] >= VERKLEINERN_MAX:
        return {
            "art": "strategie",
            "text": "Das Kleinermachen hilft gerade nicht. "
                    "Sollen wir etwas anderes probieren?",
            "optionen": ["anderer_schritt", "hilfe", "ruhen"],
        }

    if grund == "zu_schwer":
        neu = vorschlaege.KLEINER.get(s["groesse"], "klein")
        a = store.anker(s["zyklus_id"], s["fach_id"]) if s["fach_id"] else None
        v = vorschlaege.vorschlag(fach_name, s["anlass"], neu, klasse,
                                  a["text"] if a else None)
        return {"art": "kleiner", "text": GRUND_ANTWORT[grund],
                "neu": v, "optionen": ["annehmen", "lassen"]}

    if grund == "keine_zeit":
        return {"art": "zeitpunkt", "text": GRUND_ANTWORT[grund],
                "optionen": vorschlaege.TAGESANKER}

    if grund == "keine_lust":
        return {"art": "kurz", "text": GRUND_ANTWORT[grund],
                "optionen": ["annehmen", "lassen"]}

    return {"art": "kurz", "text": GRUND_ANTWORT.get(grund, "Okay."),
            "optionen": ["annehmen", "lassen"]}


# --------------------------------------------------------------------------
# „Was ich ueber dich weiss"
# --------------------------------------------------------------------------

def _wissen_schreiben(schluessel: str, symbol: str, text: str) -> None:
    """Schreibt eine berechnete Zeile — niemals ueber eine Kind-Zeile."""
    vorhanden = db.q1("SELECT * FROM woche_wissen WHERE schluessel=?", schluessel)
    if vorhanden and vorhanden["quelle"] == "kind":
        return
    with db.tx() as c:
        if vorhanden:
            c.execute("UPDATE woche_wissen SET symbol=?, text=? WHERE id=?",
                      (symbol, text, vorhanden["id"]))
        else:
            c.execute("INSERT INTO woche_wissen (schluessel, symbol, text, "
                      "quelle, created_at) VALUES (?,?,?,'zaehler',?)",
                      (schluessel, symbol, text, db.now()))


def wissen_neu_berechnen() -> None:
    store.ensure()
    z = zaehler()
    k = store.kind()
    d = store.ding()

    if d:
        form = store.FORMEN.get(d["form"], store.FORMEN["einfach"])
        if d["freigabe"] == "ja":
            satz = f"Dein Ding ist {d['wort']}."
        else:
            satz = f"Du machst es als {form['label']}."
        _wissen_schreiben("ding", form["symbol"], satz)

    for tag in z["schlechte_tage"][:1]:
        _wissen_schreiben("schlechter_tag", "📅",
                          f"{store.TAGE[tag]}s ist es meistens schwer.")
    for tag in z["gute_tage"][:1]:
        _wissen_schreiben("guter_tag", "📅",
                          f"{store.TAGE[tag]}s klappt es am besten.")

    if k and k["anstupser_anker"]:
        _wissen_schreiben("anker", "🍽",
                          f"Du fängst am ehesten {k['anstupser_anker']} an.")

    if z["zu_schwer"] >= ZU_SCHWER_AB:
        _wissen_schreiben("minuten", "⏱",
                          "Kurze Blöcke passen dir besser als lange.")

    if z["lieblingsform"]:
        form = store.FORMEN.get(z["lieblingsform"], store.FORMEN["einfach"])
        _wissen_schreiben("form", form["symbol"],
                          f"{form['label']} klappt bei dir am besten.")

    if z["bestzeit"]:
        _wissen_schreiben("bestzeit", "⏱",
                          f"Deine Bestzeit: {int(z['bestzeit'])} Sekunden.")

    t = store.fester_termin()
    if t and t["fester_tag"]:
        zeit = f" um {t['feste_zeit']}" if t["feste_zeit"] else ""
        _wissen_schreiben("termin", "👤",
                          f"{t['name']} hat {store.TAGE[t['fester_tag']].lower()}s"
                          f"{zeit} Zeit für dich.")


def wissen_zeilen(alle: bool = False) -> list[sqlite3.Row]:
    store.ensure()
    if alle:
        return db.q("SELECT * FROM woche_wissen ORDER BY id")
    return db.q("SELECT * FROM woche_wissen WHERE sichtbar=1 ORDER BY id")


def wissen_sagen(schluessel: str, symbol: str, text: str) -> None:
    """Etwas, das das Kind selbst gesagt hat. Wird nie ueberschrieben."""
    store.ensure()
    with db.tx() as c:
        c.execute(
            "INSERT INTO woche_wissen (schluessel, symbol, text, quelle, "
            "created_at) VALUES (?,?,?,'kind',?) "
            "ON CONFLICT(schluessel) DO UPDATE SET text=excluded.text, "
            "quelle='kind', sichtbar=1",
            (schluessel, symbol, text, db.now()))


def wissen_ausblenden(wissen_id: int) -> None:
    with db.tx() as c:
        c.execute("UPDATE woche_wissen SET sichtbar=0 WHERE id=?", (wissen_id,))


# --------------------------------------------------------------------------
# Rueckblick — nur belegte Saetze
# --------------------------------------------------------------------------

def rueckblick(zyklus_id: int) -> list[str]:
    """Jeder Satz haengt an einem echten Ereignis. Sonst kein Satz."""
    store.ensure()
    saetze: list[str] = []
    e = store.ereignisse(zyklus_id)
    arten = [(x["art"], x["wert"]) for x in e]

    angefangen = sum(1 for a, w in arten if a == "einstieg" and w == "gemacht")
    if angefangen >= 2:
        saetze.append(f"Du hast {angefangen}-mal angefangen.")
    elif angefangen == 1:
        saetze.append("Du hast angefangen.")

    if any(a == "hilfe" for a, _ in arten):
        vor_schwierig = next((i for i, (a, w) in enumerate(arten)
                              if a == "rueckmeldung" and w == "schwierig"), 10**6)
        erste_hilfe = next((i for i, (a, _) in enumerate(arten) if a == "hilfe"),
                           10**6)
        if erste_hilfe < vor_schwierig:
            saetze.append("Du hast gefragt, bevor es schwierig wurde.")
        else:
            saetze.append("Du hast dir Hilfe geholt.")

    if any(a == "anpassung" for a, _ in arten):
        saetze.append("Du hast deinen Plan geändert, statt aufzugeben.")

    if any(a == "weglassen" for a, _ in arten):
        saetze.append("Du hast selbst entschieden, was nicht dran ist.")

    if any(a == "notfall" for a, _ in arten):
        saetze.append("Du hast dir abends noch selbst geholfen.")

    if any(a == "karte" for a, _ in arten):
        saetze.append("Du hast eine neue Karte dazubekommen.")

    return saetze


def rueckblick_leer_text() -> tuple[str, list | None]:
    """Was steht da, wenn nichts passiert ist?

    Ab dem zweiten Nullzyklus wird nicht mehr zusammengefasst, sondern
    gefragt — derselbe Satz dreimal wird sonst zur Bestaetigung des
    Scheiterns."""
    if nullzyklen() >= NULLZYKLEN_AB:
        return ("Zwei Mal hat's nicht geklappt. Was passt gerade besser?",
                [("kurz", "kürzer machen (nur 3 Tage)"),
                 ("ein_fach", "nur ein Fach"),
                 ("pause", "Pause machen"),
                 ("weiss_nicht", "weiß nicht")])
    return ("Diese Woche war zäh. Das kommt vor. Montag fangen wir neu an.",
            None)


# --------------------------------------------------------------------------
# Eltern: vier Zustaende, ein Impuls
# --------------------------------------------------------------------------

ZUSTAENDE = {
    "laeuft": ("Der Plan läuft.", "Heute nichts nötig."),
    "gefragt": ("Ihr Kind hat gefragt.",
                "Frag kurz, ob ihr gemeinsam draufschauen sollt."),
    "passt_nicht": ("Der Plan passt gerade nicht.",
                    "Beim nächsten Start gemeinsam neu planen."),
    "pause": ("Pausiert.", "Nicht ansprechen. Ihr fester Termin bleibt."),
}

ZUSTAND_REGELN = [
    ("gefragt", "Das Kind hat um Hilfe gebeten."),
    ("passt_nicht", "Die Anpassungsgrenze wurde erreicht, oder der Zyklus "
                    "wurde nicht gestartet."),
    ("pause", "Das Kind hat die App pausiert."),
    ("laeuft", "Mindestens einmal angefangen, kein offener Hilferuf."),
]


def eltern_zustand() -> dict:
    store.ensure()
    if store.pause_aktiv():
        return {"key": "pause", **_zustand("pause")}

    z = store.zyklus()
    if z is None:
        return {"key": "passt_nicht", **_zustand("passt_nicht")}

    e = store.ereignisse(z["id"])
    hilfe = [x for x in e if x["art"] == "hilfe"]
    if hilfe:
        return {"key": "gefragt", **_zustand("gefragt")}

    grenze = any(s["verkleinert"] >= VERKLEINERN_MAX for s in store.schritte(z["id"]))
    angefangen = sum(1 for x in e if x["art"] == "einstieg" and x["wert"] == "gemacht")
    halbzeit = dt.date.fromisoformat(z["start"]) + dt.timedelta(
        days=max(1, z["laenge"] // 2))
    if grenze or (angefangen == 0 and dt.date.today() > halbzeit):
        return {"key": "passt_nicht", **_zustand("passt_nicht")}

    return {"key": "laeuft", **_zustand("laeuft")}


def _zustand(key: str) -> dict:
    titel, impuls = ZUSTAENDE[key]
    return {"titel": titel, "impuls": impuls}


def eltern_zusammenfassung() -> dict:
    """Was auf dem Elternbildschirm steht. Kein „offen", keine Quote."""
    store.ensure()
    z = store.zyklus() or store.zyklus_faellig()
    if z is None:
        return {"zyklus": None, "fokus": None, "gemacht": [], "stimmung": None,
                **eltern_zustand()}

    e = store.ereignisse(z["id"])
    angefangen = sum(1 for x in e if x["art"] == "einstieg" and x["wert"] == "gemacht")
    hilfe = sum(1 for x in e if x["art"] == "hilfe")
    gemacht = []
    if angefangen:
        gemacht.append(f"{angefangen}-mal angefangen")
    if hilfe:
        gemacht.append(f"{hilfe}-mal Hilfe geholt")

    # Eine einzelne Rueckmeldung ist keine Stimmung. Aus n=1 ein Urteil zu
    # bauen waere genau die Sorte Aussage, die dieses Dashboard nicht trifft.
    rueck = [x["wert"] for x in e if x["art"] == "rueckmeldung"]
    if len(rueck) < 2:
        stimmung = None
    elif rueck.count("schwierig") > len(rueck) / 2:
        stimmung = "oft schwierig"
    elif rueck.count("gut") > len(rueck) / 2:
        stimmung = "meist gut"
    else:
        stimmung = "meist okay"

    return {"zyklus": z, "fokus": z["fokus"], "gemacht": gemacht,
            "stimmung": stimmung, **eltern_zustand()}


# --------------------------------------------------------------------------
# Notfall: Triage statt Planung
# --------------------------------------------------------------------------

def notfall(fach_name: str, minuten: int, stunde: int | None = None) -> dict:
    """Eine Sache. Ehrlich. Nach 21 Uhr gar nichts mehr."""
    jetzt = stunde if stunde is not None else dt.datetime.now().hour
    if jetzt >= SCHLAFGRENZE:
        return {"schlaf": True,
                "text": "Das reicht für heute. Schlaf lieber — müde schreibt "
                        "sich schlechter als unvorbereitet.",
                "schritt": None}

    k = store.kind()
    klasse = k["klasse"] if k else 6
    groesse = "klein" if minuten <= 20 else "mittel"
    v = vorschlaege.vorschlag(fach_name, "morgen", groesse, klasse, None)
    ehrlich = ("Das schaffst du nicht mehr komplett. Das hier bringt am meisten:"
               if minuten <= 20 else
               "Alles geht nicht mehr. Das hier bringt am meisten:")
    # Im Notfall ist Karos Wissen am wertvollsten: statt „die letzten zwei
    # Hausaufgaben" kann genau die Lücke drinstehen, die Karo gemessen hat.
    luecke = bruecke.titelzusatz(fach_name)
    if luecke:
        v["titel"] = luecke
        v["einstieg"] = (f"Schlag {fach_name} bei „{luecke}“ auf und lies die "
                         f"erste Aufgabe laut vor.")
    return {"schlaf": False, "text": ehrlich, "schritt": v,
            "lerneinheit": bruecke.lerneinheit(luecke) if luecke else None}
