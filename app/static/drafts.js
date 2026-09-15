/* Save to Karo, retain an offline copy, and never overwrite a newer tab silently. */
(() => {
  'use strict';
  const quiz = document.querySelector('[data-draft-key]');
  if (!quiz || !['bereit', 'ausgewertet'].includes(quiz.dataset.quizState)) return;
  const form = document.querySelector('[data-answer-form], [data-review-form]');
  if (!form) return;
  const review = form.hasAttribute('data-review-form');
  const phase = review ? 'review' : 'answers';
  const key = quiz.dataset.draftKey + (review ? '-review' : '');
  const status = form.querySelector('[data-draft-status]');
  const revisionInput = form.querySelector('[name="draft_revision"]');
  let revision = Number(quiz.dataset.draftRevision || 0);
  let timer, running, dirty = false, blocked = false, localConflict;
  const fields = [...form.querySelectorAll(review ? '[name^="urteil_"], [name^="fehler_"]' : '[name^="antwort_"]')];
  const read = () => Object.fromEntries(fields.filter(f => f.type !== 'radio' || f.checked).map(f => [f.name, f.value]));
  const snapshot = () => ({values: read(), position: Number(form.dataset.position || quiz.dataset.draftPosition || 0)});
  const message = text => { if (status) status.textContent = text; };
  function cache(unsynced) {
    try { localStorage.setItem(key, JSON.stringify({...snapshot(), revision, unsynced, savedAt: Date.now()})); }
    catch (_) { if (unsynced) message('Wird in Karo gespeichert …'); }
  }
  function restore(draft) {
    fields.forEach(field => {
      if (Object.hasOwn(draft.values, field.name)) {
        if (field.type === 'radio') field.checked = draft.values[field.name] === field.value;
        else field.value = draft.values[field.name];
      }
    });
    form.dataset.position = Number(draft.position || 0);
    form.dispatchEvent(new Event('draft-restored'));
  }
  async function flush() {
    clearTimeout(timer);
    if (blocked) throw new Error('conflict');
    if (running) return running;
    running = (async () => {
      while (dirty) {
        dirty = false;
        const sent = snapshot();
        const body = new URLSearchParams({
          _csrf: form.querySelector('[name="_csrf"]').value,
          phase, revision: String(revision), values: JSON.stringify(sent.values), position: String(sent.position)
        });
        try {
          const id = form.action.match(/\/quiz\/(\d+)\//)[1];
          const response = await fetch(`/quiz/${id}/entwurf`, {method: 'POST', body, keepalive: true});
          if (!response.ok) {
            if (response.status === 409) {
              blocked = true;
              message('Ein anderes Fenster oder ein neuer Prüfungsstand ist aktueller. Deine Eingaben bleiben lokal erhalten. Bitte lade diese Seite neu.');
            }
            throw new Error('save');
          }
          const result = await response.json();
          revision = result.revision;
          if (revisionInput) revisionInput.value = revision;
          if (JSON.stringify(snapshot()) !== JSON.stringify(sent)) dirty = true;
          cache(dirty);
          if (!dirty) message('In Karo gespeichert. Du kannst das Fenster schließen.');
        } catch (error) {
          dirty = true;
          cache(true);
          if (!blocked) {
            message('Noch nicht in Karo gespeichert. Eine Kopie bleibt auf diesem Gerät; wir versuchen es erneut.');
            timer = setTimeout(() => flush().catch(() => {}), 3000);
          }
          throw error;
        }
      }
    })().finally(() => { running = null; });
    return running;
  }
  function schedule() {
    dirty = true;
    cache(true);
    if (blocked) return;
    message('Wird gespeichert …');
    clearTimeout(timer);
    timer = setTimeout(() => flush().catch(() => {}), 300);
  }
  form.karoDraft = {schedule, flush};
  try {
    const draft = JSON.parse(localStorage.getItem(key) || 'null');
    if (draft) {
      // Read pre-autosave local copies too, so an upgrade cannot lose them.
      if (draft.answers) { draft.values = draft.answers; draft.unsynced = true; draft.revision = 0; }
      if (draft.unsynced && draft.values) {
        if (draft.revision === revision) { restore(draft); schedule(); }
        else if (JSON.stringify(draft.values) !== JSON.stringify(read())) {
          localConflict = draft;
          blocked = true;
          fields.forEach(field => { field.disabled = true; });
          message('Es gibt zusätzlich einen ungespeicherten lokalen Entwurf. Aktuell siehst du den Stand aus Karo.');
          for (const [text, useLocal] of [['Lokalen Entwurf übernehmen', true], ['Stand aus Karo behalten', false]]) {
            const button = document.createElement('button');
            button.type = 'button'; button.className = 'ghost'; button.textContent = text;
            button.dataset.draftChoice = '';
            button.addEventListener('click', () => {
              if (useLocal) restore(localConflict);
              blocked = false;
              fields.forEach(field => { field.disabled = false; });
              form.querySelectorAll('[data-draft-choice]').forEach(b => b.remove());
              if (useLocal) schedule(); else { dirty = false; cache(false); message('Stand aus Karo geladen.'); }
            });
            status?.after(button);
          }
        }
      }
    }
  } catch (_) {}
  form.addEventListener('input', schedule);
  form.addEventListener('change', schedule);
  window.addEventListener('online', () => { if (dirty) flush().catch(() => {}); });
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden' && dirty) flush().catch(() => {});
  });
  window.addEventListener('pagehide', () => { if (dirty) flush().catch(() => {}); });
  form.addEventListener('submit', async event => {
    if (event.defaultPrevented) return;
    event.preventDefault();
    if (blocked) return;
    dirty = true; cache(true);
    try {
      await flush();
      HTMLFormElement.prototype.submit.call(form);
    } catch (_) { /* Preserve the form and its local copy until saving succeeds. */ }
  });
})();
