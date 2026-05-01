/**
 * FastBlog PWA Service Worker
 *
 * 功能:
 * 1. 静态资源缓存（App Shell）
 * 2. 动态内容缓存策略
 * 3. 离线页面支持
 * 4. 后台同步
 */

const CACHE_NAME = 'fastblog-v1';
const STATIC_CACHE = 'fastblog-static-v1';
const DYNAMIC_CACHE = 'fastblog-dynamic-v1';

// 需要预缓存的静态资源
const PRECACHE_URLS = [
  '/',
  '/manifest.json',
    '/offline.html',
];

// 安装事件 - 预缓存静态资源
self.addEventListener('install', (event) => {
  event.waitUntil(
      caches.open(PRECACHE_CACHE)
      .then((cache) => {
          console.log('[Service Worker] Precaching app shell');
          return cache.addAll(PRECACHE_URLS);
      })
      .then(() => self.skipWaiting())
  );
});

// 激活事件 - 清理旧缓存
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
            .filter((name) => name !== STATIC_CACHE && name !== DYNAMIC_CACHE)
            .map((name) => {
                console.log('[Service Worker] Deleting old cache:', name);
                return caches.delete(name);
            })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch 事件 - 缓存策略
self.addEventListener('fetch', (event) => {
    const {request} = event;
    const url = new URL(request.url);

    // API 请求 - Network First
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirst(request));
    return;
  }

    // 静态资源 - Cache First
    if (isStaticAsset(url.pathname)) {
        event.respondWith(cacheFirst(request));
        return;
    }

    // 页面请求 - Stale While Revalidate
    if (request.mode === 'navigate') {
        event.respondWith(staleWhileRevalidate(request));
        return;
    }

    // 默认策略
    event.respondWith(fetch(request));
});

// 消息事件 - 手动控制缓存
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }

    if (event.data && event.data.type === 'CLEAR_CACHE') {
        caches.keys().then((cacheNames) => {
            Promise.all(
                cacheNames.map((name) => caches.delete(name))
            );
        });
  }
});

/**
 * 缓存策略实现
 */

// Cache First - 优先使用缓存，缓存不存在则网络请求
async function cacheFirst(request) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }

    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        // 网络失败，返回离线页面
        return caches.match('/offline.html');
    }
}

// Network First - 优先使用网络，网络失败则使用缓存
async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        const cachedResponse = await caches.match(request);
        return cachedResponse || new Response(
            JSON.stringify({error: 'Network error'}),
            {status: 503, headers: {'Content-Type': 'application/json'}}
        );
    }
}

// Stale While Revalidate - 先返回缓存，同时更新缓存
async function staleWhileRevalidate(request) {
    const cache = await caches.open(DYNAMIC_CACHE);
    const cachedResponse = await cache.match(request);

    const fetchPromise = fetch(request).then((networkResponse) => {
        if (networkResponse.ok) {
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    }).catch(() => {
        // 网络失败，如果也没有缓存，返回离线页面
        return cachedResponse || caches.match('/offline.html');
    });

    return cachedResponse || fetchPromise;
}

// 判断是否为静态资源
function isStaticAsset(pathname) {
    const staticExtensions = [
        '.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg',
        '.ico', '.woff', '.woff2', '.ttf', '.eot', '.webp'
    ];

    return staticExtensions.some(ext => pathname.endsWith(ext));
}
