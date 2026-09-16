# Implementierungsauftrag für Codex: „Meine Woche“ in Karo

Du bist der verantwortliche Software Engineer für das bestehende Repository https://github.com/Ferid1088/karo. Implementiere den folgenden Pilot vollständig im vorhandenen Projekt. Liefere funktionierenden, geprüften Code und eine kurze Bedienungsanleitung. Bleibe nicht bei Analyse, Vorschlägen oder Pseudocode stehen.

## 1. Ziel und verbindliche Produktentscheidung

Karo bekommt einen kleinen Bereich „Meine Woche“, der einem Kind beim Anfangen hilft und eine verlässliche Zusammenarbeit mit seinen Eltern ermöglicht. Er unterstützt sowohl altersgerechte Ziele als auch Routinen. Er ist fachlich unabhängig von Karos Lernstand, Quizzen, Erklärungen und Lernzyklen, gehört aber sichtbar zur selben Anwendung.

Die Leitidee lautet: **Ein überschaubarer gemeinsamer Plan darf angepasst werden. Das Kind wird für Schwierigkeiten oder ausgelassene Schritte nicht beschämt. Auch die Eltern übernehmen eine konkrete Aufgabe.**

Für den Pilot gelten diese Grenzen:

- Pro Kind und Woche höchstens ein aktives Wochenziel, eine aktive Routine und eine aktive Elternzusage; einzelne Bestandteile dürfen fehlen.
- Eine Kind-Hauptseite; Einrichtung, Bearbeitung und Rückblick möglichst als kurze Abschnitte oder Dialoge innerhalb des vorhandenen Designs.
- Eine übersichtliche Karte im vorhandenen Eltern-Dashboard, von der aus Eltern die Vereinbarung bearbeiten können.
- Kein zusätzlicher Login, kein zweites Benutzer- oder Rollenmodell und keine doppelte Erfassung bereits vorhandener Kinderdaten.
- Keine KI-Aufrufe für dieses Modul. Vorschläge stammen aus einer kleinen, überprüfbaren Sammlung.
- Keine neue Plattform, kein Frameworkwechsel und kein umfassendes Refactoring der übrigen App.

Dieser Auftrag ersetzt den Umfang eines eventuell vorhandenen älteren „Meine Woche“-Prototyps. Dessen Code ist höchstens wiederverwendbares Material, keine unverändert zu übernehmende Spezifikation. Vorhandene Nutzerdaten dürfen dabei nicht still gelöscht oder überschrieben werden.

## 2. Zuerst den tatsächlichen Repository-Stand prüfen

Lies AGENTS.md und relevante Projektanweisungen. Prüfe Remote, aktuellen Branch, Arbeitsverzeichnis und uncommittete Änderungen. Der korrekte Repository-Owner ist **Ferid1088**.

Ein vorheriger begrenzter Blick auf `master` zeigte FastAPI, Jinja2, SQLite, SessionMiddleware, ein Gate für Anmeldung/CSRF sowie Router für auth, eltern, kind und admin. Das ist ein historischer Hinweis, keine verlässliche Beschreibung deines aktuellen Checkouts. Ein Entwicklungsbranch namens `kind_eltern` könnte existieren; entscheide anhand des vorhandenen Arbeitsstands, nicht anhand einer angenommenen Branchbezeichnung.

Ermittle konkret:

1. Wie Anmeldung, Rollen, Eltern-Kind-Zuordnung und Zugriffsschutz implementiert sind.
2. Ob Karo mehrere Kinder in einer Datenbank unterstützt oder ein bewusstes Ein-Kind-Installationsmodell hat.
3. Wo Kind-Startseite, Eltern-Dashboard, Navigation und gemeinsame Templates liegen.
4. Wie Datenbankinitialisierung, Migrationen, Transaktionen und Tests funktionieren.
5. Ob `app/woche/` oder Teile des früheren Patches bereits existieren.
6. Ob es eine etablierte Zeitzone und Datumsbehandlung gibt.

