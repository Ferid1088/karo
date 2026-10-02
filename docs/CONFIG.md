# Karo-Konfiguration

Karo hat zwei getrennte Konfigurationsebenen:

| Ebene | Ort | Inhalt |
|---|---|---|
| `Config` | `app/config.py` → `/data/config.json` | Familien- und Produkteinstellungen (Name, Klasse, Fach, Modelle, Lernregeln). Wird über die Einstellungsseite gepflegt. Enthält die Secrets (API-Key, OAuth-Token, Curriculum-Key, Passwort-Hashes). |
| `Ops` | `app/config.py` → Umgebung | Betriebsparameter (Limits, Timeouts, Ports, Retries, Intervalle). Defaults im Code, Override per `KARO_*`-Env. Wird einmal beim Start geladen und validiert — Fehler wird mit `OpsInvalid` sofort gemeldet. |

**Secrets stehen ausschließlich in `config.json`** (`/data`, nicht im Repo). Sie werden
nie in Docs, Logs oder Env-Defaults abgelegt. Welche: siehe
`docs/ENVIRONMENT_VARIABLES.md` und `docs/API_INVENTORY.md`.

**Zeitzone:** eine Quelle — `config.zeitzone()` liefert `KARO_TIMEZONE` > `TZ` >
`config.timezone` > `Europe/Berlin`. Alle Tagesgrenzen (Lernzeit, Heute, Woche,
Welt) nutzen diese Funktion.

---

## Http / Session / Betrieb

| Parameter | Typ | Default | Env-Override | Beschreibung | Verwendet in |
|---|---|---|---|---|---|
| `max_body_bytes` | int | 105 MB | `KARO_MAX_BODY_BYTES` | Obergrenze für Request-Bodies; muss größer als `paket_max_bytes` + Overhead sein, sonst kommen große Pakete nie an. | `app/main.py` |
| `session_max_age_seconds` | int | 14 Tage | `KARO_SESSION_MAX_AGE_SECONDS` | Lebensdauer der signierten Session-Cookies. | `app/main.py` |
| `hsts_seconds` | int | 31 536 000 | `KARO_HSTS_SECONDS` | Strict-Transport-Security-Header, nur wenn `https_only` aktiv. | `app/main.py` |
| `https_only` | bool | `false` | `KARO_HTTPS_ONLY` | Secure-Cookies + HSTS + HTTPS-Redirect. Lokal aus (kein TLS im Container). | `app/main.py` |
| `log_level` | str | `INFO` | `KARO_LOG_LEVEL` | Log-Schwelle: `DEBUG`/`INFO`/`WARNING`/`ERROR`. | `app/observability/logging.py`, `app/main.py` |
| `environment` | str | `prod` | `KARO_ENV` | Umgebungsname, landet im Log-Kontext (`env`-Feld). | `app/observability/logging.py` |

## Datenbank

| Parameter | Typ | Default | Env-Override | Beschreibung | Verwendet in |
|---|---|---|---|---|---|
| `db_connect_timeout_seconds` | float | 30.0 | `KARO_DB_CONNECT_TIMEOUT_SECONDS` | SQLite-Connect-Timeout. | `app/db.py`, `app/materials.py`, `app/welten/world_db.py` |
| `db_busy_timeout_ms` | int | 30 000 | `KARO_DB_BUSY_TIMEOUT_MS` | Wie lange SQLite bei gesperrter Datei wartet, bevor `SQLITE_BUSY` kommt. | dieselben |

## Jobs (Hintergrund-Thread)

