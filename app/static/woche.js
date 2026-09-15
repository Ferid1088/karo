/* „Meine Woche" — Stoppuhr, Timer, Clip.
 *
 * Alles laeuft im Browser. Der Clip wird nicht hochgeladen und nicht
 * gespeichert: er existiert, solange die Seite offen ist, und ist danach weg.
 * Das ist keine Sparmassnahme, sondern die Zusage an das Kind.
 */
(function () {
  "use strict";

  var karte = document.getElementById("formkarte");
  if (!karte) return;

  var art = karte.dataset.form || "einfach";
  var minuten = parseInt(karte.dataset.minuten || "8", 10);
  var uhr = document.getElementById("uhr");

  // ---------------------------------------------------------------- Speedrun
  if (art === "speedrun") {
    var start = null, timer = null;
    var startknopf = document.getElementById("startknopf");
    var fertigknopf = document.getElementById("fertigknopf");
    var feld = document.getElementById("sekunden");

    startknopf.addEventListener("click", function () {
      if (timer) return;
      start = Date.now();
      startknopf.hidden = true;
      fertigknopf.hidden = false;
      timer = setInterval(function () {
        var s = (Date.now() - start) / 1000;
        uhr.textContent = s.toFixed(1).replace(".", ",");
      }, 100);
    });

    fertigknopf.addEventListener("click", function () {
      if (!start) return;
      clearInterval(timer);
      feld.value = Math.max(1, Math.round((Date.now() - start) / 1000));
    });
    return;
  }

  // -------------------------------------------------------------------- Clip
  if (art === "clip") {
    var clipknopf = document.getElementById("clipknopf");
    var vorschau = document.getElementById("vorschau");
    var rec = null, strom = null, teile = [], rest = 60, lauf = null;

    clipknopf.addEventListener("click", function () {
      if (rec) { stopp(); return; }
      navigator.mediaDevices.getUserMedia({audio: true, video: true})
        .then(function (s) {
          strom = s;
          teile = [];
          rec = new MediaRecorder(s);
          rec.ondataavailable = function (e) { teile.push(e.data); };
          rec.onstop = function () {
            vorschau.src = URL.createObjectURL(new Blob(teile));
            vorschau.hidden = false;
          };
          rec.start();
          clipknopf.textContent = "fertig";
          rest = 60;
          uhr.textContent = rest;
          lauf = setInterval(function () {
            rest -= 1;
            uhr.textContent = rest;
            if (rest <= 0) stopp();
          }, 1000);
        })
        .catch(function () {
          uhr.textContent = "—";
          clipknopf.textContent = "geht hier nicht";
          clipknopf.disabled = true;
        });
    });

    function stopp() {
      if (lauf) clearInterval(lauf);
      if (rec && rec.state !== "inactive") rec.stop();
      if (strom) strom.getTracks().forEach(function (t) { t.stop(); });
      rec = null;
      clipknopf.textContent = "nochmal";
    }
    return;
  }

  // ------------------------------------------------------------------ Timer
  var knopf = document.getElementById("startknopf");
  var rest2 = minuten * 60, lauf2 = null;

  function zeige() {
    var m = Math.floor(rest2 / 60), s = rest2 % 60;
    uhr.textContent = m + ":" + (s < 10 ? "0" : "") + s;
  }

  knopf.addEventListener("click", function () {
    if (lauf2) { clearInterval(lauf2); lauf2 = null; knopf.textContent = "weiter"; return; }
    knopf.textContent = "Pause";
    lauf2 = setInterval(function () {
      rest2 -= 1;
      zeige();
      if (rest2 <= 0) {
        clearInterval(lauf2);
        lauf2 = null;
        uhr.textContent = "fertig";
        knopf.hidden = true;
      }
    }, 1000);
  });
})();
