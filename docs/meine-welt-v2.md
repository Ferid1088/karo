# Meine Welt V2 – private, deterministische Kinderwelt

Status: Implementierungsbasis für den Branch `meine-welt-v2-secure`.

## Produktkern

„Meine Welt“ hat genau drei Bereiche:

1. **Heute** – eine kuratierte Entdeckung, eine Denkfrage, ein persönlicher Moment.
2. **Mein Jahr** – chronologische Erinnerungen und gemerkte Entdeckungen.
3. **Zeitkapseln** – private Nachrichten an das spätere Ich.

Keine KI, kein Live-Web, kein Feed, keine Punkte/Streaks, kein Tracking.

## Datenschutz- und Sicherheitsprinzipien

- Persönliche Welt-Daten liegen **nicht** in der Lern-Datenbank.
- Fotos und Audio liegen **nicht** in SQLite, sondern in einem privaten Medienspeicher.
- Browser-/App-Zugriff auf Medien erfolgt nur über authentifizierte Routen; es gibt keine öffentlichen Dateipfade.
- Fotos werden serverseitig neu codiert (EXIF/Metadaten entfernt, Größe begrenzt, Thumbnail erzeugt).
- Audio wird nicht transkribiert und nicht an Speech-/AI-Dienste übertragen.
- Keine externen Webfonts/Tracker im Kinderbereich.
- Elternfreigabe vor Nutzung persönlicher Speicherfunktionen.
- Harte serverseitige Tageslimits:
  - höchstens 2 Fotos
  - höchstens 60 Sekunden Audio
- Kindgerechte Datenschutzhinweise; Eltern können Daten exportieren und vollständig löschen.
- Zeitkapsel-Inhalte werden vor dem Öffnungsdatum nicht ausgeliefert.
- Produktionsbetrieb später: EU-Hosting, TLS, private Object-Storage-Buckets, Verschlüsselung at rest, verschlüsselte Backups, Schlüsselmanagement, Monitoring ohne Inhaltslogs und dokumentierte Lösch-/Incident-Prozesse.

## Rechtlicher Rahmen für Produktion

Die Implementierung folgt technisch den Prinzipien von DSGVO Art. 5 (Zweckbindung, Datenminimierung, Speicherbegrenzung, Integrität/Vertraulichkeit), Art. 25 (Privacy by Design/Default) und Art. 32 (Sicherheit). Bei einem unmittelbar an Kinder gerichteten Dienst ist Art. 8 relevant, wenn die Verarbeitung auf Einwilligung beruht. Rechtsgrundlage, Einwilligungs-/Elternprozess, Informationspflichten, Auftragsverarbeiter, TOMs, Verzeichnis der Verarbeitungstätigkeiten und ggf. DSFA müssen vor einem öffentlichen Produktstart rechtlich geprüft und dokumentiert werden.

## Datenhaltung

```
/data/
  karo.db                        # bestehendes Lernsystem
  meine-welt-private/
    world.sqlite3                # nur Meine-Welt-Metadaten
    media/                       # privat, nicht statisch gemountet
      photos/
      thumbs/
      audio/
```

Die Anwendung ist aktuell eine Single-Learner-Installation. `child_key='installation'` ist bewusst pseudonym und enthält keinen Namen. Das Schema ist so gehalten, dass später ein tenant-/subject-key ergänzt werden kann.

## Content

Wissensartikel und Denkfragen sind kuratiertes Produkt-Content und enthalten keine personenbezogenen Daten. Sie können getrennt von der privaten Welt-Datenbank als Code/JSON ausgeliefert und redaktionell versioniert werden. Jede Entdeckung hat Quellenmetadaten; Bilder werden später nur als lokal gespeicherte, lizenzgeprüfte Assets eingebunden.

## Produktions-Gate

Vor Freigabe für echte Familien:

- HTTPS-only + Secure Cookies + HSTS
- EU-Region für DB/Object Storage/Backups
- private Buckets, keine öffentlichen ACLs
- Verschlüsselung at rest und Key-Rotation
- Restore-Test der Backups
- Datenexport und vollständige Löschung getestet
- Security Review / Threat Model
- Datenschutzinformationen für Eltern und Kinder
- AV-Verträge für jeden Auftragsverarbeiter
- rechtliche Prüfung der Rechtsgrundlage und ggf. DSFA
