# Karo – Prompts Schritt für Schritt

Reihenfolge einhalten. Einen Prompt erst geben, wenn der vorige **fertig** ist (Bedingung steht jeweils unten).
Erledigt: Runde 1 (Vertrag), Runde 2 (Container-SHA, Fail-closed, Vertragsversion, CI, Dockerfile, Kontingent),
Schritt 1 (karo 130285a). Deployment und Brücke übernimmt Schritt 1b.

Jeder Prompt beginnt mit demselben Rahmen – bei einer neuen Agent-Sitzung immer mitgeben:

```text
Rahmen: Repos karo und karo-curriculum-team. Arbeitsweise: Tests zuerst, kleine Commits,
nichts Unbeteiligtes ändern, beide Repos pushen, am Ende Bericht (geändert / Tests / offen).
Grundregeln von Karo: Kein Bild und keine Familien-/Kinderkennung geht je an ein KI-Modell.
Karo bewertet und begleitet Kinder ohne KI; KI erzeugt nur Inhalte im Curriculum-Dienst.
```

---

## Schritt 1 – Keine Bilder mehr an Claude

```text
Ziel: Sofortiger Datenschutzschritt. Kein Foto geht mehr an ein KI-Modell.

- kb_extract, exam_scan_read, quiz_read_sheet: kein image_path mehr an den LLM-Client.
- quiz_read_sheet (Handschrift) entfällt ganz: Antworten gibt das Kind in der App ein.
  Den Papierweg in der Oberfläche entfernen oder als "nicht mehr verfügbar" kennzeichnen.
- kb_extract und exam_scan_read arbeiten bis Schritt 2 mit manueller Eingabe: Eltern/Kind
  wählen Fach und Thema aus der Liste bzw. tragen das Prüfungsdatum ein.
- Architekturtest: kein Codepfad ruft client().complete(... image_path=...) auf, und der
  LLM-Client hat keinen Bild-Parameter mehr.
```
**Fertig, wenn:** Test grün, App läuft ohne Bildaufrufe, Upload → manuelle Themenwahl funktioniert.

---

## Schritt 1b – Deployment und Brücke (damit im Alltag nichts auffällt)

```text
Ziel: Schritt 1 läuft live, und Karo bleibt bis Schritt 2 voll benutzbar, ohne dass die
Familie etwas umstellen muss.

1. Deployment übernimmst du selbst
   - Laufende Instanz auf den Stand 130285a (oder neuer) bringen: Image bauen, Container neu
     starten, danach prüfen: /health zeigt den gepushten SHA, kein Codepfad schickt Bilder
     (Architekturtest), Login, Heute und eine Lerneinheit funktionieren (Rauchtest).
   - Vorher ein Backup der Daten (Volume/SQLite), bei Fehlschlag automatisch auf das alte Image
     zurück. Mir nur das Ergebnis melden.

2. Brücke bis Schritt 2: Blatt als Text
   - Beim Hochladen zusätzlich ein Feld "Text vom Blatt einfügen oder abtippen" (optional,
     vorbelegt leer). Dieser Text läuft über GENAU den Weg, den Schritt 2 später nutzt:
     POST /blatt/text → pii.scrub() → Thema per Regeln/Katalog → Top-3 → Bestätigung, und
     füllt kb_chunk wieder, damit die Wissensbasis nicht leer bleibt.
   - Ist kein Text da, bleibt es beim eingetippten Thema wie jetzt.
   - Die Fehlermeldung "Wissensbasis füllt sich nicht" durch einen freundlichen Hinweis
     ersetzen, der auf das Textfeld zeigt.
   - Wenn Schritt 2 fertig ist, füllt das Browser-OCR dasselbe Feld automatisch; die Familie
     merkt nur, dass sie nichts mehr abtippen muss.
```
**Fertig, wenn:** Live-Instanz läuft auf neuem SHA, Rauchtest grün, Text-Brücke füllt die Wissensbasis.

---

## Schritt 2 – OCR im Browser (Foto bleibt auf dem Gerät)

