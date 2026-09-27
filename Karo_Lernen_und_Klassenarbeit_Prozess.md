# Karo – Lernprozess und Klassenarbeitsprozess

## Zielbild

Karo hat zwei klar getrennte Bereiche:

- **Lernen**: eigene Lernthemen des Kindes
- **Klassenarbeit**: eigene Prüfungsthemen mit Termin, Kalender und Simulation

Beide Bereiche benutzen darunter denselben Lernmotor und dasselbe **Karo Curriculum + Datenbank-System**.

```text
KARO CURRICULUM + DATENBANK
            ↓
      gemeinsamer Lernmotor
     ↙                    ↘
LERNEN              KLASSENARBEIT
eigene Themen        eigene Prüfungsthemen
                    + Termin
                    + Kalender
                    + Simulation
```

Der Lernmotor arbeitet grundsätzlich so:

```text
prüfen
→ Fehlertyp erkennen
→ passende Erklärung
→ üben
→ erneut prüfen
→ MASTERED
```

Wichtig: Karo soll Fragen und Erklärungen nicht bei jedem Durchlauf frei neu erfinden. Zuerst werden vorhandene, geprüfte Inhalte aus Curriculum und Datenbank verwendet. Nur wenn ein Thema noch nicht vorhanden ist, wird der bestehende Erzeugungs-, Prüf- und Freigabeprozess benutzt.

---

## 1. Prozess „Lernen“

Der Bereich **Lernen** hat seine eigenen Lernthemen. Diese Themen sind unabhängig von Klassenarbeiten und werden separat angezeigt.

### Wie ein Lernthema entsteht

Ein neues Lernthema kann auf mehreren Wegen entstehen:

```text
Kind erstellt ein Thema selbst
oder
Kind lädt ein Themen-/Arbeitsblatt hoch
oder
Eltern legen ein Thema an
↓
Karo erkennt bzw. übernimmt das Thema
↓
Thema erscheint unter „Lernen“
```

Das Kind muss also selbst ein Themenblatt hochladen oder ein neues Thema anlegen können.

### Trennung der Themen

Die Themen unter **Lernen** sind normale Lernthemen.

Beispiele:

```text
Meine Lernthemen
- Brüche addieren
- Prozentrechnung
- Volumen eines Würfels
```

Diese Liste darf nicht mit den Themen einer bestimmten Klassenarbeit vermischt werden.

---

## 2. Curriculum- und Datenbankprozess für Lernthemen

Nachdem ein Thema ausgewählt oder angelegt wurde, sucht Karo zuerst im bestehenden Curriculum und in der Datenbank.

```text
Thema
↓
Karo Curriculum / Katalog durchsuchen
```

### Fall A – Thema ist bereits vorhanden

```text
Thema im Curriculum vorhanden
↓
vorhandenes geprüftes Konzept verwenden
↓
vorhandene Diagnoseaufgaben
vorhandene Fehlertypen
vorhandene Erklärungen
vorhandene Beispiele
vorhandene Übungsaufgaben
vorhandene Hilfen
```

Es soll kein unnötiger neuer Modellaufruf stattfinden.

### Fall B – Thema ist noch nicht vorhanden

Dann wird der bereits vorhandene Karo-Prozess verwendet:

```text
Thema nicht im Curriculum vorhanden
↓
Lernreihe erzeugen
↓
Inhalt prüfen
↓
erst nach erfolgreicher Prüfung freigeben
↓
in Curriculum / Datenbank speichern
↓
ab jetzt wiederverwenden
```

Das bedeutet:

- neue Inhalte werden nicht direkt an das Kind ausgeliefert;
- sie müssen den vorhandenen Prüf- und Freigabeprozess durchlaufen;
- erfolgreiche Inhalte werden gespeichert;
- bei späteren Kindern bzw. späteren Sitzungen werden sie wiederverwendet.

---

## 3. Eigentliche Lernbegleitung