Arbeite im vorgesehenen Checkout. Überschreibe keine fremden Änderungen; nutze bei Bedarf einen isolierten Branch oder Worktree. Kein force push, kein automatisches Merge und keine Veröffentlichung. Für diesen Auftrag sind lokale Implementierung und Prüfung ausreichend.

Halte nach der Untersuchung einen kurzen Arbeitsplan fest und implementiere anschließend selbstständig. Frage nur bei einer tatsächlich blockierenden fachlichen oder destruktiven Entscheidung nach. Routinemäßige technische Entscheidungen triffst du selbst und dokumentierst relevante Annahmen.

## 3. Der konkrete Nutzerablauf

### 3.1 Gemeinsame Wochenvereinbarung

Eltern öffnen aus ihrem bestehenden Dashboard „Meine Woche“ für das berechtigte Kind. Das kurze Formular ist für ein gemeinsames Gespräch mit dem Kind gedacht, ungefähr drei Minuten.

Es enthält:

- **Wochenziel:** „Was möchtest du diese Woche schaffen?“ Auswahl aus wenigen altersgerechten Vorschlägen oder ein kurzer eigener Text.
- **Erster Schritt:** eine konkrete, sofort ausführbare Handlung, möglichst unter zwei Minuten. Beispiel: „Öffne deine Referatsnotizen und markiere eine Stelle, die du erklären möchtest.“ Der Einstieg erleichtert den Beginn; er ersetzt nicht das eigentliche Wochenziel.
- **Routine:** eine kleine wiederkehrende Handlung mit ausgewählten Wochentagen. Beispiel: „Dienstags und donnerstags zehn Minuten am Referat arbeiten.“ Keine komplizierten Wiederholungsregeln im Pilot.
- **Elternzusage:** ein konkreter Beitrag mit optionalem Tag und Uhrzeit. Beispiel: „Papa hört dir am Donnerstag um 18 Uhr zehn Minuten zu.“
- **Gemeinsame Bestätigung:** Eltern bestätigen ausdrücklich „Mit meinem Kind besprochen“. Das ist eine dokumentierte Selbstauskunft der Eltern, kein behaupteter Nachweis einer separaten Kind-Zustimmung.

Eigene Texte müssen kurz bleiben, beispielsweise Ziel bis 160 Zeichen, Einstieg und Zusage bis 240 Zeichen. Validierung serverseitig; Grenzen zentral festlegen und in Formularen verständlich anzeigen.

Die Vereinbarung darf auch nur eine Routine oder ein Ziel enthalten. Es gibt keine Pflicht, alle Felder auszufüllen. Ein vollständig leeres Formular erzeugt keinen aktiven Plan.

Das Kind sieht unmittelbar, was vereinbart wurde, kann „Passt für mich“ oder „Bitte ändern“ antippen. Eine Änderungsbitte erscheint bei den Eltern. Bei einer wesentlichen späteren Änderung von Ziel, Routine oder Zusage wird eine frühere Kind-Bestätigung zurückgesetzt. Die Kind-Bestätigung blockiert das Ausprobieren nicht.

### 3.2 Kind-Seite „Meine Woche“

Die vorhandene Kind-Navigation erhält einen gut sichtbaren Eintrag. Gemeinsame Karo-Kopfzeile, Typografie, Farben und Komponenten weiterverwenden.

Die Seite zeigt in dieser Reihenfolge:

1. Das Wochenziel in einem kurzen Satz, sofern vorhanden.
2. Genau eine hervorgehobene Karte „Dein nächster Schritt“.
3. Drei eindeutige Aktionen: **Loslegen**, **Heute nicht**, **Hilfe**.
4. Die Elternzusage, zum Beispiel „Am Donnerstag hört Papa dir zu“.
5. Einen kleinen aufklappbaren Bereich für Routine, gemeinsame Vereinbarung und optionale Wochenrückmeldung.

Wenn noch nichts vereinbart ist: „Was möchtest du diese Woche angehen? Legt gemeinsam etwas Kleines fest.“ Kein leerer Fehlerzustand und keine automatische Planerzeugung.

