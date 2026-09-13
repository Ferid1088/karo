# Karo – Zielarchitektur, Rollenmodell und Refactoring-Plan

## Ziel

Die App soll funktional klar, sicher, wartbar und erweiterbar werden.

Die wichtigste fachliche Vorgabe lautet:

- **Eltern** sind die dominante Rolle.
- **Eltern dürfen auf alle Bereiche zugreifen**, auch auf den Kind-Bereich.
- **Kinder dürfen ausschließlich ihren eigenen Lernbereich verwenden**.
- Die Trennung muss **serverseitig erzwungen** werden und darf nicht nur über versteckte Menüpunkte oder andere Templates erfolgen.

---

# 1. Aktueller Zustand

Im aktuellen Branch `kind_eltern` existiert bereits eine klare Trennung der Oberflächen in Bereiche wie:

- Auth / Setup
- Dashboard
- Eltern
- Kind
- Lernzyklus
- Admin
- Quiz
- Klassenarbeit
- Wissen
- Themen
- Recherche
- Lernstand

Es gibt außerdem zwei zusätzliche Router:

- `vorbereitung.py`
- `messung.py`

Diese beiden Router sind aktuell **nicht in `main.py` registriert** und deshalb nicht erreichbar.

Der bestehende Code enthält bereits viele funktionierende Komponenten und umfangreiche End-to-End-Tests. Das bedeutet: Die App soll nicht komplett neu gebaut werden. Stattdessen sollte die bestehende Logik kontrolliert konsolidiert werden.

---

# 2. Kritischster Punkt: echte Rollen fehlen

Derzeit unterscheidet die App im Kern nur zwischen:

```text
nicht eingeloggt
eingeloggt
```

Nach erfolgreichem Login wird im Wesentlichen nur Folgendes gesetzt:

```python
request.session["auth"] = True
```

Eine echte Rolle wie

```python
request.session["role"] = "parent"
```

oder

```python
request.session["role"] = "child"
```

existiert aktuell nicht.

Damit sind Eltern- und Kind-Bereich zwar optisch bzw. strukturell getrennt, aber noch nicht wirklich autorisiert.

## Zielmodell

```text
ELTERN
├── Eltern-Dashboard
├── Vorbereitung
├── Messung
├── Wissen
├── Themen
├── Recherche
├── Klassenarbeiten
├── Einstellungen
├── Admin
└── vollständiger Zugriff auf Kind-Bereich

KIND
├── Kind-Dashboard / Heute
├── Lernzyklus
├── Lernen
├── Quiz
└── eigenes Lernmaterial
```

Das Kind darf insbesondere **nicht** auf folgende Bereiche zugreifen:

```text
/setup
/wissen
/themen
/recherche
/lernstand
/admin
/eltern
/vorbereitung
/messung
```

## Wichtig

Es reicht nicht, diese Links im Kind-Menü auszublenden.

Ein Kind, das manuell folgende URL eingibt:

```text
/setup
```

muss serverseitig geblockt werden.

Ebenso:

```text
/admin
/wissen
/vorbereitung
```

Die Rollenlogik gehört daher zentral in Middleware, Dependencies oder eine gemeinsame Autorisierungsschicht.

---

# 3. Empfohlenes Rollenmodell

Minimal:

```python
role = "parent"
role = "child"
```

In der Session:

```python
request.session["auth"] = True
request.session["role"] = "parent"
```

oder:

```python
request.session["auth"] = True
request.session["role"] = "child"
```

Später sinnvoll:

```python
request.session["child_id"] = 123
```

oder bei Eltern:

```python
request.session["active_child_id"] = 123
```

Damit kann die App später mehrere Kinder sauber unterstützen.

## Grundregel

```text
parent -> allow all
child  -> allow only child-safe routes
```

Ein mögliches Konzept:

```python
CHILD_ALLOWED_PREFIXES = (
    "/",
    "/lernen",
    "/lernzyklus",
    "/quiz",
    "/material",
)
```

Besser als eine globale Blacklist ist eine **Allowlist** für Kinder.

---

# 4. Rollenprüfung serverseitig

Empfohlene zentrale Funktionen:

```python
def current_role(request: Request) -> str | None:
    return request.session.get("role")
```

```python
def require_parent(request: Request):
    if request.session.get("role") != "parent":
        raise HTTPException(status_code=403)
```

