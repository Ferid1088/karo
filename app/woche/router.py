"""„Meine Woche" — Routen des Begleiters.

Fünf Bildschirme für das Kind, einer für die Eltern. Wenn ein sechster
dazukommt, ist etwas falsch gelaufen.

  /woche                 Heute        eine Sache, ein Knopf
  /woche/plan            Meine Woche  das Angebot und mein Ding
  /woche/hilfe           Hilfe        wer da ist, mit Namen
  /woche/ueber-dich      Was ich über dich weiß
  /woche/stundenplan     Mein Stundenplan
  /woche/eltern          ein Bildschirm, ein Impuls

Der Begleiter benutzt von Karo nur die Infrastruktur (Verbindung, Sitzung,
CSRF) — keine Themen, keine Flaggen, keinen Lernzyklus, kein Sprachmodell.
"""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_303_SEE_OTHER

from .. import security
from . import bruecke, regeln, store, vorschlaege

log = logging.getLogger("karo.woche")
router = APIRouter(prefix="/woche")

BASE = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE / "templates"))

try:
    ASSET_VERSION = str(int((BASE / "static" / "woche.css").stat().st_mtime))
except OSError:                                    # pragma: no cover
    ASSET_VERSION = "0"

MAX_BILD_BYTES = 8 * 1024 * 1024


def render(request: Request, name: str, **ctx) -> HTMLResponse:
    """Eigener Renderer — der Begleiter erbt Karos Kopfzeile nicht."""
    token = request.session.get("csrf")
    if not token:
        token = security.new_csrf_token()
        request.session["csrf"] = token
    d = store.ding()
    basis = {
        "request": request,
        "asset_version": ASSET_VERSION,
        "csrf": token,
        "csrf_field": security.CSRF_FIELD,
        "path": request.url.path,
        "kind": store.kind(),
        "ding": d,
        "ding_wort": store.wort_oder_form(d),
        "formen": store.FORMEN,
        "tage": store.TAGE,
        "heute_tag": store.wochentag(),
        "pause": store.pause_aktiv(),
        "offene_freigaben": len(store.offene_freigaben()),
        "datum_kurz": store.datum_kurz,
    }
    basis.update(ctx)
    return templates.TemplateResponse(request, f"woche/{name}", basis)


def zurueck(ziel: str = "/woche") -> RedirectResponse:
    return RedirectResponse(ziel, status_code=HTTP_303_SEE_OTHER)


def sag(request: Request, text: str) -> None:
    request.session["woche_sagt"] = text


# ==========================================================================
# Bildschirm 1 — Heute
# ==========================================================================

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def heute(request: Request):
    store.ensure()
    if not store.eingerichtet():
        return zurueck("/woche/einrichtung")

    if store.pause_aktiv():
        return render(request, "pause.html")

    faellig = store.zyklus_faellig()
    if faellig is not None:
        return zurueck("/woche/abschluss")

    z = store.zyklus()
    if z is None:
        # Stille Woche: ab Dienstag legt die App selbst etwas hin, statt
        # „Plane deine Woche" zu verlangen. Planen ist die hoechste Huerde
        # und darf den Zugang nie blockieren.
        if store.wochentag() >= 2 and store.letzte_zyklen(2):
            z_id = store.zyklus_starten("", regeln.horizont(), still=True)
            regeln.angebot_bauen(z_id, "", max_schritte=1)
            z = store.zyklus()
        else:
            return zurueck("/woche/plan")

    regeln.wissen_neu_berechnen()
    s = regeln.heute_schritt(z["id"])
    fehlt = store.anker_fehlend_heute(z["id"])
    return render(request, "heute.html", zyklus=z, schritt=s, anker_fach=fehlt,
                  anker_vorschlag=bruecke.ankervorschlag(fehlt["name"]) if fehlt else "",
                  sagt=request.session.pop("woche_sagt", None),
                  still=bool(z["still"]))


@router.post("/anker")
def anker_setzen(request: Request, fach_id: int = Form(...),
                 text: str = Form("")):
    z = store.zyklus()
    if z is None:
        return zurueck()
    if text.strip() and text.strip() != "weiß nicht":
        store.anker_setzen(z["id"], fach_id, text)
    else:
        # „weiß nicht" ist eine vollwertige Antwort und wird nicht nachgehakt.
        store.anker_setzen(z["id"], fach_id, "")
    return zurueck()


# --------------------------------------------------------------------------
# Die Einstiegshandlung
# --------------------------------------------------------------------------