```text
Ziel: Arbeitsblätter werden im Browser gelesen. Zum Server geht nur gefilterter Text.

1. Foto UND PDF auf JEDEM Gerät (iPad/iPhone Safari, Android Chrome, Windows/Mac/Linux in
   Chrome, Edge, Firefox, Safari):
   - Zwei Knöpfe: "Blatt fotografieren" (<input accept="image/*" capture="environment">) und
     "Datei wählen" (<input accept="image/*,application/pdf">, OHNE capture – sonst lässt iOS
     nur die Kamera zu und kein PDF aus der Dateien-App). Am PC zusätzlich Drag & Drop.
     Hat das Gerät keine Kamera, wird nur "Datei wählen" gezeigt.
   - Formate: JPG, PNG, WEBP, HEIC/HEIF (iPhone-Fotos; im Browser mit selbst gehostetem
     heic2any umwandeln, sonst Server-Rückfall), PDF.
   - Vor dem Fotografieren eigener Hinweis-Bildschirm: warum Karo die Kamera braucht, dass das
     Foto auf dem Gerät bleibt und nur Text ohne Namen übertragen wird.
2. Auf dem Gerät per Canvas: EXIF-Drehung, verkleinern, Kontrast, Kopfbereich
   (header_crop_percent) abschneiden.
3. Tesseract.js mit deu + eng. Worker, WASM und traineddata SELBST hosten unter /static/ocr/,
   nichts von CDNs. Caching per Service Worker. Fortschrittsanzeige.
4. Pro Wort Konfidenz auswerten, unsichere Wörter verwerfen (filtert auch Handschrift).
   Zu wenig sicherer Text → "Bitte neu fotografieren" mit Tipps.
5. POST /blatt/text {text, fach, ocr_konfidenz} – kein Bild. Server: pii.scrub(), Thema
   per Regeln/Katalog zuordnen, Top-3 zurück. Kind/Eltern bestätigen mit einem Klick,
   sonst Auswahl aus der Liste. Rohtext nicht dauerhaft speichern.
6. Rückfall ohne WASM: Upload an den Server, dort lokales Tesseract, Bild sofort löschen.
   Den Eltern vorher sagen, dass das Foto in diesem Fall kurz auf den Server geht.
7. PDF und PC: Dateiauswahl mit accept="image/*,application/pdf" (am PC ohne Kamera nur
   Dateiauswahl, auch Drag & Drop). PDF wird ebenfalls im Browser gelesen, mit pdf.js
   (selbst gehostet unter /static/pdfjs/, kein CDN):
   - Seite hat eine Textebene → Text direkt übernehmen, kein OCR (schneller und fehlerfrei).
   - Seite ohne Textebene (eingescannt) → Seite mit pdf.js auf ein Canvas rendern → Tesseract.js.
   - Gemischte PDFs Seite für Seite entscheiden. Seitenlimit (z. B. 20), Fortschritt pro Seite.
   - Mehrseitige PDFs: jede Seite als eigenes Blatt, Eltern können Seiten abwählen.
   - Kopfbereich/Namensfeld auch bei PDF-Text entfernen (erste Zeilen jeder Seite + pii.scrub()).
   Rückfall auf dem Server: pypdfium2 für die Textebene, Tesseract für gescannte Seiten,
   Datei sofort löschen.
8. Testsatz tests/ocr_fixtures (echte Fotos UND PDFs – mit Textebene, gescannt, gemischt –
   ohne echte Namen). Zielwert: richtiges Thema unter den Top 3 in ≥ 90 %, getrennt
   ausgewiesen für Foto, PDF mit Text und gescanntes PDF. Läuft in der CI.
   Gerätematrix: Playwright-Tests mit chromium, firefox und webkit sowie Mobil-Emulation
   (iPad, iPhone, Android) für Foto, HEIC, PDF mit Text und gescanntes PDF. Dazu eine
   Checkliste docs/GERAETETEST.md für echte Geräte (iPad, Android-Tablet, Windows-PC, Mac),
   die ich selbst abhake.
9. PyMuPDF (AGPL) durch pypdfium2 ersetzen.
Datenschutzerklärung und Hilfe-Seite anpassen.
```
**Fertig, wenn:** gemessene Trefferquote im Bericht, Zielwert erreicht oder Abweichung begründet.

### Antwort an den Agenten zu Schritt 2 (nach seiner Rückfrage)

