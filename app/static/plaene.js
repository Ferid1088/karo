(function () {
  var clock = document.querySelector('[data-plans-clock]');
  if (clock) {
    var clockDate = clock.querySelector('[data-clock-date]');
    var clockTime = clock.querySelector('[data-clock-time]');
    var dateFormatter = new Intl.DateTimeFormat('de-DE', {
      weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric'
    });
    var timeFormatter = new Intl.DateTimeFormat('de-DE', {
      hour: '2-digit', minute: '2-digit'
    });
    function updateClock() {
      var now = new Date();
      clock.dateTime = now.toISOString();
      clockDate.textContent = dateFormatter.format(now);
      clockTime.textContent = timeFormatter.format(now) + ' Uhr';
    }
    updateClock();
    window.setInterval(updateClock, 30000);
  }

  var actual = document.querySelector('[data-range="actual"]');
  var focus = document.querySelector('[data-range="focus"]');
  function update() {
    if (actual) {
      var out = document.querySelector('[data-actual-output]');
      var percent = document.querySelector('[data-percent-output]');
      var planned = Number(document.querySelector('.selected-goal small').textContent.match(/\d+/)[0]);
      // Schon fruehere Abschnitte des Tages zaehlen mit, sonst springt die Anzeige zurueck.
      var live = percent && percent.closest('.live-result');
      var done = live ? Number(live.dataset.doneMinutes || 0) : 0;
      if (out) out.textContent = actual.value;
      if (percent) percent.textContent = Math.round((done + Number(actual.value)) / planned * 100) + ' %';
    }
    if (focus) {
      var focusOut = document.querySelector('[data-focus-output]');
      if (focusOut) focusOut.textContent = focus.value;
      document.querySelectorAll('[data-focus-mark]').forEach(function (mark) {
        mark.classList.toggle('active', Number(mark.dataset.focusMark) === Number(focus.value));
        mark.setAttribute('aria-pressed', Number(mark.dataset.focusMark) === Number(focus.value) ? 'true' : 'false');
      });
    }
  }
  [actual, focus].forEach(function (input) { if (input) input.addEventListener('input', update); });
  document.querySelectorAll('[data-focus-mark]').forEach(function (mark) {
    mark.addEventListener('click', function () {
      if (!focus) return;
      focus.value = mark.dataset.focusMark;
      focus.dispatchEvent(new Event('input', { bubbles: true }));
    });
  });
  update();

  var completionForm = document.querySelector('[data-completion-form][data-parent-feedback]');
  var roleNotice = document.querySelector('[data-role-notice]');
  if (completionForm && roleNotice) {
    var roleNoticeButtons = roleNotice.querySelectorAll('[data-role-notice-close]');
    var saveButton = completionForm.querySelector('button[type="submit"]');
    function openRoleNotice() {
      roleNotice.hidden = false;
      roleNoticeButtons[0].focus();
    }
    function closeRoleNotice() {
      roleNotice.hidden = true;
      if (saveButton) saveButton.focus();
    }
    completionForm.addEventListener('submit', function (event) {
      event.preventDefault();
      openRoleNotice();
    });
    roleNoticeButtons.forEach(function (button) { button.addEventListener('click', closeRoleNotice); });
    roleNotice.addEventListener('click', function (event) {
      if (event.target === roleNotice) closeRoleNotice();
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && !roleNotice.hidden) closeRoleNotice();
    });
    if (!roleNotice.hidden) roleNoticeButtons[0].focus();
  }

  document.querySelectorAll('[data-plan-tabs]').forEach(function (tabs) {
    // Panels liegen im umschliessenden Bereich, damit mehrere Reiter-Gruppen sich nicht stoeren.
    var scope = tabs.closest('[data-plan-tab-scope]') || document;
    var buttons = tabs.querySelectorAll('[data-tab]');
    function activate(name, updateHash) {
      var selected = tabs.querySelector('[data-tab="' + name + '"]');
      if (!selected) return false;
      buttons.forEach(function (b) {
        b.classList.toggle('active', b === selected);
        b.setAttribute('aria-selected', b === selected ? 'true' : 'false');
      });
      scope.querySelectorAll('[data-plan-panel]').forEach(function (panel) {
        panel.classList.toggle('active', panel.dataset.planPanel === name);
      });
      if (updateHash) history.replaceState(null, '', '#' + name);
      return true;
    }
    buttons.forEach(function (button) {
      button.addEventListener('click', function () {
        activate(button.dataset.tab, true);
      });
    });
    if (!activate(location.hash.slice(1), false) && buttons.length) {
      activate(buttons[0].dataset.tab, false);
    }
  });

  var durationForm = document.querySelector('[data-duration-form]');
  if (durationForm) {
    var custom = durationForm.querySelector('[data-custom-date]');
    var startDate = durationForm.querySelector('[data-start-date]');
    function durationChanged() {
      var selected = durationForm.querySelector('[name="duration"]:checked');
      custom.hidden = !selected || selected.value !== 'custom';
      custom.querySelector('input').required = !custom.hidden;
      if (startDate && startDate.value) {
        custom.querySelector('input').min = startDate.value;
        if (custom.querySelector('input').value && custom.querySelector('input').value < startDate.value) {
          custom.querySelector('input').value = '';
        }
      }
    }
    durationForm.addEventListener('change', durationChanged); durationChanged();
  }
  var customMinutes = document.querySelector('[data-custom-minutes]');
  if (customMinutes) customMinutes.addEventListener('input', function () {
    var radios = document.querySelectorAll('input[name="minutes"]');
    var customRadio = radios[radios.length - 1]; customRadio.value = customMinutes.value; customRadio.checked = true;
  });

  var deleteForm = document.querySelector('[data-delete-goal-form]');
  var deleteDialog = document.querySelector('[data-delete-goal-dialog]');
  if (deleteForm && deleteDialog) {
    var deleteTrigger = deleteForm.querySelector('button[name="action"]');
    var deleteCancel = deleteDialog.querySelector('[data-delete-cancel]');
    var deleteConfirm = deleteDialog.querySelector('[data-delete-confirm]');
    deleteForm.addEventListener('submit', function (event) {
      if (deleteForm.dataset.confirmed === 'yes') return;
      event.preventDefault();
      deleteDialog.hidden = false;
      deleteCancel.focus();
    });
    deleteCancel.addEventListener('click', function () {
      deleteDialog.hidden = true;
      deleteTrigger.focus();
    });
    deleteConfirm.addEventListener('click', function () {
      deleteForm.dataset.confirmed = 'yes';
      deleteDialog.hidden = true;
      deleteForm.requestSubmit(deleteTrigger);
    });
    deleteDialog.addEventListener('click', function (event) {
      if (event.target === deleteDialog) deleteCancel.click();
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && !deleteDialog.hidden) deleteCancel.click();
    });
  }
})();
