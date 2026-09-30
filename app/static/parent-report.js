/* Same-page drilldown; every link also works without JavaScript.
   Tiles open details in native <dialog>s; without JS they open via #anchor (:target). */
(() => {
  document.documentElement.classList.add('pr-js');
  let requestNumber = 0;
  let controller;
  const status = document.getElementById('report-status');
  const plainClick = event => event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
  function closeSheets() {
    document.querySelectorAll('#parent-report dialog.pr-sheet[open]').forEach(d => d.close());
  }
  async function show(url, push, focusKey) {
    const old = document.getElementById('parent-report');
    if (!old) return;
    const number = ++requestNumber;
    if (controller) controller.abort();
    controller = new AbortController();
    old.setAttribute('aria-busy', 'true');
    if (status) status.textContent = 'Bericht wird geladen.';
    try {
      const target = new URL(url, location.href);
      const endpoint = new URL('/eltern/bericht', location.origin);
      endpoint.search = target.search;
      const response = await fetch(endpoint, {signal:controller.signal, credentials:'same-origin', cache:'no-store'});
      if (!response.ok) throw new Error('load');
      const parsed = new DOMParser().parseFromString(await response.text(), 'text/html');
      const next = parsed.getElementById('parent-report');
      if (!next) throw new Error('load');
      if (number !== requestNumber) return;
      closeSheets();
      old.replaceWith(next);
      if (push) history.pushState({}, '', target.pathname + target.search);
      if (status) status.textContent = next.querySelector('.pr-range').textContent + ': Bericht aktualisiert.';
      const focus = focusKey ? [...next.querySelectorAll('[data-report-link]')].find(a => a.getAttribute('href') === focusKey && !a.closest('dialog')) : null;
      (focus || next.querySelector('.pr-switch a[aria-current]'))?.focus({preventScroll:true});
    } catch (error) {
      if (error.name === 'AbortError' || number !== requestNumber) return;
      closeSheets();
      const warning = old.querySelector('#report-error');
      warning.hidden = false;
      warning.textContent = 'Der Bericht konnte nicht geladen werden. Bitte erneut wählen oder die Seite neu laden.';
      if (status) status.textContent = '';
    } finally {
      if (number === requestNumber) document.getElementById('parent-report')?.removeAttribute('aria-busy');
    }
  }
  function openSheet(id, opener) {
    const sheet = document.getElementById(id);
    if (!sheet || typeof sheet.showModal !== 'function') return false;
    const from = opener.closest('dialog');
    if (from && from !== sheet) from.close();
    if (!sheet.open) sheet.showModal();
    sheet.scrollTop = 0;
    sheet.querySelector('.pr-close')?.focus({preventScroll:true});
    sheet.returnTo = from ? sheet.returnTo || from.returnTo : opener;
    return true;
  }
  document.addEventListener('click', event => {
    if (!plainClick(event)) return;
    const closer = event.target.closest('#parent-report [data-close]');
    if (closer) { event.preventDefault(); closer.closest('dialog')?.close(); return; }
    const opener = event.target.closest('#parent-report [data-dialog]');
    if (opener) { if (openSheet(opener.dataset.dialog, opener)) event.preventDefault(); return; }
    const sheet = event.target.closest('#parent-report dialog.pr-sheet');
    if (sheet && event.target === sheet) { sheet.close(); return; }  // click on the backdrop
    const anchor = event.target.closest('#parent-report a[data-report-link]');
    if (!anchor) return;
    event.preventDefault();
    show(anchor.href, true, anchor.getAttribute('href'));
  });
  document.addEventListener('close', event => {
    const sheet = event.target;
    if (!sheet.matches?.('dialog.pr-sheet') || !sheet.returnTo?.isConnected) return;
    // Der Fokus geht zurueck zu dem Element, das den Dialog geoeffnet hat —
    // aber nur, wenn ihn seither niemand selbst woandershin gesetzt hat.
    // `close` wird verzoegert zugestellt: wer den Dialog schliesst und sofort
    // etwas anderes anspringt, bekam den Fokus sonst wieder weggerissen, und
    // die naechste Taste landete auf dem alten Knopf statt auf dem neuen Ziel.
    const aktiv = document.activeElement;
    if (aktiv && aktiv !== document.body && !sheet.contains(aktiv)) return;
    sheet.returnTo.focus({preventScroll:true});
  }, true);
  window.addEventListener('popstate', () => show(location.href, false));
  // Post von zu Hause: ein Vorschlag landet im Textfeld (dort änderbar) und wählt sein Emoji.
  document.addEventListener('change', event => {
    const choice = event.target.closest?.('[data-post-form] input[name="vorschlag"]');
    if (!choice) return;
    const form = choice.form;
    form.elements.text.value = choice.value;
    const emoji = form.querySelector(`input[name="emoji"][value="${CSS.escape(choice.dataset.emoji || '')}"]`);
    if (emoji) emoji.checked = true;
    form.elements.text.dispatchEvent(new Event('input', {bubbles:true}));
  });
  document.addEventListener('input', event => {
    const box = event.target.closest?.('[data-post-form] textarea[name="text"]');
    const count = box?.form.querySelector('[data-post-count]');
    if (count) count.textContent = `${box.value.length} / ${box.maxLength} Zeichen`;
  });
  // Beim Öffnen steht der ausgewählte Vorschlag schon im Textfeld.
  document.addEventListener('click', event => {
    const opener = event.target.closest?.('#parent-report [data-dialog="pr-d-post"]');
    if (!opener) return;
    const form = document.querySelector('#pr-d-post [data-post-form]');
    const picked = form?.querySelector('input[name="vorschlag"]:checked');
    if (form && picked && !form.elements.text.value) {
      form.elements.text.value = picked.value;
      form.elements.text.dispatchEvent(new Event('input', {bubbles:true}));
    }
  });
})();
