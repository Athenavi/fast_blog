/**
 * 岛屿模式组件 - Islands Architecture
 *
 * 将页面拆分为独立的交互"岛屿"，其余部分保持静态 HTML
 * 这是 Astro 的核心思想，我们在这里用 React 模拟实现
 */

'use client';

import React, {lazy, Suspense, useEffect, useState} from 'react';
import LoadingState from '@/components/LoadingState';

/**
 * 岛屿组件包装器
 * 只在需要交互时才加载 JavaScript
 */
export function Island({
                           component,
                           fallback = <LoadingState/>,
                           ...props
                       }: {
    component: () => Promise<any>;
    fallback?: React.ReactNode;
    [key: string]: any;
}) {
    const LazyComponent = lazy(component);

    return (
        <Suspense fallback={fallback}>
            <LazyComponent {...props} />
        </Suspense>
    );
}

/**
 * 客户端仅渲染组件
 * 确保组件只在浏览器中渲染（SSR 时显示占位符）
 */
export function ClientOnly({
                               children,
                               fallback = null,
                           }: {
    children: React.ReactNode;
    fallback?: React.ReactNode;
}) {
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    if (!mounted) {
        return <>{fallback}</>;
    }

    return <>{children}</>;
}

/**
 * 视口内加载组件
 * 只有当组件进入视口才加载其 JavaScript
 */
export function ViewportIsland({
                                   component,
                                   rootMargin = '200px',
                                   threshold = 0.1,
                                   placeholder,
                                   ...props
                               }: {
    component: () => Promise<any>;
    rootMargin?: string;
    threshold?: number;
    placeholder?: React.ReactNode;
    [key: string]: any;
}) {
    const [isVisible, setIsVisible] = useState(false);
    const [ref, setRef] = useState<HTMLDivElement | null>(null);

    useEffect(() => {
        if (!ref) return;

        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    setIsVisible(true);
                    observer.disconnect();
                }
            },
            {rootMargin, threshold}
        );

        observer.observe(ref);
        return () => observer.disconnect();
    }, [ref, rootMargin, threshold]);

    if (!isVisible) {
        return (
            <div ref={setRef} style={{minHeight: '100px'}}>
                {placeholder || <div className="animate-pulse bg-gray-200 dark:bg-gray-800 rounded-lg h-32"/>}
            </div>
        );
    }

    const LazyComponent = lazy(component);

    return (
        <div ref={setRef}>
            <Suspense fallback={placeholder}>
                <LazyComponent {...props} />
            </Suspense>
        </div>
    );
}

/**
 * 轻量级评论组件（示例）
 * 仅在用户滚动到评论区时才加载
 */
export function CommentIsland({articleId}: { articleId: number }) {
    return (
        <ViewportIsland
            component={() => import('@/components/CommentSection')}
            placeholder={
                <div className="space-y-4">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="animate-pulse bg-gray-100 dark:bg-gray-800 rounded-lg p-4 h-24"/>
                    ))}
                </div>
            }
            articleId={articleId}
        />
    );
}

/**
 * 轻量级搜索组件（示例）
 */
export function SearchIsland() {
    return (
        <ClientOnly fallback={<div className="w-full h-12 bg-gray-100 dark:bg-gray-800 rounded-xl"/>}>
            <Island
                component={() => import('@/app/search/ClientSearchPage')}
                fallback={<div className="w-full h-12 bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse"/>}
            />
        </ClientOnly>
    );
}

/**
 * 社交分享组件（示例）
 * 仅在用户交互时加载
 */
export function SocialShareIsland({url, title}: { url: string; title: string }) {
    const [showShare, setShowShare] = useState(false);

    if (!showShare) {
        return (
            <button
                onClick={() => setShowShare(true)}
                className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
                分享文章
            </button>
        );
    }

    return (
        <Island
            component={() => import('@/components/SocialShare')}
            fallback={<div className="flex gap-2">{[1, 2, 3, 4].map(i => <div key={i}
                                                                              className="w-10 h-10 bg-gray-200 rounded-full animate-pulse"/>)}</div>}
            url={url}
            title={title}
        />
    );
}
