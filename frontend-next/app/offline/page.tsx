'use client';

import {useEffect, useState} from 'react';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Button} from '@/components/ui/button';
import {Badge} from '@/components/ui/badge';
import {BookOpen, Home, RefreshCw, Wifi, WifiOff} from 'lucide-react';
import {motion} from 'framer-motion';

export default function OfflinePage() {
    const [isOnline, setIsOnline] = useState(false);
    const [cachedArticles, setCachedArticles] = useState<string[]>([]);

    useEffect(() => {
        // 监听网络状态
        const handleOnline = () => setIsOnline(true);
        const handleOffline = () => setIsOnline(false);

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        // 尝试从缓存中获取最近访问的文章
        if ('caches' in window) {
            caches.keys().then((cacheNames) => {
                cacheNames.forEach(async (cacheName) => {
                    const cache = await caches.open(cacheName);
                    const keys = await cache.keys();
                    const articleUrls = keys
                        .map((request) => request.url)
                        .filter((url) => url.includes('/articles/') || url.includes('/blog/'))
                        .slice(0, 5); // 最多显示5个

                    if (articleUrls.length > 0) {
                        setCachedArticles(articleUrls);
                    }
                });
            });
        }

        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, []);

    const handleReload = () => {
        window.location.reload();
    };

    const handleGoHome = () => {
        window.location.href = '/';
    };

    // 如果网络已恢复，自动刷新
    useEffect(() => {
        if (isOnline) {
            const timer = setTimeout(() => {
                window.location.reload();
            }, 1500);
            return () => clearTimeout(timer);
        }
    }, [isOnline]);

    return (
        <div
            className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 p-4">
            <motion.div
                initial={{opacity: 0, y: 20}}
                animate={{opacity: 1, y: 0}}
                transition={{duration: 0.5}}
                className="w-full max-w-md"
            >
                <Card className="shadow-xl border-2">
                    <CardHeader className="text-center space-y-4">
                        <motion.div
                            animate={isOnline ? {
                                scale: [1, 1.2, 1],
                                rotate: [0, 360]
                            } : {}}
                            transition={{duration: 1}}
                            className="mx-auto w-20 h-20 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center"
                        >
                            {isOnline ? (
                                <Wifi className="h-10 w-10 text-green-600 dark:text-green-400"/>
                            ) : (
                                <WifiOff className="h-10 w-10 text-blue-600 dark:text-blue-400"/>
                            )}
                        </motion.div>
                        <div>
                            <CardTitle className="text-2xl font-bold">
                                {isOnline ? '网络已恢复！' : '您已离线'}
                            </CardTitle>
                            <CardDescription className="text-base mt-2">
                                {isOnline
                                    ? '正在重新加载页面...'
                                    : '无法连接到网络，请检查您的网络连接'}
                            </CardDescription>
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {/* 状态提示 */}
                        <div
                            className={`rounded-lg p-4 border ${
                                isOnline
                                    ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                                    : 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800'
                            }`}
                        >
                            <p className={`text-sm ${
                                isOnline
                                    ? 'text-green-800 dark:text-green-200'
                                    : 'text-yellow-800 dark:text-yellow-200'
                            }`}>
                                {isOnline ? (
                                    <span>✅ <strong>太好了！</strong>网络已恢复，即将刷新页面...</span>
                                ) : (
                                    <span>💡 <strong>提示：</strong>部分已缓存的内容仍然可以访问。您可以尝试刷新页面或返回首页查看缓存的文章。</span>
                                )}
                            </p>
                        </div>

                        {/* 缓存的文章列表 */}
                        {cachedArticles.length > 0 && !isOnline && (
                            <div className="space-y-2">
                                <div className="flex items-center gap-2">
                                    <BookOpen className="h-4 w-4 text-blue-600"/>
                                    <span className="text-sm font-medium">可离线阅读的文章：</span>
                                </div>
                                <div className="space-y-2 max-h-40 overflow-y-auto">
                                    {cachedArticles.map((url, index) => {
                                        const title = url.split('/').pop() || `文章 ${index + 1}`;
                                        return (
                                            <a
                                                key={index}
                                                href={url}
                                                className="block p-3 bg-gray-50 dark:bg-gray-800 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                            >
                                                <div className="flex items-center justify-between">
                                                    <span className="text-sm truncate flex-1">{title}</span>
                                                    <Badge variant="secondary" className="ml-2">
                                                        缓存
                                                    </Badge>
                                                </div>
                                            </a>
                                        );
                                    })}
                                </div>
                            </div>
                        )}

                        {/* 操作按钮 */}
                        <div className="flex gap-3">
                            <Button onClick={handleReload} className="flex-1 gap-2" disabled={isOnline}>
                                <RefreshCw className={`h-4 w-4 ${isOnline ? 'animate-spin' : ''}`}/>
                                {isOnline ? '加载中...' : '刷新页面'}
                            </Button>
                            <Button onClick={handleGoHome} variant="outline" className="flex-1 gap-2">
                                <Home className="h-4 w-4"/>
                                返回首页
                            </Button>
                        </div>

                        {/* PWA 特性说明 */}
                        {!isOnline && (
                            <div className="pt-4 border-t">
                                <p className="text-xs text-muted-foreground text-center mb-2">
                                    FastBlog PWA - 随时随地阅读
                                </p>
                                <div className="flex justify-center gap-2">
                                    <Badge variant="outline" className="text-xs">
                                        📱 离线访问
                                    </Badge>
                                    <Badge variant="outline" className="text-xs">
                                        ⚡ 快速加载
                                    </Badge>
                                    <Badge variant="outline" className="text-xs">
                                        🔔 推送通知
                                    </Badge>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </motion.div>
        </div>
    );
}
