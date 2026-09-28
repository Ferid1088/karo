/* Apply each area's saved palette before first paint.
   Parents also choose Hell, Dunkel or Automatisch (follows the device, like
   prefers-color-scheme). The saved parent palette is the light one; "nacht"
   is the dark mode. Everything stays in this browser (localStorage). */
(() => {
  'use strict';
  const palettes = {
    parent: ['schiefer', 'sand', 'nacht'],
    child: ['lila', 'ozean', 'wiese', 'sonne', 'zuckerwatte', 'lava', 'dunkel']
  };
  const DARK = 'nacht';
  const MODES = ['auto', 'hell', 'dunkel'];
  const root = document.documentElement;
  const area = root.dataset.uiArea === 'parent' ? 'parent' : 'child';
  const media = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
  const read = key => { try { return localStorage.getItem(key); } catch (_) { return null; } };
  const write = (key, value) => { try { localStorage.setItem(key, value); } catch (_) {} };

  function saved(target) {
    let value = read(`karo-farbwelt-${target}`);
    if (!value && target === 'child') value = read('karo-farbwelt');
    return palettes[target].includes(value) ? value : palettes[target][0];
  }
  function lightPalette() {
    const value = saved('parent');
    return value === DARK ? palettes.parent[0] : value;
  }
  function mode() {
    const value = read('karo-modus-parent');
    if (MODES.includes(value)) return value;
    // Earlier versions stored "Nachtblau" as palette: keep it as an explicit dark choice.
    return read('karo-farbwelt-parent') === DARK ? 'dunkel' : 'auto';
  }
  function effective(target) {
    if (target !== 'parent') return saved(target);
    const current = mode();
    return current === 'dunkel' || (current === 'auto' && media && media.matches) ? DARK : lightPalette();
  }
  function apply() {
    root.dataset.themeColor = effective(area);
    if (area === 'parent') root.dataset.themeMode = mode();
  }
  function sync() {
    const current = mode();
    document.querySelectorAll('[data-modus]').forEach(button =>
      button.setAttribute('aria-pressed', String(button.dataset.modus === current)));
    document.querySelectorAll('[data-modus-picker]').forEach(select => { select.value = current; });
    document.querySelectorAll('[data-theme-picker]').forEach(picker => {
      if (palettes[picker.dataset.themePicker]) picker.value = effective(picker.dataset.themePicker);
    });
  }
  function setMode(value) {
    if (!MODES.includes(value)) return;
    write('karo-modus-parent', value);
    apply();
    sync();
  }

  apply();
  if (media) {
    const follow = () => { if (mode() === 'auto') { apply(); sync(); } };
    if (media.addEventListener) media.addEventListener('change', follow);
    else if (media.addListener) media.addListener(follow);
  }
  // Another tab changed the choice.
  window.addEventListener('storage', event => {
    if (event.key && event.key.startsWith('karo-')) { apply(); sync(); }
  });
  document.addEventListener('DOMContentLoaded', () => {
    sync();
    document.addEventListener('click', event => {
      const button = event.target.closest && event.target.closest('[data-modus]');
      if (button) setMode(button.dataset.modus);
    });
    document.querySelectorAll('[data-modus-picker]').forEach(select =>
      select.addEventListener('change', () => setMode(select.value)));
    document.querySelectorAll('[data-theme-picker]').forEach(picker => {
      const target = picker.dataset.themePicker;
      if (!palettes[target]) return;
      picker.addEventListener('change', () => {
        const value = picker.value;
        if (!palettes[target].includes(value)) return;
        if (target === 'parent') {
          // Picking a palette is an explicit choice and overrides "Automatisch".
          if (value === DARK) write('karo-modus-parent', 'dunkel');
          else { write('karo-farbwelt-parent', value); write('karo-modus-parent', 'hell'); }
        } else {
          write(`karo-farbwelt-${target}`, value);
        }
        if (target === area) apply();
        sync();
      });
    });
  });
})();
