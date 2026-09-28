# Prüfung der getrennten Lernwege – 28.09.2026

## Aktueller Stand: Gesamttest grün

Zwei vollständige App-Testläufe bestehen jeweils: **520 Tests bestanden,
0 Fehler, 0 fehlgeschlagene Tests, 0 übersprungen**. Laufzeit: 137 bzw.
136 Sekunden. Ergebnisdateien: `output/app-regression-repaired.xml` und
`output/app-regression-final.xml` (abschließende Wiederholung).

Die vorherigen 45 Fehlschläge waren nicht 45 unabhängige Produktfehler:

- Echte Anzeige-/Einstiegsfehler: vorbereitete Fragerunden wurden auf „Heute“
  ignoriert; freigegebene Antwortprüfungen und Schulblätter waren im Kindbereich
  nicht erreichbar; das gespeicherte Profilfoto wurde nicht angezeigt.
  Diese Funktionen wurden wieder angeschlossen, mit unveränderten Berechtigungen.
- Zusätzlich behoben: Der Heute-Start funktioniert auch bei abgeschaltetem
  adaptivem Lernen. Persönliche offene Aufgaben schließen Prüfungsthemen und
  historische Prüfungs-Fragerunden aus. Rückwege nach manueller Lernmarkierung
  verwenden den aktuellen Statusfilter.
- Veraltete Testverträge: alte Beschriftungen, Navigationsreihenfolge,
  Erstellformular auf der Übersicht, gemeinsame Themen-/Prüfungsstände,
  automatische KI-Tagespläne ohne Kalendereingabe und Wechsel in persönliche
  Quiz-Seiten. Diese Erwartungen wurden durch Prüfungen der vereinbarten,
  getrennten Abläufe ersetzt – nicht durch Abschalten der Tests.

Die Prüfungsfixtures besitzen jetzt eigene Prüfungsthemen. Geprüft werden
Upload und manuelle Anlage, unabhängige Minuten, Terminfreigabe der Generalprobe,
der Start einer eigenen Diagnosesitzung, getrennte Lernstände und Schutz vor
fremden IDs. Historische Materialien bleiben separat auf Lesbarkeit, Archiv,
Video-Range, gespeicherte Auswertung und sicheren Datenbankumzug geprüft.
Ihr stillgelegter HTTP-Generator darf auch mit Legacy-Schalter keine neuen
Aufträge oder persönlichen Quiz-Seiten erzeugen.

Fünf zusätzliche Testfälle sichern den Heute-Start, die Trennung offener Aufgaben
und die manuelle Prüfungsanlage ab. Keine Tests wurden übersprungen oder als
erwarteter Fehler markiert. Die Module „Meine Welt“ und „Ziele planen“ wurden
nicht geändert; zwei Tests prüfen lediglich die aktuelle gemeinsame Navigation.
Alle Tests verwenden temporäre Datenbanken und simulierte Modelle. Der grüne
Lauf ist kein Nachweis vollständiger pädagogischer Qualität künftig erzeugter
Inhalte. Eine Deprecation-Warnung von Starlette/AnyIO bleibt bestehen.

```sh
karo-py310/bin/python -m pytest -q --tb=short --show-capture=no \
  --junitxml=output/app-regression-final.xml
```

## Historischer Ausgangsstand vom 27.09.2026

## Ergebnis und Grenzen

„Meine Themen“ und jede einzelne Klassenarbeit haben eigene lokale Themen,
Sitzungen und Lernstände. Gemeinsam bleiben die geprüften Curriculum-Inhalte
und der Lernmotor. Die neuen Ablauftests prüfen beide Bereiche separat.

Damals gab es **keine Freigabe als vollständig fehlerfreie Gesamtanwendung**:
Der damalige vollständige Testlauf enthielt Fehler in älteren Erwartungen.
Ein unveränderter Checkout von `170b8a9` wurde zum Vergleich separat geprüft.

## Automatisierte Prüfung

- Unveränderter Git-Stand: 464 Tests, 425 bestanden, 39 fehlgeschlagen.
- Vollständiger Lauf nach dem Prozessumbau: 482 Tests, 437 bestanden,
  45 fehlgeschlagen; keine Test-Ausführungsfehler.
