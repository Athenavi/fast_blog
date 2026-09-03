/**
 * useNetworkState - 网络状态检测 Hook
 * 检测网络连接状态、带宽、延迟等
 *
 * 使用示例:
 * ```tsx
 * const network = useNetworkState();
 * if (!network.isOnline) {
 *   // 显示离线提示
 * }
 * if (network.isSlow) {
 *   // 降级策略：不加载重型资源
 * }
 * ```
 */

import {useCallback, useEffect, useRef, useState} from 'react';

export interface NetworkInfo {
  /** 是否在线 */
  isOnline: boolean;
  /** 有效类型 (4g, 3g, 2g, 'slow-2g', 'offline') */
  effectiveType: string;
  /** 下行带宽 (Mbps) */
  downlink: number | null;
  /** 往返延迟 (ms) */
  rtt: number | null;
  /** 是否省流量模式 */
  saveData: boolean;
  /** 是否弱网络 (2g/3g/断网) */
  isSlow: boolean;
  /** 是否离线 */
  isOffline: boolean;
}

const DEFAULT_NETWORK: NetworkInfo = {
  isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
  effectiveType: 'unknown',
  downlink: null,
  rtt: null,
  saveData: false,
  isSlow: false,
  isOffline: false
};

/**
 * 从 Navigation API 估算实际网络延迟
 */
function getNetworkMetrics(): Partial<NetworkInfo> {
  if (typeof performance === 'undefined') return {};

  const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
  if (!nav) return {};

  return {
    rtt: Math.round(nav.connectEnd - nav.connectStart) || null
  };
}

/**
 * 网络状态 Hook
 */
export function useNetworkState(): NetworkInfo {
  const [state, setState] = useState<NetworkInfo>(() => {
    if (typeof window === 'undefined') return DEFAULT_NETWORK;
    return getNetworkState();
  });

  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    const handleOnline = () => updateState();
    const handleOffline = () => updateState();

    // Navigator connection API
    const connection = (navigator as any).connection ||
      (navigator as any).mozConnection ||
      (navigator as any).webkitConnection;

    let connectionHandler: (() => void) | null = null;
    if (connection) {
      connectionHandler = () => updateState();
      connection.addEventListener?.('change', connectionHandler);
    }

    function updateState() {
      const ns = getNetworkState();
      if (
        ns.isOnline !== stateRef.current.isOnline ||
        ns.effectiveType !== stateRef.current.effectiveType
      ) {
        setState(ns);
      }
    }

    window.addEventListener('online', handleOnline, {passive: true});
    window.addEventListener('offline', handleOffline, {passive: true});

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      if (connection && connectionHandler) {
        connection.removeEventListener?.('change', connectionHandler);
      }
    };
  }, []);

  return state;
}

function getNetworkState(): NetworkInfo {
  const isOnline = typeof navigator !== 'undefined' ? navigator.onLine : true;

  const connection = (navigator as any).connection ||
    (navigator as any).mozConnection ||
    (navigator as any).webkitConnection;

  const effectiveType = connection?.effectiveType || 'unknown';
  const downlink = connection?.downlink ?? null;
  const rtt = connection?.rtt ?? null;
  const saveData = connection?.saveData ?? false;

  const isSlow = ['slow-2g', '2g', '3g'].includes(effectiveType);

  return {
    isOnline,
    effectiveType,
    downlink,
    rtt,
    saveData,
    isSlow,
    isOffline: !isOnline
  };
}

/**
 * 网络感知请求 Hook
 * 在弱网络下自动降级
 */
export function useNetworkAwareFetch() {
  const network = useNetworkState();

  const fetchWithRetry = useCallback(async <T>(
    url: string,
    options?: RequestInit,
    maxRetries: number = 2
  ): Promise<T> => {
    let lastError: Error | null = null;

    for (let i = 0; i <= maxRetries; i++) {
      try {
        // 弱网络增加超时
        const timeout = network.isSlow ? 15000 : 5000;
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeout);

        const response = await fetch(url, {
          ...options,
          signal: controller.signal
        });
        clearTimeout(timer);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        return await response.json() as T;
      } catch (e) {
        lastError = e as Error;
        if (i < maxRetries && network.isOnline) {
          // 指数退避
          await new Promise(r => setTimeout(r, Math.pow(2, i) * 1000));
        }
      }
    }

    throw lastError || new Error('Network request failed');
  }, [network.isOnline, network.isSlow]);

  return {
    fetchWithRetry,
    network
  };
}

export default useNetworkState;
