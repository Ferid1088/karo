/* Settings: disclose relevant controls while retaining ordinary HTML forms. */
(() => {
  'use strict';
  document.querySelectorAll('[data-backend-form]').forEach(form => {
    function updateBackend() {
      const selected = form.querySelector('input[name="backend"]:checked');
      form.querySelectorAll('[data-backend-panel]').forEach(panel => {
        panel.hidden = !!selected && panel.dataset.backendPanel !== selected.value;
      });
    }
    form.addEventListener('change', updateBackend);
    updateBackend();
  });

  const form = document.querySelector('[data-settings-form]');
  if (form) {
    const format = form.querySelector('[name="default_ausgabe"]');
    const button = document.querySelector('[data-settings-save]');
    const status = document.querySelector('[data-settings-status]');
    const initial = new URLSearchParams(new FormData(form)).toString();
    let dirty = form.dataset.invalid === 'true';
    function update() {
      form.querySelectorAll('[data-format-options]').forEach(panel => {
        panel.hidden = panel.dataset.formatOptions !== format.value;
      });
      if (form.dataset.configured === 'true') {
        dirty = new URLSearchParams(new FormData(form)).toString() !== initial;
        button.disabled = !dirty && form.dataset.invalid !== 'true';
        status.textContent = dirty ? 'Noch nicht gespeicherte Änderungen.' :
          (form.dataset.invalid === 'true' ? 'Bitte prüfen Sie die markierten Angaben.' : 'Alles gespeichert.');
      }
      form.querySelectorAll('.settings-choice').forEach(choice => {
        choice.querySelector('[data-child-destination]').textContent =
          choice.querySelector('input').checked ? 'Beim Kind' : 'Nur Eltern';
      });
    }
    form.addEventListener('input', update);
    form.addEventListener('change', update);
    form.addEventListener('submit', () => { dirty = false; });
    window.addEventListener('beforeunload', event => {
      if (dirty) { event.preventDefault(); event.returnValue = ''; }
    });
    form.addEventListener('invalid', event => {
      let parent = event.target.parentElement;
      while (parent && parent !== form) {
        if (parent.tagName === 'DETAILS') parent.open = true;
        parent = parent.parentElement;
      }
    }, true);
    update();
  }

  function openLinkedSection() {
    const target = document.getElementById(location.hash.slice(1));
    if (target && target.tagName === 'DETAILS') {
      target.open = true;
      requestAnimationFrame(() => target.scrollIntoView({block: 'start'}));
    }
  }
  window.addEventListener('hashchange', openLinkedSection);
  openLinkedSection();

  document.querySelectorAll('[data-nlm-login]').forEach(loginForm => {
    loginForm.addEventListener('submit', async event => {
      event.preventDefault();
      const button = loginForm.querySelector('button');
      const hint = loginForm.closest('[data-nlm-block]').querySelector('[data-nlm-login-hinweis]');
      const popup = window.open('about:blank', 'karo-notebooklm-login', 'width=980,height=680');
      if (!popup) {
        hint.textContent = 'Bitte erlauben Sie Popups für Karo und versuchen Sie es erneut.';
        return;
      }
      popup.document.title = 'NotebookLM-Anmeldung';
      popup.document.body.textContent = 'Die Google-Anmeldung wird vorbereitet …';
      button.disabled = true;
      hint.textContent = 'Die Anmeldung wird vorbereitet. Das Fenster öffnet sich gleich.';
      try {
        const response = await fetch(loginForm.action, {method: 'POST', body: new FormData(loginForm)});
        if (!response.ok) throw new Error('Login request failed');
      } catch (_) {
        popup.close();
        button.disabled = false;
        hint.textContent = 'Die Anmeldung konnte nicht gestartet werden. Bitte erneut versuchen.';
        return;
      }
      let attempts = 0;
      let connected = false;
      async function poll() {
        if (popup.closed) {
          button.disabled = false;
          hint.textContent = 'Anmeldefenster geschlossen. Sie können es erneut öffnen.';
          return;
        }
        attempts++;
        try {
          const response = await fetch('/setup/notebooklm/status', {cache: 'no-store'});
          if (!response.ok) throw new Error('Status request failed');
          const state = await response.json();
          if (!state.laeuft) {
            button.disabled = false;
            hint.textContent = state.meldung || 'Anmeldung beendet. Bei Bedarf erneut versuchen.';
            if (state.ok) { popup.close(); location.reload(); }
            return;
          }
          if (state.vnc_bereit && !connected) {
            const port = Number(state.novnc_port);
            if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Invalid login address');
            popup.location = `http://127.0.0.1:${port}/vnc.html?autoconnect=true&resize=scale&reconnect=true`;
            connected = true;
            hint.textContent = 'Melden Sie sich im geöffneten Fenster bei Google an. Karo aktualisiert sich danach automatisch.';
          }
        } catch (_) {
          hint.textContent = 'Der Anmeldestatus ist gerade nicht erreichbar. Karo versucht es erneut.';
        }
        if (attempts < 150) {
          setTimeout(poll, 2000);
        } else {
          button.disabled = false;
          hint.textContent = 'Die Anmeldung dauert länger. Öffnen Sie das Anmeldefenster bei Bedarf erneut.';
        }
      }
      setTimeout(poll, 2000);
    });
  });
})();
