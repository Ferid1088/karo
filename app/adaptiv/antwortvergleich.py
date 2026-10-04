"""Antworten fachlich vergleichen, nicht buchstabengenau.

`ist_richtig` kannte zwei Faelle: derselbe Bruchwert oder dieselbe
Zeichenkette. Damit war „2x+6" auf „2(x+3)" falsch — mathematisch dieselbe
Antwort, als falsch gewertet. Diese Datei prueft je nach `antwort_art` der
Aufgabe:

* Zahlen und Brueche: Wertvergleich in Bruchzahlen — 1/2 == 2/4 == 0,5,
  auch „12 : 4" statt „3".
* Terme: Linearform a·x + b — „2(x+3)" == „2x+6".
* Gleichungen: Loesungsmenge — „x = 5" == „5 = x", und „5" ist eine
  richtige Antwort auf „x = 5".
* Auswahl und Text: normalisierte Zeichenkette, wie bisher.

Wie `rechnen.py` bewusst kein `eval()`: ein kleiner Parser ist sicherer
als eine Zeichenkette, die irgendwann aus einer Modellausgabe stammt.
Was sich nicht sicher vergleichen laesst, wird als Zeichenkette
verglichen — lieber einmal zu streng als einmal falsch richtig.
"""

from __future__ import annotations

import re
from fractions import Fraction

from karo_contract import rechnen

from .normalisierung import normalisiere, normalisiere_thema

#: Welche `antwort_art` auf welchen Vergleich weist.
_ZAHLEN = {"bruch", "fraction", "zahl", "integer", "ganzzahl",
           "dezimal", "decimal", "rechnung"}
_TERME = {"term", "expression", "ausdruck"}
_GLEICHUNGEN = {"gleichung", "equation"}
_TEXT = {"auswahl", "choice", "text", "freitext"}


class _NichtVergleichbar(ValueError):
    """Der Ausdruck ist kein linearer Term — kein Fehlverhalten, nur
    ausserhalb dessen, was sicher verglichen werden kann."""


# --------------------------------------------------------------------------
# Lineare Terme: a·x + b
# --------------------------------------------------------------------------

def _marken(text: str) -> list:
    """Zahlen, genau eine Unbekannte und Operatoren — wirft sonst."""
    roh = (text.replace("·", "*").replace("×", "*").replace(":", "/")
               .replace("−", "-").replace("–", "-").replace(",", "."))
    marken, i, variablen = [], 0, set()
    while i < len(roh):
        z = roh[i]
        if z.isspace():
            i += 1
        elif z.isdigit() or z == ".":
            j = i
            while j < len(roh) and (roh[j].isdigit() or roh[j] == "."):
                j += 1
            zahl = roh[i:j]
            if not zahl.strip(".") or zahl.count(".") > 1:
                raise _NichtVergleichbar(roh[i:j])
            marken.append(Fraction(zahl))
            i = j
        elif z.isalpha():
            variablen.add(z.lower())
            marken.append("x")          # jede Unbekannte zaehlt gleich
            i += 1
        elif z in "+-*/()":
            marken.append(z)
            i += 1
        else:
            raise _NichtVergleichbar(z)
    if not marken or len(variablen) > 1:
        # Verschiedene Unbekannte kann die Linearform nicht unterscheiden.
        raise _NichtVergleichbar(text)
    # Implizite Multiplikation einsetzen: „2x", „2(…)", „x(…)", „)x".
    ergaenzt = []
    for marke in marken:
        if (ergaenzt and isinstance(ergaenzt[-1], (Fraction, str))
                and (ergaenzt[-1] == "x" or ergaenzt[-1] == ")"
                     or isinstance(ergaenzt[-1], Fraction))
                and (marke == "x" or marke == "("
                     or isinstance(marke, Fraction))):
            ergaenzt.append("*")
        ergaenzt.append(marke)
    return ergaenzt


