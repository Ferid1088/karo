# Karo — Externe APIs und Integrationen

Nur Integrationen, die im Code tatsächlich vorhanden sind. Keine Annahmen.

---

## Übersicht

| Name | Typ | Richtung | Auth | aktiv/optional |
|---|---|---|---|---|
| KI-Anbieter (aktiv: `Config.ai_provider`) | LLM-Provider | ausgehend HTTPS | Bearer-Schlüssel des Adapters, nur aus Umgebung | genau ein aktiver Anbieter |
| ↳ Devin API | LLM-Provider-Adapter | ausgehend HTTPS | `DEVIN_API_KEY` | Default-Anbieter |
| ↳ OpenRouter API | LLM-Provider-Adapter | ausgehend HTTPS | `OPENROUTER_API_KEY` | verfügbar, nicht aktiv |
| Curriculum-Dienst | HTTP-Service | ausgehend | `curriculum_key` (Header) | optional — nur wenn konfiguriert |
| NotebookLM-CLI | lokales Werkzeug | ausgehend Google | Google-Session in `NOTEBOOKLM_HOME` | optional — nur wenn eingerichtet |
| Tesseract | lokales Werkzeug | lokal | — | Teil des Images |
| Tesseract.js (Browser) | lokale WASM | im Browser | — | Teil der Upload-Seite |
| Piper TTS | lokales Werkzeug | lokal | — | optional — wenn Binary vorhanden |
| ffmpeg | lokales Werkzeug | lokal | — | Teil des Images (wenn `KARO_MIT_MP4`) |
| Xvfb / noVNC | lokale Werkzeuge | lokal | — | für NotebookLM-Login |

**Nicht vorhanden:** OpenAI, ElevenLabs, Google-OAuth
(kein OAuth-Client im Code), Google Drive API. „Google" kommt nur über die
NotebookLM-CLI hinein, die selbst eine Google-Browsersession pflegt.
OpenRouter ist als Adapter vorhanden, aber nicht aktiv — siehe unten.

---

## 1. KI-Anbieter-Schicht (`app/ai/`)

Alle allgemeinen KI-Aufrufe laufen über `AIClient` → `AIProvider`
(start/poll, neutrale Status `pending/running/completed/failed`) → den
Adapter aus `Config.ai_provider` (Registry `app/ai/registry.py`).
Domain-Code kennt weder Anbieter-Namen noch -URLs noch -Zustände.

| | |
|---|---|
| Wahl | `Config.ai_provider` — einzige Provider-Wahrheit |
| Lauf-Idempotenz | SHA-256-Fingerabdruck → Tabelle `ai_run` (`provider`, `run_id`, `status`, `meta`); identische Aufrufe teilen den Lauf, geparkte Jobs finden ihn wieder |
| Asynchron | `AIPending` → `jobs.Deferred` (`not_before`), kein Versuch verbraucht; synchrone Adapter liefern sofort |
| Gemeinsame Ops | `ai_poll_seconds` (300 s), `ai_max_run_seconds` (7200 s), `ai_http_timeout_seconds` (60 s), `ai_max_restarts` (1) |
| Fehler-Einordnung | Adapter übersetzt: 401/403 → `AIAuthError`, 429 → rate-limited, 5xx/Timeout → retryable (`app/ai/http.py`) |
| Rausgehende Daten | Prompts mit Aufgabentexten/Themen; **keine Bilder** (Privacy-Test `test_keine_bilder_an_modelle`) — die Schnittstelle hat gar keinen Bild-Parameter |
| Personenbezogen | Lernstände, Themen — kein Name, kein Foto |
| Code | `app/ai/client.py` (Fassade + `llm_call`-Audit), `types.py`, `provider.py`, `registry.py`, `runs.py`, `http.py`, `providers/` |

### 1a. Devin API — Adapter, aktiv (Default)

| | |
|---|---|
| Typ | LLM-Provider, asynchron per Session |
| Verwendung | Lernserien, Fachklassifikation, Materialanalyse, Recherche-Ranking, Gegenprüfungen |
| Base URL | Adapter-Default `api.devin.ai/v1`, Override `ops.ai_devin_base_url` |
| Ablauf | `start()` → `POST /sessions` (Run `pending`) → `poll()` → `GET /sessions/{id}` bis `structured_output` da ist (`completed`) |
| Auth | `Authorization: Bearer $DEVIN_API_KEY` — nur aus der Umgebung, nie in `config.json` |
| Heilen | `blocked` → ein Nudge per `POST /sessions/{id}/message`; abgelaufen/gescheitert → max. `ai_max_restarts` (1) Neustart, sonst `failed` |
| Adapter-Ops | `ai_devin_max_acu` (0 = kein Limit) |
| Code | `app/ai/providers/devin.py` |

### 1b. OpenRouter API — Adapter, verfügbar (nicht aktiv)

| | |
|---|---|
| Typ | LLM-Provider, synchron per Chat-Completions |
| Base URL | Adapter-Default `openrouter.ai/api/v1`, Override `ops.ai_openrouter_base_url` |
| Ablauf | `start()` → `POST /chat/completions` mit `response_format: json_schema` → sofort `completed` (`poll()` ist leer) |
| Auth | `Authorization: Bearer $OPENROUTER_API_KEY` — nur aus der Umgebung |
| Modell | `ops.ai_openrouter_model` — Pflicht, wenn aktiv (kein harter Modellname im Code) |
| Code | `app/ai/providers/openrouter.py` |

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
Externe APIs/Integrationen insgesamt:   4   (Devin API, OpenRouter API, Curriculum, NotebookLM)
OAuth-Integrationen:                    1   (NotebookLM-Browsersession)
LLM-/AI-Provider-Adapter:               2   (Devin = aktiv, OpenRouter = verfügbar)
aktive KI-Anbieter gleichzeitig:        1   (Config.ai_provider)
lokale externe Werkzeuge:               5   (Tesseract, Tesseract.js, Piper, ffmpeg, Xvfb/noVNC)
optionale Integrationen:                4   (OpenRouter, Curriculum, NotebookLM, Piper)
aktive Standardintegrationen:           2   (Devin API + Tesseract; Rest erst nach Einrichtung)
```

```text
AI: 1 · Speech: 1 (Piper) · Storage: 0 · Auth: 0 · Curriculum: 1 ·
Media: 3 (NotebookLM, ffmpeg, Xvfb) · Monitoring: 0 · Other: 0
```
