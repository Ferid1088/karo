# Karo

Lernbegleiter für ein Kind und ein Fach. Läuft ausschließlich auf dem eigenen
Rechner. Google Drive bleibt Archiv und Eingangskanal, alles andere passiert
lokal, und die Zugangsdaten verlassen den Rechner nie.

Karo liest die Blätter aus dem Unterricht, prüft daran den Stand je Thema,
erklärt die Lücken mit genau dem Rechenweg aus diesen Blättern und fragt
danach nach, bis das Thema sitzt.

---

## Einfach durch den Alltag

Die Hauptnavigation hat drei Ziele: **Heute** zeigt den nächsten Lernschritt,
**Lernen** die Themen und angefangenen Runden, **Erfolge** den bestätigten
Lernstand. Auf der Lernseite steht die Erklärung direkt über dem Knopf für die
Fragen. Am Bildschirm erscheint jeweils eine Frage; Antworten werden auf dem
Gerät zwischengespeichert, damit eine Pause möglich ist. Ohne JavaScript bleibt
der vollständige Fragebogen als normales Formular nutzbar.

Unter **Für Eltern** sind Schulblätter, Themenfreigabe, Quellen, Klassenarbeiten,
ausführliche Berichte und Export, Einstellungen sowie Protokoll und erneute
Versuche erreichbar. Selten benötigte Optionen lassen sich aufklappen. Der
Elternbereich ordnet die Funktionen; er ist keine zusätzliche Passwortsperre.
Bewertungen brauchen weiterhin eine ausdrückliche Entscheidung je Antwort.

Der Klassenarbeitsplan ist auch direkt von **Heute** erreichbar. Lernmaterialien
lassen sich weiterhin in jeder Themenzeile erstellen und in einem eigenen Tab
öffnen. Materialarchiv, frühere Lernrunden, Papieraufgaben, Ausgabeformate und
Speicherpfad bleiben verfügbar.

## Der Ablauf

**1. Wissensbasis.** Erklärblätter und Aufgabenblätter werden fotografiert und
landen über Drive im Eingangsordner. Karo liest sie, erkennt, ob ein Blatt
erklärt oder fragt, zerlegt es in Abschnitte und legt es durchsuchbar ab. Das
ist die Faktenquelle für alles Weitere — Karo erfindet keinen Rechenweg.

**2. Themen.** Karo schlägt aus den Blättern Themen vor, ein Erwachsener gibt
sie frei oder legt eigene an. Ein Thema pro Zeile, wie im Schulheft.

**3. Prüfen.** Zu jedem Thema erzeugt Karo Fragen — am Bildschirm oder als
druckbares Blatt. Das Kind antwortet; bei Papier wird das ausgefüllte Blatt auf
derselben Seite abfotografiert. Karo schlägt je Frage eine Bewertung vor.

**4. Freigabe.** Nichts wird gespeichert, bevor ein Mensch jede Frage
bestätigt, korrigiert oder bewusst übersprungen hat.

**5. Flagge.** Aus den freigegebenen Antworten berechnet Karo je Thema eine
Flagge — mit einer festen Regel im Code, nicht durch das Sprachmodell. Die
Tabelle `Lernstand.xlsx` im Drive-Ordner zeigt sie farbig; in Drive öffnet sie
sich mit einem Klick als Google Sheet.

**6. Erklären.** Zu roten und gelben Themen baut Karo eine Lerneinheit aus zwei
Quellen: den eigenen Blättern (Fakten) und optional Fundstellen aus dem Netz
(nur Anregung, nur von einer festen Liste, nur nach Freigabe).

**7. Gegenprüfung.** Bevor das Kind die Erklärung sieht, prüft Karo sie gegen
das Schulmaterial. Widerspricht sie dem dort gelernten Weg, wird sie
**verworfen und neu geschrieben** — nicht angezeigt. Ein Kind, das zwei
Rechenwege gleichzeitig lernt, lernt keinen.