def _linear(text: str) -> tuple[Fraction, Fraction]:
    """Der Term als (a, b) mit der Bedeutung a·x + b — wirft sonst.

    Mehr als linear wird nicht verglichen: x², 1/x und zwei Unbekannte
    landen alle in der Zeichenketten-Normalform, nicht im Termvergleich.
    """
    marken = _marken(str(text))
    pos = 0

    def mal(a_links, b_links, a_rechts, b_rechts):
        if a_links == 0:
            return a_rechts * b_links, b_rechts * b_links
        if a_rechts == 0:
            return a_links * b_rechts, b_links * b_rechts
        raise _NichtVergleichbar("nicht linear")

    def summe():
        nonlocal pos
        a, b = produkt()
        while pos < len(marken) and marken[pos] in ("+", "-"):
            op = marken[pos]
            pos += 1
            ra, rb = produkt()
            a, b = (a + ra, b + rb) if op == "+" else (a - ra, b - rb)
        return a, b

    def produkt():
        nonlocal pos
        a, b = faktor()
        while pos < len(marken) and marken[pos] in ("*", "/"):
            op = marken[pos]
            pos += 1
            ra, rb = faktor()
            if op == "*":
                a, b = mal(a, b, ra, rb)
            else:
                if ra != 0 or rb == 0:
                    raise _NichtVergleichbar("durch x oder null")
                a, b = a / rb, b / rb
        return a, b

    def faktor():
        nonlocal pos
        if pos >= len(marken):
            raise _NichtVergleichbar("unvollständig")
        marke = marken[pos]
        if marke == "-":
            pos += 1
            a, b = faktor()
            return -a, -b
        if marke == "+":
            pos += 1
            return faktor()
        if marke == "(":
            pos += 1
            wert = summe()
            if pos >= len(marken) or marken[pos] != ")":
                raise _NichtVergleichbar("Klammer offen")
            pos += 1
            return wert
        if marke == "x":
            pos += 1
            return Fraction(1), Fraction(0)
        if isinstance(marke, Fraction):
            pos += 1
            return Fraction(0), marke
        raise _NichtVergleichbar(str(marke))

    wert = summe()
    if pos != len(marken):
        raise _NichtVergleichbar("Rest")
    return wert


def _linear_oder_none(text) -> tuple | None:
    try:
        return _linear(text)
    except (_NichtVergleichbar, ZeroDivisionError):
        return None


def _loesung_der_gleichung(a: Fraction, b: Fraction):
    """a·x + b = 0: der x-Wert, 'immer', 'nie' oder None."""
    if a == 0:
        return "immer" if b == 0 else "nie"
    return -b / a


def _gleichung(text: str):
    """Eine Gleichung als Normalform (a, b) von a·x + b = 0 — wirft sonst."""
    seiten = str(text).split("=")
    if len(seiten) != 2:
        raise _NichtVergleichbar(text)
    la, lb = _linear(seiten[0])
    ra, rb = _linear(seiten[1])
    return la - ra, lb - rb


# --------------------------------------------------------------------------
# Die Vergleiche
# --------------------------------------------------------------------------

def _gleiche_zahl(antwort, loesung) -> bool:
    """1/2, 2/4, 0.5, „0,5" und „12 : 4" sind derselbe Wert."""
    gegeben, gesucht = rechnen.wert(str(antwort)), rechnen.wert(str(loesung))
    return gegeben is not None and gegeben == gesucht


def _gleicher_term(antwort, loesung) -> bool:
    gegeben, gesucht = _linear_oder_none(antwort), _linear_oder_none(loesung)
    return gegeben is not None and gegeben == gesucht


def _gleiche_gleichung(antwort, loesung) -> bool:
    """Gleiche Loesungsmenge: „x = 5" und „5 = x" sind dieselbe Aussage."""
    try:
        a_l, b_l = _gleichung(antwort)
    except _NichtVergleichbar:
        # Keine Gleichung als Antwort — „5" auf „x = 5" behandelt
        # `_wert_auf_gleichung` separat.
        return False
    try:
        a_r, b_r = _gleichung(loesung)
    except _NichtVergleichbar:
        # Umgekehrt: erwartet „5" (der Wert), gegeben „x = 5".
        wert_antwort = _loesung_der_gleichung(a_l, b_l)
        loesung_wert = _linear_oder_none(loesung)
        return (isinstance(wert_antwort, Fraction)
                and loesung_wert is not None
                and loesung_wert[0] == 0
                and loesung_wert[1] == wert_antwort)
    links = _loesung_der_gleichung(a_l, b_l)
    rechts = _loesung_der_gleichung(a_r, b_r)
    return links == rechts


def _wert_auf_gleichung(antwort, loesung) -> bool:
    """„5" auf „x = 5": der nackte Wert als Loesung der Gleichung."""
    try:
        a_r, b_r = _gleichung(loesung)
    except _NichtVergleichbar:
        return False
    wert = _loesung_der_gleichung(a_r, b_r)
    gegeben = _linear_oder_none(antwort)
    return (isinstance(wert, Fraction)
            and gegeben is not None
            and gegeben[0] == 0
            and gegeben[1] == wert)


def _gleicher_text(antwort, loesung) -> bool:
    links, rechts = normalisiere(antwort), normalisiere(loesung)
    return bool(links) and links == rechts


_RUBRIK_ARTEN = {"begriffe", "rubric", "rubrik"}

#: Das Urteil einer Antwort: mehr als richtig/falsch, weil eine halbe
#: Erklärung eben keine falsche ist (Partial Correctness).
RICHTIG = "richtig"
TEILWEISE = "teilweise"
FALSCH = "falsch"