@router.post("/schritt/{schritt_id}/einstieg")
def einstieg(request: Request, schritt_id: int, wert: str = Form("gemacht")):
    s = store.schritt(schritt_id)
    if s is None:
        return zurueck()
    wert = "gemacht" if wert == "gemacht" else "nicht"
    store.ereignis("einstieg", wert, zyklus_id=s["zyklus_id"],
                   schritt_id=schritt_id, fach_id=s["fach_id"])
    if wert == "nicht":
        sag(request, "Okay. Morgen wieder.")
        return zurueck()
    return zurueck(f"/woche/schritt/{schritt_id}/weiter")


@router.get("/schritt/{schritt_id}/weiter", response_class=HTMLResponse)
def weiter_fragen(request: Request, schritt_id: int):
    s = store.schritt(schritt_id)
    if s is None:
        return zurueck()
    minuten = vorschlaege.MINUTEN.get(s["groesse"], 8)
    return render(request, "weiter.html", schritt=s, minuten=minuten)


@router.post("/schritt/{schritt_id}/weiter")
def weiter(request: Request, schritt_id: int, wert: str = Form("nein")):
    s = store.schritt(schritt_id)
    if s is None:
        return zurueck()
    store.ereignis("weiter", "ja" if wert == "ja" else "nein",
                   zyklus_id=s["zyklus_id"], schritt_id=schritt_id,
                   fach_id=s["fach_id"])
    if wert != "ja":
        # „Nein" ist ein vollwertiger Abschluss. Angefangen war das Ziel.
        sag(request, "Passt. Du hast angefangen — das war's schon.")
        return zurueck()
    return zurueck(f"/woche/schritt/{schritt_id}/form")


@router.get("/schritt/{schritt_id}/form", response_class=HTMLResponse)
def form_seite(request: Request, schritt_id: int):
    s = store.schritt(schritt_id)
    if s is None:
        return zurueck()
    minuten = vorschlaege.MINUTEN.get(s["groesse"], 8)
    z = regeln.zaehler()
    thema = bruecke.titelzusatz(s["fach_name"] or "")
    return render(request, "form.html", schritt=s, minuten=minuten,
                  bestzeit=z["bestzeit"], thema=thema,
                  lerneinheit=bruecke.lerneinheit(thema) if thema else None)


@router.post("/schritt/{schritt_id}/bestzeit")
def bestzeit(request: Request, schritt_id: int, sekunden: int = Form(...)):
    s = store.schritt(schritt_id)
    if s is None or sekunden <= 0 or sekunden > 3600:
        return zurueck()
    store.ereignis("bestzeit", str(int(sekunden)), zyklus_id=s["zyklus_id"],
                   schritt_id=schritt_id, fach_id=s["fach_id"])
    return zurueck(f"/woche/schritt/{schritt_id}/rueckmeldung")


@router.get("/schritt/{schritt_id}/rueckmeldung", response_class=HTMLResponse)
def rueckmeldung_seite(request: Request, schritt_id: int):
    s = store.schritt(schritt_id)
    if s is None:
        return zurueck()
    return render(request, "rueckmeldung.html", schritt=s)


@router.post("/schritt/{schritt_id}/rueckmeldung")
def rueckmeldung(request: Request, schritt_id: int, wert: str = Form("okay")):
    s = store.schritt(schritt_id)
    if s is None:
        return zurueck()
    wert = wert if wert in ("gut", "okay", "schwierig") else "okay"
    store.ereignis("rueckmeldung", wert, zyklus_id=s["zyklus_id"],
                   schritt_id=schritt_id, fach_id=s["fach_id"])
    if wert == "schwierig":
        return zurueck(f"/woche/schritt/{schritt_id}/grund")
    # War es gut oder okay, passiert nichts weiter. Kein Lob, keine Rückfrage.
    if wert == "gut" and s["fach_name"]:
        return zurueck(f"/woche/schritt/{schritt_id}/karte")
    sag(request, "Gut. Bis morgen.")
    return zurueck()


# --------------------------------------------------------------------------
# Wenn etwas schwierig war
# --------------------------------------------------------------------------

@router.get("/schritt/{schritt_id}/grund", response_class=HTMLResponse)
def grund_seite(request: Request, schritt_id: int):
    s = store.schritt(schritt_id)
    if s is None:
        return zurueck()
    return render(request, "grund.html", schritt=s,
                  gruende=regeln.GRUND_LABELS)


