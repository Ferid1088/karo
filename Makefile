.DEFAULT_GOAL := hilfe
.PHONY: hilfe pull up up-klein publish down logs test backup backup-alles restore shell stimme \
        notebooklm-login dev dev-reload dev-stop dev-log dev-status

VOLUME := karo_karo-data
STAMP  := $(shell date +%Y%m%d-%H%M)
DOCKERHUB_REPO := farid1088/karo

# Beide Overlay-Aufrufe (up, up-klein) bauen lokal aus dem Quellcode statt
# das fertige Docker-Hub-Image zu ziehen — siehe docker-compose.build.yml.
BUILD_COMPOSE := docker compose -f docker-compose.yml -f docker-compose.build.yml

# --- Lokale Entwicklung, ohne Docker --------------------------------------
# Laeuft gegen dieselben Daten wie der Container, aber mit dem Quellcode aus
# diesem Verzeichnis. Die beiden KARO_*-Variablen sind der springende Punkt:
# ohne sie sucht Karo die Datenbank unter /data und findet nichts.
UVICORN   := ./karo-py310/bin/uvicorn
DEV_PORT  ?= 8000
DEV_HOME  ?= $(HOME)/karo-data
DEV_DATA  ?= $(DEV_HOME)/data
DEV_DRIVE ?= $(DEV_HOME)/drive
DEV_LOG   ?= $(DEV_HOME)/karo-uvicorn.log

hilfe:
	@echo "make pull          fertiges Image von Docker Hub ziehen und starten (kein Build)"
	@echo "make up            selbst bauen und starten (alle Ausgabemodi)"
	@echo "make up-klein      selbst bauen, schlanke Variante ohne MP4"
	@echo "make stimme        deutsche Sprachdatei für die MP4-Ausgabe laden"
	@echo "make notebooklm-login  einmalige NotebookLM-Anmeldung (im Browser)"
	@echo "make publish       Image für amd64+arm64 bauen und nach Docker Hub veröffentlichen"
	@echo "make down          stoppen"
	@echo "make logs          Protokoll mitlesen"
	@echo "make test          Tests ausführen"
	@echo ""
	@echo "Lokal entwickeln (ohne Docker, Port $(DEV_PORT)):"
	@echo "make dev           starten — ein Prozess, kein Neuladen bei Änderungen"
	@echo "make dev-reload    starten mit --reload — zwei Prozesse, dafür bequem"
	@echo "make dev-stop      stoppen"
	@echo "make dev-log       Protokoll mitlesen"
	@echo "make dev-status    läuft da was?"
	@echo "make backup        Lerndaten sichern (OHNE Zugangsdaten)"
	@echo "make backup-alles  alles sichern, inklusive API-Schlüssel"
	@echo "make restore ARCHIV=sicherung/karo-....tar.gz"

# Für alle, die nicht selbst bauen wollen: zieht $(DOCKERHUB_REPO):latest
# und startet direkt — siehe docker-compose.yml.
pull:
	docker compose pull
	docker compose up -d
	@echo "Karo läuft auf http://127.0.0.1:8080"

# Gebaut wird ueber build.sh: nur aus einem sauberen, committeten, gepushten
# Stand, und mit KARO_GIT_SHA im Image. Ohne das traegt das Image keinen Stand,
# und /health kann nicht sagen, welcher Code antwortet.
up:
	./build.sh
	$(BUILD_COMPOSE) up -d --no-build
	@echo "Karo läuft auf http://127.0.0.1:8080"

up-klein:
	KARO_MIT_MP4=0 ./build.sh
	KARO_MIT_MP4=0 $(BUILD_COMPOSE) up -d --no-build
	@echo "Karo (schlank) läuft auf http://127.0.0.1:8080"

