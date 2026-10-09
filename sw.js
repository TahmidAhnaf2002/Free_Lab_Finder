/* Free Lab Finder service worker.
 *
 * The routine lives inside index.html, so a stale page means a student reads
 * last semester's schedule. That is worse than a slow page. So:
 *
 *   index.html -> network first, with a short timeout, cache as a backup
 *   fonts      -> cache first, refreshed quietly in the background
 *
 * update_routine.py bumps VERSION every semester, which wipes the old cache.
 */

const VERSION = 'fall2026-1';
const CACHE = 'flf-' + VERSION;
const PAGE = './index.html';
const TIMEOUT = 2500;

const SHELL = [
  './',
  './index.html'
];

const FONT_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com'];

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    // add one at a time so a single missing file cannot fail the whole install
    await Promise.all(SHELL.map(url => cache.add(url).catch(() => { })));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(
      names.filter(n => n.startsWith('flf-') && n !== CACHE).map(n => caches.delete(n))
    );
    await self.clients.claim();
  })());
});

self.addEventListener('message', event => {
  if (event.data === 'skip-waiting') self.skipWaiting();
});

function keepable(res) {
  // opaque responses (some font files) report status 0 but are still worth keeping
  return res && (res.ok || res.type === 'opaque');
}

async function networkFirst(request) {
  const cache = await caches.open(CACHE);

  const fromNetwork = fetch(request).then(res => {
    // cache every page response under one key, so ?day=sun&room=... does not
    // fill the cache with near-identical copies
    if (keepable(res)) cache.put(PAGE, res.clone()).catch(() => { });
    return res;
  });

  const giveUp = new Promise((_, reject) => setTimeout(() => reject(new Error('slow')), TIMEOUT));

  try {
    return await Promise.race([fromNetwork, giveUp]);
  } catch (err) {
    // offline, or the network is dragging - the background fetch still updates
    // the cache for next time
    const hit = (await cache.match(PAGE)) || (await cache.match('./'));
    if (hit) return hit;
    // never hand back a rejected promise: the browser cannot render that and
    // shows a confusing "Failed to convert value to 'Response'" instead
    return offlinePage();
  }
}

function offlinePage() {
  return new Response(
    '<!doctype html><meta charset="utf-8">'
    + '<meta name="viewport" content="width=device-width,initial-scale=1">'
    + '<title>Free Lab Finder</title>'
    + '<body style="background:#070b0d;color:#d7e5ea;font-family:system-ui;'
    + 'display:grid;place-items:center;height:100vh;margin:0;text-align:center">'
    + '<div><h1 style="font-size:19px">No connection</h1>'
    + '<p style="color:#7795a0;font-size:14px">Open this once while online and '
    + 'it will work offline afterwards.</p></div>',
    { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
  );
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(request);

  if (hit) {
    fetch(request)
      .then(res => { if (keepable(res)) cache.put(request, res.clone()); })
      .catch(() => { });
    return hit;
  }

  const res = await fetch(request);
  if (keepable(res)) cache.put(request, res.clone()).catch(() => { });
  return res;
}

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;

  let url;
  try { url = new URL(request.url); } catch (e) { return; }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return;

  const sameOrigin = url.origin === self.location.origin;

  if (request.mode === 'navigate' || (sameOrigin && url.pathname.endsWith('/index.html'))) {
    event.respondWith(networkFirst(request));
    return;
  }

  if (sameOrigin || FONT_HOSTS.includes(url.hostname)) {
    event.respondWith(
      cacheFirst(request)
        .catch(() => caches.match(request))
        .then(res => res || new Response('', { status: 504 }))
    );
  }
});
