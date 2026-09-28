/* Search lives in the dropdown; the native select remains a no-JS fallback. */
document.querySelectorAll('[data-topic-picker]').forEach(function (form) {
  const select = form.querySelector('select');
  const dropdown = form.querySelector('[data-topic-dropdown]');
  const trigger = dropdown.querySelector('button');
  const value = dropdown.querySelector('[data-topic-value]');
  const panel = dropdown.querySelector('.topic-dropdown-panel');
  const search = dropdown.querySelector('input');
  const list = dropdown.querySelector('[role="listbox"]');
  const status = dropdown.querySelector('[role="status"]');
  const submit = form.querySelector('button[type="submit"]');
  const topics = Array.from(select.options).filter(function (option) { return option.value; });
  let matches = [];
  let active = -1;

  function normalize(text) {
    return text.toLocaleLowerCase('de').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/ß/g, 'ss').replace(/ae/g, 'a').replace(/oe/g, 'o').replace(/ue/g, 'u');
  }
  function close(restoreFocus) {
    panel.hidden = true;
    trigger.setAttribute('aria-expanded', 'false');
    search.setAttribute('aria-expanded', 'false');
    search.removeAttribute('aria-activedescendant');
    if (restoreFocus) trigger.focus();
  }
  function highlight(index) {
    active = index;
    Array.from(list.children).forEach(function (item, i) {
      item.classList.toggle('is-active', i === active);
    });
    const item = list.children[active];
    if (item) {
      search.setAttribute('aria-activedescendant', item.id);
      item.scrollIntoView({block: 'nearest'});
    } else search.removeAttribute('aria-activedescendant');
  }
  function choose(index) {
    if (!matches[index]) return;
    select.value = matches[index].value;
    value.textContent = select.value;
    trigger.setAttribute('aria-label', 'Thema auswählen: ' + select.value);
    submit.disabled = false;
    close(true);
  }
  function filter() {
    const words = normalize(search.value).trim().split(/\s+/).filter(Boolean);
    matches = topics.filter(function (option) {
      const label = normalize(option.textContent);
      return words.every(function (word) { return label.includes(word); });
    });
    list.replaceChildren();
    matches.forEach(function (option, index) {
      const item = document.createElement('div');
      item.id = list.id + '-' + index;
      item.setAttribute('role', 'option');
      item.setAttribute('aria-selected', String(option.value === select.value));
      item.textContent = option.textContent;
      item.addEventListener('mousedown', function (event) { event.preventDefault(); });
      item.addEventListener('click', function () { choose(index); });
      list.append(item);
    });
    highlight(-1);
    status.textContent = matches.length
      ? matches.length + (matches.length === 1 ? ' Thema zur Auswahl' : ' Themen zur Auswahl')
      : 'Kein Thema gefunden. Versuche ein anderes Suchwort.';
  }
  function open() {
    panel.hidden = false;
    trigger.setAttribute('aria-expanded', 'true');
    search.setAttribute('aria-expanded', 'true');
    search.value = '';
    filter();
    search.focus();
  }
  trigger.addEventListener('click', function () { if (panel.hidden) open(); else close(false); });
  trigger.addEventListener('keydown', function (event) {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      open();
      highlight(event.key === 'ArrowDown' ? 0 : matches.length - 1);
    }
  });
  search.addEventListener('input', filter);
  search.addEventListener('keydown', function (event) {
    if (event.isComposing) return;
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      if (matches.length) highlight(event.key === 'ArrowDown'
        ? Math.min(active + 1, matches.length - 1)
        : active < 0 ? matches.length - 1 : Math.max(0, active - 1));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      if (active >= 0) choose(active);
      else if (matches.length === 1) choose(0);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      close(true);
    }
  });
  dropdown.addEventListener('focusout', function (event) {
    if (!dropdown.contains(event.relatedTarget)) close(false);
  });
  document.addEventListener('pointerdown', function (event) {
    if (!dropdown.contains(event.target)) close(false);
  });
  form.addEventListener('submit', function (event) {
    if (!select.value) { event.preventDefault(); open(); }
  });
  form.querySelector('[data-topic-native]').hidden = true;
  select.required = false;
  dropdown.hidden = false;
  if (select.value) value.textContent = select.value;
  submit.disabled = !select.value;
});