def _wort_treffer(begriff: str, text: str) -> bool:
    """Steht der geforderte Begriff als eigenes Wort in der Antwort?

    Der Begriff ist ein Wortanfang: „dativ" trifft „Dativobjekt" genauso
    wie „Dativ-Objekt", „herstell" trifft „herstellt" und „herstellst" —
    Flexion ist keine andere Antwort. Was am Wortanfang nicht steht,
    zählt nicht: „ist" bleibt in „bist" unsichtbar.
    """
    if not begriff or not text:
        return False
    return bool(re.search(r"(?<![a-z0-9])" + re.escape(begriff), text))


def _rubrik_bewerten(antwort: str, rubrik: dict) -> dict:
    """Begriffe zaehlen, die eine vollstaendige Antwort nennen muss.

    `mindestens` ist die Schwelle fuer „richtig"; darunter, aber ueber null,
    ist die Antwort „teilweise" — das Kind hat schon etwas erkannt, nur
    fehlt ein Stueck. Die Liste der fehlenden Begriffe geht mit, damit
    der Unterricht genau dieses Stueck nachholt statt von vorn zu beginnen.
    """
    gruppen = []
    for eintrag in (rubrik.get("begriffe") or []):
        # Ein Eintrag ist ein Begriff — oder eine Liste gleichwertiger
        # Schreibweisen, von denen eine genuegt (Flexion, Synonyme).
        if isinstance(eintrag, (list, tuple)):
            varianten = [str(b).strip() for b in eintrag if str(b).strip()]
            if varianten:
                gruppen.append(varianten)
        elif str(eintrag).strip():
            gruppen.append([str(eintrag).strip()])
    if not gruppen:
        return {"urteil": FALSCH, "fehlende": [], "hinweis": None}
    text = normalisiere_thema(antwort)
    fehlende = [varianten[0] for varianten in gruppen
                if not any(_wort_treffer(normalisiere_thema(w), text)
                           for w in varianten)]
    gefunden = len(gruppen) - len(fehlende)
    schwelle = int(rubrik.get("mindestens") or len(gruppen))
    hinweise = rubrik.get("hinweise") or {}
    if gefunden >= schwelle:
        return {"urteil": RICHTIG, "fehlende": [], "hinweis": None}
    if gefunden > 0:
        return {"urteil": TEILWEISE, "fehlende": fehlende,
                "hinweis": hinweise.get("teilweise")}
    return {"urteil": FALSCH, "fehlende": fehlende,
            "hinweis": hinweise.get("fehlt") or hinweise.get("misconception")}


def bewerte(antwort: str | None, loesung: str | None,
            antwort_art: str | None = None,
            rubrik: dict | None = None) -> dict:
    """Bewertet eine Antwort: richtig / teilweise / falsch.

    Wirft nie — wie `check_answer` ist jede unklare Eingabe bestenfalls
    teilweise. Hat die Aufgabe eine Begriffs-Rubrik (Vertrag 1.5), zaehlt
    die Abdeckung; ohne Rubrik bleibt es beim Zweiwert-Urteil des
    bisherigen Vergleichs.
    """
    try:
        art = (antwort_art or "").strip().lower()
        if rubrik and (not art or art in _RUBRIK_ARTEN):
            return _rubrik_bewerten(antwort or "", rubrik)
        urteil = RICHTIG if _check(antwort, loesung, antwort_art) else FALSCH
        return {"urteil": urteil, "fehlende": [], "hinweis": None}
    except Exception:
        return {"urteil": FALSCH, "fehlende": [], "hinweis": None}


def check_answer(antwort: str | None, loesung: str | None,
                 antwort_art: str | None = None,
                 rubrik: dict | None = None) -> bool:
    """Ist die Antwort auf diese Aufgabe fachlich richtig?

    Wirft nie: eine nicht vergleichbare Eingabe ist einfach falsch oder
    faellt auf den Zeichenkettenvergleich zurueck. Eine leere Antwort ist
    nie richtig.
    """
    return bewerte(antwort, loesung, antwort_art, rubrik)["urteil"] == RICHTIG


def _check(antwort: str | None, loesung: str | None,
           antwort_art: str | None) -> bool:
    if not antwort or not loesung:
        return False
    art = (antwort_art or "").strip().lower()
    hat_gleich = "=" in str(antwort) or "=" in str(loesung)
    hat_variable = any(c.isalpha() for c in str(antwort) + str(loesung))

    if art in _TEXT:
        return _gleicher_text(antwort, loesung)
    if art in _GLEICHUNGEN or (not art and hat_gleich):
        return (_gleiche_gleichung(antwort, loesung)
                or _wert_auf_gleichung(antwort, loesung)
                or _gleicher_text(antwort, loesung))
    if art in _TERME or (not art and hat_variable):
        return (_gleicher_term(antwort, loesung)
                or _gleicher_text(antwort, loesung))
    if art in _ZAHLEN or not art:
        return (_gleiche_zahl(antwort, loesung)
                or _gleicher_term(antwort, loesung)
                or _gleicher_text(antwort, loesung))
    return _gleicher_text(antwort, loesung)
