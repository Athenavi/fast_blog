/**
 * useRequestQueue - 请求队列 Hook
 * 在弱网络下自动排队请求，避免并发连接过多导致失败
 * 支持优先级排序和请求取消
 *
 * 使用示例:
 * ```tsx
 * const queue = useRequestQueue();
 *
 * // 添加请求到队列
 * const promise = queue.enqueue({
 *   key: 'getUser',
 *   url: '/api/user/123',
 *   priority: 'high' // 'low' | 'normal' | 'high'
 * });
 *
 * const result = await promise;
 * ```
 */

import {useCallback, useEffect, useRef, useState} from 'react';
import {useNetworkState} from './useNetworkState';
import {cachedFetch} from '@/lib/api-cache';

export type RequestPriority = 'low' | 'normal' | 'high';

export interface QueuedRequest<T = any> {
  key: string;
  url: string;
  options?: RequestInit;
  ttl?: number;
  priority?: RequestPriority;
}

export interface QueueStats {
  pending: number;
  processing: number;
  completed: number;
  failed: number;
}

export interface UseRequestQueueOptions {
  /** 弱网络下的最大并发请求数 */
  weakNetworkConcurrency?: number;
  /** 正常网络下的最大并发请求数 */
  normalConcurrency?: number;
  /** 请求队列最大长度（超出时丢弃最低优先级请求） */
  maxQueueSize?: number;
  /** 单个请求超时时间 (ms) */
  requestTimeout?: number;
}

const PRIORITY_ORDER: Record<RequestPriority, number> = {
  high: 0,
  normal: 1,
  low: 2
};

export function useRequestQueue(options: UseRequestQueueOptions = {}) {
  const {
    weakNetworkConcurrency = 1,
    normalConcurrency = 3,
    maxQueueSize = 20,
    requestTimeout = 10000
  } = options;

  const network = useNetworkState();
  const queueRef = useRef<Array<{
    request: QueuedRequest;
    resolve: (value: any) => void;
    reject: (error: Error) => void;
    priority: number;
  }>>([]);
  const processingRef = useRef<Set<string>>(new Set());
  const statsRef = useRef<QueueStats>({pending: 0, processing: 0, completed: 0, failed: 0});
  const abortControllersRef = useRef<Map<string, AbortController>>(new Map());
  const [stats, setStats] = useState<QueueStats>(statsRef.current);

  // 当前并发数
  const getConcurrency = useCallback(() => {
    return network.isSlow ? weakNetworkConcurrency : normalConcurrency;
  }, [network.isSlow, weakNetworkConcurrency, normalConcurrency]);

  // 处理队列中的下一个请求
  const processNext = useCallback(async () => {
    const queue = queueRef.current;
    const concurrency = getConcurrency();

    // 排序队列：高优先级先处理
    queue.sort((a, b) => a.priority - b.priority);

    while (queue.length > 0 && processingRef.current.size < concurrency) {
      const item = queue.shift();
      if (!item) break;

      const {request, resolve, reject} = item;
      processingRef.current.add(request.key);
      statsRef.current.processing++;
      setStats({...statsRef.current});

      const controller = new AbortController();
      abortControllersRef.current.set(request.key, controller);

      try {
        // 使用 AbortSignal.timeout 和 controller.signal 中的任何一个先触发
        const timeoutSignal = AbortSignal.timeout(requestTimeout);

        // 创建组合信号：取消或超时都中断
        const abortAny = AbortSignal.any([controller.signal, timeoutSignal]);

        const result = await cachedFetch(
          request.url,
          {
            ...request.options,
            signal: abortAny
          },
          request.ttl
        );

        processingRef.current.delete(request.key);
        abortControllersRef.current.delete(request.key);
        statsRef.current.processing--;
        statsRef.current.completed++;
        setStats({...statsRef.current});

        resolve(result);
      } catch (error) {
        processingRef.current.delete(request.key);
        abortControllersRef.current.delete(request.key);
        statsRef.current.processing--;
        statsRef.current.failed++;
        setStats({...statsRef.current});

        const errorObj = error instanceof Error ? error : new Error(String(error));
        reject(errorObj);
      }

      // 处理下一个
      if (queue.length > 0) {
        // 使用 microtask 确保 UI 有机会更新
        Promise.resolve().then(() => processNext());
      }
    }
  }, [getConcurrency, requestTimeout]);

  // 添加请求到队列
  const enqueue = useCallback(<T = any>(request: QueuedRequest): Promise<T> => {
    // 检查队列是否已满
    if (queueRef.current.length >= maxQueueSize) {
      // 尝试找到最低优先级请求并丢弃
      const lowestIndex = queueRef.current.reduce((minIdx, item, idx) => {
        return item.priority > queueRef.current[minIdx].priority ? idx : minIdx;
      }, 0);

      if (PRIORITY_ORDER[request.priority || 'normal'] > queueRef.current[lowestIndex].priority) {
        // 丢弃最低优先级请求
        const discarded = queueRef.current.splice(lowestIndex, 1)[0];
        statsRef.current.pending--;
        setStats({...statsRef.current});
        discarded.reject(new Error('Request discarded due to queue limit'));
      } else {
        return Promise.reject(new Error('Queue is full'));
      }
    }

    statsRef.current.pending++;
    setStats({...statsRef.current});

    const promise = new Promise<T>((resolve, reject) => {
      queueRef.current.push({
        request,
        resolve,
        reject,
        priority: PRIORITY_ORDER[request.priority || 'normal']
      });

      // 启动处理
      processNext();
    });

    return promise;
  }, [maxQueueSize, processNext]);

  // 取消请求
  const cancel = useCallback((key: string) => {
    const controller = abortControllersRef.current.get(key);
    if (controller) {
      controller.abort();
      abortControllersRef.current.delete(key);
    }

    // 从队列中移除
    const idx = queueRef.current.findIndex(item => item.request.key === key);
    if (idx !== -1) {
      queueRef.current.splice(idx, 1);
      statsRef.current.pending--;
      setStats({...statsRef.current});
    }
  }, []);

  // 清空队列
  const clear = useCallback(() => {
    // 取消所有待处理请求
    queueRef.current.forEach(item => {
      item.reject(new Error('Queue cleared'));
    });
    queueRef.current = [];

    // 取消所有正在处理的请求
    abortControllersRef.current.forEach(controller => controller.abort());
    abortControllersRef.current.clear();

    processingRef.current.clear();

    statsRef.current = {pending: 0, processing: 0, completed: 0, failed: 0};
    setStats({...statsRef.current});
  }, []);

  // 清理
  useEffect(() => {
    return () => {
      clear();
    };
  }, [clear]);

  return {
    enqueue,
    cancel,
    clear,
    stats,
    network
  };
}

export default useRequestQueue;
