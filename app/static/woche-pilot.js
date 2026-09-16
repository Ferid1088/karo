(() => {
  document.querySelector('[data-apply-suggestion]')?.addEventListener('click', () => {
    const option = document.querySelector('[data-weekly-suggestions]').selectedOptions[0];
    if (!option.dataset.goal) return;
    document.querySelector('[name="goal"]').value = option.dataset.goal;
    document.querySelector('[name="step"]').value = option.dataset.step;
  });
  document.querySelectorAll('[data-weekly-review]').forEach(form => {
    form.querySelector('[data-review-save]').hidden = true;
    form.addEventListener('change', () => {
      if (form.querySelector('[name="feeling"]:checked') && form.querySelector('[name="wish"]:checked')) form.requestSubmit();
    });
  });
  document.querySelectorAll('.weekly form').forEach(form => {
    form.addEventListener('submit', event => {
      if (form.dataset.saving) { event.preventDefault(); return; }
      form.dataset.saving = 'true';
      // Keep the clicked button's name/value in the submitted form.
      form.querySelectorAll('button').forEach(button => button.setAttribute('aria-disabled', 'true'));
    });
  });
  window.addEventListener('pageshow', () => document.querySelectorAll('.weekly form').forEach(form => {
    delete form.dataset.saving;
    form.querySelectorAll('button').forEach(button => button.removeAttribute('aria-disabled'));
  }));
})();