- 37 fehlgeschlagene Tests waren bereits im Vergleichsstand rot.
- Acht zusätzliche Abweichungen erwarten den alten `/lerntag`-Generator,
  gemeinsame Quiz-Links, den alten statischen Plan oder das Erstellformular
  direkt auf der Übersicht. Diese Wege wurden bewusst durch den separaten
  Prüfungsprozess bzw. `/klassenarbeit/neu` ersetzt. Die alten Tests sind
  zu diesem Zeitpunkt noch nicht auf den neuen Vertrag umgestellt.
- Zwei zuvor fehlgeschlagene Tests zur Rückkehr nach manueller Lernmarkierung
  bestehen jetzt. Eine zwischenzeitliche Router-Import-Regression wurde behoben.

Gezielte Testauswahl:

**107 Tests bestanden**, einschließlich drei zusätzlicher Abschlussprüfungen
für den vollständigen Themenblatt-Upload und historische HTML-/Video-Medien.

```sh
karo-py310/bin/python -m pytest \
  tests/test_separate_learning_journeys.py \
  tests/test_adaptiv_lektion.py tests/test_adaptiv_domain.py \
  tests/test_lektion_auf_anfrage.py tests/test_lektion_speichern.py \
  tests/test_lektionen_zuordnung.py tests/test_lektion_erzeugung.py \
  tests/test_architecture.py tests/test_exam_month_view.py
```

Die Ablaufprüfungen umfassen:

- gleichnamige persönliche Themen und zwei gleichnamige Prüfungen;
- Schutz gegen fremde Themen-/Sitzungs-IDs, parallele Tabs und Archivaktionen;
- Diagnose, Fehlerrückmeldung, Erklärung, geführte und selbstständige Übung,
  Transfer und Abschluss ohne zusätzlichen Modellaufruf bei Datenbanktreffern;
- fehlende Inhalte: Erzeugen, Prüfen, Speichern, korrektes Fortsetzen und
  spätere Wiederverwendung; getrennte Klassenstufen bleiben auffindbar;
- Themenblatt hochladen, erkannte Themen bestätigen, eigene Prüfung anlegen;
- Kalender bis zum Prüfungstermin, unabhängige Minuten je Prüfung,
  Erhalt nicht übermittelter Tage und vorgezogene Generalprobe an freien Tagen;
- Datumssperre, eigene Aufgaben und Ergebnisse, wiederholtes Öffnen ohne
  doppelte Generalprobe und unveränderte fremde Lernstände;
- historische Prüfungsmedien über eigene Prüfungs-URLs, einschließlich
  Video-Range-Anfragen; kein Ausweichen auf persönliche Materialseiten;
- idempotente Migration ohne Löschen alter Sitzungen;
- begrenzte Wiederholungen bei unbekannten Antworten mit Hinweis auf Hilfe.

Die Erzeugungs- und Uploadprüfungen verwenden ein simuliertes Modell. Ein
neuer kostenpflichtiger Live-Modellaufruf wurde nicht als Qualitätsnachweis
verwendet. Schema- und Rechenprüfungen garantieren keine vollständige
pädagogische/fachliche Korrektheit jedes künftig erzeugten Inhalts.

## Browserprüfung

Lokal geprüft: Themenübersicht, neue Prüfung, Prüfungsübersicht, Detailplan,
gespeicherte Prüfungssitzung und Rückweg. Die aktive Lernrunde zeigt keinen
fremden Lernbereich. Auf einer schmalen Ansicht wurden überlappende
Kalenderfelder behoben; der Kalender verwendet dort zwei lesbare Spalten.
Die temporäre Browser-Größenänderung wurde zurückgesetzt.

## Bestandsdaten

Vor der Migration wurde die aktive SQLite-Datenbank gesichert:
`data/process-audit-backup.H11cur/live-karo.db`.

Nach der Migration: keine von mehreren Prüfungen geteilten Themen-IDs,
keine gleichzeitig persönlichen und prüfungsgebundenen Themen. Alle sieben
bestehenden Sitzungen sind erhalten. 32 alte Mitgliedschaften sind in
`exam_topic_legacy` dokumentiert. Mehrdeutige historische Lernspuren werden
nicht willkürlich einer Prüfung zugerechnet.

„Meine Welt“ und „Ziele planen“ wurden in diesem Prozessumbau nicht verändert.
Es wurde kein Commit erstellt und nichts zu GitHub gepusht.