# Baut für beide Architekturen (Apple Silicon UND Intel/AMD, also auch
# Windows) und veröffentlicht in einem Schritt nach Docker Hub. Setzt
# vorher `docker login` und einen buildx-Builder voraus:
#   docker buildx create --use
# Verlangt eine Versionsnummer, damit nicht mehr nur `latest` verschoben wird
# und ein bestimmter Stand jederzeit gezielt zurückgeholt werden kann:
#   make publish VERSION=1.1.0
publish:
	@test -n "$(VERSION)" || (echo "Bitte eine Version angeben, z. B. make publish VERSION=1.1.0"; exit 1)
	@command -v docker buildx >/dev/null || (echo "docker buildx wird gebraucht (in Docker Desktop enthalten)"; exit 1)
	@test -z "$$(git status --porcelain)" || (echo "Der Arbeitsbaum ist nicht sauber — ein veroeffentlichtes Image aus nicht committetem Code ist nicht nachvollziehbar."; git status --short; exit 2)
	@git branch -r --contains HEAD | grep -q . || (echo "HEAD ist auf keinem Remote. Erst pushen, dann veroeffentlichen."; exit 3)
	docker buildx build --platform linux/amd64,linux/arm64 \
		--build-arg KARO_GIT_SHA=$$(git rev-parse HEAD) \
		-t $(DOCKERHUB_REPO):$(VERSION) -t $(DOCKERHUB_REPO):latest --push .
	@echo "Veröffentlicht: $(DOCKERHUB_REPO):$(VERSION) und :latest (linux/amd64, linux/arm64)"

# Misst die Trefferquote beim Lesen von Blaettern — ausschliesslich lokal, an
# echten Blaettern dieser Familie. Sie bleiben in OCR_PROBEN (von .gitignore
# ausgeschlossen); ins Repository kommt nur die Kennzahl. Laeuft im Container,
# weil dort tesseract und pypdfium2 liegen.
OCR_PROBEN ?= $(HOME)/karo-ocr-proben
.PHONY: ocr-report
ocr-report:
	@test -d "$(OCR_PROBEN)" || (echo "Kein Probenordner: $(OCR_PROBEN)"; 	  echo "Blaetter dort ablegen (sie bleiben dort) oder OCR_PROBEN=... setzen."; exit 2)
	docker compose cp tools/ocr_report.py karo:/srv/tools/ocr_report.py
	docker run --rm -v "$(OCR_PROBEN)":/proben:ro -v $(VOLUME):/data 	  -v "$$PWD/tools":/srv/tools:ro -v "$$PWD/app":/srv/app:ro 	  -w /srv karo:local python tools/ocr_report.py --quelle /proben --db /data/karo.db 	  --bericht /dev/stdout

# Die Sprachdateien liegen bewusst nicht im Image: wer nur den HTML-Modus
# benutzt, lädt nie etwas herunter.
STIMME ?= de_DE-thorsten-medium
stimme:
	docker compose exec -T karo sh -c '\
		mkdir -p /data/stimmen && cd /data/stimmen && \
		base=https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE && \
		name=$(STIMME) && \
		sprecher=$$(echo $$name | cut -d- -f2) && \
		qual=$$(echo $$name | cut -d- -f3) && \
		for endung in onnx onnx.json; do \
			[ -f $$name.$$endung ] || curl -fsSL \
				"$$base/$$sprecher/$$qual/$$name.$$endung" -o $$name.$$endung; \
		done && ls -la'
	@echo "Stimme $(STIMME) liegt in /data/stimmen."

# Läuft bewusst NICHT im Container: die Anmeldung braucht einen echten
# Browser, den ein Container ohne Bildschirm nicht hat. Sie läuft hier auf
# dem Rechner der Familie und schreibt in denselben Ordner, den der
# Container unter /data/notebooklm einhängt (siehe docker-compose.yml).
# Voraussetzung: `pip install "notebooklm-py[browser]"` auf diesem Rechner.
NOTEBOOKLM_HOME ?= $(CURDIR)/notebooklm-lokal
notebooklm-login:
	@command -v notebooklm >/dev/null || (echo "Bitte zuerst installieren: \
pip install \"notebooklm-py[browser]\""; exit 1)
	NOTEBOOKLM_HOME=$(NOTEBOOKLM_HOME) notebooklm login
	@echo "Angemeldet. Der Container liest dieselbe Sitzung aus $(NOTEBOOKLM_HOME)."

