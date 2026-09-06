/**
 * useNetworkState - 网络状态检测 Hook
 * 检测网络连接状态、带宽、延迟等
 *
 * 增强功能:
 * - 网络质量评分 (0-100)
 * - 自适应超时计算
 * - 网络变化事件
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
 * if (network.qualityScore < 50) {
 *   // 使用更激进的缓存策略
 * }
 * ```
 */

import {useCallback, useEffect, useRef, useState} from 'react';
import {getConfig} from '@/lib/config';

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
  /** 网络质量评分 (0-100, 越高越好) */
  qualityScore: number;
  /** 建议的请求超时时间 (ms) */
  suggestedTimeout: number;
  /** 建议的最大并发连接数 */
  suggestedConcurrency: number;
  /** 建议的图片质量 (0-1) */
  suggestedImageQuality: number;
  /** 网络类型标签 */
  networkLabel: 'excellent' | 'good' | 'fair' | 'poor' | 'offline';
}

const DEFAULT_NETWORK: NetworkInfo = {
  isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
  effectiveType: 'unknown',
  downlink: null,
  rtt: null,
  saveData: false,
  isSlow: false,
  isOffline: false,
  qualityScore: 100,
  suggestedTimeout: 5000,
  suggestedConcurrency: 6,
  suggestedImageQuality: 1,
  networkLabel: 'excellent',
};

/**
 * 计算网络质量评分 (0-100)
 * 基于带宽、延迟和网络类型
 */
function calculateQualityScore(effectiveType: string, downlink: number | null, rtt: number | null): number {
  if (effectiveType === 'offline' || effectiveType === 'slow-2g') return 0;

  let score = 100;

  // 基于网络类型扣分
  switch (effectiveType) {
    case '2g':
      score -= 80;
      break;
    case '3g':
      score -= 40;
      break;
    case '4g':
      score -= 10;
      break;
    case 'unknown':
      score -= 20;
      break;
  }

  // 基于带宽扣分 (Mbps)
  if (downlink !== null) {
    if (downlink < 0.1) score -= 30;
    else if (downlink < 0.5) score -= 20;
    else if (downlink < 1) score -= 10;
    else if (downlink > 10) score += 5; // 高速网络奖励
  }

  // 基于延迟扣分 (ms)
  if (rtt !== null) {
    if (rtt > 1000) score -= 30;
    else if (rtt > 500) score -= 20;
    else if (rtt > 200) score -= 10;
    else if (rtt < 50) score += 5; // 低延迟奖励
  }

  return Math.max(0, Math.min(100, score));
}

/**
 * 根据网络状态计算建议的超时时间
 */
function calculateSuggestedTimeout(effectiveType: string, rtt: number | null): number {
  const baseTimeout = rtt ? rtt * 3 : 5000; // 3倍 RTT 作为基础

  switch (effectiveType) {
    case 'slow-2g':
    case '2g':
      return Math.max(baseTimeout, 15000);
    case '3g':
      return Math.max(baseTimeout, 10000);
    case '4g':
      return Math.max(baseTimeout, 5000);
    default:
      return Math.max(baseTimeout, 3000);
  }
}

/**
 * 根据网络状态计算建议的并发连接数
 */
function calculateSuggestedConcurrency(effectiveType: string): number {
  switch (effectiveType) {
    case 'slow-2g':
    case '2g':
      return 1;
    case '3g':
      return 2;
    case '4g':
      return 4;
    default:
      return 6;
  }
}

/**
 * 根据网络状态计算建议的图片质量
 */
function calculateSuggestedImageQuality(effectiveType: string, saveData: boolean): number {
  if (saveData) return 0.5;

  switch (effectiveType) {
    case 'slow-2g':
    case '2g':
      return 0.3;
    case '3g':
      return 0.6;
    case '4g':
      return 0.85;
    default:
      return 1;
  }
}

/**
 * 获取网络标签
 */
function getNetworkLabel(score: number, isOnline: boolean): NetworkInfo['networkLabel'] {
  if (!isOnline) return 'offline';
  if (score >= 80) return 'excellent';
  if (score >= 60) return 'good';
  if (score >= 40) return 'fair';
  return 'poor';
}

/**
 * 从 Navigation API 估算实际网络延迟
 */