| Parameter | Typ | Default | Env-Override | Beschreibung | Verwendet in |
|---|---|---|---|---|---|
| `jobs_max_attempts` | int | 3 | `KARO_JOBS_MAX_ATTEMPTS` | Versuche pro Job, danach `fehlgeschlagen`. | `app/jobs.py` |
| `jobs_poll_seconds` | float | 3.0 | `KARO_JOBS_POLL_SECONDS` | Leerlauf-Pause des Worker-Threads. | `app/jobs.py` |
| `jobs_retry_delays` | tuple | `(60, 300)` | `KARO_JOBS_RETRY_DELAYS` | Wartezeiten vor dem 2./3. Versuch (kommagetrennt). | `app/jobs.py` |
| `jobs_defer_min_seconds` / `jobs_defer_max_seconds` | int | 5 / 300 | `KARO_JOBS_DEFER_*` | Grenzen für vom Job selbst gewählte Wiederhol-Abstände. | `app/jobs.py` |
| `jobs_stop_timeout_seconds` | float | 10.0 | `KARO_JOBS_STOP_TIMEOUT_SECONDS` | Wie lange der Shutdown auf den Worker wartet. | `app/jobs.py` |

## Uploads (Material-Pakete)

| Parameter | Typ | Default | Env-Override | Beschreibung | Verwendet in |
|---|---|---|---|---|---|
| `upload_max_bytes` | int | 25 MB | `KARO_UPLOAD_MAX_BYTES` | Einzel-Upload-Limit (klassischer Einzelblatt-Upload). | `app/security.py` |
| `passwort_min_laenge` | int | 8 | `KARO_PASSWORT_MIN_LAENGE` | Mindestlänge für Familien-/Kind-Passwort. | `app/security.py` |
| `paket_max_seiten` | int | 10 | `KARO_PAKET_MAX_SEITEN` | Max. Seiten pro Material-Paket; begrenzt OCR-Aufwand und Speicher. | `app/material_paket.py`, `learning_upload.html` |
| `seite_min_zeichen` | int | 40 | `KARO_SEITE_MIN_ZEICHEN` | Weniger Zeichen OCR-Text = leeres Blatt, kein Inhalt. | `app/material_paket.py`, `blatt-lesen.js` |
| `paket_max_bild_bytes` | int | 15 MB | `KARO_PAKET_MAX_BILD_BYTES` | Einzelbild JPG/PNG. | `app/material_paket.py` |
| `paket_max_pdf_bytes` | int | 50 MB | `KARO_PAKET_MAX_PDF_BYTES` | Einzel-PDF. | `app/material_paket.py` |
| `paket_max_bytes` | int | 100 MB | `KARO_PAKET_MAX_BYTES` | Gesamtgröße eines Pakets inkl. nachgeladener Seiten. | `app/material_paket.py` |
| `paket_overhead_bytes` | int | 2 MB | `KARO_PAKET_OVERHEAD_BYTES` | Formdata-Overhead je Request bei der Body-Prüfung. | `app/config.py` (Validierung) |
| `paket_max_text_zeichen` | int | 20 000 | `KARO_PAKET_MAX_TEXT_ZEICHEN` | Deckel des gesammelten OCR-Texts vor der Modellanalyse. | `app/material_paket.py` |
| `paket_max_themen` | int | 20 | `KARO_PAKET_MAX_THEMEN` | Max. Themen, die eine Paket-Analyse liefern darf. | `app/material_paket.py` |

## Dokument-Einlesen (`ingest`, klassischer Upload)

