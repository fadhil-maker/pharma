// SELF-DESTRUCTING SERVICE WORKER
// This service worker immediately unregisters itself and clears ALL caches.
// Once deployed, it will break the old cache loop permanently.

self.addEventListener('install', () => {
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        Promise.all([
            // Delete every single cache
            caches.keys().then(names => Promise.all(names.map(n => caches.delete(n)))),
            // Unregister this service worker
            self.registration.unregister()
        ]).then(() => {
            // Force all open tabs to reload with fresh content from server
            self.clients.matchAll().then(clients => {
                clients.forEach(client => client.navigate(client.url));
            });
        })
    );
});

// NEVER intercept fetch — always go to network
self.addEventListener('fetch', () => {});
