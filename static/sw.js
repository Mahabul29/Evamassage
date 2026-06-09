const CACHE_NAME = 'evamassage-v2';

// FIX: Only cache files that definitely exist (removed /dashboard /profile /settings)
const urlsToCache = [
    '/',
    '/static/css/style.css'
];

self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(function(cache) {
                console.log('Service Worker: Caching Files');
                return cache.addAll(urlsToCache);
            })
            .then(function() {
                return self.skipWaiting();
            })
            .catch(function(err) {
                console.log('Cache addAll failed:', err);
            })
    );
});

self.addEventListener('activate', function(event) {
    event.waitUntil(
        Promise.all([
            caches.keys().then(function(cacheNames) {
                return Promise.all(
                    cacheNames.map(function(cache) {
                        if (cache !== CACHE_NAME) {
                            console.log('Service Worker: Clearing Old Cache:', cache);
                            return caches.delete(cache);
                        }
                    })
                );
            }),
            // FIX: Take control of all pages immediately
            self.clients.claim()
        ])
    );
});

self.addEventListener('fetch', function(event) {
    const url = new URL(event.request.url);
    const dynamicRoutes = ['/', '/dashboard', '/profile', '/settings'];

    if (url.origin === self.location.origin && dynamicRoutes.includes(url.pathname)) {
        // Network first for dynamic pages
        event.respondWith(
            fetch(event.request)
                .then(function(response) {
                    if (!response || response.status !== 200) {
                        return response;
                    }
                    return caches.open(CACHE_NAME).then(function(cache) {
                        cache.put(event.request, response.clone());
                        return response;
                    });
                })
                .catch(function() {
                    return caches.match(event.request);
                })
        );
    } else {
        // Cache first for static assets
        event.respondWith(
            caches.match(event.request)
                .then(function(response) {
                    return response || fetch(event.request);
                })
        );
    }
});
