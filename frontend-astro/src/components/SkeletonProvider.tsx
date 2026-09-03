/**
 * SkeletonProvider - 骨架屏上下文提供者
 * 提供全局骨架屏配置和统一加载状态管理
 */

'use client';

import React, {createContext, useCallback, useContext, useMemo, useState} from 'react';
import {Skeleton, SkeletonCard} from '@/components/ui/skeleton';
import {getFullMediaUrl} from '@/lib/utils';
import {ImageIcon} from 'lucide-react';

export interface SkeletonTheme {
  className?: string;
  variant?: 'pulse' | 'shimmer';
  duration?: number;
}

interface SkeletonProviderContextValue {
  theme: SkeletonTheme;
  loadingStates: Map<string, boolean>;
  setLoading: (key: string, loading: boolean) => void;
  ArticleCard: React.FC<{ count?: number }>;
  MediaCard: React.FC<{ count?: number }>;
  UserCard: React.FC<{ count?: number }>;
  LazyImage: React.FC<LazyImageProps>;
}

const SkeletonProviderContext = createContext<SkeletonProviderContextValue | null>(null);

export interface LazyImageProps {
  src: string;
  threshold?: number;
  rootMargin?: string;
  aspectRatio?: string;
  width?: string | number;
  height?: string | number;
  showProgress?: boolean;
  className?: string;
  style?: React.CSSProperties;
  alt?: string;
}

export const LazyImage: React.FC<LazyImageProps> = React.memo(({
                                                                 src,
                                                                 threshold = 0.1,
                                                                 rootMargin = '200px',
                                                                 aspectRatio = '16/10',
                                                                 width,
                                                                 height,
                                                                 showProgress = false,
                                                                 className = '',
                                                                 style = {},
                                                                 alt = '',
                                                               }) => {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  const [progress, setProgress] = useState(0);
  const imgRef = React.useRef<HTMLImageElement>(null);
  const observerRef = React.useRef<IntersectionObserver | null>(null);
  const shouldLoad = React.useRef(false);

  React.useEffect(() => {
    const img = imgRef.current;
    if (!img) return;

    observerRef.current = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry.isIntersecting && !shouldLoad.current) {
          shouldLoad.current = true;
          observerRef.current?.disconnect();
          const loader = new Image();
          loader.decoding = 'async';
          if (showProgress) {
            loader.onloadstart = () => setProgress(10);
          }
          loader.onload = () => {
            if ('decode' in img && typeof img.decode === 'function') {
              img.decode().then(() => {
                setProgress(100);
                setLoaded(true);
              }).catch(() => setLoaded(true));
            } else {
              setProgress(100);
              setLoaded(true);
            }
          };
          loader.onerror = () => {
            setError(true);
            setLoaded(true);
          };
          loader.src = getFullMediaUrl(src);
        }
      },
      {threshold, rootMargin}
    );
    observerRef.current.observe(img);
    return () => observerRef.current?.disconnect();
  }, [src, threshold, rootMargin, showProgress]);

  if (loaded && !error) {
    return (
      <img ref={imgRef} src={getFullMediaUrl(src)} alt={alt}
           className={`transition-opacity duration-300 ${className}`}
           style={{...style, opacity: 1}}
           width={width} height={height}
           loading="lazy" decoding="async"/>
    );
  }
  if (error) {
    return (
      <div className={`flex items-center justify-center bg-muted/50 ${className}`}
           style={{aspectRatio, ...style, width, height}}
           role="img" aria-label={alt || '图片加载失败'}>
        <ImageIcon className="w-8 h-8 text-muted-foreground"/>
      </div>
    );
  }
  return (
    <div className={`relative overflow-hidden ${className}`}
         style={{aspectRatio, ...style, width, height}}>
      <Skeleton className="absolute inset-0" variant="shimmer" width="100%" height="100%" borderRadius="0"/>
      {showProgress && progress > 0 && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-sm text-muted-foreground">{progress}%</div>
        </div>
      )}
    </div>
  );
});
LazyImage.displayName = 'LazyImage';

export const SkeletonProvider: React.FC<{
  children: React.ReactNode;
  theme?: SkeletonTheme;
}> = ({children, theme = {}}) => {
  const [loadingStates, setLoadingStates] = useState(new Map<string, boolean>());
  const setLoading = useCallback((key: string, loading: boolean) => {
    setLoadingStates(prev => {
      const next = new Map(prev);
      next.set(key, loading);
      return next;
    });
  }, []);

  const ArticleCard: React.FC<{ count?: number }> = React.memo(({count = 3}) => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {Array.from({length: count}).map((_, i) => <SkeletonCard key={i} variant="article"/>)}
    </div>
  ));
  ArticleCard.displayName = 'ArticleCard';

  const MediaCard: React.FC<{ count?: number }> = React.memo(({count = 6}) => (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {Array.from({length: count}).map((_, i) => <SkeletonCard key={i} variant="media"/>)}
    </div>
  ));
  MediaCard.displayName = 'MediaCard';

  const UserCard: React.FC<{ count?: number }> = React.memo(({count = 3}) => (
    <div className="space-y-4">
      {Array.from({length: count}).map((_, i) => <SkeletonCard key={i} variant="user"/>)}
    </div>
  ));
  UserCard.displayName = 'UserCard';

  const value = useMemo<SkeletonProviderContextValue>(() => ({
    theme, loadingStates, setLoading, ArticleCard, MediaCard, UserCard, LazyImage,
  }), [theme, loadingStates, setLoading]);

  return (
    <SkeletonProviderContext.Provider value={value}>
      {children}
    </SkeletonProviderContext.Provider>
  );
};

export function useSkeleton(): SkeletonProviderContextValue {
  const context = useContext(SkeletonProviderContext);
  if (!context) throw new Error('useSkeleton must be used within SkeletonProvider');
  return context;
}

export default SkeletonProvider;
