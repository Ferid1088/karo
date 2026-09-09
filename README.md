# Karo

Lernbegleiter für ein Kind und ein Fach. Läuft ausschließlich auf dem eigenen
Rechner. Google Drive bleibt Archiv und Eingangskanal, alles andere passiert
lokal, und die Zugangsdaten verlassen den Rechner nie.

Karo liest die Blätter aus dem Unterricht, prüft daran den Stand je Thema,
erklärt die Lücken mit genau dem Rechenweg aus diesen Blättern und fragt
danach nach, bis das Thema sitzt.

---

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

## Zugang: das 20-€-Abo oder ein API-Schlüssel

Karo kann **beides**, die Wahl fällt bei der Einrichtung.

### Weg A — Claude-Abo (Pro/Max, ohne API-Schlüssel)

Auf dem Rechner einmalig:

```bash
npm install -g @anthropic-ai/claude-code
claude setup-token
```

Der Befehl zeigt einen langlebigen Token. Diesen bei der Einrichtung
einsetzen. Karo ruft danach die Claude-CLI im Hintergrund auf
(`claude -p --output-format json --json-schema …`) und rechnet über das Abo ab
— kein API-Schlüssel, keine Rechnung pro Aufruf.

Zwei Dinge dazu, offen gesagt:

* **Kontingent.** Das Abo hat Nutzungsfenster. Karos Aufrufe zählen mit. Ein
  Kind pro Tag liegt weit darunter; parallel eigenes Programmieren mit Claude
  Code kann in einen Deckel laufen. Karo zeigt dann eine klare Meldung und
  arbeitet den Vorgang später erneut ab.
* **Weitergabe.** Anthropic erlaubt Dritt-Entwicklern nicht, claude.ai-Login
  oder -Kontingente für ihre Produkte anzubieten. Für die eigene Familie ist
  das unproblematisch. Gibt jemand das Image an einen Freund weiter, der sein
  **eigenes** Abo und seinen **eigenen** Token einsetzt, nutzt jeder sein
  eigenes Kontingent — technisch saubere Trennung, aber der Bereich bleibt eine
  Grauzone der Nutzungsbedingungen. Für ein verkauftes Produkt ist es nicht
  zulässig; dafür ist Weg B da.

### Weg B — Anthropic-API-Schlüssel

Zu holen unter `console.anthropic.com` → *API Keys*. Rund ein Euro im Monat bei
täglicher Nutzung; die geschätzten Kosten stehen laufend unter *Protokoll*.
Dieser Weg ist der vorgesehene für alles außer der eigenen Familie.

Der Rest der Anwendung merkt von der Wahl nichts: beide Wege liegen hinter
demselben `ClaudeClient`. Ein Wechsel auf Bedrock, Vertex oder ein lokales
Modell ist eine neue Datei in `app/llm/` und ein Eintrag in einem Dictionary.

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

**Schritt 1 — Zugang.** Erst die Wahl zwischen Abo und API-Schlüssel, dann die
Zugangsdaten sowie Vorname und Klassenstufe des Kindes; beides bleibt auf
diesem Rechner. Karo prüft den Zugang sofort mit einem echten Aufruf und
speichert ihn nur, wenn er funktioniert. Bei falschen Daten erscheint eine
verständliche Meldung — beim Abo-Weg mit dem konkreten nächsten Schritt
(„Bitte am Rechner erneut `claude setup-token` ausführen") — und die Eingabe
bleibt offen.

**Schritt 2 — Modelle, Ausgabe, Ablage, Passwort.** Beim API-Weg fragt Karo
das Konto ab und zeigt nur freigeschaltete Modelle; beim Abo-Weg die drei, die
die CLI kennt. Dazu die Voreinstellung für die Ausgabe des Lernmaterials, wie
viel vom oberen Blattrand abgeschnitten wird, und ein Passwort für diese
Instanz — beim ersten Mal **Pflicht**, mindestens 8 Zeichen. Später unter
*Einstellungen* änderbar; dort ist das Feld optional, ein leeres Feld behält
das bestehende Passwort.

### Wo die Zugangsdaten liegen

Ausschließlich in `/data/config.json` im Docker-Volume auf Ihrem Rechner, mit
Dateirechten `0600`. Nicht im Image, nicht im Quellcode, nicht in Git, nicht in
den Protokollen — ein Formatter schwärzt Schlüssel- und Tokenmuster
einschließlich der in Fehlermeldungen und Tracebacks, bevor eine Zeile
geschrieben wird. Beim Start prüft Karo diese Schwärzung selbst und verweigert
sonst den Dienst.

Zugang wechseln oder löschen: *Einstellungen* → *Zugangsdaten löschen und neu
eingeben*.

---

## Drei Ausgabeformen für das Lernmaterial

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

An Anthropic gehen:

* das Bild des Blattes, zugeschnitten und verkleinert
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

58 Tests, ohne Netz und ohne Kosten: beide Zugangswege laufen gegen ein
gefälschtes Modell, der Abo-Weg gegen eine nachgebildete Claude-CLI, die prüft,
dass kein API-Schlüssel in der Umgebung steht und `--bare` nicht benutzt wird
(es würde die Abo-Anmeldung übergehen).

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
  llm/
    base.py       DER Vertrag: Protokoll, Ausnahmen, RawResult
    cli_backend.py   Abo-Weg über die Claude-CLI als Unterprozess
    api_backend.py   API-Weg über die anthropic-Bibliothek
    client.py     ClaudeClient — die einzige Naht zum Modell
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

Zwei Nähte tragen das Ganze: `app/llm/base.py` legt fest, was ein Backend
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
