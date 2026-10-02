/* Blätter auf dem Gerät lesen — das Bild verlässt den Rechner nicht.
 *
 * Karo hat Fotos von Schulblättern an ein Modell geschickt. Ein Foto trägt
 * mehr als das, was jemand zeigen wollte, und es lässt sich nicht säubern wie
 * ein Text. Also wird hier gelesen: Tesseract als WASM im Browser, pdf.js für
 * PDFs, beides von unserem eigenen Server. Zum Server geht nur Text, gefiltert
 * und ohne unsichere Wörter.
 *
 * Alles hier ist Ergänzung: ohne JavaScript, ohne WASM oder mit einem alten
 * Browser bleibt das Formular ein Formular, und der Text wird eingetippt.
 */
(function () {
  "use strict";

  const OCR = "/static/ocr/";
  const PDFJS = "/static/pdfjs/";
  const SPRACHEN = "deu+eng";
  const MAX_SEITEN = 20;
  const MAX_KANTE = 2000;          // größer bringt nichts und dauert lang
  const MIN_KONFIDENZ = 60;        // Wörter darunter sind geraten
  const MIN_ZEICHEN = 40;          // weniger ist kein Blatt, sondern ein Versuch

  function el(name, klasse, text) {
    const k = document.createElement(name);
    if (klasse) k.className = klasse;
    if (text != null) k.textContent = text;
    return k;
  }

  /* ---------------------------------------------------------------- Bild */

  // EXIF-Drehung: iPhones speichern das Bild liegend und merken sich die
  // Drehung daneben. Ohne das steht der Text quer und Tesseract liest nichts.
  async function alsBitmap(datei) {
    if (window.createImageBitmap) {
      try {
        return await createImageBitmap(datei, { imageOrientation: "from-image" });
      } catch (e) { /* ältere Safari-Versionen: unten weiter */ }
    }
    return await new Promise((fertig, fehler) => {
      const bild = new Image();
      bild.onload = () => fertig(bild);
      bild.onerror = () => fehler(new Error("Bild nicht lesbar"));
      bild.src = URL.createObjectURL(datei);
    });
  }

  function aufbereiten(quelle, kopfProzent) {
    const breite = quelle.width || quelle.naturalWidth;
    const hoehe = quelle.height || quelle.naturalHeight;
    const faktor = Math.min(1, MAX_KANTE / Math.max(breite, hoehe));
    const kopf = Math.round(hoehe * Math.min(kopfProzent, 25) / 100);
    const c = document.createElement("canvas");
    c.width = Math.round(breite * faktor);
    c.height = Math.round((hoehe - kopf) * faktor);
    const ctx = c.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(quelle, 0, kopf, breite, hoehe - kopf, 0, 0, c.width, c.height);

    // Graustufen und etwas mehr Kontrast: ein abfotografiertes Blatt ist fast
    // nie gleichmäßig beleuchtet, und Tesseract liest Grau schlechter als
    // Schwarz auf Weiß.
    const bild = ctx.getImageData(0, 0, c.width, c.height);
    const p = bild.data;
    for (let i = 0; i < p.length; i += 4) {
      const grau = 0.299 * p[i] + 0.587 * p[i + 1] + 0.114 * p[i + 2];
      const hart = Math.max(0, Math.min(255, (grau - 128) * 1.4 + 128));
      p[i] = p[i + 1] = p[i + 2] = hart;
    }
    ctx.putImageData(bild, 0, 0);
    return c;
  }

  async function heicUmwandeln(datei, melde) {
    melde("iPhone-Foto wird umgewandelt …");
    await laden(OCR + "heic2any.min.js");
    const blob = await window.heic2any({ blob: datei, toType: "image/jpeg", quality: 0.9 });
    return Array.isArray(blob) ? blob[0] : blob;
  }

  /* ---------------------------------------------------------------- Laden */

  const geladen = {};
  function laden(url) {
    if (geladen[url]) return geladen[url];
    geladen[url] = new Promise((fertig, fehler) => {
      const s = document.createElement("script");
      s.src = url;
      s.onload = fertig;
      s.onerror = () => fehler(new Error("Datei nicht ladbar: " + url));
      document.head.appendChild(s);
    });
    return geladen[url];
  }

  let werker = null;
  async function tesseract(melde) {
    if (werker) return werker;
    await laden(OCR + "tesseract.min.js");
    melde("Lesehilfe wird geladen (einmalig, dann aus dem Zwischenspeicher) …");
    werker = await window.Tesseract.createWorker(SPRACHEN, 1, {
      workerPath: OCR + "worker.min.js",
      corePath: OCR,
      langPath: OCR,
      gzip: false,
      logger: (m) => {
        if (m.status === "recognizing text") {
          melde("Blatt wird gelesen … " + Math.round(m.progress * 100) + " %");
        }
      },
    });
    return werker;
  }

  /* ------------------------------------------------------------ Erkennen */

  // Unsichere Wörter fliegen raus. Das filtert nebenbei Handschrift: die liest
  // Tesseract fast nie sicher, und geratene Wörter im Lernmaterial wären
  // schlimmer als eine Lücke.
  function sicherenTextNehmen(daten) {
    const woerter = (daten.words || []).filter((w) => w.confidence >= MIN_KONFIDENZ);
    if (!woerter.length) return { text: "", konfidenz: 0 };
    const zeilen = [];
    let aktuell = null;
    woerter.forEach((w) => {
      const y = w.bbox ? w.bbox.y0 : 0;
      if (!aktuell || Math.abs(y - aktuell.y) > 12) {
        aktuell = { y: y, teile: [] };
        zeilen.push(aktuell);
      }
      aktuell.teile.push(w.text);
    });
    const mittel = woerter.reduce((s, w) => s + w.confidence, 0) / woerter.length;
    return { text: zeilen.map((z) => z.teile.join(" ")).join("\n"), konfidenz: mittel / 100 };
  }

  async function bildLesen(canvas, melde) {
    const w = await tesseract(melde);
    const ergebnis = await w.recognize(canvas, {}, { text: true, words: true });
    return sicherenTextNehmen(ergebnis.data);
  }

  /* ------------------------------------------------------------------ PDF */

  async function pdfLesen(datei, kopfProzent, melde) {
    melde("PDF wird geöffnet …");
    const pdfjs = await import(PDFJS + "pdf.min.mjs");
    pdfjs.GlobalWorkerOptions.workerSrc = PDFJS + "pdf.worker.min.mjs";
    const doc = await pdfjs.getDocument({ data: await datei.arrayBuffer() }).promise;
    const seiten = Math.min(doc.numPages, MAX_SEITEN);
    const ergebnisse = [];
    for (let n = 1; n <= seiten; n++) {
      melde("Seite " + n + " von " + seiten + " …");
      const seite = await doc.getPage(n);
      const inhalt = await seite.getTextContent();
      const text = inhalt.items.map((i) => i.str).join(" ").trim();
      if (text.length >= MIN_ZEICHEN) {
        // Seite mit Textebene: direkt übernehmen. Schneller und fehlerfrei —
        // OCR darüber laufen zu lassen würde Fehler erst erzeugen.
        ergebnisse.push({ seite: n, art: "pdf-text", text: text, konfidenz: 1 });
        continue;
      }
      const skala = seite.getViewport({ scale: 1 });
      const faktor = Math.min(2, MAX_KANTE / Math.max(skala.width, skala.height));
      const ansicht = seite.getViewport({ scale: faktor });
      const c = document.createElement("canvas");
      c.width = Math.round(ansicht.width);
      c.height = Math.round(ansicht.height);
      await seite.render({ canvasContext: c.getContext("2d"), viewport: ansicht }).promise;
      const gelesen = await bildLesen(aufbereiten(c, kopfProzent), melde);
      ergebnisse.push({ seite: n, art: "pdf-ocr", text: gelesen.text, konfidenz: gelesen.konfidenz });
    }
    if (doc.numPages > seiten) {
      melde("Nur die ersten " + seiten + " Seiten wurden gelesen.");
    }
    return ergebnisse;
  }

  /* ------------------------------------------------- Paket: Bild + Text */

  // Für den Seiten-Upload (`material-paket.js`): die Vorschau braucht das
  // Bild jeder Seite, der Server speichert es als Dokument — nur der Text
  // dazu kommt aus OCR. `paketSeiten` rendert und liest die Textebene;
  // OCR läuft erst beim Einlesen (`paketOcr`), weil die Vorschau vorher
  // schon da sein soll.

  function canvasZuJpeg(canvas) {
    return new Promise((fertig) => {
      canvas.toBlob((b) => fertig(b), "image/jpeg", 0.85);
    });
  }

  // Farbiges, verkleinertes Abbild — Vorschau und Ablage. `aufbereiten`
  // macht daraus erst beim Lesen das Graustufenbild für Tesseract.
  function farbCanvas(quelle) {
    const breite = quelle.width || quelle.naturalWidth;
    const hoehe = quelle.height || quelle.naturalHeight;
    const faktor = Math.min(1, MAX_KANTE / Math.max(breite, hoehe));
    const c = document.createElement("canvas");
    c.width = Math.round(breite * faktor);
    c.height = Math.round(hoehe * faktor);
    c.getContext("2d").drawImage(quelle, 0, 0, c.width, c.height);
    return c;
  }

  async function paketPdfSeiten(datei, melde) {
    melde("PDF wird geöffnet …");
    const pdfjs = await import(PDFJS + "pdf.min.mjs");
    pdfjs.GlobalWorkerOptions.workerSrc = PDFJS + "pdf.worker.min.mjs";
    const doc = await pdfjs.getDocument({ data: await datei.arrayBuffer() }).promise;
    if (doc.numPages > MAX_SEITEN) {
      throw new Error("Das PDF hat " + doc.numPages + " Seiten — es passen nur " + MAX_SEITEN + " in ein Paket.");
    }
    const seiten = doc.numPages;
    const ergebnisse = [];
    for (let n = 1; n <= seiten; n++) {
      melde("Seite " + n + " von " + seiten + " …");
      const seite = await doc.getPage(n);
      const skala = seite.getViewport({ scale: 1 });
      const faktor = Math.min(2, MAX_KANTE / Math.max(skala.width, skala.height));
      const ansicht = seite.getViewport({ scale: faktor });
      const c = document.createElement("canvas");
      c.width = Math.round(ansicht.width);
      c.height = Math.round(ansicht.height);
      await seite.render({ canvasContext: c.getContext("2d"), viewport: ansicht }).promise;
      const inhalt = await seite.getTextContent();
      const text = inhalt.items.map((i) => i.str).join(" ").trim();
      ergebnisse.push({
        seite: n, canvas: c, jpeg: await canvasZuJpeg(c),
        art: text.length >= MIN_ZEICHEN ? "pdf-text" : "pdf-ocr",
        text: text.length >= MIN_ZEICHEN ? text : "", konfidenz: text.length >= MIN_ZEICHEN ? 1 : 0,
      });
    }
    return ergebnisse;
  }

  async function paketSeiten(datei, kopfProzent, melde) {
    const name = (datei.name || "").toLowerCase();
    if (datei.type === "application/pdf" || name.endsWith(".pdf")) {
      return await paketPdfSeiten(datei, melde);
    }
    let bild = datei;
    if (/heic|heif/.test(datei.type) || /\.hei[cf]$/.test(name)) {
      bild = await heicUmwandeln(datei, melde);
    }
    const canvas = farbCanvas(await alsBitmap(bild));
    return [{ seite: 1, canvas: canvas, jpeg: await canvasZuJpeg(canvas),
              art: "foto", text: "", konfidenz: 0 }];
  }

  // Erst beim Einlesen: Textebene schon da? dann nichts zu tun — sonst OCR.
  async function paketOcr(seite, kopfProzent, melde) {
    if (seite.text && seite.text.length >= MIN_ZEICHEN) return seite;
    const gelesen = await bildLesen(aufbereiten(seite.canvas, kopfProzent), melde);
    seite.text = gelesen.text;
    seite.konfidenz = gelesen.konfidenz;
    return seite;
  }

  /* --------------------------------------------------------------- Ablauf */

  async function lesen(datei, kopfProzent, melde) {
    const name = (datei.name || "").toLowerCase();
    if (datei.type === "application/pdf" || name.endsWith(".pdf")) {
      return await pdfLesen(datei, kopfProzent, melde);
    }
    let bild = datei;
    if (/heic|heif/.test(datei.type) || /\.hei[cf]$/.test(name)) {
      bild = await heicUmwandeln(datei, melde);
    }
    const bitmap = await alsBitmap(bild);
    const gelesen = await bildLesen(aufbereiten(bitmap, kopfProzent), melde);
    return [{ seite: 1, art: "foto", text: gelesen.text, konfidenz: gelesen.konfidenz }];
  }

  // Zwischenspeicher für die 21 MB Lesehilfe. Fehlt er (altes Safari,
  // privates Fenster), wird eben jedes Mal geladen — es geht auch ohne.
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/ocr-sw.js", { scope: "/static/" })
      .catch(() => { /* ohne Zwischenspeicher weiter */ });
  }

  window.karoBlattLesen = { lesen: lesen, paketSeiten: paketSeiten,
                            paketOcr: paketOcr, MIN_ZEICHEN: MIN_ZEICHEN };
})();
