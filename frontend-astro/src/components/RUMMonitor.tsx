/**
 * RUMMonitor - Real User Monitoring 监控组件
 *
 * 收集真实用户性能数据并上报，包括：
 * - Web Vitals (LCP/INP/CLS/FCP/TTFB)
 * - JS 错误捕获
 * - 资源加载失败
 * - 网络请求性能
 * - 页面导航事件
 *
 * 使用示例:
 * ```tsx
 * // 在根布局中挂载
 * <RUMMonitor
 *   endpoint="/api/rum"
 *   sampleRate={0.1} // 10% 采样率
 *   reportThreshold="poor" // 仅上报差的指标
 * />
 * ```
 */

'use client';

import {memo, useCallback, useEffect, useRef} from 'react';
import {
  type LongTaskEntry,
  observeLongTasks,
  observeSlowResources,
  type SlowResource,
  useWebVitals,
} from '@/lib/perf-monitor';
import {useNetworkState} from '@/lib/hooks/useNetworkState';
import {useVisibilityState} from '@/lib/hooks/useVisibilityState';

export interface RUMMonitorProps {
  /** 上报端点 URL */
  endpoint?: string;
  /** 采样率 (0-1) */
  sampleRate?: number;
  /** 上报阈值 - 只上报达到此等级的指标 */
  reportThreshold?: 'good' | 'needs-improvement' | 'poor';
  /** 自定义上报函数 */
  reporter?: (data: RUMData) => void | Promise<void>;
  /** 是否启用错误捕获 */
  captureErrors?: boolean;
  /** 是否捕获资源错误 */
  captureResourceErrors?: boolean;
  /** 上报批次大小 */
  batchSize?: number;
  /** 上报间隔 (ms) */
  flushInterval?: number;
}

export interface RUMData {
  /** 采集时间 */
  timestamp: number;
  /** 页面 URL */
  url: string;
  /** 会话 ID */
  sessionId: string;
  /** 指标类型 */
  type: 'webvital' | 'error' | 'navigation' | 'resource' | 'longtask' | 'network';
  /** 指标名称 */
  name: string;
  /** 指标值 */
  value: number;
  /** 性能等级 */
  rating?: 'good' | 'needs-improvement' | 'poor';
  /** 网络类型 */
  effectiveType?: string;
  /** 额外数据 */
  meta?: Record<string, any>;
}

