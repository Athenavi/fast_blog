/**
 * OfflineBanner - 离线提示横幅
 * 网络断开时显示，恢复时自动隐藏
 * 支持手动刷新重试
 */

'use client';

import {memo, useCallback} from 'react';
import {RefreshCw, Wifi, X} from 'lucide-react';
import {useNetworkState} from '@/lib/hooks/useNetworkState';

const OfflineBanner = memo(() => {
  const {isOnline, isSlow, effectiveType} = useNetworkState();

  const handleRetry = useCallback(() => {
    window.location.reload();
  }, []);

  const handleDismiss = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const banner = document.getElementById('offline-banner');
    if (banner) {
      banner.style.display = 'none';
    }
  }, []);

  if (isOnline && !isSlow) return null;

  return (
    <div
      id="offline-banner"
      className={`fixed top-0 left-0 right-0 z-[60] flex items-center justify-between px-4 py-2 text-sm transition-all duration-300 ${
        isOnline
          ? 'bg-amber-50 dark:bg-amber-950 text-amber-800 dark:text-amber-200 border-b border-amber-200 dark:border-amber-800'
          : 'bg-red-50 dark:bg-red-950 text-red-800 dark:text-red-200 border-b border-red-200 dark:border-red-800'
      }`}
      role="alert"
    >
      <div className="flex items-center gap-2 min-w-0">
        {isOnline ? (
          <>
            <RefreshCw className="w-4 h-4 flex-shrink-0 animate-spin"/>
            <span className="truncate">
              网络连接较慢 ({effectiveType || '未知'})，已启用省流量模式
            </span>
          </>
        ) : (
          <>
            <Wifi className="w-4 h-4 flex-shrink-0"/>
            <span className="truncate">网络连接已断开，您已离线</span>
          </>
        )}
      </div>

      <div className="flex items-center gap-1 flex-shrink-0 ml-2">
        {!isOnline && (
          <button
            onClick={handleRetry}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs bg-red-100 dark:bg-red-900 hover:bg-red-200 dark:hover:bg-red-800 transition-colors touch-target"
            aria-label="重新连接"
          >
            <RefreshCw className="w-3 h-3"/>
            重试
          </button>
        )}
        <button
          onClick={handleDismiss}
          className="p-1 rounded hover:bg-black/5 dark:hover:bg-white/10 transition-colors touch-target"
          aria-label="关闭提示"
        >
          <X className="w-4 h-4"/>
        </button>
      </div>
    </div>
  );
});

OfflineBanner.displayName = 'OfflineBanner';

export default OfflineBanner;
