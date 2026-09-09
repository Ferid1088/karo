"""Ausgabemodus „html": Folien mit Stimme, direkt im Browser.

Der einfachste der drei Modi und der einzige ohne jede Zusatzabhängigkeit: die
Sprachausgabe kommt von der Sprachsynthese des Betriebssystems über die
Web-Speech-API. macOS und Windows bringen deutsche Stimmen mit, Linux je nach
Installation.

Die erzeugte Datei ist eine einzelne HTML-Datei ohne externe Verweise. Sie
liegt im Drive-Ordner, läuft offline und lässt sich verschicken.
"""

from __future__ import annotations

import html
import json


def _esc(text) -> str:
    return html.escape(str(text or ""), quote=True)


def lerneinheit(titel: str, kernidee: str, folien: list[dict],
                thema: str = "", stufe_hinweis: str = "") -> str:
    """Baut den Foliensatz als eine autarke HTML-Datei."""
    daten = [{"nr": f.get("nr", i + 1),
              "titel": str(f.get("titel") or ""),
              "punkte": [str(p) for p in (f.get("punkte") or [])][:5],
              "tafel": (str(f["tafel"]) if f.get("tafel") else None),
              "sprechtext": str(f.get("sprechtext") or "")}
             for i, f in enumerate(folien)]

    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(titel)}</title>
<style>
  :root {{
    --ground: #10131a; --card: #191e28; --line: #2b3242;
    --text: #eef1f6; --muted: #98a2b5;
    --ink: #8ba3ff; --ink-soft: #1d2544;
    --ok: #62c48f; --warn: #d9a13f;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--ground); color: var(--text);
    font: 16px/1.6 "IBM Plex Sans", -apple-system, BlinkMacSystemFont,
          "Segoe UI", sans-serif;
    display: flex; flex-direction: column; min-height: 100vh;
  }}
  header {{
    padding: .8rem 1.2rem; border-bottom: 1px solid var(--line);
    display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;
  }}
  header .thema {{ font-size: .8rem; color: var(--muted); }}
  header h1 {{ font-size: 1rem; margin: 0; font-weight: 600; }}
  .spacer {{ margin-left: auto; }}

  main {{ flex: 1; display: grid; place-items: center; padding: 1.5rem 1.2rem; }}
  .folie {{
    background: var(--card); border: 1px solid var(--line); border-radius: 14px;
    width: min(880px, 100%); padding: clamp(1.5rem, 4vw, 2.8rem);
    min-height: 340px; display: flex; flex-direction: column; gap: 1.1rem;
  }}
  .folie h2 {{
    margin: 0; font-size: clamp(1.4rem, 3.4vw, 2rem); line-height: 1.2;
    letter-spacing: -.02em; text-wrap: balance;
  }}
  .folie ul {{ margin: 0; padding-left: 1.3rem; display: flex;
    flex-direction: column; gap: .5rem; }}
  .folie li {{ font-size: clamp(1rem, 2.2vw, 1.15rem); }}
  .tafel {{
    background: #0c0f15; border: 1px solid var(--line); border-radius: 10px;
    padding: 1.1rem 1.3rem; font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: clamp(1.05rem, 2.6vw, 1.5rem); white-space: pre-wrap;
    color: var(--ok); overflow-x: auto; margin-top: auto;
  }}
  .kernidee {{
    background: var(--ink-soft); border-left: 3px solid var(--ink);
    padding: .8rem 1rem; border-radius: 0 8px 8px 0; font-size: .95rem;
  }}

  footer {{
    border-top: 1px solid var(--line); padding: .8rem 1.2rem;
    display: flex; gap: .8rem; align-items: center; flex-wrap: wrap;
  }}
  button {{
    font: inherit; font-weight: 600; font-size: .92rem; cursor: pointer;
    padding: .55rem 1.1rem; border-radius: 8px;
    border: 1px solid var(--ink); background: var(--ink); color: #0d1016;
  }}
  button.quiet {{ background: transparent; color: var(--text);
    border-color: var(--line); }}
  button:disabled {{ opacity: .45; cursor: not-allowed; }}
  .zaehler {{ font-size: .85rem; color: var(--muted);
    font-variant-numeric: tabular-nums; }}
  .balken {{ height: 3px; background: var(--line); border-radius: 2px;
    flex: 1 1 120px; min-width: 90px; overflow: hidden; }}
  .balken i {{ display: block; height: 100%; background: var(--ink); width: 0;
    transition: width .3s ease; }}
  .hinweis {{ font-size: .8rem; color: var(--muted); padding: 0 1.2rem 1rem; }}
  .stimme {{ font: inherit; font-size: .82rem; background: var(--card);
    color: var(--text); border: 1px solid var(--line); border-radius: 6px;
    padding: .35rem .5rem; max-width: 210px; }}
  @media (prefers-reduced-motion: reduce) {{ .balken i {{ transition: none; }} }}
</style>
</head>
<body>

<header>
  <div>
    <div class="thema">{_esc(thema)}</div>
    <h1>{_esc(titel)}</h1>
  </div>
  <div class="spacer"></div>
  <select class="stimme" id="stimme" aria-label="Stimme"></select>
