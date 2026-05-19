/**
 * Web Push Notification Hook
 * 用于管理浏览器推送通知订阅和接收
 */

import {useState, useEffect, useCallback} from 'react';
import apiClient from '@/lib/api-client';

interface PushSubscriptionState {
    isSupported: boolean;
    isSubscribed: boolean;
    subscription: PushSubscription | null;
    permission: NotificationPermission;
}

interface UseWebPushOptions {
    onNotificationClick?: (data: any) => void;
    onNotificationShow?: (data: any) => void;
}

export function useWebPush(options: UseWebPushOptions = {}) {
    const [state, setState] = useState<PushSubscriptionState>({
        isSupported: false,
        isSubscribed: false,
        subscription: null,
        permission: 'default',
    });

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // 检查浏览器支持
    useEffect(() => {
        const checkSupport = () => {
            const supported = 'serviceWorker' in navigator && 'PushManager' in window;
            setState(prev => ({...prev, isSupported: supported}));

            if (supported) {
                // 检查当前权限状态
                setState(prev => ({...prev, permission: Notification.permission}));
            }
        };

        checkSupport();
    }, []);

    // 请求通知权限
    const requestPermission = useCallback(async (): Promise<boolean> => {
        if (!state.isSupported) {
            setError('浏览器不支持推送通知');
            return false;
        }

        try {
            setLoading(true);
            setError(null);

            const permission = await Notification.requestPermission();
            setState(prev => ({...prev, permission}));

            if (permission === 'granted') {
                console.log('[Push] Permission granted');
                return true;
            } else if (permission === 'denied') {
                setError('用户拒绝了通知权限');
                return false;
            } else {
                setError('通知权限被忽略');
                return false;
            }
        } catch (err) {
            console.error('[Push] Failed to request permission:', err);
            setError('请求权限失败');
            return false;
        } finally {
            setLoading(false);
        }
    }, [state.isSupported]);

    // 获取VAPID公钥
    const getVapidPublicKey = useCallback(async (): Promise<string | null> => {
        try {
            const response = await apiClient.get('/push/vapid-public-key');
            if (response.success && response.data) {
                return response.data.public_key;
            }
            return null;
        } catch (err) {
            console.error('[Push] Failed to get VAPID key:', err);
            return null;
        }
    }, []);

    // 订阅推送
    const subscribe = useCallback(async (): Promise<boolean> => {
        if (!state.isSupported) {
            setError('浏览器不支持推送通知');
            return false;
        }

        try {
            setLoading(true);
            setError(null);

            // 1. 请求权限
            const hasPermission = await requestPermission();
            if (!hasPermission) {
                return false;
            }

            // 2. 注册Service Worker
            const registration = await navigator.serviceWorker.ready;
            console.log('[Push] Service Worker ready');

            // 3. 获取VAPID公钥
            const vapidPublicKey = await getVapidPublicKey();
            if (!vapidPublicKey) {
                setError('无法获取VAPID密钥');
                return false;
            }

            // 4. 订阅推送
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
            });

            console.log('[Push] Subscribed successfully');

            // 5. 发送订阅到服务器
            const subscriptionData = subscription.toJSON();
            await apiClient.post('/push/subscribe', {
                endpoint: subscriptionData.endpoint,
                keys: subscriptionData.keys,
                user_agent: navigator.userAgent,
            });

            setState(prev => ({
                ...prev,
                isSubscribed: true,
                subscription: subscription,
            }));

            return true;
        } catch (err) {
            console.error('[Push] Failed to subscribe:', err);
            setError(`订阅失败: ${err instanceof Error ? err.message : '未知错误'}`);
            return false;
        } finally {
            setLoading(false);
        }
    }, [state.isSupported, requestPermission, getVapidPublicKey]);

    // 取消订阅
    const unsubscribe = useCallback(async (): Promise<boolean> => {
        if (!state.subscription) {
            return false;
        }

        try {
            setLoading(true);
            setError(null);

            // 1. 取消浏览器订阅
            await state.subscription.unsubscribe();
            console.log('[Push] Unsubscribed from browser');

            // 2. 通知服务器
            await apiClient.post('/push/unsubscribe', {
                endpoint: state.subscription.endpoint,
            });

            setState(prev => ({
                ...prev,
                isSubscribed: false,
                subscription: null,
            }));

            return true;
        } catch (err) {
            console.error('[Push] Failed to unsubscribe:', err);
            setError('取消订阅失败');
            return false;
        } finally {
            setLoading(false);
        }
    }, [state.subscription]);

    // 检查订阅状态
    const checkSubscription = useCallback(async () => {
        if (!state.isSupported) {
            return;
        }

        try {
            const response = await apiClient.get('/push/subscription-status');

            if (response.success && response.data) {
                setState(prev => ({
                    ...prev,
                    isSubscribed: response.data.subscribed,
                }));
            }
        } catch (err) {
            console.error('[Push] Failed to check subscription:', err);
        }
    }, [state.isSupported]);

    // 初始化 - 检查现有订阅
    useEffect(() => {
        if (state.isSupported) {
            checkSubscription();

            // 监听Service Worker消息
            const handleMessage = (event: MessageEvent) => {
                console.log('[Push] Message from SW:', event.data);
            };

            navigator.serviceWorker.addEventListener('message', handleMessage);

            return () => {
                navigator.serviceWorker.removeEventListener('message', handleMessage);
            };
        }
    }, [state.isSupported, checkSubscription]);

    // 监听通知点击
    useEffect(() => {
        if (typeof window !== 'undefined') {
            const handleNotificationClick = (event: any) => {
                if (options.onNotificationClick) {
                    options.onNotificationClick(event.detail);
                }
            };

            window.addEventListener('notification-click', handleNotificationClick);

            return () => {
                window.removeEventListener('notification-click', handleNotificationClick);
            };
        }
    }, [options.onNotificationClick]);

    return {
        ...state,
        loading,
        error,
        subscribe,
        unsubscribe,
        requestPermission,
        checkSubscription,
        clearError: () => setError(null),
    };
}

// 工具函数: 将Base64 URL转换为Uint8Array
function urlBase64ToUint8Array(base64String: string): Uint8Array {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }

    return outputArray;
}

export default useWebPush;
