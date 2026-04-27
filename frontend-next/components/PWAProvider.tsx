'use client';

/**
 * PWA 注册和管理组件
 * 处理 Service Worker 注册、更新提示和离线检测
 */

import {useCallback, useEffect, useState} from 'react';

interface PWAState {
    isSupported: boolean;
    isInstalled: boolean;
    needsRefresh: boolean;
    isOnline: boolean;
    updateAvailable: boolean;
}

export default function PWAProvider({children}: { children: React.ReactNode }) {
    const [state, setState] = useState<PWAState>({
        isSupported: false,
        isInstalled: false,
        needsRefresh: false,
        isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
        updateAvailable: false,
    });

    const [deferredPrompt, setDeferredPrompt] = useState<any>(null);

    /**
     * 注册 Service Worker
     */
    const registerServiceWorker = useCallback(async () => {
        if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
            setState(prev => ({...prev, isSupported: false}));
            return;
        }

        try {
            setState(prev => ({...prev, isSupported: true}));

            const registration = await navigator.serviceWorker.register('/sw.js', {
                scope: '/',
            });

            console.log('[PWA] Service Worker registered:', registration.scope);

            // 监听更新
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;

                if (!newWorker) return;

                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        // 有新版本可用
                        setState(prev => ({...prev, updateAvailable: true, needsRefresh: true}));
                        console.log('[PWA] New version available');
                    }
                });
            });

            // 检查是否已安装
            if (window.matchMedia('(display-mode: standalone)').matches) {
                setState(prev => ({...prev, isInstalled: true}));
            }

        } catch (error) {
            console.error('[PWA] Service Worker registration failed:', error);
        }
    }, []);

    /**
     * 监听在线/离线状态
     */
    useEffect(() => {
        if (typeof window === 'undefined') return;

        // 初始化时同步当前网络状态
        setState(prev => ({...prev, isOnline: navigator.onLine}));

        const handleOnline = () => {
            setState(prev => ({...prev, isOnline: true}));
            console.log('[PWA] Back online');
        };

        const handleOffline = () => {
            setState(prev => ({...prev, isOnline: false}));
            console.log('[PWA] Offline');
        };

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, []);

    /**
     * 监听安装提示
     */
    useEffect(() => {
        if (typeof window === 'undefined') return;

        const handleBeforeInstallPrompt = (e: Event) => {
            e.preventDefault();
            setDeferredPrompt(e);
            console.log('[PWA] Install prompt available');
        };

        window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

        return () => {
            window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
        };
    }, []);

    /**
     * 初始化 Service Worker
     */
    useEffect(() => {
        registerServiceWorker();
    }, [registerServiceWorker]);

    /**
     * 安装 PWA
     */
    const installPWA = async () => {
        if (!deferredPrompt) {
            console.log('[PWA] Installation not available');
            return;
        }

        try {
            deferredPrompt.prompt();
            const {outcome} = await deferredPrompt.userChoice;

            if (outcome === 'accepted') {
                console.log('[PWA] User accepted installation');
                setState(prev => ({...prev, isInstalled: true}));
            } else {
                console.log('[PWA] User dismissed installation');
            }

            setDeferredPrompt(null);
        } catch (error) {
            console.error('[PWA] Installation failed:', error);
        }
    };

    /**
     * 更新应用
     */
    const updateApp = () => {
        if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage({type: 'SKIP_WAITING'});
            window.location.reload();
        }
    };

    /**
     * 清除缓存
     */
    const clearCache = async () => {
        if ('serviceWorker' in navigator) {
            const messageChannel = new MessageChannel();

            messageChannel.port1.onmessage = (event) => {
                if (event.data.success) {
                    console.log('[PWA] Cache cleared');
                    window.location.reload();
                }
            };

            navigator.serviceWorker.controller?.postMessage(
                {type: 'CLEAR_CACHE'},
                [messageChannel.port2]
            );
        }
    };

    return (
        <>
            {children}

            {/* 离线提示 */}
            {!state.isOnline && (
                <div
                    className="fixed bottom-4 left-4 z-50 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                              d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/>
                    </svg>
                    <span>您已离线</span>
                </div>
            )}

            {/* 更新提示 */}
            {state.updateAvailable && (
                <div
                    className="fixed bottom-4 right-4 z-50 bg-blue-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
                    <span>新版本可用</span>
                    <button
                        onClick={updateApp}
                        className="bg-white text-blue-500 px-3 py-1 rounded hover:bg-blue-50 transition"
                    >
                        立即更新
                    </button>
                </div>
            )}

            {/* 安装提示 - 仅在未安装且支持时显示 */}
            {!state.isInstalled && state.isSupported && deferredPrompt && (
                <div
                    className="fixed top-4 right-4 z-50 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
                    <span>安装 FastBlog</span>
                    <button
                        onClick={installPWA}
                        className="bg-white text-green-500 px-3 py-1 rounded hover:bg-green-50 transition"
                    >
                        安装
                    </button>
                </div>
            )}
        </>
    );
}
