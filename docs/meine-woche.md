# Meine Woche – Pilot

## Start und Nutzung

Aus dem Repository den lokalen Quellcode bauen und starten:

```sh
make up-klein
```

Das vorhandene Compose-Mapping ist `127.0.0.1:8080:8080`.

- Kind: <http://127.0.0.1:8080/woche>, auch in der Hauptnavigation und auf „Heute“.
- Eltern: Karte auf <http://127.0.0.1:8080/eltern>, Verwaltung unter
  <http://127.0.0.1:8080/woche/eltern>.
- Anmeldung: <http://127.0.0.1:8080/login>, bestehendes Eltern- oder Kind-Passwort.
  Alternativ auf `/eltern` unter „Aussehen und Anmeldung“ den Kind-Modus starten.
  Zurück zu Eltern geht es nur über eine erneute Anmeldung mit Eltern-Passwort.

Eltern vereinbaren gemeinsam höchstens ein Ziel, eine Routine und eine Zusage.
Alle Bestandteile sind optional; ein völlig leeres Formular wird abgewiesen.
Ein Ziel ohne eingetragenen Einstieg erhält einen neutralen Anfang:
Ziel lesen und eine kleine Handlung auswählen. Es entstehen keine zusätzlichen
Lernaufgaben. Die Klassenangabe aus Karos Konfiguration steuert die Vorschläge.

Das Kind kann anfangen, einen Schritt melden, Hilfe holen, für heute ausblenden,
sich umentscheiden, eine Planänderung erbitten oder pausieren. „Wochenziel erreicht“
ist eine gesonderte, korrigierbare Selbstauskunft. Eltern sagen Hilfe zu und
markieren sie erst nach der Unterstützung als erledigt. Hilfe bleibt in Karo.

## Anschluss an den vorhandenen Stand

Untersucht am 15.09.2026: Branch `meine-woche`, Remote
`https://github.com/Ferid1088/karo.git`. Keine `AGENTS.md` im Checkout oder den
übergeordneten Verzeichnissen gefunden. Der vorhandene uncommittete Import und
die Routerregistrierung in `app/main.py` wurden beibehalten und gezielt ergänzt.
Die Dateien `main.py.vorher`, `einbau.py` und `meine-woche.patch` wurden nicht verändert.

Karo hat **eine Kind-Installation pro Datenbank**, keine Benutzer-/Kindtabelle und
keine Familienzuordnung. `config.learner_name` und `config.learner_grade` beschreiben
dieses Kind. Der feste `child_key='installation'` in den neuen Vereinbarungen bildet
diese bestehende Grenze ab; dies ist keine Mehrkind- oder Mehrfamilienlösung.
Es werden keine Kindprofile dupliziert. Mehrere Kinder benötigen getrennte Installationen.

Karos SessionMiddleware, Login, Gate und CSRF-Prüfung bleiben zuständig.
Zusätzlich prüft jede Wochenroute Anmeldung und gültige Rolle. Elternrouten haben
eine ausdrückliche Elternprüfung. Kind-IDs sind nicht auswählbar; übergebene
`child_id`/`kind_id` werden abgewiesen. Plan- und Hilfe-IDs werden gegen die lokale
Installation geprüft. Eltern können die Kindseite ansehen und pausieren, aber
keine Kind-Selbstauskunft oder Hilfeanfrage im Namen des Kindes absenden.

## Dateien und Regeln

- `app/woche/pilot.py`: zentrale Textgrenzen, Eingabeprüfung, Vorschläge, lokale
  Woche und deterministische Auswahl: Pause → offene Hilfe zur aktuellen
  Vereinbarung → heutige Routine → Ziel-Einstieg → nichts vorgesehen.
- `app/woche/pilot_store.py` und `pilot.sql`: Vereinbarung, positive Rückmeldungen,
  Hilfestatus und Versionsprüfung. SQLite-Transaktionen und Unique-Constraints
  verhindern doppelte Pläne, Erfolge und offene Hilferufe.
