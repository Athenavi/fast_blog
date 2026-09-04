/**
 * useAsyncScript - 第三方脚本异步加载 Hook
 * 安全地异步加载第三方脚本，支持 retry、timeout 和错误处理
 *
 * 功能：
 * 1. 异步加载外部脚本
 * 2. 加载超时控制
 * 3. 自动重试机制
 * 4. 加载状态管理
 * 5. 卸载清理
 * 6. 弱网络下自动跳过
 *
 * 使用示例:
 * ```tsx
 * // 加载 Chart.js
 * const {loaded, error} = useAsyncScript({
 *   src: 'https://cdn.example.com/chart.js',
 *   id: 'chart-js',
 *   strategy: 'lazyOnload', // 'eager' | 'lazyOnload' | 'worker'
 *   onLoad: () => console.log('Chart.js loaded'),
 *   onError: () => console.log('Chart.js failed')
 * });
 *
 * // 延迟加载 Three.js
 * const {load, loaded} = useAsyncScript({
 *   src: '/three.min.js',
 *   strategy: 'manual'
 * });
 * ```
 */

import {useCallback, useEffect, useRef, useState} from 'react';
import {useNetworkState} from './useNetworkState';

export type ScriptStrategy = 'eager' | 'lazyOnload' | 'manual' | 'worker';

interface ScriptLoaderState {
  /** 加载状态 */
  loaded: boolean;
  /** 加载中 */
  loading: boolean;
  /** 加载失败 */
  error: Error | null;
  /** 是否被跳过（弱网络等） */
  skipped: boolean;
}

export interface AsyncScriptOptions {
  /** 脚本 URL */
  src: string;
  /** 脚本 ID，用于去重 */
  id?: string;
  /** 加载策略 */
  strategy?: ScriptStrategy;
  /** 超时时间 (ms) */
  timeout?: number;
  /** 最大重试次数 */
  maxRetries?: number;
  /** 是否立即加载 */
  immediate?: boolean;
  /** 是否缓存加载结果 */
  cache?: boolean;
  /** 加载成功回调 */
  onLoad?: () => void;
  /** 加载失败回调 */
  onError?: (error: Error) => void;
  /** 额外属性 */
  attributes?: Record<string, string>;
  /** 弱网络下是否跳过 */
  skipOnSlowNetwork?: boolean;
  /** 离线时是否跳过 */
  skipWhenOffline?: boolean;
}

// 全局脚本加载缓存
const scriptCache = new Map<string, Promise<void>>();

