// Base API client for Next.js frontend
import type {ApiResponse} from '@/lib/api/base-types';

const API_BASE_URL = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000';
const API_PREFIX = '/api/v1';

// 从cookie中获取token
const getTokenFromCookie = (): string | null => {
    if (typeof document === 'undefined') return null;

    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'access_token') {
            return decodeURIComponent(value);
        }
    }
    return null;
};

// 统一的请求头配置
const getDefaultHeaders = (isFormData: boolean = false): Record<string, string> => {
    const headers: Record<string, string> = {};
    
    // 只有非 FormData 请求才设置 Content-Type
    if (!isFormData) {
        headers['Content-Type'] = 'application/json';
    }

    // 优先从cookie获取，然后从localStorage获取
    let token = getTokenFromCookie();
    if (!token && typeof window !== 'undefined') {
        token = localStorage.getItem('access_token');
    }

    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    return headers;
};

// 统一的错误处理
const handleError = (path: string, error: unknown): ApiResponse<never> => {
    console.error(`API请求失败: ${path}`, error);
    return {
        success: false,
        error: error instanceof Error ? error.message : String(error)
    };
};

// 核心请求方法
const request = async <T>(
    path: string,
    options: RequestInit = {}
): Promise<ApiResponse<T>> => {
    const fullPath = path.startsWith(API_PREFIX) ? path : `${API_PREFIX}${path}`;
    const fullUrl = `${API_BASE_URL}${fullPath}`;

    try {
        // 检测是否为 FormData 请求
        const isFormData = options.body instanceof FormData;
        
        const response = await fetch(fullUrl, {
            ...options,
            headers: {...getDefaultHeaders(isFormData), ...options.headers},
            credentials: 'include',
        });

        const data = await response.json();

        if (!response.ok) {
            const isAuthError = response.status === 401 || data.requires_auth === true;

            if (isAuthError && typeof window !== 'undefined') {
                localStorage.setItem('redirect_after_login', window.location.pathname);
            }

            const errorResponse: ApiResponse<never> = {
                success: false,
                error: data.error || data.message || `HTTP Error: ${response.status}`,
                data: data.data,
                requires_auth: isAuthError
            };

            return errorResponse;
        }

        return {...data, success: data.success ?? true} as ApiResponse<T>;
    } catch (error) {
        return handleError(fullUrl, error);
    }
};

// 简化的 API 客户端
export const apiClient = {
    get: <T>(path: string, params?: Record<string, unknown>): Promise<ApiResponse<T>> => {
        let fullPath = path.startsWith(API_PREFIX) ? path : `${API_PREFIX}${path}`;
        const fullUrl = `${API_BASE_URL}${fullPath}`;

        if (params) {
            const searchParams = new URLSearchParams();
            Object.entries(params).forEach(([key, value]) => {
                if (value != null) {
                    searchParams.append(key, String(value));
                }
            });
            const queryString = searchParams.toString();
            if (queryString) fullPath += `?${queryString}`;
        }

        return request<T>(fullPath, {method: 'GET'});
    },

    post: <T>(path: string, data?: unknown): Promise<ApiResponse<T>> =>
        request<T>(path, {
            method: 'POST',
            body: data ? JSON.stringify(data) : undefined
        }),

    put: <T>(path: string, data?: unknown): Promise<ApiResponse<T>> =>
        request<T>(path, {
            method: 'PUT',
            body: data ? JSON.stringify(data) : undefined
        }),

    patch: <T>(path: string, data?: unknown): Promise<ApiResponse<T>> =>
        request<T>(path, {
            method: 'PATCH',
            body: data ? JSON.stringify(data) : undefined
        }),

    delete: <T>(path: string): Promise<ApiResponse<T>> =>
        request<T>(path, {method: 'DELETE'}),

    request: <T>(path: string, options: RequestInit = {}): Promise<ApiResponse<T>> =>
        request<T>(path, options)
};