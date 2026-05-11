/**
 * 性能优化组件
 * 提供资源预加载、懒加载等功能
 */

'use client';

import React, {useEffect, useRef} from 'react';

interface PerformanceOptimizerProps {
    children: React.ReactNode;
    enablePreload?: boolean;
    enableLazyLoad?: boolean;
    preloadUrls?: string[];
}

export const PerformanceOptimizer: React.FC<PerformanceOptimizerProps> = ({
                                                                              children,
                                                                              enablePreload = true,
                                                                              enableLazyLoad = true,
                                                                              preloadUrls = []
                                                                          }) => {
    const observerRef = useRef<IntersectionObserver | null>(null);

    useEffect(() => {
        // 预加载关键资源
        if (enablePreload && preloadUrls.length > 0) {
            preloadResources(preloadUrls);
        }

        // 设置图片懒加载
        if (enableLazyLoad) {
            setupLazyLoading();
        }

        return () => {
            if (observerRef.current) {
                observerRef.current.disconnect();
                observerRef.current = null;
            }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []); // 只在挂载时执行一次

    // 预加载资源函数
    const preloadResources = (urls: string[]) => {
        urls.forEach(url => {
            // 预加载链接
            const link = document.createElement('link');
            link.rel = 'preload';
            link.href = url;
            link.as = getResourceType(url);
            document.head.appendChild(link);
        });
    };

    // 根据URL确定资源类型
    const getResourceType = (url: string): string => {
        if (url.endsWith('.js')) return 'script';
        if (url.endsWith('.css')) return 'style';
        if (url.match(/\.(png|jpg|jpeg|gif|svg|webp)$/)) return 'image';
        if (url.endsWith('.woff2') || url.endsWith('.woff')) return 'font';
        return 'fetch';
    };

    // 设置懒加载
    const setupLazyLoading = () => {
        if ('IntersectionObserver' in window) {
            observerRef.current = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target as HTMLImageElement;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                            observerRef.current?.unobserve(img);
                        }
                    }
                });
            });

            // 观察所有带 data-src 属性的图片
            setTimeout(() => {
                const lazyImages = document.querySelectorAll('img[data-src]');
                lazyImages.forEach(img => {
                    observerRef.current?.observe(img);
                });
            }, 100);
        }
    };

    return <>{children}</>;
};

// 预加载关键页面的高阶组件
export const withPreload = (WrappedComponent: React.ComponentType<any>, urls: string[]) => {
    return function PreloadedComponent(props: any) {
        useEffect(() => {
            // 预加载指定URL
            urls.forEach(url => {
                const link = document.createElement('link');
                link.rel = 'prefetch';
                link.href = url;
                document.head.appendChild(link);
            });
        }, []);

        return <WrappedComponent {...props} />;
    };
};

// 懒加载组件
export const LazyComponent = ({component: Component, fallback = null, ...props}: any) => {
    const [isVisible, setIsVisible] = React.useState(false);
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    setIsVisible(true);
                    observer.disconnect();
                }
            },
            {threshold: 0.1}
        );

        if (ref.current) {
            observer.observe(ref.current);
        }

        return () => observer.disconnect();
    }, []);

    return (
        <div ref={ref}>
            {isVisible ? <Component {...props} /> : fallback}
        </div>
    );
};

export default PerformanceOptimizer;