down:
	docker compose down

logs:
	docker compose logs -f karo

test:
	python -m pytest

# Die Sicherung enthaelt bewusst KEINE Zugangsdaten: ein Archiv mit dem
# API-Schluessel darf nicht versehentlich in ein Repository wandern. Der
# Schluessel ist in zwei Minuten neu erzeugt, die Lerndaten nicht.
#
# VACUUM INTO schreibt einen konsistenten Schnappschuss. Der laufende
# karo.db samt -wal wird bewusst NICHT mitgesichert — beim Kopieren
# entstuenden sonst Dateien aus verschiedenen Augenblicken, und der
# Wiederherstellungsweg griffe die falsche davon.
backup:
	@mkdir -p sicherung
	docker compose exec -T karo python -c "import sqlite3, pathlib, os; \
p = pathlib.Path('/data/backups'); p.mkdir(parents=True, exist_ok=True); \
ziel = p / 'karo-snapshot.db'; \
[f.unlink() for f in p.glob('karo-snapshot.db*')]; \
c = sqlite3.connect('/data/karo.db'); \
c.execute(\"VACUUM INTO '/data/backups/karo-snapshot.db'\"); c.close(); \
print('Schnappschuss:', ziel.stat().st_size // 1024, 'KB')"
	docker run --rm -v $(VOLUME):/data -v "$$PWD/sicherung":/out alpine \
		tar czf /out/karo-$(STAMP).tar.gz -C /data \
		--exclude=config.json --exclude=session.key \
		--exclude=karo.db --exclude=karo.db-wal --exclude=karo.db-shm \
		backups scans eingang 2>/dev/null || \
	docker run --rm -v $(VOLUME):/data -v "$$PWD/sicherung":/out alpine \
		sh -c "cd /data && tar czf /out/karo-$(STAMP).tar.gz \
		--exclude=config.json --exclude=session.key \
		--exclude=karo.db --exclude=karo.db-wal --exclude=karo.db-shm ."
	@echo "Sicherung ohne Zugangsdaten: sicherung/karo-$(STAMP).tar.gz"

backup-alles:
	@echo "ACHTUNG: dieses Archiv enthält Ihren API-Schlüssel."
	@mkdir -p sicherung
	docker compose down
	docker run --rm -v $(VOLUME):/data -v "$$PWD/sicherung":/out alpine \
		tar czf /out/karo-vollstaendig-$(STAMP).tar.gz -C /data .
	@chmod 600 sicherung/karo-vollstaendig-$(STAMP).tar.gz
	@if docker image inspect karo:local >/dev/null 2>&1; then $(BUILD_COMPOSE) up -d; else docker compose up -d; fi
	@echo "Bitte an einem sicheren Ort ablegen, nicht in ein Repository."

# Stellt den Schnappschuss als aktive Datenbank wieder her.
restore:
	@test -n "$(ARCHIV)" || (echo "ARCHIV=sicherung/karo-....tar.gz angeben"; exit 1)
	docker compose down
	docker run --rm -v $(VOLUME):/data -v "$$PWD":/in alpine sh -c "\
		rm -rf /data/* && \
		tar xzf /in/$(ARCHIV) -C /data && \
		if [ -f /data/backups/karo-snapshot.db ]; then \
			cp /data/backups/karo-snapshot.db /data/karo.db; \
			echo 'Datenbank aus dem Schnappschuss wiederhergestellt.'; \
		else \
			echo 'WARNUNG: kein Schnappschuss im Archiv gefunden.'; \
		fi"
	@if docker image inspect karo:local >/dev/null 2>&1; then $(BUILD_COMPOSE) up -d; else docker compose up -d; fi
	@echo "Wiederhergestellt aus $(ARCHIV)."
	@echo "Enthielt das Archiv keine Zugangsdaten, fragt Karo sie beim Öffnen erneut ab."

shell:
	docker compose exec karo sh


