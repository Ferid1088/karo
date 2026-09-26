/* Private browser-only helpers for Meine Welt.
   No browser speech-to-text, analytics, model API or third-party request. */
(function () {
  "use strict";

  function two(n) { return String(n).padStart(2, "0"); }

  document.querySelectorAll("[data-photo-input]").forEach(function (input) {
    var max = Math.max(0, Number(input.dataset.photoMax || 0));
    var status = input.parentElement.querySelector("[data-photo-status]") ||
                 document.querySelector("[data-photo-status]");
    input.addEventListener("change", function () {
      var count = input.files ? input.files.length : 0;
      if (count > max) {
        input.value = "";
        if (status) status.textContent = "Heute sind nur noch " + max + " Foto(s) möglich.";
        return;
      }
      if (status) status.textContent = count ? count + " Foto(s) ausgewählt." : "";
    });
  });

  document.querySelectorAll("[data-open-date]").forEach(function (button) {
    button.addEventListener("click", function () {
      var form = button.closest("form");
      var input = form && form.querySelector("[data-open-date-input]");
      if (input) input.value = button.dataset.openDate;
    });
  });

  document.querySelectorAll("[data-world-recorder]").forEach(function (form) {
    var button = form.querySelector("[data-record-button]");
    var input = form.querySelector("[data-audio-input]");
    var durationInput = form.querySelector("[data-audio-duration]");
    var time = form.querySelector("[data-record-time]");
    var status = form.querySelector("[data-record-status]");
    var preview = form.querySelector("[data-audio-preview]");
    if (!button || !input || !durationInput || !time || !preview) return;

    var maximum = Math.min(60, Math.max(0, Number(form.dataset.maxSeconds || 0)));
    var recorder = null, stream = null, chunks = [], timer = null;
    var startedAt = 0, elapsed = 0, objectUrl = null;

    function setTime(seconds) {
      seconds = Math.max(0, Math.min(maximum, Math.ceil(seconds)));
      time.textContent = two(Math.floor(seconds / 60)) + ":" + two(seconds % 60);
    }

    function preferredType() {
      if (!window.MediaRecorder) return "";
      var types = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
      for (var i = 0; i < types.length; i++) {
        if (!MediaRecorder.isTypeSupported || MediaRecorder.isTypeSupported(types[i])) return types[i];
      }
      return "";
    }

    function extension(type) {
      if (type.indexOf("mp4") !== -1) return "m4a";
      if (type.indexOf("ogg") !== -1) return "ogg";
      return "webm";
    }

    function cleanupStream() {
      if (timer) { clearInterval(timer); timer = null; }
      if (stream) {
        stream.getTracks().forEach(function (track) { track.stop(); });
        stream = null;
      }
    }

    function stopRecording() {
      if (recorder && recorder.state !== "inactive") recorder.stop();
      cleanupStream();
    }

    function tick() {
      elapsed = Math.min(maximum, (Date.now() - startedAt) / 1000);
      setTime(elapsed);
      if (elapsed >= maximum) stopRecording();
    }

    function startRecording() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
        if (status) status.textContent = "Aufnahme wird von diesem Browser nicht unterstützt.";
        return;
      }
      if (maximum <= 0) {
        if (status) status.textContent = "Für heute ist die Audio-Minute schon aufgebraucht.";
        return;
      }

      navigator.mediaDevices.getUserMedia({audio:true}).then(function (newStream) {
        stream = newStream;
        chunks = [];
        elapsed = 0;
        var type = preferredType();
        recorder = type ? new MediaRecorder(stream, {mimeType:type}) : new MediaRecorder(stream);

        recorder.addEventListener("dataavailable", function (event) {
          if (event.data && event.data.size) chunks.push(event.data);
        });
        recorder.addEventListener("stop", function () {
          cleanupStream();
          var seconds = Math.max(1, Math.min(maximum, Math.ceil(elapsed || ((Date.now()-startedAt)/1000))));
          var mime = recorder.mimeType || type || "audio/webm";
          var blob = new Blob(chunks, {type:mime});
          var file = new File([blob], "aufnahme." + extension(mime), {type:mime});
          try {
            var transfer = new DataTransfer();
            transfer.items.add(file);
            input.files = transfer.files;
          } catch (e) {
            if (status) status.textContent = "Die Aufnahme kann in diesem Browser nicht angehängt werden.";
            return;
          }
          durationInput.value = String(seconds);
          if (objectUrl) URL.revokeObjectURL(objectUrl);
          objectUrl = URL.createObjectURL(blob);
          preview.src = objectUrl;
          preview.hidden = false;
          button.textContent = "Neu aufnehmen";
          if (status) status.textContent = seconds + " Sekunden aufgenommen.";
          setTime(seconds);
        });

        recorder.start(250);
        startedAt = Date.now();
        button.textContent = "Aufnahme stoppen";
        if (status) status.textContent = "Nimmt nur auf diesem Gerät auf …";
        setTime(0);
        timer = setInterval(tick, 200);
      }).catch(function () {
        if (status) status.textContent = "Mikrofon nicht verfügbar. Du kannst auch schreiben oder ein Foto wählen.";
      });
    }

    button.addEventListener("click", function () {
      if (recorder && recorder.state === "recording") stopRecording();
      else startRecording();
    });

    window.addEventListener("beforeunload", cleanupStream);
  });
})();
