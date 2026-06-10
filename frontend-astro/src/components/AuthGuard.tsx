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
    const check = async () => {
      try {
        // 直接调用 /users/me 验证 cookie 中的 token
        // 浏览器会自动发送 httponly 的 access_token/refresh_token
        const res = await apiClient.get(USERS.ME);
        if (res.success && res.data) {
          if (!cancelled) setStatus('authenticated');
        } else {
          if (!cancelled) setStatus('unauthenticated');
        }
      } catch {
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
