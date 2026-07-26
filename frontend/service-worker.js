const CACHE_NAME = 'pharma-tracker-v2';
const ASSETS_TO_CACHE = [
    './',
    './index.html',
    './manifest.json',
    './icon.png'
];

// Install Event — cache assets and activate immediately
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
        .then(cache => cache.addAll(ASSETS_TO_CACHE))
    );
    self.skipWaiting(); // Force instant activation (don't wait for old tabs to close)
});

// Activate Event — delete ALL old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(name => name !== CACHE_NAME)
                    .map(name => caches.delete(name))
            );
        })
    );
    self.clients.claim(); // Take control of all open tabs immediately
});

// Fetch Event — NETWORK-FIRST strategy (always get fresh content)
self.addEventListener('fetch', event => {
    event.respondWith(
        fetch(event.request)
            .then(networkResponse => {
                // Got fresh response from server — update cache and return it
                if (networkResponse && networkResponse.status === 200) {
                    const responseClone = networkResponse.clone();
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, responseClone);
                    });
                }
                return networkResponse;
            })
            .catch(() => {
                // Network failed (offline) — fall back to cache
                return caches.match(event.request);
            })
    );
});
