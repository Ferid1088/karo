# Karo_Prompts_Schritt_für_Schritt

Reihenfolge einhalten. Einen Prompt erst geben, wenn der vorige **fertig** ist (Bedingung steht jeweils unten).
Erledigt: Runde 1 (Vertrag), Runde 2 (Container-SHA, Fail-closed, Vertragsversion, CI, Dockerfile,
Kontingent) und **Schritt 1** (keine Bilder mehr an Claude).

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

**Erledigt** (Commits 915cc04, 226f7a3, 536b142, 498a7f7). Offen daraus für Schritt 2:
die Wissensbasis füllt sich nicht mehr aus Blättern, also braucht der klassische Lernweg
bis dahin eine freigegebene Internetquelle oder den Lehrplan-Dienst. `topic_propose`
(Unterthemen aus Text) bleibt bestehen und wird wieder gerufen, sobald Text vorliegt.

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
- Wiederholung mit Abstand nach Abschluss.
- Grenzen: nie unter die Untergrenze, Abschluss immer auf Zielniveau.
- Antwortzeit nur schwach gewichten.
Jede Regel mit eigenem Test. LERNKREISLAUF.md aktualisieren.
```
**Fertig, wenn:** jede Regel hat einen Test, Dokument = Code.

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