Wenn das Thema im Curriculum verfügbar ist, startet der Lernprozess.

```text
Thema auswählen
↓
Karo prüft zuerst
↓
Was kann das Kind schon?
↓
Wo ist die konkrete Lücke / Fehlvorstellung?
↓
gezielte Erklärung
↓
Beispiel
↓
geführte Aufgabe
↓
selbstständige Aufgabe
↓
erneut prüfen
↓
sicher?
```

### Wenn die Antwort falsch ist

Karo soll nicht nur „falsch“ melden.

Stattdessen:

```text
falsche Antwort
↓
bekannten Fehlertyp in der Datenbank suchen
↓
passende geprüfte Erklärung auswählen
↓
Beispiel zeigen
↓
geführte Übung
↓
selbstständige Aufgabe
↓
erneut prüfen
```

Wenn die gleiche Fehlvorstellung bestehen bleibt:

```text
noch nicht sicher
↓
andere Erklärung
oder
andere Darstellung
↓
weitere Übung
↓
erneut prüfen
```

### Wenn das Kind sicher ist

```text
mehrere passende Antworten / Transfer erfolgreich
↓
Thema = MASTERED
```

Eine einzelne richtige Antwort reicht nicht automatisch aus.

Das Ziel ist nicht „Aufgabe erledigt“, sondern:

```text
Kind kann das Thema sicher
```

---

## 4. Woher kommen Fragen und Erklärungen?

Karo benutzt den bestehenden Curriculum-/Katalog-/Datenbankprozess.

Die Reihenfolge ist:

```text
1. vorhandenes Karo Curriculum
2. geprüfte Inhalte in der Datenbank
3. zugeordnetes Schulmaterial / Wissensbasis
4. bestehender Erzeugungsprozess für fehlende Inhalte
```

### Fragen

Fragen kommen bevorzugt aus gespeicherten, geprüften Aufgabentypen.

Es gibt unterschiedliche Rollen:

```text
Diagnosefrage
Vorhersage
Beispiel
geführte Aufgabe
selbstständige Aufgabe
Transfer / Kontrollfrage
```

Fragen werden passend zur Lernphase ausgeliefert.

### Erklärungen

Erklärungen werden nicht allgemein für ein Thema ausgewählt, sondern möglichst passend zur erkannten Fehlvorstellung.

```text
falsche Antwort
↓
Fehlertyp
↓
passende geprüfte Erklärung
```

Wenn eine Erklärung nicht wirkt:

```text
andere / einfachere Erklärung
oder
andere Visualisierung
```

### Wiederverwendung

Wenn Inhalte bereits geprüft und gespeichert sind:

```text
Datenbanktreffer
↓
kein neuer Modellaufruf nötig
```

Das spart Kosten und sorgt für konsistente Qualität.

---

# 5. Prozess „Klassenarbeit“

Der Bereich **Klassenarbeit** ist separat vom normalen Bereich „Lernen“.

Eine Klassenarbeit besteht aus:

```text
Termin
+
eigene Prüfungsthemen
+
Lernkalender
+
Lernstand pro Prüfungsthema
+
Wiederholung
+
Prüfungssimulation
```

---

## 6. Wer kann eine Klassenarbeit anlegen?

Sowohl das Kind als auch die Eltern.

```text
Kind oder Eltern
↓
Themenblatt hochladen
oder
Prüfungsthemen manuell eingeben
↓
Termin festlegen
↓
Klassenarbeit anlegen
```

Das Kind muss selbst:

- ein Themenblatt hochladen können;
- eine neue Klassenarbeit anlegen können;
- Prüfungsthemen eingeben können;
- den Termin festlegen können.

---

## 7. Prüfungsthemen sind eigene Themen

Die Prüfungsthemen müssen separat von normalen Lernthemen dargestellt werden.

Beispiel:

```text
Klassenarbeit Mathematik
04.10.

Prüfungsthemen
- Brüche addieren
- Brüche kürzen
- Textaufgaben
```

