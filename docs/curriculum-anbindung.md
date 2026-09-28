# Karo ↔ Karo Curriculum – 28.09.2026

## Zuständigkeiten

Der Curriculum-Dienst erstellt, prüft und versioniert wiederverwendbare Inhalte.
Karo verwaltet ausschließlich lokal die Themen des Kindes, Prüfungen, Kalender,
Antworten, Sitzungen und Lernstände. Die Anbindung überträgt nur geschwärzten
Thementext, Fach, Klasse und den technischen Inhaltsvertrag – keine lokalen
Themen-/Prüfungs-IDs, Kalender, Antworten oder persönlichen Lernverläufe.
Die Textschwärzung ist keine Garantie, sämtliche persönlichen Angaben zu erkennen.

„Meine Themen“ und jede Prüfung haben weiterhin eigene Themen-IDs, Routen,
Sitzungen und Fortschritte. Gemeinsame Inhalte sind kein gemeinsamer Lernstand.
„Meine Welt“ und „Ziele planen“ werden nicht verändert.

## Ablauf

1. Passendes freigegebenes Material im lokalen Katalog suchen (Fach und Klasse).
2. Fehlt es: `POST /v1/lessons` mit einem stabilen Karo-Formatvertrag senden.
3. Bei `pending`: Export-ID, Startzeit, Fach, Klasse und Dienstadresse im
   bestehenden Job speichern; nächsten Abruf mit `not_before` terminieren.
   Andere Jobs laufen weiter. Ein normaler Wartezustand verbraucht keine
   Fehlerversuche. Neustarts verlieren die Export-ID nicht.
4. Bei `ready`: Karo prüft erneut das Inhaltsformat, die erlaubten Darstellungen,
   Thema/Klasse, Einstieg, unterschiedliche Übungsfragen und erkennbare
   Rechenausdrücke. Erst danach wird die Lernreihe sichtbar.
5. Inhalte als unveränderliche lokale Fassung importieren. Fingerabdruck und
   Herkunft einschließlich Export-ID und Konzeptversion stehen in
   `lern_curriculum_import`. Eine neue Fassung erhält eine neue Konzept-ID.
6. Das Kind setzt seinen eigenen Lernweg fort. Eine offene Sitzung bleibt an
   ihre ursprüngliche Fassung gebunden, auch wenn der Katalog sich verändert.

Ein abgelehnter Export wird maximal zweimal über `/reject` zur Nacharbeit
zurückgegeben. Gesperrtes Material, fehlende Berechtigung und unbekannte
Antwortformate führen zum definierten Fehlerzustand. Temporäre Netzwerkfehler
nutzen die vorhandenen drei Versuche mit Abstand. Die Vorbereitung endet nach
maximal 24 Stunden in einem wiederholbaren Fehlerzustand, nicht in einer
endlosen Warteschleife. Ein späterer manueller Neustart legt einen neuen Job an.

## Konfiguration

Die lokale App nutzt `curriculum_url` und `curriculum_key` aus ihrer geschützten
`config.json`. Alternativ überschreiben `KARO_CURRICULUM_URL` und
`KARO_CURRICULUM_KEY` diese Werte. Beispieladresse für den lokalen Prozess:
`http://127.0.0.1:8088`. Schlüssel niemals ins Repository oder in Protokolle schreiben.

Für Docker gibt es `docker-compose.curriculum.yml`: Dienstadresse
`http://curriculum-api:8088`, gemeinsames Netzwerk `karo-net`, Schlüssel aus `.env`.
Die Ergänzung benötigt ein App-Image, das diese Anbindung bereits enthält;
ein unverändertes älteres Docker-Hub-Image genügt nicht.

Sobald URL oder Schlüssel konfiguriert ist, wird fehlendes Material über den
Dienst angefordert, auch ohne lokale KI-Erzeugungsfreigabe. Fehler führen
**nicht** zu einem stillen lokalen KI-Fallback. Ohne Konfiguration bleibt der
bisherige, schaltbare lokale Erzeugungsweg aus Kompatibilitätsgründen erhalten.
Ein bereits gestarteter externer Job wechselt bei einer Konfigurationsänderung
nicht heimlich zum lokalen Generator oder zu einem anderen Dienst.

