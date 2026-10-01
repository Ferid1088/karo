/* Zwischenspeicher für die Lesehilfe — damit das zweite Blatt sofort geht.
 *
 * Tesseract-WASM, die Sprachdaten und pdf.js sind zusammen rund 21 MB. Einmal
 * laden ist in Ordnung; bei jedem Blatt erneut wäre es das nicht — auf einem
 * iPad im Mobilfunknetz schon gar nicht.
 *
 * Nur diese Dateien, und nur „erst Zwischenspeicher, dann Netz". Seiten der
 * App fasst dieser Worker nicht an: ein Zwischenspeicher, der eine veraltete
 * Lernseite ausliefert, wäre schlimmer als gar keiner. Deshalb liegt er unter
 * /static/ — sein Geltungsbereich endet dort.
 */
const SPEICHER = "karo-lesehilfe-v1";
const UNSERE = [/^\/static\/ocr\//, /^\/static\/pdfjs\//];

self.addEventListener("install", (e) => self.skipWaiting());

self.addEventListener("activate", (e) => {
  // Alte Fassungen aufräumen: sonst liegen nach einem Update 42 MB herum.
  e.waitUntil(caches.keys().then((namen) =>
    Promise.all(namen.filter((n) => n.startsWith("karo-lesehilfe-") && n !== SPEICHER)
                     .map((n) => caches.delete(n)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return;
  if (!UNSERE.some((m) => m.test(url.pathname))) return;
  e.respondWith(caches.open(SPEICHER).then((speicher) =>
    speicher.match(e.request).then((treffer) => treffer || fetch(e.request).then((antwort) => {
      if (antwort.ok) speicher.put(e.request, antwort.clone());
      return antwort;
    }))));
});
