# Der Lernkreislauf — IST-Stand

Was Karo heute wirklich tut, wenn ein Kind ein Thema lernt. Kein Entwurf und
kein Ziel: wo der Code etwas anderes macht als die Absicht, steht das als
Abweichung dabei, und am Ende in der Liste **Zur Entscheidung**.

Es gibt **zwei Kreisläufe** nebeneinander. Das zu wissen ist die halbe Miete,
denn sie messen verschieden, zählen verschieden und hören verschieden auf:

| | **Adaptiver Weg** | **Klassischer Weg** |
|---|---|---|
| Einheit | eine Fehlvorstellung | ein Thema |
| Datei | `app/adaptiv/` | `app/teaching.py`, `app/quizzes.py` |
| Material | geprüfter Katalog (Lehrplan-Dienst) | Schulblätter + Modell |
| Fortschritt | `lern_fortschritt` je Konzept/Fehlertyp | `topic_flag` je Thema |
| Abbruch | nach 3 erfolglosen Runden → `ESCALATED` | nach `max_lernrunden` → `abgebrochen` |
| Modellaufrufe im Ablauf | **keine** | Fragen schreiben, Material erzeugen |

Der adaptive Weg ist der neuere und der engere. Der klassische trägt heute
noch den Alltag. Beide enden bei einem Menschen, wenn es nicht reicht.

---

## 1. Thema erkannt

**Eingang:** ein Themenname — eingetippt, von einem Schulblatt abgetippt
(seit Schritt 1b) oder vom Browser gelesen (Schritt 2); dazu immer ein Fach
aus dem Reiter, in dem die Familie gerade ist.

**Entscheidungsregel:** Wortabgleich, kein Modell.
`lektionen.fuer_thema()` normalisiert den Text
(`karo_contract.normalisierung.normalisiere_thema`: Kleinschreibung,
Umlaute ausgeschrieben, nur Buchstaben und Ziffern) und vergleicht ihn mit
den Stichworten und der Bezeichnung jeder verfassten Lektion desselben Fachs
(`karo_contract.huelle.trifft_thema`: Teilzeichenkette in beide Richtungen).
Mehrere Treffer → `lektionen.empfehlungen()` sortiert nach Anzahl gemeinsamer
Sinnwörter, höchstens drei. Kein Treffer → **kein Vorschlag**, und das wird
gesagt. Für Blatt-Text macht `blatt_text.vorschlaege()` dasselbe gegen den
Themenkatalog, gewichtet nach Anteil des getroffenen Themas.

**Was es nicht gibt:** eine Rangfolge nach Voraussetzungen. Der Docstring in
`lektionen.empfehlungen()` sagt das selbst: „eine echte Voraussetzungskette
gehört in den Katalog und nicht in eine Heuristik".

**Ausgang:** ein `konzept_id` (adaptiv) oder ein `topic` (klassisch) — oder
die ehrliche Auskunft, dass es dazu nichts gibt.

**Zuständig:** `app/adaptiv/lektionen.py:fuer_thema/empfehlungen`,
`app/blatt_text.py:vorschlaege`, `app/topics.py:aus_blatt`.

---

## 2. Einstufung

Es gibt **zwei** Einstufungen, und sie haben nichts miteinander zu tun.

### 2a. Vor einer Klassenarbeit (`exam_placement.py`)

**Eingang:** die Themen einer angelegten Klassenarbeit.

**Entscheidungsregel:** je Thema **zwei** geprüfte Aufgaben
(`AUFGABEN_JE_THEMA = 2`) aus dem Katalog. Bewertet wird mit
`unterricht.ist_richtig()` (6/8 = 3/4). Dann:

| Treffer | Flagge |
|---|---|
| 2 von 2 | grün |
| 1 von 2 | gelb |
| 0 von 2 | rot |
| nur 1 Aufgabe vorhanden, richtig | **gelb**, nie grün |

Der letzte Fall ist Absicht: „Eine einzige Aufgabe belegt keine Sicherheit,
nur einen Anfang."

**Ausgang:** `exam_placement.ergebnis()` → Flagge je Thema. Das ist die
belastbarste Quelle, die Karo hat, weil sie aus geprüften Aufgaben kommt.

### 2b. Im laufenden Betrieb (`domain.compute_flag`)

**Eingang:** alle gespeicherten Antworten zu einem Thema (`answer_log`).

**Entscheidungsregel**, in dieser Reihenfolge — die Reihenfolge ist der Inhalt:

