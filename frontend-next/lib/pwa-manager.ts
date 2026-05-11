/**
 * PWA 注册和管理工具
 */

export interface PWAStatus {
    isSupported: boolean;
    isInstalled: boolean;
    isInstallable: boolean;
    serviceWorkerActive: boolean;
    pushNotificationEnabled: boolean;
}

class PWAManager {
    private static instance: PWAManager;
    private registration: ServiceWorkerRegistration | null = null;

    private constructor() {
    }

    static getInstance(): PWAManager {
        if (!PWAManager.instance) {
            PWAManager.instance = new PWAManager();
        }
        return PWAManager.instance;
    }

    /**
     * 注册Service Worker
     */
    async registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
        if (!('serviceWorker' in navigator)) {
            console.warn('[PWA] Service Worker not supported');
            return null;
        }

        try {
            // 使用增强的PWA Service Worker
            this.registration = await navigator.serviceWorker.register('/pwa-service-worker.js', {
                scope: '/',
            });

            console.log('[PWA] Service Worker registered:', this.registration.scope);

            // 监听更新
            this.registration.addEventListener('updatefound', () => {
                console.log('[PWA] New content available');
            });

            return this.registration;
        } catch (error) {
            console.error('[PWA] Service Worker registration failed:', error);
            return null;
        }
    }

    /**
     * 获取PWA状态
     */
    getStatus(): PWAStatus {
        return {
            isSupported: 'serviceWorker' in navigator && 'PushManager' in window,
            isInstalled: window.matchMedia('(display-mode: standalone)').matches,
            isInstallable: false, // 需要通过事件监听设置
            serviceWorkerActive: this.registration?.active !== null,
            pushNotificationEnabled: Notification.permission === 'granted',
        };
    }

    /**
     * 请求推送通知权限
     */
    async requestNotificationPermission(): Promise<boolean> {
        if (!('Notification' in window)) {
            console.warn('[PWA] Notifications not supported');
            return false;
        }

        try {
            const permission = await Notification.requestPermission();
            return permission === 'granted';
        } catch (error) {
            console.error('[PWA] Notification permission request failed:', error);
            return false;
        }
    }

    /**
     * 订阅推送通知
     */
    async subscribeToPush(): Promise<PushSubscription | null> {
        if (!this.registration) {
            console.warn('[PWA] Service Worker not registered');
            return null;
        }

        try {
            const subscription = await this.registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(
                    // TODO: 从环境变量获取VAPID公钥
                    process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY || ''
                ),
            });

            console.log('[PWA] Push subscription created');
            return subscription;
        } catch (error) {
            console.error('[PWA] Push subscription failed:', error);
            return null;
        }
    }

    /**
     * 取消推送订阅
     */
    async unsubscribeFromPush(): Promise<boolean> {
        if (!this.registration) {
            return false;
        }

        try {
            const subscription = await this.registration.pushManager.getSubscription();
            if (subscription) {
                await subscription.unsubscribe();
                console.log('[PWA] Push subscription removed');
                return true;
            }
            return false;
        } catch (error) {
            console.error('[PWA] Unsubscribe failed:', error);
            return false;
        }
    }

    /**
     * 清除所有缓存
     */
    async clearAllCache(): Promise<void> {
        if ('caches' in window) {
            const cacheNames = await caches.keys();
            await Promise.all(cacheNames.map(name => caches.delete(name)));
            console.log('[PWA] All caches cleared');
        }
    }

    /**
     * 预缓存指定URLs
     */
    async precacheUrls(urls: string[]): Promise<void> {
        if (!this.registration) {
            console.warn('[PWA] Service Worker not registered');
            return;
        }

        const messageChannel = new MessageChannel();

        return new Promise((resolve, reject) => {
            messageChannel.port1.onmessage = (event) => {
                if (event.data.success) {
                    resolve();
                } else {
                    reject(new Error('Precache failed'));
                }
            };

            this.registration.active?.postMessage(
                {type: 'CACHE_URLS', urls},
                [messageChannel.port2]
            );
        });
    }

    /**
     * 检查更新
     */
    async checkForUpdate(): Promise<boolean> {
        if (!this.registration) {
            return false;
        }

        try {
            await this.registration.update();
            return true;
        } catch (error) {
            console.error('[PWA] Update check failed:', error);
            return false;
        }
    }

    /**
     * 强制更新
     */
    async forceUpdate(): Promise<void> {
        if (!this.registration) {
            return;
        }

        const messageChannel = new MessageChannel();

        return new Promise((resolve) => {
            messageChannel.port1.onmessage = () => {
                window.location.reload();
                resolve();
            };

            this.registration.active?.postMessage(
                {type: 'SKIP_WAITING'},
                [messageChannel.port2]
            );
        });
    }

    /**
     * 将Base64转换为Uint8Array（用于VAPID密钥）
     */
    private urlBase64ToUint8Array(base64String: string): Uint8Array {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }

        return outputArray;
    }
}

// 导出单例
export const pwaManager = PWAManager.getInstance();

// 便捷函数
export async function initPWA(): Promise<PWAStatus> {
    await pwaManager.registerServiceWorker();
    return pwaManager.getStatus();
}