```text
Antworten zu deinen Fragen aus Schritt 2:

1. Repo-Größe: Die OCR-/PDF-Dateien kommen NICHT ins Repo. Ein Build-Schritt holt sie beim
   Image-Bau in festen Versionen aus dem npm-Registry (tesseract.js, tesseract.js-core,
   pdfjs-dist, heic2any) und die traineddata deu+eng (tessdata_fast) aus einer festen Release-
   Version, prüft jede Datei per SHA-256 gegen eine eingecheckte Prüfsummenliste und legt sie
   unter /static/ocr/ und /static/pdfjs/ ab. Zur Laufzeit lädt der Browser alles nur von
   unserem eigenen Server – kein CDN. Bei falscher Prüfsumme bricht der Build ab.

2. Testmaterial ohne Aufwand für mich: Nutze die Blätter, die Karo bereits hat (scans_dir
   und 02_Verarbeitet auf dieser Maschine), NUR lokal:
   - `make ocr-report` liest sie aus einem lokalen, per .gitignore ausgeschlossenen Ordner,
     schneidet den Kopfbereich ab, lässt OCR laufen und vergleicht mit dem Thema, das für
     dieses Blatt schon bestätigt in der Datenbank steht.
   - Kein echtes Blatt und kein Text daraus kommt je ins Repo, in die CI oder an eine KI.
     Ins Repo kommt nur die Kennzahl (Trefferquote pro Art: Foto, PDF mit Text, gescanntes PDF).
   - Für die CI: wenige synthetische Dateien als Rauchtest, damit der Ablauf geprüft ist.
   - Reichen die vorhandenen Blätter für eine Art nicht (z. B. keine PDFs), sag mir nur, was
     fehlt; alles andere läuft weiter.
   Die Fertig-Bedingung (Trefferquote ≥ 90 %) wird mit diesem lokalen Bericht geprüft.
```

---

## Schritt 3 – Lernkreislauf beschreiben (nur dokumentieren)

```text
Ziel: Festhalten, was Karo heute beim Prüfen und Begleiten tut. Keine Codeänderung.

Schreib docs/LERNKREISLAUF.md: Thema erkannt → Einstufung → Lernplan → Erklärung → Beispiel →
geführte Aufgabe → selbstständige Aufgabe → Mini-Test → Anpassung → Abschluss.
Pro Schritt: Eingang, Entscheidungsregel (wann schneller, langsamer, andere Erklärung, zurück
zur Voraussetzung, Wiederholung), Ausgang, zuständige Datei/Funktion.
Dokumentiere den IST-Stand. Wo Code und Absicht auseinanderlaufen oder eine Regel fehlt:
als Liste "Zur Entscheidung" am Ende, NICHT still reparieren.
Danach anhalten und auf meine Freigabe warten.
```
**Fertig, wenn:** Du hast das Dokument gelesen und die Liste "Zur Entscheidung" beantwortet.

---

## Schritt 4 – Fehlende Lernregeln umsetzen

```text
Ziel: Die in LERNKREISLAUF.md freigegebenen Entscheidungen umsetzen.
Meine Entscheidungen: <HIER DEINE ANTWORTEN AUS SCHRITT 3 EINFÜGEN>

Vorgaben, falls noch nicht vorhanden:
- Mastery-Wert pro Kind und Konzept (Elo: Kind gegen Aufgabe), deterministisch, erklärbar.
- Schnell (hohe Trefferquote ohne Hilfe): Schritte überspringen, höhere Schwierigkeit.
- Langsam: andere Erklärung, kleinere Schritte, mehr Beispiele; nach wiederholtem Scheitern
  Voraussetzung prüfen.
- Gleiche Fehlvorstellung zweimal: gezielte Erklärung zu genau dieser Fehlvorstellung.
- Wiederholung mit Abstand: siehe Schritt 4a.
- Grenzen: nie unter die Untergrenze, Abschluss immer auf Zielniveau.
- Antwortzeit nur schwach gewichten.
Jede Regel mit eigenem Test. LERNKREISLAUF.md aktualisieren.
```
**Fertig, wenn:** jede Regel hat einen Test, Dokument = Code.

---

## Schritt 4a – Grundlagen: einzelne Antworten, aktive Zeit, Wiederholung

