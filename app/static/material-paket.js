/* Ein Material-Paket zusammenstellen: Seiten wählen oder fotografieren,
 * in der Vorschau ordnen und gemeinsam einlesen lassen.
 *
 * Gelesen wird auf dem Gerät (karoBlattLesen aus blatt-lesen.js):
 * pdf.js zerlegt PDFs, Tesseract-WASM liest Bilder. Zum Server gehen die
 * Seiten als JPEG samt ihrem Text — das fachliche Modell sieht nie ein
 * Bild. Ohne JavaScript bleibt das normale Dateifeld daneben der Weg.
 */
(function () {
  "use strict";

  const zone = document.querySelector("[data-paket-zone]");
  if (!zone || !window.karoBlattLesen) return;

  const form = zone.closest("form");
  // Die Grenzen stehen im Server (config.ops() → material_paket.py) und werden
  // vom Template als data-Attribute geliefert — hier keine eigenen Zahlen,
  // sonst liefen zwei Quellen auseinander.
  const MB = 1048576;
  const MAX = parseInt(zone.dataset.maxSeiten, 10);
  const KOPF = parseFloat(zone.dataset.kopfProzent || "0");
  const MAX_BILD = parseInt(zone.dataset.maxBildMb, 10) * MB;
  const MAX_PDF = parseInt(zone.dataset.maxPdfMb, 10) * MB;
  const MAX_PAKET = parseInt(zone.dataset.maxPaketMb, 10) * MB;
  const liste = zone.querySelector("[data-paket-liste]");
  const zaehler = zone.querySelector("[data-paket-zaehler]");
  const fehlerEl = zone.querySelector("[data-paket-fehler]");
  const standEl = zone.querySelector("[data-paket-stand]");
  const startBtn = zone.querySelector("[data-paket-start]");
  const nativ = form ? form.querySelector("[data-paket-nativ]") : null;

  const seiten = [];  // {name, art, text, konfidenz, canvas, jpeg, thumb}

  function el(name, klasse, text) {
    const k = document.createElement(name);
    if (klasse) k.className = klasse;
    if (text != null) k.textContent = text;
    return k;
  }

  function melde(text) { if (standEl) standEl.textContent = text || ""; }
  function fehler(text) {
    if (!fehlerEl) return;
    fehlerEl.textContent = text || "";
    fehlerEl.hidden = !text;
  }

  /* ------------------------------------------------ versteckte Inputs */

  // Zwei getrennte Eingänge: der normale Dialog ohne `capture` — dort liegen
  // PDFs und die Dateien-App —, die Kamera mit `capture` für den direkten
  // Schnappschuss. `capture` am selben Feld sperrte auf iOS alles außer der
  // Kamera aus.
  const dateiInput = el("input");
  dateiInput.type = "file";
  dateiInput.multiple = true;
  dateiInput.accept = ".pdf,.jpg,.jpeg,.png,.heic,.heif";
  dateiInput.hidden = true;

  const fotoInput = el("input");
  fotoInput.type = "file";
  fotoInput.accept = "image/*";
  fotoInput.setAttribute("capture", "environment");
  fotoInput.hidden = true;

  zone.appendChild(dateiInput);
  zone.appendChild(fotoInput);

  zone.hidden = false;
  if (nativ) nativ.hidden = true;

  /* ------------------------------------------------------------ Liste */

  function zeichnen() {
    liste.innerHTML = "";
    seiten.forEach((s, i) => {
      const zeile = el("div", "paket-seite");

      const bild = el("img", "paket-thumb");
      bild.src = s.thumb;
      bild.alt = "Seite " + (i + 1);
      zeile.appendChild(bild);

      const mitte = el("div", "paket-seite-info");
      mitte.appendChild(el("b", null, "Seite " + (i + 1)));
      mitte.appendChild(el("small", null, s.name || ""));
      zeile.appendChild(mitte);

      const knoepfe = el("div", "paket-seite-knoepfe");
      const hoch = el("button", "quiet", "↑");
      hoch.type = "button";
      hoch.title = "Seite nach vorne";
      hoch.setAttribute("aria-label", "Seite " + (i + 1) + " nach vorne");
      hoch.disabled = i === 0;
      hoch.addEventListener("click", () => {
        seiten.splice(i - 1, 0, seiten.splice(i, 1)[0]);
        zeichnen();
      });
      const runter = el("button", "quiet", "↓");
      runter.type = "button";
      runter.title = "Seite nach hinten";
      runter.setAttribute("aria-label", "Seite " + (i + 1) + " nach hinten");
      runter.disabled = i === seiten.length - 1;
      runter.addEventListener("click", () => {
        seiten.splice(i + 1, 0, seiten.splice(i, 1)[0]);
        zeichnen();
      });
      const weg = el("button", "quiet", "Entfernen");
      weg.type = "button";
      weg.addEventListener("click", () => {
        URL.revokeObjectURL(s.thumb);
        seiten.splice(i, 1);
        zeichnen();
      });
      knoepfe.appendChild(hoch);
      knoepfe.appendChild(runter);
      knoepfe.appendChild(weg);
      zeile.appendChild(knoepfe);

      liste.appendChild(zeile);
    });

    zaehler.textContent = seiten.length + " von " + MAX + " Seiten";
    startBtn.disabled = seiten.length === 0;
    startBtn.textContent = seiten.length === 0
      ? "Seiten einlesen →"
      : seiten.length + (seiten.length === 1 ? " Seite" : " Seiten") + " einlesen →";
  }

  /* ------------------------------------------------------- Hinzufügen */

  async function hinzufuegen(dateien) {
    fehler("");
    for (const datei of Array.from(dateien)) {
      if (seiten.length >= MAX) {
        fehler("Es passen nur " + MAX + " Seiten in ein Paket — " +
               seiten.length + " sind schon drin.");
        break;
      }
      try {
        const istPdf = /\.pdf$/i.test(datei.name || "") ||
                       datei.type === "application/pdf";
        const grenze = istPdf ? MAX_PDF : MAX_BILD;
        if (datei.size > grenze) {
          throw new Error("zu gross");
        }
        const neu = await window.karoBlattLesen.paketSeiten(datei, KOPF, melde);
        for (const s of neu) {
          if (seiten.length >= MAX) {
            fehler("Es passen nur " + MAX + " Seiten in ein Paket — " +
                   seiten.length + " sind schon drin.");
            break;
          }
          s.name = neu.length > 1
            ? (datei.name || "PDF") + " · Seite " + s.seite
            : (datei.name || "Foto");
          s.thumb = URL.createObjectURL(s.jpeg);
          seiten.push(s);
        }
      } catch (e) {
        fehler(e && e.message === "zu gross"
          ? "„" + (datei.name || "Das Foto") + "“ ist zu groß — " +
            "Bilder bis " + Math.round(MAX_BILD / MB) + " MB, PDFs bis " +
            Math.round(MAX_PDF / MB) + " MB."
          : "„" + (datei.name || "Das Foto") + "“ konnte nicht gelesen " +
            "werden. Versuche es mit einer anderen Datei.");
      }
    }
    melde("");
    zeichnen();
  }

  zone.querySelector("[data-paket-datei]").addEventListener("click", () => {
    dateiInput.click();
  });
  zone.querySelector("[data-paket-foto]").addEventListener("click", () => {
    fotoInput.click();
  });
  dateiInput.addEventListener("change", () => {
    hinzufuegen(dateiInput.files);
    dateiInput.value = "";
  });
  fotoInput.addEventListener("change", () => {
    hinzufuegen(fotoInput.files);
    fotoInput.value = "";
  });

  /* ------------------------------------------------------------ Senden */

  form.addEventListener("submit", async (e) => {
    if (seiten.length === 0) return;   // nichts gesammelt: nativer Weg
    e.preventDefault();
    startBtn.disabled = true;
    fehler("");

    // OCR erst jetzt: die Vorschau soll sofort da sein, das Lesen darf dauern.
    for (let i = 0; i < seiten.length; i++) {
      melde("Seite " + (i + 1) + " von " + seiten.length + " wird gelesen …");
      try {
        await window.karoBlattLesen.paketOcr(seiten[i], KOPF, melde);
      } catch (err) {
        seiten[i].text = "";
        seiten[i].konfidenz = 0;
      }
    }

    // Gesamtgröße der zu sendenden Seiten — dieselbe Grenze wie am Server.
    const gesamt = seiten.reduce((summe, s) => summe + (s.jpeg ? s.jpeg.size : 0), 0);
    if (gesamt > MAX_PAKET) {
      fehler("Zusammen sind die Seiten zu groß — ein Paket darf höchstens " +
             Math.round(MAX_PAKET / MB) + " MB haben. Entferne eine Seite.");
      startBtn.disabled = false;
      return;
    }

    melde("Wird gespeichert …");
    const fd = new FormData();
    fd.append(zone.dataset.csrfName, zone.dataset.csrf);
    fd.append("zweck", zone.dataset.zweck || "lernen");
    fd.append("fach", zone.dataset.fach || "");
    fd.append("quelle", zone.dataset.quelle || "");
    const meta = seiten.map((s, i) => {
      fd.append("seite", s.jpeg, "seite-" + (i + 1) + ".jpg");
      return { name: s.name, art: s.art, text: s.text || "",
               konfidenz: s.konfidenz || 0 };
    });
    fd.append("seiten", JSON.stringify(meta));

    try {
      const r = await fetch(zone.dataset.url, { method: "POST", body: fd });
      const j = await r.json().catch(() => null);
      if (r.ok && j && j.weiter) {
        location.href = j.weiter;
        return;
      }
      fehler((j && j.fehler) ||
             "Das hat nicht geklappt — bitte versuche es noch einmal.");
    } catch (e2) {
      fehler("Keine Verbindung zum Server — bitte versuche es noch einmal.");
    }
    melde("");
    startBtn.disabled = false;
  });

  zeichnen();

  // „Foto machen" von der Einstiegskarte: die Kamera direkt anbieten — wo
  // der Browser den Klick ohne Finger verweigert, liegt der Knopf fokussiert
  // bereit und wartet auf den eigenen Tipp.
  if (/[?&]kamera=1/.test(location.search)) {
    const knopf = zone.querySelector("[data-paket-foto]");
    knopf.focus();
    try { fotoInput.click(); } catch (e) { /* dann eben per Tipp */ }
  }
})();
