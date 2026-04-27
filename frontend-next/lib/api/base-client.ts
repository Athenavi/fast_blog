// Base API client for Next.js frontend
import type {ApiResponse} from '@/lib/api/base-types';
import {getConfig} from '@/lib/config';

const API_PREFIX = getConfig().API_PREFIX;

// 从 cookie 中获取 token
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

// 保存 token 到 cookie
const saveTokens = (accessToken: string, refreshToken?: string) => {
    if (typeof window === 'undefined') return;

    // 只保存到 cookie，不再使用 localStorage
    const expirationDate = new Date();
    expirationDate.setTime(expirationDate.getTime() + (60 * 60 * 1000)); // 1 小时后过期
    document.cookie = `access_token=${accessToken}; expires=${expirationDate.toUTCString()}; path=/; SameSite=Lax;`;

    // Refresh token 也保存到 cookie（如果需要）
    if (refreshToken) {
        const refreshExpirationDate = new Date();
        refreshExpirationDate.setTime(refreshExpirationDate.getTime() + (7 * 24 * 60 * 60 * 1000)); // 7 天后过期
        document.cookie = `refresh_token=${refreshToken}; expires=${refreshExpirationDate.toUTCString()}; path=/; SameSite=Lax;`;
    }
};

// 清除过期的 token
const clearTokens = () => {
    if (typeof window === 'undefined') return;

    // 只清除 cookie，不再使用 localStorage
    document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/';
    document.cookie = 'refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/';
};

// 统一的请求头配置
const getDefaultHeaders = (isFormData: boolean = false): Record<string, string> => {
    const headers: Record<string, string> = {};

    // 只有非 FormData 请求才设置 Content-Type
    if (!isFormData) {
        headers['Content-Type'] = 'application/json';
    }

    // 只从 cookie 获取 token
    const token = getTokenFromCookie();

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

// 跟踪正在进行的 token 刷新请求，避免并发刷新
let refreshingTokenPromise: Promise<string | null> | null = null;

// 刷新 token 的函数
const refreshAccessToken = async (): Promise<string | null> => {
    // 从 cookie 获取 refresh_token
    const refreshToken = getTokenFromCookie();
    if (!refreshToken) {
        console.log('No refresh token available in cookie');
        return null;
    }

    // 如果已经有刷新请求在进行中，等待该请求完成
    if (refreshingTokenPromise) {
        console.log('Token refresh already in progress, waiting...');
        return refreshingTokenPromise;
    }

    // 创建新的刷新请求
    refreshingTokenPromise = (async () => {
        try {
            const config = getConfig();
            const response = await fetch(`${config.API_BASE_URL}${config.API_PREFIX}/auth/token/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({refresh: refreshToken}),
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success && data.data?.access_token) {
                    const newAccessToken = data.data.access_token;
                    const newRefreshToken = data.data.refresh_token || refreshToken;

                    // 保存新的 tokens
                    saveTokens(newAccessToken, newRefreshToken);
                    console.log('Token refreshed successfully');
                    return newAccessToken;
                }
            }

            console.log('Failed to refresh token:', response.status);
            // 如果刷新失败，清除所有 token
            clearTokens();
            return null;
        } catch (error) {
            console.error('Error refreshing token:', error);
            return null;
        } finally {
            // 清除刷新标志，允许下次刷新
            refreshingTokenPromise = null;
        }
    })();

    return refreshingTokenPromise;
};

// 核心请求方法
const request = async <T>(
    path: string,
    options: RequestInit = {}
): Promise<ApiResponse<T>> => {
    const config = getConfig();
    const fullPath = path.startsWith(config.API_PREFIX) ? path : `${config.API_PREFIX}${path}`;
    const fullUrl = `${config.API_BASE_URL}${fullPath}`;

    try {
        // 检测是否为 FormData 请求
        const isFormData = options.body instanceof FormData;

        // 先获取默认的 Authorization header
        const defaultHeaders = getDefaultHeaders(isFormData);

        // 合并 headers，确保 Authorization header 不会被覆盖
        const mergedHeaders = {
            ...defaultHeaders,
            ...(options.headers || {})
        };

        const response = await fetch(fullUrl, {
            ...options,
            headers: mergedHeaders,
            credentials: 'include'
            // 移除 redirect: 'manual'，让浏览器自动跟随重定向
        });

        // 检查响应头中是否有新的 token（后端中间件自动刷新）
        const newAccessToken = response.headers.get('X-New-Access-Token');
        const newRefreshToken = response.headers.get('X-New-Refresh-Token');
        const tokenRefreshed = response.headers.get('X-Token-Refreshed');
        
        if (tokenRefreshed === 'true' && newAccessToken) {
            console.log('Backend auto-refreshed token detected');
            // 保存新的 tokens（如果后端已经设置了 cookie，这里只是确保一致性）
            saveTokens(newAccessToken, newRefreshToken || undefined);
        }

        // 注意：不再需要手动处理重定向，因为移除了 redirect: 'manual'
        // 浏览器会自动跟随重定向

        // 尝试解析 JSON，但要处理可能的解析错误
        let data: any;
        try {
            data = await response.json();
        } catch (parseError) {
            // 如果响应不是 JSON（比如重定向或 HTML 页面），返回错误
            console.warn(`API 响应不是有效的 JSON: ${fullUrl}, status: ${response.status}`);
            return {
                success: false,
                error: `服务器返回了非 JSON 响应 (HTTP ${response.status})`,
                redirect_url: response.headers.get('Location') || undefined
            };
        }

        if (!response.ok) {
            const isAuthError = response.status === 401 || data.requires_auth === true;

            // 如果是认证错误，尝试刷新 token
            if (isAuthError && typeof window !== 'undefined') {
                console.log('Authentication error detected (status:', response.status, '), attempting to refresh token...');

                // 尝试刷新 token（有 refresh token 就会尝试）
                const newToken = await refreshAccessToken();

                if (newToken) {
                    console.log('Token refreshed successfully, retrying request...');
                    // 使用新 token 重试请求
                    const retryOptions = {
                        ...options,
                        headers: {
                            ...getDefaultHeaders(options.body instanceof FormData),
                            ...options.headers
                        }
                    };
                    return request<T>(path, retryOptions);
                } else {
                    console.log('Token refresh failed or no refresh token available, redirecting to login');
                    // 刷新失败或没有 refresh token，重定向到登录页
                    if (typeof window !== 'undefined') {
                        // 登录后跳转回当前页面
                        const redirectPath = window.location.pathname + window.location.search;
                        // 使用 setTimeout 确保在下一个事件循环中执行重定向
                        setTimeout(() => {
                            window.location.href = `/login?next=${encodeURIComponent(redirectPath)}`;
                        }, 0);
                    }
                    // 立即返回，不再继续处理错误响应
                    return {
                        success: false,
                        error: 'Authentication required',
                        requires_auth: true
                    };
                }
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
        // 构建带查询参数的路径
        let fullPath = path;
        
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

    // 专门用于表单提交的 post 方法（application/x-www-form-urlencoded）
    postForm: <T>(path: string, data?: Record<string, unknown>): Promise<ApiResponse<T>> => {
        const formData = new URLSearchParams();
        if (data) {
            Object.entries(data).forEach(([key, value]) => {
                if (value !== undefined && value !== null) {
                    formData.append(key, String(value));
                }
            });
        }

        return request<T>(path, {
            method: 'POST',
            body: formData.toString(),
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        });
    },

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