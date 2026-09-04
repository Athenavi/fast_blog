/**
 * useBatchRequests - 批量请求 Hook
 * 将多个独立请求合并发送，减少 HTTP 往返次数
 *
 * 使用示例:
 * ```tsx
 * const { execute, isLoading, results, errors } = useBatchRequests();
 *
 * // 发起批量请求
 * execute([
 *   { key: 'articles', url: '/api/articles' },
 *   { key: 'categories', url: '/api/categories' },
 *   { key: 'user', url: '/api/user/me' },
 * ]);
 * ```
 */

import {useCallback, useRef, useState} from 'react';
import {apiCache, cachedFetchBatch, networkAwareBatchFetch} from '@/lib/api-cache';
import {useNetworkState} from './useNetworkState';

export interface BatchRequestEntry {
  key: string;
  url: string;
  options?: RequestInit;
  ttl?: number;
}

export interface BatchRequestResult<T extends Record<string, any>> {
  results: T;
  errors: Partial<Record<string, Error>>;
}

export interface UseBatchRequestsOptions {
  /** 批量超时时间 (ms) */
  timeout?: number;
  /** 是否并行请求（弱网络下自动串行） */
  parallel?: boolean;
  /** 是否在请求完成时自动更新缓存 */
  updateCache?: boolean;
}

export function useBatchRequests(options: UseBatchRequestsOptions = {}) {
  const {
    timeout = 10000,
    parallel = true,
    updateCache = true
  } = options;

  const network = useNetworkState();
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<Record<string, any | null>>({});
  const [errors, setErrors] = useState<Partial<Record<string, Error>>>({});
  const abortRef = useRef<AbortController | null>(null);

  const execute = useCallback(async <T extends Record<string, any>>(
    entries: BatchRequestEntry[]
  ): Promise<BatchRequestResult<T>> => {
    // 取消之前的请求
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setIsLoading(true);
    setErrors({});

    const batchEntries = entries.map(entry => ({
      ...entry,
      options: {
        ...entry.options,
        signal: controller.signal,
        // 弱网络增加超时
        signal: AbortSignal.timeout(timeout)
      }
    }));

    try {
      let fetchedResults: Record<string, any>;

      if (network.isSlow || !parallel) {
        // 弱网络：串行请求
        fetchedResults = await networkAwareBatchFetch<T>(
          batchEntries,
          {isSlow: network.isSlow, isOnline: network.isOnline}
        );
      } else {
        // 正常网络：并行请求
        fetchedResults = await cachedFetchBatch<T>(
          batchEntries,
          true
        );
      }

      setResults(fetchedResults);

      // 检查哪些请求失败
      const newErrors: Partial<Record<string, Error>> = {};
      for (const entry of entries) {
        if (fetchedResults[entry.key] === null && !apiCache.has(`etag:${entry.url}`)) {
          newErrors[entry.key] = new Error(`Request failed: ${entry.url}`);
        }
      }
      setErrors(newErrors);

      return {
        results: fetchedResults as T,
        errors: newErrors
      };
    } catch (error) {
      if (controller.signal.aborted) {
        return {results: {} as T, errors: {}};
      }
      const errorObj = error instanceof Error ? error : new Error(String(error));
      const newErrors: Partial<Record<string, Error>> = {};
      for (const entry of entries) {
        newErrors[entry.key] = errorObj;
      }
      setErrors(newErrors);
      throw errorObj;
    } finally {
      setIsLoading(false);
    }
  }, [timeout, parallel, network.isSlow, network.isOnline]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setIsLoading(false);
  }, []);

  const reset = useCallback(() => {
    setResults({});
    setErrors({});
  }, []);

  return {
    execute,
    cancel,
    reset,
    isLoading,
    results,
    errors
  };
}

export default useBatchRequests;
