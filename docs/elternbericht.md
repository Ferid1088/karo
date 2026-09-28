# Elternbericht

`/eltern` zeigt den kompakten Bericht. `ansicht=monat|woche|tag` und
`datum=YYYY-MM-DD` wählen den Zeitraum. Tageslinks merken den Ausgangszeitraum
über `zurueck` und `basis`. `/eltern/bericht` liefert denselben Bericht als
HTML-Fragment für die progressive Navigation. Beide Routen sind ausschließlich
für Eltern zugänglich und verwenden `Cache-Control: no-store`.

Die vorhandenen Werkzeuge liegen unter „Verwalten & Einstellungen“. Zugänge
zu Schulmaterial und Klassenarbeiten bleiben für Eltern verfügbar, auch wenn
die jeweilige Kinderfreigabe aktiviert wird. Die Kinderfreigabe erweitert
nicht den Zugriff auf den Elternbericht.

## Datenvertrag

- **Bewertete Antworten:** Adaptive Ereignisse „Antwort richtig“, „Fehlertyp
  erkannt“, „Lehrrunde ohne Erfolg“ und „Fehler nicht im Katalog“. Quizantworten
  kommen ausschließlich aus `answer_log`, pro Frage die letzte freigegebene
  Version bis zum Berichts-Stichtag. Eine Korrektur ist kein weiterer Versuch.
- **Aktive Tage:** Tage mit einer Antwort, einem Lerncheck, einer tatsächlichen
  Eingabe/Hilfeanforderung im Lernprozess oder einer Zielmeldung. Automatische
  Vorbereitung, bloßes Anlegen von Material und geplante Termine zählen nicht.
- **Neu sichere Themen:** Erster protokollierter `MASTERED`-Übergang je eigenem
  Thema. Erneute Checks desselben Themas werden nicht noch einmal gezählt.
  Das manuelle „Gelernt“-Häkchen ist kein Lerncheck.
- **Eigene Themen / Prüfungen:** Explizite lokale Themen-ID und `exam_topic`
  entscheiden über die Zuordnung, nie ein ähnlicher Titel oder geteiltes
  Curriculum-Konzept. Mehrdeutige Altzuordnungen, gelöschte Inhalte und fremde
  Fächer werden nicht zugerechnet. Vergangene Prüfungs-Lernstände werden aus
  der letzten damals vorhandenen Sitzung und ihren Ereignissen rekonstruiert.
- **Zielmeldungen:** Gespeicherte Abschnitte aus `plan_completion`, einschließlich
  selbst gemeldeter Minuten. Jede Meldung zählt einmal. Nachholen zählt am
  tatsächlichen lokalen Meldetag, nicht rückwirkend am geplanten Tag. Mehrere
  Abschnitte derselben Einheit sind deshalb mehrere Meldungen, keine mehrfach
  abgeschlossenen Ziele. Zielpläne und Meldungen sind keine gemeinsame Quote.
- **Planung:** Ziel-Einheiten und konkrete Prüfungstage bleiben ausdrücklich
  „geplant“. Für Themen und Prüfungen existiert kein verlässlicher Aktivtimer;
  der Bericht erfindet weder Lernminuten noch eine Lernzeit aus offenen Tabs.
- **Zeit:** UTC-Zeitstempel werden in der Zeitzone von Ziele planen (Standard
  Europe/Berlin) ausgewertet. ISO-Kalendertage bleiben lokale Kalendertage.
  Zukünftige Datensätze zählen nicht als beobachtete Aktivität.

Planungen zeigen die aktuell gespeicherten Termine, keinen unveränderlichen
historischen Planstand. Alte Wochenvereinbarungen bleiben im bisherigen
Elternbereich unter „Verwalten & Einstellungen“; private Pilot-Rückmeldungen,
Konzentrationsangaben und Meine-Welt-Notizen werden nicht in den Bericht gelesen.

Der Bericht ist ausschließlich lesend. Auch ein bisher unbenutztes Zielsystem
wird durch einen Besuch nicht initialisiert. Es gibt keine neue KI-Anfrage,
keine Änderung an Lernzuständen oder Plänen und kein externes Tracking.

## Bedienung und Test

Der farbige Überblick benennt bearbeitete Themen, erste bestandene Lernchecks
(hier eigene und Prüfungsthemen) und einen belegbaren Gesprächsanlass. Eine
Prüfung innerhalb von sieben Tagen mit offenen Themen hat Vorrang; andernfalls
wird ein bearbeitetes, noch nicht sicheres Thema mit nicht richtigen Antworten
genannt. Das ist keine Diagnose oder Schulnotenprognose. Bei leeren oder
zukünftigen Zeiträumen erscheinen keine erfundenen Fortschrittsaussagen.

„Lernen im Verlauf“ stapelt Antworten nach Fach; Schraffur markiert nicht
richtige Antworten. Die ergänzende Tabelle zeigt richtige/gesamte Antworten,
erste bestandene Lernchecks, selbst gemeldete Zielminuten und geplante
Prüfungsminuten pro Zeitabschnitt. Es gibt keine irreführende gemeinsame
Minutensumme und keine unbeschriftete zweite Achse. Die Antwortquote ist eine
Beschreibung der erfassten Versuche, kein Beleg für steigende Kompetenz bei
unterschiedlich schweren Aufgaben. Themen-Details zeigen nur eigene Themen;
Prüfungsbereitschaft bleibt separat. Farben werden durch Text, Zahlen und
Schraffur ergänzt und funktionieren auch in der Nachtpalette.

Zeitraum, Diagrammbalken und Kalendertage sind echte Links. JavaScript ersetzt
nur den Bericht, aktualisiert den Verlauf und meldet den neuen Zeitraum für
Screenreader. Ohne JavaScript funktionieren dieselben Links serverseitig.
Netzfehler lassen den bisherigen Bericht stehen und erlauben einen neuen Versuch.

`tests/test_parent_report.py` prüft Zuordnung, Erstchecks, Antwortkorrekturen,
Nachholen, Zeitzonen/Sommerzeit, Monats- und Jahresgrenzen, Leerzustände,
Zukunft, Elternrechte, Schreibfreiheit, Browser-Verlauf, Tastatur, Netzfehler,
vier Bildschirmbreiten und die drei Elternpaletten mit isolierten Testdaten.