```text
Ziel: Drei Bausteine, die das Lernsystem braucht und auf denen später die Sterne aufbauen.
Noch keine Sterne in diesem Schritt.

1. Einzelne Antworten protokollieren
   - Neue Tabelle lern_antwort: child_key, sitzung_id, aufgabe_id, konzept_id, fach,
     gezeigt_at, beantwortet_at, antwort, richtig, tipp_genutzt, phase.
   - Jede beantwortete Aufgabe (anker, diagnose, aufgabe, vorhersage, transfer) schreibt genau
     eine Zeile. Nur anhängen, nie ändern.

2. Aktive Zeit (getrennt von learning_time, das für den Elternbericht bleibt)
   - lern_aufgabe bekommt erwartete_sekunden (Standardwert nach antwort_art und Klasse,
     überschreibbar durch Curriculum-Inhalte).
   - Aktive Zeit einer Aufgabe = Zeit von gezeigt_at bzw. letzter Eingabe bis beantwortet_at,
     höchstens 2 × erwartete_sekunden.
   - Die Lernseite meldet Eingaben (Tippen, Auswählen, Tipp öffnen) leichtgewichtig; nach
     2 Minuten ohne Eingabe oder wenn die Seite im Hintergrund ist, stoppt die Uhr.
   - Nach Ende einer Einheit (COMPLETE/MASTERED/ESCALATED) entsteht keine aktive Zeit mehr.
   - Antworten unter 3 Sekunden zählen 0; eine Serie solcher Antworten markiert den Abschnitt
     als "nicht ernsthaft" (Kennzeichen in lern_antwort, Regel konfigurierbar).
   - Funktion aktive_zeit(child_key, von, bis, fach=None) mit Tests.

3. Wiederholung mit Abstand
   - Heute zählt lern_fortschritt.wiederholungen nur neue Runden nach einem Fehler – das
     bleibt so, heißt aber nichts mit Abstand.
   - Neue Tabelle lern_wiederholung: child_key, konzept_id, faellig_am, gewaehlt_am, status
     (offen / bestanden / nicht_bestanden), ergebnis.
   - Nach MASTERED fragt Karo das Kind: "Wann willst du das noch einmal wiederholen?"
     Auswahl: in 2, 3, 4 oder 5 Tagen. Steht eine Klassenarbeit an, markiert Karo den Tag
     davor als Vorschlag (innerhalb dieser Auswahl).
   - "Heute" (services/today.py, mein_tag) zeigt fällige Wiederholungen als eigene Einträge
     ("Wiederholen: Brüche addieren, ca. 5 Minuten"). Verpasste bleiben als "noch offen"
     stehen, bis sie gemacht sind.
   - Die Wiederholung ist ein kurzer Check: 3–5 NEUE Aufgaben auf Zielniveau (andere als in
     der Einheit; bei Mathe Varianten über rechnen.py/Aufgabenvorlagen).
   - Bestanden → Konzept gilt als gefestigt. Nicht bestanden → kurze Auffrischung (andere
     Erklärung, geführte Aufgabe), danach wählt das Kind wieder 2–5 Tage. Kein Minus.
   - Tests: Auswahl, Anzeige unter Heute am richtigen lokalen Tag, verpasste Wiederholung,
     bestanden/nicht bestanden, neue Aufgaben statt alter.

LERNKREISLAUF.md um diese drei Bausteine ergänzen.
```
**Fertig, wenn:** alle Tests grün, Wiederholung erscheint unter „Heute“, aktive Zeit ist für eine offene App ohne Eingabe 0.

---

## Schritt 5 – Simulierte Kinder und Messung

