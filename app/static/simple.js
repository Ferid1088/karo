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
  if (form && quiz) {
    const questions = [...form.querySelectorAll('[data-question]')];
    const previous = form.querySelector('[data-question-prev]');
    const next = form.querySelector('[data-question-next]');
    const submit = form.querySelector('[data-answer-submit]');
    const count = form.querySelector('[data-question-count]');
    const progress = form.querySelector('[data-question-progress]');
    let index = Math.max(0, Math.min(Number(quiz.dataset.draftPosition || 0), questions.length - 1));
    function save() {
      if (form.karoDraft) form.karoDraft.schedule();
    }
    function show(focus) {
      form.dataset.position = index;
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
      previous.addEventListener('click', () => { index--; show(true); save(); });
      next.addEventListener('click', () => { index++; show(true); save(); });
      form.addEventListener('draft-restored', () => {
        index = Math.max(0, Math.min(Number(form.dataset.position || 0), questions.length - 1));
        show(false);
      });
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