- `app/woche/router.py`: geschützte Formulare und Statusaktionen; gemeinsames Rendern.
- `app/templates/woche/pilot_*.html`, `app/static/woche-pilot.*`: kleine Abschnitte
  im vorhandenen Karo-Design. Navigation, Dashboard und `areas.css` sind integriert.
- `app/db.py`: Schemaanlage ausschließlich bei `db.init()`, nicht bei Seitenaufrufen.

Zeitzone: `KARO_TIMEZONE`, sonst bestehendes `TZ`, sonst `Europe/Berlin`.
Das vorhandene Compose setzt `TZ=Europe/Berlin`. Wochen laufen Montag bis Sonntag,
auch über Sommerzeitwechsel. Abgelaufene Wochen werden nicht automatisch kopiert.
„Übernehmen“ öffnet ein vorausgefülltes Formular; erst die gemeinsame Bestätigung
speichert die neue Woche. Fortschritt, Pause, Rückblick, Kind-Bestätigung und Hilfe
werden nicht kopiert. Offene frühere Hilfe bleibt für beide Seiten erreichbar.

Inhaltliche Änderungen erhöhen die Vereinbarungsrevision und setzen die
Kind-Bestätigung zurück; geänderte Ziele setzen auch die Erreicht-Meldung zurück.
Rückmeldungen/Hilfe behalten ihre ursprüngliche Revision. Neue Inhalte können
wieder ausprobiert werden. Veraltete Formulare erhalten HTTP 409 mit einem Link
zum Neuladen; eingegebene Vereinbarungstexte bleiben im Formular sichtbar.

„Heute nicht“ und der einmalige einfachere Einstieg gelten pro Aktivität, Revision,
lokalem Tag und Sitzung. Es gibt keine geräteübergreifende Ausblendung. Die kleine
signierte Sitzung speichert keine Gründe; abgelaufene Auswahl wird beim nächsten
Wochenaufruf entfernt und bei Anmeldung/Abmeldung verworfen. Schwierigkeitengründe
und der private Freitext werden nicht gespeichert. Der kleinere Einstieg bezieht
sich auf die tatsächlich vereinbarte Handlung und wird nicht rekursiv verkleinert.

Die Elternausgabe erhält keine Ausblendungen oder Schwierigkeitengründe und keine
Tages-/Uhrzeitliste positiver Rückmeldungen. Das Modul importiert keine Lernlogik,
ruft keine KI auf und schreibt weder Quizdaten noch Lernstände oder Lernzyklen.
Die optionale Verbindung zu Lernthemen wurde für diesen Pilot weggelassen.

## Migration, Sicherung und alte Daten

Die additive, wiederholbare Initialisierung legt `woche_plan`, `woche_feedback`,
`woche_help` und `woche_migration` an. Neue Tabellen haben löschbare Fremdschlüssel
mit `ON DELETE CASCADE`; es werden keine unveränderlichen Ereignis-Trigger angelegt.

Alle Tabellen, Bilder und übrigen Daten des früheren Prototyps bleiben unverändert
vorhanden. Die Migration protokolliert, ob dessen Profiltabelle bei der ersten
Initialisierung existierte. Alte Profile, Stundenpläne und Lernzyklen werden nicht
als vermeintlich gemeinsam bestätigte neue Vereinbarung interpretiert. Es gibt
keine automatische Zuordnung alter eigener Kindprofile zum konfigurierten Kind.
Falls Inhalte übernommen werden sollen, müssen zunächst Profilzugehörigkeit und
gewünschte Vereinbarungsinhalte gemeinsam geklärt werden. Das blockiert neue,
ausdrücklich bestätigte Vereinbarungen nicht.

Alte Prototyp-Routen wie `/woche/einrichtung` oder `/woche/notfall` sind nicht mehr
registriert. Die alten Helfer/Assets bleiben nur als Material für einen späteren,
bewussten Datenimport erhalten; sie werden vom Pilot nicht aufgerufen.

Das Projekt hat keinen allgemeinen Kinddaten-Lösch- oder personenbezogenen
Exportablauf. Die vorhandene vollständige SQLite-Sicherung (`make backup`) enthält
auch die neuen und alten Wochentabellen. `Lernstand.xlsx` bleibt ein Lernstandexport
und erhält keine Wochen- oder privaten Sitzungsdaten. Vor einem Update lässt sich
mit `make backup` die vorhandene vollständige Sicherung erstellen.