```text
Ziel: Nachweisen, dass Einstufung und Begleitung funktionieren – mit Zahlen.

Simulierte Kinder in Karo (Idee aus kcteam/simulate.py, aber mit Wahrscheinlichkeiten und
Lernen), gegen echte Bibliotheksinhalte. Jedes Kind hat eine verborgene wahre Fähigkeit pro
Konzept, die Karo nicht kennt:
schnell (p=0.9) · langsam (p=0.3, steigt pro Übung) · fehlvorstellung:X (bis zur passenden
Erklärung) · lücke:Voraussetzung · rater (zufällig) · unterfordert · abbrecher (hört auf,
kommt am nächsten Tag wieder).

Zielwerte VOR dem Lauf festlegen und als Tests in die CI:
- Einstufung trifft die richtige Niveaustufe in ≥ 80 %.
- schnell braucht deutlich weniger Aufgaben als langsam.
- fehlvorstellung bekommt die passende Erklärung, lücke die Voraussetzung.
- Lernende Profile erreichen das Zielniveau; Anzahl Aufgaben bis dahin ausweisen.
- rater schafft den Abschluss in < 5 % der Läufe.
- Keine Endlosschleife, keine Sackgasse, keine Aufgabenwiederholung.
- abbrecher setzt korrekt fort.
Je Profil 200 Läufe, fester Seed. Bericht: Zielwert / Ist / bestanden, Ursachen der Fehler.
```
**Fertig, wenn:** alle Zielwerte erreicht oder bewusst angepasst.

---

## Schritt 5b – Sterne und Vereinbarungen

```text
Ziel: Sterne zeigen den Eltern verlässlich, dass das Kind wirklich gelernt hat, und Eltern
und Kind können damit Vereinbarungen treffen. Baut auf Schritt 4a auf (lern_antwort, aktive
Zeit, lern_wiederholung). Keine KI, alles regelbasiert.

Abgrenzung: "Meine Welt" und "Ziele planen" gehören NICHT zu diesem System – keine Daten von
dort (auch nicht die selbst eingetragenen Minuten), keine Anzeige dort, keine Verknüpfung im
Code. Architekturtest dafür.

1. Silberstern – Einsatz
   - ½ Stern = 15 Minuten aktive Zeit (aus Schritt 4a), 1 Stern = 30 Minuten.
   - Nur Aufgaben auf dem eigenen Niveau zählen (Konzept noch nicht beherrscht oder fällige
     Wiederholung); schon beherrschte leichte Aufgaben nicht.
   - Abschnitte "nicht ernsthaft" (Zufallsklicken) zählen nicht.
   - Minuten sammeln sich über Tage; Reste verfallen nicht. Kein Tageslimit.
   - Jeder halbe Stern trägt sein Fach.

2. Goldstern – Geschafft
   - ½ Stern: Konzept beherrscht (MASTERED, Abschlusstest auf Zielniveau selbstständig).
   - ½ Stern: Wiederholung zu diesem Konzept bestanden.
   - +1 Stern: ganzes Thema erledigt = alle Konzepte des Themas beherrscht UND wiederholt.
   - Jedes Konzept zahlt nur einmal.

3. Beleg zu jedem Stern
   - Tabelle stern: child_key, art (silber/gold), menge (0.5 oder 1), fach, grund,
     quelle (eindeutig: kein Ereignis erzeugt zwei Sterne), beleg (Thema, aktive Minuten,
     Anzahl Aufgaben, Ergebnis vorher/nachher), created_at. Nur anhängen.
   - Tabelle stern_ruecknahme: Eltern nehmen einen Stern mit Begründung zurück (protokolliert;
     das Kind sieht es freundlich erklärt).
   - Der Kontostand wird immer berechnet (Sterne − Rücknahmen − Einlösungen), nie gespeichert.
   - Vergabe: nach jedem geschriebenen lern_antwort/lern_ereignis bzw. Wiederholungsergebnis
     prüft services/sterne.py die Regeln, in derselben Transaktion.

4. Vereinbarungen – Ping-Pong
   - Tabelle vereinbarung (status: verhandlung → aktiv → einloesung_angefragt → eingeloest,
     oder abgelehnt) und vereinbarung_angebot (seite kind/eltern, wunsch, sternzahl, faecher
     = alle oder 1–2 Fächer, antwort, zeitpunkt; nur anhängen).
   - Eine Seite macht ein Angebot, die andere ist am Zug: zustimmen, Gegenangebot (Wunsch,
     Sternzahl und/oder Fächer ändern) oder ablehnen. Immer nur eine Seite am Zug, ein offenes
     Angebot pro Vereinbarung. Weiter, bis beide zustimmen. Das Kind kann sein offenes Angebot
     zurückziehen. Verlauf sichtbar.
   - Zu jeder Sternzahl zeigt Karo eine Einordnung ("20 Sterne ≈ 10 Stunden Lernen, bei deinem
     Tempo etwa 3 Wochen"), berechnet aus den Sternen der letzten Wochen.
   - Wunschtext des Kindes: kurz (max. 60 Zeichen), pii.scrub(), Filter für Unpassendes.
   - Nach Einigung sind Wunsch, Sternzahl und Fächer fest; Änderung nur über neue Verhandlung.
   - Balken zählt nur Sterne aus den vereinbarten Fächern. Jeder Stern kann nur einmal
     eingelöst werden; laufen zwei Vereinbarungen parallel, zeigt Karo vor dem Einlösen, wie
     sich der andere Balken verändert.
   - Einlösen: Kind tippt "Einlösen" → Eltern bekommen die Anfrage (Muster wie woche_help) →
     Eltern bestätigen → erst dann Abbuchung; optional Feier-Nachricht über family_post.

5. Oberfläche
   - Kind: eigener Bereich "Meine Sterne" (erreichbar von der Lernseite und nach jeder
     Einheit): Sternglas mit halben Sternen, Silber und Gold, Balken der Vereinbarungen,
     Wunsch vorschlagen, Verhandlung, Einlösen. Nach einer Einheit kurze Animation mit dem
     Grund in einem Satz.
   - Eltern: Sterne pro Woche mit Beleg, Angebote beantworten, Einlösungen bestätigen,
     Rücknahme.
   - Erklärtext für beide: "Silberne Sterne gibt es fürs Dranbleiben: eine halbe Stunde
     ernsthaft gelernt. Goldene Sterne gibt es fürs Schaffen: etwas verstanden, und es sitzt
     auch noch Tage später."

6. Grenzen
   - Keine Ranglisten, kein Vergleich zwischen Kindern oder Geschwistern, kein Abzug durch
     das System, keine Käufe/Shops/Werbung/Produktvorschläge.
   - Sterne und Wünsche verlassen Karo nie (nicht an den Curriculum-Dienst, nicht an eine KI).

7. Tests
   - Jede Vergaberegel, "nicht ernsthaft" zählt nicht, offene App ohne Eingabe gibt nichts,
     Konzept zahlt Gold nur einmal, Thema-Bonus, Rücknahme, Kontostand-Berechnung.
   - Ping-Pong vollständig (Angebot, Gegenangebot, Zustimmung, Ablehnung, Zurückziehen),
     Fächerfilter, Einlösen mit Bestätigung, doppelte Einlösung unmöglich.
   - Simulationsprofile aus Schritt 5: schnell und langsam bekommen pro aktiver Lernzeit
     vergleichbar viele Silbersterne; rater praktisch keine; Anteil Gold ungefähr 1/3.
```
**Fertig, wenn:** alle Tests grün und die Sternverteilung der Simulationsprofile im Bericht.

