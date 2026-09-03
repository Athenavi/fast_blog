/**
 * VirtualList - 虚拟列表组件
 * 用于长列表性能优化，仅渲染可视区域内的元素
 *
 * 使用方式:
 * ```tsx
 * <VirtualList
 *   items={articles}
 *   itemHeight={200}
 *   renderItem={(item, index) => <ArticleCard article={item} />}
 *   containerStyle={{ height: '600px' }}
 * />
 * ```
 */

import {useCallback, useEffect, useRef, useState} from 'react';

export interface VirtualListProps<T> {
  /** 数据源 */
  items: T[];
  /** 单个元素高度 (px) */
  itemHeight: number;
  /** 渲染单个元素的函数 */
  renderItem: (item: T, index: number) => React.ReactNode;
  /** 容器样式 */
  containerStyle?: React.CSSProperties;
  /** 容器 className */
  className?: string;
  /** 缓冲区域高度 (px) - 可视区域上下额外渲染的范围 */
  bufferSize?: number;
  /** 使用原生 overflow scroll (性能更好，但无法精确控制) */
  useNativeScroll?: boolean;
}

/**
 * VirtualList Component
 * 支持固定高度物品的虚拟滚动列表
 */
export const VirtualList = <T, >({
                                   items,
                                   itemHeight,
                                   renderItem,
                                   containerStyle = {},
                                   className = '',
                                   bufferSize = 5,
                                   useNativeScroll = false,
                                 }: VirtualListProps<T>) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollY, setScrollY] = useState(0);
  const [containerHeight, setContainerHeight] = useState(600);
  const rafRef = useRef<number | null>(null);

  // 计算容器高度
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerHeight(entry.contentRect.height);
      }
    });

    observer.observe(container);
    setContainerHeight(container.clientHeight || containerHeight);

    return () => observer.disconnect();
  }, []);

  // 带节流/防抖的 scroll handler (使用 requestAnimationFrame)
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

  // 清理 raf
  useEffect(() => {
    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, []);

  // 计算可见范围
  const totalCount = items.length;
  const totalHeight = totalCount * itemHeight;

  // 可见区域索引范围
  const startIndex = Math.max(0, Math.floor(scrollY / itemHeight) - bufferSize);
  const visibleCount = Math.ceil(containerHeight / itemHeight) + bufferSize * 2;
  const endIndex = Math.min(totalCount, startIndex + visibleCount);

  // 可见 items
  const visibleItems = items.slice(startIndex, endIndex);

  // 偏移量
  const offsetY = startIndex * itemHeight;

  return (
    <div
      ref={containerRef}
      className={`virtual-list-container ${className}`}
      style={{
        overflow: 'auto',
        height: containerHeight,
        position: 'relative',
        ...containerStyle,
      }}
      onScroll={handleScroll}
    >
      {/* Total height spacer */}
      <div style={{height: totalHeight, position: 'relative', width: '100%'}}>
        {/* Visible items */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            transform: `translateY(${offsetY}px)`,
          }}
        >
          {visibleItems.map((item, vi) => {
            const realIndex = startIndex + vi;
            return (
              <div
                key={realIndex}
                style={{
                  height: itemHeight,
                  width: '100%',
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
};

/**
 * VirtualListWithVariableHeight - 变高虚拟列表 (使用 IntersectionObserver)
 * 适用于高度不固定的列表项
 */
export const VirtualGrid = <T, >({
                                   items,
                                   columns = 3,
                                   renderItem,
                                   className = '',
                                   containerStyle = {},
                                 }: {
  items: T[];
  columns?: number;
  renderItem: (item: T, index: number) => React.ReactNode;
  className?: string;
  containerStyle?: React.CSSProperties;
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [visibleIndices, setVisibleIndices] = useState<Set<number>>(new Set());

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const index = Number(entry.target.getAttribute('data-index'));
          if (isNaN(index)) return;

          setVisibleIndices((prev) => {
            const next = new Set(prev);
            if (entry.isIntersecting) {
              next.add(index);
            } else {
              next.delete(index);
            }
            return next;
          });
        });
      },
      {
        root: container,
        rootMargin: '100px',
      }
    );

    const observerElements = container.querySelectorAll('[data-index]');
    observerElements.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, [items, columns]);

  const cols = Math.min(columns, items.length);
  const gridStyle: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: `repeat(${cols}, 1fr)`,
    gap: '1.5rem',
    ...containerStyle,
  };

  return (
    <div
      ref={containerRef}
      className={`virtual-list-container ${className}`}
      style={containerStyle}
    >
      <div style={gridStyle}>
        {items.map((item, index) => (
          <div
            key={index}
            data-index={index}
            style={{
              contentVisibility: visibleIndices.has(index) ? 'visible' : 'hidden',
            }}
          >
            {visibleIndices.has(index) ? renderItem(item, index) : (
              <div className="skeleton rounded-2xl" style={{aspectRatio: '16/10'}}/>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default VirtualList;
