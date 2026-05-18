// Service worker mínimo: sólo habilita "Añadir a pantalla de inicio" en Android.
// No cacheamos para que cambios en el servidor se vean inmediatamente.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => { /* network passthrough */ });