@router.post("/schritt/{schritt_id}/grund")
def grund(request: Request, schritt_id: int, wert: str = Form("")):
    s = store.schritt(schritt_id)
    if s is None:
        return zurueck()
    if wert in regeln.GRUND_LABELS:
        store.ereignis("grund", wert, zyklus_id=s["zyklus_id"],
                       schritt_id=schritt_id, fach_id=s["fach_id"])
        return zurueck(f"/woche/schritt/{schritt_id}/anpassung?grund={wert}")
    return zurueck()


@router.get("/schritt/{schritt_id}/anpassung", response_class=HTMLResponse)
def anpassung_seite(request: Request, schritt_id: int, grund: str = ""):
    s = store.schritt(schritt_id)
    if s is None:
        return zurueck()
    return render(request, "anpassung.html", schritt=s, grund=grund,
                  vorschlag=regeln.anpassen(s, grund),
                  helfer=store.helfer())


@router.post("/schritt/{schritt_id}/anpassung")
def anpassung(request: Request, schritt_id: int, art: str = Form(""),
              wert: str = Form("")):
    s = store.schritt(schritt_id)
    if s is None:
        return zurueck()

    if art == "kleiner" and wert == "annehmen":
        v = regeln.anpassen(s, "zu_schwer")
        if v["art"] == "kleiner":
            store.schritt_anpassen(schritt_id, v["neu"]["titel"],
                                   v["neu"]["einstieg"], v["neu"]["groesse"])
            store.ereignis("anpassung", "kleiner", zyklus_id=s["zyklus_id"],
                           schritt_id=schritt_id, fach_id=s["fach_id"])
            sag(request, "Okay, kleiner. Morgen neu.")
    elif art == "zeitpunkt":
        store.ereignis("anpassung", "zeitpunkt", zyklus_id=s["zyklus_id"],
                       schritt_id=schritt_id, notiz=wert)
        sag(request, f"Gemerkt: {wert}.")
    elif art == "ruhen":
        store.schritt_ruhen(schritt_id)
        store.ereignis("anpassung", "strategie", zyklus_id=s["zyklus_id"],
                       schritt_id=schritt_id)
        sag(request, "Lassen wir diese Woche ruhen.")
    elif art == "kurz":
        store.ereignis("anpassung", "kurz", zyklus_id=s["zyklus_id"],
                       schritt_id=schritt_id)
        sag(request, "Morgen nur zwei Minuten.")
    return zurueck()


# --------------------------------------------------------------------------
# Sammelkarte
# --------------------------------------------------------------------------

@router.get("/schritt/{schritt_id}/karte", response_class=HTMLResponse)
def karte_seite(request: Request, schritt_id: int):
    s = store.schritt(schritt_id)
    if s is None:
        return zurueck()
    a = store.anker(s["zyklus_id"], s["fach_id"]) if s["fach_id"] else None
    thema = (a["text"] if a and a["text"] else s["fach_name"]) or "Thema"
    return render(request, "karte.html", schritt=s, thema=thema)


@router.post("/schritt/{schritt_id}/karte")
def karte(request: Request, schritt_id: int, thema: str = Form(""),
          nein: str = Form("")):
    s = store.schritt(schritt_id)
    if s is None or nein:
        return zurueck()
    d = store.ding()
    store.karte_anlegen(thema or (s["fach_name"] or "Thema"),
                        d["bild"] if d else None)
    store.ereignis("karte", thema[:80], zyklus_id=s["zyklus_id"],
                   schritt_id=schritt_id, fach_id=s["fach_id"])
    sag(request, "Karte dazu.")
    return zurueck()


# ==========================================================================
# Bildschirm 2 — Meine Woche
# ==========================================================================

@router.get("/plan", response_class=HTMLResponse)
def plan(request: Request):
    store.ensure()
    if not store.eingerichtet():
        return zurueck("/woche/einrichtung")
    z = store.zyklus()
    k = store.kind()
    frage = None
    if z is None:
        idx = (k["frage_index"] or 0) % len(vorschlaege.FRAGEN)
        frage = dict(vorschlaege.FRAGEN[idx])
        if frage["schluessel"] == "nervt":
            frage["antworten"] = [f["name"] for f in store.faecher()]
    karo_satz = ""
    for f in store.faecher():
        karo_satz = bruecke.hinweis(f["name"])
        if karo_satz:
            break
    return render(request, "plan.html", zyklus=z, faecher=store.faecher(),
                  schritte=store.schritte(z["id"]) if z else [],
                  karten=store.karten(), horizont=regeln.horizont(),
                  frage=frage, gemieden=regeln.gemiedene_faecher(),
                  karo_satz=karo_satz)