function getNetworkMetrics(): { rtt: number | null } {
  if (typeof performance === 'undefined') return {rtt: null};

  const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
  if (!nav) return {rtt: null};

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

  // 网络变化回调
  const onChangeRef = useRef<((prev: NetworkInfo, next: NetworkInfo) => void) | null>(null);
  const onChangedRef = useRef<((network: NetworkInfo) => void) | null>(null);

  // 用于主动网络检测的 ref
  const pingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const handleOnline = () => {
      // 延迟更新，等待网络真正恢复
      updateState();
      schedulePingCheck();
    };
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

    // 主动 Ping 检测网络是否真的可用
    function schedulePingCheck() {
      if (pingTimeoutRef.current) {
        clearTimeout(pingTimeoutRef.current);
      }
      // 在 1 秒后检查网络
      pingTimeoutRef.current = setTimeout(() => {
        pingNetwork().then((pingOnline) => {
          const prev = stateRef.current;
          const browserOnline = navigator.onLine;
          // 如果 ping 成功，强制设置为在线（即使 navigator.onLine 返回 false）
          // 如果 ping 失败且浏览器也认为离线，才标记为离线
          const shouldBeOffline = !pingOnline && !browserOnline;
          const isActuallyOnline = pingOnline || (browserOnline && !shouldBeOffline);
          if (prev.isOnline !== isActuallyOnline) {
            const ns = {...getNetworkState(), isOnline: isActuallyOnline, isOffline: !isActuallyOnline};
            if (!isActuallyOnline) {
              ns.isSlow = true;
              ns.qualityScore = 0;
              ns.networkLabel = 'offline';
            } else {
              // 如果在网络上，确保清除离线状态
              if (ns.isOffline) {
                ns.isOffline = false;
                ns.isSlow = false;
              }
            }
            onChangeRef.current?.(prev, ns);
            onChangedRef.current?.(ns);
            setState(ns);
          }
        });
      }, 1000);
    }

    async function pingNetwork(): Promise<boolean> {
      try {
        // 使用配置的 API_BASE_URL 构建完整路径，以支持开发环境跨端口访问
        const {API_BASE_URL, API_PREFIX} = getConfig();
        const healthUrl = `${API_BASE_URL}${API_PREFIX}/health`;

        // 尝试 fetching 后端健康检查端点来验证连接
        await fetch(healthUrl, {
          method: 'GET',
          cache: 'no-store',
          signal: AbortSignal.timeout(3000)
        });
        return true;
      } catch {
        // 如果 API 请求失败，尝试 fetch 当前站点的静态资源（用于检测前端服务器是否可用）
        try {
          await fetch('/favicon.ico', {
            method: 'HEAD',
            cache: 'no-store',
            signal: AbortSignal.timeout(2000)
          });
          return true;
        } catch {
          return false;
        }
      }
    }

    function updateState() {
      const ns = getNetworkState();
      const prev = stateRef.current;

      if (
        ns.isOnline !== prev.isOnline ||
        ns.effectiveType !== prev.effectiveType ||
        ns.qualityScore !== prev.qualityScore
      ) {
        // 通知回调
        onChangeRef.current?.(prev, ns);
        onChangedRef.current?.(ns);
        setState(ns);
      }
    }

    window.addEventListener('online', handleOnline, {passive: true});
    window.addEventListener('offline', handleOffline, {passive: true});

    // 初始化时也进行一次 ping 检查
    schedulePingCheck();

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      if (connection && connectionHandler) {
        connection.removeEventListener?.('change', connectionHandler);
      }
      if (pingTimeoutRef.current) {
        clearTimeout(pingTimeoutRef.current);
      }
    };
  }, []);

  // 注册网络变化回调
  const onNetworkChange = useCallback((callback: (prev: NetworkInfo, next: NetworkInfo) => void) => {
    onChangeRef.current = callback;
    return () => {
      if (onChangeRef.current === callback) {
        onChangeRef.current = null;
      }
    };
  }, []);

  const onNetworkChanged = useCallback((callback: (network: NetworkInfo) => void) => {
    onChangedRef.current = callback;
    return () => {
      if (onChangedRef.current === callback) {
        onChangedRef.current = null;
      }
    };
  }, []);

  return {
    ...state,
    onNetworkChange,
    onNetworkChanged
  };
}

function getNetworkState(): NetworkInfo {
  // 仅在服务器端渲染时直接返回默认值
  if (typeof navigator === 'undefined') {
    return DEFAULT_NETWORK;
  }

  const isOnline = navigator.onLine;

  const connection = (navigator as any).connection ||
    (navigator as any).mozConnection ||
    (navigator as any).webkitConnection;

  const effectiveType = connection?.effectiveType || 'unknown';
  const downlink = connection?.downlink ?? null;
  const rtt = connection?.rtt ?? null;
  const saveData = connection?.saveData ?? false;

  const isOffline = !isOnline;
  // 只有在确认离线或确实是慢速网络时才标记为 isSlow
  // 'unknown' 不应该被视为慢速网络
  const isSlow = isOffline || (connection && ['slow-2g', '2g', '3g'].includes(effectiveType));

  // 获取实际测量到的 RTT
  const measuredMetrics = getNetworkMetrics();
  const actualRtt = rtt ?? measuredMetrics.rtt;

  const qualityScore = calculateQualityScore(effectiveType, downlink, actualRtt);
  const suggestedTimeout = calculateSuggestedTimeout(effectiveType, actualRtt);
  const suggestedConcurrency = calculateSuggestedConcurrency(effectiveType);
  const suggestedImageQuality = calculateSuggestedImageQuality(effectiveType, saveData);
  const networkLabel = getNetworkLabel(qualityScore, isOnline);

  return {
    isOnline,
    effectiveType,
    downlink,
    rtt: actualRtt,
    saveData,
    isSlow,
    isOffline: !isOnline,
    qualityScore,
    suggestedTimeout,
    suggestedConcurrency,
    suggestedImageQuality,
    networkLabel,
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
        // 使用自适应超时
        const timeout = network.suggestedTimeout * (i + 1);
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
  }, [network.isOnline, network.suggestedTimeout]);

  return {
    fetchWithRetry,
    network
  };
}

export default useNetworkState;
