"""Der ganze Klassenarbeits-Bereich steht auf exam_base — nichts erbt Lernen.

Zwei Prüfebenen: statisch (kein Klassenarbeits-Template verweist auf die
Lernbereich-Basis, deren Styles oder deren Klassen) und gerendert (jede
/klassenarbeit-Seite trägt exam-page ohne learning-ui; die geteilten
Sitzungs-Templates unter /klassenarbeit/{id}/lernen bekommen ihre Basis
injiziert, nicht geerbt).
"""
from __future__ import annotations

import pathlib
import re

from .test_app import einrichten

WURZEL = pathlib.Path(__file__).resolve().parent.parent

# Seiten des Klassenarbeitsbereichs — plus deren Basis und die exam-Partials.
KLASSENARBEIT_TEMPLATES = [
    "exam_base.html", "klassenarbeit_neu.html", "klassenarbeit_detail.html",
    "klassenarbeit_kalender.html", "klassenarbeit_kind.html",
    "klassenarbeit_einstufung.html", "klassenarbeit_material.html",
    "exam_simulation.html", "exam_rehearsal.html",
    "themenblatt_upload.html", "themenblatt_pruefen.html",
    "_exam_week.html", "_exam_monat.html",
]

VERBOTEN = (
    'extends "learning_base', "learning_base.html", "learning_ui",
    "learning-main", "learning-session", "/static/learning",
    "learn-form", "learn-two-col", "learn-heading", "learn-zweit-action",
    "learn-status", "learning-entry", "lernmaterial-",
    'href="/lernen', 'action="/lernen',
)


def test_klassenarbeit_templates_ohne_lernbereich():
    """Jedes Klassenarbeits-Template steht auf exam_base (oder base) und
    trägt keine Lernbereich-Abhängigkeit — weder Vererbung noch Klassen."""
    for name in KLASSENARBEIT_TEMPLATES:
        text = (WURZEL / "app/templates" / name).read_text()
        for verboten in VERBOTEN:
            assert verboten not in text, f"{name}: {verboten}"


def test_kein_template_erbt_learning_base_versehentlich():
    """learning_base darf nur noch von echten Lernbereich-Seiten kommen —
    nie von einer Seite, die unter /klassenarbeit gerendert wird. Die
    geteilten Sitzungs-Templates (adaptiv_*, learning_unavailable,
    learning_grade_warning) erben sie nicht: sie nehmen `basis` entgegen."""
    lernseiten = {"learning_new.html", "learning_topic_intro.html",
                  "learning_upload.html", "lernen_start.html",
                  "material_pruefen.html", "dashboard.html"}
    erbt = re.compile(r"extends\s+['\"]learning_base")
    for pfad in (WURZEL / "app/templates").glob("*.html"):
        if pfad.name in lernseiten:
            continue
        assert not erbt.search(pfad.read_text()), pfad.name


def _exam_asserts(html: str) -> None:
    """Klassenarbeits-Chrome: exam-page, kein Lernbereich irgendwo."""
    assert 'class="exam-page' in html
    assert "learning-ui" not in html
    assert "learning-main" not in html
    for sheet in ("learning.css", "learning-session.css",
                  "learning-exam.css", "learning-mascot.css"):
        assert f"/static/{sheet}" not in html, sheet


# --------------------------------------------------------------------------
# Jede Klassenarbeits-Seite rendert im eigenen Bereich
# --------------------------------------------------------------------------

def test_uebersicht_neu_kalender_im_exam_bereich(client, fake_llm, app_env):
    einrichten(client, fake_llm)
    for pfad in ("/klassenarbeit", "/klassenarbeit/neu",
                 "/klassenarbeit/kalender", "/klassenarbeit/themenblatt"):
        r = client.get(pfad)
        assert r.status_code == 200, pfad
        _exam_asserts(r.text)
        # Elternbereich: „Lernstand“ trägt den aktiven Hauptpunkt.
        assert re.search(r'href="/messung/fortschritt"[^>]*aria-current=page',
                         r.text), pfad


def test_detail_einstufung_vorbereitung_im_exam_bereich(client, fake_llm,
                                                       app_env):
    from app.services import exam
    einrichten(client, fake_llm)
    eid = exam.create_exam("2099-05-05", manual_topics="Brüche addieren",
                           subject="mathematik").exam_id
    for pfad in (f"/klassenarbeit/{eid}", f"/klassenarbeit/{eid}/einstufung",
                 f"/klassenarbeit/{eid}/lernen"):
        r = client.get(pfad)
        assert r.status_code == 200, pfad
        _exam_asserts(r.text)


def test_vorbereitungssitzung_teilt_template_nicht_chrome(client, fake_llm,
                                                        app_env):
    """Derselbe Sitzungsbildschirm unter /lernen/adaptiv trägt learning-ui,
    unter /klassenarbeit/{id}/lernen exam-page — die Basis wird injiziert."""
    from app.services import exam
    einrichten(client, fake_llm)
    app_env.config.update(adaptive_learning_enabled=True, learner_grade=6)
    eid = exam.create_exam("2099-05-05", manual_topics="Brüche addieren",
                           subject="mathematik").exam_id

    lernen = client.get("/lernen/adaptiv")
    assert lernen.status_code == 200
    assert 'class="learning-ui' in lernen.text
    assert "exam-page" not in lernen.text

    arbeit = client.get(f"/klassenarbeit/{eid}/lernen")
    assert arbeit.status_code == 200
    _exam_asserts(arbeit.text)
    # Der Exam-Kontext hält die Auswahl in der Prüfungsvorbereitung.
    assert "Prüfungsvorbereitung" in arbeit.text or "sitzung" in arbeit.text


# --------------------------------------------------------------------------
# Lernen bleibt unverändert auf seiner eigenen Basis
# --------------------------------------------------------------------------

def test_lernen_behält_learning_chrome(client, fake_llm, app_env):
    einrichten(client, fake_llm)
    r = client.get("/lernen")
    assert r.status_code == 200
    assert 'class="learning-ui' in r.text
    assert "exam-page" not in r.text
    assert "/static/learning.css" in r.text
    # Die Exam-Stylesheets gehören dem anderen Bereich.
    assert "/static/exam.css" not in r.text
    assert "/static/exam-detail.css" not in r.text

    r = client.get("/lernen/material")
    assert 'class="learning-ui' in r.text
    assert re.search(r'class="learning-entry"[^>]*aria-current=page', r.text)