@router.post("/start")
async def start(request: Request):
    formular = await request.form()
    fokus = str(formular.get("fokus") or "").strip()
    fach_ids = [int(v) for v in formular.getlist("fach_id") if str(v).isdigit()]
    laenge = regeln.horizont()
    z_id = store.zyklus_starten(fokus, laenge)
    regeln.angebot_bauen(z_id, fokus, fach_ids or None)

    # Die eine Kennenlernfrage — ueberspringbar, rotierend.
    antwort = str(formular.get("frage_antwort") or "").strip()
    schluessel = str(formular.get("frage_schluessel") or "").strip()
    if antwort and schluessel:
        eintrag = next((f for f in vorschlaege.FRAGEN
                        if f["schluessel"] == schluessel), None)
        if eintrag:
            regeln.wissen_sagen(schluessel, eintrag["symbol"],
                                eintrag["satz"].format(wert=antwort[:40]))
    k = store.kind()
    store.kind_setzen(frage_index=(k["frage_index"] or 0) + 1)
    return zurueck()


@router.post("/weglassen")
def weglassen(request: Request, fach_id: int = Form(...)):
    """Bewusst weglassen ist eine Entscheidung, kein Versagen."""
    f = store.fach(fach_id)
    if f is None:
        return zurueck("/woche/plan")
    store.ereignis("weglassen", f["name"], fach_id=fach_id)
    sag(request, f"Okay. {f['name']} ist gerade kein Thema.")
    return zurueck("/woche/plan")


@router.post("/ding")
async def ding_aendern(request: Request, wort: str = Form(""),
                       form: str = Form("einfach"),
                       bild: UploadFile | None = None):
    """Wechseln dauert zehn Sekunden. Keine Rückfrage, keine Historie."""
    name = None
    if bild is not None and getattr(bild, "filename", ""):
        puffer = bytearray()
        while stueck := await bild.read(1 << 20):
            puffer.extend(stueck)
            if len(puffer) > MAX_BILD_BYTES:
                sag(request, "Das Bild ist zu groß.")
                return zurueck("/woche/plan")
        name = store.ding_bild_speichern(bytes(puffer),
                                         Path(bild.filename).suffix)
    if wort.strip() or name:
        store.ding_setzen(wort or "mein Ding", form, name)
    return zurueck("/woche/plan")


@router.get("/bild/{name}")
def bild(name: str):
    pfad = (store.bilder_dir() / Path(name).name)
    if not pfad.is_file():
        return HTMLResponse("", status_code=404)
    return FileResponse(str(pfad))


# ==========================================================================
# Bildschirm 3 — Hilfe
# ==========================================================================

@router.get("/hilfe", response_class=HTMLResponse)
def hilfe_seite(request: Request):
    store.ensure()
    z = regeln.zaehler()
    return render(request, "hilfe.html", helfer=store.helfer(),
                  termin=store.fester_termin(),
                  nie_gefragt=(z["hilfe_geholt"] == 0),
                  sagt=request.session.pop("woche_sagt", None))


@router.post("/hilfe")
def hilfe(request: Request, helfer_id: int = Form(0), frage: str = Form("")):
    z = store.zyklus()
    name = "aufgeschrieben"
    if helfer_id:
        treffer = [h for h in store.helfer() if h["id"] == helfer_id]
        if treffer:
            name = treffer[0]["name"]
    store.ereignis("hilfe", name, zyklus_id=z["id"] if z else None,
                   notiz=frage)
    if helfer_id:
        sag(request, f"{name} weiß Bescheid.")
    else:
        sag(request, "Aufgeschrieben. Kommt beim nächsten festen Termin dran.")
    return zurueck("/woche/hilfe")


# ==========================================================================
# Bildschirm 4 — Was ich über dich weiß
# ==========================================================================

@router.get("/ueber-dich", response_class=HTMLResponse)
def ueber_dich(request: Request):
    store.ensure()
    regeln.wissen_neu_berechnen()
    return render(request, "ueber_dich.html", zeilen=regeln.wissen_zeilen(),
                  anker_optionen=vorschlaege.TAGESANKER)