Auswahl des nächsten Schritts deterministisch halten:

- Bei Pause: keine Startkarte; „Woche fortsetzen“ anbieten.
- Bei ungelöstem Hilfewunsch zur aktuellen Aktivität: Hilfestatus und gegebenenfalls Elternantwort anzeigen, keine neue Hilfeaufforderung erzwingen.
- Sonst eine heute anstehende, noch nicht rückgemeldete Routine priorisieren.
- Andernfalls den aktiven Einstieg zum Wochenziel anbieten, sofern dieser heute noch nicht abgeschlossen oder für heute ausgeblendet wurde und das Ziel nicht als erreicht gemeldet ist.
- Ist heute nichts mehr vorgesehen: neutral „Für heute ist hier nichts weiter vorgesehen“. Keine zusätzliche Beschäftigung erfinden.

Eine verpasste Routine wird nicht am nächsten Tag nachgeholt. Ein Wochenziel bleibt während der Woche verfügbar, ohne jeden Tag automatisch einen neuen angeblichen Teilschritt zu erzeugen.

### 3.3 Loslegen und Rückmeldung

„Loslegen“ zeigt die konkrete Handlung und danach zwei einfache Rückmeldungen:

- **Geschafft**: bedeutet „diesen Schritt gemacht“, nicht „Wochenziel erreicht“ und nicht „Thema beherrscht“.
- **War schwierig**: zeigt wenige freiwillige Auswahlmöglichkeiten: „Zu schwer“, „Keine Zeit“, „Weiß nicht, wie anfangen“, „Etwas anderes“. Freitext ist optional, keine Nachfragekette.

Passende Reaktion:

- Zu schwer / weiß nicht wie: einen einmalig einfacheren, fachlich passenden Einstieg anbieten oder Hilfe ermöglichen.
- Keine Zeit: für heute beenden, ohne Nachholpflicht.
- Etwas anderes: eine neutrale Auswahl „Hilfe“ oder „Für heute aufhören“.

Keine unbegrenzte automatische Verkleinerung. Keine Diagnosen oder Charakterurteile. Nach einem abgeschlossenen Schritt darf das Kind freiwillig selbst weiterarbeiten; die App erzeugt keine weiteren Pflichtaufgaben.

„Heute nicht“ blendet nur die betreffende Aktivität für das heutige lokale Datum aus. Es verändert weder das Wochenziel noch den Plan und zählt nicht als Misserfolg. Eine einfache Möglichkeit „Doch starten“ muss erreichbar sein. Diese Auswahl wird nicht als negatives Elternsignal angezeigt.

Das Erreichen des Wochenziels ist eine separate freiwillige Aktion „Wochenziel erreicht“. Diese Meldung muss korrigierbar sein und als Kind-Selbstauskunft behandelt werden.

### 3.4 Hilfe mit verbindlicher Elternreaktion

„Hilfe“ erzeugt einen ausdrücklich vom Kind ausgelösten Hilfewunsch. Vor dem Absenden ist erkennbar: „Das sehen deine Eltern“. Keine Nachricht an E-Mail, Messenger oder externe Dienste senden; im Pilot nur in Karo anzeigen.

Das Kind kann zwischen „Erklären“, „Zusammen anfangen“ und „Kurz sprechen“ wählen. Zusätzlicher Text bleibt optional.

Eltern sehen die Anfrage im bestehenden Dashboard und können:

- „Ich helfe dir“ bestätigen, optional mit einem konkreten Termin und kurzem Text.
- Den Hilfewunsch nach der Unterstützung als erledigt markieren.

Das Kind sieht die Reaktion. Es kann eine eigene Anfrage zurücknehmen. Wiederholtes Klicken darf keine identischen offenen Hilfewünsche erzeugen. Ein bloßes Bestätigen durch Eltern darf die Hilfe noch nicht als geleistet markieren. Definiere dafür einfache Zustände wie angefragt, zugesagt, erledigt, zurückgenommen.

