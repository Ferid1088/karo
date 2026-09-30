"""Acceptance and privacy tests for "Meine Welt" V2."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from .conftest import csrf_from, make_jpeg
from .test_woche import family, role


@pytest.fixture
def welt(family):
    from app.welten import media, store, world_db
    return family, store, media, world_db


def activate(welt, age_band="10-11", photos=True, audio=True):
    family, store, *_ = welt
    role(family, "parent")
    page = family[0].get("/welten/eltern")
    token = csrf_from(page.text)
    data = {"_csrf": token, "age_band": age_band}
    if photos:
        data["allow_photos"] = "1"
    if audio:
        data["allow_audio"] = "1"
    response = family[0].post(
        "/welten/eltern/freigabe", data=data, follow_redirects=False)
    assert response.status_code == 303, response.text[:800]
    role(family, "child")
    assert store.settings()["enabled"] == 1


def post_form(family, path, data=None, files=None, token_page=None):
    page = family[0].get(token_page or path)
    token = csrf_from(page.text)
    payload = {"_csrf": token, **(data or {})}
    return family[0].post(
        path, data=payload, files=files, follow_redirects=False)


def future_day(world_db, days=30):
    day = dt.date.fromisoformat(world_db.today()) + dt.timedelta(days=days)
    return day.isoformat()


def audio_bytes(size=700):
    return b"\x1aE\xdf\xa3" + (b"\x00" * max(0, size - 4))


def test_personal_world_database_is_separate_from_learning_database(welt):
    family, store, media, world_db = welt
    assert world_db.db_path() != family[1].data / "karo.db"
    assert world_db.db_path().parent.name == "meine-welt-private"
    tables = {
        row["name"] for row in family[1].db.q(
            "SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "world_entry" not in tables
    world_tables = {
        row["name"] for row in world_db.q(
            "SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"world_settings", "world_entry", "world_media", "world_capsule"} <= world_tables


def test_child_is_locked_until_parent_approval(welt):
    family, store, *_ = welt
    role(family, "child")
    page = family[0].get("/welten")
    assert page.status_code == 200
    assert "Elternteil" in page.text
    assert store.settings()["enabled"] == 0
    assert family[0].get("/welten/festhalten").status_code == 403

    activate(welt)
    page = family[0].get("/welten")
    assert "Heute für dich" in page.text
    assert "ohne KI" in page.text


def test_parent_settings_are_not_available_to_child(welt):
    family = welt[0]
    role(family, "child")
    assert family[0].get("/welten/eltern").status_code == 403
    response = family[0].post(
        "/welten/eltern/freigabe",
        data={"_csrf": "test-token", "age_band": "10-11"},
        follow_redirects=False,
    )
    assert response.status_code == 403


def test_discovery_is_deterministic_and_does_not_call_llm(welt, fake_llm):
    family = welt[0]
    activate(welt, age_band="12-13")
    before = len(fake_llm.calls)
    first = family[0].get("/welten/entdecken")
    second = family[0].get("/welten/entdecken")
    assert first.status_code == second.status_code == 200
    assert first.text == second.text
    assert len(fake_llm.calls) == before
    assert "Woher wissen wir das?" in first.text


def test_reflection_is_one_editable_answer_per_day(welt):
    family, store, *_ = welt
    activate(welt)
    home = family[0].get("/welten")
    token = csrf_from(home.text)
    from app.welten import content as editorial
    expected = editorial.daily_reflection(
        store.settings()["age_band"],
        dt.date.fromisoformat(welt[3].today()),
    )
    r = family[0].post(
        "/welten/nachdenken",
        data={"_csrf": token, "prompt_id": expected.id, "text": "Heute traue ich mich mehr."},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert store.reflection_for_day()["text"] == "Heute traue ich mich mehr."


def test_photo_is_reencoded_private_and_exif_free(welt, tmp_path):
    family, store, media, world_db = welt
    activate(welt)
    photo = make_jpeg(tmp_path / "original.jpg", size=(1200, 900))
    response = post_form(
        family,
        "/welten/festhalten",
        data={"mood": "besonders", "text": "Ein Foto."},
        files=[("photos", ("original.jpg", photo.read_bytes(), "image/jpeg"))],
    )
    assert response.status_code == 303, response.text[:800]
    moment = store.moment_for_day()
    rows = store.media_for_entry(moment["id"])
    assert len(rows) == 1
    row = rows[0]
    assert row["mime_type"] == "image/webp"
    assert row["storage_key"].endswith(".webp")
    assert not row["storage_key"].startswith("/")
    stored = media.path_for(row["storage_key"])
    assert stored.is_file()
    assert "meine-welt-private" in str(stored)

    served = family[0].get(f"/welten/media/{row['token']}")
    assert served.status_code == 200
    assert served.headers["content-type"].startswith("image/webp")
    assert "no-store" in served.headers["cache-control"]


def test_two_photo_limit_is_shared_with_time_capsules(welt, tmp_path):
    family, store, media, world_db = welt
    activate(welt)
    photo = make_jpeg(tmp_path / "a.jpg", size=(600, 600)).read_bytes()
    response = post_form(
        family,
        "/welten/festhalten",
        data={"text": "Zwei Fotos."},
        files=[
            ("photos", ("a.jpg", photo, "image/jpeg")),
            ("photos", ("b.jpg", photo, "image/jpeg")),
        ],
    )
    assert response.status_code == 303
    assert store.usage_today()["photos_left"] == 0

    response = post_form(
        family,
        "/welten/zeitkapseln",
        token_page="/welten/zeitkapseln",
        data={"title": "Später", "text": "", "opens_on": future_day(world_db)},
        files=[("photos", ("c.jpg", photo, "image/jpeg"))],
    )
    assert response.status_code == 303
    assert len(store.capsules()) == 0


def test_audio_limit_is_shared_and_no_speech_recognition_is_used(welt):
    family, store, media, world_db = welt
    activate(welt)
    first = post_form(
        family,
        "/welten/zeitkapseln",
        token_page="/welten/zeitkapseln",
        data={
            "title": "Audio eins", "text": "", "opens_on": future_day(world_db, 20),
            "audio_duration": "40",
        },
        files=[("audio", ("aufnahme.webm", audio_bytes(), "audio/webm"))],
    )
    assert first.status_code == 303
    assert store.usage_today()["audio_seconds_left"] == 20

    second = post_form(
        family,
        "/welten/zeitkapseln",
        token_page="/welten/zeitkapseln",
        data={
            "title": "Audio zwei", "text": "", "opens_on": future_day(world_db, 25),
            "audio_duration": "21",
        },
        files=[("audio", ("aufnahme.webm", audio_bytes(), "audio/webm"))],
    )
    assert second.status_code == 303
    assert len(store.capsules()) == 1

    js = (Path(__file__).parents[1] / "app" / "static" / "meine-welt.js").read_text()
    assert "SpeechRecognition" not in js
    assert "webkitSpeechRecognition" not in js


def test_locked_capsule_never_sends_secret_text_or_media(welt):
    family, store, media, world_db = welt
    activate(welt)
    response = post_form(
        family,
        "/welten/zeitkapseln",
        token_page="/welten/zeitkapseln",
        data={
            "title": "Geheim", "text": "DIESER INHALT MUSS GESPERRT BLEIBEN",
            "opens_on": future_day(world_db, 60),
            "audio_duration": "10",
        },
        files=[("audio", ("aufnahme.webm", audio_bytes(), "audio/webm"))],
    )
    assert response.status_code == 303
    item = store.capsules()[0]
    row = store.media_for_capsule(item["id"])[0]

    page = family[0].get(f"/welten/zeitkapseln/{item['id']}")
    assert page.status_code == 200
    assert "DIESER INHALT MUSS GESPERRT BLEIBEN" not in page.text
    assert "Der Inhalt wird vorher nicht an den Browser ausgeliefert" in page.text
    assert family[0].get(f"/welten/media/{row['token']}").status_code == 404


def test_world_pages_have_private_cache_and_csp_and_no_google_fonts(welt):
    family = welt[0]
    activate(welt)
    response = family[0].get("/welten")
    assert "no-store" in response.headers["cache-control"]
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "fonts.googleapis.com" not in response.text
    assert "fonts.gstatic.com" not in response.text


def test_parent_can_delete_world_without_touching_learning_database(welt, tmp_path):
    family, store, media, world_db = welt
    activate(welt)
    photo = make_jpeg(tmp_path / "delete.jpg", size=(500, 500)).read_bytes()
    post_form(
        family,
        "/welten/festhalten",
        data={"text": "Wird gelöscht."},
        files=[("photos", ("delete.jpg", photo, "image/jpeg"))],
    )
    row = store.media_for_entry(store.moment_for_day()["id"])[0]
    path = media.path_for(row["storage_key"])
    assert path.exists()

    role(family, "parent")
    page = family[0].get("/welten/eltern")
    token = csrf_from(page.text)
    response = family[0].post(
        "/welten/eltern/alles-loeschen",
        data={"_csrf": token, "confirm": "ALLES LÖSCHEN"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert store.settings()["enabled"] == 0
    assert store.moment_for_day() is None
    assert not path.exists()
    assert (family[1].data / "karo.db").exists()


def test_world_content_is_closed_to_the_parent_password(welt):
    """"Meine Welt" ist das Tagebuch des Kindes. Wer mit dem Eltern-Passwort
    angemeldet ist, kommt an den Inhalt nicht heran — nur an Freigabe,
    Export und Loeschen."""
    family = welt[0]
    activate(welt)
    role(family, "parent")
    for pfad in ("/welten", "/welten/entdecken", "/welten/jahr",
                 "/welten/zeitkapseln", "/welten/festhalten"):
        assert family[0].get(pfad).status_code == 403, pfad
    assert family[0].post(
        "/welten/nachdenken", data={"_csrf": "x", "text": "hallo"},
        follow_redirects=False).status_code == 403

    # Was Eltern brauchen, bleibt offen — und steht im Elternbereich.
    seite = family[0].get("/welten/eltern")
    assert seite.status_code == 200
    assert 'data-ui-area="parent"' in seite.text
    assert 'href="/welten/jahr"' not in seite.text
    assert family[0].get("/welten/datenschutz").status_code == 200

    # Und im Kinderbereich taucht der Weg dorthin fuer Eltern nicht auf.
    heute = family[0].get("/")
    assert heute.status_code == 200
    assert 'href="/welten"' not in heute.text


def test_child_still_reaches_its_own_world(welt):
    family = welt[0]
    activate(welt)
    role(family, "child")
    for pfad in ("/welten", "/welten/entdecken", "/welten/jahr",
                 "/welten/zeitkapseln"):
        assert family[0].get(pfad).status_code == 200, pfad
    assert 'href="/welten"' in family[0].get("/").text