@router.post("/wissen/{wissen_id}/aus")
def wissen_aus(request: Request, wissen_id: int):
    """Ein Tap. Keine Rückfrage, kein „bist du sicher?"."""
    regeln.wissen_ausblenden(wissen_id)
    return zurueck("/woche/ueber-dich")


@router.post("/anstupser")
def anstupser(request: Request, wert: str = Form(""), aus: str = Form("")):
    if aus:
        store.kind_setzen(anstupser_aus=1, anstupser_anker=None)
    elif wert in vorschlaege.TAGESANKER:
        store.kind_setzen(anstupser_anker=wert, anstupser_aus=0)
    return zurueck("/woche/ueber-dich")


# ==========================================================================
# Bildschirm 5 — Mein Stundenplan
# ==========================================================================

@router.get("/stundenplan", response_class=HTMLResponse)
def stundenplan(request: Request):
    store.ensure()
    k = store.kind()
    return render(request, "stundenplan.html", plan=store.stundenplan(),
                  faecher=store.faecher(), termine=store.termine(),
                  bild=k["plan_bild"] if k else None)


@router.post("/stundenplan/foto")
async def stundenplan_foto(request: Request, bild: UploadFile | None = None):
    """Das Foto bleibt nützlich, auch wenn nichts daraus gelesen wird.

    Texterkennung ist bewusst nicht im MVP: eine Erkennungsquote unter 100 %
    in der ersten Minute wäre der schlechteste denkbare Einstieg. Das Bild
    ist der Stundenplan — antippen der Fächer kostet einen Tap mehr.
    """
    if bild is None or not getattr(bild, "filename", ""):
        return zurueck("/woche/stundenplan")
    puffer = bytearray()
    while stueck := await bild.read(1 << 20):
        puffer.extend(stueck)
        if len(puffer) > MAX_BILD_BYTES:
            sag(request, "Das Bild ist zu groß.")
            return zurueck("/woche/stundenplan")
    name = store.ding_bild_speichern(bytes(puffer), Path(bild.filename).suffix)
    store.kind_setzen(plan_bild=name)
    return zurueck("/woche/stundenplan")


@router.post("/stundenplan/tage")
async def stundenplan_tage(request: Request):
    formular = await request.form()
    for f in store.faecher():
        tage = [int(v) for v in formular.getlist(f"tag_{f['id']}")
                if str(v).isdigit()]
        store.stunden_setzen(f["id"], tage)
    return zurueck("/woche/stundenplan")


# ==========================================================================
# Notfall, Pause, Abschluss
# ==========================================================================

@router.get("/notfall", response_class=HTMLResponse)
def notfall_seite(request: Request):
    store.ensure()
    return render(request, "notfall.html", faecher=store.faecher(),
                  ergebnis=None, helfer=store.helfer())


@router.post("/notfall")
def notfall(request: Request, fach_id: int = Form(0), was: str = Form("arbeit"),
            minuten: int = Form(20)):
    f = store.fach(fach_id)
    name = f["name"] if f else "das Fach"
    z = store.zyklus()
    store.ereignis("notfall", was, zyklus_id=z["id"] if z else None,
                   fach_id=fach_id or None)
    ergebnis = regeln.notfall(name, minuten)
    return render(request, "notfall.html", faecher=store.faecher(),
                  ergebnis=ergebnis, fach=f, helfer=store.helfer())


@router.post("/pause")
def pause(request: Request, wochen: int = Form(1)):
    store.pause_setzen(wochen)
    return zurueck()


@router.post("/pause/ende")
def pause_ende(request: Request):
    store.pause_beenden()
    return zurueck()


@router.get("/abschluss", response_class=HTMLResponse)
def abschluss_seite(request: Request):
    store.ensure()
    z = store.zyklus_faellig() or store.letzte_zyklen(1)
    z = z if not isinstance(z, list) else (z[0] if z else None)
    if z is None:
        return zurueck("/woche/plan")
    saetze = regeln.rueckblick(z["id"])
    leer_text, leer_optionen = regeln.rueckblick_leer_text()
    gemacht = [s for s in store.schritte(z["id"])
               if any(e["schritt_id"] == s["id"] for e in
                      store.ereignisse(z["id"], "einstieg"))]
    return render(request, "abschluss.html", zyklus=z, saetze=saetze,
                  gemacht=gemacht, leer_text=leer_text,
                  leer_optionen=leer_optionen)