Private Schwierigkeitengründe aus der Rückmeldung werden nicht automatisch an Eltern weitergereicht. Beim Hilfewunsch muss klar sein, welche Angaben sichtbar werden.

### 3.5 Pause, Wochenwechsel und Rückblick

- Kind und berechtigte Eltern können die aktuelle Woche pausieren und wieder fortsetzen.
- Pause erzeugt keine Strafe, keine Warnung und keine nachträgliche Aufholpflicht.
- Eine vorhandene Elternzusage bleibt während der Pause sichtbar; nichts wird extern abgesagt.
- Die Woche läuft von Montag bis Sonntag in der konfigurierten lokalen Zeitzone. Wenn Karo keine Konfiguration besitzt, verwende für diesen Pilot Europe/Berlin an einer zentralen Stelle.
- Eine abgelaufene Woche wird nicht automatisch kopiert oder als gescheitert markiert.
- Eltern können „Für nächste Woche übernehmen“ wählen und die Vereinbarung anpassen. Das erzeugt einen Entwurf bzw. eine neue Wochenvereinbarung, keine kopierten Fortschritte, Kind-Bestätigungen oder Hilfestatus.
- Offene Hilfewünsche verschwinden beim Wochenwechsel nicht; Eltern können sie weiterhin bearbeiten, mit erkennbarer Herkunftswoche.
- Optionaler Rückblick mit zwei Klicks: „Gut / Ging so / War schwierig“ und „So lassen / Leichter / Anders“. Der Rückblick ist ausdrücklich als gemeinsame Rückmeldung gekennzeichnet und für Eltern sichtbar; keine Pflicht.
- Ohne Rückmeldung keine psychologische Interpretation und kein erfundenes Lob.

## 4. Eltern-Dashboard und klare Sichtbarkeit

Die Elternkarte zeigt ausschließlich überprüfbare Angaben:

- Welches Ziel und welche Routine vereinbart sind.
- Welche Elternzusage gilt.
- Ob das Kind eine Änderung angefragt hat.
- Freiwillig gemeldete positive Fortschritte, etwa „Ein Einstieg als geschafft gemeldet“, ohne Quote, Tagesvergleich oder detaillierte Uhrzeiten.
- „Wochenziel als erreicht gemeldet“, ausdrücklich als Selbstauskunft.
- Aktuelle Hilfewünsche und Antworten.
- Gemeinsame Wochenrückmeldung, sofern abgegeben.
- Pause, sofern aktiv.

Ohne Aktivitätsmeldungen heißt es „Noch keine Rückmeldung“. Nicht „inaktiv“, „faul“, „läuft schlecht“ oder automatisch „läuft gut“.

Eltern haben die Verwaltungsrechte über Vereinbarungen für ihre zugeordneten Kinder und dürfen den jeweiligen Kindbereich ansehen. Das Kind hat keinen Zugriff auf Elternverwaltung oder andere Kinder. Interne Schwierigkeitengründe und „Heute nicht“-Entscheidungen gehören nicht in das Dashboard. Setze diese Begrenzung auch serverseitig um, statt Daten lediglich mit CSS zu verstecken.

Erkläre auf der Kind-Seite in wenigen Worten „Das sehen deine Eltern“. Versprich keine umfassende Privatheit gegenüber Personen mit direktem Datenbank- oder Serverzugriff.

## 5. Altersgerechte Vorschläge

Nutze vorhandene Klassen- oder Altersangaben. Keine erneute Pflichtabfrage, wenn Karo diese Daten bereits kennt. Bei fehlenden Angaben neutrale Vorschläge, keine erfundene Altersannahme.

Erstelle eine kleine Sammlung für etwa Klassen 3–5, 6–8 und 9–10. Eigene Texte bleiben möglich; die Gruppierung ist Orientierung, keine starre Einschränkung.

Beispiele für Klassen 6–8:

