# syntax=docker/dockerfile:1
#
# Karo — ein Container, der auf dem Rechner der Familie läuft.
#
# Keine Zugangsdaten im Image. Keine Schlüssel, keine .env, kein config.json.
# Alles Geheime entsteht erst beim ersten Start im Volume unter /data.
#
# Zwei Bauvarianten:
#
#   make up                    volle Variante (~3,9 GB) — alle drei Ausgabemodi,
#                               inklusive eines echten Browsers im Bild für die
#                               NotebookLM-Anmeldung (siehe unten)
#   make up-klein              schlank (~320 MB) — nur Folien mit Stimme
#
# Der Unterschied ist ffmpeg plus die Sprachausgabe für die MP4-Ausgabe, dazu
# Xvfb/x11vnc/noVNC und ein eigenes Chromium für die NotebookLM-Anmeldung im
# Browser. Der HTML-Modus braucht nichts davon: er benutzt die Sprachsynthese
# des Betriebssystems im Browser.

FROM python:3.11-slim AS base

ARG MIT_MP4=1
ARG MIT_NOTEBOOKLM=1
ARG NODE_MAJOR=22

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    KARO_DATA_DIR=/data \
    KARO_DRIVE_DIR=/drive \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FUND=false \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers

WORKDIR /srv

# --- Systempakete -----------------------------------------------------------
# curl und ca-certificates werden für Node gebraucht, fonts-dejavu für die
# Folienbilder der MP4-Ausgabe. ffmpeg nur in der vollen Variante.
#
# xvfb/x11vnc/novnc/websockify: fuer die NotebookLM-Anmeldung IM Browser auf
# der Einstellungsseite, ohne dass jemand ein Terminal braucht. Xvfb ist ein
# Bildschirm ohne Monitor, x11vnc teilt ihn per VNC, websockify macht daraus
# eine WebSocket-Verbindung, die noVNC (ein reines JS/HTML-Programm) in einem
# iframe anzeigt. Alles nur auf 127.0.0.1 erreichbar und nur waehrend eine
# Anmeldung tatsaechlich laeuft — siehe app/media/notebooklm.py und
# docker-compose.yml.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg fonts-dejavu-core \
    && if [ "$MIT_MP4" = "1" ]; then \
        apt-get install -y --no-install-recommends ffmpeg; \
       fi \
    && if [ "$MIT_NOTEBOOKLM" = "1" ]; then \
        apt-get install -y --no-install-recommends \
            xvfb x11vnc novnc websockify; \
       fi \
    && rm -rf /var/lib/apt/lists/*

# Feste UID/GID (5000), nicht die naechste freie, und schon hier statt ganz
# am Ende: welche Nummer `--system` vergeben wuerde, haengt davon ab, welche
# Systempakete gerade installiert sind — jedes Mal, wenn sich das aendert,
# haette ein frueheres Image eine andere Nummer bekommen als die Dateien, die
# es im /data-Volume angelegt hat, und Karo kaeme beim Start nicht mehr an
# seine eigene Datenbank heran. Der Nutzer muss hier schon existieren, damit
# spaeter installierte, teils sehr grosse Dateien (Chromium) gleich mit der
# richtigen Eigentuemerschaft entstehen — ein chown in einer spaeteren Ebene
# wuerde sie in der Docker-Ebenen-Struktur sonst komplett verdoppeln.
RUN addgroup --gid 5000 karo \
    && adduser --disabled-password --uid 5000 --gid 5000 --home /srv --gecos "" karo

# --- Node und die Claude-Code-CLI ------------------------------------------
# Nötig für den Zugang über das Claude-Abo: Karo ruft `claude -p` als
# Unterprozess auf. Der API-Weg braucht das nicht, aber die CLI ist klein
# genug, dass beide Wege im selben Image Platz haben.
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x -o /tmp/node.sh \
    && bash /tmp/node.sh \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -f /tmp/node.sh \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @anthropic-ai/claude-code \
    && npm cache clean --force \
    && claude --version

# --- Python-Abhängigkeiten -------------------------------------------------
# notebooklm-py[browser] bringt Playwright mit; playwright install lädt dazu
# ein eigenes, getestetes Chromium samt Systembibliotheken — bewusst nicht
# Debians eigenes Chromium-Paket, weil Playwright auf eine genau passende
# Browser-Version pinnt und ein anderer Build leicht inkompatibel ist.
COPY requirements.txt requirements-mp4.txt requirements-notebooklm.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$MIT_MP4" = "1" ]; then \
        pip install --no-cache-dir -r requirements-mp4.txt; \
       fi \
    && if [ "$MIT_NOTEBOOKLM" = "1" ]; then \
        pip install --no-cache-dir -r requirements-notebooklm.txt \
        && playwright install --with-deps chromium \
        && chown -R karo:karo /opt/playwright-browsers \
        && rm -rf /var/lib/apt/lists/*; \
       fi

COPY --chown=karo:karo app ./app

# Nur die WORKDIR-Ebene selbst chownen, nicht rekursiv: app/ ist durch
# COPY --chown oben schon richtig — ein chown -R wuerde jede Datei darin
# trotzdem "beruehren" und damit erneut komplett in diese Ebene kopieren,
# selbst wenn sich der Eigentuemer gar nicht aendert (Copy-up in Docker
# reagiert auf den Zugriff, nicht auf eine tatsaechliche Aenderung).
RUN mkdir -p /data /drive \
    && chown karo:karo /srv \
    && chown -R karo:karo /data /drive
USER karo

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; \
      sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=4).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", \
     "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1"]
