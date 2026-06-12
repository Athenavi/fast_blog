/**
 * V3 管理端 API 客户端
 *
 * 特性:
 *   1. 自动 V3 → V2 降级 — V3 重试 3 次后自动降级到 V2 重试 2 次
 *   2. 前端无版本路径硬编码 — 组件只调用 service 方法
 *   3. 与 base-client.ts 共享认证（cookie / token refresh）
 *
 * 用法:
 *   import { adminApi } from '@/lib/api/admin-api-client';
 *   const res = await adminApi.get('/admin/users', '/users/', { page: 1 });
 */

import {getConfig} from '@/lib/config';
import type {ApiResponse} from '@/lib/api/base-types';

// ─── Cookie helpers ──────────────────────────────
function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  for (const c of document.cookie.split(';')) {
    const [n, v] = c.trim().split('=');
    if (n === name && v) return decodeURIComponent(v);
  }
  return null;
}

function clearCookie(name: string) {
  if (typeof document === 'undefined') return;
  document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC; SameSite=Lax`;
}

// ─── Token refresh (引用 base-client 的逻辑) ─────
let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

async function doRefreshToken(): Promise<boolean> {
  if (typeof document === 'undefined') return false;
  try {
    const base = getConfig().API_BASE_URL || '';
    const res = await fetch(`${base}/api/v2/auth/token/refresh`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      credentials: 'include',
      body: JSON.stringify({}),
    });
    if (!res.ok) return false;
    const json = await res.json();
    return !!(json.success && json.data);
  } catch {
    return false;
  }
}

async function ensureTokenFresh(): Promise<boolean> {
  if (isRefreshing && refreshPromise) return refreshPromise;
  isRefreshing = true;
  refreshPromise = doRefreshToken();
  const result = await refreshPromise;
  isRefreshing = false;
  refreshPromise = null;
  return result;
}

// ─── 延迟工具 ────────────────────────────────────
function delay(ms: number): Promise<void> {
  return new Promise(r => setTimeout(r, ms));
}

// ─── 单次请求 ────────────────────────────────────
async function singleRequest(
  method: string,
  fullUrl: string,
  body?: any,
  contentType?: string,
): Promise<Response> {
  const opts: RequestInit = {
    method,
    credentials: 'include',
  };

  if (body && method !== 'GET') {
    if (body instanceof FormData) {
      opts.body = body;
    } else {
      opts.headers = {'Content-Type': contentType || 'application/json'};
      opts.body = JSON.stringify(body);
    }
  }

  const accessToken = getCookie('access_token');
  if (accessToken) {
    opts.headers = {
      ...(opts.headers as Record<string, string> || {}),
      'Authorization': `Bearer ${accessToken}`,
    };
  }

  return fetch(fullUrl, opts);
}

// ─── 带重试的请求（指数退避） ────────────────────
async function retryRequest(
  method: string,
  fullUrl: string,
  maxRetries: number,
  body?: any,
  contentType?: string,
): Promise<Response> {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const res = await singleRequest(method, fullUrl, body, contentType);

    // 401 → refresh token 后重试
    if (res.status === 401) {
      const refreshed = await ensureTokenFresh();
      if (refreshed) continue; // 重试当前 attempt（不计数）
    }

    if (res.ok || res.status === 403) {
      // 成功或明确拒绝 → 直接返回
      return res;
    }

    // 服务端错误 (5xx) → 重试
    if (res.status >= 500 && attempt < maxRetries) {
      await delay(100 * Math.pow(2, attempt)); // 100ms, 200ms, 400ms
      continue;
    }

    // 4xx 其他 → 直接返回
    return res;
  }

  // 全部重试耗尽
  return new Response(null, {status: 504, statusText: 'Retry exhausted'});
}

// ─── 构建完整 URL ────────────────────────────────
function buildFullUrl(path: string, params?: Record<string, any>): string {
  const base = getConfig().API_BASE_URL || '';
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  let url = `${base}${path}`;
  if (!params) return url;
  const qs = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join('&');
  return qs ? `${url}?${qs}` : url;
}

// ─── 解析响应 ────────────────────────────────────
async function parseResponse<T>(res: Response): Promise<ApiResponse<T>> {
  try {
    const text = await res.text();
    return JSON.parse(text);
  } catch {
    return {success: false, error: `HTTP ${res.status}: ${res.statusText}`};
  }
}

// ─── 核心请求函数：V3 + V2 降级 ─────────────────
const RETRIES_V3 = 3;
const RETRIES_V2 = 2;

async function requestWithFallback<T = any>(
  method: string,
  v3Path: string,
  v2FallbackPath: string,
  body?: any,
  params?: Record<string, any>,
  contentType?: string,
): Promise<ApiResponse<T>> {
  // ── 阶段 1: 尝试 V3 ──
  const v3Url = buildFullUrl(v3Path, method === 'GET' ? params : undefined);
  const resV3 = await retryRequest(method, v3Url, RETRIES_V3, body, contentType);

  if (resV3.ok) {
    return parseResponse<T>(resV3);
  }

  // 403 是权限拒绝，不降级
  if (resV3.status === 403) {
    return parseResponse<T>(resV3);
  }

  // ── 阶段 2: 降级到 V2 ──
  const v2Url = buildFullUrl(v2FallbackPath, method === 'GET' ? params : undefined);
  const resV2 = await retryRequest(method, v2Url, RETRIES_V2, body, contentType);

  return parseResponse<T>(resV2);
}

// ─── 导出客户端 ──────────────────────────────────
export const adminApi = {
  get: <T = any>(
    v3Path: string,
    v2Fallback: string,
    params?: Record<string, any>,
  ) => requestWithFallback<T>('GET', v3Path, v2Fallback, undefined, params),

  post: <T = any>(
    v3Path: string,
    v2Fallback: string,
    body?: any,
  ) => requestWithFallback<T>('POST', v3Path, v2Fallback, body),

  put: <T = any>(
    v3Path: string,
    v2Fallback: string,
    body?: any,
  ) => requestWithFallback<T>('PUT', v3Path, v2Fallback, body),

  delete: <T = any>(
    v3Path: string,
    v2Fallback: string,
  ) => requestWithFallback<T>('DELETE', v3Path, v2Fallback),

  postForm: <T = any>(
    v3Path: string,
    v2Fallback: string,
    body?: Record<string, any>,
  ) => requestWithFallback<T>('POST', v3Path, v2Fallback, body, undefined, 'application/x-www-form-urlencoded'),
};