- Ziel: „Meinen Referatseinstieg sicher erzählen.“ Einstieg: „Öffne deine Notizen und lies den ersten Satz laut.“
- Ziel: „Eine Mathefrage klären, bei der ich gerade hänge.“ Einstieg: „Such eine Aufgabe aus und markiere die unklare Stelle.“
- Routine: „Dienstags und donnerstags zehn Minuten am eigenen Projekt arbeiten.“
- Alltag: „Zwei feste Zeiten für mein eigenes Vorhaben ausprobieren.“
- Elternzusage: „Ich nehme mir am Donnerstag zehn Minuten zum Zuhören.“

Für ältere Kinder keine standardmäßigen Missionen wie „Schultasche selbst packen“. Keine erzwungene Jugendsprache, keine pauschalen Leistungsversprechen. Schule darf vorkommen, aber das Modul ist auch für Alltag und eigene Interessen nutzbar.

## 6. Technische Integration

### 6.1 Modulgrenzen

Verwende nach Möglichkeit `app/woche/` für eigene Logik. Wähle wenige Dateien mit klaren Aufgaben, passend zum Repository, etwa Modelle/Validierung, Datenzugriff, Regeln/Vorschläge und Router. Bestehende Projektkonventionen gehen einer starren Dateiliste vor.

- Eigene Tabellen mit `woche_`-Präfix sind sinnvoll.
- Bestehende DB-Verbindung, Benutzeridentität, Rollenprüfungen, CSRF-Schutz, Templates und Navigation wiederverwenden.
- Keine eigene Login-Lösung, keine globale „aktuell gewähltes Kind“-Variable und keine globale Ein-Kind-Zeile als Ersatz für vorhandene Identitäten.
- Bei vorhandenem Mehrkindmodell müssen alle relevanten Datensätze der korrekten Kindidentität zugeordnet sein; wo sinnvoll bestehende Fremdschlüssel verwenden.
- Bei bewusst isolierter Ein-Kind-Installation das vorhandene Modell respektieren. Keine vollständige Mandantenplattform bauen; die Beschränkung klar dokumentieren und keine Mehrkindfähigkeit behaupten.
- Schema über den vorhandenen Start-/Migrationsmechanismus anlegen, nicht bei jeder Seitenansicht.
- Seitenaufrufe schreiben keine Geschäftsereignisse und erzeugen keine Wochenpläne.

Die alte Forderung „genau zwei Zeilen in main.py“ ist kein Ziel. Ändere gezielt alle notwendigen Integrationsstellen, einschließlich Navigation, Rollen, Migrationen und Tests.

### 6.2 Datenmodell

Entwirf das kleinste verständliche Modell für:

1. Wochenvereinbarung mit Kindbezug, Wochenbeginn, Ziel, Einstieg, Routine/Wochentagen, Elternzusage, optionalem Zusagetermin, Pause und Bestätigungs-/Änderungsstatus.
2. Aktivitätsrückmeldungen mit eindeutiger Zuordnung zu Woche, Aktivität und lokalem Datum; speichere nur notwendige Angaben.
3. Hilfewünsche mit Kind-/Wochenbezug, freiwillig geteiltem Inhalt, Status und Elternantwort.
4. Optionaler Wochenrückmeldung, wenn diese nicht bereits sinnvoll in der Vereinbarung gespeichert wird.

Das ist eine fachliche Liste, keine Pflicht zu exakt vier Tabellen. Kein Event-Sourcing und keine große Profiling-Engine einführen.

Erzwinge die relevanten Invarianten mit DB-Constraints und Transaktionen, insbesondere nur eine Vereinbarung pro Kind/Woche, zulässige Statuswerte und Schutz vor doppelten Rückmeldungen. Eine Routine kann pro geplantem Datum einmal als geschafft gelten, ohne dadurch die ganze Routine zu beenden.

„Heute nicht“ nur so lange und so detailliert speichern, wie es für die heutige Ausblendung erforderlich ist. Keine Langzeitstatistik darüber. Falls Schwierigkeitengründe für die einmalige Antwort nicht persistiert werden müssen, speichere sie nicht.

