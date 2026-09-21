"""Adaptives Lernen: Diagnose vor Erklärung.

Aufbau (01_ARCHITECTURE.md):

    normalisierung.py  Antworten vergleichbar machen (Tier-1-Vorstufe)
    schemas.py         Modell-/Inhaltsprüfung, bevor etwas gespeichert wird
    store.py           Repository — die EINZIGE Stelle mit SQL (§10)
    katalog.py         Fehlertyp finden, Erklärung ausliefern (§6)
    sitzung.py         Zustandsautomat, Eskalation, Beherrschung (§7, §8)

`store.py` ist bewusst die einzige Schicht, die die Datenbank kennt: der
Wechsel auf PostgreSQL in Meilenstein 4 darf nur diese Datei berühren.
"""
