'use client';

import React, {useEffect, useState} from 'react';
import {apiClient} from '@/lib/api/base-client';
import {USERS} from '@/lib/api/api-paths';

/**
 * AuthGuard - 认证守卫组件
 * 直接调用 /api/v2/users/me 验证登录状态（cookie 自动发送，httponly 兼容）
 */
export function AuthGuard({children}: {children: React.ReactNode}) {
  const [status, setStatus] = useState<'loading' | 'authenticated' | 'unauthenticated'>('loading');

  useEffect(() => {
    let cancelled = false;
    let retries = 0;
    const maxRetries = 2;

    const check = async (): Promise<void> => {
      try {
        const {getAccessTokenFromCookie} = await import('@/lib/auth-utils');
        // 如果没有 token cookie，直接判定未登录
        if (!getAccessTokenFromCookie()) {
          if (!cancelled) setStatus('unauthenticated');
          return;
        }

        const res = await apiClient.get(USERS.ME);
        if (res.success && res.data) {
          if (!cancelled) setStatus('authenticated');
        } else {
          // 有 token 但请求失败，重试一次（可能 config 尚未加载）
          if (retries < maxRetries) {
            retries++;
            await new Promise(r => setTimeout(r, 500));
            return check();
          }
          if (!cancelled) setStatus('unauthenticated');
        }
      } catch {
        if (retries < maxRetries) {
          retries++;
          await new Promise(r => setTimeout(r, 500));
          return check();
        }
        if (!cancelled) setStatus('unauthenticated');
      }
    };
    check();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (status === 'unauthenticated') {
      const next = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.replace(`/login?next=${next}`);
    }
  }, [status]);

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-2 border-blue-600 border-t-transparent mb-3" />
          <p className="text-sm text-gray-500">验证登录状态...</p>
        </div>
      </div>
    );
  }

  if (status === 'unauthenticated') return null;

  return <>{children}</>;
}