| Parameter | Typ | Default | Env-Override | Beschreibung | Verwendet in |
|---|---|---|---|---|---|
| `ingest_max_source_bytes` | int | 60 MB | `KARO_INGEST_MAX_SOURCE_BYTES` | Quelldatei-Limit. | `app/ingest.py` |
| `ingest_max_pdf_pages` | int | 300 | `KARO_INGEST_MAX_PDF_PAGES` | Max. PDF-Seiten beim Einlesen. | `app/ingest.py` |
| `ingest_max_edge` | int | 1 800 | `KARO_INGEST_MAX_EDGE` | Zielkante beim Normalisieren von Seitenbildern. | `app/ingest.py` |
| `ingest_target_bytes` | int | 4,4 MB | `KARO_INGEST_TARGET_BYTES` | Zielgröße normalisierter Bilder (JPEG-Qualität wird gesenkt, bis drunter). | `app/ingest.py` |
| `ingest_min_quality` | int | 45 | `KARO_INGEST_MIN_QUALITY` | JPEG-Qualität, unter die beim Verkleinern nie gefallen wird. | `app/ingest.py` |
| `ingest_max_image_pixels` | int | 40 M | `KARO_INGEST_MAX_IMAGE_PIXELS` | PIL-Decompression-Bomb-Schutz. | `app/ingest.py`, `app/profile.py` |
| `kopfzeile_max_prozent` | int | 25 | `KARO_KOPFZEILE_MAX_PROZENT` | Obere Schranke für `Config.header_crop_percent` — mehr würde Inhalt abschneiden. | `app/routers/auth.py`, `app/ingest.py` |
| `blatt_max_abschnitte` | int | 60 | `KARO_BLATT_MAX_ABSCHNITTE` | Abschnitte pro eingelesenem Blatt. | `app/blatt_text.py` |
| `blatt_max_zeichen` | int | 6 000 | `KARO_BLATT_MAX_ZEICHEN` | Zeichendeckel pro Abschnitt. | `app/blatt_text.py` |

## OCR

| Parameter | Typ | Default | Env-Override | Beschreibung | Verwendet in |
|---|---|---|---|---|---|
| `ocr_timeout_seconds` | int | 120 | `KARO_OCR_TIMEOUT_SECONDS` | Tesseract-Laufzeitdeckel pro Seite. | `app/blatt_text.py` |
| `ocr_sprachen` | str | `deu+eng` | `KARO_OCR_SPRACHEN` | Tesseract-Sprachpakete; wird ins Template als `data-ocr-sprachen` weitergereicht. | `app/blatt_text.py`, `blatt-lesen.js` |
| `ocr_max_pdf_seiten` | int | 20 | `KARO_OCR_MAX_PDF_SEITEN` | Server-OCR zerlegt höchstens so viele PDF-Seiten. | `app/blatt_text.py` |
| `browser_ocr_max_seiten` | int | 20 | `KARO_BROWSER_OCR_MAX_SEITEN` | Browser-seitige PDF-Render-Obergrenze pro Dokument. | `learning_upload.html` → `blatt-lesen.js` |
| `browser_ocr_max_kante` | int | 2 000 | `KARO_BROWSER_OCR_MAX_KANTE` | Zielkante beim Browser-PDF-Render. | dto. |
| `browser_ocr_min_konfidenz` | int | 60 | `KARO_BROWSER_OCR_MIN_KONFIDENZ` | Tesseract.js-Konfidenz; darunter gelten Wörter als geraten. | dto. |

## KI-Anbieter (Devin)

Der einzige externe KI-Anbieter ist Devin (asynchron per Session:
`POST /v1/sessions` → später pollen → `structured_output`). Alle Aufrufe
laufen über die Fassade `AIClient` (`app/ai/`); der Zugangsschlüssel kommt
ausschließlich aus der Umgebungsvariable `DEVIN_API_KEY`.

