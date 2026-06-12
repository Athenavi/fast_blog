'use client';

import {useEffect, useState} from 'react';
import {useToast} from '@/components/ui/toast-provider';

/**
 * ForbiddenListener — 全局 403 监听
 *
 * 在 App 层挂载一次，所有 apiClient 和 adminApi 的 403 响应
 * 都会触发 toast 提示，且若连续 3 次 403 则跳转到首页。
 *
 * 用法:
 *   <ForbiddenListener />
 */
export function ForbiddenListener() {
  const toast = useToast();
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail || {};
      const msg = detail.error || '权限不足，请联系管理员';

      toast.error(msg);

      setCount(prev => {
        const next = prev + 1;
        if (next >= 3) {
          // 连续 3 次 403 → 跳转
          window.location.href = '/admin';
        }
        return next;
      });
    };

    window.addEventListener('api:forbidden', handler);
    return () => window.removeEventListener('api:forbidden', handler);
  }, [toast]);

  return null;
}
