/**
 * useSkeletonState - 骨架屏精细化状态管理 Hook
 *
 * 按组件粒度管理骨架屏显示/隐藏，支持：
 * - 区域独立加载状态
 * - 最小显示时间（防止闪烁）
 * - 渐进式加载
 * - 加载超时
 *
 * 使用示例:
 * ```tsx
 * const skeleton = useSkeletonState();
 *
 * // 在异步数据获取中：
 * useEffect(() => {
 *   skeleton.start();
 *   fetchData().then(data => {
 *     setData(data);
 *     skeleton.complete();
 *   });
 * }, []);
 *
 * // 模板中：
 * if (skeleton.visible) {
 *   return <SkeletonCard />;
 * }
 * ```
 */

import {useCallback, useEffect, useMemo, useRef, useState} from 'react';

export interface SkeletonRegion {
  /** 区域 ID */
  id: string;
  /** 是否加载中 */
  loading: boolean;
  /** 加载开始时间 */
  startedAt: number | null;
  /** 加载耗时 (ms) */
  duration: number | null;
}

export interface SkeletonState {
  /** 是否显示骨架屏 */
  visible: boolean;
  /** 是否加载中 */
  loading: boolean;
  /** 加载进度 (0-100) */
  progress: number;
  /** 区域列表 */
  regions: SkeletonRegion[];
  /** 错误状态 */
  error: boolean;
  /** 加载耗时 (ms) */
  duration: number | null;

  /** 开始加载 */
  start: (regionId?: string) => void;
  /** 完成单个区域 */
  complete: (regionId?: string) => void;
  /** 全部完成 */
  finish: () => void;
  /** 设置错误 */
  setError: (error?: Error) => void;
  /** 重置 */
  reset: () => void;
}

export function useSkeletonState(
  options: {
    /** 最小显示时间 (ms)，防止闪烁 */
    minDisplayTime?: number;
    /** 加载超时时间 (ms) */
    timeout?: number;
    /** 区域数量（用于计算进度） */
    totalRegions?: number;
    /** 超时回调 */
    onTimeout?: () => void;
  } = {}
): SkeletonState {

  const {minDisplayTime = 500, timeout = 15000, totalRegions = 1, onTimeout} = options;
  const startTimeRef = useRef<number | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [state, setInternalState] = useState({
    loading: false,
    visible: false,
    progress: 0,
    regions: [] as SkeletonRegion[],
    error: false,
    duration: null as number | null,
  });

  const cleanup = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const start = useCallback((regionId?: string) => {
    const now = Date.now();
    startTimeRef.current = startTimeRef.current ?? now;

    // 清除超定时器
    cleanup();

    // 设置超时
    if (timeout > 0) {
      timerRef.current = setTimeout(() => {
        onTimeout?.();
        setInternalState(prev => ({
          ...prev,
          error: true,
        }));
      }, timeout);
    }

    setInternalState(prev => {
      const regions = regionId
        ? [...prev.regions, {id: regionId, loading: true, startedAt: now, duration: null}]
        : prev.regions;
      const completedCount = regions.filter((r: SkeletonRegion) => !r.loading).length;
      const progress = totalRegions > 0 ? Math.round((completedCount / totalRegions) * 100) : prev.progress;

      return {
        ...prev,
        loading: true,
        visible: true,
        progress,
        regions,
        error: false,
      };
    });

    // 保证最小显示时间
    if (minDisplayTime > 0) {
      hideTimerRef.current = setTimeout(() => {
        // Nothing, just ensure minimum display
      }, minDisplayTime);
    }
  }, [cleanup, timeout, onTimeout, totalRegions, minDisplayTime]);

  const complete = useCallback((regionId?: string) => {
    setInternalState(prev => {
      const now = Date.now();
      const regions = regionId
        ? prev.regions.map((r: SkeletonRegion) => {
          if (r.id === regionId && r.loading) {
            return {
              ...r,
              loading: false,
              duration: now - (r.startedAt || now),
            };
          }
          return r;
        })
        : prev.regions.map((r: SkeletonRegion) => ({
          ...r,
          loading: false,
          duration: r.startedAt ? now - r.startedAt : 0,
        }));

      const completedCount = regions.filter((r: SkeletonRegion) => !r.loading).length;
      const progress = totalRegions > 0 ? Math.round((completedCount / totalRegions) * 100) : 100;
      const loading = regions.some((r: SkeletonRegion) => r.loading);
      const duration = !loading && startTimeRef.current ? now - startTimeRef.current : prev.duration;

      return {
        ...prev,
        loading,
        visible: loading || progress < 100,
        progress: loading ? progress : 100,
        regions,
        duration: loading ? prev.duration : duration,
      };
    });

    if (regionId === undefined) {
      finish();
    }
  }, [totalRegions]);

  const finish = useCallback(() => {
    cleanup();
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }

    setInternalState(prev => {
      if (!prev.loading && prev.progress >= 100) return prev;
      const now = Date.now();
      const duration = startTimeRef.current ? now - startTimeRef.current : 0;
      return {
        ...prev,
        loading: false,
        visible: false,
        progress: 100,
        regions: prev.regions.map((r: SkeletonRegion) => ({
          ...r,
          loading: false,
          duration: r.startedAt ? now - r.startedAt : 0,
        })),
        duration,
      };
    });
  }, [cleanup]);

  const setError = useCallback((error?: Error) => {
    cleanup();
    if (error && import.meta.env.DEV) {
      console.warn('[SkeletonState] Load error:', error);
    }
    setInternalState(prev => ({
      ...prev,
      loading: false,
      visible: false,
      error: true,
    }));
  }, [cleanup]);

  const reset = useCallback(() => {
    cleanup();
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
    startTimeRef.current = null;
    setInternalState({
      loading: false,
      visible: false,
      progress: 0,
      regions: [],
      error: false,
      duration: null,
    });
  }, [cleanup]);

  // 组件卸载时清理
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  return useMemo(() => ({
    visible: state.visible,
    loading: state.loading,
    progress: state.progress,
    regions: state.regions,
    error: state.error,
    duration: state.duration,
    start,
    complete,
    finish,
    setError,
    reset,
  }), [state, start, complete, finish, setError, reset]);
}

export default useSkeletonState;
