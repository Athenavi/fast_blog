/**
 * PullToRefresh - 下拉刷新组件
 * 用于移动端的下拉刷新交互
 *
 * 使用方式:
 * ```tsx
 * <PullToRefresh onRefresh={handleRefresh} pulling={pulling}>
 *   <LongList />
 * </PullToRefresh>
 * ```
 */

'use client';

import React, {memo, useCallback, useEffect, useRef, useState} from 'react';

export interface PullToRefreshProps {
  /** 刷新回调 */
  onRefresh: () => Promise<void> | void;
  /** 触发刷新的阈值 (px) */
  threshold?: number;
  /** 最大下拉距离 (px) */
  maxPullDistance?: number;
  /** 是否禁用 */
  disabled?: boolean;
  /** 刷新组件 */
  children: React.ReactNode;
  /** 容器 className */
  className?: string;
  /** 自定义下拉指示器 */
  pullIndicator?: (progress: number, refreshing: boolean) => React.ReactNode;
}

interface PullState {
  pulling: boolean;
  refreshing: boolean;
  pullDistance: number;
  progress: number; // 0-1, 达到1时触发
}

function PullToRefreshImpl({
                             onRefresh,
                             threshold = 80,
                             maxPullDistance = 150,
                             disabled = false,
                             children,
                             className = '',
                             pullIndicator,
                           }: PullToRefreshProps) {
  const [state, setState] = useState<PullState>({
    pulling: false,
    refreshing: false,
    pullDistance: 0,
    progress: 0,
  });

  const startY = useRef(0);
  const currentY = useRef(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number | null>(null);

  const handleTouchStart = useCallback((e: TouchEvent) => {
    if (disabled) return;

    // 只有在顶部时才支持下拉
    const container = containerRef.current;
    if (container && container.scrollTop !== 0) return;

    startY.current = e.touches[0].clientY;
    setState(prev => ({...prev, pulling: true}));
  }, [disabled]);

  const handleTouchMove = useCallback((e: TouchEvent) => {
    if (!state.pulling || state.refreshing) return;

    const deltaY = e.touches[0].clientY - startY.current;
    if (deltaY <= 0) return; // 只处理下拉

    // 使用阻尼效果
    const resistance = 0.4;
    const pullDistance = Math.min(deltaY * resistance, maxPullDistance);

    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
    }

    rafRef.current = requestAnimationFrame(() => {
      const progress = Math.min(pullDistance / threshold, 1);
      setState({
        pulling: true,
        refreshing: false,
        pullDistance,
        progress,
      });
      rafRef.current = null;
    });

    currentY.current = pullDistance;

    // 防止页面滚动
    if (pullDistance > 10) {
      e.preventDefault();
    }
  }, [state.pulling, state.refreshing, threshold, maxPullDistance]);

  const handleTouchEnd = useCallback(async () => {
    if (!state.pulling || state.refreshing) return;

    if (state.progress >= 1) {
      // 触发刷新
      setState(prev => ({...prev, refreshing: true, pullDistance: threshold}));
      try {
        await onRefresh();
      } finally {
        setState({pulling: false, refreshing: false, pullDistance: 0, progress: 0});
      }
    } else {
      // 复位
      setState({pulling: false, refreshing: false, pullDistance: 0, progress: 0});
    }
  }, [state.pulling, state.refreshing, state.progress, threshold, onRefresh]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('touchstart', handleTouchStart, {passive: true});
    container.addEventListener('touchmove', handleTouchMove, {passive: false});
    container.addEventListener('touchend', handleTouchEnd);

    return () => {
      container.removeEventListener('touchstart', handleTouchStart);
      container.removeEventListener('touchmove', handleTouchMove);
      container.removeEventListener('touchend', handleTouchEnd);
    };
  }, [handleTouchStart, handleTouchMove, handleTouchEnd]);

  // 默认下拉指示器
  const defaultIndicator = () => {
    const {progress, refreshing, pullDistance} = state;
    if (!state.pulling && !state.refreshing && pullDistance === 0) return null;

    return (
      <div
        className="flex items-center justify-center"
        style={{
          height: `${Math.max(pullDistance, 40)}px`,
          transition: !state.pulling ? 'height 0.3s ease' : 'none',
        }}
      >
        {refreshing ? (
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"/>
            <span className="text-sm text-gray-500 dark:text-gray-400">刷新中...</span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1">
            <svg
              className="w-6 h-6 text-gray-400 transition-transform"
              style={{transform: `rotate(${progress * 180}deg)`}}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
            {progress >= 1 && (
              <span className="text-xs text-gray-400">释放刷新</span>
            )}
          </div>
        )}
      </div>
    );
  };

  const indicator = pullIndicator
    ? pullIndicator(state.progress, state.refreshing)
    : defaultIndicator();

  return (
    <div
      ref={containerRef}
      className={`pull-to-refresh ${className}`}
      style={{
        overscrollBehavior: 'contain',
        transform: state.refreshing ? `translateY(${threshold}px)` : state.pulling ? `translateY(${state.pullDistance}px)` : undefined,
        transition: !state.pulling ? 'transform 0.3s ease' : 'none',
      }}
    >
      {indicator}
      {children}
    </div>
  );
}

export const PullToRefresh = memo(PullToRefreshImpl) as typeof PullToRefreshImpl;
PullToRefresh.displayName = 'PullToRefresh';

/**
 * PullToRefresh hook - 如果不需要使用组件包装，可以用 hook 版本
 */
export function usePullToRefresh(
  onRefresh: () => Promise<void> | void,
  options: { threshold?: number; disabled?: boolean } = {}
) {
  const {threshold = 80, disabled = false} = options;
  const [refreshing, setRefreshing] = useState(false);
  const startY = useRef(0);

  const handleTouchStart = useCallback((e: TouchEvent) => {
    if (disabled) return;
    startY.current = e.touches[0].clientY;
  }, [disabled]);

  const handleTouchEnd = useCallback(async (e: TouchEvent) => {
    const deltaY = e.changedTouches[0].clientY - startY.current;
    if (deltaY > threshold && !refreshing) {
      setRefreshing(true);
      try {
        await onRefresh();
      } finally {
        setRefreshing(false);
      }
    }
  }, [threshold, refreshing, onRefresh]);

  return {refreshing, handleTouchStart, handleTouchEnd};
}

export default PullToRefresh;