---

## Schritt 6 – Inhaltsprüfung der Bibliothek

```text
Ziel: Die Qualität der freigegebenen Inhalte prüfen.

Automatisch für alle freigegebenen Konzepte: Rechenlösungen richtig, keine doppelten
Aufgaben, Aufgabenniveau passt zum Konzept, jede Fehlvorstellung hat Diagnoseaufgabe UND
Erklärung, jede Visualisierung zeichenbar, Klassenbereich plausibel.
Befunde als Liste; fehlerhafte Konzepte sperren (neue Version anfordern), nicht still ändern.

Rückruf-Funktion: Konzeptversion sperren → laufende Sitzungen wechseln auf die
Vorgängerversion. Eltern können einen Fehler an einer Aufgabe melden.

docs/PRUEFBOGEN.md für eine Lehrkraft: 20 zufällige Konzepte mit fachlicher Richtigkeit,
Altersgerechtheit, Verständlichkeit, Passung zur Klasse (je 1–5 und Kommentar).
Den Bogen füllt ein Mensch aus, nicht du.
```
**Fertig, wenn:** automatische Prüfung grün, Prüfbogen an eine Lehrkraft gegeben.

---

## Schritt 7 – Schlechte Wege Ende-zu-Ende

```text
Ziel: Jeder Weg endet in einem verständlichen Zustand für Kind und Eltern.

Ende-zu-Ende-Tests: Thema nicht gefunden → Vorschläge → Auswahl; Foto unlesbar;
Curriculum-Dienst nicht erreichbar; Tageskontingent erschöpft; Thema wird gerade vorbereitet;
Kind wechselt mitten im Thema; Klassenarbeit rückt näher, Plan verdichtet sich;
Konzeptversion zurückgerufen.
Für jeden Fall: was sieht das Kind, was sehen die Eltern, was steht im Betriebsprotokoll.
```
**Fertig, wenn:** alle Fälle getestet, keine Sackgasse.

