/**
 * useDebounceCallback - 防抖回调 Hook
 * 创建防抖版本的回调函数，自动清理定时器
 *
 * 使用示例:
 * ```tsx
 * const debouncedSearch = useDebounceCallback((query: string) => {
 *   // 搜索逻辑
 * }, 300);
 *
 * // 在输入时使用
 * <input onChange={(e) => debouncedSearch(e.target.value)} />
 * ```
 */

import {useCallback, useEffect, useRef} from 'react';

export interface UseDebounceCallbackOptions {
  /** 延迟时间 (ms) */
  delay?: number;
  /** 是否在首次调用时立即执行 */
  leading?: boolean;
  /** 是否在延迟结束后执行 */
  trailing?: boolean;
  /** 最大等待时间 (ms)，超过后强制执行 */
  maxWait?: number;
}

function useDebounceCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number = 300,
  options: UseDebounceCallbackOptions = {}
) {
  const {leading = false, trailing = true, maxWait} = options;

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const maxWaitTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastCallTimeRef = useRef<number>(0);
  const lastArgsRef = useRef<Parameters<T> | null>(null);
  const mountedRef = useRef<boolean>(true);

  // 清理定时器
  const clearTimers = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (maxWaitTimerRef.current) {
      clearTimeout(maxWaitTimerRef.current);
      maxWaitTimerRef.current = null;
    }
  }, []);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      clearTimers();
    };
  }, [clearTimers]);

  const debouncedCallback = useCallback((...args: Parameters<T>) => {
    const now = Date.now();
    const timeSinceLastCall = now - lastCallTimeRef.current;

    // 如果设置了 maxWait，启动最大等待定时器
    if (maxWait && !maxWaitTimerRef.current) {
      maxWaitTimerRef.current = setTimeout(() => {
        if (lastArgsRef.current && mountedRef.current) {
          callback(...lastArgsRef.current);
          clearTimers();
          lastCallTimeRef.current = Date.now();
        }
      }, maxWait);
    }

    // 如果设置了 leading 且是首次调用或距离上次调用超过 delay
    if (leading && timeSinceLastCall >= delay) {
      if (mountedRef.current) {
        callback(...args);
      }
      lastCallTimeRef.current = now;
      return;
    }

    // 清除之前的定时器
    clearTimers();

    // 保存最新的参数
    lastArgsRef.current = args;
    lastCallTimeRef.current = now;

    // 如果设置了 trailing，在延迟后执行
    if (trailing && mountedRef.current) {
      timerRef.current = setTimeout(() => {
        if (lastArgsRef.current && mountedRef.current) {
          callback(...lastArgsRef.current);
        }
        clearTimers();
      }, delay - timeSinceLastCall);
    }
  }, [callback, delay, leading, trailing, maxWait, clearTimers]);

  // 取消函数
  const cancel = useCallback(() => {
    clearTimers();
  }, [clearTimers]);

  // 立即执行函数
  const flush = useCallback(() => {
    if (lastArgsRef.current) {
      callback(...lastArgsRef.current);
      clearTimers();
      lastCallTimeRef.current = Date.now();
    }
  }, [callback, clearTimers]);

  return Object.assign(debouncedCallback, {cancel, flush});
}

export default useDebounceCallback;
