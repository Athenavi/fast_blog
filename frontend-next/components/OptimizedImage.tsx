'use client';

import React, {useEffect, useRef, useState} from 'react';

interface OptimizedImageProps {
    src: string;
    alt: string;
    width?: number;
    height?: number;
    className?: string;
    priority?: boolean; // 是否优先加载（首屏图片）
    sizes?: string; // 响应式尺寸断点
    quality?: number; // 图片质量 1-100
    format?: 'webp' | 'jpeg' | 'png'; // 优先格式
    onLoad?: () => void;
    onError?: () => void;
}

/**
 * 优化的图片组件
 * 支持懒加载、WebP 格式、响应式图片
 */
const OptimizedImage: React.FC<OptimizedImageProps> = ({
                                                           src,
                                                           alt,
                                                           width,
                                                           height,
                                                           className = '',
                                                           priority = false,
                                                           sizes,
                                                           quality = 85,
                                                           format = 'webp',
                                                           onLoad,
                                                           onError,
                                                       }) => {
    const [isLoaded, setIsLoaded] = useState(false);
    const [isInView, setIsInView] = useState(priority); // 如果是优先加载，直接显示
    const [error, setError] = useState(false);
    const imgRef = useRef<HTMLImageElement>(null);

    // 懒加载：使用 IntersectionObserver
    useEffect(() => {
        if (priority || isInView) return;

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        setIsInView(true);
                        observer.unobserve(entry.target);
                    }
                });
            },
            {
                rootMargin: '200px', // 提前 200px 开始加载
                threshold: 0,
            }
        );

        if (imgRef.current) {
            observer.observe(imgRef.current);
        }

        return () => {
            if (imgRef.current) {
                observer.unobserve(imgRef.current);
            }
        };
    }, [priority]);

    // 生成 WebP 和 fallback URL
    const webpSrc = format === 'webp' ? `${src}?format=webp&quality=${quality}` : src;
    const fallbackSrc = `${src}?format=jpeg&quality=${quality}`;

    // 处理加载完成
    const handleLoad = () => {
        setIsLoaded(true);
        onLoad?.();
    };

    // 处理加载错误
    const handleError = () => {
        setError(true);
        onError?.();
    };

    return (
        <div
            ref={imgRef}
            className={`relative overflow-hidden ${className}`}
            style={{width, height}}
        >
            {/* 加载占位符 */}
            {!isLoaded && !error && (
                <div className="absolute inset-0 bg-gray-200 dark:bg-gray-700 animate-pulse"/>
            )}

            {/* 错误占位符 */}
            {error && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-100 dark:bg-gray-800">
                    <svg
                        className="w-12 h-12 text-gray-400"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                        />
                    </svg>
                </div>
            )}

            {/* 图片 */}
            {isInView && !error && (
                <picture>
                    {/* WebP 格式（现代浏览器） */}
                    <source srcSet={webpSrc} type="image/webp"/>

                    {/* JPEG/PNG fallback */}
                    <img
                        src={fallbackSrc}
                        alt={alt}
                        width={width}
                        height={height}
                        sizes={sizes}
                        loading={priority ? 'eager' : 'lazy'}
                        decoding="async"
                        onLoad={handleLoad}
                        onError={handleError}
                        className={`transition-opacity duration-300 ${
                            isLoaded ? 'opacity-100' : 'opacity-0'
                        }`}
                    />
                </picture>
            )}
        </div>
    );
};

export default OptimizedImage;
