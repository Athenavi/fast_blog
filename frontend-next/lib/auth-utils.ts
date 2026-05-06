/**
 * 认证工具函数
 * 统一从 cookie 获取 token，不使用 localStorage
 */

/**
 * 从 cookie 获取 access_token
 */
export function getAccessTokenFromCookie(): string | null {
    if (typeof document === 'undefined') return null;

    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'access_token' && value) {
            return decodeURIComponent(value);
        }
    }
    return null;
}

/**
 * 从 cookie 获取 refresh_token
 */
export function getRefreshTokenFromCookie(): string | null {
    if (typeof document === 'undefined') return null;

    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'refresh_token' && value) {
            return decodeURIComponent(value);
        }
    }
    return null;
}

/**
 * 清除认证 cookie
 */
export function clearAuthCookies(): void {
    if (typeof window === 'undefined') return;

    // 清除 access_token
    document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';

    // 清除 refresh_token
    document.cookie = 'refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
}

/**
 * 检查用户是否已认证
 */
export function isAuthenticated(): boolean {
    return getAccessTokenFromCookie() !== null;
}
