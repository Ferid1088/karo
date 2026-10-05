/* Kopf-Picker fuer die Design-Welten.

   Die Grundfunktion laeuft ohne Skript: <details> oeffnet, jede Kachel ist
   ein Formular, die Wahl laedt die Seite neu. Dieses Skript macht daraus:
     - Klick auf eine Kachel -> Sofort-Vorschau + Speichern per fetch,
       das Popover bleibt offen
     - Klassen-Chips -> andere Klassen im selben Popover (max. 10 Kacheln)
     - ESC oder Klick daneben -> schliessen */
(() => {
  'use strict';
  const picker = document.querySelector('[data-design-picker]');
  if (!picker) return;

  const datenEl = picker.querySelector('#theme-daten');
  let daten = {};
  try { daten = JSON.parse(datenEl ? datenEl.textContent : '{}'); } catch (_) {}
  const katalog = daten.catalog || {};
  const grid = picker.querySelector('[data-theme-grid]');
  const klassenLabel = picker.querySelector('[data-grade-label]');
  const csrfFeld = picker.dataset.csrfField || '_csrf';
  const csrf = picker.dataset.csrf || '';
  const ziel = picker.dataset.ziel || '/';
  let gewaehlt = picker.dataset.selected || 'default';
  let klasse = picker.dataset.grade || '';

  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  function kachel(t) {
    const form = el('form', 'theme-tile' + (t.id === gewaehlt ? ' aktiv' : ''));
    form.method = 'post';
    form.action = '/themes/waehlen';
    form.dataset.themeId = t.id;
    for (const [name, wert] of [[csrfFeld, csrf], ['theme_id', t.id], ['ziel', ziel]]) {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = name;
      input.value = wert;
      form.appendChild(input);
    }
    const btn = el('button', 'theme-tile-btn');
    btn.type = 'submit';
    btn.style.setProperty('--ta', (t.accent || [])[0] || '');
    btn.style.setProperty('--tb', (t.accent || [])[1] || '');
    const emoji = el('span', 'theme-emoji', t.icon || '🎨');
    emoji.setAttribute('aria-hidden', 'true');
    const check = el('span', 'theme-check', '✓');
    check.setAttribute('aria-hidden', 'true');
    const sr = el('span', 'sr', 'ausgewählt');
    btn.append(emoji, el('span', 'theme-name', t.name),
               el('span', 'theme-tags', (t.tags || []).join(' · ')), check, sr);
    form.appendChild(btn);
    return form;
  }

  function zeigeKlasse(g) {
    const eintraege = katalog[String(g)] || [];
    klasse = String(g);
    if (klassenLabel) klassenLabel.textContent = 'Klasse ' + g;
    if (grid) {
      grid.textContent = '';
      // Nie mehr als die konfigurierte Anzahl Kacheln — auch wenn der
      // Katalog einmal groesser wird.
      eintraege.slice(0, daten.per_grade || 10).forEach(t => grid.appendChild(kachel(t)));
    }
    picker.querySelectorAll('.theme-klasse').forEach(chip => {
      const aktiv = chip.dataset.grade === klasse;
      chip.classList.toggle('aktiv', aktiv);
      if (aktiv) chip.setAttribute('aria-current', 'true');
      else chip.removeAttribute('aria-current');
    });
  }

  function anwenden(theme) {
    const root = document.documentElement;
    if (theme.family) {
      root.dataset.themeFamily = theme.family;
      root.dataset.themeBand = theme.band;
      root.dataset.themeId = theme.id;
    } else {
      delete root.dataset.themeFamily;
      delete root.dataset.themeBand;
      delete root.dataset.themeId;
    }
    gewaehlt = theme.id;
    picker.dataset.selected = theme.id;
    picker.querySelectorAll('.theme-tile').forEach(f =>
      f.classList.toggle('aktiv', f.dataset.themeId === theme.id));
  }

  function fehler(text) {
    let box = picker.querySelector('.theme-fehler');
    if (!box) {
      box = el('p', 'theme-fehler');
      box.setAttribute('role', 'status');
      picker.querySelector('.theme-pop').appendChild(box);
    }
    box.textContent = text;
  }

  function schliessen() {
    if (picker.open) picker.removeAttribute('open');
  }

  // Auswahl per fetch: Vorschau sofort, Popover bleibt offen.
  picker.addEventListener('submit', event => {
    const form = event.target;
    if (!form || form.action.indexOf('/themes/waehlen') === -1) return;
    event.preventDefault();
    fetch(form.action, {
      method: 'POST',
      headers: { 'Accept': 'application/json' },
      body: new FormData(form),
    }).then(r => r.json().then(daten_ => ({ ok: r.ok, daten: daten_ })))
      .then(({ ok, daten: d }) => {
        if (ok && d && d.ok && d.theme) anwenden(d.theme);
        else fehler((d && d.fehler) || 'Das hat nicht geklappt. Noch einmal versuchen?');
      })
      .catch(() => fehler('Keine Verbindung. Noch einmal versuchen?'));
  });

  // Klassen-Chips wechseln den Katalog im selben Popover.
  picker.addEventListener('click', event => {
    const chip = event.target.closest && event.target.closest('.theme-klasse');
    if (chip && chip.dataset.grade) zeigeKlasse(chip.dataset.grade);
  });

  // ESC schliesst; Klick ausserhalb schliesst; Fokus wandert nach draussen
  // schliesst ebenfalls, damit die Tastatur nie im Popover haengen bleibt.
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && picker.open) {
      schliessen();
      const tab = picker.querySelector('.theme-tab');
      if (tab) tab.focus();
    }
  });
  document.addEventListener('click', event => {
    if (picker.open && !picker.contains(event.target)) schliessen();
  });
  picker.addEventListener('focusout', event => {
    if (picker.open && event.relatedTarget && !picker.contains(event.relatedTarget)) {
      schliessen();
    }
  });

  // Pfeiltasten im Kachel-Raster: hoch/runter springt eine Zeile
  // (Spaltenzahl kommt aus dem gerenderten --spalten-Wert).
  if (grid) {
    grid.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
      const kacheln = Array.from(grid.querySelectorAll('.theme-tile-btn'));
      const i = kacheln.indexOf(document.activeElement);
      if (i === -1) return;
      const spalten = parseInt(getComputedStyle(grid).getPropertyValue('--spalten'), 10) || 2;
      let zielIdx = i;
      if (event.key === 'ArrowLeft') zielIdx = i - 1;
      if (event.key === 'ArrowRight') zielIdx = i + 1;
      if (event.key === 'ArrowUp') zielIdx = i - spalten;
      if (event.key === 'ArrowDown') zielIdx = i + spalten;
      if (kacheln[zielIdx]) { event.preventDefault(); kacheln[zielIdx].focus(); }
    });
  }

  zeigeKlasse(klasse);
})();
