"""Architektur-Regressionstests (change.txt Abschnitt 4/15).

Diese Tests lesen den Quellcode statt ihn auszufuehren — sie sollen genau
EINE Regel erzwingen: Router rufen sich nicht gegenseitig fuer
Geschaeftslogik auf. Gemeinsames Verhalten gehoert in `app/services/*`.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ROUTERS_DIR = REPO_ROOT / "app" / "routers"

_EXEMPT = {"__init__", "shared"}
ROUTER_MODULES = {p.stem for p in ROUTERS_DIR.glob("*.py") if p.stem not in _EXEMPT}

#: Router, die nach der Service-Extraktion keine eigene business-SQL mehr
#: haben sollten — bewusst nicht ALLE Router (siehe admin.py/dashboard.py/
#: eltern.py: ein paar reine Anzeige-Reads bleiben dort, change.txt
#: Abschnitt 3: "Do not move trivial presentation-only reads ... for no
#: benefit"). lernzyklus.py behaelt drei URL-Parameter-Konsistenzchecks
#: (gehoert dieses Quiz wirklich zu diesem Thema?) - HTTP-Adapter-Sache,
#: keine Geschaeftsentscheidung.
ROUTERS_OHNE_DIREKTES_SQL = {"auth", "kind", "messung", "vorbereitung"}


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), str(path))


def test_kein_router_importiert_einen_anderen_router():
    """Ein `from . import kind` oder `from .kind import x` in irgendeinem
    anderen Router-Modul waere ein Router-zu-Router-Aufruf."""
    verstoesse: list[str] = []
    for path in sorted(ROUTERS_DIR.glob("*.py")):
        if path.stem in _EXEMPT:
            continue
        for node in ast.walk(_parse(path)):
            if not isinstance(node, ast.ImportFrom) or node.level != 1:
                continue
            if node.module in (None, ""):
                for alias in node.names:
                    if alias.name in ROUTER_MODULES and alias.name != path.stem:
                        verstoesse.append(f"{path.name}: from . import {alias.name}")
            elif node.module in ROUTER_MODULES and node.module != path.stem:
                namen = ", ".join(a.name for a in node.names)
                verstoesse.append(f"{path.name}: from .{node.module} import {namen}")
    assert not verstoesse, (
        "Router-zu-Router-Import gefunden — gemeinsames Verhalten gehoert "
        "in einen Service (app/services/*):\n" + "\n".join(verstoesse))


def test_ausgewaehlte_router_haben_keine_eigene_sql():
    """Diese Router wurden gezielt auf reine HTTP-Adapter reduziert
    (change.txt Abschnitt 3) — kein `db.q`/`db.q1`/`db.tx` mehr direkt im
    Router-Modul, alles laeuft ueber einen Service."""
    verstoesse: list[str] = []
    for name in ROUTERS_OHNE_DIREKTES_SQL:
        path = ROUTERS_DIR / f"{name}.py"
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.Attribute) and node.attr in ("q", "q1", "tx"):
                if isinstance(node.value, ast.Name) and node.value.id == "db":
                    verstoesse.append(f"{name}.py: db.{node.attr}(...) bei Zeile {node.lineno}")
    assert not verstoesse, "Business-SQL direkt im Router gefunden:\n" + "\n".join(verstoesse)