---

## Schritt 8 – Pilot vorbereiten (5–10 Familien, 4 Wochen)

```text
Ziel: Einen echten Pilot messbar machen.

- Einwilligung der Eltern für den Pilot (Zweck, Daten, Dauer, Löschung) als Seite in der App.
- Vorher-/Nachher-Kurztest pro Thema (gleiche Kompetenz, andere Aufgaben).
- Auswertung für mich: Lernzeit, Aufgaben bis Abschluss, Vorher/Nachher, Abbrüche,
  Rückmeldung der Eltern (3 Fragen nach jedem Thema). Nur zusammengefasst, pseudonym.
- Nach Pilotende: Pilotdaten automatisch löschen oder auf Wunsch behalten.
```
**Fertig, wenn:** Pilot gelaufen und ausgewertet. Erst danach Schritt 9.

---

## Schritt 9 – Mandantenfähigkeit planen

```text
Ziel: Karo wird ein Serverdienst für viele Familien. Familien melden sich an; sie geben nie
einen KI-Token ein; KI läuft nur serverseitig über die API. Zielgröße 100.000 Familien.

Liefere NUR einen Architekturplan, keinen Code:
- Datenmodell family → parent_account → child_profile; learner_name/learner_grade wandern in
  child_profile.
- Liste aller Tabellen mit family_id/child_id; Row Level Security in Postgres.
- Migration SQLite → Postgres (Alembic), Import des bestehenden Stands als erste Familie.
- Uploads/Objektspeicher in der EU, Sitzungen, Job-Warteschlange (SKIP LOCKED) mit eigenem
  Worker, zustandslose Web-Instanzen, Konfiguration über Umgebungsvariablen.
- Reihenfolge der Umsetzung in Phasen, Risiken, was sich für den Nutzer ändert.
Danach anhalten und auf meine Freigabe warten.
```

## Schritt 10 – Mandantenfähigkeit umsetzen (je Phase ein Prompt)

```text
Setze Phase <N> des freigegebenen Plans um.
Pflicht in jeder Phase: Isolations-Test über alle Routen (Familie A sieht nie Daten von B),
App nach der Phase lauffähig, Bericht.
```
Phasen: (1) Konten, Login, Einwilligung → (2) Postgres + RLS → (3) Objektspeicher, Scans löschen →
(4) Worker + zustandslose Web-Instanzen → (5) Datenschutz-Selbstbedienung: Export, Löschen, Audit-Log.

## Schritt 11 – Produktions-KI

```text
- Curriculum-Dienst: Provider claude_token nur bei KCTEAM_ENV=dev. Mit KCTEAM_ENV=prod
  verweigert der Dienst den Start ohne API-Provider in einer EU-Region (z. B. Claude über
  AWS Bedrock Frankfurt oder Vertex AI Europe).
- Karo (Web und Worker) hat keinen KI-Schlüssel; CI-Test: app/ importiert keinen KI-Client.
- Kosten pro Thema aus curriculum.topic_cost in €, Monatsbudget mit Warnung.
- Vorab-Erzeugung der häufigsten Themen (z. B. Mathe 5–8) vor Schuljahresbeginn.
- Lasttest mit Locust: 1.000 Familien gleichzeitig am Sonntagabend.
```

## Schritt 12 – Native App (später)

```text
Capacitor-Hülle um die Web-App. Scan und OCR auf dem Gerät: iOS VNDocumentCameraViewController +
Vision, Android ML Kit Document Scanner + Text Recognition v2. Gleicher Endpunkt /blatt/text,
gleiche Filter und Bestätigung. Kamera-Begründung in NSCameraUsageDescription bzw. im
eigenen Hinweis-Bildschirm.
```