In der lokalen Installation wurde ein eigener Client `karo-local-bridge`
angelegt. Der Schlüssel liegt nur in der bestehenden geschützten Konfiguration.
Vorherige Konfiguration: `data/curriculum-bridge-backup.APc01b/config.json`.

## Prüfung und Grenzen

- 167 gezielte App-Tests bestanden, darunter 28 neue Anbindungstests.
- 102 Tests des Curriculum-Projekts bestanden (vollständige Sammlung).
- App-Gesamtlauf nach Aufarbeitung der 45 Fehlschläge am 28.09.2026:
  **520 bestanden, 0 fehlgeschlagen, 0 Ausführungsfehler, 0 übersprungen**
  (137 Sekunden); der vollständige Wiederholungslauf bestätigt alle 520 Tests
  (136 Sekunden). Maschinenlesbare Ergebnisse:
  `output/app-regression-repaired.xml` und `output/app-regression-final.xml`.
  Der frühere Lauf mit 45 Fehlschlägen
  bleibt unter `output/curriculum-regression.xml` als Ausgangsbefund erhalten.
- Neue App-Vertragstests prüfen echte Job-Persistenz, Auftragszusammenlegung,
  Wartezeiten, begrenzte Nacharbeit, Ausfälle, Geheimnisschutz, Versionierung
  und getrennte Themen-/Prüfungssitzungen nach einem Curriculum-Import.
- Das Curriculum-Projekt hat zusätzlich einen Test mit dem **tatsächlichen**
  Karo-Format (`KARO_APP_PATH`), PostgreSQL, HTTP-API und simuliertem Modell.
- Der authentifizierte Live-Lesezugriff auf das freigegebene Konzept
  `MA.BRUECHE.BEGRIFF` funktioniert. Kein kostenpflichtiger neuer Live-KI-Lauf
  wurde als Qualitätsnachweis verwendet.
- API und Hintergrund-Agent wurden mit der Korrektur neu gebaut und gestartet;
  der Live-Lesezugriff wurde danach erneut erfolgreich geprüft.
- Echte Anzeige-/Einstiegsfehler wurden behoben, veraltete Kalender-/Generator-
  Testverträge auf die getrennten Abläufe umgestellt und zusätzliche
  Regressionstests ergänzt; siehe `PRUEFBERICHT_LERNWEGE.md`.
- Freitextaufgaben, pädagogische Eignung und vollständige fachliche Richtigkeit
  sind durch Schema- und Rechenprüfungen nicht garantiert.
- Kein automatischer Austausch bestehender Inhaltsfassungen, keine vollständige
  Zerlegung jedes breiten Themas in einen mehrteiligen Kurs und keine Migration
  des gesamten lokalen Altbestands in den zentralen Dienst in diesem Schritt.
- Die Anbindung bündelt ganze Lernreihen. Bereits vorhandene gesonderte
  KI-Funktionen für Materialanalyse/Fehleranalyse werden dadurch nicht ersetzt.

## Curriculum-Stabilität

Im Volltest wurde ein Verbindungsleck sichtbar: beendete Arbeits-Threads
behielten ihre PostgreSQL-Verbindungen. Der Dienst räumt diese nun beim
nächsten Zugriff auf, ohne Verbindungen aktiver Threads zu schließen. Beim
Beenden der API werden ihre selbst angelegten Verbindungen geschlossen.
Zwei Regressionstests sichern dieses Verhalten. Die Paket-Sperrdatei wurde
mit den bereits deklarierten Laufzeitabhängigkeiten synchronisiert.

Alle PostgreSQL-Tests laufen ausschließlich gegen eine eigens angelegte
Testdatenbank. Die bestehenden Tests löschen Schemas; daher niemals die
Produktionsadresse als `TEST_DATABASE_URL` verwenden.
Die ausschließlich dafür angelegte Datenbank `karo_bridge_test_20260928_7426`
wurde nach Abschluss entfernt; sie lässt sich für einen neuen Testlauf neu
erstellen. Produktionsdaten wurden dabei nicht gelöscht.
