(function () {
  var actual = document.querySelector('[data-range="actual"]');
  var focus = document.querySelector('[data-range="focus"]');
  function update() {
    if (actual) {
      var out = document.querySelector('[data-actual-output]');
      var percent = document.querySelector('[data-percent-output]');
      var planned = Number(document.querySelector('.selected-goal small').textContent.match(/\d+/)[0]);
      if (out) out.textContent = actual.value;
      if (percent) percent.textContent = Math.round(Number(actual.value) / planned * 100) + ' %';
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
    tabs.querySelectorAll('[data-tab]').forEach(function (button) {
      button.addEventListener('click', function () {
        tabs.querySelectorAll('[data-tab]').forEach(function (b) { b.classList.toggle('active', b === button); });
        document.querySelectorAll('[data-plan-panel]').forEach(function (panel) {
          panel.classList.toggle('active', panel.dataset.planPanel === button.dataset.tab);
        });
      });
    });
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