| Parameter | Typ | Default | Env-Override | Beschreibung | Verwendet in |
|---|---|---|---|---|---|
| `devin_base_url` | str | `https://api.devin.ai/v1` | `KARO_DEVIN_BASE_URL` | Basis-URL der Devin-API. | `app/ai/devin.py` |
| `devin_poll_seconds` | int | 300 | `KARO_DEVIN_POLL_SECONDS` | Wartezeit, bis ein geparkter Auftrag die Session erneut abfragt. | `app/jobs.py`, `app/ai/devin.py` |
| `devin_max_session_seconds` | int | 7 200 | `KARO_DEVIN_MAX_SESSION_SECONDS` | Höchstalter einer Session; danach gilt sie als gescheitert. | `app/ai/devin.py` |
| `devin_http_timeout_seconds` | float | 60 | `KARO_DEVIN_HTTP_TIMEOUT_SECONDS` | HTTP-Deckel pro API-Anfrage (Anlegen, Pollen, Nudge). | dto. |
| `devin_max_restarts` | int | 1 | `KARO_DEVIN_MAX_RESTARTS` | Neustarts abgelaufener/gescheiterter Sessions je Auftrag. | dto. |
| `devin_max_acu` | int | 0 | `KARO_DEVIN_MAX_ACU` | ACU-Obergrenze pro Session (0 = ohne Limit anlegen). | dto. |
| `llm_default_max_tokens` | int | 8 192 | `KARO_LLM_DEFAULT_MAX_TOKENS` | Standard-Antwortbudget, wenn kein Aufruf ein anderes nennt. | `app/ai/client.py` |
| `llm_fach_max_tokens` | int | 64 | `KARO_LLM_FACH_MAX_TOKENS` | Fachklassifikation: kurzer Aufruf, kurzes Budget. | `app/faecher.py` |
| `llm_lektion_max_tokens` | int | 32 000 | `KARO_LLM_LEKTION_MAX_TOKENS` | Token-Budget für eine komplette Lernreihe. | `app/adaptiv/erzeugung.py` |

`Config.ai_provider` ist fix `"devin"` — es gibt keine Backend-Wahl mehr.
`Config.has_credentials` liest nur, ob `DEVIN_API_KEY` in der Umgebung
steht; der Schlüssel wird nie in `config.json` gespeichert.

## Curriculum-Dienst

| Parameter | Typ | Default | Env-Override | Beschreibung | Verwendet in |
|---|---|---|---|---|---|
| `curriculum_request_timeout_seconds` | int | 8 | `KARO_CURRICULUM_REQUEST_TIMEOUT_SECONDS` | Einzel-HTTP-Aufruf an den Dienst. | `app/adaptiv/curriculum_dienst.py` |
| `curriculum_max_wait_seconds` | int | 24 h | `KARO_CURRICULUM_MAX_WAIT_SECONDS` | So lange wartet ein Themen-Auftrag insgesamt. | dto. |
| `curriculum_max_response_bytes` | int | 2 MB | `KARO_CURRICULUM_MAX_RESPONSE_BYTES` | Antwortdeckel. | dto. |
| `curriculum_poll_seconds` | int | 300 | `KARO_CURRICULUM_POLL_SECONDS` | Abstand zwischen „ist es fertig?"-Nachfragen. | dto. |
| `curriculum_error_retry_seconds` | int | 15 | `KARO_CURRICULUM_ERROR_RETRY_SECONDS` | Rückzug nach einem Fehler des Dienstes. | dto. |

Basis-URL und Schlüssel: `Config.curriculum_url` / `curriculum_key` (config.json),
überschreibbar per `KARO_CURRICULUM_URL` / `KARO_CURRICULUM_KEY`.

## NotebookLM