Keine unveränderlichen Ereignis-Trigger, die spätere Datenkorrektur oder das im Projekt etablierte Löschen von Kinderdaten verhindern. Integriere neue Tabellen in vorhandene Lösch-/Exportabläufe, soweit diese Kinderdaten bereits abdecken.

Wenn ein früherer Prototyp eigene Kinddaten besitzt, führe eine nachvollziehbare, idempotente Migration durch. Bei mehrdeutiger Zuordnung keine Daten einem beliebigen Kind zuweisen. Bestehenden Datenbestand sichern bzw. erhalten und die konkrete Zuordnungsfrage melden.

### 6.3 Rollen und Eingabesicherheit

Prüfe Berechtigung an jeder lesenden und schreibenden Route anhand der Session und des tatsächlichen Datensatzes. Eine URL oder eine versteckte Schaltfläche ist kein Zugriffsschutz.

Verbindlich:

- Nicht angemeldete Nutzer erhalten keinen Zugriff auf Wochen- oder Hilfedaten.
- Kind kann nur eigene zulässige Aktionen ausführen und keine Elternzusage bestätigen oder Elternhilfe als geleistet ausgeben.
- Eltern können ausschließlich berechtigte Kinder verwalten.
- Übergebene Kind-, Wochen-, Aktivitäts- oder Anfrage-IDs dürfen diese Regeln nicht umgehen.
- Elternaktionen benötigen eine ausdrückliche serverseitige Elternrollenprüfung; ein allgemeines `session.auth` genügt nicht.
- Vorhandenen CSRF-Schutz für alle zustandsändernden Requests anwenden.
- Parametrisierte SQL-Abfragen, serverseitige Längen-/Enum-/Datumsvalidierung und sichere Template-Ausgabe.
- Keine neuen Logs mit sensiblen Kindtexten.
- Browser-Refresh und Doppelklick dürfen keine doppelten Erfolge, Pläne oder Hilferufe erzeugen.
- Bei veralteten Formularen bestehende neuere Änderungen nicht still überschreiben; verwende eine einfache Versions-/Updated-at-Prüfung oder eine gleichwertige vorhandene Lösung.

Fehlt im Checkout die benötigte Rollenbasis vollständig, benenne das früh und implementiere den kleinsten sicheren Anschluss an Karos Authentifizierung. Erzeuge keine scheinbare Trennung durch bloß unterschiedliche URLs. Eine notwendige umfangreiche Auth-Umstellung ist ein konkreter Klärungspunkt, keine Ausrede, ungeschützte Elternaktionen auszuliefern.

### 6.4 Optionale Verbindung zu Lerninhalten

Das Modul muss ohne Lerninhalte vollständig funktionieren. Nur falls der Checkout bereits eine einfache, berechtigungsgeprüfte Schnittstelle dafür hat, darf ein vorhandenes Thema als Kontext ausgewählt oder ein Link zur passenden Karo-Lernseite angeboten werden.

- Keine Quiz-, Noten- oder Lernstandsdaten verändern.
- Kein automatischer Start eines Lernzyklus.
- Keine Umwandlung von „Schritt geschafft“ in „Wissen verbessert“.
- Keine erneute Abfrage bereits vorhandener Fachangaben erzwingen.
- Keine fragile SQL-Brücke gegen vermutete Tabellennamen bauen.

Fehlt eine saubere Schnittstelle, lass diese optionale Verbindung im Pilot weg und dokumentiere das. Sie ist kein Abnahmeblocker.

## 7. Bewusst nicht im Pilot

- Punkte, Abzeichen, Streaks, Bestzeiten, Ranglisten oder Erfolgsquoten.
- Rote Warnungen für ausgelassene Schritte, Nachholschulden oder automatische Übertragung.
- Speedruns, Video-/Audioaufnahmen, Foto-Uploads oder Interessen-Freigabeworkflows.
- Zusätzlicher Stundenplan-Editor, OCR oder vollständiger Kalender.
- KI-generierte Aufgaben, Agentenketten, Verhaltensprofile oder Diagnosen.
- Automatische Folgerungen aus Nichtnutzung oder mehrwöchige Vermeidungsanalysen.
- Starre Schlafenszeit-Sperren oder ein Notfallmodus für Klassenarbeiten.
- Push, E-Mail, Messenger, externe Benachrichtigungen oder neue Hintergrundjobs.
- Eine zweite App-Navigation, zusätzliche Pflichtseiten oder ein separates Elternportal.

