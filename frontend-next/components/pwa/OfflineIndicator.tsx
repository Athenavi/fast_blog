'use client';

/**
 * 离线状态指示器
 * 显示网络连接状态和离线提示
 */

import {useEffect, useState} from 'react';
import {Wifi, WifiOff} from 'lucide-react';

export default function OfflineIndicator() {
    const [isOnline, setIsOnline] = useState(true);
    const [showOfflineMessage, setShowOfflineMessage] = useState(false);

    useEffect(() => {
        // 初始状态 - 添加延迟确保准确检测
        const checkInitialStatus = () => {
            setIsOnline(navigator.onLine);
            console.log('[OfflineIndicator] Initial network status:', navigator.onLine ? 'online' : 'offline');
        };

        setTimeout(checkInitialStatus, 200);

        // 监听网络状态变化
        const handleOnline = () => {
            setIsOnline(true);
            // 3秒后隐藏离线消息
            setTimeout(() => setShowOfflineMessage(false), 3000);
        };

        const handleOffline = () => {
            setIsOnline(false);
            setShowOfflineMessage(true);
        };

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, []);

    // 如果在线且不显示离线消息，不渲染
    if (isOnline && !showOfflineMessage) return null;

    return (
        <div
            className={`fixed top-4 left-1/2 -translate-x-1/2 z-50 transition-all duration-300 ${
                showOfflineMessage ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-4'
            }`}
        >
            <div
                className={`flex items-center gap-2 px-4 py-2 rounded-full shadow-lg ${
                    isOnline
                        ? 'bg-green-500 text-white'
                        : 'bg-red-500 text-white'
                }`}
            >
                {isOnline ? (
                    <>
                        <Wifi className="w-4 h-4"/>
                        <span className="text-sm font-medium">已恢复网络连接</span>
                    </>
                ) : (
                    <>
                        <WifiOff className="w-4 h-4"/>
                        <span className="text-sm font-medium">离线模式 - 部分内容可能不可用</span>
                    </>
                )}
            </div>
        </div>
    );
}