```python
def require_child_or_parent(request: Request):
    if request.session.get("role") not in {"parent", "child"}:
        raise HTTPException(status_code=403)
```

Noch besser: FastAPI Dependencies.

Beispiel:

```python
def parent_only(request: Request):
    if request.session.get("role") != "parent":
        raise HTTPException(status_code=403)
```

Dann:

```python
@router.get("/wissen", dependencies=[Depends(parent_only)])
def wissen(...):
    ...
```

Für ganze Router kann man sogar zentral absichern.

---

# 5. Inhalt von `vorbereitung.py`

`vorbereitung.py` ist kein zufälliger Dead Code.

Die Datei ist erkennbar ein begonnener Architektur-Umbau, der mehrere bestehende Elternfunktionen unter einem fachlich sinnvollen Bereich zusammenführen soll.

Die Datei definiert:

```text
/vorbereitung
```

## 5.1 Schulmaterial

Routen:

```text
GET  /vorbereitung
GET  /vorbereitung/
POST /vorbereitung/schulmaterial/einlesen
POST /vorbereitung/schulmaterial/hochladen
GET  /vorbereitung/schulmaterial/{doc_id}
```

Funktional beinhaltet dieser Bereich:

- bestehendes Schulmaterial anzeigen
- Dokumente aus einem Drive-Ordner einlesen
- Material direkt hochladen
- KB-Extraktion starten
- Dokumentdetails anzeigen
- Abschnitte des Dokuments darstellen

Das entspricht weitgehend dem jetzigen Bereich:

```text
/wissen
```

---

## 5.2 Inhalte / Themen genehmigen

Routen:

```text
GET  /vorbereitung/inhalte
POST /vorbereitung/inhalte/entscheiden
POST /vorbereitung/inhalte/neu
```

Funktional:

- vorgeschlagene Themen anzeigen
- Themen akzeptieren
- Themen ablehnen
- Themen umbenennen
- neue Themen manuell anlegen
- aktive Themen anzeigen
- Verlauf und Lernstatus einblenden

Das entspricht im Wesentlichen:

```text
/themen
```

---

## 5.3 Recherche / Quellen

Routen:

```text
GET  /vorbereitung/inhalte/sources
POST /vorbereitung/inhalte/sources/entscheiden
```

Funktional:

- Recherchetreffer anzeigen
- zugelassene Quellen anzeigen
- Quellen freigeben
- Quellen ablehnen
- Recherchekonfiguration berücksichtigen

Das entspricht Teilen von:

```text
/recherche
```

---

# 6. Bewertung von `vorbereitung.py`

Die fachliche Struktur ist sinnvoller als die derzeitige Verteilung.

Heute existieren mehrere einzelne Elternbereiche:

```text
/wissen
/themen
/recherche
```

Die neue Zielstruktur wäre:

```text
/vorbereitung
├── Schulmaterial
├── Themen / Inhalte
└── Recherche / Quellen
```

Das ist aus Prozesssicht klarer.

Die Eltern beantworten damit die Frage:

> Was soll das Kind lernen, auf welcher Materialbasis und mit welchen zugelassenen Quellen?

Das ist fachlich genau ein Bereich: **Vorbereitung**.

---

# 7. Inhalt von `messung.py`

Auch `messung.py` ist ein begonnener konsolidierter Elternbereich.

Prefix:

```text
/messung
```

Der Router verbindet:

- Lernfortschritt
- Export
- Klassenarbeiten / Prüfungen
- Prognosen
- tatsächliche Ergebnisse
- Kalibrierung der Prognosen

---

## 7.1 Fortschritt

Routen:

```text
GET  /messung
GET  /messung/
GET  /messung/fortschritt
POST /messung/export
```

Funktional:

- Lernstand anzeigen
- bisherigen Verlauf anzeigen
- Regelparameter anzeigen
- Export nach Excel / Tabelle
- Drive-Verfügbarkeit prüfen

Das entspricht weitgehend:

```text
/lernstand
```

---

## 7.2 Klassenarbeiten / Examen

Routen:

```text
GET  /messung/examen
POST /messung/examen/neu
POST /messung/examen/{exam_id}/ergebnis
```

Funktional:

