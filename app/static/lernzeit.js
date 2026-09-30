/* Lernzeit messen.
 *
 * Solange eine Lernseite offen und sichtbar ist, meldet sie sich im Takt.
 * Der Server verlaengert damit das laufende Stueck; bleiben die Schlaege
 * aus, endet es von selbst. Gezaehlt wird nur, was zwischen zwei Schlaegen
 * wirklich verging — wer den Tab wegklickt, sammelt keine Zeit.
 *
 * Bewusst anspruchslos: kein Zustand im Browser, keine Genauigkeit unter
 * einem Takt, und ein fehlgeschlagener Schlag wird still verschluckt. Eine
 * Messung darf nie eine Lernseite stoeren.
 */
(function () {
  'use strict';
  var script = document.currentScript || document.querySelector('script[data-lernzeit]');
  if (!script) { return; }
  var feld = script.getAttribute('data-feld');
  var token = script.getAttribute('data-token');
  var takt = parseInt(script.getAttribute('data-takt'), 10) || 30;
  if (!feld || !token) { return; }

  var uhr = null;

  function schlagen() {
    if (document.visibilityState === 'hidden') { return; }
    var daten = new FormData();
    daten.append(feld, token);
    daten.append('pfad', location.pathname);
    try {
      fetch('/lernen/zeit', {
        method: 'POST', body: daten, credentials: 'same-origin',
        cache: 'no-store', keepalive: true
      }).catch(function () {});
    } catch (e) { /* Eine Lernseite steht nie wegen der Messung still. */ }
  }

  function starten() {
    if (uhr !== null) { return; }
    schlagen();
    uhr = window.setInterval(schlagen, takt * 1000);
  }

  function anhalten() {
    if (uhr === null) { return; }
    window.clearInterval(uhr);
    uhr = null;
  }

  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') { anhalten(); } else { starten(); }
  });
  window.addEventListener('pagehide', anhalten);
  starten();
})();
