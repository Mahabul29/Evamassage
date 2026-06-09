const CACHE_NAME = 'evamassage-v1';

const urlsToCache = [
    '/',
    '/dashboard',
    '/profile',
    '/settings',
    '/static/css/style.css'
];

// Install stage - caches the vital assets initially
self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(function(cache) {
                return cache.addAll(urlsToCache);
            })
            .then(function() {
                return self.skipWaiting(); // Forces the waiting service worker to become active
            })
    );
});

// Activate stage - cleans up old caches if CACHE_NAME changes
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

// Fetch stage - handles smart routing for network vs cache
self.addEventListener('fetch', function(event) {
    const url = new URL(event.request.url);

    // Array of dynamic HTML application routes to protect with Network-First strategy
    const dynamicRoutes = ['/', '/dashboard', '/profile', '/settings'];

    // Strategy 1: Network-First for dynamic HTML templates
    if (url.origin === self.location.origin && dynamicRoutes.includes(url.pathname)) {
        event.respondWith(
            fetch(event.request)
                .then(function(response) {
                    // Check if we received a valid response back to cache
                    if (!response || response.status !== 200) {
                        return response;
                    }
                    // Update the cache with the newest version of the page
                    return caches.open(CACHE_NAME).then(function(cache) {
                        cache.put(event.request, response.clone());
                        return response;
                    });
                })
                .catch(function() {
                    // If network fails (user is offline), serve the cached version of that specific page
                    return caches.match(event.request);
                })
        );
    } else {
        // Strategy 2: Cache-First for static assets (CSS, JS files, images)
        event.respondWith(
            caches.match(event.request)
                .then(function(response) {
                    return response || fetch(event.request);
                })
        );
    }
});