const RUMMonitor = memo(({
                           endpoint = '/api/rum',
                           sampleRate = 0.1,
                           reportThreshold = 'poor',
                           reporter,
                           captureErrors = true,
                           captureResourceErrors = true,
                           batchSize = 100,
                           flushInterval = 30000,
                         }: RUMMonitorProps) => {

  const bufferRef = useRef<RUMData[]>([]);
  const sessionIdRef = useRef(generateSessionId());
  const flushingRef = useRef(false);
  const vitals = useWebVitals();
  const network = useNetworkState();
  const visibility = useVisibilityState();

  const thresholdPriority = {
    'good': 0,
    'needs-improvement': 1,
    'poor': 2,
  };

  const shouldReport = useCallback((rating: string): boolean => {
    // 采样控制
    if (Math.random() > sampleRate) return false;
    // 阈值控制
    const current = thresholdPriority[rating as keyof typeof thresholdPriority] ?? 0;
    const minPriority = thresholdPriority[reportThreshold as keyof typeof thresholdPriority] ?? 0;
    return current >= minPriority;
  }, [sampleRate, reportThreshold]);

  const flushBuffer = useCallback(async () => {
    if (flushingRef.current || bufferRef.current.length === 0) return;
    flushingRef.current = true;

    const batch = bufferRef.current.splice(0, batchSize);

    try {
      if (reporter) {
        await reporter(batch[0]);
        batch.slice(1).forEach(d => reporter?.(d));
      } else if (endpoint && typeof navigator !== 'undefined' && navigator.sendBeacon) {
        const blob = new Blob([JSON.stringify(batch)], {type: 'application/json'});
        navigator.sendBeacon(endpoint, blob);
      }
    } catch {
      // 上报失败不影响主流程
    } finally {
      flushingRef.current = false;
    }
  }, [endpoint, reporter, batchSize]);

  // 定期 flush
  useEffect(() => {
    const timer = setInterval(flushBuffer, flushInterval);
    return () => clearInterval(timer);
  }, [flushBuffer, flushInterval]);

  // Web Vitals 监控
  useEffect(() => {
    const record = (name: string, value: number, rating: string) => {
      if (!shouldReport(rating) || value === 0) return;
      bufferRef.current.push({
        timestamp: Date.now(),
        url: window.location.href,
        sessionId: sessionIdRef.current,
        type: 'webvital',
        name,
        value,
        rating: rating as any,
        effectiveType: network.effectiveType,
      });
    };

    record('LCP', vitals.lcp, getRating(vitals.lcp, 2500, 4000));
    record('INP', vitals.inp, getRating(vitals.inp, 200, 500));
    record('CLS', vitals.cls, getRating(vitals.cls, 0.1, 0.25));
    record('FCP', vitals.fcp, getRating(vitals.fcp, 1800, 3000));
    record('TTFB', vitals.ttfb, getRating(vitals.ttfb, 800, 1800));
  }, [vitals, shouldReport, network.effectiveType]);

  // 错误捕获
  useEffect(() => {
    if (!captureErrors) return;

    const handleError = (event: ErrorEvent) => {
      bufferRef.current.push({
        timestamp: Date.now(),
        url: window.location.href,
        sessionId: sessionIdRef.current,
        type: 'error',
        name: event.error?.name || 'Error',
        value: 0,
        meta: {
          message: event.message,
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
          stack: event.error?.stack?.slice(0, 500),
        },
      });
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      bufferRef.current.push({
        timestamp: Date.now(),
        url: window.location.href,
        sessionId: sessionIdRef.current,
        type: 'error',
        name: 'UnhandledPromiseRejection',
        value: 0,
        meta: {
          reason: String(event.reason),
        },
      });
    };

    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, [captureErrors]);

  // 资源错误捕获
  useEffect(() => {
    if (!captureResourceErrors) return;

    const handleError = (event: Event) => {
      const target = (event.target as HTMLElement) | null;
      bufferRef.current.push({
        timestamp: Date.now(),
        url: window.location.href,
        sessionId: sessionIdRef.current,
        type: 'resource',
        name: (target as any)?.src || (target as any)?.href || 'unknown',
        value: 0,
        meta: {
          tagName: target?.tagName,
        },
      });
    };

    window.addEventListener('error', handleError, true);
    return () => window.removeEventListener('error', handleError, true);
  }, [captureResourceErrors]);

  // 页面隐藏时 flush
  useEffect(() => {
    if (visibility.isHidden && bufferRef.current.length > 0) {
      flushBuffer();
    }
  }, [visibility.isHidden, flushBuffer]);

  // 页面卸载时 flush
  useEffect(() => {
    const handleUnload = () => {
      flushBuffer();
    };
    window.addEventListener('pagehide', handleUnload);
    return () => window.removeEventListener('pagehide', handleUnload);
  }, [flushBuffer]);

  // Long Task 监控
  useEffect(() => {
    const onLongTask = (entry: LongTaskEntry) => {
      if (!shouldReport('poor')) return;
      bufferRef.current.push({
        timestamp: Date.now(),
        url: window.location.href,
        sessionId: sessionIdRef.current,
        type: 'longtask',
        name: 'LongTask',
        value: entry.duration,
        rating: 'poor',
        meta: {
          start: entry.startTime,
          blocking: entry.duration - 50,
        },
      });
    };
    return observeLongTasks(onLongTask);
  }, [shouldReport]);

  // Slow Resources 监控
  useEffect(() => {
    const onSlowResource = (res: SlowResource) => {
      bufferRef.current.push({
        timestamp: Date.now(),
        url: window.location.href,
        sessionId: sessionIdRef.current,
        type: 'resource',
        name: res.name,
        value: res.duration,
        meta: {
          transferSize: res.transferSize,
          decodedSize: res.decodedSize,
        },
      });
    };
    return observeSlowResources(onSlowResource);
  }, []);

  return null; // 纯监控组件，不渲染任何内容
});

RUMMonitor.displayName = 'RUMMonitor';

function generateSessionId(): string {
  if (typeof window === 'undefined') return 'server';
  let id = sessionStorage.getItem('__rum_session__');
  if (!id) {
    id = `rum_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    sessionStorage.setItem('__rum_session__', id);
  }
  return id;
}

function getRating(value: number, good: number, poor: number): string {
  if (value <= good) return 'good';
  if (value <= poor) return 'needs-improvement';
  return 'poor';
}

export default RUMMonitor;
