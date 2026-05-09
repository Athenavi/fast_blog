'use client';

import React, {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {useToast} from '@/hooks/use-toast';
import {Bell, Download, RefreshCw, Smartphone, Wifi, WifiOff, X} from 'lucide-react';

interface PWAInstallPromptProps {
    showPrompt?: boolean;
}

export default function PWAInstallPrompt({showPrompt = true}: PWAInstallPromptProps) {
    const {toast} = useToast();
    const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
    const [isInstallable, setIsInstallable] = useState(false);
    const [isInstalled, setIsInstalled] = useState(false);
    const [isVisible, setIsVisible] = useState(false);
    const [isOffline, setIsOffline] = useState(!navigator.onLine);
    const [updateAvailable, setUpdateAvailable] = useState(false);

    useEffect(() => {
        // 检查是否已安装
        if (window.matchMedia('(display-mode: standalone)').matches) {
            setIsInstalled(true);
            return;
        }

        // 监听beforeinstallprompt事件
        const handler = (e: Event) => {
            e.preventDefault();
            setDeferredPrompt(e);
            setIsInstallable(true);

            // 延迟显示提示，避免打扰用户
            setTimeout(() => {
                setIsVisible(true);
            }, 3000);
        };

        window.addEventListener('beforeinstallprompt', handler);

        // 监听网络状态
        const handleOnline = () => setIsOffline(false);
        const handleOffline = () => setIsOffline(true);

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        // 检查Service Worker更新
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.ready.then((registration) => {
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    if (newWorker) {
                        newWorker.addEventListener('statechange', () => {
                            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                                setUpdateAvailable(true);
                                toast({
                                    title: '更新可用',
                                    description: '新版本已准备好，请刷新页面',
                                    action: (
                                        <Button size="sm" onClick={() => window.location.reload()}>
                                            刷新
                                        </Button>
                                    ),
                                });
                            }
                        });
                    }
                });
            });
        }

        return () => {
            window.removeEventListener('beforeinstallprompt', handler);
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, []);

    const handleInstall = async () => {
        if (!deferredPrompt) {
            toast({
                title: '提示',
                description: '当前浏览器不支持自动安装',
            });
            return;
        }

        try {
            await deferredPrompt.prompt();
            const choiceResult = await deferredPrompt.userChoice;

            if (choiceResult.outcome === 'accepted') {
                console.log('[PWA] User accepted the install prompt');
                toast({
                    title: '安装成功',
                    description: 'FastBlog 已添加到您的桌面',
                });
            } else {
                console.log('[PWA] User dismissed the install prompt');
            }

            setDeferredPrompt(null);
            setIsVisible(false);
        } catch (error) {
            console.error('[PWA] Install failed:', error);
            toast({
                title: '错误',
                description: '安装失败，请稍后重试',
                variant: 'destructive',
            });
        }
    };

    const handleDismiss = () => {
        setIsVisible(false);
        // 保存用户选择，30天内不再显示
        if (typeof window !== 'undefined') {
            localStorage.setItem('pwa-install-dismissed', Date.now().toString());
        }
    };

    const handleUpdate = () => {
        if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage({type: 'SKIP_WAITING'});
            window.location.reload();
        }
    };

    // 检查是否应该显示
    const dismissedTime = typeof window !== 'undefined' ? localStorage.getItem('pwa-install-dismissed') : null;
    const shouldShow = showPrompt &&
        isInstallable &&
        !isInstalled &&
        isVisible &&
        (!dismissedTime || Date.now() - parseInt(dismissedTime) > 30 * 24 * 60 * 60 * 1000);

    if (!shouldShow && !isOffline && !updateAvailable) {
        return null;
    }

    return (
        <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-sm">
            {/* 离线提示 */}
            {isOffline && (
                <Card className="bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800">
                    <CardContent className="p-4 flex items-center gap-3">
                        <WifiOff className="h-5 w-5 text-yellow-600"/>
                        <div className="flex-1">
                            <p className="text-sm font-medium">离线模式</p>
                            <p className="text-xs text-muted-foreground">部分内容可能不可用</p>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* 更新提示 */}
            {updateAvailable && (
                <Card className="bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
                    <CardContent className="p-4 flex items-center gap-3">
                        <RefreshCw className="h-5 w-5 text-blue-600"/>
                        <div className="flex-1">
                            <p className="text-sm font-medium">新版本可用</p>
                            <p className="text-xs text-muted-foreground">点击刷新以获取最新功能</p>
                        </div>
                        <Button size="sm" onClick={handleUpdate}>
                            刷新
                        </Button>
                    </CardContent>
                </Card>
            )}

            {/* 安装提示 */}
            {shouldShow && (
                <Card className="shadow-lg animate-in slide-in-from-bottom-4">
                    <CardHeader className="pb-3">
                        <div className="flex items-start justify-between">
                            <div className="flex items-center gap-2">
                                <Smartphone className="h-5 w-5 text-primary"/>
                                <CardTitle className="text-base">安装 FastBlog</CardTitle>
                            </div>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0"
                                onClick={handleDismiss}
                            >
                                <X className="h-4 w-4"/>
                            </Button>
                        </div>
                        <CardDescription>
                            将 FastBlog 添加到桌面，获得更好的体验
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <div className="flex gap-2 text-xs text-muted-foreground">
                            <Badge variant="secondary" className="gap-1">
                                <Wifi className="h-3 w-3"/>
                                离线访问
                            </Badge>
                            <Badge variant="secondary" className="gap-1">
                                <Bell className="h-3 w-3"/>
                                推送通知
                            </Badge>
                            <Badge variant="secondary" className="gap-1">
                                <Smartphone className="h-3 w-3"/>
                                原生体验
                            </Badge>
                        </div>

                        <div className="flex gap-2">
                            <Button onClick={handleInstall} className="flex-1 gap-2">
                                <Download className="h-4 w-4"/>
                                立即安装
                            </Button>
                            <Button variant="outline" onClick={handleDismiss}>
                                稍后再说
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