</header>

<main>
  <div class="folie" id="folie">
    <h2 id="f-titel"></h2>
    <ul id="f-punkte"></ul>
    <div class="tafel" id="f-tafel" hidden></div>
  </div>
</main>

<footer>
  <button id="play">▶ Vorlesen</button>
  <button class="quiet" id="zurueck">← zurück</button>
  <button class="quiet" id="weiter">weiter →</button>
  <span class="zaehler" id="zaehler"></span>
  <div class="balken"><i id="balken"></i></div>
</footer>

<p class="hinweis" id="hinweis">
  Mit den Pfeiltasten blättern, Leertaste startet und stoppt das Vorlesen.
  {_esc(stufe_hinweis)}
</p>

<script>
const FOLIEN = {json.dumps(daten, ensure_ascii=False)};
const KERNIDEE = {json.dumps(kernidee or "", ensure_ascii=False)};

let index = 0, laeuft = false, stimmen = [], aktuelleStimme = null;
const $ = (id) => document.getElementById(id);

function stimmenLaden() {{
  const alle = window.speechSynthesis ? speechSynthesis.getVoices() : [];
  stimmen = alle.filter(v => (v.lang || "").toLowerCase().startsWith("de"));
  const wahl = $("stimme");
  wahl.innerHTML = "";
  if (!stimmen.length) {{
    wahl.innerHTML = '<option>keine deutsche Stimme gefunden</option>';
    wahl.disabled = true;
    $("hinweis").textContent =
      "Dieser Browser hat keine deutsche Sprachausgabe. Die Folien lassen " +
      "sich trotzdem lesen — der Sprechtext steht unter jeder Folie.";
    return;
  }}
  stimmen.forEach((v, i) => {{
    const o = document.createElement("option");
    o.value = String(i); o.textContent = v.name;
    wahl.appendChild(o);
  }});
  // Eine lokal installierte Stimme klingt besser und braucht kein Netz.
  const lokal = stimmen.findIndex(v => v.localService);
  wahl.value = String(lokal >= 0 ? lokal : 0);
  aktuelleStimme = stimmen[Number(wahl.value)];
}}

if (window.speechSynthesis) {{
  speechSynthesis.onvoiceschanged = stimmenLaden;
  stimmenLaden();
}} else {{
  stimmenLaden();
}}

$("stimme").addEventListener("change", (e) => {{
  aktuelleStimme = stimmen[Number(e.target.value)] || null;
}});

function zeichnen() {{
  const f = FOLIEN[index];
  $("f-titel").textContent = f.titel;
  const liste = $("f-punkte");
  liste.innerHTML = "";
  (f.punkte || []).forEach(p => {{
    const li = document.createElement("li");
    li.textContent = p;
    liste.appendChild(li);
  }});
  if (index === 0 && KERNIDEE) {{
    const li = document.createElement("li");
    li.className = "kernidee";
    li.textContent = KERNIDEE;
    liste.appendChild(li);
  }}
  const tafel = $("f-tafel");
  if (f.tafel) {{ tafel.textContent = f.tafel; tafel.hidden = false; }}
  else {{ tafel.hidden = true; }}

  $("zaehler").textContent = `Folie ${{index + 1}} von ${{FOLIEN.length}}`;
  $("balken").style.width = ((index + 1) / FOLIEN.length * 100) + "%";
  $("zurueck").disabled = index === 0;
  $("weiter").disabled = index === FOLIEN.length - 1;
}}

function stopp() {{
  laeuft = false;
  if (window.speechSynthesis) speechSynthesis.cancel();
  $("play").textContent = "▶ Vorlesen";
}}

function vorlesen() {{
  if (!window.speechSynthesis || !stimmen.length) return;
  laeuft = true;
  $("play").textContent = "■ Stopp";
  speechSynthesis.cancel();
  const text = FOLIEN[index].sprechtext;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "de-DE";
  if (aktuelleStimme) u.voice = aktuelleStimme;
  u.rate = 0.95;
  u.onend = () => {{
    if (!laeuft) return;
    if (index < FOLIEN.length - 1) {{
      index += 1; zeichnen();
      setTimeout(() => {{ if (laeuft) vorlesen(); }}, 700);
    }} else {{
      stopp();
    }}
  }};
  u.onerror = stopp;
  speechSynthesis.speak(u);
}}

$("play").addEventListener("click", () => laeuft ? stopp() : vorlesen());
$("weiter").addEventListener("click", () => {{
  if (index < FOLIEN.length - 1) {{ stopp(); index += 1; zeichnen(); }}
}});
$("zurueck").addEventListener("click", () => {{
  if (index > 0) {{ stopp(); index -= 1; zeichnen(); }}
}});
document.addEventListener("keydown", (e) => {{
  if (e.key === "ArrowRight") $("weiter").click();
  else if (e.key === "ArrowLeft") $("zurueck").click();
  else if (e.key === " ") {{ e.preventDefault(); $("play").click(); }}
}});
window.addEventListener("beforeunload", stopp);

zeichnen();
</script>
</body>
</html>"""
