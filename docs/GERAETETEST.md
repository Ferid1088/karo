# Gerätetest: Blatt lesen

Die Playwright-Tests prüfen, was sich automatisch prüfen lässt: dass die
Knöpfe dastehen, dass der Datei-Knopf PDFs zulässt, dass der Hinweis vor der
Kamera kommt. Was sie **nicht** prüfen können, ist, ob Ihr Kind mit dem iPad
in der Hand ein Blatt so fotografiert bekommt, dass Karo es lesen kann. Dafür
braucht es echte Geräte und eine Hand.

Diese Liste hakt ein Mensch ab — nicht Karo.

Vorbereitung: Karo läuft (`http://127.0.0.1:8080`), ein Schulblatt liegt
bereit (Mathe, mit Regel/Beispiel/Aufgaben), dazu ein PDF vom Lehrer und
ein eingescanntes PDF ohne Textebene.

## Pro Gerät

Jeweils unter **Schulblätter → Ein Blatt hinzufügen**.

| | iPad (Safari) | Android-Tablet (Chrome) | Windows-PC | Mac (Safari) |
|---|---|---|---|---|
| Knopf „Blatt fotografieren" da | ☐ | ☐ | ☐ (soll **fehlen**) | ☐ (soll **fehlen**) |
| Hinweis erscheint **vor** der Kamera | ☐ | ☐ | — | — |
| Kamera öffnet sich, Foto landet im Feld | ☐ | ☐ | — | — |
| Fortschritt sichtbar (Prozent) | ☐ | ☐ | ☐ | ☐ |
| Text erscheint im Feld, lesbar | ☐ | ☐ | ☐ | ☐ |
| „Datei wählen" zeigt **auch PDFs** | ☐ | ☐ | ☐ | ☐ |
| PDF mit Textebene: sofort da, kein Prozentbalken | ☐ | ☐ | ☐ | ☐ |
| Gescanntes PDF: liest Seite für Seite | ☐ | ☐ | ☐ | ☐ |
| Mehrseitiges PDF: Seiten lassen sich abwählen | ☐ | ☐ | ☐ | ☐ |
| iPhone-Foto (HEIC) wird angenommen | ☐ | — | ☐ | ☐ |
| Drag & Drop | — | — | ☐ | ☐ |
| Zweites Blatt: Lesehilfe lädt **nicht** neu | ☐ | ☐ | ☐ | ☐ |
| Abschicken → Abschnitte in der Wissensbasis | ☐ | ☐ | ☐ | ☐ |

## Worauf es ankommt

**Der Hinweis vor der Kamera.** Er muss *vor* dem Kameradialog stehen, und er
muss stimmen: das Foto bleibt auf dem Gerät, nur der Text geht weiter. Steht
er danach, ist er wertlos.

**Kein Kamera-Knopf ohne Kamera.** Am Schreibtisch-PC wäre er eine Sackgasse.

**PDFs auf dem iPad.** Das ist die Stelle, die am leichtesten kaputtgeht: mit
`capture` am Datei-Feld lässt iOS nur die Kamera zu, und aus der Dateien-App
kommt nichts. Wenn die PDF-Zeile hier leer bleibt, ist genau das passiert.

**Das zweite Blatt.** Beim ersten Mal lädt der Browser rund 21 MB Lesehilfe.
Beim zweiten darf das nicht wieder passieren — sonst ist Karo im Mobilfunknetz
unbenutzbar. (Sichtbar in den Entwicklerwerkzeugen unter „Netzwerk": beim
zweiten Blatt sollte dort nichts Großes mehr stehen.)

## Wenn etwas nicht geht

Es gibt immer einen Weg weiter, und er steht in der Oberfläche: Text eintippen.
Das Blatt wird trotzdem hochgeladen. Wenn ein Gerät gar nicht lesen kann,
bietet Karo an, auf dem Server zu lesen — dem Rechner, auf dem Karo läuft, und
die Datei wird sofort danach gelöscht. Beides ist kein Fehler, sondern der
Rückfall. Notieren Sie trotzdem, welches Gerät es war.