| Parameter | Typ | Default | Env-Override | Beschreibung |
|---|---|---|---|---|
| `notebooklm_login_browser_timeout_seconds` | int | 300 | `KARO_NOTEBOOKLM_LOGIN_BROWSER_TIMEOUT_SECONDS` | Browser-Login-Fenster |
| `notebooklm_auth_check_timeout_seconds` | int | 30 | `KARO_NOTEBOOKLM_AUTH_CHECK_TIMEOUT_SECONDS` | „Bin ich angemeldet?"-Probe |
| `notebooklm_short_timeout_seconds` | int | 90 | `KARO_NOTEBOOKLM_SHORT_TIMEOUT_SECONDS` | kurze CLI-Aufrufe |
| `notebooklm_generate_timeout_seconds` | int | 2 700 | `KARO_NOTEBOOKLM_GENERATE_TIMEOUT_SECONDS` | Artefakt-Erzeugung (Video/Audio) |
| `notebooklm_download_timeout_seconds` | int | 300 | `KARO_NOTEBOOKLM_DOWNLOAD_TIMEOUT_SECONDS` | Artefakt-Download |
| `notebooklm_cancel_poll_seconds` | int | 5 | `KARO_NOTEBOOKLM_CANCEL_POLL_SECONDS` | Abbruch-Prüfintervall |
| `notebooklm_attempts` | int | 3 | `KARO_NOTEBOOKLM_ATTEMPTS` | Versuche für kurze Operationen |
| `notebooklm_generate_attempts` | int | 2 | `KARO_NOTEBOOKLM_GENERATE_ATTEMPTS` | Versuche für Erzeugung |
| `notebooklm_retry_base_seconds` | int | 15 | `KARO_NOTEBOOKLM_RETRY_BASE_SECONDS` | Basis für linearen Rückzug |
| `notebooklm_vnc_rfb_port` | int | 5 901 | `KARO_NOTEBOOKLM_VNC_RFB_PORT` | RFB-Port des Xvfb-Browsers (1-65535 validiert) |
| `notebooklm_novnc_port` | int | 6 080 | `KARO_NOTEBOOKLM_NOVNC_PORT` | noVNC-Web-Port (1-65535 validiert) |
| `notebooklm_vnc_display` | str | `:99` | `KARO_NOTEBOOKLM_VNC_DISPLAY` | Xvfb-Display-Nummer |
| `notebooklm_vnc_ready_timeout_seconds` | int | 15 | `KARO_NOTEBOOKLM_VNC_READY_TIMEOUT_SECONDS` | Warten auf Xvfb-Bereitschaft |
| `notebooklm_vnc_screen` | str | `1280x800x24` | `KARO_NOTEBOOKLM_VNC_SCREEN` | Xvfb-Bildschirm |
| `notebooklm_novnc_dir` | str | `/usr/share/novnc` | `KARO_NOTEBOOKLM_NOVNC_DIR` | noVNC-Installation im Image |

Verwendung: `app/media/notebooklm.py`. Daten-Home liegt unter `NOTEBOOKLM_HOME`
bzw. `KARO_DATA_DIR/notebooklm`.

## Medien (TTS / Video / Profilbild)

| Parameter | Typ | Default | Env-Override | Beschreibung | Verwendet in |
|---|---|---|---|---|---|
| `tts_timeout_seconds` | int | 180 | `KARO_TTS_TIMEOUT_SECONDS` | Sprachsynthese-Laufzeitdeckel. | `app/media/tts.py` |
| `video_timeout_seconds` | int | 600 | `KARO_VIDEO_TIMEOUT_SECONDS` | ffmpeg-Laufzeitdeckel. | `app/media/video.py` |
| `profil_bild_pixel` | int | 512 | `KARO_PROFIL_BILD_PIXEL` | Kantenlänge des gespeicherten Profilbilds. | `app/profile.py` |
| `profil_bild_cache_seconds` | int | 86 400 | `KARO_PROFIL_BILD_CACHE_SECONDS` | `Cache-Control max-age` des Profilbilds im Browser. | `app/routers/auth.py` |

## Verbindungen / Lernzeit

| Parameter | Typ | Default | Env-Override | Beschreibung | Verwendet in |
|---|---|---|---|---|---|
| `connections_cache_ttl_seconds` | float | 100 | `KARO_CONNECTIONS_CACHE_TTL_SECONDS` | TTL des Verbindungs-Caches. | `app/connections.py` |
| `lernzeit_takt_seconds` | int | 30 | `KARO_LERNZEIT_TAKT_SECONDS` | Herzschlag des Zeitmessers im Browser. | `app/services/learning_time.py` |
| `lernzeit_anschluss_seconds` | int | 90 | `KARO_LERNZEIT_ANSCHLUSS_SECONDS` | Lücke bis zu der zwei Takte noch zusammengehören. | dto. |
| `lernzeit_pause_seconds` | int | 300 | `KARO_LERNZEIT_PAUSE_SECONDS` | Ab hier gilt eine Unterbrechung als Pause. | dto. |
| `lernzeit_gutschrift_seconds` | int | 60 | `KARO_LERNZEIT_GUTSCHRIFT_SECONDS` | Zeit, die nach einem Abbruch pro Takt noch zählt. | dto. |
| `lernzeit_tagesdeckel_seconds` | int | 8 h | `KARO_LERNZEIT_TAGESDECKEL_SECONDS` | Mehr aktive Lernzeit wird pro Tag nicht verbucht. | dto. |