- Klassenarbeit anlegen
- Datum speichern
- Themen speichern
- aktuellen Lernstand als Prognose einfrieren
- später tatsächliche Ergebnisse erfassen
- Prognose mit Realität vergleichen

Beispiel:

```text
Vor der Klassenarbeit

Brüche          -> grün
Prozentrechnung -> gelb
Gleichungen     -> rot
```

Später:

```text
                 Prognose   Tatsächlich

Brüche             grün        grün
Prozentrechnung    gelb        rot
Gleichungen        rot         rot
```

Dann berechnet `_kalibrierung()` die Prognosequalität.

Beispiel:

```text
2 von 3 Prognosen korrekt
Quote = 0.67
```

Das ist funktional sehr wertvoll.

Es beantwortet langfristig die Frage:

> Wie gut sagt Karos Lernstandsmodell die tatsächliche Leistung des Kindes voraus?

---

# 8. Bewertung von `messung.py`

Auch dieser neue Bereich ist fachlich sinnvoller.

Statt:

```text
/lernstand
/klassenarbeit
```

kann die App langfristig bekommen:

```text
/messung
├── Fortschritt
└── Klassenarbeiten
```

Damit werden zwei zusammengehörende Prozesse konsolidiert:

- aktueller Lernstand
- externe Validierung durch echte Schulleistung

---

# 9. Empfohlene Zielarchitektur der App

Die App sollte langfristig ungefähr so aufgebaut sein:

```text
KARO

AUTH
├── Login
├── Logout
└── Setup

ELTERN
├── Dashboard
├── Vorbereitung
│   ├── Schulmaterial
│   ├── Themen
│   └── Recherche
├── Messung
│   ├── Lernstand
│   └── Klassenarbeiten
├── Einstellungen
├── Admin
└── Kind-Bereich ansehen

KIND
├── Heute
├── Lernzyklus
├── Lernen
├── Quiz
└── Lernmaterial
```

---

# 10. Wichtiges Architekturproblem: Router rufen Router auf

Aktuell delegiert `lernzyklus.py` direkt an Funktionen aus `kind.py`.

Beispiele:

```python
return kind.lernen_seite(...)
```

```python
return kind.quiz_seite(...)
```

```python
return await kind.quiz_antworten(...)
```

```python
return await kind.quiz_freigabe(...)
```

Das funktioniert technisch, ist aber keine saubere Architektur.

## Warum?

Ein Router sollte HTTP behandeln:

```text
Request
Form
Response
Redirect
Statuscode
```

Business-Logik sollte dagegen unabhängig davon sein.

Aktuell passiert eher:

```text
Router A
   ↓
Router B
   ↓
Business Logic
```

Besser:

```text
Router A ─┐
          ├──> Workflow Service
Router B ─┘
              ↓
         Domain Logic
              ↓
             DB
```

---

# 11. Empfohlene Service-Schicht

Beispiel:

```text
services/
├── learning_service.py
├── quiz_service.py
├── parent_service.py
├── exam_service.py
└── workflow_service.py
```

Dann:

```python
result = learning_service.get_lesson(...)
```

statt:

```python
kind.lernen_seite(...)
```

Damit können mehrere URLs dieselbe Logik nutzen, ohne Router gegenseitig aufzurufen.

---

# 12. `/lernzyklus/*` vereinfachen

Aktuell existieren zwei URL-Familien:

```text
/lernen/*
/lernzyklus/*
```

Viele davon führen funktional in denselben Code.

Das erzeugt unnötige Komplexität.

Langfristig sollte entschieden werden:

## Variante A – `/lernzyklus` wird die primäre API

Dann werden alte Routen wie:

```text
/lernen/{id}
```

nach:

```text
/lernzyklus/{topic_id}
```

weitergeleitet.

## Variante B – `/lernen` bleibt technisch primär

Dann ist `/lernzyklus` nur ein sauberer Einstieg / Alias.

Wichtig ist:

Nicht zwei gleichwertige Workflow-Systeme dauerhaft parallel pflegen.

---

# 13. Quiz als State Machine

Der Quiz-Knoten ist aktuell die stärkste Kreuzung der App.

Ein Quiz kann aus unterschiedlichen Kontexten gestartet werden:

- Themenprüfung
- Lernrunde
- Klassenarbeitsmaterial
- Lernzyklus