## 8. Oberfläche und Verständlichkeit

- Kurze deutsche Sätze, große gut lesbare Schaltflächen, wenig Pflichttexteingabe.
- Auf etwa 360–400 Pixel Breite nutzbar, ohne horizontales Scrollen.
- Bestehendes responsives Design und Light-/Dark-Modus übernehmen, soweit vorhanden.
- Native Formularlabels, Tastaturbedienbarkeit, sichtbarer Fokus und verständliche Fehlermeldungen.
- Status nicht ausschließlich durch Farbe unterscheiden.
- Erfolgreiche Aktionen sichtbar bestätigen, ohne übertriebenes Lob oder Animationen.
- Keine technischen IDs, Datenbankbegriffe oder Implementierungsdetails in der Nutzeroberfläche.
- Während eine Aktion gespeichert wird, Mehrfachklicks möglichst verhindern; serverseitige Absicherung bleibt erforderlich.

## 9. Tests und konkrete Abnahme

Ermittle zuerst einen angemessenen Ausgangsstand der relevanten bestehenden Tests. Behauptungen über 32 bestandene Tests oder sieben alte Fehler aus früheren Gesprächen gelten nicht als aktueller Nachweis.

Schreibe gezielte Tests für Geschäftsregeln, Integration und Zugriffsgrenzen. Vermeide Tests, die lediglich Funktionsnamen, Dateinamen oder den eigenen Implementierungstext spiegeln.

Verbindliche Szenarien:

1. Berechtigte Eltern legen gemeinsam besprochene Vereinbarung an; sie erscheint für das richtige Kind und im Eltern-Dashboard.
2. Ziel allein und Routine allein funktionieren. Ein komplett leerer Plan wird nicht gespeichert.
3. Kein Login, falsche Rolle, fremde Kind-ID und fremde Hilfewunsch-ID werden bei Lesen und Schreiben abgewehrt. Bei Mehrkindfähigkeit mindestens zwei Familien/Kinder in den Tests verwenden.
4. Das Kind kann keine Elternvereinbarung verwalten und keine Elternantwort durch direkten POST vortäuschen.
5. „Loslegen“ allein erzeugt noch keinen Erfolg. „Geschafft“ bestätigt nur die betreffende Aktivität; das Wochenziel bleibt separat.
6. Doppelte Requests erzeugen keine doppelten Erfolgsrückmeldungen, Hilferufe oder Wochenvereinbarungen.
7. „Heute nicht“ blendet nur heute aus, kann rückgängig gemacht werden und führt zu keinem negativen Dashboardeintrag.
8. Routine wird nur an vereinbarten Tagen angeboten; keine Nachholpflicht für verpasste Tage.
9. Die Auswahl der nächsten Karte entspricht der festgelegten Priorität, einschließlich Pause und ungelöster Hilfe.
10. Schwierigkeitengründe gelangen nicht unbemerkt in die Elternausgabe. Ohne Rückmeldung entsteht keine Erfolgs- oder Misserfolgsbehauptung.
11. Hilfe kann angefragt, zugesagt, erledigt und zurückgenommen werden; die jeweilige Gegenseite sieht den korrekten Status. Zusage bedeutet noch nicht erledigt.
12. Pause und Fortsetzen funktionieren; die Elternzusage bleibt sichtbar.
13. Wochenwechsel, Sonntag/Montag und ein Datum nahe Mitternacht folgen der lokalen Zeitzone. Übernehmen kopiert Inhalte, keine Aktivitätsdaten; offene Hilfe bleibt bearbeitbar.
14. Wesentliche Planänderung setzt die Kind-Bestätigung zurück; veraltete Formulare überschreiben keine neueren Daten still.
15. Migration/Initialisierung lässt sich wiederholen und erhält bestehende Karo-Daten. Alt-Prototyp-Daten werden nicht still gelöscht oder falsch zugeordnet.
16. Neue Aktivitäten ändern keine vorhandenen Lernstände, Quizdaten oder Lernzyklen und lösen keine KI-Aufrufe aus.
17. CSRF-Abweisung und unsichere Texteingaben werden über tatsächliche Requests geprüft; vorhandene Sicherheitsfixtures nutzen.