1. weniger als `min_evidenz` (2) verwertbare Antworten → **weiß**
   („ehrlicher als eine Vermutung")
2. mindestens `rot_konzeptfehler` (2) Verständnisfehler in den letzten
   `fenster` (5) Antworten → **rot**
3. die letzten `gruen_tage` (2) Übungstage vollständig fehlerfrei **und**
   insgesamt `gruen_richtige` (3) richtige → **grün**
4. sonst → **gelb**

Grün wird in **Tagen** gerechnet, nicht in Zeilen: ein Arbeitsblatt liefert
fünf bis zehn Antworten am selben Tag, eine zeilenbasierte Regel wäre nie
erreichbar. „Nicht bearbeitet" zählt gar nicht als Evidenz. Als
Verständnisfehler gelten nur `konzeptfehler` und `regel_vergessen` —
ein Rechenfehler oder Flüchtigkeit führen nie zu Rot.

**Ausgang:** `topic_flag`. Rot und Gelb lösen eine Lerneinheit aus
(`NEEDS_TEACHING`), Grün und Weiß nicht.

**Zuständig:** `app/services/exam_placement.py:abgeben/ergebnis`,
`app/domain.py:compute_flag`, Schwellen in `domain.Rule` und den Einstellungen.

---

## 3. Lernplan

**Eingang:** Themen einer Klassenarbeit, ihre Flaggen aus 2a/2b, das
Prüfungsdatum und die Lerntage, die das Kind selbst im Kalender gewählt hat.

**Entscheidungsregel:** erst der Bedarf, dann die Verteilung.

Der Bedarf je Thema kommt aus einer Tabelle, nicht aus einem Modell
(`exam_effort.MINUTEN`):

| Flagge | Minuten |
|---|---|
| rot | 20–28 |
| weiß | 16–22 |
| gelb | 10–15 |
| grün | 4–6 |

Weiß liegt **zwischen** rot und gelb — „noch nie geübt" ist nicht dasselbe
wie „Lücke", aber teurer als „wackelig". Dazu ein stiller Zuschlag von 20 %
(`ZUSCHLAG = 1.2`), gerundet auf 5 Minuten (`STUFE`).

Verteilt wird der Reihe nach (`exam_effort.verteilung()`): sichere Themen
fallen raus, der Rest wird in der angekündigten Reihenfolge auf die gewählten
Tage gelegt, ein Thema darf über mehrere Tage laufen. Reicht die Zeit nicht,
bleibt der Rest **unverteilt und sichtbar** — der Kalender sagt es, statt
heimlich zu kürzen.

**Was nicht passiert:** keine Umsortierung nach Schwierigkeit, keine
Wiederholung mit Abstand, keine Rücksicht auf Voraussetzungen. Die
angekündigte Reihenfolge gewinnt.

**Ausgang:** `exam_schedule_day` mit Minuten je Tag und Thema.

**Zuständig:** `app/services/exam_effort.py:themen/bedarf/verteilung/lage`,
`app/services/exam_calendar.py`.

---

## 4.–9. Die Lerneinheit selbst

Ab hier trennen sich die beiden Wege vollständig.

### Adaptiver Weg: ein Zustandsautomat

`app/adaptiv/sitzung.py` führt zwei Ebenen: einen **Zustand** und, innerhalb
von `TEACHING`, eine **Phase**. Jeder Übergang ist aufgezählt; was nicht in
der Tabelle steht, wirft `UebergangVerboten`. Der Zustand liegt in der
Datenbank, nicht in der Cookie-Sitzung — eine Sitzung übersteht ein
Neu-Login.

```
INPUT_RECEIVED → MATERIAL_ANALYZED → DIAGNOSING ─┬→ ERROR_IDENTIFIED → TEACHING ─┬→ MASTERED
                                                  ├→ MASTERED                     ├→ DIAGNOSING
                                                  └→ ESCALATED                    └→ ESCALATED

TEACHING-Phasen:
HOOK → RULE → WORKED_EXAMPLE → GUIDED_TASK ⇄ ADAPTATION
                                     ↓
                               INDEPENDENT_TASK ⇄ ADAPTATION
                                     ↓
                                 COMPLETE
```

#### 4. Diagnose (`DIAGNOSING`)

**Eingang:** das Konzept.

**Ablauf:** erst der **Anker** (`SCHRITT_ANKER`) — eine Frage, die Vorwissen
weckt und **nicht benotet** wird. Dann die erste Diagnoseaufgabe.

**Entscheidungsregel** (`unterricht.diagnose_beantwortet`):

- leere Antwort oder Text, wo eine Zahl hingehört → Hinweis, kein Versuch
  verbraucht
- **richtig** → Erfolg gebucht, aber **keine Beherrschung**: eine zweite,
  andere Kontrollaufgabe folgt (`bestaetigung`). Erst wenn auch die sitzt,
  ist `darf_abschliessen` wahr. Fehlt die zweite Aufgabe in der Lektion,
  wird das gesagt — nicht stillschweigend abgeschlossen.
- **falsch und im Katalog** → Fehlertyp erkannt, passende Erklärung geholt
  (nach Klassenstufe des Themas, sonst Profilklasse) → `TEACHING`/`HOOK`
- **falsch und nicht im Katalog** → es wird **keine Fehlvorstellung
  erfunden**. Hinweis, erneut versuchen; nach **3** unbekannten Antworten
  → `ESCALATED`.

**Ausgang:** ein Fehlertyp mit Erklärung — oder Beherrschung, oder Eskalation.

#### 5. Erklärung (`HOOK` → `RULE`)

**HOOK ist zweistufig und die Reihenfolge ist der Punkt:** das Kind sagt
**zuerst** voraus (`art: "vorhersage"`), was herauskommt — *bevor* es die
Erklärung sieht. Die Vorhersage wird nicht benotet. Danach wird der
Widerspruch gezeigt (`art: "haken"`), mit der eigenen Antwort daneben.

`RULE` zeigt die Regel mit ihrer Visualisierung. Weiter geht es ohne Eingabe
(`unterricht.weiter`), die Phasen folgen fest: HOOK → RULE → WORKED_EXAMPLE
→ GUIDED_TASK.

#### 6. Beispiel (`WORKED_EXAMPLE`)

Eine vorgerechnete Aufgabe aus dem Katalog. Keine Eingabe, keine Bewertung.

#### 7. Geführte Aufgabe (`GUIDED_TASK`)

**Eingang:** die Aufgabe der Rolle `gefuehrt`, **mit** Bild.

**Entscheidungsregel** (`unterricht.aufgabe_beantwortet`):

- richtig → Erfolg gebucht, Tippstufe zurück auf 0, weiter zu
  `INDEPENDENT_TASK`
- falsch, **dieselbe Fehlvorstellung** (Antwort gleich dem hinterlegten
  `typischer_fehler`) → sofort `ADAPTATION`
- falsch, andere Abweichung → Tippstufe +1, dieselbe Aufgabe noch einmal

**Tipps** sind gestuft (`unterricht.tipp`) und verraten nie die Lösung.

#### 8. Selbstständige Aufgabe (`INDEPENDENT_TASK`) und Mini-Test

**Eingang:** die Aufgabe der Rolle `selbststaendig`, **ohne** Bild.

Richtig gerechnet beendet die Phase **nicht**. Danach kommt der **Transfer**
(`art: "transfer"`): derselbe Gedanke an einer anderen Struktur, ohne
Rechnen. Das ist der Mini-Test.

- Transfer richtig → Erfolg; bei erreichter Schwelle `MASTERED`, sonst
  `COMPLETE`
- Transfer falsch → Runde zählt (`runde_gescheitert`), Hinweis, erneut
- falsch in der selbstständigen Phase → **immer** `ADAPTATION`, unabhängig
  davon, ob es dieselbe Fehlvorstellung war

#### 9. Anpassung (`ADAPTATION`)

**Eingang:** eine erfolglose Runde.

**Regel:** andere **Darstellung** derselben Erklärung
(`visualisierung_alternativ`) — „nicht derselbe Streifen noch einmal".
Danach zurück an die Stelle, an der es hakte: war es die selbstständige
Aufgabe, geht es dorthin zurück, sonst zur geführten
(`weiter_nach_adaptation`, gemerkt in `war_selbststaendig`).

**Was es nicht gibt:** einen Rücksprung zu einer Voraussetzung.

#### Abschluss, Beherrschung, Eskalation

- **Beherrschung** (`sitzung.beherrscht`): `adaptiv_mastery_treffer`, Standard
  **2**, Minimum 2 — „eine richtige Antwort ist nie Beherrschung". Erst dann
  `MASTERED` und `mastery='sicher'`.
- **Eskalation** (`sitzung.eskalieren`): nach `adaptiv_max_lehrrunden`,
  Standard **3**, erfolglosen Runden. Jede erfolglose Runde läuft zwingend
  durch `runde_gescheitert()`, und die eskaliert selbst — es gibt keinen Weg
  daran vorbei. Danach wird **keine weitere Erklärung ausgeliefert**
  (`darf_erklaeren`), und der Fehlertyp steht im Profil als
  `braucht_mensch`.
- Eskalation ist ein **normaler Ausgang**, kein Fehlerzustand.

**Zuständig:** `app/adaptiv/unterricht.py` (Ablauf und Bildschirme),
`app/adaptiv/sitzung.py` (Zustände, Zählung, Schwellen),
`app/adaptiv/katalog.py` (Fehlertyp erkennen, Erklärung holen),
`app/adaptiv/store.py` (`fortschritt_buchen`).

### Klassischer Weg: Runden mit Stufen

**Eingang:** ein Thema mit roter oder gelber Flagge.

**Ablauf je Runde** (`teaching.runde_starten` → `lesson_build` →
`quizzes` → Freigabe → `teaching.nach_freigabe`):

1. **Vorbedingung:** Ohne eigenes Material (`kb.lehrmaterial`) **und** ohne
   freigegebene Internetquelle (`research.material_fuer`) startet keine
   Runde. Die Lerneinheit bleibt auf `wartet` — kein Abbruch, der Weg
   bleibt offen. Die Meldung nennt beide Wege (Text vom Blatt, Quelle
   freigeben).
2. **Bestätigung:** Jede Runde — auch die erste — wartet auf einen Menschen
   (`naechste_runde_bestaetigen`), damit vorher entschieden werden kann, ob
   im Netz gesucht wird.
3. **Material** wird erzeugt, gegengeprüft und erst nach bestandener Prüfung
   ausgeliefert.
4. **Fragen** dazu, beantwortet am Bildschirm (seit Schritt 1 auch im
   Papiermodus: gedruckt wird weiter, getippt wird am Bildschirm).
5. **Freigabe durch einen Menschen** — nicht abschaltbar. Erst danach gehen
   die Antworten in `answer_log` und die Flagge wird neu gerechnet.

**Entscheidungsregel danach** (`teaching.nach_freigabe`):

| Lage | Folge |
|---|---|
| Flagge **grün** | `gelernt`, fertig |
| `runden >= max_runden` | `abgebrochen`, „hier hilft ein Mensch mehr als eine weitere Erklärung" |
| sonst | nächste Runde, **eine Stufe einfacher** |

**Stufen** (`domain.NEXT_STUFE`): `normal` → `einfacher`
(mehr Zwischenschritte) → `ganz_einfach` (Bilder, Alltagsbeispiele). Tiefer
geht es nicht; danach greift die Rundengrenze.

**Zuständig:** `app/teaching.py:runde_starten/nach_freigabe/abbrechen`,
`app/quizzes.py`, `app/domain.py:NEXT_STUFE`.

---

## 10. Abschluss

| Weg | Abschluss | Was gespeichert wird |
|---|---|---|
| adaptiv | `MASTERED` | `lern_fortschritt.mastery='sicher'` je Konzept+Fehlertyp |
| adaptiv | `ESCALATED` | `braucht_mensch=1`, erscheint im Elternbereich |
| klassisch | `gelernt` | `lesson.finished_at`, Flagge grün |
| klassisch | `abgebrochen` | `abbruch_grund`, für Menschen lesbar |

**Lernzeit** wird unabhängig davon gemessen (`services/learning_time.py`):
ein Schlag alle 30 s, Lücken bis 90 s gelten als dieselbe Einheit, ab 300 s
Pause beginnt eine neue, pro Einheit 60 s Gutschrift, Deckel 8 h am Tag.
Nur für die Kindrolle.

---

## Zur Entscheidung

Hier laufen Code und Absicht auseinander, oder eine Regel fehlt. **Nichts
davon habe ich angefasst.** Die Nummern sind zum Draufzeigen.

### Z1 — Es gibt keinen Mastery-Wert pro Kind und Konzept
Schritt 4 setzt einen Elo-artigen Wert voraus („Kind gegen Aufgabe,
deterministisch, erklärbar"). Den gibt es nicht. Heute: ein Zähler
(`erfolge`) gegen eine feste Schwelle (2) im adaptiven Weg, eine
Fensterregel über Antworten im klassischen. Beide kennen keine
Aufgabenschwierigkeit. **Entscheidung:** Elo einführen — oder die
Zählregeln als ausreichend erklären und Schritt 4 entsprechend kürzen?

### Z2 — „Schneller" gibt es nicht
Die Phasenfolge HOOK → RULE → WORKED_EXAMPLE → GUIDED_TASK ist fest. Ein
Kind, das die Diagnose sofort zweimal richtig löst, ist `MASTERED` und
überspringt damit alles — aber es gibt kein „überspringt die Erklärung,
bekommt schwerere Aufgaben". Schwierigkeitsstufen bei Aufgaben existieren
nicht. **Entscheidung:** Überspringen einzelner Phasen, oder reicht der
Sprung von der Diagnose direkt zu `MASTERED`?

### Z3 — Es gibt keine Voraussetzungen in Karo
Weder der adaptive noch der klassische Weg kann „zurück zur Voraussetzung".
Der Lehrplan-Dienst führt Voraussetzungsketten (`concept_prerequisites`),
Karo nutzt sie nicht. `lektionen.empfehlungen()` sagt im Docstring selbst,
dass das fehlt. **Entscheidung:** Voraussetzungen vom Dienst mitimportieren
und bei wiederholtem Scheitern dorthin zurückspringen — oder weiterhin
eskalieren und einen Menschen holen?

### Z4 — Es gibt keine Wiederholung mit Abstand
Nach `MASTERED` oder `gelernt` passiert nichts mehr. Kein Termin, keine
Auffrischung, keine Vergessenskurve. Die Flagge bleibt grün, bis zufällig
wieder geübt wird. **Entscheidung:** Wiederholungstermine einführen (wo?
eigene Tabelle, oder über den Kalender der Klassenarbeit) — oder bewusst
darauf verzichten?

### Z5 — Antwortzeit wird nirgends gemessen
Schritt 4 nennt „Antwortzeit nur schwach gewichten". Gewichtet wird sie
gar nicht; gemessen wird nur Gesamtlernzeit je Tag, nicht je Aufgabe.
**Entscheidung:** Zeit je Antwort erfassen — oder streichen?

### Z6 — Zwei Fortschrittsbegriffe nebeneinander
`lern_fortschritt` (Konzept+Fehlertyp, adaptiv) und `topic_flag` (Thema,
klassisch) wissen nichts voneinander. Ein Kind kann im adaptiven Weg eine
Fehlvorstellung sicher beherrschen, während das Thema klassisch rot bleibt —
und umgekehrt. Die Einstufung vor der Klassenarbeit (2a) ist eine **dritte**
Quelle. **Entscheidung:** zusammenführen, oder die Trennung festschreiben
und in der Oberfläche erklären?

### Z7 — „Grün" ist in den beiden Wegen etwas anderes
Adaptiv: zwei richtige Antworten zu **einer Fehlvorstellung**. Klassisch:
zwei fehlerfreie **Übungstage** und drei richtige Antworten zum **Thema**.
Einstufung: zwei von zwei Aufgaben an **einem** Tag. Drei Maßstäbe, ein
Wort, eine Farbe. **Entscheidung:** angleichen, oder die Unterschiede
benennen (z. B. verschiedene Begriffe in der Oberfläche)?

### Z8 — Die Grenze „3 unbekannte Antworten" steht im Code
`unterricht.diagnose_beantwortet` eskaliert nach drei nicht im Katalog
gefundenen Antworten. Diese 3 ist die einzige Schwelle des adaptiven Wegs,
die **nicht** konfigurierbar ist (`max_runden` und `mastery_treffer` sind
es). **Entscheidung:** in die Konfiguration, oder absichtlich fest?

### Z9 — Der Lernplan kennt die Reihenfolge der Themen nicht
`exam_effort.verteilung()` legt die Themen in der angekündigten Reihenfolge
auf die Tage. Steht „Probe durchführen" vor „Gleichungen lösen", wird in
dieser Reihenfolge gelernt. Der Kommentar in `exam_effort.py` erwähnt
Voraussetzungen, die Verteilung berücksichtigt sie nicht. **Entscheidung:**
nach Flagge sortieren (rot zuerst), nach Voraussetzungen, oder bei der
angekündigten Reihenfolge bleiben?

### Z10 — Eine Erklärung wird gemessen, aber nichts folgt daraus
`store.erklaerung_wirkte()` zählt, wenn nach einer Erklärung richtig
geantwortet wurde. Diese Zahl wird nirgends gelesen: eine Erklärung, die
nie wirkt, wird weiter ausgeliefert. **Entscheidung:** auswerten (schlechte
Erklärungen ersetzen lassen) — oder die Zählung entfernen, statt eine
Messung zu führen, die folgenlos bleibt?