@router.post("/abschluss")
def abschluss(request: Request, gefuehl: str = Form("okay"),
              wunsch: str = Form("genauso")):
    z = store.zyklus_faellig() or store.zyklus()
    if z is None:
        return zurueck("/woche/plan")
    store.zyklus_abschliessen(z["id"], gefuehl, wunsch)
    if wunsch == "pause":
        store.pause_setzen(1)
        return zurueck()
    return zurueck("/woche/plan")


# ==========================================================================
# Einrichtung — drei Minuten
# ==========================================================================

STANDARD_FAECHER = ["Mathematik", "Deutsch", "Englisch", "Biologie", "Physik",
                    "Chemie", "Geschichte", "Erdkunde", "Französisch", "Latein",
                    "Kunst", "Musik", "Sport", "Religion", "Ethik", "Politik"]


@router.get("/einrichtung", response_class=HTMLResponse)
def einrichtung(request: Request):
    store.ensure()
    return render(request, "einrichtung.html", standard=STANDARD_FAECHER,
                  faecher=store.faecher(), helfer=store.helfer(),
                  schritt=_einrichtungsschritt())


def _einrichtungsschritt() -> int:
    if not store.faecher():
        return 1
    if store.ding() is None:
        return 2
    if not store.helfer():
        return 3
    return 4


@router.post("/einrichtung/faecher")
async def einrichtung_faecher(request: Request):
    formular = await request.form()
    namen = [str(v) for v in formular.getlist("fach")]
    klasse = str(formular.get("klasse") or "6")
    store.faecher_setzen(namen)
    if klasse.isdigit():
        store.kind_setzen(klasse=max(1, min(13, int(klasse))))
    return zurueck("/woche/einrichtung")


@router.post("/einrichtung/ding")
async def einrichtung_ding(request: Request, wort: str = Form(""),
                           form: str = Form("einfach"),
                           bild: UploadFile | None = None):
    name = None
    if bild is not None and getattr(bild, "filename", ""):
        puffer = bytearray()
        while stueck := await bild.read(1 << 20):
            puffer.extend(stueck)
            if len(puffer) > MAX_BILD_BYTES:
                break
        if len(puffer) <= MAX_BILD_BYTES:
            name = store.ding_bild_speichern(bytes(puffer),
                                             Path(bild.filename).suffix)
    store.ding_setzen(wort or "mein Ding", form, name)
    return zurueck("/woche/einrichtung")


@router.post("/einrichtung/helfer")
def einrichtung_helfer(request: Request, name: str = Form(""),
                       fester_tag: int = Form(0), feste_zeit: str = Form(""),
                       fertig: str = Form("")):
    if name.strip():
        store.helfer_anlegen(name, None,
                             fester_tag if 1 <= fester_tag <= 7 else None,
                             feste_zeit)
    if fertig:
        store.kind_setzen(eingerichtet_am=dt.date.today().isoformat())
        return zurueck("/woche/plan")
    return zurueck("/woche/einrichtung")


# ==========================================================================
# Eltern — ein Bildschirm, ein Impuls
# ==========================================================================

@router.get("/eltern", response_class=HTMLResponse)
def eltern(request: Request):
    store.ensure()
    k = store.kind()
    return render(request, "eltern.html",
                  zusammenfassung=regeln.eltern_zusammenfassung(),
                  zusagen=store.zusagen(),
                  regeln_liste=regeln.ZUSTAND_REGELN,
                  freigaben=store.offene_freigaben(),
                  termin=store.fester_termin(),
                  bruecke_an=bool(k and k["karo_bruecke"]),
                  karo_fach=bruecke.karo_fach())


@router.post("/eltern/bruecke")
def eltern_bruecke(request: Request, an: str = Form("")):
    """Schaltet mit, ob der Begleiter Karos Themen mitliest.

    Standardmaessig aus: der Begleiter soll auch dann vollstaendig
    funktionieren, wenn Karo leer ist oder ein anderes Fach abdeckt."""
    store.kind_setzen(karo_bruecke=1 if an else 0)
    return zurueck("/woche/eltern")


@router.post("/eltern/zusage")
def eltern_zusage(request: Request, nr: int = Form(...)):
    if 1 <= nr <= 3:
        store.zusage_setzen(nr)
    return zurueck("/woche/eltern")


@router.post("/eltern/freigabe/{ding_id}")
def eltern_freigabe(request: Request, ding_id: int, ja: str = Form("")):
    store.ding_freigeben(ding_id, bool(ja))
    return zurueck("/woche/eltern")
