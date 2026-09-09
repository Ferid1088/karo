"""Tests für die Wiederholungslogik der NotebookLM-Anbindung.

Reine Einheitstests von `_voruebergehend()`/`_mit_wiederholung()` — ohne
Subprozess-Mocking, weil die eigentliche Behauptung ist: ein erkennbar
vorübergehender Fehler wird mehrfach versucht, ein dauerhafter nicht, und ein
Abbruch von Hand wirkt sofort, egal welcher Fehler gerade vorliegt.
"""

from __future__ import annotations

import pytest

from app.media import notebooklm as nlm


def test_voruebergehende_fehler_werden_erkannt():
    assert nlm._voruebergehend(
        nlm.NotebookLmUnavailable("HTTP 500 (server-error retries exhausted)"))
    assert nlm._voruebergehend(
        nlm.NotebookLmUnavailable("Rate limit exceeded, try again later"))
    assert nlm._voruebergehend(
        nlm.NotebookLmUnavailable("Connection reset by peer"))
    assert not nlm._voruebergehend(
        nlm.NotebookLmUnavailable("Es liegt keine gültige NotebookLM-Anmeldung vor."))
    assert not nlm._voruebergehend(nlm.Abgebrochen("Von Hand abgebrochen."))


def test_wiederholung_erholt_sich_von_voruebergehendem_fehler(monkeypatch):
    """Genau der Fall aus dem echten Test heute: ein einzelner HTTP-500 auf
    ADD_SOURCE, danach geht der gleiche Aufruf durch."""
    monkeypatch.setattr(nlm.time, "sleep", lambda s: None)
    versuche = []

    def aufruf():
        versuche.append(1)
        if len(versuche) < 2:
            raise nlm.NotebookLmUnavailable(
                "RPC ADD_SOURCE failed: HTTP 500 (server-error retries exhausted)")
        return {"ok": True}

    ergebnis = nlm._mit_wiederholung("test", aufruf)
    assert ergebnis == {"ok": True}
    assert len(versuche) == 2


def test_wiederholung_gibt_bei_dauerhaftem_fehler_sofort_auf(monkeypatch):
    """Fehlende Anmeldung aendert sich durch einen zweiten Versuch nicht —
    also wird auch keine Pause abgewartet."""
    def explodiere_bei_schlaf(_s):
        raise AssertionError("sollte bei einem dauerhaften Fehler nicht schlafen")
    monkeypatch.setattr(nlm.time, "sleep", explodiere_bei_schlaf)
    versuche = []

    def aufruf():
        versuche.append(1)
        raise nlm.NotebookLmUnavailable(
            "Es liegt keine gültige NotebookLM-Anmeldung vor.")

    with pytest.raises(nlm.NotebookLmUnavailable):
        nlm._mit_wiederholung("test", aufruf)
    assert len(versuche) == 1


def test_wiederholung_gibt_nach_max_versuchen_auf(monkeypatch):
    monkeypatch.setattr(nlm.time, "sleep", lambda s: None)
    versuche = []

    def aufruf():
        versuche.append(1)
        raise nlm.NotebookLmUnavailable("Connection reset by peer")

    with pytest.raises(nlm.NotebookLmUnavailable):
        nlm._mit_wiederholung("test", aufruf, versuche=3)
    assert len(versuche) == 3


def test_wiederholung_bricht_bei_abbruch_sofort_ab(monkeypatch):
    """Ein Abbruch von Hand gewinnt gegen jede Wiederholungslogik — auch bei
    einem sonst wiederholbaren Fehler."""
    def explodiere_bei_schlaf(_s):
        raise AssertionError("sollte bei einem Abbruch nicht schlafen")
    monkeypatch.setattr(nlm.time, "sleep", explodiere_bei_schlaf)
    versuche = []

    def aufruf():
        versuche.append(1)
        raise nlm.NotebookLmUnavailable("Connection reset by peer")

    with pytest.raises(nlm.Abgebrochen):
        nlm._mit_wiederholung("test", aufruf, versuche=5, abgebrochen=lambda: True)
    assert len(versuche) == 1


def test_vnc_verfuegbar_erkennt_fehlende_werkzeuge(monkeypatch):
    monkeypatch.setattr(nlm.shutil, "which", lambda name: None)
    assert nlm._vnc_verfuegbar() is False


def test_vnc_verfuegbar_erkennt_vorhandene_werkzeuge(monkeypatch):
    monkeypatch.setattr(nlm.shutil, "which", lambda name: f"/usr/bin/{name}")
    assert nlm._vnc_verfuegbar() is True


def test_tcp_offen_erkennt_geschlossenen_port():
    # Port 1 (tcpmux) ist auf einem normalen Rechner praktisch nie offen.
    assert nlm._tcp_offen("127.0.0.1", 1) is False


def test_ratenbegrenzung_wird_lesbar_uebersetzt():
    """Genau der Fall, an dem das heute in der echten App scheiterte: ein
    roher Logger-Mitschnitt mit mehreren Wiederholungsversuchen darf nicht
    unveraendert auf der Lerneinheit-Seite landen."""
    roh = (
        '14:15:59 ERROR [notebooklm._rpc_executor] [req=5731310e] '
        'RPC CREATE_ARTIFACT failed after 0.494s: RateLimitError '
        'rpc_code=USER_DISPLAYABLE_ERROR\n'
        '14:17:01 ERROR [notebooklm._rpc_executor] [req=8b289af1] '
        'RPC CREATE_ARTIFACT failed after 0.505s: RateLimitError '
        'rpc_code=USER_DISPLAYABLE_ERROR\n'
        '14:19:07 WARNING [notebooklm.middleware.tracing] [req=36999f65] '
        'rpc failed: RPC CREATE_ARTIFACT (TransportServerError)'
    )
    meldung = nlm._lesbare_fehlermeldung(roh, "generate", 1)
    assert "[notebooklm._rpc_executor]" not in meldung
    assert "[req=" not in meldung
    assert "Tageslimit" in meldung


def test_server_fehler_wird_lesbar_uebersetzt():
    meldung = nlm._lesbare_fehlermeldung(
        "RPC ADD_SOURCE failed: HTTP 500 (server-error retries exhausted)",
        "source", 1)
    assert "[notebooklm" not in meldung
    assert "Server-Fehler" in meldung


def test_unbekannter_fehler_verliert_wenigstens_logger_vorspann():
    meldung = nlm._lesbare_fehlermeldung(
        "10:00:00 ERROR [irgendein.modul] [req=abc123] Irgendwas Neues",
        "create", 1)
    assert meldung == "Irgendwas Neues"


def test_leerer_fehler_bekommt_generische_meldung():
    meldung = nlm._lesbare_fehlermeldung("", "download", 1)
    assert "download" in meldung
    assert "Code 1" in meldung


def test_tcp_offen_erkennt_offenen_port():
    import socket

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    try:
        assert nlm._tcp_offen("127.0.0.1", port) is True
    finally:
        server.close()