## Adaptive Lernstrecke

| Parameter | Typ | Default | Env-Override | Beschreibung | Verwendet in |
|---|---|---|---|---|---|
| `adaptiv_grundzeit_auswahl_seconds` | int | 25 | `KARO_ADAPTIV_GRUNDZEIT_AUSWAHL_SECONDS` | Erwartete Antwortzeit: Auswahlaufgabe. | `app/adaptiv/protokoll.py` |
| `adaptiv_grundzeit_bruch_seconds` | int | 60 | `KARO_ADAPTIV_GRUNDZEIT_BRUCH_SECONDS` | Erwartete Antwortzeit: Bruch/Rechnen. | dto. |
| `adaptiv_grundzeit_text_seconds` | int | 90 | `KARO_ADAPTIV_GRUNDZEIT_TEXT_SECONDS` | Erwartete Antwortzeit: Freitext. | dto. |
| `adaptiv_zeit_spanne_min` / `adaptiv_zeit_spanne_max` | float | 0,6 / 1,8 | `KARO_ADAPTIV_ZEIT_SPANNE_*` | Faktorkorridor für die individuelle Zeitnorm. | dto. |
| `wiederholung_abstaende` | tuple | `(2,3,4,5)` | `KARO_WIEDERHOLUNG_ABSTAENDE` | Tage-Abstände, die das Kind für Wiederholungen wählen kann. | `app/adaptiv/wiederholung.py` |
| `voraussetzung_aufgaben` | int | 2 | `KARO_VORAUSSETZUNG_AUFGABEN` | Übungsaufgaben bei einem Voraussetzungs-Umweg. | `app/adaptiv/voraussetzung.py` |
| `hinweis_max_age_seconds` | int | 1 800 | `KARO_HINWEIS_MAX_AGE_SECONDS` | Gültigkeit der signierten Prüf-Hinweise. | `app/routers/adaptiv.py` |
| `erfolg_tage` | int | 14 | `KARO_ERFOLG_TAGE` | Wie weit „Heute" in die Erfolgsgeschichte schaut. | `app/services/today.py` |
| `family_daily_topics` | int | 5 | `KARO_FAMILY_DAILY_TOPICS` | Neue Themen pro Tag beim Lehrplan-Dienst; `0` = unbegrenzt. | `app/services/topic_budget.py` |

## Meine Woche

| Parameter | Typ | Default | Env-Override | Beschreibung | Verwendet in |
|---|---|---|---|---|---|
| `woche_fenster_tage` | int | 28 | `KARO_WOCHE_FENSTER_TAGE` | Beobachtungsfenster der Wochenregeln. | `app/woche/regeln.py` |
| `woche_gemieden_tage` | int | 28 | `KARO_WOCHE_GEMIEDEN_TAGE` | Rückblick für „wird gemieden". | dto. |
| `woche_gemieden_min_stunden` | int | 3 | `KARO_WOCHE_GEMIEDEN_MIN_STUNDEN` | Mindest-Beschäftigung, bevor „gemieden" greift. | dto. |
| `woche_schlafgrenze_stunde` | int | 21 | `KARO_WOCHE_SCHLAFGRENZE_STUNDE` | Aktivität nach dieser Stunde zählt als „zu spät". | dto. |
| `woche_schlechter_tag_ab` / `woche_guter_tag_ab` | int | 3 / 3 | `KARO_WOCHE_*` | Ab so vielen Vorkommnissen wird ein Wochentag auffällig. | dto. |
| `woche_zu_schwer_ab` / `woche_abbruch_ab` / `woche_verkleinern_max` / `woche_schwierig_tage_ab` / `woche_nullzyklen_ab` / `woche_karten_schwelle` | int | 2 / 3 / 2 / 3 / 2 / 2 | `KARO_WOCHE_*` | Schwellen der übrigen Wochenregeln. | dto. |

