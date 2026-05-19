/**
 * FastBlog PWA Service Worker
 * 提供离线缓存、后台同步、推送通知等功能
 */

const CACHE_VERSION = 'v1';
const STATIC_CACHE = `fastblog-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `fastblog-dynamic-${CACHE_VERSION}`;
const API_CACHE = `fastblog-api-${CACHE_VERSION}`;

// 需要预缓存的静态资源
const PRECACHE_URLS = [
    '/',
    '/offline.html',
    '/manifest.json',
    '/icons/icon-192x192.png',
    '/icons/icon-512x512.png',
];

// 不需要缓存的路径
const EXCLUDE_PATHS = [
    '/api/v1/auth',
    '/admin',
    '/api/v1/installation',
];

// 安装事件 - 预缓存关键资源
self.addEventListener('install', (event) => {
    console.log('[SW] Installing service worker...');
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => {
                console.log('[SW] Precaching static assets');
                return cache.addAll(PRECACHE_URLS);
            })
            .then(() => self.skipWaiting())
    );
});

// 激活事件 - 清理旧缓存
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating service worker...');
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((name) => {
                            return name !== STATIC_CACHE &&
                                name !== DYNAMIC_CACHE &&
                                name !== API_CACHE;
                        })
                        .map((name) => {
                            console.log('[SW] Deleting old cache:', name);
                            return caches.delete(name);
                        })
                );
            })
            .then(() => self.clients.claim())
    );
});

// Fetch事件 - 智能缓存策略
self.addEventListener('fetch', (event) => {
    const {request} = event;
    const url = new URL(request.url);

    // 排除不需要缓存的路径
    if (shouldExclude(url.pathname)) {
        return;
    }

    // 根据请求类型选择不同的缓存策略
    if (request.method !== 'GET') {
        return;
    }

    if (url.pathname.startsWith('/api/')) {
        // API请求：网络优先，失败时返回缓存
        event.respondWith(networkFirstStrategy(request));
    } else if (isStaticAsset(url.pathname)) {
        // 静态资源：缓存优先
        event.respondWith(cacheFirstStrategy(request, STATIC_CACHE));
    } else {
        // 页面请求： stale-while-revalidate 策略
        event.respondWith(staleWhileRevalidate(request));
    }
});

// 推送通知事件
self.addEventListener('push', (event) => {
    console.log('[SW] Push notification received');

    let data = {};
    try {
        data = event.data ? event.data.json() : {};
    } catch (e) {
        console.error('[SW] Failed to parse push data:', e);
        data = {
            title: 'FastBlog',
            body: '您有一条新消息',
        };
    }

    const title = data.title || 'FastBlog';
    const options = {
        body: data.body || '',
        icon: data.icon || '/icons/icon-192x192.png',
        badge: data.badge || '/icons/icon-72x72.png',
        image: data.image,
        data: data.data || {},
        actions: data.actions || [
            {action: 'open', title: '查看'},
            {action: 'dismiss', title: '关闭'},
        ],
        tag: data.tag || 'default',
        requireInteraction: data.requireInteraction || false,
        silent: data.silent || false,
        timestamp: data.timestamp || Date.now(),
    };

    event.waitUntil(self.registration.showNotification(title, options));
});

// 通知点击事件
self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification clicked');
    event.notification.close();

    const action = event.action;
    const notificationData = event.notification.data || {};

    if (action === 'dismiss') {
        return;
    }

    const urlToOpen = notificationData.url || '/';

    event.waitUntil(
        clients.matchAll({type: 'window', includeUncontrolled: true})
            .then((windowClients) => {
                for (let client of windowClients) {
                    if (client.url === urlToOpen && 'focus' in client) {
                        return client.focus();
                    }
                }
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

// 后台同步事件
self.addEventListener('sync', (event) => {
    console.log('[SW] Background sync triggered:', event.tag);

    if (event.tag === 'sync-content') {
        event.waitUntil(syncContent());
    }
});

// 消息事件 - 与主线程通信
self.addEventListener('message', (event) => {
    console.log('[SW] Message received:', event.data);

    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    } else if (event.data && event.data.type === 'CLEAR_CACHE') {
        event.waitUntil(
            caches.keys().then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((name) => caches.delete(name))
                );
            }).then(() => {
                console.log('[SW] All caches cleared');
                event.ports[0].postMessage({success: true});
            })
        );
    } else if (event.data && event.data.type === 'CACHE_URLS') {
        // 动态缓存指定URLs
        const urls = event.data.urls || [];
        event.waitUntil(
            caches.open(DYNAMIC_CACHE)
                .then((cache) => cache.addAll(urls))
                .then(() => {
                    console.log('[SW] Cached URLs:', urls);
                    event.ports[0].postMessage({success: true});
                })
        );
    }
});

// ==================== 缓存策略函数 ====================

/**
 * 缓存优先策略（适用于静态资源）
 */
async function cacheFirstStrategy(request, cacheName) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }

    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        console.error('[SW] Fetch failed:', error);
        return new Response('Offline', {status: 503, statusText: 'Service Unavailable'});
    }
}

/**
 * 网络优先策略（适用于API请求）
 */
async function networkFirstStrategy(request) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(API_CACHE);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        console.log('[SW] Network failed, trying cache');
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        return new Response(
            JSON.stringify({error: 'Offline', message: 'No network connection and no cached data'}),
            {
                status: 503,
                headers: {'Content-Type': 'application/json'}
            }
        );
    }
}

/**
 * Stale-while-revalidate 策略（适用于页面）
 */
async function staleWhileRevalidate(request) {
    const cache = await caches.open(DYNAMIC_CACHE);
    const cachedResponse = await cache.match(request);

    const fetchPromise = fetch(request)
        .then((networkResponse) => {
            if (networkResponse.ok) {
                cache.put(request, networkResponse.clone());
            }
            return networkResponse;
        })
        .catch(() => {
            console.log('[SW] Fetch failed for:', request.url);
        });

    return cachedResponse || fetchPromise || caches.match('/offline.html');
}

// ==================== 辅助函数 ====================

/**
 * 判断是否应该排除缓存
 */
function shouldExclude(pathname) {
    return EXCLUDE_PATHS.some(path => pathname.startsWith(path));
}

/**
 * 判断是否是静态资源
 */
function isStaticAsset(pathname) {
    const staticExtensions = ['.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2'];
    return staticExtensions.some(ext => pathname.endsWith(ext));
}

/**
 * 同步内容（后台同步）
 */
async function syncContent() {
    try {
        console.log('[SW] Syncing content...');
        // Sync offline content (drafts, comments, likes, etc.)
        // Example: Fetch pending actions from IndexedDB and send to server
        const pendingActions = await getPendingActions();
        for (const action of pendingActions) {
            await fetch(action.url, {
                method: action.method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(action.data)
            });
        }
        await clearPendingActions();
        console.log('[SW] Content synced successfully');
    } catch (error) {
        console.error('[SW] Sync failed:', error);
    }
}
