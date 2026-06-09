const CACHE_NAME = 'evamassage-v3';

// Only cache files that definitely exist
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
                console.log('Cache failed:', err);
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
                            console.log('Deleting old cache:', cache);
                            return caches.delete(cache);
                        }
                    })
                );
            }),
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
                    if (!response || response.status !== 200) return response;
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
