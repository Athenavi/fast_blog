/**
 * useOptimistic - 乐观更新 Hook
 *
 * 在 API 响应返回前立即更新 UI，失败时自动回滚。
 * 适用于点赞、收藏、关注等用户交互场景。
 *
 * 使用示例:
 * ```tsx
 * const [opt, execute] = useOptimistic(
 *   { likes: article.likes },
 *   async (prev) => {
 *     await fetchLike(article.id);
 *     return { likes: prev.likes + 1 };
 *   }
 * );
 * ```
 */

import {useCallback, useEffect, useRef, useState} from 'react';

export interface UseOptimisticOptions<TData> {
  optimisticData?: TData | ((prev: TData) => TData);
  rollback?: (prev: TData, optimistic: TData, error: Error) => void;
  onSuccess?: (data: TData) => void;
  onError?: (error: Error) => void;
  disabled?: boolean;
}

export interface OptimisticState<TData> {
  data: TData;
  isSyncing: boolean;
  isConfirmed: boolean;
  error: Error | null;
}

export function useOptimistic<TData>(
  serverData: TData,
  mutation: (prev: TData) => Promise<TData>,
  options: UseOptimisticOptions<TData> = {}
): [OptimisticState<TData>, () => Promise<TData>] {

  const {optimisticData, rollback, onSuccess, onError, disabled = false} = options;
  const serverRef = useRef(serverData);
  serverRef.current = serverData;

  const [state, setState] = useState<OptimisticState<TData>>({
    data: serverData,
    isSyncing: false,
    isConfirmed: true,
    error: null,
  });

  // 当 serverData 变化时同步回主数据流
  useEffect(() => {
    if (state.isConfirmed) {
      setState(prev => ({...prev, data: serverData}));
    }
  }, [serverData, state.isConfirmed]);

  const execute = useCallback(async (): Promise<TData> => {
    if (disabled) {
      const result = await mutation(serverRef.current);
      onSuccess?.(result);
      return result;
    }
    const current = serverRef.current;
    const optData = typeof optimisticData === 'function'
      ? optimisticData(current)
      : optimisticData ?? current;

    setState({data: optData, isSyncing: true, isConfirmed: false, error: null});

    try {
      const result = await mutation(current);
      setState({data: result, isSyncing: false, isConfirmed: true, error: null});
      onSuccess?.(result);
      return result;
    } catch (e) {
      const error = e instanceof Error ? e : new Error(String(e));
      rollback?.(current, optData, error);
      setState({data: current, isSyncing: false, isConfirmed: true, error});
      onError?.(error);
      throw error;
    }
  }, [disabled, optimisticData, mutation, rollback, onSuccess, onError]);

  return [state, execute];
}

export default useOptimistic;
