// Service Worker: macht die App installierbar und offline nutzbar.
// Bei Änderungen an den App-Dateien die Versionsnummer erhöhen.
const CACHE = 'radar-v1';
const LIB_CACHE = 'radar-lib'; // Bibliotheken & Modell bleiben bei Updates erhalten
const APP_FILES = [
  './',
  './index.html',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/apple-touch-icon.png'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(APP_FILES)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE && k !== LIB_CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;

  if (new URL(req.url).origin === location.origin) {
    // Eigene Dateien: erst Netz (damit Updates sofort ankommen), offline aus dem Cache
    e.respondWith(
      fetch(req)
        .then(res => {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy));
          return res;
        })
        .catch(() => caches.match(req))
    );
  } else {
    // Bibliotheken und KI-Modell (versioniert, ändern sich nicht): erst Cache, dann Netz
    e.respondWith(
      caches.match(req).then(hit => hit || fetch(req).then(res => {
        if (res.ok || res.type === 'opaque') {
          const copy = res.clone();
          caches.open(LIB_CACHE).then(c => c.put(req, copy));
        }
        return res;
      }))
    );
  }
});
