'use client';

import {useState, useEffect} from 'react';
import {X, Download} from 'lucide-react';

interface BeforeInstallPromptEvent extends Event {
    prompt: () => Promise<void>;
    userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export default function PWAInstallPrompt() {
    const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
    const [showPrompt, setShowPrompt] = useState(false);

    useEffect(() => {
        // 监听 beforeinstallprompt 事件
        const handler = (e: Event) => {
            e.preventDefault();
            setDeferredPrompt(e as BeforeInstallPromptEvent);
            // 延迟显示，避免立即弹出
            setTimeout(() => {
                setShowPrompt(true);
            }, 3000);
        };

        window.addEventListener('beforeinstallprompt', handler);

        return () => {
            window.removeEventListener('beforeinstallprompt', handler);
        };
    }, []);

    const handleInstall = async () => {
        if (!deferredPrompt) return;

        try {
            await deferredPrompt.prompt();
            const {outcome} = await deferredPrompt.userChoice;

            if (outcome === 'accepted') {
                console.log('[PWA] 用户接受了安装');
            } else {
                console.log('[PWA] 用户拒绝了安装');
            }
        } catch (error) {
            console.error('[PWA] 安装失败:', error);
        } finally {
            setDeferredPrompt(null);
            setShowPrompt(false);
        }
    };

    const handleDismiss = () => {
        setShowPrompt(false);
        // 保存到 localStorage，30天内不再显示
        localStorage.setItem('pwa-install-dismissed', Date.now().toString());
    };

    // 检查是否已经 dismissed
    useEffect(() => {
        const dismissed = localStorage.getItem('pwa-install-dismissed');
        if (dismissed) {
            const dismissedTime = parseInt(dismissed);
            const thirtyDays = 30 * 24 * 60 * 60 * 1000;

            if (Date.now() - dismissedTime < thirtyDays) {
                setShowPrompt(false);
            }
        }
    }, []);

    if (!showPrompt || !deferredPrompt) return null;

    return (
        <div className="fixed bottom-4 right-4 z-50 max-w-sm w-full">
            <div
                className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4 animate-slide-up">
                <div className="flex items-start justify-between">
                    <div className="flex-1">
                        <div className="flex items-center space-x-3">
                            <div className="flex-shrink-0">
                                <div
                                    className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                                    <Download className="w-6 h-6 text-white"/>
                                </div>
                            </div>
                            <div className="flex-1">
                                <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                                    安装 FastBlog
                                </h3>
                                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                                    添加到主屏幕，获得更好的体验
                                </p>
                            </div>
                        </div>

                        <div className="mt-3 flex space-x-2">
                            <button
                                onClick={handleInstall}
                                className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md transition-colors"
                            >
                                立即安装
                            </button>
                            <button
                                onClick={handleDismiss}
                                className="px-3 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 text-sm font-medium rounded-md transition-colors"
                            >
                                稍后
                            </button>
                        </div>
                    </div>

                    <button
                        onClick={handleDismiss}
                        className="ml-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                    >
                        <X className="w-4 h-4"/>
                    </button>
                </div>
            </div>
        </div>
    );
}
