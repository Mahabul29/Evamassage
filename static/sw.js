const CACHE_NAME = 'evamassage-v1';

const urlsToCache = [
    '/',
    '/dashboard',
    '/profile',
    '/settings',
    '/static/css/style.css'
];

self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(function(cache) {
                return cache.addAll(urlsToCache);
            })
            .then(function() {
                return self.skipWaiting();
            })
    );
});

self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(cacheNames) {
            return Promise.all(
                cacheNames.map(function(cache) {
                    if (cache !== CACHE_NAME) {
                        console.log('Service Worker: Clearing Old Cache');
                        return caches.delete(cache);
                    }
                })
            );
        })
    );
});

self.addEventListener('fetch', function(event) {
    const url = new URL(event.request.url);
    const dynamicRoutes = ['/', '/dashboard', '/profile', '/settings'];

    if (url.origin === self.location.origin && dynamicRoutes.includes(url.pathname)) {
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
        event.respondWith(
            caches.match(event.request)
                .then(function(response) {
                    return response || fetch(event.request);
                })
        );
    }
});

