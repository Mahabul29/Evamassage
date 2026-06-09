const CACHE_NAME = 'evamassage-v4';

// Cache nothing on install - avoids STARTING stuck problem
self.addEventListener('install', function(event) {
    console.log('SW: Installing...');
    // Skip waiting immediately - no cache addAll that can fail
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    console.log('SW: Activating...');
    event.waitUntil(
        Promise.all([
            // Clear all old caches
            caches.keys().then(function(cacheNames) {
                return Promise.all(
                    cacheNames.map(function(cache) {
                        if (cache !== CACHE_NAME) {
                            return caches.delete(cache);
                        }
                    })
                );
            }),
            // Take control immediately
            self.clients.claim()
        ])
    );
});

self.addEventListener('fetch', function(event) {
    // Only cache GET requests for static assets
    if (event.request.method !== 'GET') return;

    const url = new URL(event.request.url);

    // Only cache static files, never dynamic pages
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(event.request).then(function(response) {
                if (response) return response;
                return fetch(event.request).then(function(fetchResponse) {
                    if (!fetchResponse || fetchResponse.status !== 200) {
                        return fetchResponse;
                    }
                    const responseClone = fetchResponse.clone();
                    caches.open(CACHE_NAME).then(function(cache) {
                        cache.put(event.request, responseClone);
                    });
                    return fetchResponse;
                });
            })
        );
    } else {
        // All other requests go straight to network
        event.respondWith(fetch(event.request));
    }
});

