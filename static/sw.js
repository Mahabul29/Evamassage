const CACHE_NAME = 'evamassage-v1';

const urlsToCache = [
    '/',
    '/static/css/style.css'
];

// Install stage - caches the initial vital assets
self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(function(cache) {
                return cache.addAll(urlsToCache);
            })
    );
});

// Fetch stage - handles smart routing for network vs cache
self.addEventListener('fetch', function(event) {
    const url = new URL(event.request.url);

    // Strategy 1: Network-First for dynamic HTML routes (like the home page)
    if (url.origin === self.location.origin && url.pathname === '/') {
        event.respondWith(
            fetch(event.request)
                .then(function(response) {
                    // Check if we received a valid response back to cache
                    if (!response || response.status !== 200 || response.type !== 'basic') {
                        return response;
                    }
                    // Update the cache with the newest version of the page
                    return caches.open(CACHE_NAME).then(function(cache) {
                        cache.put(event.request, response.clone());
                        return response;
                    });
                })
                .catch(function() {
                    // If network fails (user is offline), serve the cached version
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