Nach Freigabe gibt es mehrere mögliche Ziele:

```text
/lernen/{lesson_id}
/lernzyklus/{topic_id}
/klassenarbeit/material/{material_id}
```

Die Entscheidung hängt aktuell von mehreren Datenpunkten ab.

Das ist korrekt möglich, aber schwer wartbar.

## Empfohlener Zustand

```text
CREATED
   ↓
GENERATING
   ↓
READY
   ↓
ANSWERED
   ↓
EVALUATED
   ↓
RELEASED
```

Optional:

```text
CANCELLED
FAILED
```

Jeder Übergang sollte explizit definiert sein.

---

# 14. Navigation nach Quiz-Freigabe auslagern

Aktuell entscheidet `quiz_freigabe()` gleichzeitig:

- Bewertung speichern
- Folgeprozess auslösen
- Lernrunde fortsetzen
- Klassenarbeitskontext erkennen
- Redirect-Ziel bestimmen

Das ist zu viel Verantwortung.

Besser:

```python
result = quiz_service.release(...)
next_action = workflow_service.after_quiz_release(result)
```

Beispiel:

```python
NextAction(
    kind="lesson",
    url="/lernen/17",
    reason="Quiz gehörte zu aktiver Lernrunde"
)
```

Oder:

```python
NextAction(
    kind="exam_material",
    url="/klassenarbeit/material/8",
    reason="Quiz stammt aus Klassenarbeitsmaterial"
)
```

Der Router macht anschließend nur:

```python
return redirect(next_action.url)
```

---

# 15. „Heute“ als zentraler Workflow-Orchestrator

Eine Lern-App braucht einen klaren nächsten Schritt.

Statt an vielen Stellen unterschiedliche Logik zu verwenden, sollte es genau eine Funktion geben:

```python
get_next_action(child_id)
```

Rückgabe:

```python
NextAction(
    kind="quiz",
    id=42,
    url="/quiz/42",
    reason="Offenes Quiz hat Priorität"
)
```

Eine mögliche Priorität:

```text
1. offene Freigabe / Review
2. offenes Quiz
3. aktive Lernrunde
4. Klassenarbeitsmaterial
5. neues relevantes Thema
6. kein offener Schritt
```

Damit ist „Heute“ deterministisch.

---

# 16. Parent-dominantes Rollenmodell

Da Eltern alle Kinderfunktionen verwenden dürfen, ist das Berechtigungsmodell hier relativ einfach.

## Eltern

```text
ALLOW ALL
```

## Kind

```text
ALLOW ONLY:
- Dashboard Kind
- Heute
- Lernzyklus
- Lernen
- Quiz
- Material
```

Das ist einfacher als komplexes RBAC.

Trotzdem sollte die Implementierung so gestaltet sein, dass später weitere Rollen möglich wären.

Beispiel:

```text
parent
child
teacher
admin
```

müssten später ergänzbar sein.

---

# 17. Migration von alten zu neuen Eltern-Routen

Nicht alles sofort löschen.

Empfohlen:

## Phase 1

Neue Router aktivieren:

```python
app.include_router(vorbereitung.router)
app.include_router(messung.router)
```

## Phase 2

Neue Oberfläche testen.

## Phase 3

Alte URLs vorübergehend weiterleiten:

```text
/wissen     -> /vorbereitung
/themen     -> /vorbereitung/inhalte
/recherche  -> /vorbereitung/inhalte/sources
/lernstand  -> /messung/fortschritt
```

## Phase 4

Wenn Tests stabil sind:

- alten doppelten Code entfernen
- alte Templates entfernen
- Redirect-Kompatibilität ggf. behalten

---

# 18. Tests als Sicherheitsnetz

Die bestehende Testbasis ist wertvoll und sollte vor dem Umbau erweitert werden.

## P0 – Rollen

Tests:

```text
parent can access /eltern
parent can access /lernen
parent can access /quiz
parent can access /admin

child can access /lernen
child can access /quiz

child cannot access /eltern
child cannot access /wissen
child cannot access /themen
child cannot access /setup
child cannot access /admin
child cannot access /vorbereitung
child cannot access /messung
```

---

# 19. Tests für Workflow-Zustände

Zusätzlich:

