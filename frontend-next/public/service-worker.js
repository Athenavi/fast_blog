/**
 * Service Worker for Push Notifications
 * 处理Web推送通知和后台同步
 */

const CACHE_NAME = 'fastblog-push-v1';
const PUSH_CACHE_NAME = 'fastblog-push-data-v1';

// 安装事件
self.addEventListener('install', (event) => {
    console.log('[SW] Installing service worker...');
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll([
                '/',
                '/manifest.json',
                '/icons/icon-192x192.png',
                '/icons/icon-512x512.png',
            ]);
        })
    );
    self.skipWaiting();
});

// 激活事件
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating service worker...');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME && name !== PUSH_CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        })
    );
    self.clients.claim();
});

// 推送事件
self.addEventListener('push', (event) => {
    console.log('[SW] Push notification received');

    let data = {};

    try {
        data = event.data ? event.data.json() : {};
    } catch (e) {
        console.error('[SW] Failed to parse push data:', e);
        data = {
            title: '新通知',
            body: '您有一条新消息',
        };
    }

    const title = data.title || 'FastBlog';
    const options = {
        body: data.body || '',
        icon: data.icon || '/icons/icon-192x192.png',
        badge: data.badge || '/icons/badge-72x72.png',
        image: data.image,
        data: data.data || {},
        actions: data.actions || [
            {
                action: 'open',
                title: '查看',
            },
            {
                action: 'dismiss',
                title: '关闭',
            },
        ],
        tag: data.tag || 'default',
        requireInteraction: data.requireInteraction || false,
        silent: data.silent || false,
        timestamp: data.timestamp || Date.now(),
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

// 通知点击事件
self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification clicked');

    event.notification.close();

    const action = event.action;
    const notificationData = event.notification.data || {};

    if (action === 'dismiss') {
        // 用户点击关闭,不做任何操作
        return;
    }

    // 默认打开URL或首页
    const urlToOpen = notificationData.url || '/';

    event.waitUntil(
        clients.matchAll({type: 'window', includeUncontrolled: true})
            .then((windowClients) => {
                // 检查是否已有打开的窗口
                for (let client of windowClients) {
                    if (client.url === urlToOpen && 'focus' in client) {
                        return client.focus();
                    }
                }

                // 没有则打开新窗口
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

// 通知关闭事件
self.addEventListener('notificationclose', (event) => {
    console.log('[SW] Notification closed');
    // 可以在这里记录用户关闭通知的行为
});

// Fetch事件 - 缓存策略
self.addEventListener('fetch', (event) => {
    // 只缓存GET请求
    if (event.request.method !== 'GET') {
        return;
    }

    // API请求不缓存
    if (event.request.url.includes('/api/')) {
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                // 缓存命中,返回缓存
                if (response) {
                    return response;
                }

                // 缓存未命中,从网络获取
                return fetch(event.request).then((networkResponse) => {
                    // 检查是否是有效响应
                    if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
                        return networkResponse;
                    }

                    // 克隆响应用于缓存
                    const responseToCache = networkResponse.clone();

                    caches.open(CACHE_NAME)
                        .then((cache) => {
                            cache.put(event.request, responseToCache);
                        });

                    return networkResponse;
                });
            })
    );
});

// 后台同步
self.addEventListener('sync', (event) => {
    console.log('[SW] Background sync triggered:', event.tag);

    if (event.tag === 'sync-notifications') {
        event.waitUntil(syncNotifications());
    }
});

// 同步通知数据
async function syncNotifications() {
    try {
        // Fetch latest notifications from server
        console.log('[SW] Syncing notifications...');

        const response = await fetch('/api/v1/notifications?limit=20');
        if (response.ok) {
            const notifications = await response.json();

            // Cache notifications for offline access
            const cache = await caches.open(PUSH_CACHE_NAME);
            await cache.put('/api/v1/notifications?cached=true', new Response(JSON.stringify(notifications)));

            console.log('[SW] Notifications synced:', notifications.length);
        }

        // Can implement offline notification queue sync here
    } catch (error) {
        console.error('[SW] Failed to sync notifications:', error);
    }
}

// 消息事件 - 与主线程通信
self.addEventListener('message', (event) => {
    console.log('[SW] Message received:', event.data);

    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    } else if (event.data && event.data.type === 'CLEAR_CACHE') {
        // 清除缓存
        event.waitUntil(
            caches.keys().then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((name) => caches.delete(name))
                );
            }).then(() => {
                // 通知主线程清除完成
                event.ports[0].postMessage({success: true});
            })
        );
    }
});

// 定期后台同步(Periodic Background Sync)
self.addEventListener('periodicsync', (event) => {
    console.log('[SW] Periodic sync triggered:', event.tag);

    if (event.tag === 'update-content') {
        event.waitUntil(updateContent());
    }
});

// 更新内容
async function updateContent() {
    try {
        console.log('[SW] Updating content...');

        // 预取最新内容
        const response = await fetch('/api/v1/articles?limit=10');
        if (response.ok) {
            const data = await response.json();

            // 缓存最新文章
            const cache = await caches.open(PUSH_CACHE_NAME);
            await cache.put('/api/v1/articles?cached=true', new Response(JSON.stringify(data)));
        }
    } catch (error) {
        console.error('[SW] Failed to update content:', error);
    }
}
