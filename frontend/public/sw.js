// =============================================================================
// SERVICE WORKER: sw.js
// PURPOSE: Enables PWA "Add to Home Screen" install prompts + offline shell
/* global clients */
// STRATEGY:
//   - Static assets (JS/CSS/fonts/images): Cache-first (stale-while-revalidate)
//   - API calls (/api/*): Network-first with cache fallback
//   - HTML navigation: Network-first with offline fallback to cached index.html
// CACHE NAMES: versioned so stale caches get cleaned up on SW update
// =============================================================================

const CACHE_VERSION = 'v1';
const STATIC_CACHE = `zenith-static-${CACHE_VERSION}`;
const RUNTIME_CACHE = `zenith-runtime-${CACHE_VERSION}`;
const KNOWN_CACHES = [STATIC_CACHE, RUNTIME_CACHE];

// Assets to pre-cache on install (app shell)
const PRECACHE_ASSETS = [
  '/',
  '/manifest.json',
  '/favicon.ico',
  '/icon-192.png',
  '/icon-512.png',
];

// ── Install: pre-cache the app shell ────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) => cache.addAll(PRECACHE_ASSETS))
      .then(() => self.skipWaiting()) // activate immediately
  );
});

// ── Activate: clean up old caches ───────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => !KNOWN_CACHES.includes(key))
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim()) // take control of all open tabs
  );
});

// ── Fetch: routing strategy ──────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // 1. Skip non-GET and cross-origin requests (e.g. analytics, fonts CDN)
  if (request.method !== 'GET') return;
  if (url.origin !== self.location.origin && !url.hostname.endsWith('fonts.gstatic.com')) return;

  // 2. API calls → network-first, fall back to cache
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstWithCache(request, RUNTIME_CACHE));
    return;
  }

  // 3. Google Fonts (CSS + font files) → cache-first
  if (
    url.hostname === 'fonts.googleapis.com' ||
    url.hostname === 'fonts.gstatic.com'
  ) {
    event.respondWith(cacheFirstWithNetwork(request, RUNTIME_CACHE));
    return;
  }

  // 4. Static assets (JS, CSS, images, icons, manifest) → stale-while-revalidate
  if (
    /\.(js|css|png|jpg|jpeg|svg|ico|woff2?|ttf|json)(\?.*)?$/.test(url.pathname)
  ) {
    event.respondWith(staleWhileRevalidate(request, STATIC_CACHE));
    return;
  }

  // 5. HTML navigation → network-first, offline falls back to cached '/'
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match('/').then((cached) => cached || Response.error())
      )
    );
    return;
  }

  // 6. Everything else → network only
});

// ── Strategy helpers ─────────────────────────────────────────────────────────

async function networkFirstWithCache(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    return cached || Response.error();
  }
}

async function cacheFirstWithNetwork(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return Response.error();
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  const networkFetch = fetch(request)
    .then((response) => {
      if (response.ok) cache.put(request, response.clone());
      return response;
    })
    .catch(() => null);

  return cached || (await networkFetch) || Response.error();
}

// ── Push notifications (future use) ─────────────────────────────────────────
self.addEventListener('push', (event) => {
  if (!event.data) return;
  try {
    const data = event.data.json();
    event.waitUntil(
      self.registration.showNotification(data.title || 'Zenith', {
        body: data.body || '',
        icon: '/icon-192.png',
        badge: '/favicon-48.png',
        tag: data.tag || 'zenith-notification',
        data: { url: data.url || '/' },
      })
    );
  } catch {
    // ignore malformed push data
  }
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = event.notification.data?.url || '/';
  event.waitUntil(
    clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then((windowClients) => {
        const existing = windowClients.find((c) => c.url === target && 'focus' in c);
        if (existing) return existing.focus();
        return clients.openWindow(target);
      })
  );
});
