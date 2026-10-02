# Karo — Externe APIs und Integrationen

Nur Integrationen, die im Code tatsächlich vorhanden sind. Keine Annahmen.

---

## Übersicht

| Name | Typ | Richtung | Auth | aktiv/optional |
|---|---|---|---|---|
| Anthropic API | LLM-Provider | ausgehend HTTPS | `anthropic_api_key` (Bearer-Header durch SDK) | optional — Backend `api` |
| Claude CLI / Abo | LLM-Provider | ausgehend (CLI) | `claude_oauth_token` → `CLAUDE_CODE_OAUTH_TOKEN` | optional — Backend `abo` |
| Curriculum-Dienst | HTTP-Service | ausgehend | `curriculum_key` (Header) | optional — nur wenn konfiguriert |
| NotebookLM-CLI | lokales Werkzeug | ausgehend Google | Google-Session in `NOTEBOOKLM_HOME` | optional — nur wenn eingerichtet |
| Tesseract | lokales Werkzeug | lokal | — | Teil des Images |
| Tesseract.js (Browser) | lokale WASM | im Browser | — | Teil der Upload-Seite |
| Piper TTS | lokales Werkzeug | lokal | — | optional — wenn Binary vorhanden |
| ffmpeg | lokales Werkzeug | lokal | — | Teil des Images (wenn `KARO_MIT_MP4`) |
| Xvfb / noVNC | lokale Werkzeuge | lokal | — | für NotebookLM-Login |

**Nicht vorhanden:** OpenAI, OpenRouter, ElevenLabs, Devin-API, Google-OAuth
(kein OAuth-Client im Code), Google Drive API. „Google" kommt nur über die
NotebookLM-CLI hinein, die selbst eine Google-Browsersession pflegt.

---

## 1. Anthropic API (Backend `api`)

| | |
|---|---|
| Typ | LLM-Provider |
| Richtung | ausgehend HTTPS |
| Verwendung | Lernserien, Fachklassifikation, Materialanalyse, Recherche-Ranking |
| Base URL | SDK-Standard `https://api.anthropic.com` |
| Auth | `x-api-key` aus `Config.anthropic_api_key` (config.json) |
| Provider/Modell | `Config.model_stark`, `Config.model_text`, `Config.model_video` |
| Timeout | `ops.llm_api_timeout_seconds` (180 s); Lektionen 900 s |
| Retry | SDK `max_retries = ops.llm_api_max_retries` (3) |
| Rate-Limit | SDK-Retry; Fehler landen als `ClaudeError` im Job |
| Rausgehende Daten | Prompts mit Aufgabentexten/Themen; **keine Bilder** (Privacy-Test `test_keine_bilder_an_modelle`) |
| Personenbezogen | Lernstände, Themen — kein Name, kein Foto |
| Code | `app/llm/api_backend.py`, `app/llm/client.py` |

## 2. Claude CLI / Abo (Backend `abo`)

| | |
|---|---|
| Typ | LLM-Provider über die installierte `claude`-CLI |
| Richtung | ausgehend (CLI ruft Anthropic) |
| Verwendung | wie oben — gleiche `ClaudeClient`-Schnittstelle |
| Base URL | intern der CLI |
| Auth | `CLAUDE_CODE_OAUTH_TOKEN` aus `Config.claude_oauth_token` (config.json); `ANTHROPIC_API_KEY` wird aus der CLI-Umgebung gelöscht |
| Provider/Modell | `sonnet`/`haiku`/`opus`-Aliase der CLI |
| Timeout | `ops.llm_cli_timeout_seconds` (300 s) |
| Retry | keine eigenen — Job-Layer (`jobs_retry_delays`) |
| Rate-Limit | Abo-Kontingent; Fehler wird als Job-Fehler gezeigt |
| Rausgehende Daten | wie Anthropic API |
| Personenbezogen | wie oben |
| Code | `app/llm/cli_backend.py`, `app/llm/client.py` |

## 3. Curriculum-Dienst

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

## 4. NotebookLM-CLI

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

## 5. Lokale Werkzeuge

| Name | Zweck | Konfiguration | Code |
|---|---|---|---|
| Tesseract | Server-OCR-Fallback | `ocr_timeout_seconds`, `ocr_sprachen`, `ocr_max_pdf_seiten` | `app/blatt_text.py` |
| Tesseract.js | Browser-OCR | `browser_ocr_*` via `data-*`-Attribute | `app/static/blatt-lesen.js` |
| Piper | Sprachausgabe | `tts_timeout_seconds` | `app/media/tts.py` |
| ffmpeg | Video-Erzeugung | `video_timeout_seconds` | `app/media/video.py` |
| Xvfb/noVNC | NotebookLM-Login | `notebooklm_vnc_*`, `notebooklm_novnc_*` | `app/media/notebooklm.py` |

## 6. Eingebettete Inhalte (keine API)

`app/welten/content.py` enthält eine kuratierte Liste öffentlicher Bildungs-URLs
(NASA, MedlinePlus, USFS usw.) als Lesestoff für „Meine Welt". Das sind Links,
keine Anbindungen — keine Auth, keine Calls.

---

## Zählung

```text
Externe APIs/Integrationen insgesamt:   4   (Anthropic, Claude-CLI, Curriculum, NotebookLM)
OAuth-Integrationen:                    1   (NotebookLM-Browsersession; Claude-CLI nutzt OAuth-Token)
LLM-/AI-Provider:                       2   (Anthropic API, Claude CLI — ein Ziel, zwei Wege)
lokale externe Werkzeuge:               5   (Tesseract, Tesseract.js, Piper, ffmpeg, Xvfb/noVNC)
optionale Integrationen:                4   (alles außer Tesseract/ffmpeg im Image)
aktive Standardintegrationen:           2   (LLM-Backend + Tesseract; Rest erst nach Einrichtung)
```

```text
AI: 2 · Speech: 1 (Piper) · Storage: 0 · Auth: 0 · Curriculum: 1 ·
Media: 3 (NotebookLM, ffmpeg, Xvfb) · Monitoring: 0 · Other: 0
```
