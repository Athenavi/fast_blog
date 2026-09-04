/**
 * InfiniteList - 无限滚动列表组件
 * 结合虚拟滚动和无限加载，适用于超长列表场景
 *
 * 使用示例:
 * ```tsx
 * <InfiniteList
 *   items={articles}
 *   itemHeight={200}
 *   renderItem={(item) => <ArticleCard article={item} />}
 *   onLoadMore={fetchNextPage}
 *   hasMore={currentPage < totalPages}
 *   containerHeight="70vh"
 * />
 * ```
 */

'use client';

import {memo, useMemo, useRef} from 'react';
import {VirtualList} from '@/components/VirtualList';
import {useInfiniteScroll} from '@/hooks/useInfiniteScroll';

export interface InfiniteListProps<T> {
  /** 数据源 */
  items: T[];
  /** 单个元素高度 */
  itemHeight: number;
  /** 渲染函数 */
  renderItem: (item: T, index: number) => React.ReactNode;
  /** 加载更多回调 */
  onLoadMore: () => Promise<void> | void;
  /** 是否还有更多数据 */
  hasMore: boolean;
  /** 容器高度 (CSS 单位) */
  containerHeight?: string | number;
  /** 容器 className */
  className?: string;
  /** 是否启用虚拟滚动 */
  virtualScroll?: boolean;
  /** 缓冲区大小 */
  bufferSize?: number;
  /** 空状态组件 */
  emptyComponent?: React.ReactNode;
  /** 底部加载指示器 */
  loadingFooter?: React.ReactNode;
}

function InfiniteListImpl<T>({
                               items,
                               itemHeight,
                               renderItem,
                               onLoadMore,
                               hasMore,
                               containerHeight = '70vh',
                               className = '',
                               virtualScroll = true,
                               bufferSize = 5,
                               emptyComponent,
                               loadingFooter,
                             }: InfiniteListProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);

  const {isLoadingMore, loadMore, observerElement} = useInfiniteScroll({
    onLoadMore,
    hasMore,
    rootMargin: '100px',
    enabled: true,
    root: null,
  });

  const containerStyle = useMemo(() => ({
    height: typeof containerHeight === 'number' ? `${containerHeight}px` : containerHeight,
    maxHeight: typeof containerHeight === 'number' ? `${containerHeight}px` : containerHeight,
  }), [containerHeight]);

  // 默认空状态
  const defaultEmptyComponent = (
    <div className="text-center py-16 text-gray-400 dark:text-gray-600">
      <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M4 6h16M4 12h16M4 18h16"/>
      </svg>
      <p className="text-sm">暂无数据</p>
    </div>
  );

  // 默认加载指示器
  const defaultLoadingFooter = isLoadingMore ? (
    <div className="flex items-center justify-center gap-2 py-6">
      <div className="w-5 h-5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"/>
      <span className="text-sm text-gray-500 dark:text-gray-400">加载中...</span>
    </div>
  ) : null;

  if (items.length === 0 && !isLoadingMore) {
    return (
      <div ref={containerRef} className={`infinite-list ${className}`}>
        {emptyComponent || defaultEmptyComponent}
      </div>
    );
  }

  if (virtualScroll) {
    return (
      <div ref={containerRef} className={`infinite-list ${className}`}
           style={{display: 'flex', flexDirection: 'column'}}>
        {/* 虚拟滚动列表 */}
        <div style={{flex: 1, minHeight: 0}}>
          <VirtualList
            items={items}
            itemHeight={itemHeight}
            renderItem={renderItem}
            containerStyle={containerStyle}
            bufferSize={bufferSize}
          />
        </div>
        {/* 加载状态指示器 */}
        {isLoadingMore && (
          <div className="flex items-center justify-center gap-2 py-4 border-t border-gray-100 dark:border-gray-800">
            <div className="w-5 h-5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"/>
            <span className="text-sm text-gray-500 dark:text-gray-400">加载中...</span>
          </div>
        )}
        {/* 底部观察哨兵 - 触发无限滚动 */}
        {hasMore && (
          <div ref={observerElement} style={{height: 1}}>
            {/* 观察元素不可见 */}
          </div>
        )}
        {/* 底部加载指示器 */}
        {loadingFooter || defaultLoadingFooter}
        {/* 无更多数据提示 */}
        {!hasMore && items.length > 0 && (
          <div className="text-center py-4 text-xs text-gray-400 dark:text-gray-600">
            已加载全部数据 ({items.length})
          </div>
        )}
      </div>
    );
  }

  // 非虚拟滚动模式 - 使用原生无限滚动
  return (
    <div ref={containerRef} className={`infinite-list ${className}`}>
      {/* 列表容器 */}
      <div style={{overscrollBehavior: 'contain'}} className="pb-4">
        {items.map((item, index) => (
          <div key={index} style={{height: itemHeight}}>
            {renderItem(item, index)}
          </div>
        ))}
      </div>
      {/* 加载状态 */}
      {isLoadingMore && (
        <div className="flex items-center justify-center gap-2 py-4">
          <div className="w-5 h-5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"/>
          <span className="text-sm text-gray-500 dark:text-gray-400">加载中...</span>
        </div>
      )}
      {/* 底部观察哨兵 */}
      {hasMore && (
        <div ref={observerElement} style={{height: 1}}/>
      )}
      {/* 底部加载指示器 */}
      {loadingFooter || defaultLoadingFooter}
      {/* 无更多数据 */}
      {!hasMore && items.length > 0 && (
        <div className="text-center py-4 text-xs text-gray-400 dark:text-gray-600">
          已加载全部数据 ({items.length})
        </div>
      )}
    </div>
  );
}

