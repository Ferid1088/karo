"""Tests der Flaggenregel.

Die wichtigste Zusage des Produkts steht in compute_flag(): eine einzelne
falsche Antwort aendert die Flagge nie. Genau das wird hier bewiesen.
"""

from app.domain import Answer, Flag, Rule, compute_flag


def a(tag: str, richtig: bool, err: str | None = None, seq: int = 0) -> Answer:
    return Answer(tag=tag, richtig=richtig, fehlertyp=err,
                  created_at=tag, seq=seq)


def blatt(tag: str, richtig: int, falsch: int = 0, err: str = "rechenfehler",
          start: int = 0) -> list[Answer]:
    """Ein Arbeitsblatt: mehrere Antworten am selben Tag."""
    heraus, n = [], start
    for _ in range(richtig):
        n += 1
        heraus.append(a(tag, True, None, n))
    for _ in range(falsch):
        n += 1
        heraus.append(a(tag, False, err, n))
    return heraus


# --------------------------------------------------------------------------
# Die Kernzusage
# --------------------------------------------------------------------------

def test_eine_falsche_antwort_erzeugt_kein_rot():
    """Der wichtigste Test des Projekts."""
    o = [a("2026-09-01", True, seq=1), a("2026-09-02", True, seq=2),
         a("2026-09-03", False, "konzeptfehler", 3)]
    assert compute_flag(o).flag == Flag.GELB.value


def test_eine_richtige_antwort_erzeugt_kein_gruen():
    assert compute_flag([a("2026-09-01", True, seq=1)]).flag == Flag.WEISS.value


def test_leere_liste_ist_weiss():
    r = compute_flag([])
    assert r.flag == Flag.WEISS.value
    assert r.antworten == 0


# --------------------------------------------------------------------------
# rot
# --------------------------------------------------------------------------

def test_zwei_konzeptfehler_im_fenster_ergeben_rot():
    o = [a("2026-09-01", False, "konzeptfehler", 1),
         a("2026-09-02", True, None, 2),
         a("2026-09-03", False, "regel_vergessen", 3)]
    assert compute_flag(o).flag == Flag.ROT.value


def test_zwei_rechenfehler_ergeben_kein_rot():
    """Ausfuehrungsfehler sind kein Wissensproblem."""
    o = [a("2026-09-01", False, "rechenfehler", 1),
         a("2026-09-02", False, "fluechtigkeit", 2),
         a("2026-09-03", False, "rechenfehler", 3)]
    assert compute_flag(o).flag == Flag.GELB.value


def test_alte_konzeptfehler_fallen_aus_dem_fenster():
    o = [a("2026-09-01", False, "konzeptfehler", 1),
         a("2026-09-02", False, "konzeptfehler", 2)] + [
        a(f"2026-09-0{d}", True, None, d + 2) for d in (3, 4, 5, 6, 7)]
    assert compute_flag(o).flag == Flag.GRUEN.value


# --------------------------------------------------------------------------
# gruen — in Tagen gerechnet, nicht in Zeilen
# --------------------------------------------------------------------------

def test_zwei_saubere_uebungstage_ergeben_gruen():
    """Der beworbene Kreislauf muss sich schliessen koennen.

    Sechs richtige Aufgaben auf einem Blatt, dann sechs auf einem zweiten:
    genau der Weg, den Karo selbst vorschlaegt.
    """
    o = blatt("2026-09-01", 6) + blatt("2026-09-05", 6, start=100)
    r = compute_flag(o)
    assert r.flag == Flag.GRUEN.value
    assert "fehlerfrei" in r.begruendung


def test_ein_einziges_blatt_reicht_nicht_fuer_gruen():
    """Zehn richtige Antworten an einem Tag sind noch kein Beleg."""
    assert compute_flag(blatt("2026-09-01", 10)).flag == Flag.GELB.value


def test_fehler_am_letzten_uebungstag_verhindert_gruen():
    o = blatt("2026-09-01", 6) + blatt("2026-09-05", 5, 1, "konzeptfehler",
                                       start=100)
    assert compute_flag(o).flag == Flag.GELB.value


def test_fehler_am_selben_tag_versteckt_sich_nicht():
    """Ein Konzeptfehler darf nicht hinter hoeheren Aufgabennummern verschwinden."""
    o = [a("2026-09-01", True, None, 1),
         a("2026-09-01", False, "konzeptfehler", 2),
         a("2026-09-03", True, None, 3), a("2026-09-03", True, None, 4)]
    assert compute_flag(o).flag == Flag.GELB.value


def test_gruen_faellt_nach_einem_fehler_zurueck():
    o = [a("2026-09-01", True, seq=1), a("2026-09-02", True, seq=2),
         a("2026-09-03", True, seq=3),
         a("2026-09-04", False, "rechenfehler", 4)]
    assert compute_flag(o).flag == Flag.GELB.value


# --------------------------------------------------------------------------
# Reihenfolge und Sonderfaelle
# --------------------------------------------------------------------------

def test_reihenfolge_der_eingabe_aendert_nichts():
    o = [a("2026-09-01", True, seq=1), a("2026-09-03", True, seq=2),
         a("2026-09-05", True, seq=3)]
    assert compute_flag(o).flag == compute_flag(list(reversed(o))).flag


def test_reihenfolge_innerhalb_eines_tages_aendert_nichts():
    richtig = a("2026-09-01", True, None, 1)
    falsch = a("2026-09-01", False, "konzeptfehler", 2)
    tag2 = [a("2026-09-03", True, None, 3), a("2026-09-03", True, None, 4)]
    assert (compute_flag([richtig, falsch] + tag2).flag
            == compute_flag([falsch, richtig] + tag2).flag)


def test_nicht_bearbeitet_zaehlt_nicht_als_evidenz():
    o = [a(f"2026-09-0{d}", False, "nicht_bearbeitet", d) for d in (1, 2, 3)]
    r = compute_flag(o)
    assert r.flag == Flag.WEISS.value
    assert r.antworten == 0


def test_dominanter_fehler_wird_ermittelt():
    o = [a("2026-09-01", False, "rechenfehler", 1),
         a("2026-09-02", False, "rechenfehler", 2),
         a("2026-09-03", False, "fluechtigkeit", 3)]
    assert compute_flag(o).haupt_fehler == "rechenfehler"


def test_strengere_regel_verlangt_mehr():
    o = blatt("2026-09-01", 2) + blatt("2026-09-03", 2, start=50)
    assert compute_flag(o).flag == Flag.GRUEN.value
    streng = Rule(gruen_richtige=6, gruen_tage=3)
    assert compute_flag(o, streng).flag == Flag.GELB.value
