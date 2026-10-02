"""Tests für die zentrale Betriebskonfiguration `config.ops()`.

Geprüft wird:
  * Defaults laden
  * Env-Overrides greifen (KARO_<FELD> plus historische Aliase)
  * ungültige Werte werden mit OpsInvalid abgelehnt
  * die Modul-Aliase zeigen auf dieselbe Quelle (Single Source of Truth)
"""

from __future__ import annotations

import pytest

from app import config


@pytest.fixture(autouse=True)
def _ops_frisch(monkeypatch):
    """Jeder Test bekommt ein frisches ops() — kein Env-Streu zwischen Tests."""
    for f in config.fields(config.Ops):
        monkeypatch.delenv(config._ops_env_name(f.name), raising=False)
    config.ops.cache_clear()
    yield
    config.ops.cache_clear()


def test_defaults_laden():
    o = config.ops()
    assert o.upload_max_bytes == 25 * 1024 * 1024
    assert o.jobs_max_attempts == 3
    assert o.paket_max_seiten == 10
    assert o.log_level == "INFO"


def test_env_override_ganzzahl(monkeypatch):
    monkeypatch.setenv("KARO_PAKET_MAX_SEITEN", "5")
    config.ops.cache_clear()
    assert config.ops().paket_max_seiten == 5


def test_env_override_alias(monkeypatch):
    monkeypatch.setenv("KARO_LOG_LEVEL", "DEBUG")
    config.ops.cache_clear()
    assert config.ops().log_level == "DEBUG"


def test_env_override_boolean(monkeypatch):
    monkeypatch.setenv("KARO_HTTPS_ONLY", "1")
    config.ops.cache_clear()
    assert config.ops().https_only is True


def test_env_override_tuple(monkeypatch):
    monkeypatch.setenv("KARO_WIEDERHOLUNG_ABSTAENDE", "1,7,30")
    config.ops.cache_clear()
    assert config.ops().wiederholung_abstaende == (1, 7, 30)


def test_ungueltiger_wert_abgelehnt(monkeypatch):
    monkeypatch.setenv("KARO_PAKET_MAX_SEITEN", "keine-zahl")
    config.ops.cache_clear()
    with pytest.raises(config.OpsInvalid, match="KARO_PAKET_MAX_SEITEN"):
        config.ops()


def test_negativer_wert_abgelehnt(monkeypatch):
    monkeypatch.setenv("KARO_UPLOAD_MAX_BYTES", "-1")
    config.ops.cache_clear()
    with pytest.raises(config.OpsInvalid):
        config.ops()


def test_ungueltiger_log_level_abgelehnt(monkeypatch):
    monkeypatch.setenv("KARO_LOG_LEVEL", "FLAPPERT")
    config.ops.cache_clear()
    with pytest.raises(config.OpsInvalid):
        config.ops()


def test_leerer_string_abgelehnt(monkeypatch):
    monkeypatch.setenv("KARO_OCR_SPRACHEN", "")
    config.ops.cache_clear()
    # Leerer Override wird ignoriert (leere Env = nicht gesetzt)
    assert config.ops().ocr_sprachen == "deu+eng"


def test_port_bereich_validiert(monkeypatch):
    monkeypatch.setenv("KARO_NOTEBOOKLM_VNC_RFB_PORT", "70000")
    config.ops.cache_clear()
    with pytest.raises(config.OpsInvalid):
        config.ops()


def test_groessenverhaeltnis_validiert(monkeypatch):
    monkeypatch.setenv("KARO_MAX_BODY_BYTES", str(1024))
    config.ops.cache_clear()
    with pytest.raises(config.OpsInvalid, match="max_body_bytes"):
        config.ops()


def test_family_daily_topics_null_erlaubt(monkeypatch):
    """0 = kein Tageslimit für neue Themen — eine bewusste Bedeutung."""
    monkeypatch.setenv("KARO_FAMILY_DAILY_TOPICS", "0")
    config.ops.cache_clear()
    assert config.ops().family_daily_topics == 0


def test_modul_alias_ist_ops():
    """Modul-Konstanten sind nur Namen auf ops() — kein zweiter Default."""
    from app import jobs, security, material_paket
    o = config.ops()
    assert jobs.MAX_ATTEMPTS == o.jobs_max_attempts
    assert security.MAX_UPLOAD_BYTES == o.upload_max_bytes
    assert material_paket.MAX_SEITEN == o.paket_max_seiten


def test_zeitzone_zentral():
    import app.welten.world_db as world_db
    assert world_db.BERLIN is config.zeitzone()


def test_ops_enthaelt_keine_secrets():
    """Kein Ops-Feld darf nach Secret aussehen — die liegen in Config/config.json."""
    for f in config.fields(config.Ops):
        assert not any(s in f.name for s in (
            "api_key", "oauth", "secret", "password", "access_token",
            "refresh_token", "bearer")), f.name


def test_zeitzone_env_override(monkeypatch):
    monkeypatch.setenv("KARO_TIMEZONE", "Europe/Vienna")
    assert str(config.zeitzone()) == "Europe/Vienna"


def test_zeitzone_unbekannt_faellt_weich(monkeypatch):
    monkeypatch.setenv("KARO_TIMEZONE", "Mars/Olympus")
    assert str(config.zeitzone()) == "Europe/Berlin"
