/**
 * ListLoadingFooter - 列表加载底部组件
 * 统一无限滚动列表的底部加载状态显示
 */

'use client';

import {memo} from 'react';

export interface ListLoadingFooterProps {
  /** 正在加载 */
  isLoading?: boolean;
  /** 加载完成，无更多数据 */
  hasLoadedAll?: boolean;
  /** 总加载数量 */
  totalLoaded?: number;
  /** 出错 */
  error?: string | null;
  /** 重试回调 */
  onRetry?: () => void;
}

function ListLoadingFooterImpl({
                                 isLoading = false,
                                 hasLoadedAll = false,
                                 totalLoaded = 0,
                                 error = null,
                                 onRetry,
                               }: ListLoadingFooterProps) {
  // 加载中
  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-6">
        <div className="w-5 h-5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"/>
        <span className="text-sm text-gray-500 dark:text-gray-400">加载中...</span>
      </div>
    );
  }

  // 出错
  if (error) {
    return (
      <div className="flex flex-col items-center gap-3 py-6">
        <span className="text-sm text-red-500">{error}</span>
        {onRetry && (
          <button
            onClick={onRetry}
            className="px-4 py-2 text-sm bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors"
          >
            重新加载
          </button>
        )}
      </div>
    );
  }

  // 全部加载完成
  if (hasLoadedAll && totalLoaded > 0) {
    return (
      <div className="text-center py-4 text-xs text-gray-400 dark:text-gray-600">
        已加载全部 {totalLoaded} 条数据
      </div>
    );
  }

  return null;
}

export const ListLoadingFooter = memo(ListLoadingFooterImpl);
ListLoadingFooter.displayName = 'ListLoadingFooter';

export default ListLoadingFooter;
