'use client';

/**
 * PWA 安装提示组件
 * 当应用可安装时显示安装按钮
 */

import {useEffect, useState} from 'react';
import {Button} from '@/components/ui/button';
import {Card} from '@/components/ui/card';
import {Download, Smartphone, X} from 'lucide-react';

interface BeforeInstallPromptEvent extends Event {
    userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;

    prompt(): Promise<void>;
}

export default function PWAInstallPrompt() {
    const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
    const [showPrompt, setShowPrompt] = useState(false);
    const [isInstalled, setIsInstalled] = useState(false);

    useEffect(() => {
        // 检查是否已安装
        const checkIfInstalled = () => {
            const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
            const isInWebAppiOS = (window.navigator as any).standalone === true;
            setIsInstalled(isStandalone || isInWebAppiOS);
        };

        checkIfInstalled();

        // 监听 beforeinstallprompt 事件
        const handleBeforeInstallPrompt = (e: Event) => {
            e.preventDefault();
            setDeferredPrompt(e as BeforeInstallPromptEvent);
            setShowPrompt(true);
        };

        // 监听 appinstalled 事件
        const handleAppInstalled = async () => {
            console.log('[PWA] App installed successfully');
            setIsInstalled(true);
            setShowPrompt(false);
            setDeferredPrompt(null);
        };

        window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
        window.addEventListener('appinstalled', handleAppInstalled);

        return () => {
            window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
            window.removeEventListener('appinstalled', handleAppInstalled);
        };
    }, []);

    const handleInstall = async () => {
        if (!deferredPrompt) return;

        try {
            await deferredPrompt.prompt();
            const {outcome} = await deferredPrompt.userChoice;

            if (outcome === 'accepted') {
                console.log('[PWA] User accepted the install prompt');
            } else {
                console.log('[PWA] User dismissed the install prompt');
            }

            setDeferredPrompt(null);
            setShowPrompt(false);
        } catch (error) {
            console.error('[PWA] Install prompt failed:', error);
        }
    };

    const handleDismiss = () => {
        setShowPrompt(false);
        // 可以在这里设置 localStorage 标记，避免短期内再次显示
        localStorage.setItem('pwa-install-dismissed', Date.now().toString());
    };

    // 如果已安装或不显示提示，不渲染
    if (isInstalled || !showPrompt) return null;

    return (
        <div className="fixed bottom-4 right-4 z-50 animate-in slide-in-from-bottom-4 fade-in duration-300">
            <Card className="p-4 shadow-lg max-w-sm bg-background border-primary/20">
                <div className="flex items-start gap-3">
                    <div
                        className="flex-shrink-0 w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                        <Smartphone className="w-5 h-5 text-primary"/>
                    </div>

                    <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-sm mb-1">安装 FastBlog</h3>
                        <p className="text-xs text-muted-foreground mb-3">
                            将 FastBlog 安装到您的设备，获得更好的体验和离线访问功能
                        </p>

                        <div className="flex gap-2">
                            <Button
                                size="sm"
                                onClick={handleInstall}
                                className="flex-1"
                            >
                                <Download className="w-4 h-4 mr-1"/>
                                立即安装
                            </Button>

                            <Button
                                size="sm"
                                variant="ghost"
                                onClick={handleDismiss}
                                className="flex-shrink-0"
                            >
                                <X className="w-4 h-4"/>
                            </Button>
                        </div>
                    </div>
                </div>
            </Card>
        </div>
    );
}
