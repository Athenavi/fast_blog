'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {pwaEnhancer} from '@/lib/pwa-enhancer';
import {Bell, Database, RefreshCw, Smartphone, Wifi, Zap} from 'lucide-react';
import {useToast} from '@/hooks/use-toast';

/**
 * PWA 功能面板组件
 * 展示和管理 PWA 相关功能
 */
export default function PWAFeaturesPanel() {
    const {toast} = useToast();
    const [pwaStatus, setPwaStatus] = useState(pwaEnhancer.getPWAInstallStatus());
    const [cacheSize, setCacheSize] = useState<number>(0);
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        // 加载缓存大小
        loadCacheSize();
    }, []);

    const loadCacheSize = async () => {
        const size = await pwaEnhancer.getCacheSize();
        setCacheSize(size);
    };

    // 格式化字节大小
    const formatBytes = (bytes: number): string => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
    };

    // 请求通知权限
    const handleRequestNotification = async () => {
        setIsLoading(true);
        const permission = await pwaEnhancer.requestNotificationPermission();

        if (permission === 'granted') {
            toast({
                title: '✅ 成功',
                description: '已授予通知权限',
            });

            // 发送测试通知
            await pwaEnhancer.sendLocalNotification({
                title: 'FastBlog',
                body: '推送通知已启用！您将收到最新文章的通知。',
                icon: '/icons/icon-192x192.png',
            });
        } else if (permission === 'denied') {
            toast({
                title: '❌ 拒绝',
                description: '您已拒绝通知权限',
                variant: 'destructive',
            });
        }

        setIsLoading(false);
    };

    // 清除缓存
    const handleClearCache = async () => {
        setIsLoading(true);
        const success = await pwaEnhancer.clearAllCaches();

        if (success) {
            toast({
                title: '✅ 成功',
                description: '缓存已清除',
            });
            await loadCacheSize();
        } else {
            toast({
                title: '❌ 失败',
                description: '清除缓存失败',
                variant: 'destructive',
            });
        }

        setIsLoading(false);
    };

    // 注册后台同步
    const handleRegisterSync = async () => {
        setIsLoading(true);
        const success = await pwaEnhancer.registerBackgroundSync('sync-articles');

        if (success) {
            toast({
                title: '✅ 成功',
                description: '后台同步已注册，网络恢复时将自动同步',
            });
        } else {
            toast({
                title: '⚠️ 提示',
                description: '您的浏览器不支持后台同步',
            });
        }

        setIsLoading(false);
    };

    // 刷新状态
    const handleRefresh = async () => {
        setPwaStatus(pwaEnhancer.getPWAInstallStatus());
        await loadCacheSize();
        toast({
            title: '🔄 已刷新',
            description: 'PWA 状态已更新',
        });
    };

    return (
        <Card className="w-full max-w-2xl">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <Smartphone className="h-5 w-5"/>
                            PWA 功能中心
                        </CardTitle>
                        <CardDescription>
                            管理 Progressive Web App 功能和设置
                        </CardDescription>
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleRefresh}
                        disabled={isLoading}
                    >
                        <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`}/>
                    </Button>
                </div>
            </CardHeader>
            <CardContent className="space-y-6">
                {/* PWA 状态 */}
                <div className="space-y-3">
                    <h3 className="text-sm font-medium">应用状态</h3>
                    <div className="grid grid-cols-3 gap-3">
                        <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                            <div className="flex items-center gap-2 mb-1">
                                <Smartphone className="h-4 w-4 text-blue-600"/>
                                <span className="text-xs text-muted-foreground">安装状态</span>
                            </div>
                            <Badge variant={pwaStatus.isInstalled ? 'default' : 'secondary'}>
                                {pwaStatus.isInstalled ? '已安装' : '未安装'}
                            </Badge>
                        </div>

                        <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                            <div className="flex items-center gap-2 mb-1">
                                <Wifi className="h-4 w-4 text-green-600"/>
                                <span className="text-xs text-muted-foreground">离线访问</span>
                            </div>
                            <Badge variant="default">支持</Badge>
                        </div>

                        <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                            <div className="flex items-center gap-2 mb-1">
                                <Zap className="h-4 w-4 text-yellow-600"/>
                                <span className="text-xs text-muted-foreground">快速加载</span>
                            </div>
                            <Badge variant="default">已优化</Badge>
                        </div>
                    </div>
                </div>

                {/* 缓存信息 */}
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <h3 className="text-sm font-medium flex items-center gap-2">
                            <Database className="h-4 w-4"/>
                            缓存管理
                        </h3>
                        <span className="text-xs text-muted-foreground">
                            {formatBytes(cacheSize)}
                        </span>
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleClearCache}
                        disabled={isLoading || cacheSize === 0}
                        className="w-full"
                    >
                        <Database className="h-4 w-4 mr-2"/>
                        清除所有缓存
                    </Button>
                </div>

                {/* 功能操作 */}
                <div className="space-y-3">
                    <h3 className="text-sm font-medium">功能操作</h3>

                    <div className="space-y-2">
                        <Button
                            variant="outline"
                            onClick={handleRequestNotification}
                            disabled={isLoading}
                            className="w-full justify-start"
                        >
                            <Bell className="h-4 w-4 mr-2"/>
                            启用推送通知
                        </Button>

                        <Button
                            variant="outline"
                            onClick={handleRegisterSync}
                            disabled={isLoading}
                            className="w-full justify-start"
                        >
                            <RefreshCw className="h-4 w-4 mr-2"/>
                            注册后台同步
                        </Button>
                    </div>
                </div>

                {/* 提示信息 */}
                <div
                    className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                    <p className="text-sm text-blue-800 dark:text-blue-200">
                        💡 <strong>提示：</strong>将 FastBlog 添加到主屏幕，享受原生应用般的体验！
                    </p>
                    {!pwaStatus.isInstalled && (
                        <p className="text-xs text-blue-600 dark:text-blue-300 mt-2">
                            在浏览器菜单中选择"添加到主屏幕"或"安装应用"
                        </p>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