**8. Nachfragen im Kreis.** Nach dem Lernen kommen Verständnisfragen. Sitzt es
noch nicht, erklärt Karo eine Stufe einfacher und fragt neu — bis zu drei
Runden. Danach hört Karo auf: an dieser Stelle hilft ein Mensch mehr als eine
vierte Erklärung.

**9. Klassenarbeit.** Vorher friert Karo die Einschätzung ein, nachher wird
verglichen. Das ist die einzige echte Messung, ob das System funktioniert.

## Was Karo bewusst nicht tut

Es löst keine Aufgaben für das Kind, es setzt keine Flagge ohne menschliche
Freigabe, es benutzt keine Fundstelle ohne Freigabe, und es überträgt nichts
an den Hersteller.

---

## Zugang: der API-Schlüssel des KI-Anbieters

Der KI-Anbieter ist eine Konfigurationsentscheidung: `ai_provider` in
`config.json` wählt den Adapter (`"devin"` Standard, `"openrouter"` als
Alternative — siehe `docs/CONFIG.md`). Der Schlüssel des jeweils aktiven
Anbieters kommt **ausschließlich aus der Umgebung**, nie aus der
Konfigurationsdatei:

```bash
# .env neben der docker-compose.yml
DEVIN_API_KEY=…
# bzw. OPENROUTER_API_KEY=… bei ai_provider="openrouter"
```

Karo arbeitet asynchron: ein Auftrag legt einen Lauf beim Anbieter an,
parkt sich selbst (`not_before`), fragt später erneut nach und übernimmt
dann das strukturierte Ergebnis — synchrone Anbieter liefern direkt,
derselbe Weg. Eltern merken davon nichts — die Seite zeigt „in Arbeit",
bis das Ergebnis da ist. Fehlt der Schlüssel, bleiben alle Einstellungen
erreichbar und Karo meldet klar, was fehlt — es gibt keinen stillen
Fallback auf einen anderen Anbieter.

Alle Modellaufrufe laufen über die Fassade `AIClient` in `app/ai/` — kein
Modul spricht direkt mit einer Anbieter-API, kein Domain-Code kennt
Anbieter-Namen oder -Zustände.

---

## Installation

Voraussetzung: Docker Desktop (macOS, Windows) oder Docker Engine (Linux).

Zwei Wege — beide benutzen dieselbe `docker-compose.yml`:

### Weg 1 — fertiges Image, kein Quellcode nötig

Das Image liegt öffentlich auf Docker Hub als `farid1088/karo:latest`, für
Intel/AMD (Windows, die meisten Macs) **und** Apple Silicon gleichermaßen —
beim Pull wählt Docker automatisch die zur Maschine passende Variante. Kein
Build, keine Kompilierzeit, kein `git clone` des gesamten Quellcodes nötig:
`docker-compose.yml` genügt in einem leeren Ordner.

```bash
docker compose up -d
```

Das erste Mal lädt Docker das Image herunter (~3,9 GB, je nach Leitung
einige Minuten); danach startet Karo sofort.

### Weg 2 — selbst aus dem Quellcode bauen

Für eigene Änderungen am Code oder um `MIT_MP4`/`MIT_NOTEBOOKLM` beim Bauen
abzuschalten:

```bash
git clone <repository> karo
cd karo
```

### Drive-Ordner eintragen

Karo spricht **nicht** mit der Google-API. Es liest den Ordner, den der
Drive-Desktop-Client ohnehin auf den Rechner synchronisiert. Legen Sie in Ihrem
Drive einen Ordner `Karo` an und tragen Sie den Pfad in eine Datei `.env`
neben der `docker-compose.yml` ein:

```bash
# macOS
KARO_DRIVE_PATH=/Users/IHRNAME/Library/CloudStorage/GoogleDrive-ihre@mail.de/Meine Ablage/Karo

# Windows (Docker Desktop mit WSL2)
KARO_DRIVE_PATH=/mnt/g/Meine Ablage/Karo

# Linux
KARO_DRIVE_PATH=/home/ihrname/GoogleDrive/Karo
```

Ohne diesen Eintrag läuft Karo trotzdem — Blätter werden dann direkt in der
Oberfläche hochgeladen und die Tabelle liegt im Docker-Volume.