## Meine Welt

| Parameter | Typ | Default | Env-Override | Beschreibung | Verwendet in |
|---|---|---|---|---|---|
| `welt_foto_source_bytes` | int | 12 MB | `KARO_WELT_FOTO_SOURCE_BYTES` | Quellfoto-Limit. | `app/welten/media.py` |
| `welt_audio_bytes` | int | 2 MB | `KARO_WELT_AUDIO_BYTES` | Sprachclip-Limit. | `app/welten/media.py` |
| `welt_max_image_pixels` | int | 25 M | `KARO_WELT_MAX_IMAGE_PIXELS` | Decompression-Bomb-Deckel. | `app/welten/media.py` |
| `welt_max_image_edge` / `welt_thumb_edge` | int | 1 800 / 360 | `KARO_WELT_*` | Bild-/Vorschaubild-Kante. | `app/welten/media.py` |
| `welt_fotos_tag` | int | 2 | `KARO_WELT_FOTOS_TAG` | Tägliches Foto-Kontingent. | `app/welten/store.py` |
| `welt_audio_sekunden_tag` | int | 60 | `KARO_WELT_AUDIO_SEKUNDEN_TAG` | Tägliches Hör-Kontingent. | `app/welten/store.py` |
| `welt_kapsel_max_tage` | int | 1 830 | `KARO_WELT_KAPSEL_MAX_TAGE` | Wie weit eine Zeitkapsel in der Zukunft liegen darf. | `app/welten/store.py` |

## Suche / Eingaben / Textdeckel

| Parameter | Typ | Default | Env-Override | Beschreibung | Verwendet in |
|---|---|---|---|---|---|
| `kb_suche_treffer` | int | 12 | `KARO_KB_SUCHE_TREFFER` | Treffer der Themen-Volltextsuche. | `app/kb.py` |
| `kb_lehrmaterial_treffer` | int | 10 | `KARO_KB_LEHRMATERIAL_TREFFER` | Lehrmaterial-Treffer pro Thema. | `app/kb.py` |
| `themen_zuordnung_treffer` | int | 30 | `KARO_THEMEN_ZUORDNUNG_TREFFER` | Treffermenge für die automatische Chunk-Zuordnung. | `app/topics.py` |
| `themen_duplikat_schwelle` | float | 0,88 | `KARO_THEMEN_DUPLIKAT_SCHWELLE` | Ähnlichkeit, ab der ein Thema als Dublette gilt. | `app/topics.py` |
| `entwurf_antwort_zeichen` | int | 2 000 | `KARO_ENTWURF_ANTWORT_ZEICHEN` | Antwortdeckel im Quiz-Entwurf. | `app/services/quiz_drafts.py` |
| `probe_antwort_zeichen` | int | 1 000 | `KARO_PROBE_ANTWORT_ZEICHEN` | Antwortdeckel in der Klassenarbeit-Probe. | `app/services/exam_rehearsal.py` |
| `recherche_max_treffer` | int | 8 | `KARO_RECHERCHE_MAX_TREFFER` | Websuche-Treffer für den Wochen-Post. | `app/research.py` |
| `recherche_max_inhalt_zeichen` | int | 6 000 | `KARO_RECHERCHE_MAX_INHALT_ZEICHEN` | Zeichen pro abgerufener Trefferseite. | dto. |
| `post_max_text_zeichen` / `post_max_feier_zeichen` | int | 200 / 60 | `KARO_POST_MAX_*` | Zeichendeckel beim Familien-Post. | `app/services/family_post.py` |
| `formular_wunsch_zeichen` | int | 500 | `KARO_FORMULAR_WUNSCH_ZEICHEN` | „Was willst du lernen?"-Feld, gespeichert. | `app/teaching.py` |
| `prompt_wunsch_zeichen` | int | 300 | `KARO_PROMPT_WUNSCH_ZEICHEN` | Anteil davon, der in Prompts einfließt. | `app/prompts.py` |