export const InfiniteList = memo(InfiniteListImpl) as typeof InfiniteListImpl;
InfiniteList.displayName = 'InfiniteList';

/**
 * InfiniteGrid - 无限滚动网格组件
 */
export interface InfiniteGridProps<T> {
  items: T[];
  columns?: number;
  renderItem: (item: T, index: number) => React.ReactNode;
  onLoadMore: () => Promise<void> | void;
  hasMore: boolean;
  className?: string;
  gap?: string;
  virtualScroll?: boolean;
}

function InfiniteGridImpl<T>({
                               items,
                               columns = 3,
                               renderItem,
                               onLoadMore,
                               hasMore,
                               className = '',
                               gap = '1.5rem',
                               virtualScroll = false,
                             }: InfiniteGridProps<T>) {
  const {isLoadingMore, observerElement} = useInfiniteScroll({
    onLoadMore,
    hasMore,
    rootMargin: '200px',
  });

  const col = Math.min(columns, items.length);
  const gridStyle = useMemo(() => ({
    display: 'grid',
    gridTemplateColumns: `repeat(${col}, 1fr)`,
    gap,
  }), [col, gap]);

  if (items.length === 0 && !isLoadingMore) {
    return (
      <div className={`infinite-grid ${className}`}>
        <div className="text-center py-16 text-gray-400">
          <p>暂无数据</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`infinite-grid ${className}`}>
      <div style={gridStyle}>
        {items.map((item, index) => (
          <div key={index}>
            {renderItem(item, index)}
          </div>
        ))}
      </div>
      {isLoadingMore && (
        <div className="flex items-center justify-center gap-2 py-6">
          <div className="w-5 h-5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"/>
          <span className="text-sm text-gray-500">加载中...</span>
        </div>
      )}
      {hasMore && <div ref={observerElement} style={{height: 1}}/>}
      {!hasMore && items.length > 0 && (
        <div className="text-center py-4 text-xs text-gray-400">
          已加载全部数据 ({items.length})
        </div>
      )}
    </div>
  );
}

export const InfiniteGrid = memo(InfiniteGridImpl) as typeof InfiniteGridImpl;
InfiniteGrid.displayName = 'InfiniteGrid';

export default InfiniteList;
