// KimConnect Service Worker - Enables offline functionality
const CACHE_NAME = 'kimconnect-v1';
const STATIC_ASSETS = [
    '/',
    '/static/manifest.json',
    '/static/js/app.js',
    '/static/municipal_service/Images/logo.png',
    'https://cdn.tailwindcss.com',
    'https://unpkg.com/lucide@latest'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('KimConnect: Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .catch((err) => {
                console.log('KimConnect: Cache failed', err);
            })
    );
    self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        })
    );
    self.clients.claim();
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', (event) => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') return;
    
    // Skip Chrome extensions
    if (event.request.url.startsWith('chrome-extension')) return;
    
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
