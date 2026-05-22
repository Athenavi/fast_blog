// Minimal API client for admin pages

interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  pagination?: any;
}

function buildUrl(path: string, params?: Record<string, any>): string {
  // If already absolute with /api/, use as-is
  const url = path.startsWith('/api/') ? path : path;
  if (!params) return url;
  const qs = Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== null && v !== '')
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
      .join('&');
  return qs ? `${url}?${qs}` : url;
}

async function request<T = any>(method: string, path: string, body?: any, params?: Record<string, any>): Promise<ApiResponse<T>> {
  try {
    const url = method === 'GET' && params ? buildUrl(path, params) : buildUrl(path);
    const opts: RequestInit = {
      method,
      headers: {'Content-Type': 'application/json'},
      credentials: 'include',
    };
    if (body && method !== 'GET') {
      opts.body = JSON.stringify(body);
    }
    if (method === 'GET' && params) {
      // params already encoded in URL
    }
    const res = await fetch(url, opts);
    return await res.json();
  } catch (e: any) {
    return {success: false, error: e.message || 'Network error'};
  }
}

export const apiClient = {
  get: <T = any>(path: string, params?: Record<string, any>) => request<T>('GET', path, undefined, params),
  post: <T = any>(path: string, body?: any) => request<T>('POST', path, body),
  put: <T = any>(path: string, body?: any) => request<T>('PUT', path, body),
  delete: <T = any>(path: string) => request<T>('DELETE', path),
};
