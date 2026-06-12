'use client';

import {useEffect, useState, useRef} from 'react';

/**
 * 请求级缓存 — 同一页面内多次 useCapability('article:create') 只发一次请求
 */
const _permCache = new Map<string, boolean | 'loading'>();
let _cacheVersion = 0;

/**
 * useCapability — 组件级权限检查 hook
 *
 * 检查当前用户是否拥有指定权限代码。
 * 内部调用 V3 check-permission 端点，V3 不可用时自动降级到 V2。
 *
 * 用法:
 *   const canCreate = useCapability('article:create');
 *   {canCreate && <CreateButton />}
 *
 *   const canDelete = useCapability('user:delete');
 *   {canDelete && <DeleteButton />}
 *
 * 性能:
 *   - 同页面同 capability 只发一次请求（Map 缓存）
 *   - 组件卸载不清缓存（其他组件可能正在用）
 *   - 返回 boolean | undefined (undefined = loading)
 */
export function useCapability(code?: string): boolean | undefined {
  const [result, setResult] = useState<boolean | undefined>(
    code ? _getCached(code) : true,
  );
  const codeRef = useRef(code);
  codeRef.current = code;

  useEffect(() => {
    if (!code) {
      setResult(true);
      return;
    }

    const cached = _getCached(code);
    if (cached !== undefined) {
      setResult(cached);
      return;
    }

    // 标记 loading 防止重复请求
    _permCache.set(code, 'loading');
    let cancelled = false;

    (async () => {
      try {
        const {adminPermissionService} = await import(
          '@/lib/api/admin-service'
        );
        const res = await adminPermissionService.check(code);
        const has = res.data?.has_permission === true;
        _permCache.set(code, has);
        if (!cancelled) setResult(has);
      } catch {
        // 保守放行（后端 Depends(Permission) 兜底）
        _permCache.set(code, true);
        if (!cancelled) setResult(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [code]);

  return result;
}

function _getCached(code: string): boolean | undefined {
  const v = _permCache.get(code);
  if (v === 'loading' || v === undefined) return undefined;
  return v;
}

/**
 * 清空 useCapability 缓存（用户角色变更后调用）
 */
export function clearCapabilityCache() {
  _permCache.clear();
}
