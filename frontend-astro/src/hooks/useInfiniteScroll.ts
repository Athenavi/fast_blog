/**
 * useInfiniteScroll - 无限滚动 Hook
 * 支持 IntersectionObserver 自动加载下一页
 *
 * 使用示例:
 * ```tsx
 * const {
 *   loadMore,
 *   isLoadingMore,
 *   hasMore,
 *   observerElement,
 * } = useInfiniteScroll({
 *   onLoadMore: fetchNextPage,
 *   hasMore: currentPage < totalPages,
 * });
 *
 * return (
 *   <div>
 *     {items.map(item => <Item key={item.id} {...item} />)}
 *     <div ref={observerElement} />
 *   </div>
 * );
 * ```
 */

import {useCallback, useEffect, useRef, useState} from 'react';

export interface UseInfiniteScrollOptions {
  /** 加载更多数据的回调函数 */
  onLoadMore: () => Promise<void> | void;
  /** 是否还有更多数据 */
  hasMore: boolean;
  /** 观察元素距离视口多少 px 时触发加载 (默认 200) */
  rootMargin?: string;
  /** 是否启用自动加载 (默认 true) */
  enabled?: boolean;
  /** 自定义 IntersectionObserver root */
  root?: Element | null;
}

export interface UseInfiniteScrollReturn {
  /** 是否正在加载更多 */
  isLoadingMore: boolean;
  /** 是否还有更多数据 */
  hasMore: boolean;
  /** 手动触发加载更多 */
  loadMore: () => void;
  /** 观察元素的 ref */
  observerElement: (element: HTMLDivElement | null) => void;
}

export function useInfiniteScroll({
                                    onLoadMore,
                                    hasMore,
                                    rootMargin = '200px',
                                    enabled = true,
                                    root = null,
                                  }: UseInfiniteScrollOptions): UseInfiniteScrollReturn {
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const elementRef = useRef<HTMLDivElement | null>(null);
  const hasMoreRef = useRef(hasMore);

  // 同步 hasMore 到 ref，避免 closure 过期
  useEffect(() => {
    hasMoreRef.current = hasMore;
  }, [hasMore]);

  const loadMore = useCallback(async () => {
    if (!hasMoreRef.current || isLoadingMore || !enabled) return;
    setIsLoadingMore(true);
    try {
      await onLoadMore();
    } finally {
      setIsLoadingMore(false);
    }
  }, [onLoadMore, enabled, isLoadingMore]);

  // 创建 IntersectionObserver
  useEffect(() => {
    if (!enabled || !hasMore) return;

    const element = elementRef.current;
    if (!element) return;

    // 清理旧的 observer
    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    observerRef.current = new IntersectionObserver(
      (entries) => {
        const firstEntry = entries[0];
        if (firstEntry.isIntersecting) {
          loadMore();
        }
      },
      {root, rootMargin}
    );

    observerRef.current.observe(element);

    return () => {
      observerRef.current?.disconnect();
    };
  }, [enabled, hasMore, loadMore, root, rootMargin]);

  const observerElement = useCallback((element: HTMLDivElement | null) => {
    elementRef.current = element;
  }, []);

  return {isLoadingMore, hasMore, loadMore, observerElement};
}

export default useInfiniteScroll;
