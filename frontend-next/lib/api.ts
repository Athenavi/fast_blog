/**
 * API 请求工具函数
 *
 * 用于拼接完整的后端API地址
 */

// 后端API基础URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:9421';

/**
 * 获取完整的API URL
 * @param path - API路径（例如：'/api/v1/collaboration/invites/create'）
 * @returns 完整的API URL
 */
export function getApiUrl(path: string): string {
    // 确保路径以 / 开头
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    return `${API_BASE_URL}${normalizedPath}`;
}

/**
 * 执行API请求
 * @param path - API路径
 * @param options - fetch选项
 * @returns fetch响应
 */
export async function apiFetch(path: string, options?: RequestInit): Promise<Response> {
    const url = getApiUrl(path);
    console.log('API Request:', url, options?.method || 'GET');

    return fetch(url, {
        ...options,
        credentials: 'include', // 携带cookie
        headers: {
            'Content-Type': 'application/json',
            ...options?.headers,
        },
    });
}

/**
 * 执行API请求并解析JSON
 * @param path - API路径
 * @param options - fetch选项
 * @returns 解析后的数据
 */
export async function apiRequest<T = any>(path: string, options?: RequestInit): Promise<T> {
    const response = await apiFetch(path, options);

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `API request failed: ${response.status}`);
    }

    return response.json();
}
