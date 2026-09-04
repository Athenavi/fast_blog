/**
 * StartupOptimizer - 启动优化器
 * 加速移动端首次加载，减少白屏时间
 *
 * 优化策略:
 * 1. 关键路径资源预加载
 * 2. 路由预取 (Route Prefetching)
 * 3. API 数据预取
 * 4. Service Worker 注册优化
 * 5. 首屏渲染性能监控
 */

'use client';

import {useCallback, useEffect, useRef} from 'react';
import {useNetworkState} from '@/lib/hooks/useNetworkState';

interface StartupOptimizerProps {
  /** 优先预加载的路由 */
  priorityRoutes?: string[];
  /** 预加载延迟 (ms) */
  preloadDelay?: number;
  /** 是否启用 Service Worker 优化注册 */
  optimizeSW?: boolean;
}

const StartupOptimizer: React.FC<StartupOptimizerProps> = ({
                                                             priorityRoutes = ['/articles', '/categories'],
                                                             preloadDelay = 2000,
                                                             optimizeSW = true,
                                                           }) => {
  const initialized = useRef(false);
  const {isSlow, saveData, effectiveType} = useNetworkState();

  const optimizeStartup = useCallback(() => {
    if (initialized.current) return;
    initialized.current = true;

    // 1. 关键字体预加载
    const preloadFont = () => {
      const link = document.createElement('link');
      link.rel = 'preload';
      link.as = 'font';
      link.type = 'font/woff2';
      link.crossOrigin = 'anonymous';
      link.href = 'https://fonts.gstatic.com/s/inter/v18/UcC73FwrK3iLTeHuS_fvQtMwCp50KnMa1ZL7.woff2';
      document.head.appendChild(link);
    };

    // 2. 路由预取 - 使用 Link prefetch
    const prefetchRoute = (route: string) => {
      // 检查是否弱网络，弱网络不预取
      if (isSlow || saveData) return;

      // 使用 fetch 预取 (适用于 MPA)
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3000);

      fetch(route, {
        signal: controller.signal,
        cache: 'force-cache',
        credentials: 'same-origin',
      }).catch(() => {
        // 静默失败
      }).finally(() => clearTimeout(timeout));
    };

    // 3. 关键 CSS 预渲染优化
    const optimizeCriticalCSS = () => {
      // 移除 non-critical stylesheets 的阻塞
      const stylesheets = document.querySelectorAll('link[rel="stylesheet"]');
      stylesheets.forEach(sheet => {
        const href = (sheet as HTMLLinkElement).href;
        // 如果是第三方 CSS，延迟加载
        if (href.includes('fonts.googleapis') || href.includes('cdn')) {
          sheet.media = 'print';
          sheet.addEventListener('load', () => {
            (sheet as HTMLLinkElement).media = 'all';
          });
        }
      });
    };

    // 4. Service Worker 延迟注册 (非阻塞)
    const registerSWOptimized = async () => {
      if (!optimizeSW || 'serviceWorker' in navigator === false) return;

      // 使用 requestIdleCallback 避免阻塞
      const register = async () => {
        try {
          const registration = await navigator.serviceWorker.getRegistration('/');
          if (!registration) {
            // SW 尚未注册，等待 Astro PWA 插件处理
          }
        } catch {
          // SW 不可用
        }
      };

      if (typeof requestIdleCallback !== 'undefined') {
        requestIdleCallback(register, {timeout: 5000});
      } else {
        setTimeout(register, 100);
      }
    };

    // 5. 性能监控标记
    const markStartup = () => {
      if (typeof performance === 'undefined') return;

      try {
        performance.mark('startup:optimizer:init');

        // 记录网络信息
        const navEntry = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
        if (navEntry) {
          const metrics = {
            effectiveType,
            download: (navigator as any).connection?.downlink,
            rtt: (navigator as any).connection?.rtt,
            saveData: (navigator as any).connection?.saveData,
            domContentLoaded: navEntry.domContentLoadedEventEnd - navEntry.startTime,
            loadComplete: navEntry.loadEventEnd - navEntry.startTime,
          };

          if (import.meta.env.DEV) {
            console.table('[Startup] Network Metrics', metrics);
          }

          // 上报性能数据 (可以集成到 RUM)
          if (typeof window !== 'undefined') {
            (window as any).__startupMetrics = metrics;
          }
        }
      } catch {
        // 性能标记失败不影响主流程
      }
    };

    // 调度预加载任务
    const schedulePreloads = () => {
      if (document.readyState !== 'complete') {
        window.addEventListener('load', () => {
          // 页面加载完成后开始预加载
          setTimeout(() => {
            priorityRoutes.forEach(route => prefetchRoute(route));
          }, preloadDelay);
        }, {once: true, passive: true});
      } else {
        // 页面已加载，直接预加载
        setTimeout(() => {
          priorityRoutes.forEach(route => prefetchRoute(route));
        }, preloadDelay);
      }
    };

    // 执行优化
    if (!isSlow && !saveData) {
      // 正常网络：完整优化
      preloadFont();
      optimizeCriticalCSS();
      registerSWOptimized();
      schedulePreloads();
    } else {
      // 弱网络：最小化优化
      optimizeCriticalCSS();
      markStartup();
    }

    markStartup();
  }, [priorityRoutes, preloadDelay, optimizeSW, isSlow, saveData, effectiveType]);

  useEffect(() => {
    // 使用 requestIdleCallback 避免阻塞主线程
    if (typeof requestIdleCallback !== 'undefined') {
      const handle = requestIdleCallback(optimizeStartup, {timeout: 1000});
      return () => requestIdleCallback.cancel(handle);
    } else {
      setTimeout(optimizeStartup, 100);
    }
  }, [optimizeStartup]);

  return null;
};

export default StartupOptimizer;
