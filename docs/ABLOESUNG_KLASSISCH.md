# Ablösung des klassischen Lernwegs

Es gab zwei Lernwege nebeneinander (siehe `LERNKREISLAUF.md`). Seit
Schritt 4 gilt: **der adaptive Weg (`app/adaptiv/`) ist der Lernweg.** Der
klassische Weg ist *eingefroren* — er trägt noch den Alltag, aber er wächst
nicht mehr.

## Was „eingefroren" heißt

| | eingefroren | abgeschaltet |
|---|---|---|
| läuft weiter | ja | nein |
| Fehler werden behoben | ja | — |
| neue Funktionen | **nein** | — |
| Begriffe in der Oberfläche | folgen dem adaptiven Weg | — |

Eingefroren sind:

| Datei | SHA-256 |
|---|---|
| `app/teaching.py` | `801e5c47f881981cb8f269f8fbe9e5b0ae865eaf60a3e97a77c5dade361bbebb` |
| `app/quizzes.py` | `00394403e4c45255510c077d084fd181ce778054bd7b5f5d861274985d84987f` |

`tests/test_lernregeln.py::test_z6_der_klassische_weg_ist_eingefroren`
vergleicht diese Zahlen mit dem Stand im Baum. Eine Änderung an einer der
beiden Dateien lässt den Test rot werden — das ist der Zweck. Wer einen
Fehler behebt, trägt die neue Zahl hier ein und schreibt in der Zeile
darunter, warum. So ist jede Änderung am klassischen Weg eine Entscheidung
und kein Nebenbei.

Änderungsprotokoll:

- `teaching.py` (2026): `MAX_WUNSCH_LAENGE` zeigt auf
  `config.ops().formular_wunsch_zeichen` statt des Literals 500 — reine
  Konfigurations-Zentralisierung, gleicher Wert, kein Verhalten geändert.

Mit den beiden Dateien hängen zusammen, ohne selbst eingefroren zu sein:
`app/routers/lernzyklus.py` (Einstieg), `app/services/learning_content.py`
(Freigabe), `app/services/workflow.py` (Lernrunden). Sie bedienen auch
anderes und dürfen sich weiter ändern.

## Warum nicht einfach abschalten

Der klassische Weg kann etwas, das der adaptive heute noch nicht kann: er
arbeitet mit **dem Schulblatt dieser Familie**, auch wenn es zum Thema keine
geprüfte Lektion im Katalog gibt. Der adaptive Weg braucht eine Lektion aus
dem Lehrplan-Dienst. Solange der Katalog Lücken hat, wäre Abschalten eine
Lücke im Alltag des Kindes.

## Woran die Ablösung fertig ist

1. Zu jedem Thema, das eine Familie real aufschlägt, findet
   `lektionen.fuer_thema()` eine geprüfte Lektion — oder der Dienst
   erzeugt sie rechtzeitig (`adaptiv/erzeugung.py`).
2. Der Fortschritt steht nur noch in `lern_fortschritt`; `topic_flag` wird
   daraus abgeleitet statt getrennt gerechnet (Z6).
3. Dann: Routen des klassischen Wegs entfernen, `teaching.py` und
   `quizzes.py` löschen, `topic_flag` migrieren.

Vorher nicht. Ein halb abgeschalteter Weg ist schlimmer als zwei ganze.

## Die Begriffe (Z7)

Drei Maßstäbe trugen dasselbe Wort und dieselbe Farbe. Jetzt heißt jedes
Ding anders:

| gemeint ist | Wort | Farbe |
|---|---|---|
| die erste Abfrage, bevor gelernt wird (klassisch *und* vor der Klassenarbeit) | **Ersteinschätzung** | — |
| eine einzelne Fehlvorstellung ist überwunden (adaptiv, `MASTERED`) | **verstanden** | — |
| ein ganzes Thema ist belegt sicher (`topic_flag = gruen`, und seit
Schritt 4a: die Wiederholung bestanden) | **Thema sicher** | grün |

**Grün gibt es nur für „Thema sicher".** Eine verstandene Fehlvorstellung
ist kein grünes Thema: sie ist ein Schritt dorthin. Zwei richtige Antworten
zu *einem* Denkfehler sind etwas anderes als zwei fehlerfreie Übungstage zum
*Thema* — und genau diese Verwechslung hat die Oberfläche vorher nahegelegt.

Die beiden Fortschrittsbegriffe bleiben getrennt (Z6: *festschreiben statt
zusammenführen*). Zusammenführen hieße, aus zwei verschieden gemessenen
Zahlen eine zu rechnen, die keine von beiden ist. Stattdessen stehen beide
da, jede unter ihrem Namen.
