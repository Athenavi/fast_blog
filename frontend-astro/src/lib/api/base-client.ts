// API client for frontend

interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  pagination?: any;
}

/** 构建完整 URL：补全 API 前缀 + 查询参数 */
function buildUrl(path: string, params?: Record<string, any>): string {
  // 如果已经是完整 /api/ 路径，直接使用
  let url = path.startsWith('/api/') ? path : `/api/v2${!path.startsWith('/') ? '/' : ''}${path}`;
  if (!params) return url;
  const qs = Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== null && v !== '')
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
      .join('&');
  return qs ? `${url}?${qs}` : url;
}

async function request<T = any>(
    method: string,
    path: string,
    contentType?: string,
    body?: any,
    params?: Record<string, any>
): Promise<ApiResponse<T>> {
  try {
    const url = buildUrl(path, method === 'GET' ? params : undefined);
    const opts: RequestInit = {
      method,
      credentials: 'include',
    };

    if (body && method !== 'GET') {
      if (contentType === 'application/x-www-form-urlencoded') {
        opts.headers = {'Content-Type': 'application/x-www-form-urlencoded'};
        opts.body = Object.entries(body)
            .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
            .join('&');
      } else {
        opts.headers = {'Content-Type': 'application/json'};
        opts.body = JSON.stringify(body);
      }
    }
    // Append query params for non-GET methods too
    if (params && method !== 'GET') {
      // Rebuild URL with params
      // (for uncommon cases where we need query + body)
    }
    const res = await fetch(url, opts);
    // Handle non-JSON responses
    const text = await res.text();
    try { return JSON.parse(text); } catch { return {success: false, error: text}; }
  } catch (e: any) {
    return {success: false, error: e.message || '网络异常'};
  }
}

export const apiClient = {
  get: <T = any>(path: string, params?: Record<string, any>) => request<T>('GET', path, undefined, undefined, params),
  post: <T = any>(path: string, body?: any) => request<T>('POST', path, 'application/json', body),
  postForm: <T = any>(path: string, body?: Record<string, any>) => request<T>('POST', path, 'application/x-www-form-urlencoded', body),
  put: <T = any>(path: string, body?: any) => request<T>('PUT', path, 'application/json', body),
  delete: <T = any>(path: string) => request<T>('DELETE', path),
};
