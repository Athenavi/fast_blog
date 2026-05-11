'use client';

/**
 * PWA 状态管理 Hook
 * 提供 PWA 相关状态的便捷访问
 */

import {useEffect, useState} from 'react';

interface PWAState {
    isSupported: boolean;
    isInstalled: boolean;
    isOnline: boolean;
    serviceWorkerActive: boolean;
}

export function usePWA(): PWAState {
    const [state, setState] = useState<PWAState>({
        isSupported: false,
        isInstalled: false,
        isOnline: true,
        serviceWorkerActive: false,
    });

    useEffect(() => {
        // 检查 PWA 支持
        const checkPWASupport = () => {
            const isSupported = 'serviceWorker' in navigator && 'PushManager' in window;

            // 检查是否已安装
            const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
            const isInWebAppiOS = (window.navigator as any).standalone === true;
            const isInstalled = isStandalone || isInWebAppiOS;

            // 检查网络状态
            const isOnline = navigator.onLine;

            // 检查 Service Worker 状态
            let serviceWorkerActive = false;
            if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
                serviceWorkerActive = true;
            }

            setState({
                isSupported,
                isInstalled,
                isOnline,
                serviceWorkerActive,
            });
        };

        checkPWASupport();

        // 监听各种状态变化
        const handleOnline = () => setState(prev => ({...prev, isOnline: true}));
        const handleOffline = () => setState(prev => ({...prev, isOnline: false}));

        const handleDisplayModeChange = (e: MediaQueryListEvent) => {
            setState(prev => ({
                ...prev,
                isInstalled: e.matches,
            }));
        };

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        const displayModeQuery = window.matchMedia('(display-mode: standalone)');
        displayModeQuery.addEventListener('change', handleDisplayModeChange);

        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
            displayModeQuery.removeEventListener('change', handleDisplayModeChange);
        };
    }, []);

    return state;
}
