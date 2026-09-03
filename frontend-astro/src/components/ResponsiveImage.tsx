/**
 * ResponsiveImage - 响应式图片组件
 * 支持懒加载、占位符、多种降级策略
 *
 * 使用示例:
 * ```tsx
 * <ResponsiveImage
 *   src="/image.webp"
 *   alt="描述"
 *   sizes="(max-width: 768px) 100vw, 50vw"
 *   placeholder="blur"
 *   priority={false}
 * />
 * ```
 */

'use client';

import React, {memo, useEffect, useRef, useState} from 'react';
import {useNetworkState} from '@/lib/hooks/useNetworkState';

export interface ResponsiveImageProps {
  src: string;
  alt: string;
  width?: number | string;
  height?: number | string;
  sizes?: string;
  className?: string;
  /** 是否优先级加载（首屏图片设为 true） */
  priority?: boolean;
  /** 占位符类型 */
  placeholder?: 'blur' | 'color' | 'skeleton' | 'none';
  /** 模糊占位数据 (base64 small image) */
  blurDataUrl?: string;
  /** 颜色占位 */
  placeholderColor?: string;
  /** 加载失败回调 */
  onError?: () => void;
  /** 加载完成回调 */
  onLoad?: () => void;
  /** 最大重试次数 */
  maxRetries?: number;
}

const ResponsiveImage = memo(({
                                src,
                                alt,
                                width,
                                height,
                                sizes,
                                className = '',
                                priority = false,
                                placeholder = 'skeleton',
                                blurDataUrl,
                                placeholderColor,
                                onError,
                                onLoad,
                                maxRetries = 1,
                              }: ResponsiveImageProps) => {
  const [loaded, setLoaded] = useState(priority);
  const [error, setError] = useState(false);
  const [srcToUse, setSrcToUse] = useState(src);
  const retries = useRef(0);
  const imgRef = useRef<HTMLImageElement>(null);
  const {isSlow, saveData} = useNetworkState();

  // 弱网络下自动降级：尝试使用更小的图片
  useEffect(() => {
    if (isSlow || saveData) {
      // 如果URL包含尺寸参数，尝试降级到较小尺寸
      if (src.includes('w_') || src.includes('/resize/')) {
        const degraded = src
          .replace(/w_(\d+)/, (_, w) => `w_${Math.max(320, Math.round(Number(w) / 2))}`)
          .replace(/\/resize\/(\d+)/, (_, w) => `/resize/${Math.max(320, Math.round(Number(w) / 2))}`);
        if (degraded !== src) {
          setSrcToUse(degraded);
        }
      }
    }
  }, [src, isSlow, saveData]);

  const handleError = () => {
    if (retries.current < maxRetries) {
      retries.current++;
      setSrcToUse(src);
    } else {
      setError(true);
      onError?.();
    }
  };

  const handleLoad = () => {
    setLoaded(true);
    onLoad?.();

    // 使用 decode() API 确保不会因为大图解码阻塞主线程
    const img = imgRef.current;
    if (img && typeof img.decode === 'function') {
      img.decode().catch(() => {
      });
    }
  };

  // 占位符渲染
  const renderPlaceholder = () => {
    if (placeholder === 'none') return null;

    const style: React.CSSProperties = {
      width: width || '100%',
      height: height || 'auto',
      aspectRatio: width && height ? `${width} / ${height}` : undefined,
    };

    if (placeholder === 'blur' && blurDataUrl) {
      return (
        <div
          className="responsive-img-placeholder"
          style={{...style, backgroundImage: `url(${blurDataUrl})`, backgroundSize: 'cover'}}
        />
      );
    }

    if (placeholder === 'color') {
      return (
        <div
          className="responsive-img-placeholder"
          style={{...style, backgroundColor: placeholderColor || 'transparent'}}
        />
      );
    }

    // skeleton placeholder (default)
    return (
      <div
        className="skeleton responsive-img-placeholder rounded-lg"
        style={{...style}}
      />
    );
  };

  if (error) {
    return (
      <div
        className={`responsive-img-error ${className}`}
        style={{
          width: width || '100%',
          height: height || 'auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#f1f5f9',
        }}
      >
        <svg className="w-12 h-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
        </svg>
      </div>
    );
  }

  return (
    <div className={`responsive-img-wrapper ${className}`} style={{position: 'relative'}}>
      {renderPlaceholder()}
      <img
        ref={imgRef}
        src={srcToUse}
        alt={alt}
        width={typeof width === 'number' ? width : undefined}
        height={typeof height === 'number' ? height : undefined}
        sizes={sizes}
        loading={priority ? 'eager' : 'lazy'}
        decoding={priority ? 'sync' : 'async'}
        fetchpriority={priority ? 'high' : 'low'}
        className={`responsive-img ${loaded ? 'loaded' : 'img-lazy'}`}
        style={{
          position: priority ? 'relative' : 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transition: loaded ? 'none' : 'opacity 0.3s ease-in',
        }}
        onLoad={handleLoad}
        onError={handleError}
      />
    </div>
  );
});

ResponsiveImage.displayName = 'ResponsiveImage';

export default ResponsiveImage;