# --------------------------------------------------------------------------
# Lokale Entwicklung
# --------------------------------------------------------------------------
#
# `dev` startet bewusst OHNE --reload: ein Prozess auf einem Port, damit nie
# unklar ist, welcher gerade antwortet. Dafuer braucht jede Aenderung an
# Python, Templates oder CSS einen Neustart. Wer lieber bequem hat, nimmt
# `dev-reload` — das laeuft als Aufseher plus Arbeiter, also zwei Prozesse
# auf demselben Port.

# Bewusst zwei ausgeschriebene Rezepte statt eines `define` mit `$(call)`:
# dort kommt eine zusaetzliche Expansionsrunde dazwischen, und die Dollar-
# Zeichen richtig zu stapeln ist niemandem zu erklaeren.

dev: dev-stop
	@KARO_DATA_DIR=$(DEV_DATA) KARO_DRIVE_DIR=$(DEV_DRIVE) \
	  nohup $(UVICORN) app.main:app --host 127.0.0.1 --port $(DEV_PORT) \
	  > $(DEV_LOG) 2>&1 & \
	  for i in $$(seq 1 60); do \
	    curl -sf --connect-timeout 1 -o /dev/null \
	      http://127.0.0.1:$(DEV_PORT)/login && break; \
	  done; \
	  if [ -z "$$(lsof -ti:$(DEV_PORT))" ]; then \
	    echo "Karo ist nicht hochgekommen. Letzte Zeilen aus $(DEV_LOG):"; \
	    tail -15 $(DEV_LOG); exit 1; \
	  fi; \
	  echo "Karo läuft: http://127.0.0.1:$(DEV_PORT)   PID $$(lsof -ti:$(DEV_PORT) | tr '\n' ' ')"; \
	  echo "Log:        $(DEV_LOG)"

dev-reload: dev-stop
	@KARO_DATA_DIR=$(DEV_DATA) KARO_DRIVE_DIR=$(DEV_DRIVE) \
	  nohup $(UVICORN) app.main:app --host 127.0.0.1 --port $(DEV_PORT) --reload \
	  > $(DEV_LOG) 2>&1 & \
	  for i in $$(seq 1 60); do \
	    curl -sf --connect-timeout 1 -o /dev/null \
	      http://127.0.0.1:$(DEV_PORT)/login && break; \
	  done; \
	  if [ -z "$$(lsof -ti:$(DEV_PORT))" ]; then \
	    echo "Karo ist nicht hochgekommen. Letzte Zeilen aus $(DEV_LOG):"; \
	    tail -15 $(DEV_LOG); exit 1; \
	  fi; \
	  echo "Karo läuft mit --reload: http://127.0.0.1:$(DEV_PORT)"; \
	  echo "PIDs:       $$(lsof -ti:$(DEV_PORT) | tr '\n' ' ')  (Aufseher + Arbeiter)"; \
	  echo "Log:        $(DEV_LOG)"

# Wartet, bis der Port wirklich frei ist. Ein --reload-Aufseher braucht dafuer
# mehrere Sekunden, und wer zu frueh startet, bekommt „address in use" und
# einen Server, der es gar nicht erst wird.
dev-stop:
	@lsof -ti:$(DEV_PORT) 2>/dev/null | xargs kill 2>/dev/null || true
	@for i in $$(seq 1 50); do \
	  lsof -ti:$(DEV_PORT) >/dev/null 2>&1 || break; \
	  sleep 0.4; \
	  lsof -ti:$(DEV_PORT) 2>/dev/null | xargs kill 2>/dev/null || true; \
	done
	@if lsof -ti:$(DEV_PORT) >/dev/null 2>&1; then \
	  echo "Port $(DEV_PORT) ist immer noch belegt:"; \
	  lsof -nP -iTCP:$(DEV_PORT) -sTCP:LISTEN; \
	  exit 1; \
	fi
	@echo "Port $(DEV_PORT) ist frei."

dev-log:
	@tail -f $(DEV_LOG)

dev-status:
	@lsof -nP -iTCP:$(DEV_PORT) -sTCP:LISTEN 2>/dev/null \
	  || echo "Auf Port $(DEV_PORT) läuft nichts."
