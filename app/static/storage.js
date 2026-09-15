/* Select only paths available to the Karo server. Saving stays in the settings form. */
(() => {
  'use strict';
  const dialog = document.querySelector('[data-storage-dialog]');
  if (!dialog) return;
  const root = dialog.querySelector('[data-storage-root]');
  const folders = dialog.querySelector('[data-storage-folders]');
  const up = dialog.querySelector('[data-storage-up]');
  const select = dialog.querySelector('[data-storage-select]');
  const filename = dialog.querySelector('[data-storage-filename]');
  const error = dialog.querySelector('[data-storage-dialog-error]');
  let kind, field, state, requestId = 0;
  function showError(message) {
    error.textContent = message;
    error.hidden = !message;
  }
  async function browse(rootId = '', relative = '') {
    const id = ++requestId;
    state = null;
    select.disabled = true;
    up.disabled = true;
    root.disabled = true;
    folders.replaceChildren();
    folders.setAttribute('aria-busy', 'true');
    showError('');
    try {
      const query = new URLSearchParams({kind, root: rootId, relative});
      const response = await fetch(`/setup/speicher/ordner?${query}`, {cache: 'no-store'});
      if (response.redirected) throw new Error('Bitte erneut anmelden.');
      const data = await response.json();
      if (!response.ok) throw new Error(data.error);
      if (id !== requestId) return;
      state = data;
      root.replaceChildren(...data.roots.map(item => new Option(item.label, item.id)));
      root.value = data.root;
      dialog.querySelector('[data-storage-path]').textContent = data.path;
      up.disabled = !data.relative;
      for (const name of data.folders) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'quiet';
        button.textContent = `▸ ${name}`;
        button.addEventListener('click', () => browse(data.root, [data.relative, name].filter(Boolean).join('/')));
        folders.append(button);
      }
      if (!data.folders.length) {
        const empty = document.createElement('p');
        empty.textContent = 'Keine Unterordner';
        folders.append(empty);
      }
      select.disabled = false;
    } catch (exc) {
      if (id === requestId) showError(exc.message || 'Ordner konnten nicht geladen werden.');
    } finally {
      if (id === requestId) {
        root.disabled = false;
        folders.setAttribute('aria-busy', 'false');
      }
    }
  }
  document.querySelectorAll('[data-storage-picker]').forEach(button => {
    button.addEventListener('click', () => {
      kind = button.dataset.storagePicker;
      field = document.getElementById(kind === 'database' ? 'material_db_path' : 'drive_unterordner');
      filename.value = kind === 'database' ? field.value.split('/').pop() || 'lernmaterialien.sqlite3' : '';
      dialog.querySelector('[data-storage-filename-field]').hidden = kind !== 'database';
      dialog.querySelector('[data-storage-path]').textContent = '';
      dialog.showModal();
      browse();
    });
  });
  root.addEventListener('change', () => browse(root.value));
  up.addEventListener('click', () => {
    if (state) browse(state.root, state.relative.split('/').slice(0, -1).join('/'));
  });
  dialog.querySelector('[data-storage-cancel]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => { requestId++; });
  select.addEventListener('click', async () => {
    if (!state) return;
    const id = requestId;
    const selectedField = field;
    select.disabled = true;
    const body = new FormData();
    body.set('kind', kind);
    body.set('root', state.root);
    body.set('relative', state.relative);
    body.set('filename', filename.value);
    body.set('_csrf', document.querySelector('#settings-form [name="_csrf"]').value);
    try {
      const response = await fetch('/setup/speicher/auswaehlen', {method: 'POST', body});
      if (response.redirected) throw new Error('Bitte erneut anmelden.');
      const data = await response.json();
      if (id !== requestId) return;
      if (!response.ok) throw new Error(data.error);
      selectedField.value = data.value;
      selectedField.dispatchEvent(new Event('input', {bubbles: true}));
      dialog.close();
    } catch (exc) {
      if (id === requestId) showError(exc.message || 'Der Ordner konnte nicht ausgewählt werden.');
    } finally {
      if (id === requestId) select.disabled = false;
    }
  });
})();
