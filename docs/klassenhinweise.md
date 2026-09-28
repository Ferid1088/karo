# Profilklasse und fachliche Einordnung

Die Profilklasse ist Kontext des Kindes, keine Klassifizierung eines Themas.
`lern_konzept.klasse_von/klasse_bis` gehören zum geprüften Inhalt. Neue lokale
Themenkarten erhalten nur bei einem vorhandenen Katalogtreffer eine `topic.grade`;
sonst bleibt sie leer. Historische Formularwerte gelten nicht als Nachweis.

## Lernweg

1. Karo sucht das Thema im gewählten Fach, unabhängig von der Profilklasse.
2. Fehlendes Material wird vorbereitet und geprüft; es startet noch keine Sitzung.
3. Liegt die Profilklasse außerhalb des Inhaltsbereichs, erscheint ein Hinweis
   mit beiden Angaben und den Entscheidungen „Ja, trotzdem lernen“ und „Zurück“.
4. Nur die ausdrückliche, CSRF-geschützte Bestätigung speichert eine Zustimmung
   und eine Nachricht im Elternbereich (`learning_grade_notice`, eine Transaktion).
5. Die Zustimmung gilt für Lernbereich, Themenkarte, Konzept, Klassenbereich und
   Profilklasse. Fortsetzen, neue Runden und Antworten prüfen diese Bindung erneut.
   Persönliche Themen und einzelne Prüfungen autorisieren einander nicht.

Die Eltern können Nachrichten als gelesen markieren. Das löscht keine Zustimmung.
Es wird keine E-Mail verschickt. Eine Profiländerung kann einen neuen Hinweis auslösen.

## Inhaltserzeugung

- Curriculum-Dienst: Das Exportniveau bleibt innerhalb des genehmigten Curriculums.
  Die App verlangt die `classification`-Metadaten des Dienstes und gleicht den
  Klassenbereich der Lektion damit ab. Fehlende/widersprüchliche Angaben werden
  nicht importiert. Zuerst den aktualisierten Dienst bereitstellen, dann die App.
- Optionaler lokaler Generator: Der Autor bekommt keine Profilklasse. Eine zweite,
  unabhängige Einordnung sieht Thema und Aufgaben, aber weder Profilklasse noch
  vorgeschlagene Klassenlabels. Nur übereinstimmende, als sicher bewertete Angaben
  werden gespeichert. Sonst bleibt der Auftrag ohne Freigabe. Das ist eine zusätzliche
  Modellprüfung, kein Beweis pädagogischer Fehlerfreiheit und kein Ersatz für
  Fachredaktion. Pro neuer lokaler Lektion entsteht ein zusätzlicher Modellaufruf.
- Geteilte Inhalte werden wiederverwendet; Zustimmung und Lernfortschritt bleiben lokal.
- Vorhandene Lerndaten werden nicht gelöscht oder pauschal umklassifiziert.

## Regressionstests

`tests/test_grade_guidance.py` prüft Zustimmung, Elternzugriff, CSRF, Bereichstrennung,
Profilwechsel, Fortsetzen sowie Erzeugung und Ablehnung unbestätigter Einordnungen.
`tests/test_curriculum_bridge.py` prüft den Metadatenvertrag und Import bei abweichender
Profilklasse. Die Tests laufen ausschließlich mit temporären App-Datenbanken.
