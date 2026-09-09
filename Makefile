.DEFAULT_GOAL := hilfe
.PHONY: hilfe pull up up-klein publish down logs test backup backup-alles restore shell stimme \
        notebooklm-login

VOLUME := karo_karo-data
STAMP  := $(shell date +%Y%m%d-%H%M)
DOCKERHUB_REPO := farid1088/karo

# Beide Overlay-Aufrufe (up, up-klein) bauen lokal aus dem Quellcode statt
# das fertige Docker-Hub-Image zu ziehen — siehe docker-compose.build.yml.
BUILD_COMPOSE := docker compose -f docker-compose.yml -f docker-compose.build.yml

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
	@echo "make backup        Lerndaten sichern (OHNE Zugangsdaten)"
	@echo "make backup-alles  alles sichern, inklusive API-Schlüssel"
	@echo "make restore ARCHIV=sicherung/karo-....tar.gz"

# Für alle, die nicht selbst bauen wollen: zieht $(DOCKERHUB_REPO):latest
# und startet direkt — siehe docker-compose.yml.
pull:
	docker compose pull
	docker compose up -d
	@echo "Karo läuft auf http://127.0.0.1:8080"

up:
	$(BUILD_COMPOSE) up -d --build
	@echo "Karo läuft auf http://127.0.0.1:8080"

up-klein:
	KARO_MIT_MP4=0 $(BUILD_COMPOSE) up -d --build
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
	docker buildx build --platform linux/amd64,linux/arm64 \
		-t $(DOCKERHUB_REPO):$(VERSION) -t $(DOCKERHUB_REPO):latest --push .
	@echo "Veröffentlicht: $(DOCKERHUB_REPO):$(VERSION) und :latest (linux/amd64, linux/arm64)"

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
