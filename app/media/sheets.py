"""Druckbare Blätter: Fragebogen und Übungsblatt.

Kein PDF-Erzeuger im Image — das Druck-Stylesheet des Browsers reicht und
spart rund 200 MB. Strg+P, fertig.
"""

from __future__ import annotations

import html


def _esc(text) -> str:
    return html.escape(str(text or ""), quote=True)


_STYLE = """
 body{font-family:Georgia,"Times New Roman",serif;max-width:19cm;
       margin:2cm auto;line-height:1.65;color:#111}
 h1{font-size:19pt;margin:0 0 .15cm;letter-spacing:-.01em}
 .thema{font-size:10.5pt;color:#555;margin:0 0 .7cm}
 .kopf{display:flex;justify-content:space-between;font-size:10pt;color:#555;
       border-bottom:1px solid #ccc;padding-bottom:.2cm;margin-bottom:.6cm}
 .hinweis{background:#f2f4f8;padding:.5cm;border-left:3px solid #1c3fbf;
          margin:.6cm 0;font-size:11pt}
 ol{padding-left:1.1cm} li{margin-bottom:1.15cm}
 li p{margin:0 0 .35cm} .stufe{font-size:9pt;color:#888}
 .feld{border-bottom:1px solid #999;height:1.5cm}
 .feld.hoch{height:2.6cm}
 @media print{body{margin:1.4cm} .nodruck{display:none}}
"""


def aufgabenblatt(thema: str, fragen: list[dict], hinweis: str = "") -> str:
    """Fragebogen zum Ausdrucken. Ohne Lösungen."""
    zeilen = []
    for f in fragen:
        stufe = f.get("stufe")
        marke = f' <span class="stufe">({_esc(stufe)})</span>' if stufe else ""
        hoch = "hoch" if (stufe == "schwer") else ""
        zeilen.append(
            f"<li><p>{_esc(f.get('frage'))}{marke}</p>"
            f'<div class="feld {hoch}"></div></li>')
    return f"""<!doctype html><html lang="de"><meta charset="utf-8">
<title>{_esc(thema)}</title>
<style>{_STYLE}</style>
<div class="kopf"><span>Übung</span><span>Datum: __________</span></div>
<h1>{_esc(thema)}</h1>
{f'<div class="hinweis">{_esc(hinweis)}</div>' if hinweis else ''}
<ol>{''.join(zeilen)}</ol>
<p class="nodruck stufe">Zum Drucken Strg+P (Mac: Cmd+P).</p>
</html>"""


def loesungsblatt(thema: str, fragen: list[dict]) -> str:
    """Nur für die Lernbegleitung: dieselben Fragen mit erwarteten Antworten."""
    zeilen = "".join(
        f"<li><p>{_esc(f.get('frage'))}</p>"
        f"<p style='color:#1a6b3f'><strong>→ {_esc(f.get('erwartet'))}</strong></p></li>"
        for f in fragen)
    return f"""<!doctype html><html lang="de"><meta charset="utf-8">
<title>Lösungen — {_esc(thema)}</title>
<style>{_STYLE}</style>
<div class="kopf"><span>Lösungen — nicht für das Kind</span>
<span>{_esc(thema)}</span></div>
<h1>Lösungen</h1>
<ol>{zeilen}</ol>
</html>"""
