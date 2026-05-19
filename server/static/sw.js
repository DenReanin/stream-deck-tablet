// Service worker para que la PWA sea instalable.
// No cacheamos los estáticos para que los cambios en el servidor se
// vean inmediatamente sin tener que limpiar caché.
const VERSION = 'v2';

self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (e) => {
  // network-only por ahora
});
