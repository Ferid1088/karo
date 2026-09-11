/* Small enhancements; forms and navigation continue to work without JavaScript. */
(() => {
  'use strict';
  const themeKey = 'karo-farbwelt';
  const themes = ['lila', 'ozean', 'wiese', 'sonne', 'zuckerwatte', 'lava', 'dunkel'];
  const swatches = document.querySelectorAll('[data-farbe]');
  function applyTheme(theme) {
    if (!themes.includes(theme)) theme = 'lila';
    document.documentElement.dataset.themeColor = theme;
    swatches.forEach(button => {
      const selected = button.dataset.farbe === theme;
      button.classList.toggle('aktiv', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
  }
  try { applyTheme(localStorage.getItem(themeKey) || 'lila'); } catch (_) { applyTheme('lila'); }
  swatches.forEach(button => button.addEventListener('click', () => {
    applyTheme(button.dataset.farbe);
    try { localStorage.setItem(themeKey, button.dataset.farbe); } catch (_) { /* theme still works */ }
  }));
  const menu = document.querySelector('.account-menu');
  document.addEventListener('click', event => { if (menu && !menu.contains(event.target)) menu.open = false; });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menu && menu.open) {
      menu.open = false;
      menu.querySelector('summary').focus();
    }
  });

  const quiz = document.querySelector('[data-draft-key]');
  const form = document.querySelector('[data-answer-form]');
  if (quiz && !['offen', 'bereit'].includes(quiz.dataset.quizState)) {
    try { localStorage.removeItem(quiz.dataset.draftKey); } catch (_) { /* unavailable storage */ }
  }
  if (form && quiz) {
    const key = quiz.dataset.draftKey;
    const inputs = Array.from(form.querySelectorAll('input[name^="antwort_"]'));
    const status = form.querySelector('[data-draft-status]');
    let restored = false;
    try {
      const draft = JSON.parse(localStorage.getItem(key) || '{}');
      // Drafts expire after two weeks and never replace an answer already on the server.
      if (Date.now() - draft.savedAt < 14 * 86400000 && draft.answers) {
        inputs.forEach(input => {
          if (!input.value && typeof draft.answers[input.name] === 'string') {
            input.value = draft.answers[input.name].slice(0, 2000);
            restored = true;
          }
        });
      }
    } catch (_) { /* missing or invalid draft */ }
    function saveDraft() {
      try {
        const answers = Object.fromEntries(inputs.map(input => [input.name, input.value]));
        localStorage.setItem(key, JSON.stringify({savedAt: Date.now(), answers}));
        status.textContent = 'Zwischenstand in diesem Browser gespeichert.';
      } catch (_) {
        status.textContent = 'Speichern im Browser ist nicht möglich. Lass diese Seite bis zur Abgabe geöffnet.';
      }
    }
    status.textContent = restored ? 'Dein gespeicherter Zwischenstand ist wieder da.' : 'Deine Antworten werden beim Schreiben in diesem Browser gespeichert.';
    form.addEventListener('input', saveDraft);
    form.addEventListener('submit', saveDraft); // Clear only after the server accepts the answers.
    const questions = Array.from(form.querySelectorAll('[data-question]'));
    const previous = form.querySelector('[data-question-prev]');
    const next = form.querySelector('[data-question-next]');
    const submit = form.querySelector('[data-answer-submit]');
    const count = form.querySelector('[data-question-count]');
    const progress = form.querySelector('[data-question-progress]');
    let index = Math.max(0, inputs.findIndex(input => !input.value.trim()));
    function showQuestion(focus) {
      questions.forEach((question, i) => { question.hidden = i !== index; });
      previous.hidden = index === 0;
      next.hidden = index === questions.length - 1;
      submit.hidden = index !== questions.length - 1;
      count.textContent = `Frage ${index + 1} von ${questions.length}`;
      progress.value = index + 1;
      if (focus) questions[index].querySelector('.aufgabe').focus();
    }
    if (questions.length) {
      form.querySelector('[data-question-toolbar]').hidden = false;
      showQuestion(false);
      previous.addEventListener('click', () => { index--; showQuestion(true); });
      next.addEventListener('click', () => { saveDraft(); index++; showQuestion(true); });
      form.addEventListener('submit', event => {
        if (index < questions.length - 1) { event.preventDefault(); index++; showQuestion(true); }
      });
    }
  }
  document.querySelectorAll('[data-logout]').forEach(form => form.addEventListener('submit', () => {
    try {
      Object.keys(localStorage).filter(key => key.startsWith('karo-antworten-')).forEach(key => localStorage.removeItem(key));
    } catch (_) { /* unavailable storage */ }
  }));
  document.querySelectorAll('[data-review-form] .review-decision').forEach(decision => {
    decision.addEventListener('change', event => {
      if (event.target.name.startsWith('urteil_')) {
        decision.querySelector('.error-detail').open = event.target.value === 'nein';
      }
    });
  });

  if (document.querySelector('[data-auto-refresh]')) {
    const version = document.querySelector('[data-work-version]').dataset.workVersion;
    let dirty = false;
    let tries = 0;
    document.addEventListener('input', () => { dirty = true; });
    document.addEventListener('change', () => { dirty = true; });
    async function refresh() {
      if (!document.hidden && !dirty) {
        try {
          const response = await fetch('/ui/status', {headers: {Accept: 'application/json'}, cache: 'no-store'});
          if (!response.ok || response.redirected) throw new Error('Status unavailable');
          const result = await response.json();
          if (result.version !== version) { location.reload(); return; }
          tries = 0;
        } catch (_) {
          tries++;
          document.querySelectorAll('[data-refresh-status]').forEach(el => {
            el.textContent = 'Verbindung unterbrochen. Karo versucht es automatisch erneut.';
          });
        }
      }
      setTimeout(refresh, Math.min(30000, 5000 * (tries + 1)));
    }
    setTimeout(refresh, 5000);
  }
})();
