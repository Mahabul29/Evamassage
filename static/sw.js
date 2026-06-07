const CACHE_NAME = 'evamassage-v1';
const urlsToCache = ['/', '/static/manifest.json', '/static/css/style.css', '/static/js/app.js', '/static/js/chat.js', '/static/js/channel.js', '/static/js/install.js'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache)));
});

self.addEventListener('fetch', event => {
  event.respondWith(caches.match(event.request).then(response => response || fetch(event.request)));
});