Diese Themen gehören zu genau dieser Klassenarbeit.

Sie dürfen nicht einfach als normale Einträge unter „Meine Lernthemen“ erscheinen.

Die Daten können intern mit einem vorhandenen Curriculum-Thema verknüpft sein, aber die Oberfläche bleibt getrennt.

```text
Lernen
→ Meine Lernthemen

Klassenarbeit
→ Prüfungsthemen dieser Arbeit
```

---

## 8. Prüfungsthemen mit Curriculum verbinden

Für jedes Prüfungsthema macht Karo einen Abgleich:

```text
Prüfungsthema
↓
Karo Curriculum / Datenbank durchsuchen
```

### Bereits vorhandenes Thema

```text
Treffer gefunden
↓
bestehendes Curriculum-Thema verknüpfen
```

Danach stehen sofort zur Verfügung:

- Diagnosefragen
- Fehlertypen
- Erklärungen
- Beispiele
- Übungen
- Kontrollfragen

### Thema fehlt

Dann:

```text
kein Curriculum-Treffer
↓
bestehenden Curriculum-Erstellungsprozess starten
↓
Inhalt erzeugen
↓
prüfen
↓
freigeben
↓
speichern
↓
mit Prüfungsthema verknüpfen
```

Es soll dafür keinen parallelen zweiten Klassenarbeits-Generator geben.

---

# 9. Lernkalender für die Klassenarbeit

Nachdem Termin und Themen bekannt sind, sieht das Kind einen Kalender bis zur Klassenarbeit.

Das Kind entscheidet selbst:

```text
an welchem Tag lernen?
wie lange lernen?
```

Beispiel:

```text
Mo 23
Di —
Mi —
Do 29
Fr 15
Sa —
```

Wichtig:

- Das Kind muss **nicht jeden Tag lernen**.
- Ein leeres Feld bedeutet **kein Lernen an diesem Tag**.
- `0` bedeutet ebenfalls **kein Lernen an diesem Tag**.
- Nur Tage mit einer positiven Lernzeit sind Lerntage.

Der Kalender entscheidet nur:

```text
WANN lernen?
WIE LANGE?
```

Er soll nicht selbst die Didaktik übernehmen.

---

# 10. Was passiert an einem Lerntag?

An einem geplanten Lerntag prüft Karo:

```text
Welche Prüfungsthemen sind noch nicht MASTERED?
```

Dann nimmt Karo das erste noch unsichere Prüfungsthema.

```text
heutiger Lerntag
↓
erstes noch unsicheres Prüfungsthema
↓
„Jetzt lernen“
↓
normaler Karo-Lernmotor
```

Der Lernmotor ist genau derselbe wie unter „Lernen“:

```text
Diagnosefrage
↓
Antwort analysieren
↓
Fehlertyp erkennen
↓
passende Erklärung aus Curriculum / Datenbank
↓
Beispiel
↓
geführte Übung
↓
selbstständige Übung
↓
Kontrollfrage
↓
MASTERED?
```

---

# 11. Ein Thema bleibt aktiv, bis es sicher ist

Karo darf nicht einfach jeden Kalendertag zum nächsten Thema springen.

Beispiel:

```text
Thema 1: Brüche addieren
Thema 2: Brüche kürzen
Thema 3: Textaufgaben
```

Solange Thema 1 nicht sicher ist:

```text
Montag
→ Brüche addieren

Donnerstag
→ Brüche addieren

Freitag
→ Brüche addieren
```

Erst wenn:

```text
Brüche addieren = MASTERED
```

geht es weiter:

```text
nächster Lerntag
→ Brüche kürzen
```

Die tatsächliche Beherrschung entscheidet also über den Fortschritt, nicht ein statischer Tagesplan.

---

# 12. Letzter Lerntag: Wiederholung + Prüfungssimulation

Der letzte geplante Lerntag vor der Klassenarbeit wird automatisch reserviert für:

