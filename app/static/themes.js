/* Apply each area's saved palette before first paint. */
(() => {
  'use strict';
  const palettes = {
    parent: ['schiefer', 'sand', 'nacht'],
    child: ['lila', 'ozean', 'wiese', 'sonne', 'zuckerwatte', 'lava', 'dunkel']
  };
  const root = document.documentElement;
  const area = root.dataset.uiArea === 'parent' ? 'parent' : 'child';
  function saved(target) {
    let value;
    try {
      value = localStorage.getItem(`karo-farbwelt-${target}`);
      if (!value && target === 'child') value = localStorage.getItem('karo-farbwelt');
    } catch (_) {}
    return palettes[target].includes(value) ? value : palettes[target][0];
  }
  root.dataset.themeColor = saved(area);
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-theme-picker]').forEach(picker => {
      const target = picker.dataset.themePicker;
      if (!palettes[target]) return;
      picker.value = saved(target);
      picker.addEventListener('change', () => {
        if (!palettes[target].includes(picker.value)) return;
        try { localStorage.setItem(`karo-farbwelt-${target}`, picker.value); } catch (_) {}
        if (target === area) root.dataset.themeColor = picker.value;
      });
    });
  });
})();