export function useAsyncScript(options: AsyncScriptOptions) {
  const {
    src,
    id,
    strategy = 'lazyOnload',
    timeout = 10000,
    maxRetries = 1,
    cache = true,
    skipOnSlowNetwork = true,
    skipWhenOffline = true,
    onLoad,
    onError,
    attributes = {}
  } = options;

  const network = useNetworkState();
  const [state, setState] = useState<ScriptLoaderState>({
    loaded: false,
    loading: false,
    error: null,
    skipped: false
  });
  const loadedRef = useRef(false);
  const mountedRef = useRef(true);

  // 检查是否应该跳过加载
  const shouldSkip = useCallback(() => {
    if (skipWhenOffline && !network.isOnline) return true;
    if (skipOnSlowNetwork && (network.isSlow || network.saveData)) return true;
    return false;
  }, [network, skipOnSlowNetwork, skipWhenOffline]);

  const loadScript = useCallback(async (): Promise<void> => {
    // 如果已经加载过，直接返回
    if (loadedRef.current) return;

    // 检查是否需要跳过
    if (shouldSkip()) {
      setState({loaded: false, loading: false, error: null, skipped: true});
      return;
    }

    // 检查全局缓存
    if (cache && scriptCache.has(src)) {
      try {
        await scriptCache.get(src);
        if (mountedRef.current) {
          loadedRef.current = true;
          setState({loaded: true, loading: false, error: null, skipped: false});
          onLoad?.();
        }
      } catch (err) {
        if (mountedRef.current) {
          setState({loaded: false, loading: false, error: err as Error, skipped: false});
          onError?.(err as Error);
        }
      }
      return;
    }

    // 设置加载状态
    if (mountedRef.current) {
      setState(prev => ({...prev, loading: true, error: null}));
    }

    const loadAttempt = async (): Promise<void> => {
      let lastError: Error | null = null;

      for (let i = 0; i <= maxRetries; i++) {
        try {
          const script = document.createElement('script');
          script.src = src;
          script.async = true;
          script.defer = true;

          if (id) script.id = id;
          Object.entries(attributes).forEach(([key, value]) => {
            script.setAttribute(key, value);
          });

          await new Promise<void>((resolve, reject) => {
            // 超时控制
            const timer = setTimeout(() => {
              reject(new Error(`Script load timeout: ${src}`));
            }, timeout);

            script.onload = () => {
              clearTimeout(timer);
              resolve();
            };

            script.onerror = () => {
              clearTimeout(timer);
              const error = new Error(`Script load failed: ${src}`);
              reject(error);
            };

            document.head.appendChild(script);
          });

          return; // 成功，退出重试循环
        } catch (err) {
          lastError = err as Error;
          if (i < maxRetries) {
            // 指数退避
            await new Promise(r => setTimeout(r, Math.pow(2, i) * 500));
          }
        }
      }

      throw lastError || new Error(`Failed to load script: ${src}`);
    };

    try {
      let promise: Promise<void>;

      if (cache) {
        promise = loadAttempt();
        scriptCache.set(src, promise);
      } else {
        promise = loadAttempt();
      }

      await promise;

      if (mountedRef.current) {
        loadedRef.current = true;
        setState({loaded: true, loading: false, error: null, skipped: false});
        onLoad?.();
      }
    } catch (err) {
      if (mountedRef.current) {
        setState({loaded: false, loading: false, error: err as Error, skipped: false});
        onError?.(err as Error);
      }

      // 从缓存中移除失败的脚本
      if (cache) {
        scriptCache.delete(src);
      }
    }
  }, [src, id, cache, maxRetries, timeout, shouldSkip, onLoad, onError, attributes]);

  // 手动加载方法
  const load = useCallback(() => {
    loadScript();
  }, [loadScript]);

  // 根据策略自动加载
  useEffect(() => {
    mountedRef.current = true;

    const execute = () => {
      if (shouldSkip()) {
        setState({loaded: false, loading: false, error: null, skipped: true});
        return;
      }
      loadScript();
    };

    switch (strategy) {
      case 'eager':
        execute();
        break;

      case 'lazyOnload':
        if (document.readyState === 'complete') {
          execute();
        } else {
          window.addEventListener('load', execute, {once: true});
          return () => window.removeEventListener('load', execute);
        }
        break;

      case 'manual':
        // 不自动加载，等待 load() 调用
        break;

      case 'worker':
        // 使用 requestIdleCallback 在空闲时加载
        if (typeof requestIdleCallback !== 'undefined') {
          requestIdleCallback(() => execute(), {timeout: 2000});
        } else {
          setTimeout(execute, 1000);
        }
        break;
    }

    return () => {
      mountedRef.current = false;
    };
  }, [src, strategy, loadScript, shouldSkip]);

  return {
    ...state,
    /** 手动加载方法 (strategy='manual' 时使用) */
    load,
    /** 移除缓存 */
    clearCache: useCallback(() => {
      scriptCache.delete(src);
    }, [src])
  };
}

/**
 * 条件渲染组件 - 脚本加载完成后才渲染子组件
 */
export const ScriptGate: React.FC<{
  /** 脚本加载状态 */
  scriptReady: boolean;
  /** 加载中占位 */
  loading?: React.ReactNode;
  /** 加载失败占位 */
  error?: React.ReactNode;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}> = ({scriptReady, loading, error, fallback, children}) => {
  if (!scriptReady) {
    return <>{loading || fallback || null
  }
    </>;
  }
  return <>{children} < />;
};

/**
 * 异步加载的组件包装器
 */
export function withAsyncScript<T>(
  WrappedComponent: React.ComponentType<T & { scriptLoaded: boolean }>,
  scriptOptions: Omit<AsyncScriptOptions, 'onLoad' | 'onError'>
): React.FC<T> {
  return (props: T) => {
    const {loaded, loading} = useAsyncScript(scriptOptions);
    return (
      <WrappedComponent
        {...(props as any)}
    scriptLoaded = {loaded}
      >
      {!
    loaded && loading ? null : props.children
  }
    </WrappedComponent>
  )
    ;
  };
}

export default useAsyncScript;
