'use client';

import React, {useEffect, useState} from 'react';
import {Forbidden} from '@/components/admin/Forbidden';

/**
 * PermissionGuard — 组件级权限守卫
 *
 * 包裹管理端页面内容，按 capability 控制访问。
 * 内部调用 V3 的 check-permission 端点，V3 不可用时自动降级到 V2。
 *
 * 用法:
 *   <PermissionGuard capability="user:view">
 *     <UserTable />
 *   </PermissionGuard>
 */
export function PermissionGuard({
  capability,
  children,
  fallback,
}: {
  capability?: string;
  children: React.ReactNode;
  /** 可选：无权限时渲染的替代内容（默认显示 Forbidden 页） */
  fallback?: React.ReactNode;
}) {
  const [state, setState] = useState<'loading' | 'granted' | 'denied'>('loading');

  useEffect(() => {
    // 未指定 capability → 直接放行
    if (!capability) {
      setState('granted');
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        // 使用 lazy import 避免循环依赖
        const {adminPermissionService} = await import('@/lib/api/admin-service');
        const res = await adminPermissionService.check(capability);
        if (!cancelled) {
          setState(res.data?.has_permission ? 'granted' : 'denied');
        }
      } catch {
        // 检查失败 → 保守拒绝（安全优先）
        if (!cancelled) setState('denied');
      }
    })();

    return () => { cancelled = true; };
  }, [capability]);

  // ── loading ──
  if (state === 'loading') {
    return (
      <div className="min-h-[40vh] flex items-center justify-center">
        <div className="inline-block animate-spin rounded-full h-6 w-6 border-2 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  // ── 拒绝 ──
  if (state === 'denied') {
    return fallback ?? <Forbidden />;
  }

  // ── 放行 ──
  return <>{children}</>;
}
