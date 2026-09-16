/* Sprachnachricht fuer "Meine Welt": nimmt Ton auf (wird als Datei
   mitgeschickt) und versucht gleichzeitig, live mitzuschreiben, damit das
   Interesse als Text gespeichert wird — auch ohne Live-Erkennung bleibt die
   Aufnahme nutzbar, der Text kann dann von Hand ergaenzt werden. */
(function () {
  "use strict";
  var knopf = document.getElementById("aufnahmeknopf");
  var status_ = document.getElementById("aufnahmestatus");
  var textfeld = document.getElementById("interesse-text");
  var audioEingabe = document.getElementById("interesse-audio");
  var vorschau = document.getElementById("aufnahme-vorschau");
  if (!knopf) return;

  var Erkennung = window.SpeechRecognition || window.webkitSpeechRecognition;
  var erkennung = null;
  var rekorder = null, strom = null, teile = [];
  var laeuft = false;

  function starten() {
    teile = [];
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(function (s) {
        strom = s;
        rekorder = new MediaRecorder(s);
        rekorder.ondataavailable = function (e) { teile.push(e.data); };
        rekorder.onstop = function () {
          var blob = new Blob(teile, { type: "audio/webm" });
          var datei = new File([blob], "interesse.webm", { type: "audio/webm" });
          try {
            var uebertragung = new DataTransfer();
            uebertragung.items.add(datei);
            audioEingabe.files = uebertragung.files;
          } catch (_) { /* DataTransfer nicht verfuegbar — Aufnahme geht dann nicht mit */ }
          vorschau.src = URL.createObjectURL(blob);
          vorschau.hidden = false;
        };
        rekorder.start();
        laeuft = true;
        knopf.textContent = "Aufnahme beenden";
        status_.textContent = "Nimmt auf …";

        if (Erkennung) {
          erkennung = new Erkennung();
          erkennung.lang = "de-DE";
          erkennung.continuous = true;
          erkennung.interimResults = true;
          var anfangstext = textfeld.value;
          erkennung.onresult = function (ev) {
            var text = "";
            for (var i = 0; i < ev.results.length; i++) text += ev.results[i][0].transcript;
            textfeld.value = (anfangstext ? anfangstext + " " : "") + text.trim();
          };
          erkennung.onerror = function () {};
          try { erkennung.start(); } catch (_) {}
        }
      })
      .catch(function () {
        status_.textContent = "Mikrofon nicht verfügbar — du kannst auch einfach schreiben.";
      });
  }

  function stoppen() {
    laeuft = false;
    knopf.textContent = "Sprachnachricht aufnehmen";
    status_.textContent = "";
    if (rekorder && rekorder.state !== "inactive") rekorder.stop();
    if (strom) strom.getTracks().forEach(function (t) { t.stop(); });
    if (erkennung) { try { erkennung.stop(); } catch (_) {} }
  }

  knopf.addEventListener("click", function () {
    if (laeuft) stoppen(); else starten();
  });
})();