```text
Quiz doppelt absenden
Quiz doppelt freigeben
Browser Back nach Freigabe
veraltete Session
direkter Aufruf eines fremden Quiz
ungültige quiz_id
ungültige lesson_id
falsche topic_id + quiz_id Kombination
```

---

# 20. Idempotenz

Besonders kritische Operationen sollten idempotent sein.

Beispiel:

```text
POST /quiz/{id}/freigabe
```

Wenn derselbe Request zweimal gesendet wird, darf nicht zweimal:

- Bewertung geschrieben werden
- Export ausgelöst werden
- Lernstatus verändert werden
- nächste Runde erzeugt werden

Der Code berücksichtigt bereits teilweise den Fall:

```text
bereits freigegeben
```

Dieser Schutz sollte systematisch für alle kritischen Übergänge gelten.

---

# 21. Transaktionen

Kritische Zustandsänderungen gehören in eine DB-Transaktion.

Beispiel Quiz-Freigabe:

```text
Bewertungen schreiben
Quiz-Status ändern
Lernfortschritt aktualisieren
Workflow-Kontext aktualisieren
```

Diese Änderungen sollten entweder vollständig erfolgreich sein oder vollständig zurückgerollt werden.

---

# 22. Trennung zwischen HTTP und Domain

Ziel:

```text
HTTP Layer
    ↓
Authorization
    ↓
Application / Workflow Services
    ↓
Domain Logic
    ↓
Repositories / Database
```

Nicht:

```text
Router
↓
Router
↓
SQL
↓
Redirect
```

---

# 23. Empfohlene Projektstruktur

Langfristig könnte die Struktur ungefähr so aussehen:

```text
app/
├── main.py
├── auth/
│   ├── roles.py
│   ├── permissions.py
│   └── session.py
│
├── routers/
│   ├── auth.py
│   ├── parent.py
│   ├── child.py
│   ├── preparation.py
│   ├── measurement.py
│   └── admin.py
│
├── services/
│   ├── workflow.py
│   ├── learning.py
│   ├── quiz.py
│   ├── preparation.py
│   └── measurement.py
│
├── domain/
│   ├── learning.py
│   ├── quiz.py
│   ├── exam.py
│   └── roles.py
│
└── db/
```

Die bestehende Struktur muss nicht sofort vollständig dahin migriert werden.

Das ist ein Zielbild.

---

# 24. Konkrete Umsetzung in sinnvoller Reihenfolge

## Phase 1 – Rollen und Sicherheit

Priorität: **P0**

Umsetzen:

```text
role in Session
parent / child login
serverseitige Route-Guards
Kind-Allowlist
403 oder sicherer Redirect
Tests
```

Erst wenn das funktioniert, weiter.

---

## Phase 2 – Elternarchitektur konsolidieren

Aktivieren:

```text
/vorbereitung
/messung
```

`vorbereitung.py` soll langfristig übernehmen:

```text
/wissen
/themen
/recherche
```

`messung.py` soll langfristig übernehmen:

```text
/lernstand
/klassenarbeit
```

---

## Phase 3 – Workflow-Service

Business-Logik aus Router-Funktionen herausziehen.

Zuerst:

```text
Quiz
Lernen
Lernzyklus
```

Danach:

```text
Klassenarbeit
Messung
```

---

## Phase 4 – Quiz-State-Machine

Explizite Zustände definieren.

Explizite erlaubte Übergänge definieren.

Redirect-Entscheidung aus dem Router herausziehen.

---

## Phase 5 – „Heute“

Eine einzige zentrale:

```python
get_next_action()
```

Logik.

Alle Dashboards sollen diese Funktion verwenden.

---

## Phase 6 – Legacy-Routen abbauen

Nach erfolgreich bestandenen Tests:

```text
/wissen
/themen
/recherche
/lernstand
```

auf neue Bereiche redirecten.

Doppelten Code entfernen.

---

## Phase 7 – Cleanup

Danach:

- tote Funktionen entfernen
- doppelte Templates entfernen
- Imports bereinigen
- dynamische `__import__` Stellen reduzieren
- konsistente Namensgebung
- Router kleiner machen
- Logging verbessern
- Typen ergänzen
- Docstrings vereinheitlichen

---

# 25. Priorisierung

## P0 – sofort

```text
echte Rollen
Kind serverseitig einschränken
Elternzugriff vollständig erlauben
Autorisierung testen
```

