/* Aktualisiert nur die Materialzelle: geöffnete Pläne und Eingaben bleiben bestehen. */
(() => {
  'use strict';
  function update(entry, material) {
    entry.dataset.state = material.state;
    const link = entry.querySelector('a');
    link.href = material.url;
    link.textContent = material.meldung;
    entry.querySelector('span').textContent = material.titel + (material.ergebnis ? ' · ' + material.ergebnis : '');
  }
  function poll(entry) {
    if (entry.dataset.polling === 'true') return;
    entry.dataset.polling = 'true';
    let errors = 0;
    async function refresh() {
      if (!entry.isConnected) return;
      try {
        const response = await fetch(entry.dataset.statusUrl, {
          headers: {Accept: 'application/json'}, cache: 'no-store'
        });
        if (!response.ok || response.redirected) throw new Error('status');
        update(entry, await response.json());
        errors = 0;
      } catch (_) {
        errors++;
        entry.querySelector('span').textContent = 'Status gerade nicht erreichbar. Erneuter Versuch folgt automatisch.';
      }
      // Auch fertige Materialien werden beim Zurückkehren geprüft; niemals
      // die Klassenarbeit-Seite neu laden oder einen Tab automatisch öffnen.
      if (entry.dataset.state === 'offen' || entry.dataset.state === 'wartet' || errors) {
        setTimeout(refresh, Math.min(30000, 2500 * (errors + 1)));
      } else {
        entry.dataset.polling = 'false';
      }
    }
    setTimeout(refresh, 1500);
  }
  document.querySelectorAll('[data-plan-material]').forEach(cell => {
    cell.querySelectorAll('[data-material-id]').forEach(poll);
    const form = cell.querySelector('[data-material-form]');
    if (!form) return;
    const message = cell.querySelector('[data-material-message]');
    const button = form.querySelector('button[type="submit"]');
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (button.disabled) return;
      const data = new FormData(form);
      button.disabled = true;
      message.textContent = 'Die Erstellung wird gestartet …';
      try {
        const response = await fetch(form.action, {
          method: 'POST', body: data, headers: {Accept: 'application/json'}
        });
        if (response.redirected) throw new Error('Bitte erneut anmelden.');
        const material = await response.json();
        if (!response.ok) throw new Error(material.fehler || 'Die Erstellung konnte nicht gestartet werden.');
        let entry = cell.querySelector(`[data-material-id="${material.id}"]`);
        if (!entry) {
          entry = document.createElement('p');
          entry.dataset.materialId = String(material.id);
          entry.dataset.statusUrl = material.url + '/status';
          const link = document.createElement('a');
          link.target = '_blank';
          link.rel = 'noopener';
          const name = document.createElement('span');
          name.className = 'klein';
          entry.append(link, name);
          cell.querySelector('[data-material-list]').prepend(entry);
        }
        update(entry, material);
        poll(entry);
        message.textContent = 'Gestartet. Über den Link öffnest du das Material in einem neuen Tab.';
      } catch (error) {
        message.textContent = error.message || 'Die Verbindung ist unterbrochen. Bitte erneut versuchen.';
      } finally {
        button.disabled = false;
      }
    });
  });
  window.addEventListener('focus', () => {
    document.querySelectorAll('[data-material-id]').forEach(poll);
  });
})();