## Prüfung

Die vorhandene Python-3.10-Umgebung dieses Checkouts wurde verwendet:

```sh
karo-py310/bin/python -m pytest tests/test_woche.py -o addopts='' -q
karo-py310/bin/python -m pytest -o addopts='' -q
```

Die bisherigen Prototyp-Tests wurden durch Abnahmetests für den ausdrücklich
ersetzenden Pilotauftrag ersetzt. Tests für Speedrun, Notfall, Interessenfreigabe
und unveränderliche Ereignisse wären Anforderungen an das verworfene Produkt.
Die bestehenden UI-Tests prüfen jetzt die angeforderte zusätzliche Navigation.
Kein Test wurde übersprungen oder deaktiviert.

Der Ausgangslauf vor Änderungen hatte 222 bestandene Tests und einen Fehler:
`test_app.py::test_quelle_erlaubt_prueft_wirklich`. Dieser Test erwartet, dass
`de.serlo.org` durch den Allowlist-Eintrag `serlo.org` zugelassen wird; die bestehende
Funktion vergleicht Hosts exakt. Die Wochenimplementierung verändert diese
unabhängige Recherche-/Quellenentscheidung nicht.

## Manuelle Prüfung (höchstens sechs Schritte)

1. Als Eltern anmelden, `/eltern` → „Meine Woche“ öffnen, Ziel/Routine/Zusage
   gemeinsam eintragen und bestätigen. Auch Routine allein ausprobieren.
2. Kind-Modus starten, „Meine Woche“ öffnen; „Passt für mich“, „Loslegen“ und
   „Geschafft“ prüfen. Das Wochenziel erst mit der separaten Aktion melden/korrigieren.
3. „Heute nicht“ und „Doch starten“ prüfen; „War schwierig“ ausprobieren.
   Die Elternübersicht darf keine privaten Gründe oder Ausblendungen zeigen.
4. Als Kind Hilfe mit geteiltem Text anfragen; als Eltern zusagen, als Kind Antwort
   ansehen; nach Unterstützung als Eltern erledigen. Auch Zurücknehmen ausprobieren.
5. Pausieren/fortsetzen, Zusage weiter sichtbar prüfen; nächste Woche übernehmen,
   Inhalte ändern und bestätigen. Alte offene Hilfe muss weiterhin erreichbar sein.
6. Kind- und Elternseite bei 360–400 px, mit Tastatur und vorhandenen hellen/dunklen
   Farbwelten prüfen: lesbare Labels, Fokus, keine Überlagerung oder horizontale Leiste.

### Tatsächliche Ergebnisse am 15.09.2026

- Vollständiger Regressionslauf: **228 bestanden, 1 vorbestehender Fehler**
  (`test_quelle_erlaubt_prueft_wirklich`), eine vorhandene Starlette/AnyIO-Warnung.
- Abschließende gezielte Prüfung nach den letzten UI-Anpassungen:
  **52 bestanden** (`test_woche.py`, `test_ui.py`, `test_area_themes.py`,
  `test_architecture.py`), darunter **38 Pilot-Abnahmeszenarien**.
- `node --check app/static/woche-pilot.js`, Python-Kompilierung und
  `git diff --check`: erfolgreich.
- Isolierter Browser-Test mit ausschließlich erfundenen Daten auf Port 8099:
  Anmeldung als Kind und Desktop-Darstellung von `/woche` in Chrome visuell geprüft.
  Nach Öffnen der Geräteansicht lieferte die Computer-Use-Verbindung keine nutzbaren
  Zustände/Bilder mehr; auch Wiederverbinden und Safari-Ausweichversuch halfen nicht.
  **Elternansicht, 360–400-px-Ansicht und dunkle Farbwelt sind daher nicht visuell
  verifiziert.** Elternformulare und Rollen sind über echte TestClient-Requests
  geprüft. Schritt 6 der manuellen Prüfliste bleibt die visuelle Nachprüfung.
