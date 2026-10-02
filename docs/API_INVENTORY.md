# Karo — Externe APIs und Integrationen

Nur Integrationen, die im Code tatsächlich vorhanden sind. Keine Annahmen.

---

## Übersicht

| Name | Typ | Richtung | Auth | aktiv/optional |
|---|---|---|---|---|
| Devin API | LLM-Provider | ausgehend HTTPS | `DEVIN_API_KEY` (Bearer, nur aus Umgebung) | einziger KI-Anbieter |
| Curriculum-Dienst | HTTP-Service | ausgehend | `curriculum_key` (Header) | optional — nur wenn konfiguriert |
| NotebookLM-CLI | lokales Werkzeug | ausgehend Google | Google-Session in `NOTEBOOKLM_HOME` | optional — nur wenn eingerichtet |
| Tesseract | lokales Werkzeug | lokal | — | Teil des Images |
| Tesseract.js (Browser) | lokale WASM | im Browser | — | Teil der Upload-Seite |
| Piper TTS | lokales Werkzeug | lokal | — | optional — wenn Binary vorhanden |
| ffmpeg | lokales Werkzeug | lokal | — | Teil des Images (wenn `KARO_MIT_MP4`) |
| Xvfb / noVNC | lokale Werkzeuge | lokal | — | für NotebookLM-Login |

**Nicht vorhanden:** OpenAI, OpenRouter, ElevenLabs, Google-OAuth
(kein OAuth-Client im Code), Google Drive API. „Google" kommt nur über die
NotebookLM-CLI hinein, die selbst eine Google-Browsersession pflegt.

---

## 1. Devin API

| | |
|---|---|
| Typ | LLM-Provider, asynchron per Session |
| Richtung | ausgehend HTTPS |
| Verwendung | Lernserien, Fachklassifikation, Materialanalyse, Recherche-Ranking, Gegenprüfungen |
| Base URL | `ops.devin_base_url` (`https://api.devin.ai/v1`) |
| Ablauf | `POST /sessions` → Auftrag wird mit `not_before` geparkt (`AIPending` → `jobs.Deferred`) → `GET /sessions/{id}` bis `structured_output` da ist |
| Auth | `Authorization: Bearer $DEVIN_API_KEY` — nur aus der Umgebung, nie in `config.json` |
| Fingerprint | SHA-256 aus Provider+Prompts → Tabelle `provider_session`; identische Aufrufe teilen die Session, geparkte Jobs finden sie wieder |
| Timeout | `ops.devin_http_timeout_seconds` (60 s) pro Anfrage; Session-Höchstalter `devin_max_session_seconds` (7200 s) |
| Warten | `ops.devin_poll_seconds` (300 s) zwischen Polls — verbraucht keinen Job-Versuch |
| Fehler | `blocked` → ein Nudge per `POST /sessions/{id}/message`; abgelaufen/gescheitert → max. `devin_max_restarts` (1) Neustart, sonst `AIError` im Job |
| Rausgehende Daten | Prompts mit Aufgabentexten/Themen; **keine Bilder** (Privacy-Test `test_keine_bilder_an_modelle`) — die Schnittstelle hat gar keinen Bild-Parameter |
| Personenbezogen | Lernstände, Themen — kein Name, kein Foto |
| Code | `app/ai/devin.py` (Provider), `app/ai/client.py` (`AIClient`-Fassade + `llm_call`-Audit), `app/ai/base.py` (Fehler/`AIPending`) |

## 2. Curriculum-Dienst

| | |
|---|---|
| Typ | externer HTTP-Dienst |
| Richtung | ausgehend |
| Verwendung | Familien bestellen neue Themen beim Lehrplan-Dienst; Tagesbudget `family_daily_topics` |
| Base URL | `Config.curriculum_url` / `KARO_CURRICULUM_URL` |
| Auth | `Config.curriculum_key` / `KARO_CURRICULUM_KEY` |
| Timeout | `ops.curriculum_request_timeout_seconds` (8 s) |
| Warten | `ops.curriculum_max_wait_seconds` (24 h), Poll `curriculum_poll_seconds` (300 s), Fehler-Rückzug `curriculum_error_retry_seconds` (15 s) |
| Antwortdeckel | `curriculum_max_response_bytes` (2 MB) |
| Redirects | abgelehnt (`_NoRedirect`); HTTP nur für `localhost`, `127.0.0.1`, `::1`, `curriculum-api` |
| Rausgehende Daten | Themenschlüssel, Fach — **keine** Familien-/Kind-Kennung (Konzept in `services/topic_budget.py`) |
| Personenbezogen | keine |
| Code | `app/adaptiv/curriculum_dienst.py` |

## 3. NotebookLM-CLI

| | |
|---|---|
| Typ | lokale CLI, die intern Google/NotebookLM ansteuert |
| Richtung | lokal → ausgehend Google |
| Verwendung | Audio-/Video-Artefakte aus Lernthemen |
| Home | `NOTEBOOKLM_HOME` bzw. `KARO_DATA_DIR/notebooklm` |
| Auth | Google-Browsersession (VNC/Xvfb-Login), kein API-Key im Code |
| Timeouts/Retries | `ops.notebooklm_*` (siehe CONFIG.md) |
| Rausgehende Daten | Themen-Texte, die die Familie schickt |
| Personenbezogen | abhängig vom Familienkonto |
| Code | `app/media/notebooklm.py` |

## 4. Lokale Werkzeuge

| Name | Zweck | Konfiguration | Code |
|---|---|---|---|
| Tesseract | Server-OCR-Fallback | `ocr_timeout_seconds`, `ocr_sprachen`, `ocr_max_pdf_seiten` | `app/blatt_text.py` |
| Tesseract.js | Browser-OCR | `browser_ocr_*` via `data-*`-Attribute | `app/static/blatt-lesen.js` |
| Piper | Sprachausgabe | `tts_timeout_seconds` | `app/media/tts.py` |
| ffmpeg | Video-Erzeugung | `video_timeout_seconds` | `app/media/video.py` |
| Xvfb/noVNC | NotebookLM-Login | `notebooklm_vnc_*`, `notebooklm_novnc_*` | `app/media/notebooklm.py` |

## 5. Eingebettete Inhalte (keine API)

`app/welten/content.py` enthält eine kuratierte Liste öffentlicher Bildungs-URLs
(NASA, MedlinePlus, USFS usw.) als Lesestoff für „Meine Welt". Das sind Links,
keine Anbindungen — keine Auth, keine Calls.

---

## Zählung

```text
Externe APIs/Integrationen insgesamt:   3   (Devin API, Curriculum, NotebookLM)
OAuth-Integrationen:                    1   (NotebookLM-Browsersession)
LLM-/AI-Provider:                       1   (Devin API — einziger Anbieter)
lokale externe Werkzeuge:               5   (Tesseract, Tesseract.js, Piper, ffmpeg, Xvfb/noVNC)
optionale Integrationen:                3   (Curriculum, NotebookLM, Piper)
aktive Standardintegrationen:           2   (Devin API + Tesseract; Rest erst nach Einrichtung)
```

```text
AI: 1 · Speech: 1 (Piper) · Storage: 0 · Auth: 0 · Curriculum: 1 ·
Media: 3 (NotebookLM, ffmpeg, Xvfb) · Monitoring: 0 · Other: 0
```