---

## Bewusst im Code gebliebene Konstanten

Diese Literale sind Domänenlogik, kein Betriebsparameter — sie bleiben im Code:

- `app/woche/vorschlaege.py`: `MINUTEN = {"klein": 2, "mittel": 8, "gross": 15}` — Dauer der Vorschlagskarten, fachlicher Ausdruck der Kartengrößen.
- `app/services/exam_effort.py`: `MINUTEN`-Tabelle, `ZUSCHLAG = 1.2`, `STUFE = 5` — Schätzheuristik für die Prüfungsvorbereitung.
- `app/services/parent_report.py`: Schwellen der Eltern-Ampeln (`.55`, `7/10`, `21` Tage) — bewusste Berichts-Definitionen.
- `app/woche/bruecke.py`: `1/7/21`-Tage-Bänder — Einordnung der Prüfungsnähe.
- `karo_contract/`: Protokoll- und Schema-Konstanten (`MAX_VERSUCHE = 400` Generierungs-Schleife, Feldlängen, Wertebereiche des Vertrags).
- Interne Event-/Tabellen-/Spaltennamen, Statuswerte (`MASTERED` u.a.), SQL-Texte, MIME-Listen, UI-Layoutwerte.
- `app/media/notebooklm.py`: interne Poll-Schritte (`0.2 s`) und Drain-Timeouts nach `kill` — Implementierungsdetail der Prozessführung.
- Aufrufstellen-`limit=` für `kb.suche`/`kb.lehrmaterial`/`export.verlauf_zeilen` (1/8/10/200/2 000 …): Kontextgrößen des jeweiligen Aufrufs — das Budget, wie viel Material in einen Prompt oder eine Seite fließt, nicht eine Betriebsgrenze.
- Browser-seitige Timer in `app/static/*.js` (Debounce 300 ms/3 s, Status-Polls 1,5–30 s, Takt `200 ms`): UI-Implementierung, die bei Bedarf per `data-*`-Attribut verdrahtet werden kann (Muster siehe `blatt-lesen.js`).
- Feldgrenzen in Templates (`maxlength`) und Formular-Validierungen (`0 ≤ Wert ≤ 60`, Klasse 1–13): Eingaberegeln an die Schema-/UI-Grenzen angelehnt.
- `topics.py` `len(n) <= 200`: Thementitel-Kappe, gespiegelt an `karo_contract`-Titelfeld.
- `adaptiv/*` `getattr(cfg, "adaptiv_*", …)`-Fallbacks: defensive Defaults gegen Teil-`Config`-Objekte in Tests — die Werte selbst leben in `Config`.

## Was **nicht** hier steht — und warum

- **Secrets** (`curriculum_key`, Passwort-Hashes): liegen in
  `/data/config.json`, siehe `docs/API_INVENTORY.md`. `DEVIN_API_KEY`
  kommt ausschließlich aus der Umgebung.
- **Pfade** (`KARO_DATA_DIR`, `KARO_DRIVE_DIR`, `KARO_DRIVE_PATH`,
  `NOTEBOOKLM_HOME`, `KARO_GIT_SHA`): Umgebungs-/Deployment-Größen, siehe
  `docs/ENVIRONMENT_VARIABLES.md`.
- **KI-Anbieter**: fix Devin (`Config.ai_provider`); der Schlüssel lebt in
  `DEVIN_API_KEY`, nicht in `config.json`.
- **Adaptive Lernparameter** (`adaptiv_*` in `Config`): Produkteinstellungen der
  Familie, nicht Betrieb — bleiben auf der Einstellungsseite.