### Starten

```bash
docker compose up -d    # Weg 1: fertiges Image von Docker Hub ziehen
make pull                # dasselbe, als Makefile-Kurzform

make up                  # Weg 2: selbst bauen, alle Ausgabemodi, mit ffmpeg für MP4
make up-klein             # Weg 2: selbst bauen, schlank ohne MP4
```

Dann `http://127.0.0.1:8080` im Browser öffnen.

Für die MP4-Ausgabe zusätzlich einmal die deutsche Stimme laden — bewusst nicht
im Image, damit niemand etwas herunterlädt, der sie nie braucht:

```bash
make stimme
```

### Image veröffentlichen (nur für Maintainer)

Das Docker-Hub-Image `farid1088/karo:latest` wird mit `docker buildx` für
beide Architekturen in einem Schritt gebaut und veröffentlicht, damit es auf
Windows/Intel-Macs (`amd64`) genauso läuft wie auf Apple Silicon (`arm64`) —
ohne den Zwischenschritt macht `docker build` nur ein Image für die
Architektur der eigenen Maschine, das auf der jeweils anderen entweder gar
nicht oder nur langsam per Emulation läuft.

```bash
docker login                    # einmalig
docker buildx create --use      # einmalig, falls noch kein Builder existiert
make publish
```

---

## Einrichtung beim ersten Start

**Schritt 1 — Zugang.** Karo zeigt, ob der Schlüssel des gewählten
Anbieters gesetzt ist (z. B. `DEVIN_API_KEY`), und prüft die Verbindung
auf Wunsch mit einer echten Anfrage. Der Schlüssel wird nicht in der
Oberfläche eingetippt und nicht in `config.json` gespeichert — geändert
wird er in der Umgebung (`.env`), danach Neustart. Dazu Vorname und
Klassenstufe des Kindes; beides bleibt auf diesem Rechner.

**Schritt 2 — Ausgabe, Ablage, Passwort.** Die Voreinstellung für die Ausgabe
des Lernmaterials, wie viel vom oberen Blattrand abgeschnitten wird, und ein
Passwort für diese Instanz — beim ersten Mal **Pflicht**, mindestens 8 Zeichen.
Später unter *Einstellungen* änderbar; dort ist das Feld optional, ein leeres
Feld behält das bestehende Passwort.

### Wo die Zugangsdaten liegen

Der Provider-Schlüssel lebt nur in der Umgebung (`.env`), niemals in
`/data/config.json`. Die übrigen Einstellungen liegen in `/data/config.json`
im Docker-Volume auf Ihrem Rechner, mit Dateirechten `0600`. Nichts davon im
Image, im Quellcode, in Git oder in den Protokollen — ein Formatter schwärzt
Schlüssel- und Tokenmuster einschließlich der in Fehlermeldungen und
Tracebacks, bevor eine Zeile geschrieben wird. Beim Start prüft Karo diese
Schwärzung selbst und verweigert sonst den Dienst.

Schlüssel wechseln: die Variable in `.env` ändern und den Container neu
starten. Anbieter wechseln: `ai_provider` in `config.json` plus die
Secret-Variable des neuen Anbieters — kein Code-Diff.

---

## Protokolle und Fehlersuche

Karo schreibt eine JSON-Zeile pro Eintrag nach stdout, Docker sammelt sie
(`docker logs karo`). Jede Zeile trägt Zeitstempel, Level, `git_sha` und —
während einer Anfrage — eine `request_id`; Hintergrundarbeit trägt eine
`job_id`. Ein Aufruf des Lehrplan-Dienstes geht mit derselben Kennung raus
(`X-Request-Id`, bei Jobs `job-<id>`), sodass sich ein Vorgang über beide
Dienste verfolgen lässt: `docker logs curriculum-api | grep request_id=…`.

Die technischen Zeilen sind bewusst vergänglich — Docker rotiert bei
3 × 20 MB. Was dauerhaft bleiben muss, liegt nicht im Log, sondern in der
Datenbank:

- **Lernablauf** — `lern_ereignis` (jeder Übergang mit Anlass und
  Begründungsdaten, z. B. `erfolge`/`schwelle` am Mastery-Gate) und
  `lern_antwort` (Antwort, Phase, aktive Sekunden). Für eine Sitzung:
  `SELECT * FROM lern_ereignis WHERE sitzung_id = ?`.
- **Betriebsstörungen** — `betriebsmeldung` (dedupliziert nach Bereich und
  Text, mit erstem/letztem Auftreten und Zähler): Lehrplan-Dienst-Fehler,
  ungefangene Serverfehler (`bereich='http-500'`, nur Weg und Fehlertyp —
  die Meldung selbst könnte Inhalte enthalten und bleibt im rotierenden
  Log).
- **Hintergrundjobs** — `job`-Tabelle: Typ, Payload, Versuche,
  `last_error`, Zeitstempel. Ein späterer Fehler ist über die `job_id` in
  den Logzeilen und über die Zeile selbst rekonstruierbar.

Fehlersuche damit: `request_id` aus den Logs (`grep '"request_id": "…"'`)
→ dazugehörige `lern_sitzung_id` in `lern_ereignis`, Job-Ausfall in
`job`/`betriebsmeldung`.

---

## Drei Ausgabeformen für das Lernmaterial

Im Bereich **Klassenarbeit → Lernplan** lässt sich neues Material
direkt in der Themenzeile erstellen. Der Fortschritt erscheint in dieser Zeile;
der fertige Link öffnet das Material mit Lernkontrolle in einem eigenen Tab.
Der Klassenarbeit-Tab bleibt dabei unverändert. Jede Erstellung gehört zu ihrer
Lernplanzeile und erhält einen Namen mit Thema, Erklärungsinhalt, Datum und
eindeutiger Materialkennung.

Die Lernkontrolle vergleicht bestätigte Antworten nach dem Material mit der
zuletzt bewerteten Fragerunde vor der Erstellung. Ohne vollständigen
Ausgangswert wird nur das aktuelle Verständnis ausgewiesen; ein Lernzuwachs wird
dann nicht behauptet.

Unter **Einstellungen → Schulblätter & Speicher → Datenbank für Lernmaterialien**
kann ein absoluter Pfad zu einer SQLite-Datei festgelegt werden. Standard:
`/data/lernmaterialien.sqlite3` (bzw. im mit `KARO_DATA_DIR` gewählten Ordner).
Diese Datenbank enthält auch die fertigen HTML-/Videodateien. Beim Pfadwechsel
übernimmt Karo das Archiv und vorhandene ältere Materialdateien; die bisherige
Datenbank bleibt als Sicherung liegen. Das neue Ziel muss ein freier Dateiname
sein. In Docker beziehen sich die Pfade auf den Container; externe Zielordner
müssen als dauerhaftes Volume eingebunden sein.

Die Materialdatenbank zusätzlich in die eigene Sicherung aufnehmen, besonders
bei einem Pfad außerhalb von `/data`. Das bisherige `make backup` sichert die
Hauptdatenbank und Schulblätter, nicht automatisch ein externes Materialarchiv.

Die Wahl fällt **je Lerneinheit**, nicht einmal bei der Einrichtung — vor dem
Erzeugen, auf der Themenseite.

| Modus | Was entsteht | Voraussetzung |
|---|---|---|
| **Folien mit Stimme** (Standard) | eine autarke HTML-Datei: Folien zum Mitlesen, Vorlesen über die Sprachausgabe des Browsers, blättert selbst weiter | keine |
| **Video (MP4)** | dieselben Folien als Video mit gesprochener Erklärung, offline erzeugt (Piper + ffmpeg) | `make up` und `make stimme` |
| **NotebookLM** | Karo lässt ein Google-NotebookLM-Video-Overview erzeugen und legt es als MP4 ab | einmalige Anmeldung, Google-Konto |

### NotebookLM