Führe außerdem die nach Projektvorgaben notwendigen Regressionstests aus. Unterscheide vorbestehende Fehler nachvollziehbar von neuen Fehlern. Keine betroffenen Tests deaktivieren, um einen grünen Bericht zu erzielen.

Prüfe die Oberfläche, wenn Browser-/Preview-Werkzeuge vorhanden sind, einmal als Kind und einmal als Elternteil sowie auf schmalem Bildschirm. Falls eine visuelle Prüfung nicht möglich ist, benenne die Einschränkung und liefere eine kurze manuelle Prüfliste. Behaupte keine durchgeführten Prüfungen, die du nicht ausgeführt hast.

## 10. Umsetzungsschritte und Ergebnis

Arbeite in dieser Reihenfolge:

1. Checkout, bestehende Regeln, Authentifizierung, Datenmodell und eventuell vorhandenen Prototyp untersuchen.
2. Kurzen konkreten Implementierungsplan festlegen; Annahmen nennen.
3. Datenmodell und sichere Migration umsetzen.
4. Berechtigungsprüfungen und kleine Geschäftslogik implementieren.
5. Kind-Seite und Elternkarte in vorhandene Navigation und Templates integrieren.
6. Gezielte Sicherheits-, Geschäftsregel- und Integrationstests ausführen; neue Fehler beheben.
7. Oberfläche und Regressionen im erforderlichen Umfang prüfen.
8. Kurze Dokumentation im Repository ergänzen, einschließlich Startbefehlen aus dem tatsächlichen Projekt und gegebenenfalls Migrationshinweisen.

Verwende klare Namen und kleine Funktionen mit jeweils einer Aufgabe. Schreibe kurze hilfreiche Kommentare und Docstrings direkt in den Code, besonders an fachlichen Regeln und Zugriffskontrollen; kommentiere keine offensichtlichen Einzeiler. Halte dich bei Sprache und Stil an Karos vorhandenen Code. Vermeide Magic Numbers und versteckte globale Zustände.

Du sollst die Änderungen direkt im Repository implementieren. Liefere keinen Patch als alleinigen Ersatz und fordere mich nicht auf, Imports oder Dateien per Hand einzubauen. Verwende kein heuristisches `einbau.py`, wenn du die betroffenen Projektdateien direkt kontrolliert ändern kannst.

Dein Abschlussbericht enthält knapp:

- Was Kind und Eltern jetzt konkret tun können.
- Welche wesentlichen Dateien geändert wurden und warum.
- Wie Authentifizierung, Rollen und Kindzuordnung angebunden wurden.
- Welche Migrationen und Einschränkungen existieren.
- Welche Tests tatsächlich ausgeführt wurden und deren Ergebnisse, einschließlich vorbestehender Fehler.
- Exakte Startbefehle und tatsächliche lokale Routen zur Nutzung; keine erfundenen Ports.
- Eine manuelle Prüfung in höchstens sechs Schritten.

Die Arbeit ist abgeschlossen, wenn der beschriebene Pilot im bestehenden Karo erreichbar ist, seine Daten korrekt speichert, Rollen serverseitig schützt und die relevanten Tests bestehen bzw. bestehende unabhängige Fehler sauber abgegrenzt sind. Offene Sicherheits- oder Datenintegritätsprobleme dürfen nicht als fertiges Ergebnis dargestellt werden.
