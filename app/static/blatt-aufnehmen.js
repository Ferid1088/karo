/* Die Oberfläche dazu: zwei Knöpfe, ein Hinweis, ein Fortschritt.
 *
 * Das Blatt wird hier gelesen und füllt danach dasselbe Textfeld, in das
 * sonst jemand abtippt. Ein Weg, nicht zwei: was hier ankommt, geht denselben
 * Pfad wie eingetippter Text (POST /blatt/text).
 */
(function () {
  "use strict";

  const form = document.querySelector("[data-blatt-form]");
  if (!form || !window.karoBlattLesen) return;

  const textfeld = form.querySelector("textarea[name='blatt_text']");
  const dateifeld = form.querySelector("input[name='datei']");
  const bereich = form.querySelector("[data-lesen-bereich]");
  if (!textfeld || !dateifeld || !bereich) return;

  const kopfProzent = parseInt(bereich.dataset.kopfProzent || "8", 10);
  const stand = el("p", "hint", "");
  stand.setAttribute("role", "status");
  const seitenliste = el("div", "seiten-liste");
  seitenliste.hidden = true;
  bereich.appendChild(stand);
  bereich.appendChild(seitenliste);

  function el(name, klasse, text) {
    const k = document.createElement(name);
    if (klasse) k.className = klasse;
    if (text != null) k.textContent = text;
    return k;
  }
  function melde(text) { stand.textContent = text; }

  // Kamera nur anbieten, wenn es eine gibt. Am Schreibtisch-PC wäre der Knopf
  // eine Sackgasse.
  const hatKamera = "mediaDevices" in navigator || /Android|iPhone|iPad/i.test(navigator.userAgent);

  const knoepfe = el("div", "actions blatt-knoepfe");
  const kameraFeld = el("input");
  kameraFeld.type = "file";
  kameraFeld.accept = "image/*";
  // Als Attribut, nicht als Eigenschaft: nur das Attribut ist in allen
  // Engines sichtbar — und nur daran erkennt man von aussen, dass dieses
  // Feld die Kamera meint und das andere die Dateien-App.
  kameraFeld.setAttribute("capture", "environment");
  kameraFeld.hidden = true;
  const dateiWahl = el("input");
  dateiWahl.type = "file";
  // Ohne `capture` — sonst lässt iOS nur die Kamera zu und kein PDF aus der
  // Dateien-App. Das war der Grund, warum PDFs auf dem iPad nie ankamen.
  dateiWahl.accept = "image/*,application/pdf,.heic,.heif";
  dateiWahl.hidden = true;

  const kameraKnopf = el("button", "btn", "Blatt fotografieren");
  kameraKnopf.type = "button";
  const dateiKnopf = el("button", "btn quiet", "Datei wählen");
  dateiKnopf.type = "button";
  if (hatKamera) knoepfe.appendChild(kameraKnopf);
  knoepfe.appendChild(dateiKnopf);
  bereich.insertBefore(knoepfe, stand);
  bereich.appendChild(kameraFeld);
  bereich.appendChild(dateiWahl);

  /* ------------------------------------------------- Hinweis vor der Kamera */

  function hinweisZeigen() {
    const box = el("div", "card hinweis-kamera");
    box.appendChild(el("h3", null, "Bevor du fotografierst"));
    const liste = el("ul");
    [
      "Das Foto bleibt auf diesem Gerät. Es wird nirgendwohin geschickt.",
      "Karo liest den Text hier im Browser und schickt nur diesen Text weiter.",
      "Namen, Klasse und Datum oben auf dem Blatt entfernt Karo dabei.",
      "Blatt flach hinlegen, von oben fotografieren, keine Schatten.",
    ].forEach((t) => liste.appendChild(el("li", null, t)));
    box.appendChild(liste);
    const weiter = el("button", "btn", "Verstanden, Kamera öffnen");
    weiter.type = "button";
    const abbrechen = el("button", "btn quiet", "Abbrechen");
    abbrechen.type = "button";
    const zeile = el("div", "actions");
    zeile.appendChild(weiter);
    zeile.appendChild(abbrechen);
    box.appendChild(zeile);
    bereich.insertBefore(box, knoepfe.nextSibling);
    weiter.focus();
    weiter.addEventListener("click", () => { box.remove(); kameraFeld.click(); });
    abbrechen.addEventListener("click", () => { box.remove(); kameraKnopf.focus(); });
  }

  kameraKnopf.addEventListener("click", hinweisZeigen);
  dateiKnopf.addEventListener("click", () => dateiWahl.click());
  kameraFeld.addEventListener("change", () => uebernehmen(kameraFeld.files[0]));
  dateiWahl.addEventListener("change", () => uebernehmen(dateiWahl.files[0]));

  /* ------------------------------------------------------- Drag und Drop */

  if (!hatKamera) {
    ["dragover", "drop"].forEach((art) => {
      bereich.addEventListener(art, (e) => {
        e.preventDefault();
        bereich.classList.toggle("zieht", art === "dragover");
        if (art === "drop" && e.dataTransfer.files.length) {
          uebernehmen(e.dataTransfer.files[0]);
        }
      });
    });
    bereich.appendChild(el("p", "hint", "Oder die Datei einfach hierher ziehen."));
  }

  /* -------------------------------------------------------------- Lesen */

  function inDateifeld(datei) {
    // Dieselbe Datei auch als Beleg mit hochladen: das Blatt gehört zur
    // Sammlung, auch wenn niemand es liest.
    try {
      const dt = new DataTransfer();
      dt.items.add(datei);
      dateifeld.files = dt.files;
    } catch (e) { /* ältere Browser: dann lädt die Familie es selbst aus */ }
  }

  function seitenAnbieten(seiten) {
    seitenliste.innerHTML = "";
    seitenliste.hidden = seiten.length < 2;
    if (seiten.length < 2) return;
    seitenliste.appendChild(el("p", "hint", "Welche Seiten sollen übernommen werden?"));
    seiten.forEach((s, i) => {
      const zeile = el("label", "auswahl");
      const haken = el("input");
      haken.type = "checkbox";
      haken.checked = true;
      haken.addEventListener("change", () => zusammensetzen(seiten));
      s.aktiv = haken;
      zeile.appendChild(haken);
      zeile.appendChild(document.createTextNode(
        " Seite " + s.seite + " (" + (s.text.length) + " Zeichen"
        + (s.art === "pdf-text" ? ", Textebene" : ", gelesen") + ")"));
      seitenliste.appendChild(zeile);
    });
  }

  function zusammensetzen(seiten) {
    const genommen = seiten.filter((s) => !s.aktiv || s.aktiv.checked);
    textfeld.value = genommen.map((s) => s.text).join("\n\n");
    const mit = genommen.filter((s) => s.konfidenz);
    const schnitt = mit.length
      ? mit.reduce((a, s) => a + s.konfidenz, 0) / mit.length : 0;
    let feld = form.querySelector("input[name='ocr_konfidenz']");
    if (!feld) {
      feld = el("input");
      feld.type = "hidden";
      feld.name = "ocr_konfidenz";
      form.appendChild(feld);
    }
    feld.value = schnitt ? schnitt.toFixed(2) : "";
    return textfeld.value;
  }

  async function uebernehmen(datei) {
    if (!datei) return;
    inDateifeld(datei);
    melde("Einen Moment …");
    try {
      const seiten = await window.karoBlattLesen.lesen(datei, kopfProzent, melde);
      seitenAnbieten(seiten);
      const text = zusammensetzen(seiten);
      if (text.trim().length < window.karoBlattLesen.MIN_ZEICHEN) {
        melde("Auf dem Blatt war zu wenig sicher lesbar. Bitte neu fotografieren: "
              + "flach hinlegen, von oben, ohne Schatten — oder den Text eintippen.");
        return;
      }
      melde(text.length + " Zeichen gelesen. Bitte kurz durchsehen und dann abschicken.");
      textfeld.focus();
    } catch (fehler) {
      // Ehrlich sagen, was nicht ging, statt es auf das Foto zu schieben —
      // und den Rückfall anbieten, statt ihn heimlich zu nehmen.
      melde("Das Lesen im Browser hat nicht geklappt (" + fehler.message + ").");
      rueckfallAnbieten(datei);
    }
  }

  /* ------------------------------------------------- Rückfall ohne WASM */

  function rueckfallAnbieten(datei) {
    if (bereich.querySelector(".rueckfall")) return;
    const box = el("div", "card rueckfall");
    box.appendChild(el("p", null,
      "Karo kann das Blatt stattdessen auf dem Server lesen — das ist der "
      + "Rechner, auf dem Karo läuft, kein fremder Dienst. Die Datei geht "
      + "dafür kurz dorthin und wird sofort nach dem Lesen gelöscht."));
    box.appendChild(el("p", "hint",
      "Wenn dir das zu viel ist: tipp den Text einfach ein. Das Blatt wird "
      + "trotzdem hochgeladen."));
    const ja = el("button", "btn", "Auf dem Server lesen");
    ja.type = "button";
    const nein = el("button", "btn quiet", "Lieber eintippen");
    nein.type = "button";
    const zeile = el("div", "actions");
    zeile.appendChild(ja);
    zeile.appendChild(nein);
    box.appendChild(zeile);
    bereich.appendChild(box);
    nein.addEventListener("click", () => { box.remove(); textfeld.focus(); });
    ja.addEventListener("click", async () => {
      box.remove();
      melde("Das Blatt wird auf dem Server gelesen …");
      const daten = new FormData();
      daten.append("datei", datei);
      daten.append("fach", form.querySelector("input[name='fach']").value);
      const marke = form.querySelector("input[name='_csrf']");
      if (marke) daten.append("_csrf", marke.value);
      try {
        const antwort = await fetch("/blatt/serverseitig", { method: "POST", body: daten });
        const ergebnis = await antwort.json();
        if (!antwort.ok) { melde(ergebnis.fehler || "Hat nicht geklappt."); return; }
        textfeld.value = ergebnis.text || "";
        melde(textfeld.value.length + " Zeichen gelesen. Die Datei auf dem Server "
              + "ist schon wieder gelöscht. Bitte durchsehen und abschicken.");
        textfeld.focus();
      } catch (e) {
        melde("Auch das ging nicht (" + e.message + "). Bitte den Text eintippen.");
      }
    });
  }
})();