```text
Wiederholung
+
Prüfungssimulation
```

Die Simulation soll möglichst alle relevanten Prüfungsthemen abdecken.

### Fragen nicht vorher anzeigen

Die Simulationsfragen dürfen vor diesem Tag nicht sichtbar sein.

```text
vor Simulationstag
→ keine Simulationsfragen anzeigen

am Simulationstag
→ Simulation freischalten / erzeugen
```

Dadurch kann das Kind die Fragen nicht vorher lernen.

---

## 13. Simulation optional einen Tag vorziehen

Das Kind kann optional wählen:

```text
Simulation 1 Tag früher
```

Dann wird die Simulation genau einen Tag vorgezogen.

Beispiel:

```text
ursprünglich:
Donnerstag = Simulation

optional:
Mittwoch = Simulation
Donnerstag = frei / Wiederholung / Ruhe
```

Das ist freiwillig.

---

# 14. Prüfungssimulation und Curriculum

Auch die Simulation soll nicht als komplett unabhängiges Quiz funktionieren.

Sie soll auf dem bestehenden Curriculum basieren.

```text
Prüfungsthemen
↓
verknüpfte Curriculum-Konzepte
↓
vorhandene Aufgabentypen
↓
neue Prüfungsvarianten
```

Die Simulation darf neue Zahlen, Varianten und Kombinationen verwenden, aber sie soll fachlich auf dem gespeicherten Curriculum aufbauen.

---

# 15. Klare Trennung in der Oberfläche

## Bereich „Lernen“

Zeigt:

```text
Meine Lernthemen
```

Das Kind kann:

- Thema selbst erstellen
- Themen-/Arbeitsblatt hochladen
- vorhandenes Thema auswählen
- Lernen starten

Nicht anzeigen:

- Klassenarbeitstermin
- Prüfungskalender
- Prüfungssimulation

---

## Bereich „Klassenarbeit“

Zeigt:

```text
Klassenarbeit am …
Prüfungsthemen
Kalender
heutige Lerneinheit
Simulation
```

Das Kind kann:

- Themenblatt hochladen
- Prüfungsthemen eingeben
- Termin setzen
- Lerntage auswählen
- pro Lerntag eine eigene Zeit festlegen
- heute lernen
- Simulation optional einen Tag vorziehen

Die normalen Lernthemen werden hier nicht als Themenliste vermischt.

---

# 16. Verantwortlichkeiten der Komponenten

Die Architektur sollte klar bleiben.

## Karo Curriculum / Datenbank

Verantwortlich für:

- Konzepte
- Fehlertypen
- Diagnoseaufgaben
- Erklärungen
- Beispiele
- geführte Aufgaben
- selbstständige Aufgaben
- Transferfragen
- Hilfen
- Visualisierungen
- geprüften Inhalt

---

## Lernmotor

Verantwortlich für:

```text
prüfen
↓
Fehler erkennen
↓
erklären
↓
üben
↓
erneut prüfen
↓
MASTERED
```

Er wird sowohl von „Lernen“ als auch von „Klassenarbeit“ benutzt.

---

## Bereich Lernen

Verantwortlich für:

- normale Lernthemen
- selbst erstellte Themen
- hochgeladene Lernmaterialien
- Start des Lernmotors

---

## Bereich Klassenarbeit

Verantwortlich für:

- Prüfungstermin
- Prüfungsthemen
- Verknüpfung mit Curriculum-Themen
- Kalender
- Lernzeiten
- Auswahl des aktuell noch unsicheren Prüfungsthemas
- Wiederholung
- Prüfungssimulation

---

# 17. Gesamtablauf Lernen

