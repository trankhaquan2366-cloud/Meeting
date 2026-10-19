const CACHE_NAME = 'roomsync-shell-v2';
const APP_SHELL = ['/', '/manifest.json'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys
          .filter(key => key.startsWith('roomsync-shell-') && key !== CACHE_NAME)
          .map(key => caches.delete(key)),
      ))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', event => {
  const { request } = event;
  const requestUrl = new URL(request.url);

  if (
    request.method !== 'GET'
    || requestUrl.origin !== self.location.origin
    || requestUrl.pathname === '/api'
    || requestUrl.pathname.startsWith('/api/')
  ) {
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response.ok) {
            const responseCopy = response.clone();
            return caches.open(CACHE_NAME)
              .then(cache => cache.put(request, responseCopy))
              .then(() => response);
          }
          return response;
        })
        .catch(async () => (await caches.match(request)) || caches.match('/')),
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(cachedResponse => {
      if (cachedResponse) return cachedResponse;

      return fetch(request).then(response => {
        if (response.ok) {
          const responseCopy = response.clone();
          return caches.open(CACHE_NAME)
            .then(cache => cache.put(request, responseCopy))
            .then(() => response);
        }
        return response;
      });
    }),
  );
});
