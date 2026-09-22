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
    }
  }
  [actual, focus].forEach(function (input) { if (input) input.addEventListener('input', update); });
  update();

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
    function durationChanged() {
      var selected = durationForm.querySelector('[name="duration"]:checked');
      custom.hidden = !selected || selected.value !== 'custom';
      custom.querySelector('input').required = !custom.hidden;
    }
    durationForm.addEventListener('change', durationChanged); durationChanged();
  }
  var customMinutes = document.querySelector('[data-custom-minutes]');
  if (customMinutes) customMinutes.addEventListener('input', function () {
    var radios = document.querySelectorAll('input[name="minutes"]');
    var customRadio = radios[radios.length - 1]; customRadio.value = customMinutes.value; customRadio.checked = true;
  });
})();
