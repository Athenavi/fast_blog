/**
 * VariableVirtualList - 变高虚拟列表组件
 * 支持动态高度的虚拟列表，使用 estimateSize 预估高度
 *
 * 使用方式:
 * ```tsx
 * <VariableVirtualList
 *   items={articles}
 *   estimateSize={200}
 *   overscan={2}
 *   renderItem={(item, index) => <ArticleCard article={item} />}
 * />
 * ```
 */

'use client';

import {memo, useCallback, useEffect, useRef, useState} from 'react';

export interface VariableVirtualListProps<T> {
  /** 数据源 */
  items: T[];
  /** 预估单个元素高度 (用于初始布局) */
  estimateSize: number;
  /** 缓冲区 (可视区域上下额外渲染的数量) */
  overscan?: number;
  /** 渲染函数 */
  renderItem: (item: T, index: number) => React.ReactNode;
  /** 容器 className */
  className?: string;
  /** 容器样式 */
  containerStyle?: React.CSSProperties;
  /** 已测量元素高度的缓存 key (用于记忆已测量的高度) */
  measureKey?: (item: T) => string;
}

/**
 * VariableVirtualList - 核心使用 requestAnimationFrame + 动态测量
 */
function VariableVirtualListImpl<T>({
                                      items,
                                      estimateSize,
                                      overscan = 3,
                                      renderItem,
                                      className = '',
                                      containerStyle = {},
                                      measureKey,
                                    }: VariableVirtualListProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const [scrollY, setScrollY] = useState(0);
  const [containerHeight, setContainerHeight] = useState(600);
  // 存储已测量的实际高度 Map<index, actualHeight>
  const measuredHeights = useRef<Map<number, number>>(new Map());
  const [totalHeight, setTotalHeight] = useState(0);
  const rafRef = useRef<number | null>(null);

  // 初始化总高度
  useEffect(() => {
    const height = items.length * estimateSize;
    setTotalHeight(height);
  }, [items.length, estimateSize]);

  // ResizeObserver 获取容器高度
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerHeight(entry.contentRect.height);
      }
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // Scroll handler with RAF
  const handleScroll = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
    }

    rafRef.current = requestAnimationFrame(() => {
      setScrollY(container.scrollTop);
      rafRef.current = null;
    });
  }, []);

  // 清理
  useEffect(() => {
    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, []);

  // 获取 item 的实际高度 (已测量则使用实际值，否则使用预估值)
  const getItemHeight = useCallback((index: number): number => {
    return measuredHeights.current.get(index) ?? estimateSize;
  }, [estimateSize]);

  // 计算累积偏移量
  const getItemOffset = useCallback((index: number): number => {
    let offset = 0;
    for (let i = 0; i < index; i++) {
      offset += getItemHeight(i);
    }
    return offset;
  }, [getItemHeight]);

  // 计算可见范围
  const getVisibleRange = useCallback((): { start: number; end: number } => {
    if (!items.length) return {start: 0, end: 0};

    let y = 0;
    let start = 0;
    for (let i = 0; i < items.length; i++) {
      const h = getItemHeight(i);
      if (y + h > scrollY) {
        start = Math.max(0, i - overscan);
        break;
      }
      y += h;
    }

    y = 0;
    let end = items.length;
    for (let i = 0; i < items.length; i++) {
      const h = getItemHeight(i);
      y += h;
      if (y >= scrollY + containerHeight) {
        end = Math.min(items.length, i + overscan + 1);
        break;
      }
    }

    return {start, end};
  }, [items.length, scrollY, containerHeight, getItemHeight, overscan]);

  const {start, end} = getVisibleRange();
  const visibleItems = items.slice(start, end);
  const offsetY = getItemOffset(start);

  // Ref callback for measuring item height
  const setItemRef = useCallback((index: number) => {
    return (node: HTMLDivElement | null) => {
      if (!node) return;
      itemRefs.current.set(index, node);

      const observer = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const height = entry.contentRect.height;
          const prevHeight = measuredHeights.current.get(index);
          if (prevHeight !== height && height > 0) {
            measuredHeights.current.set(index, height);
            // Update total height
            let newTotal = 0;
            for (let i = 0; i < items.length; i++) {
              newTotal += measuredHeights.current.get(i) ?? estimateSize;
            }
            setTotalHeight(newTotal);
          }
        }
      });
      observer.observe(node);

      // Store observer for cleanup
      (node as any).__resizeObserver = observer;
    };
  }, [items.length, estimateSize]);

  return (
    <div
      ref={containerRef}
      className={`variable-virtual-list ${className}`}
      style={{
        overflow: 'auto',
        height: '100%',
        position: 'relative',
        willChange: 'scroll-position',
        ...containerStyle,
      }}
      onScroll={handleScroll}
    >
      {/* Total height spacer */}
      <div style={{height: totalHeight, position: 'relative', width: '100%'}}>
        {/* Visible items - 使用 translate3d for GPU acceleration */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            transform: `translate3d(0, ${offsetY}px, 0)`,
            willChange: 'transform',
          }}
        >
          {visibleItems.map((item, vi) => {
            const realIndex = start + vi;
            return (
              <div
                key={realIndex}
                ref={setItemRef(realIndex)}
                style={{
                  width: '100%',
                  // 使用预估高度，ResizeObserver 会测量实际高度
                }}
              >
                {renderItem(item, realIndex)}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export const VariableVirtualList = memo(VariableVirtualListImpl) as typeof VariableVirtualListImpl;
VariableVirtualList.displayName = 'VariableVirtualList';

export default VariableVirtualList;
