# Meine Welt: Interessen und Lernmissionen

## So funktioniert es

1. Das Kind öffnet **Meine Welt** und nennt zuerst sein eigenes Interesse.
2. Karo bildet daraus drei vollständige Spielideen: Treffpunkt, Kreativstudio und Entdeckerreise. Das Kind wählt eine davon.
3. Die Eltern öffnen **Interessen und Spielvorschau ansehen**, betrachten die gewählte Idee gemeinsam mit dem Kind und geben sie frei.
4. Das Kind wählt eine freigegebene Welt. Dort findet es Karos echten nächsten Lernschritt und freiwillige kurze Spielrunden.
5. Nach einer Spielrunde gestaltet es eine eigene Karte. Fertige Karten stehen dauerhaft in **Mein Album**.

Ein Interesse kann später bearbeitet, pausiert, fortgesetzt oder entfernt
werden. Beim Bearbeiten ist eine neue Elternfreigabe nötig. Eltern geben eine
Welt frei; welche freigegebene Welt aktiv ist, entscheidet das Kind selbst.

## Enthaltener Umfang

Aus jedem genannten Interesse entstehen drei geprüfte Spielformen:

- **Treffpunkt** zum Sammeln und gerechten Verteilen
- **Kreativstudio** zum Planen und Gestalten
- **Entdeckerreise** zum Erkunden und Lösen von Aufgaben

Jede Welt bietet zwei interaktive Bruchteil-Missionen: vier gleiche Hälften
verteilen und drei Ganze als Viertel verteilen. Das Kind bewegt die Teile mit
Plus und Minus oder gibt die Anzahl direkt ein. Die Lösung wird auf dem Server
geprüft. Falsche Versuche werden nicht gespeichert und erzeugen keine rote
Bewertung, Punkte, Serie oder Zeitdruck.

Die Welt übernimmt Karos nächsten echten Lernschritt. Wenn für ein bestätigtes
Schulthema eine neue Lernrunde erstellt wird, gibt Karo das freigegebene
Interesse als Gestaltungswunsch mit: Geschichte und Beispiele dürfen dazu
passen, Fachinhalt und Lösungen müssen aus dem Schulmaterial stammen. Die
vorhandene Gegenprüfung bleibt unverändert. Eine bereits laufende Lernrunde
wird nicht heimlich umgeschrieben, sondern direkt fortgesetzt.

Die drei Vorschläge entstehen lokal und sofort, deshalb funktioniert die
Auswahl auch ohne KI-Verbindung. Erst die spätere Erstellung eines neuen
Lernmaterials nutzt Karos ohnehin eingerichtetes Modell. Die zwei
Bruchteil-Missionen sind deutlich als freiwillige Spielrunde getrennt; sie
geben keine falsche Aussage über den allgemeinen Lernstand.

## Zustimmung und Daten

- Neue und geänderte Interessen bleiben bis zur Elternfreigabe gesperrt.
- Alle Änderungen verwenden Karos Anmeldung und CSRF-Schutz.
- Veraltete oder doppelt abgeschickte Formulare werden erkannt.
- Es gibt weiterhin genau das in Karo eingerichtete Kind; über URLs oder Formulare lässt sich kein anderes Kind auswählen.
- Abgeschlossene Albumkarten bleiben erhalten, wenn ein Interesse entfernt wird. Unfertige Missionen dieses Interesses werden entfernt.
- Albumkarten können separat gelöscht werden.
- Es werden keine Fotos, Markenbilder oder externen Bilddienste verwendet. Die Illustrationen sind lokale SVG-Grafiken.
- Die Funktion verändert weder Schulnoten noch Lernstände, Wochenvereinbarungen oder KI-Einstellungen.

Die Migration ist additiv und legt `welt_interest`, `welt_preference` und
`welt_mission` an. Reine Seitenaufrufe schreiben nichts in die Datenbank.

## Bedienbarkeit

Die Ansichten funktionieren mit Tastatur, Maus und Touch. Bedienelemente sind
mindestens 44 Pixel hoch, schmale Ansichten ordnen Karten und Spielflächen neu
an. Die vorhandenen Farbwelten einschließlich Dunkelmodus werden übernommen.
Animationen werden bei aktivierter Einstellung „Bewegung reduzieren“ entfernt.

## Lokaler Betrieb

Karo läuft wie bisher über Compose:

```bash
make up
```

Danach ist die App unter <http://127.0.0.1:8080> erreichbar. **Meine Welt**
erscheint nach der Anmeldung in der Hauptnavigation. Vor dem ersten lokalen
Rollout wurde im Datenvolume die SQLite-Sicherung
`/data/backups/vor-interessenwelten-20260915-112241.db` angelegt.

## Manuelle Prüfliste

1. Im Kindbereich ein Interesse vorschlagen; die Mission darf noch nicht starten.
2. Im Elternbereich Vorschau und Zustimmung markieren, dann freigeben.
3. Im Kindbereich die freigegebene Welt auswählen.
4. Eine Verteilung absichtlich falsch und anschließend richtig prüfen.
5. Eine Karte gestalten, speichern und im Album wiederfinden.
6. Interesse wechseln oder pausieren und prüfen, dass die Albumkarte erhalten bleibt.

Automatisierte Tests decken Rechte, Zustimmung, Statuskonflikte, doppelte
Übermittlungen, parallele Starts, beide Aufgaben in allen drei Spielformen,
Servervalidierung, Albumverhalten, CSRF und HTML-Escaping ab.
