/* All navigation and forms remain usable without JavaScript. */
(() => {
  'use strict';
  function revealHash() {
    let hash;
    try { hash = decodeURIComponent(location.hash.slice(1)); } catch (_) { return; }
    const aliases = {'lernstand-verlauf': 'ausfuehrlich', 'lernstand-uebersicht': 'ausfuehrlich', 'lerneinheit-material': 'materialsammlung'};
    const target = document.getElementById(aliases[hash] || hash);
    if (!target) return;
    for (let node = target; node; node = node.parentElement) {
      if (node.tagName === 'DETAILS') node.open = true;
    }
    target.scrollIntoView({block: 'start'});
  }
  revealHash();
  window.addEventListener('hashchange', revealHash);
  document.addEventListener('invalid', event => {
    for (let node = event.target.parentElement; node; node = node.parentElement) {
      if (node.tagName === 'DETAILS') node.open = true;
    }
  }, true);

  const quiz = document.querySelector('[data-draft-key]');
  const form = document.querySelector('[data-answer-form]');
  if (quiz && quiz.dataset.quizState !== 'bereit') {
    try { localStorage.removeItem(quiz.dataset.draftKey); } catch (_) {}
  }
  if (form && quiz) {
    const inputs = [...form.querySelectorAll('input[name^="antwort_"]')];
    const questions = [...form.querySelectorAll('[data-question]')];
    const previous = form.querySelector('[data-question-prev]');
    const next = form.querySelector('[data-question-next]');
    const submit = form.querySelector('[data-answer-submit]');
    const count = form.querySelector('[data-question-count]');
    const progress = form.querySelector('[data-question-progress]');
    const status = form.querySelector('[data-draft-status]');
    const key = quiz.dataset.draftKey;
    let index = 0;
    try {
      const draft = JSON.parse(localStorage.getItem(key) || '{}');
      if (Date.now() - draft.savedAt < 14 * 86400000 && draft.answers) {
        inputs.forEach(input => {
          if (!input.value && typeof draft.answers[input.name] === 'string') input.value = draft.answers[input.name].slice(0, 2000);
        });
        index = Math.max(0, inputs.findIndex(input => !input.value.trim()));
        status.textContent = 'Deine Antworten sind noch da.';
      }
    } catch (_) {}
    function save() {
      try {
        localStorage.setItem(key, JSON.stringify({savedAt: Date.now(), answers: Object.fromEntries(inputs.map(i => [i.name, i.value]))}));
        status.textContent = 'Deine Antworten sind auf diesem Gerät zwischengespeichert.';
      } catch (_) { status.textContent = 'Lass die Seite bis zur Abgabe geöffnet.'; }
    }
    function show(focus) {
      questions.forEach((q, i) => { q.hidden = i !== index; });
      previous.hidden = index === 0;
      next.hidden = index === questions.length - 1;
      submit.hidden = index !== questions.length - 1;
      count.textContent = `Frage ${index + 1} von ${questions.length}`;
      progress.value = index + 1;
      if (focus) questions[index].querySelector('.aufgabe').focus();
    }
    if (questions.length) {
      form.querySelector('[data-question-toolbar]').hidden = false;
      show(false);
      previous.addEventListener('click', () => { index--; show(true); });
      next.addEventListener('click', () => { save(); index++; show(true); });
      form.addEventListener('input', save);
      form.addEventListener('submit', event => {
        save();
        if (index < questions.length - 1) { event.preventDefault(); index++; show(true); }
      });
    }
  }
  document.querySelectorAll('[data-logout]').forEach(form => form.addEventListener('submit', () => {
    try { Object.keys(localStorage).filter(k => k.startsWith('karo-antworten-')).forEach(k => localStorage.removeItem(k)); } catch (_) {}
  }));
})();
