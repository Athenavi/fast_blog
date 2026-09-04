/**
 * useVisibilityState - 页面可见性状态 Hook
 *
 * 监听 document.visibilityState，在页面恢复前台时自动执行恢复策略。
 * 适用于：重新获取数据、恢复暂停的任务、刷新定时器等。
 *
 * 使用示例:
 * ```tsx
 * const visibility = useVisibilityState({
 *   onVisible: () => refetchData(),
 *   onHidden: () => pauseTimer(),
 * });
 *
 * if (!visibility.isVisible) {
 *   // 页面不可见时的 UI
 * }
 * ```
 */

import {useCallback, useEffect, useRef, useState} from 'react';

export interface UseVisibilityStateOptions {
  /** 页面变为可见时回调 */
  onVisible?: (wasHiddenFor: number) => void;
  /** 页面变为隐藏时回调 */
  onHidden?: () => void;
  /** 是否自动恢复（默认 true） */
  autoResume?: boolean;
  /** 最小隐藏时间才触发恢复 (ms，默认 5000) */
  minHiddenTime?: number;
}

export interface VisibilityState {
  /** 当前是否可见 */
  isVisible: boolean;
  /** 是否隐藏 */
  isHidden: boolean;
  /** 隐藏持续时间 (ms) */
  hiddenSince: number | null;
  /** 隐藏时长 (ms) */
  wasHiddenFor: number | null;
  /** 切换次数 */
  changeCount: number;
}

export function useVisibilityState(options: UseVisibilityStateOptions = {}) {
  const {onVisible, onHidden, autoResume = true, minHiddenTime = 5000} = options;

  const [state, setState] = useState<VisibilityState>(() => ({
    isVisible: typeof document === 'undefined' ? true : !document.hidden,
    isHidden: typeof document === 'undefined' ? false : !!document.hidden,
    hiddenSince: null,
    wasHiddenFor: null,
    changeCount: 0,
  }));

  const hiddenSinceRef = useRef<number | null>(null);
  const changeCountRef = useRef(0);

  const handleChange = useCallback(() => {
    const isHidden = document.hidden;
    changeCountRef.current += 1;

    setState(prev => {
      if (isHidden) {
        hiddenSinceRef.current = Date.now();
        return {
          isVisible: false,
          isHidden: true,
          hiddenSince: hiddenSinceRef.current,
          wasHiddenFor: null,
          changeCount: changeCountRef.current,
        };
      } else {
        const hiddenFor = hiddenSinceRef.current
          ? Date.now() - hiddenSinceRef.current
          : 0;

        if (prev.isHidden && hiddenFor >= minHiddenTime && autoResume) {
          onVisible?.(hiddenFor);
        }

        return {
          isVisible: true,
          isHidden: false,
          hiddenSince: null,
          wasHiddenFor: hiddenFor,
          changeCount: changeCountRef.current,
        };
      }
    });

    if (isHidden && onHidden) {
      onHidden();
    }
  }, [onVisible, onHidden, autoResume, minHiddenTime]);

  useEffect(() => {
    if (typeof document === 'undefined') return;
    document.addEventListener('visibilitychange', handleChange);
    return () => document.removeEventListener('visibilitychange', handleChange);
  }, [handleChange]);

  return state;
}

/**
 * 前台恢复 Hook
 * 当页面从后台恢复时自动重新获取数据
 *
 * 使用示例:
 * ```tsx
 * useForegroundRefetch(() => queryClient.invalidateQueries(['articles']), {
 *   minHiddenTime: 30000, // 30秒后才刷新
 * });
 * ```
 */
export function useForegroundRefetch(
  refetchFn: () => Promise<void> | void,
  options: UseVisibilityStateOptions = {}
) {
  const refetchRef = useRef(refetchFn);
  refetchRef.current = refetchFn;

  const {onVisible} = options;

  useVisibilityState({
    ...options,
    onVisible: (wasHiddenFor) => {
      onVisible?.(wasHiddenFor);
      // 使用 requestIdleCallback 避免阻塞恢复
      if (typeof requestIdleCallback !== 'undefined') {
        requestIdleCallback(async () => {
          await refetchRef.current();
        });
      } else {
        Promise.resolve(refetchRef.current());
      }
    },
  });
}

export default useVisibilityState;
