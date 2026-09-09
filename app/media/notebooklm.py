"""Ausgabemodus „notebooklm" — bewusst als letzte Wahl.

NotebookLM hat keine offizielle Schnittstelle für Privatkonten. Was es gibt,
ist `notebooklm-py` (https://github.com/teng-lin/notebooklm-py): ein
Gemeinschaftsprojekt, das die Sitzungs-Cookies eines echten Google-Logins
wiederverwendet und darüber ein Notebook befüllt und ein Video-Overview
anfordert. Das bedeutet konkret:

  * Die Anmeldung läuft irgendwann ab (Wochen bis Monate, je nach Google).
  * Nach einer Änderung der Google-Oberfläche steht der Weg tagelang still.
  * Es liegt in einer Grauzone der Google-Nutzungsbedingungen.
  * Weitergeben lässt sich das nicht: jede Person müsste dieselbe Bastelei
    selbst einrichten.

Deshalb ist dieser Modus in Karo optional, ausdrücklich gekennzeichnet und
niemals Voraussetzung. Die Anwendung fällt erst auf den HTML-Modus zurück,
nachdem sie es bei einem erkennbar vorübergehenden Problem — Netzwerk,
Überlastung, ein einzelner fehlgeschlagener Aufruf — mehrfach mit
wachsender Pause erneut versucht hat (siehe `_mit_wiederholung()`). Nur ein
dauerhafter Grund (keine Anmeldung, CLI fehlt, von Hand abgebrochen) führt
sofort zum Rückfall, ohne es zu wiederholen — ein zweiter Versuch würde
daran ohnehin nichts ändern.

`login_start()` stößt die Anmeldung selbst an, direkt aus der
Einstellungsseite — kein Terminal nötig. Ein Container hat aber keinen
Bildschirm, auf dem ein echtes Browserfenster erscheinen könnte, also baut
Karo sich selbst einen: Xvfb erzeugt einen Bildschirm ohne Monitor, `notebooklm
login` öffnet Chromium hinein, x11vnc teilt diesen Bildschirm per VNC, und
websockify/noVNC zeigen ihn als iframe auf der Einstellungsseite an — alles
nur über 127.0.0.1 erreichbar, und nur solange eine Anmeldung tatsächlich
läuft (siehe `_vnc_starten()`/`_vnc_stoppen()`). Die Familie sieht darin den
echten Google-Login und klickt sich selbst hindurch; Karo bekommt nie ein
Passwort zu Gesicht. Läuft Karo nativ (ohne Docker) und hat der Prozess
bereits einen echten Bildschirm, überspringt `login_start()` die
Xvfb/VNC-Kulisse und öffnet direkt ein normales Browserfenster.

In allen Fällen läuft nur die Kommandozeile von `notebooklm-py`; kein
Passwort, kein Cookie und kein Token laufen jemals durch Karos eigenen Code
oder seine Datenbank. Wer keinen Browser im Container will, kann das Image
ohne NotebookLM bauen (`KARO_MIT_NOTEBOOKLM=0`) — dann bleibt nur der
Weg über `make notebooklm-login` auf dem Rechner selbst (siehe README).
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable

from .. import config

log = logging.getLogger("karo.notebooklm")

CLI = "notebooklm"
LOGIN_BROWSER_TIMEOUT = 300     # Sekunden, die die CLI selbst auf die Anmeldung wartet

AUTH_CHECK_TIMEOUT = 30    # reine Lesepruefung der lokalen Sitzung
SHORT_TIMEOUT = 90         # Notebook anlegen/loeschen, Quelle hochladen
GENERATE_TIMEOUT = 2700    # 45 min — der CLI-Standard von 1800s reichte im
                           # Test nicht immer aus, bis NotebookLM fertig war
DOWNLOAD_TIMEOUT = 300
CANCEL_POLL_SECONDS = 5    # wie oft waehrend "generate" auf Abbruch geprueft wird

VERSUCHE = 3               # fuer kurze Schritte: anlegen, hochladen, holen, loeschen
GENERATE_VERSUCHE = 2      # fuer "generate": jeder Versuch dauert bis zu 45 Minuten
RETRY_BASIS_SEKUNDEN = 15  # Rueckzug zwischen Versuchen: 15s, 30s, 60s, ...

# --- Anmeldung im Browser, angezeigt auf der Einstellungsseite -------------
VNC_DISPLAY_NR = 99
VNC_DISPLAY = f":{VNC_DISPLAY_NR}"
VNC_RFB_PORT = 5901
NOVNC_PORT = 6080
NOVNC_WEB_DIR = "/usr/share/novnc"
VNC_BEREIT_TIMEOUT = 15    # Sekunden, die auf Xvfb/x11vnc/websockify gewartet wird


class NotebookLmUnavailable(RuntimeError):
    """Der Weg steht nicht zur Verfügung. Die Meldung ist für Menschen."""


class Abgebrochen(NotebookLmUnavailable):
    """Von Hand abgebrochen, waehrend der Aufruf noch lief."""


WARNUNG = (
    "NotebookLM hat keine offizielle Schnittstelle für Privatkonten. Dieser "
    "Weg nutzt die Kommandozeile von notebooklm-py, die sich einmalig per "
    "Browser anmeldet und die Sitzung danach lokal wiederverwendet. Läuft "
    "die Anmeldung ab, weicht Karo automatisch auf Folien mit Stimme aus."
)


def _home() -> Path:
    """Wo die NotebookLM-Sitzung liegt.

    Bewusst im Datenverzeichnis, nicht im Home-Verzeichnis des Prozesses:
    /data ist das einzige Verzeichnis, das Neustarts und Image-Updates
    übersteht. Die Anmeldung selbst entsteht anderswo (siehe README) und
    wird hierher nur gespiegelt/gemountet.
    """
    p = config.DATA_DIR / "notebooklm"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _env() -> dict:
    return {**os.environ, "NOTEBOOKLM_HOME": str(_home())}


def _cli_available() -> str | None:
    return shutil.which(CLI)


#: Bekannte Fehlermuster im rohen stderr-Mitschnitt der CLI, uebersetzt in
#: eine Meldung, die eine Familie tatsaechlich lesen soll — statt des rohen
#: Logger-Mitschnitts mit Anfrage-IDs und internen Modulnamen.
_LOGGER_VORSPANN = re.compile(
    r"^\d{2}:\d{2}:\d{2}\s+\w+\s+\[[^\]]+\]\s*(\[req=[^\]]+\]\s*)?")


def _lesbare_fehlermeldung(stderr: str, befehl: str, returncode: int) -> str:
    """Verwandelt einen rohen stderr-Mitschnitt in eine Meldung für Menschen.

    `notebooklm-py`s eigenes Logging landet unverändert in stderr — bei
    mehreren internen Wiederholungsversuchen (Ratenbegrenzung, Netzwerk)
    stehen dort mehrere Zeilen mit technischen Logger-Namen und Anfrage-IDs,
    die eine Familie nicht angezeigt bekommen soll. Bekannte Muster werden
    in eine erklärende deutsche Meldung übersetzt; alles andere wird
    wenigstens vom Logger-Vorspann befreit statt roh angezeigt.
    """
    text = (stderr or "").strip()
    klein = text.lower()

    if "ratelimiterror" in klein or "rate limit" in klein or " 429" in text:
        return (
            "NotebookLM hat gerade zu viele Anfragen abgelehnt — das "
            "deutet auf das Tageslimit für Video-Erstellung hin, nicht auf "
            "einen Fehler in Karo. Karo hat es mehrfach automatisch erneut "
            "versucht. Meist hilft es, es an einem anderen Tag erneut zu "
            "probieren.")
    if any(m in klein for m in ("server-error", "transportservererror",
                                " 500", " 502", " 503")):
        return ("NotebookLM war vorübergehend nicht erreichbar (ein "
                "Server-Fehler bei Google). Karo hat es mehrfach "
                "automatisch erneut versucht.")
    if not text:
        return f"„notebooklm {befehl}“ ist mit Code {returncode} fehlgeschlagen."

    zeilen = [z.strip() for z in text.splitlines() if z.strip()]
    letzte = _LOGGER_VORSPANN.sub("", zeilen[-1]) if zeilen else text
    return letzte[:300] or f"„notebooklm {befehl}“ ist mit Code {returncode} fehlgeschlagen."


def _antwort_auswerten(befehl: str, returncode: int, stdout: str, stderr: str) -> dict:
    rohtext = (stdout or "").strip()
    try:
        antwort = json.loads(rohtext) if rohtext else {}
    except json.JSONDecodeError:
        antwort = {}

    if returncode != 0:
        # Manche Unterbefehle liefern "error" als Freitext, andere nur als
        # Wahrheitswert (z. B. bei einem Timeout beim Warten) — nur einen
        # tatsächlichen String als Meldung verwenden, sonst weiterfallen.
        feld = antwort.get("error") if isinstance(antwort, dict) else None
        fehler = (
            feld if isinstance(feld, str) and feld
            else _lesbare_fehlermeldung(stderr, befehl, returncode)
        )
        raise NotebookLmUnavailable(fehler)

    return antwort if isinstance(antwort, dict) else {}


def _run(*args: str, timeout: int, json_ausgabe: bool = True) -> dict:
    """Ruft `notebooklm <args>` auf und gibt die geparste JSON-Antwort zurück.

    Wirft `NotebookLmUnavailable` mit einer für Menschen verständlichen
    Meldung — nie eine rohe subprocess- oder JSON-Ausnahme.
    """
    argv = [CLI, *args, "--json"] if json_ausgabe else [CLI, *args]
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout,
            env=_env(), check=False,
        )
    except subprocess.TimeoutExpired:
        raise NotebookLmUnavailable(
            f"Der Aufruf „notebooklm {args[0] if args else ''}“ hat zu lange "
            "gedauert und wurde abgebrochen.") from None
    except FileNotFoundError:
        raise NotebookLmUnavailable(
            "Die NotebookLM-Kommandozeile wurde nicht gefunden.") from None

    return _antwort_auswerten(args[0] if args else "", proc.returncode,
                              proc.stdout, proc.stderr)


def _run_abbrechbar(*args: str, timeout: int,
                    abgebrochen: Callable[[], bool]) -> dict:
    """Wie `_run`, aber fuer lange Aufrufe: prueft alle paar Sekunden, ob von
    Hand abgebrochen wurde, und beendet den Unterprozess dann sofort statt
    bis zu `timeout` Sekunden weiterzulaufen.

    Wirft `Abgebrochen` (eine `NotebookLmUnavailable`) bei einem Abbruch von
    Hand, sonst wie `_run`.
    """
    argv = [CLI, *args, "--json"]
    befehl = args[0] if args else ""
    try:
        proc = subprocess.Popen(
            argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env=_env(),
        )
    except FileNotFoundError:
        raise NotebookLmUnavailable(
            "Die NotebookLM-Kommandozeile wurde nicht gefunden.") from None

    def _abwuergen() -> None:
        proc.kill()
        try:
            proc.communicate(timeout=10)
        except Exception:                                  # pragma: no cover
            pass

    verstrichen = 0.0
    while True:
        try:
            stdout, stderr = proc.communicate(timeout=CANCEL_POLL_SECONDS)
            break
        except subprocess.TimeoutExpired:
            verstrichen += CANCEL_POLL_SECONDS
            if abgebrochen():
                _abwuergen()
                raise Abgebrochen("Von Hand abgebrochen.") from None
            if verstrichen >= timeout:
                _abwuergen()
                raise NotebookLmUnavailable(
                    f"Der Aufruf „notebooklm {befehl}“ hat zu lange gedauert "
                    "und wurde abgebrochen.") from None

    return _antwort_auswerten(befehl, proc.returncode, stdout, stderr)


#: Fehlertexte, die auf ein erkennbar vorübergehendes Problem hindeuten —
#: hier lohnt ein weiterer Versuch, weil derselbe Aufruf kurz danach oft
#: einfach durchgeht (siehe die echten Fehler, an denen dieser Code beim
#: Testen scheiterte: ein einzelner HTTP-500 auf ADD_SOURCE, eine Suche, die
#: einmalig zu lange brauchte). Alles andere — keine Anmeldung, CLI fehlt,
#: von Hand abgebrochen, ein Schema-Fehler — wird NICHT wiederholt, weil ein
#: zweiter Versuch garantiert dasselbe Ergebnis hätte.
_VORUEBERGEHEND = (
    "server-error", "server error", " 500", "502", "503", "504",
    "retries exhausted", "rate limit", "ratelimit", "too many requests",
    "429", "connection", "network", "econn", "enotfound", "timeout",
    "zu lange gedauert", "temporarily", "vorübergehend", "überlastet",
    "unavailable", "reset by peer", "broken pipe",
)


def _voruebergehend(fehler: Exception) -> bool:
    if isinstance(fehler, Abgebrochen):
        return False
    text = str(fehler).lower()
    return any(m in text for m in _VORUEBERGEHEND)


def _mit_wiederholung(schritt: str, aufruf: Callable[[], dict], *,
                      versuche: int = VERSUCHE,
                      abgebrochen: Callable[[], bool] = lambda: False) -> dict:
    """Ruft `aufruf()` auf und wiederholt bei einem erkennbar vorübergehenden
    Fehler mit wachsender Pause, statt beim ersten Wackler aufzugeben.

    Die Pause zwischen zwei Versuchen wird in kurzen Stücken abgewartet und
    dabei `abgebrochen()` geprüft, damit ein Abbruch von Hand nicht erst am
    Ende der Pause wirkt.
    """
    zuletzt: NotebookLmUnavailable | None = None
    for versuch in range(1, versuche + 1):
        try:
            return aufruf()
        except NotebookLmUnavailable as exc:
            if abgebrochen():
                raise Abgebrochen("Von Hand abgebrochen.") from None
            zuletzt = exc
            if not _voruebergehend(exc) or versuch == versuche:
                raise
            pause = RETRY_BASIS_SEKUNDEN * (2 ** (versuch - 1))
            log.warning(
                "NotebookLM-Schritt „%s“ (Versuch %s/%s) vorübergehend "
                "fehlgeschlagen, erneut in %ss: %s",
                schritt, versuch, versuche, pause, exc)
            verstrichen = 0.0
            while verstrichen < pause:
                if abgebrochen():
                    raise Abgebrochen("Von Hand abgebrochen.") from None
                schlaf = min(CANCEL_POLL_SECONDS, pause - verstrichen)
                time.sleep(schlaf)
                verstrichen += schlaf
    raise zuletzt  # pragma: no cover — die Schleife wirft immer vorher


def verfuegbar() -> tuple[bool, str]:
    """Prüft, ob die CLI da ist UND die gespeicherte Anmeldung noch gilt.

    Bewusst OHNE `--passive`: Googles rotierende Sitzungs-Cookies
    (`__Secure-1PSIDTS`) erneuern sich im normalen Betrieb selbst — das ist
    kein Fehler, sondern der vorgesehene Weg, wie die Sitzung ohne erneuten
    Login weiterlebt. Mit `--passive` verweigert die Prüfung genau diese
    Erneuerung und meldet eine gesunde Sitzung fälschlich als abgelaufen.
    """
    if _cli_available() is None:
        return False, (
            "Das Kommando „notebooklm“ ist nicht installiert. Dieser Modus ist "
            "bewusst nicht Teil des Images — siehe README, Abschnitt "
            "„NotebookLM“. Der HTML- und der MP4-Modus funktionieren ohne.")
    try:
        antwort = _run("auth", "check", "--test", timeout=AUTH_CHECK_TIMEOUT)
    except NotebookLmUnavailable:
        return False, (
            "Es liegt keine gültige NotebookLM-Anmeldung vor. Einmalig auf "
            "diesem Rechner anmelden (siehe README, Abschnitt „NotebookLM“) "
            "— danach merkt sich Karo die Sitzung und fragt nicht erneut.")

    email = ((antwort.get("account") or {}).get("email")
             if isinstance(antwort, dict) else None)
    hinweis = f"Angemeldet als {email}." if email else "Die Anmeldung ist gültig."
    return True, hinweis


def trennen() -> None:
    """Meldet die gespeicherte NotebookLM-Sitzung ab.

    Nutzt den eigenen `auth logout`-Befehl der CLI, statt selbst in
    `storage_state.json` herumzuloeschen — die CLI kennt ihre eigenen
    Sperr- und Zusatzdateien besser als Karo.

    Wirft `NotebookLmUnavailable`, wenn die CLI fehlt oder der Befehl
    scheitert. Kein Fehler, wenn ohnehin keine Sitzung vorlag.
    """
    if _cli_available() is None:
        raise NotebookLmUnavailable(
            "Die NotebookLM-Kommandozeile ist nicht installiert.")
    _run("auth", "logout", timeout=SHORT_TIMEOUT)


# --------------------------------------------------------------------------
# Anmeldung aus der Einstellungsseite anstoßen
# --------------------------------------------------------------------------

_login_lock = threading.Lock()
_login_status: dict = {
    "laeuft": False, "ok": None, "meldung": "", "vnc_bereit": False,
    "novnc_port": NOVNC_PORT,
}
_vnc_prozesse: list[subprocess.Popen] = []


def login_status() -> dict:
    """Stand der zuletzt angestoßenen Anmeldung, für die Einstellungsseite."""
    with _login_lock:
        return dict(_login_status)


def _tcp_offen(host: str, port: int) -> bool:
    import socket

    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _vnc_verfuegbar() -> bool:
    return all(shutil.which(b) for b in ("Xvfb", "x11vnc", "websockify"))


def _vnc_starten() -> bool:
    """Baut den Bildschirm ohne Monitor auf: Xvfb, dann x11vnc, dann
    websockify/noVNC. Gibt False zurück, wenn eines der Werkzeuge fehlt oder
    nicht rechtzeitig bereit wird — dann versucht `login_start()` stattdessen
    einen normalen Browser (funktioniert nur bei einem echten Bildschirm).
    """
    if not _vnc_verfuegbar():
        return False

    try:
        xvfb = subprocess.Popen(
            ["Xvfb", VNC_DISPLAY, "-screen", "0", "1280x800x24", "-nolisten", "tcp"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _vnc_prozesse.append(xvfb)

        sperre = Path(f"/tmp/.X{VNC_DISPLAY_NR}-lock")
        begonnen = time.monotonic()
        while not sperre.exists():
            if xvfb.poll() is not None or time.monotonic() - begonnen > VNC_BEREIT_TIMEOUT:
                return False
            time.sleep(0.2)

        x11vnc = subprocess.Popen(
            ["x11vnc", "-display", VNC_DISPLAY, "-rfbport", str(VNC_RFB_PORT),
             "-listen", "127.0.0.1", "-nopw", "-forever", "-shared", "-quiet"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _vnc_prozesse.append(x11vnc)

        begonnen = time.monotonic()
        while not _tcp_offen("127.0.0.1", VNC_RFB_PORT):
            if x11vnc.poll() is not None or time.monotonic() - begonnen > VNC_BEREIT_TIMEOUT:
                return False
            time.sleep(0.2)

        websockify = subprocess.Popen(
            ["websockify", f"--web={NOVNC_WEB_DIR}", str(NOVNC_PORT),
             f"127.0.0.1:{VNC_RFB_PORT}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _vnc_prozesse.append(websockify)

        begonnen = time.monotonic()
        while not _tcp_offen("127.0.0.1", NOVNC_PORT):
            if websockify.poll() is not None or time.monotonic() - begonnen > VNC_BEREIT_TIMEOUT:
                return False
            time.sleep(0.2)

        return True
    except Exception:                                        # pragma: no cover
        log.exception("Aufbau der VNC-Anzeige fehlgeschlagen")
        return False


def _vnc_stoppen() -> None:
    while _vnc_prozesse:
        proc = _vnc_prozesse.pop()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:                     # pragma: no cover
            proc.kill()
            try:
                proc.wait(timeout=5)
            except Exception:
                pass


def login_start() -> bool:
    """Stößt die Anmeldung im Hintergrund an. True, wenn sie jetzt läuft.

    Baut zuerst einen Bildschirm ohne Monitor auf (Xvfb + x11vnc + noVNC),
    damit die Familie den Google-Login als iframe auf der Einstellungsseite
    sieht und dort selbst durchklickt — kein Terminal nötig (siehe
    Modul-Docstring). Steht diese Kulisse nicht zur Verfügung (Image ohne
    NotebookLM gebaut, oder die Werkzeuge fehlen), versucht `notebooklm
    login` trotzdem — das funktioniert dann nur, wenn der Karo-Prozess
    bereits einen echten Bildschirm hat (nativer Lauf ohne Docker).

    Läuft in einem eigenen Thread, damit der Request, der den Knopf gedrückt
    hat, nicht bis zu fünf Minuten wartet. Fängt jeden Fehler selbst ab, statt
    ihn zu werfen: es gibt keine Warteschlange mit automatischer Wiederholung
    dahinter — ein Login, den niemand zu Ende geführt hat, soll nicht von
    selbst erneut aufpoppen.
    """
    if _cli_available() is None:
        return False
    with _login_lock:
        if _login_status["laeuft"]:
            return False
        _login_status.update(laeuft=True, ok=None, meldung="", vnc_bereit=False)

    def _lauf() -> None:
        vnc_aktiv = False
        try:
            vnc_aktiv = _vnc_starten()
            if vnc_aktiv:
                with _login_lock:
                    _login_status["vnc_bereit"] = True

            umgebung = _env()
            if vnc_aktiv:
                umgebung["DISPLAY"] = VNC_DISPLAY

            proc = subprocess.run(
                [CLI, "login", "--browser", "chromium",
                 "--browser-timeout", str(LOGIN_BROWSER_TIMEOUT)],
                capture_output=True, text=True,
                timeout=LOGIN_BROWSER_TIMEOUT + 30, env=umgebung, check=False,
            )
            ok = proc.returncode == 0
            meldung = "Angemeldet." if ok else (
                (proc.stderr or "").strip()[:400]
                or "Die Anmeldung wurde nicht abgeschlossen.")
        except subprocess.TimeoutExpired:
            ok, meldung = False, "Die Anmeldung hat zu lange gedauert."
        except Exception as exc:                            # pragma: no cover
            ok, meldung = False, f"Anmeldung fehlgeschlagen: {exc}"
        finally:
            if vnc_aktiv:
                _vnc_stoppen()
        with _login_lock:
            _login_status.update(laeuft=False, ok=ok, meldung=meldung, vnc_bereit=False)

    threading.Thread(target=_lauf, daemon=True, name="notebooklm-login").start()
    return True


def quelle_text(titel: str, folien: list[dict]) -> str:
    """Baut aus den Folien den Fließtext, den NotebookLM als Quelle bekommt.

    Öffentlich, damit `teaching.py` genau diesen Text — Wort für Wort das,
    was tatsächlich an NotebookLM geschickt wird — als eigene Datei ablegen
    kann, bevor `erzeugen()` überhaupt läuft (siehe dort und
    `_render_material()`). So lässt sich das jederzeit nachlesen, auch wenn
    die Erzeugung selbst fehlschlägt.
    """
    teile = [titel]
    for folie in folien:
        block = [f"Folie {folie.get('nr', '?')}: {folie.get('titel', '')}"]
        for punkt in folie.get("punkte") or []:
            block.append(f"- {punkt}")
        if folie.get("tafel"):
            block.append(f"Tafel: {folie['tafel']}")
        if folie.get("sprechtext"):
            block.append(folie["sprechtext"])
        teile.append("\n".join(block))
    return "\n\n".join(teile)


def erzeugen(titel: str, folien: list[dict], quellen_text: str,
             abgebrochen: Callable[[], bool] = lambda: False) -> str:
    """Lässt NotebookLM ein Video-Overview erzeugen und liefert den lokalen MP4-Pfad.

    Ablauf: ein eigenes, leeres Notebook anlegen, den Erklärtext als
    Textquelle hochladen, ein Video-Overview anfordern, auf das Ergebnis
    warten, es herunterladen und das Notebook wieder löschen. Das Notebook
    ist nur ein Transportmittel — im NotebookLM-Konto der Familie soll
    nichts von Karo liegen bleiben.

    `abgebrochen`: wird waehrend des bis zu 45 Minuten dauernden
    "generate"-Schritts alle paar Sekunden abgefragt. Liefert sie True (z. B.
    weil die Lerneinheit von Hand beendet wurde), bricht der laufende
    NotebookLM-Aufruf sofort ab statt bis zum Ende durchzulaufen.

    Wirft `NotebookLmUnavailable`, wenn irgendein Schritt scheitert. Die
    Aufruferin (siehe `app/teaching.py`) fällt dann auf Folien mit Stimme
    zurück.
    """
    ok, grund = verfuegbar()
    if not ok:
        raise NotebookLmUnavailable(grund)

    text = (quellen_text or "").strip() or quelle_text(titel, folien)
    if not text:
        raise NotebookLmUnavailable(
            "Es gibt keinen Text, aus dem NotebookLM ein Video machen könnte.")

    if abgebrochen():
        raise Abgebrochen("Von Hand abgebrochen.")

    notebook_id: str | None = None
    try:
        erstellt = _mit_wiederholung(
            "Notebook anlegen",
            lambda: _run("create", (titel or "Karo-Lerneinheit")[:150],
                        timeout=SHORT_TIMEOUT),
            abgebrochen=abgebrochen)
        notebook_id = erstellt.get("id") or (erstellt.get("notebook") or {}).get("id")
        if not notebook_id:
            raise NotebookLmUnavailable(
                "NotebookLM hat beim Anlegen des Notebooks keine ID zurückgemeldet.")

        _mit_wiederholung(
            "Quelle hochladen",
            lambda: _run("source", "add", text, "-n", notebook_id, "--type", "text",
                        "--title", (titel or "Erklärung")[:150], timeout=SHORT_TIMEOUT),
            abgebrochen=abgebrochen)

        if abgebrochen():
            raise Abgebrochen("Von Hand abgebrochen.")

        beschreibung = (
            f"Erkläre kindgerecht und klar auf Deutsch: {titel}. "
            "Nutze ausschließlich die bereitgestellte Quelle, erfinde nichts hinzu."
        )
        status = _mit_wiederholung(
            "Video erzeugen",
            lambda: _run_abbrechbar(
                "generate", "video", beschreibung, "-n", notebook_id,
                "--format", "explainer", "--language", "de",
                "--wait", "--timeout", str(GENERATE_TIMEOUT), "--retry", "3",
                timeout=GENERATE_TIMEOUT, abgebrochen=abgebrochen,
            ),
            versuche=GENERATE_VERSUCHE, abgebrochen=abgebrochen)
        if status.get("status") not in (None, "completed", "success", "done", "ready"):
            raise NotebookLmUnavailable(
                f"NotebookLM meldet Status „{status.get('status')}“ statt Erfolg.")

        ziel = config.media_dir() / f"notebooklm-{notebook_id}.mp4"
        _mit_wiederholung(
            "Video herunterladen",
            lambda: _run("download", "video", str(ziel), "-n", notebook_id, "--force",
                        timeout=DOWNLOAD_TIMEOUT),
            abgebrochen=abgebrochen)
        if not ziel.is_file() or ziel.stat().st_size == 0:
            raise NotebookLmUnavailable(
                "Der Download von NotebookLM hat keine Videodatei erzeugt.")
        return str(ziel)
    finally:
        if notebook_id:
            try:
                _mit_wiederholung(
                    "Notebook aufräumen",
                    lambda: _run("delete", "-n", notebook_id, "-y", timeout=SHORT_TIMEOUT))
            except NotebookLmUnavailable as exc:
                log.warning("NotebookLM-Notebook %s konnte nicht aufgeräumt "
                           "werden: %s", notebook_id, exc)
