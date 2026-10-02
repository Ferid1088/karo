# Karo — Umgebungsvariablen

Drei Gruppen:

1. **Pfade/Deployment** — wo Karo Daten ablegt und wie es deployed ist
2. **Ops-Overrides** — `KARO_<OPS_FELD>` überschreibt `config.ops()`-Defaults
3. **Provider-/CLI-Umgebung** — Variablen, die Karo an Unterprozesse weitergibt

Alle Ops-Overrides sind in `docs/CONFIG.md` einzeln beschrieben; hier nur die
Nicht-Ops-Variablen.

---

## Deployment / Pfade

| Variable | Pflicht | Default | Secret | Beschreibung | Verwendet in |
|---|---|---|---|---|---|
| `KARO_DATA_DIR` | nein | `/data` | nein | Datenverzeichnis (DB, config.json, Uploads, Session-Key) | `app/config.py` |
| `KARO_DRIVE_DIR` | nein | `/drive` | nein | Mountpunkt des Familien-Laufwerks | `app/config.py` |
| `KARO_DRIVE_PATH` | nein | — | nein | Anzeige-Override für den Drive-Pfad in der Statusanzeige | `app/routers/auth.py` |
| `KARO_GIT_SHA` | nein | `unbekannt` | nein | Commit-Stand des Images; erscheint in `/health` und Log-Kontext | `Dockerfile`, `app/observability/logging.py`, `app/routers/auth.py` |
| `KARO_TIMEZONE` | nein | — | nein | Zeitzone, schlägt `TZ` und `config.timezone` | `config.zeitzone()` |
| `TZ` | nein | — | nein | Fallback-Zeitzone | `config.zeitzone()` |
| `NOTEBOOKLM_HOME` | nein | `<data>/notebooklm` | nein | Speicherort der Google-Session der NotebookLM-CLI | `app/media/notebooklm.py`, `Makefile` |
| `KARO_MIT_MP4` | nein | `1` | nein | Build-Flag: ffmpeg/Video-Werkzeuge ins Image | `Makefile`, `docker-compose.build.yml` |
| `KARO_MIT_NOTEBOOKLM` | nein | `1` | nein | Build-Flag: NotebookLM-Tooling ins Image | `docker-compose.build.yml` |
| `DEV_PORT` | nein | `8000` | nein | Makefile-Variable für den lokalen Dev-Server | `Makefile` |

Ports sind Deployment-Größen und stehen in den Deploy-Dateien selbst:
`8080` (App, `Dockerfile`/`docker-compose.yml`), `6080` (noVNC-Brücke),
`5901` (interner RFB-Port, `Ops.notebooklm_vnc_rfb_port`).

## Provider-Overrides (nicht Ops)

| Variable | Pflicht | Default | Secret | Beschreibung | Verwendet in |
|---|---|---|---|---|---|
| `KARO_CURRICULUM_URL` | nein | `config.curriculum_url` | nein | Basis-URL des Curriculum-Dienstes | `app/adaptiv/curriculum_dienst.py`, `docker-compose.curriculum.yml` |
| `KARO_CURRICULUM_KEY` | nein | `config.curriculum_key` | **ja** | Schlüssel für den Curriculum-Dienst | dto. |

## Umgebung des LLM-CLI-Unterprozesses

Karo **setzt** diese Variablen beim Start des `claude`-Unterprozesses — sie
werden nicht gelesen:

| Variable | Wert | Beschreibung |
|---|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | `Config.claude_oauth_token` | Abo-Login der Claude-CLI |
| `ANTHROPIC_API_KEY` | *(entfernt)* | wird bewusst gelöscht, damit die CLI nicht versehentlich das API-Konto nutzt |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | `ops.llm_cli_verify_tokens` beim Testaufruf | Antwortdeckel des Einrichtungs-Tests; `docker-compose.yml` setzt zusätzlich `32000` als Container-Default für normale CLI-Läufe |

## CI (`.github/workflows/pytest-full.yml`)

| Variable | Kontext | Beschreibung |
|---|---|---|
| `KARO_APP_PATH` | Bridge-Vertragstest | Pfad zum Karo-Checkout für das externe `curriculum-team`-Repo |
| `KARO_DATA_DIR` | Bridge-Vertragstest | Wegwerf-Datenverzeichnis im Runner |
| `TEST_DATABASE_URL` | Bridge-Vertragstest | Postgres der Testinfrastruktur des Lehrplan-Dienstes |
| `APP_ENV=test` | Bridge-Vertragstest | Kennung der Curriculum-Testumgebung |
| `ALLOW_DESTRUCTIVE_DB_RESET=YES` | Bridge-Vertragstest | explizites Go für `reset_test_db` — bewusste Schranke |

## Ops-Overrides (`KARO_<FELD>`)

Jedes `Ops`-Feld in `app/config.py` hat einen Override nach dem Muster
`KARO_<FELDNAME_IN_UPPERCASE>` — z. B. `KARO_UPLOAD_MAX_BYTES`,
`KARO_LLM_API_TIMEOUT_SECONDS`, `KARO_NOTEBOOKLM_VNC_RFB_PORT`.
Vier historische Namen bleiben aus Kompatibilität kürzer:

| Ops-Feld | Env-Name |
|---|---|
| `log_level` | `KARO_LOG_LEVEL` |
| `environment` | `KARO_ENV` |
| `https_only` | `KARO_HTTPS_ONLY` |
| `family_daily_topics` | `KARO_FAMILY_DAILY_TOPICS` |

Ungültige Werte werden beim Start mit `OpsInvalid` abgelehnt — kein stiller
Fallback.

## Secrets

Secrets stehen **nicht** in der Umgebung, sondern in `/data/config.json`:
`anthropic_api_key`, `claude_oauth_token`, `curriculum_key`, `app_password_*`,
`child_password_*`, und `/data/session.key` für die Session-Signatur.
`.env` ist gitignored; siehe `.env.example` für die leeren Schlüssel.
