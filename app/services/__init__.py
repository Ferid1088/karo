"""Service layer: Karo's actual business logic, independent of HTTP.

Routers (`app/routers/*.py`) only do HTTP input, validation, authorization
and rendering — every decision and every database write lives in one of
these modules instead:

  workflow.py     quiz + Lernrunde workflow, „Heute"-Prioritaet
  preparation.py  Schulmaterial, Themen, Recherche
  measurement.py  Lernfortschritt, Klassenarbeit-Uebersicht

Legacy-Routen-Strategie (change.txt, Aufgabe 7 — Strategie A):
Alte Adressen (`/wissen`, `/themen`, `/recherche`, `/lernstand`,
`/klassenarbeit`) und neue Adressen (`/vorbereitung/*`, `/messung/*`)
bleiben BEIDE dauerhaft erreichbar und rufen dieselben Funktionen hier
auf — keine Weiterleitungen (Strategie B), kein doppelter Code. Wenn eine
dieser Funktionen sich aendert, aendert sich das Verhalten unter jeder
Adresse gleichzeitig. Alte Adressen werden nicht entfernt, solange nicht
ausdruecklich entschieden wird, sie abzubauen (Plan-Abschnitt 17, Phase 4).
"""