Für Privatkonten gibt es keine offizielle Schnittstelle. Karo nutzt dafür
[`notebooklm-py`](https://github.com/teng-lin/notebooklm-py) — ein
Gemeinschaftsprojekt, das über die Sitzungs-Cookies eines echten
Google-Logins arbeitet, nicht über eine von Google unterstützte API. Das
bedeutet: die Anmeldung läuft irgendwann ab, bricht bei Änderungen an
Googles Oberfläche und lässt sich nicht weitergeben — jede Familie richtet
sie selbst ein. Deshalb ist dieser Modus optional, ausdrücklich
gekennzeichnet und nie Voraussetzung. Fällt er aus, weicht Karo automatisch
auf Folien mit Stimme aus und schreibt in die Lerneinheit, warum.

**Anmeldung — direkt im Browser, kein Terminal nötig.** Auf der
Einstellungsseite: „Jetzt anmelden“ klicken. Karo baut sich dafür selbst
einen Bildschirm ohne Monitor (Xvfb), öffnet darin Chromium mit dem
NotebookLM-Login und zeigt das Ganze als eingebettetes Fenster direkt auf
der Seite an (über x11vnc + noVNC, nur über `127.0.0.1` erreichbar, nur
während die Anmeldung tatsächlich läuft). Die Familie klickt sich dort durch
den echten Google-Login; Karo bekommt nie ein Passwort zu Gesicht. Deshalb
ist die volle Variante des Images spürbar größer (~3,9 GB) — sie enthält ein
eigenes, von Playwright getestetes Chromium.

Die Sitzung landet in `./notebooklm-lokal/` — genau der Ordner, den
`docker-compose.yml` in den Container nach `/data/notebooklm` einhängt.
Karo liest diese Sitzung bei jedem Aufruf neu; es gibt kein Passwort und
kein Cookie in Karos eigener Konfiguration oder Datenbank. Läuft die
Sitzung ab, meldet Karo das auf der Einrichtungsseite — „Jetzt anmelden“
reicht dann erneut.

Wer den Browser nicht im Image haben will (kleineres Image, dafür Anmeldung
nur manuell), baut mit `KARO_MIT_NOTEBOOKLM=0 make up` und meldet sich
stattdessen auf dem eigenen Rechner an:

```
pip install "notebooklm-py[browser]"
make notebooklm-login
```

Das schreibt dieselbe Sitzungsdatei — der Container liest sie unabhängig
davon, welcher der beiden Wege sie erzeugt hat.

---

## Recherche: was Karo im Netz sucht

Zwei Quellen gehen in eine Erklärung ein — die eigenen Blätter und, wenn
erlaubt, Fundstellen aus dem Netz. Für die Fundstellen gelten drei Regeln:

* **Feste Quellenliste.** Gesucht wird nur auf Seiten für deutschen
  Schulunterricht (Serlo, Studyflix, simpleclub, Planet Schule, BR alpha
  Lernen, Schlaukopf u. a.), bei YouTube nur auf bekannten Schulkanälen —
  Lehrerschmidt, Daniel Jung, musstewissen und weitere. Die Liste steht in
  `app/research.py`; sie zu erweitern ist eine Codeänderung, und das ist
  Absicht.
* **Freigabe.** Kein Fund wird automatisch benutzt. Er erscheint unter
  *Recherche* als Vorschlag, ein Erwachsener hakt ihn ab.
* **Anregung, keine Faktenquelle.** Auch ein freigegebener Fund geht nur als
  Titel in die Erklärung ein. Die Fakten kommen aus dem Schulmaterial.

Ohne Recherche funktioniert Karo vollständig; sie ist ein Zusatz und
abschaltbar.

---

## Ordner in Drive

```
Karo/
├── 01_Eingang/           Blätter vom Handy hier ablegen
├── 02_Verarbeitet/       Originale nach dem Einlesen, nach Monat sortiert
├── 03_Lernmaterial/      erzeugte Folien, Videos, Fragebogen, druckbare Blätter
├── 04_Nicht_lesbar/      was sich nicht aufbereiten ließ
└── Lernstand.xlsx        Flaggen je Thema, Verlauf, Erklärung der Regel
```

Ein Kurzbefehl auf dem iPhone, der die Kamera öffnet und direkt in
`01_Eingang` speichert, ist die zuverlässigste Art, den Alltag am Laufen zu
halten. HEIC wird unterstützt.

`Lernstand.xlsx` wird bei jeder Freigabe neu geschrieben. Änderungen darin
gehen verloren — die Wahrheit steht in Karo, nicht in der Tabelle.

---

## Datenschutz

An den KI-Anbieter gehen — nur Text, niemals Bilder:

* Klassenstufe, Fach und Thema
* der abgelesene Text der Blätter und die Antworten des Kindes im Wortlaut
* die Themenliste und, für den Lernplan, die Flaggen samt Fehlerzahlen

**Nicht** übertragen werden Name, Schule, Geburtsdatum und Lehrkraft, soweit
Karo sie erkennt. Der eingetragene Vorname wird nur lokal gespeichert und dient
genau dazu: Karo entfernt ihn aus allem, was hinausgeht (`app/pii.py`), dazu
Kopfzeilenmuster wie „Name:" und „Klasse 7b", Schul- und Lehrkraftangaben,
Geburtsdaten, E-Mail-Adressen und Telefonnummern.

Was Karo **nicht** garantieren kann: einen Namen, der im Bild außerhalb des
abgeschnittenen Randes steht — in einer Fußzeile, auf einem Stempel oder mitten
in der Antwort. Ein Filter kann nicht wissen, dass „Milena" in einer Textaufgabe
diesmal die Schülerin ist. Unter *Protokoll* sehen Sie zu jedem Aufruf den
gesendeten Text im Wortlaut; das gesendete Bild sehen Sie je Blatt auf der
Freigabeseite.

Datenbank, Wissensbasis, Lernmaterial und Protokolle liegen ausschließlich im
Docker-Volume auf Ihrem Rechner. Karo hat keinen Server des Herstellers, keine
Telemetrie und keinen Konto-Zwang.

Für die private Nutzung in der eigenen Familie greift die Haushaltsausnahme der
DSGVO. Sobald Karo für andere Haushalte oder in einer Schule eingesetzt wird,
ändert sich die rechtliche Lage grundlegend — DSGVO für Minderjährigendaten,
Schulrecht der Länder, Einstufung nach Annex III des EU AI Act. Diese Prüfung
gehört vor die erste Zeile Produktcode für eine solche Version.

---

## Sicherung

```bash
make backup                                  # nach ./sicherung/, ohne Zugangsdaten
make backup-alles                            # inklusive Zugangsdaten
ARCHIV=sicherung/karo-20260906-1200.tar.gz make restore
```

`make backup` schreibt einen konsistenten Schnappschuss der Datenbank und packt
ihn zusammen mit den Blättern. Zugangsdaten sind bewusst nicht enthalten — nach
einer Wiederherstellung fragt Karo sie erneut ab. Testen Sie die
Wiederherstellung einmal, solange nichts kaputt ist. Ein ungetestetes Backup
ist kein Backup.

---

## Tests

```bash
make test
```

Die Tests laufen ohne Modellkosten: ein nachgebildeter Anbieter-Dienst
(`FakeAI` in `tests/conftest.py`) bildet den echten Lebenszyklus beider
Adapter nach — asynchrone Sessions anlegen, parken, pollen, Ergebnis
abholen, und synchrone Completions.

Die wichtigsten:

| Test | Was er beweist |
|---|---|
| `test_widerspruch_zur_schule_wird_verworfen_nicht_gezeigt` | eine Erklärung, die dem Schulweg widerspricht, wird neu geschrieben statt angezeigt |
| `test_eine_falsche_antwort_erzeugt_kein_rot` | die Flaggenregel ist eine Funktion, keine Bitte an ein Sprachmodell |
| `test_zwei_saubere_uebungstage_ergeben_gruen` | Grün wird in Übungstagen gerechnet, nicht in Zeilen |
| `test_ein_guter_tag_beendet_den_zyklus_noch_nicht` | eine fehlerfreie Runde direkt nach der Erklärung schließt nichts ab |
| `test_recherche_haelt_sich_an_die_erlaubnisliste` | das Modell kann keine Quelle einschmuggeln |
| `test_host_header_umgeht_die_zugangskontrolle_nicht` | die Zugangskontrolle hängt nicht am Host-Header |
| `test_obergrenze_beendet_den_zyklus` | nach drei Runden hört Karo auf |

---

## Aufbau

```
app/
  main.py         FastAPI, Routen, Einrichtungsweiche, Zugangskontrolle, CSRF
  ai/
    base.py       DER Vertrag: Ausnahmen, AIPending
    types.py      AIRequest/AIRun — das neutrale Auftrags- und Laufmodell
    provider.py   AIProvider-Protokoll: start/poll
    registry.py   Anbieter-Auswahl — einzige Stelle, die Namen auflöst
    http.py       gemeinsame HTTP-Ebene + Fehler-Einordnung der Adapter
    runs.py       ai_run — persistierte Lauf-Kennungen
    client.py     AIClient — die einzige Naht zum Modell, mit Audit
    providers/    Adapter — alles API-spezifische lebt nur hier
      devin.py        asynchron per Session (Standard)
      openrouter.py   synchron per Chat-Completions
  config.py       Zugangsdaten und Einstellungen, atomar in /data/config.json
  prompts.py      Prompts und Antwortschemata
  pii.py          Entfernt personenbezogene Angaben vor jedem Aufruf
  domain.py       Fehlertypen, Flaggenregel als reine Funktion
  kb.py           Wissensbasis: Abschnitte, Volltextsuche, Lehrmaterial
  topics.py       Themen: Vorschlag, Freigabe, Zuordnung
  quizzes.py      Fragen, Antworten, Freigabe, Flagge neu berechnen
  teaching.py     Lernzyklus: erklären, gegenprüfen, nachfragen, wiederholen
  research.py     Websuche mit Quellenliste und Freigabepflicht
  media/          Folien, Sprachausgabe, MP4, NotebookLM-Bündel, Tabelle
  ingest.py       Drive-Ordner einlesen, Bilder aufbereiten
  jobs.py         Warteschlange in der Datenbank, mit Wiederholungsabstand
  db.py           SQLite — der einzige Ort mit SQL
  security.py     Passwort, CSRF, Schwärzung im Protokoll
  export.py       Lernstand.xlsx in den Drive-Ordner
  schema.sql      Schema, inklusive Trigger gegen Änderungen an Antworten
```

Zwei Nähte tragen das Ganze: `app/ai/base.py` legt fest, was ein Anbieter
können muss, und `app/domain.py` entscheidet über Flaggen — ohne Modell.

---

## Die Flaggenregel

Sie steht in `app/domain.py` und ist der Kern des Produkts:

| Flagge | Bedingung |
|---|---|
| **Lücke (rot)** | 2× derselbe Verständnisfehler in den letzten 5 Antworten |
| **sitzt (grün)** | die letzten 2 Übungstage vollständig fehlerfrei **und** insgesamt mindestens 3 richtige Antworten |
| **wackelig (gelb)** | gemischtes Bild — der Normalzustand beim Lernen |
| **noch nicht geprüft (weiß)** | weniger als 2 verwertbare Antworten |

Gerechnet wird in **Tagen**, nicht in Zeilen: ein Blatt liefert fünf bis zehn
Antworten am selben Tag, und eine zeilenbasierte Regel wäre nie erreichbar
gewesen. Das hat auch einen pädagogischen Grund: wer direkt nach der Erklärung
dieselben drei Aufgaben löst, hat sich die Erklärung gemerkt, nicht das Thema
gelernt. Rechenfehler und Flüchtigkeit lösen nie eine Lücke aus. Alle Schwellen
stehen in `config.json`; nach dem Speichern der Einstellungen berechnet Karo
alle Flaggen neu.

---

## Was vor dem täglichen Einsatz noch fehlt

Eine Zahl, die dieses Projekt nicht kennt: **wie gut Handschrift erkannt wird.**
Alles andere hängt daran. Zehn echte Blätter einlesen, jede Bewertung mit der
eigenen Einschätzung vergleichen, die Übereinstimmung unter *Protokoll* ablesen.
Liegt sie unter etwa 80 %, ist die Freigabe keine Formalie, sondern die
eigentliche Arbeit — dann ist Karo ein Aufschreibewerkzeug und noch kein
Diagnosewerkzeug. Diese Messung ist der Grund, warum die Freigabe nicht
abschaltbar ist.

## Meine Woche

Ein gemeinsamer Wochenplan mit Ziel, Routine und Elternzusage ergänzt Karo.
Das Kind findet **Meine Woche** in seiner Navigation; Eltern öffnen die neue
Karte auf ihrer Übersicht. Hilfe, Pause und Rückmeldungen bleiben innerhalb
von Karo und verändern keine Lernstände.

[Bedienung, Startbefehle, Migration und Prüfliste](docs/meine-woche.md)

## Meine Welt

Kinder nennen zuerst ein aktuelles Interesse. Karo macht daraus drei passende,
vollständig spielbare Ideen; das Kind wählt eine und die Eltern sehen genau
diese Vorschau zur Freigabe. Die aktive Welt übernimmt Karos nächsten echten
Lernschritt. Bei neuen Lernmaterialien dürfen Geschichte und Beispiele zum
Interesse passen, während Fachinhalt und Lösungen weiterhin aus den geprüften
Schulunterlagen kommen. Interessen lassen sich jederzeit wechseln oder
pausieren; fertige Werke bleiben erhalten.

[Ablauf, Datenschutz, technische Grenzen und Prüfliste](docs/interessenwelten.md)

## Vertrag mit dem Lehrplan-Dienst ändern

Das Lektionsformat liegt als eigenständiges Paket in `karo_contract/`. Der
Lehrplan-Dienst (`karo-curriculum-team`) installiert es und prüft damit, bevor
eine Lektion „fertig“ wird. So gibt es **eine** Prüfung statt zwei.

Vorher gab es zwei: der Dienst gab eine Lektion frei, Karos Import lehnte sie
ab, und nach zwei Ablehnungen gab der Dienst das Thema dauerhaft nicht mehr
heraus — obwohl am Inhalt nie etwas falsch war.

Das Paket hängt an nichts aus `app/`, an keiner Datenbank und an keinem
Web-Rahmen. Das ist keine Stilfrage: sonst lässt es sich dort nicht
installieren. `tests/test_karo_contract_paket.py` hält das fest.

Reihenfolge, wenn sich am Format etwas ändert:

1. `karo_contract.CONTRACT_VERSION` erhöhen (z. B. auf `karo-adaptiv-v1.2`),
   committen, pushen.
2. Taggen: `git tag -a contract-v1.2 -m "…" && git push origin contract-v1.2`.
   Der Dienst installiert genau dieses Tag, nie `master` — sonst zöge ein
   beliebiger Commit hier still seine Prüfung mit.
3. Im Dienst die neue Fassung eintragen (`CONTRACT_VERSION`, `requirements.txt`,
   `pyproject.toml`) und **beide CIs** grün bekommen.
4. **Den Dienst zuerst ausrollen**, `kcteam doctor` grün, **erst dann Karo.**

Läuft Karo voraus, ist das nicht schlimm: es merkt den Unterschied an
`GET /v1/meta`, stellt seine Aufträge zurück und sagt es im Elternbereich.
Was es nie tut, ist ablehnen — eine Ablehnung zählt beim Dienst gegen das
Thema.

> **Ein Tag wird nie verschoben.** Wer ihn bewegt, ändert, was ein bereits
> gebautes Image installiert hat — und Docker merkt es nicht: die pip-Ebene
> hängt am Text der `requirements.txt`, nicht am Inhalt des Tags. Der Dienst
> lief danach weiter mit dem alten Paket, meldete aber die neue Fassung.
> Jede Änderung am Vertrag bekommt eine neue Nummer und einen neuen Tag.
