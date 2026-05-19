/**
 * 页面预取组件
 * 在用户悬停或可见时预取页面资源
 */

'use client';

import React, {useEffect, useRef} from 'react';
import Link from 'next/link';
import {useRouter} from 'next/navigation';

interface PrefetchLinkProps {
    href: string;
    children: React.ReactNode;
    className?: string;
    prefetchOnHover?: boolean;
    prefetchOnVisible?: boolean;
    prefetchTimeout?: number;
}

export const PrefetchLink: React.FC<PrefetchLinkProps> = ({
                                                              href,
                                                              children,
                                                              className,
                                                              prefetchOnHover = true,
                                                              prefetchOnVisible = false,
                                                              prefetchTimeout = 1000,
                                                              ...props
                                                          }) => {
    const router = useRouter();
    const linkRef = useRef<HTMLAnchorElement>(null);
    const hasPrefetched = useRef(false);

    // 预取页面
    const prefetch = () => {
        if (!hasPrefetched.current) {
            router.prefetch(href);
            hasPrefetched.current = true;
        }
    };

    // 设置悬停预取
    useEffect(() => {
        if (prefetchOnHover && linkRef.current) {
            const element = linkRef.current;

            const handleMouseEnter = () => {
                prefetch();
            };

            element.addEventListener('mouseenter', handleMouseEnter);

            return () => {
                element.removeEventListener('mouseenter', handleMouseEnter);
            };
        }
    }, [prefetchOnHover, href]);

    // 设置可见性预取
    useEffect(() => {
        if (prefetchOnVisible && linkRef.current) {
            const observer = new IntersectionObserver(
                (entries) => {
                    entries.forEach((entry) => {
                        if (entry.isIntersecting && !hasPrefetched.current) {
                            setTimeout(() => {
                                prefetch();
                            }, prefetchTimeout);
                        }
                    });
                },
                {threshold: 0.5}
            );

            observer.observe(linkRef.current);

            return () => {
                observer.disconnect();
            };
        }
    }, [prefetchOnVisible, prefetchTimeout, href]);

    return (
        <Link
            ref={linkRef}
            href={href}
            className={className}
            onMouseEnter={prefetchOnHover ? undefined : () => prefetch()}
            {...props}
        >
            {children}
        </Link>
    );
};

// 批量预取组件
interface BatchPrefetchProps {
    urls: string[];
    delay?: number;
    children: React.ReactNode;
}

export const BatchPrefetch: React.FC<BatchPrefetchProps> = ({
                                                                urls,
                                                                delay = 2000,
                                                                children
                                                            }) => {
    const router = useRouter();

    useEffect(() => {
        const timer = setTimeout(() => {
            urls.forEach(url => {
                router.prefetch(url);
            });
        }, delay);

        return () => clearTimeout(timer);
    }, [urls, delay, router]);

    return <>{children}</>;
};

export default PrefetchLink;