## P1 – sehr wichtig

```text
vorbereitung.py aktivieren
messung.py aktivieren
Quiz-Workflow entkoppeln
```

## P2 – Architektur

```text
Router-to-Router Calls entfernen
Workflow Service einführen
Heute-Orchestrator einführen
```

## P3 – Qualität

```text
Cleanup
Legacy Redirects
Typisierung
Logging
Dokumentation
UI-Verbesserungen
```

---

# 26. Zielbild des Prozesses

## Elternprozess

```text
Eltern Login
    ↓
Eltern Dashboard
    ↓
Vorbereitung
    ├── Schulmaterial
    ├── Themen
    └── Recherche
    ↓
Kind lernt
    ↓
Messung
    ├── Lernstand
    └── Klassenarbeit
    ↓
neue Vorbereitung
```

Das ist ein sauberer Lernregelkreis:

```text
VORBEREITEN
    ↓
LERNEN
    ↓
MESSEN
    ↓
ANPASSEN
    ↓
VORBEREITEN
```

---

# 27. Zielbild des Kindprozesses

```text
Kind Login
    ↓
Heute
    ↓
nächster sinnvoller Schritt
    ↓
Lerninhalt
    ↓
Quiz
    ↓
Feedback
    ↓
nächster Lernschritt
```

Das Kind soll möglichst wenig administrative Entscheidungen sehen.

Die App soll dem Kind beantworten:

> Was soll ich jetzt machen?

Nicht:

> In welchem technischen Modul befinde ich mich?

---

# 28. Prozessprinzipien

Die App sollte langfristig folgende Eigenschaften haben:

### Ein Prozess – eine Wahrheit

Es darf nicht mehrere verschiedene Implementierungen derselben Entscheidung geben.

### Eine Zustandsentscheidung – eine zentrale Funktion

Beispiel:

```text
Was kommt nach dem Quiz?
```

Diese Entscheidung darf nicht an drei verschiedenen Stellen unabhängig implementiert sein.

### Eltern kontrollieren, Kind konsumiert

Eltern:

```text
konfigurieren
freigeben
überwachen
messen
```

Kind:

```text
lernen
antworten
wiederholen
```

### Kein versteckter Zugriff

Berechtigungen werden nicht über UI versteckt, sondern serverseitig erzwungen.

### Kein Router als Service

Router koordinieren HTTP, Services koordinieren Fachlogik.

---

# 29. Mein empfohlener erster Coding-Schritt

Nicht mit `vorbereitung.py` beginnen.

Nicht mit UI beginnen.

Nicht zuerst alte Routen löschen.

Der erste konkrete Umbau sollte sein:

```text
AUTHORIZATION LAYER
```

Implementieren:

```text
role = parent / child
Session-Rolle
parent guard
child guard
child allowlist
Tests
```

Danach:

```text
vorbereitung.py
messung.py
```

aktivieren und fachlich sauber integrieren.

Danach:

```text
lernzyklus
quiz
heute
```

refactoren.

---

# 30. Kurzfassung

Die beste Zielstruktur ist:

```text
ELTERN
├── Vorbereitung
├── Messung
├── Einstellungen
├── Administration
└── voller Zugriff auf Kind

KIND
├── Heute
├── Lernen
├── Quiz
└── Material
```

Technisch:

```text
Request
   ↓
Authentication
   ↓
Authorization
   ↓
Workflow Service
   ↓
Domain Logic
   ↓
Database / Jobs / LLM
```

Und nicht:

```text
Router A
   ↓
Router B
   ↓
SQL
   ↓
Redirect
```

---

# 31. Endziel

Nach dem Refactoring soll Karo:

- klare Eltern-/Kind-Rollen haben
- Eltern vollständigen Zugriff geben
- Kinder sicher auf ihren Bereich beschränken
- keine doppelten Workflow-Implementierungen besitzen
- einen zentralen Lernzyklus haben
- Quiz-Zustände explizit verwalten
- „Heute“ deterministisch entscheiden lassen
- Vorbereitung, Lernen und Messung als klaren Regelkreis abbilden
- durch End-to-End-Tests abgesichert sein
- leichter wartbar und später auf mehrere Kinder erweiterbar sein

Das ist die Architektur, auf der die weitere Entwicklung aufgebaut werden sollte.