```text
Kind
↓
Thema erstellen / Blatt hochladen / Thema auswählen
↓
Thema erscheint unter „Lernen“
↓
Curriculum-Treffer?
    ├─ Ja → vorhandenen geprüften Inhalt verwenden
    └─ Nein → erzeugen → prüfen → freigeben → speichern
↓
Diagnose
↓
Fehlertyp erkennen
↓
passende Erklärung
↓
Beispiel
↓
geführte Übung
↓
selbstständige Übung
↓
Kontrollfrage
↓
sicher?
    ├─ Nein → andere Erklärung / weitere Übung
    └─ Ja → MASTERED
```

---

# 18. Gesamtablauf Klassenarbeit

```text
Kind oder Eltern
↓
Themenblatt hochladen
oder Prüfungsthemen eingeben
↓
Termin festlegen
↓
Klassenarbeit anlegen
↓
eigene Prüfungsthemenliste
↓
jedes Prüfungsthema mit Curriculum abgleichen
    ├─ vorhanden → verknüpfen
    └─ fehlt → erzeugen → prüfen → freigeben → speichern
↓
Kalender bis zur Prüfung
↓
Kind wählt nur gewünschte Lerntage + Zeiten
↓
heutiger Lerntag?
    ├─ Nein → nichts tun
    └─ Ja
         ↓
         erstes noch unsicheres Prüfungsthema
         ↓
         normaler Karo-Lernmotor
         ↓
         MASTERED?
             ├─ Nein → nächster Lerntag bleibt beim selben Thema
             └─ Ja → nächstes Prüfungsthema
↓
letzter geplanter Lerntag
↓
Wiederholung + Prüfungssimulation
↓
Klassenarbeit
```

---

# 19. Zentrale Regeln

1. **Kind und Eltern dürfen Themenblätter hochladen.**
2. **Das Kind darf selbst neue Lernthemen erstellen.**
3. **Das Kind darf selbst eine Klassenarbeit mit Themen und Termin anlegen.**
4. **Normale Lernthemen und Prüfungsthemen werden getrennt dargestellt.**
5. **Beide Bereiche verwenden denselben Karo-Lernmotor.**
6. **Fragen und Erklärungen kommen zuerst aus Karo Curriculum und Datenbank.**
7. **Fehlende Inhalte werden über den bestehenden Erzeugungs-, Prüf- und Freigabeprozess ergänzt.**
8. **Ungeprüfte Inhalte werden dem Kind nicht ausgeliefert.**
9. **Eine richtige Antwort allein bedeutet nicht automatisch MASTERED.**
10. **Bei Fehlern wird die konkrete Fehlvorstellung gesucht und gezielt behandelt.**
11. **Ein Prüfungsthema bleibt aktiv, bis es sicher beherrscht wird.**
12. **Das Kind muss nicht jeden Tag lernen.**
13. **Leere Kalendertage sind frei.**
14. **Der letzte geplante Lerntag ist Wiederholung + Simulation.**
15. **Simulationsfragen werden vorher nicht angezeigt.**
16. **Die Simulation kann optional genau einen Tag vorgezogen werden.**
17. **Die Klassenarbeitsplanung plant Zeit und Reihenfolge – der Lernmotor unterrichtet.**
18. **Erfolgreiche Curriculum-Inhalte werden gespeichert und später wiederverwendet.**

---

# 20. Kurzform

```text
LERNEN
= eigene Lernthemen
= Kind kann Thema erstellen oder Material hochladen
= Curriculum + Datenbank
= prüfen → erklären → üben → prüfen → MASTERED
```

```text
KLASSENARBEIT
= eigene Prüfungsthemen
= Kind oder Eltern können Themenblatt hochladen
= Termin + Kalender
= pro Lerntag erstes noch unsicheres Thema
= derselbe Lernmotor
= letzter Lerntag: Wiederholung + Simulation
```

```text
KARO CURRICULUM
= gemeinsame fachliche Quelle für beide Prozesse
= geprüfte Konzepte, Fehlertypen, Fragen, Erklärungen und Übungen
= fehlende Inhalte werden einmal erzeugt, geprüft, gespeichert und danach wiederverwendet
```
