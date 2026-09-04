/**
 * useRoutePrefetch - 路由预取 Hook
 * 当用户悬停或触摸链接时预取目标路由资源
 *
 * 使用示例:
 * ```tsx
 * const prefetch = useRoutePrefetch();
 *
 * <a onMouseEnter={() => prefetch('/article/123')} href="/article/123">
 *   文章标题
 * </a>
 * ```
 */

import {useCallback, useEffect, useRef} from 'react';
import {useNetworkState} from './useNetworkState';

export interface RoutePrefetchOptions {
  /** 预取延迟 (ms)，用户停留多久后开始预取 */
  delay?: number;
  /** 最大并发预取数 */
  maxConcurrency?: number;
  /** 是否启用基于视口的预取 */
  viewportAware?: boolean;
  /** 预取回调 */
  onPrefetch?: (route: string) => void;
}

interface PrefetchEntry {
  route: string;
  timer: ReturnType<typeof setTimeout>;
  inProgress: boolean;
}

export function useRoutePrefetch(options: RoutePrefetchOptions = {}) {
  const {
    delay = 300,
    maxConcurrency = 2,
    viewportAware = true,
    onPrefetch
  } = options;

  const network = useNetworkState();
  const prefetchMap = useRef<Map<string, PrefetchEntry>>(new Map());
  const activeCount = useRef(0);
  const prefetched = useRef(new Set<string>());

  // 清理定时器
  useEffect(() => {
    return () => {
      prefetchMap.current.forEach((entry) => {
        clearTimeout(entry.timer);
      });
      prefetchMap.current.clear();
    };
  }, []);

  const prefetch = useCallback((route: string) => {
    // 弱网络下不预取
    if (network.isSlow || network.saveData || !network.isOnline) return;

    // 已经预取过
    if (prefetched.current.has(route)) return;

    // 已经有预取在进行
    const existing = prefetchMap.current.get(route);
    if (existing) {
      clearTimeout(existing.timer);
    }

    // 设置延迟定时器
    const timer = setTimeout(() => {
      prefetchMap.current.delete(route);
      executePrefetch(route);
    }, delay);

    prefetchMap.current.set(route, {route, timer, inProgress: false});
  }, [delay, network]);

  const executePrefetch = useCallback(async (route: string) => {
    if (activeCount.current >= maxConcurrency) return;
    if (prefetched.current.has(route)) return;

    activeCount.current++;
    prefetched.current.add(route);
    onPrefetch?.(route);

    try {
      // 使用 fetch 预取页面数据
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 5000);

      await fetch(route, {
        signal: controller.signal,
        cache: 'no-store',
        priority: 'low' as RequestPriority
      });

      clearTimeout(timer);
    } catch {
      // 预取失败不影响主流程
    } finally {
      activeCount.current--;
    }
  }, [maxConcurrency, onPrefetch]);

  // 基于视口的自动预取
  useEffect(() => {
    if (!viewportAware || typeof window === 'undefined') return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const route = entry.target.getAttribute('href');
            if (route && route.startsWith('/')) {
              prefetch(route);
            }
          }
        });
      },
      {rootMargin: '200px', threshold: 0.1}
    );

    const links = document.querySelectorAll('a[href^="/"]');
    links.forEach(link => observer.observe(link));

    const mutationObserver = new MutationObserver((mutations) => {
      mutations.forEach(mutation => {
        mutation.addedNodes.forEach(node => {
          if (node instanceof HTMLElement) {
            const foundLinks = node.querySelectorAll?.('a[href^="/"]') || [];
            foundLinks.forEach(link => observer.observe(link));
            if (node.tagName === 'A' && node.getAttribute('href')?.startsWith('/')) {
              observer.observe(node);
            }
          }
        });
      });
    });

    mutationObserver.observe(document.body, {childList: true, subtree: true});

    return () => {
      observer.disconnect();
      mutationObserver.disconnect();
    };
  }, [viewportAware, prefetch]);

  const clear = useCallback((route?: string) => {
    if (route) {
      const entry = prefetchMap.current.get(route);
      if (entry) {
        clearTimeout(entry.timer);
        prefetchMap.current.delete(route);
      }
    } else {
      prefetchMap.current.forEach((entry) => {
        clearTimeout(entry.timer);
      });
      prefetchMap.current.clear();
    }
  }, []);

  return {
    prefetch,
    clear,
    getPrefetched: useCallback(() => Array.from(prefetched.current), [])
  };
}

export default useRoutePrefetch;
