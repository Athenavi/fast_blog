/**
 * 认证工具函数
 */

/**
 * 通用 cookie 读取
 */
export function getCookie(name: string): string | null {
    if (typeof document === 'undefined') return null;
    for (const c of document.cookie.split(';')) {
        const eqIdx = c.trim().indexOf('=');
        if (eqIdx === -1) continue;
        const n = c.trim().substring(0, eqIdx).trim();
        if (n === name) {
            const v = c.trim().substring(eqIdx + 1);
            return v ? decodeURIComponent(v) : null;
        }
    }
    return null;
}

/**
 * 通用 cookie 写入
 */
export function setCookie(name: string, value: string, maxAgeSec: number): void {
    if (typeof document === 'undefined') return;
    document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAgeSec}; SameSite=Lax`;
}

/**
 * 从 cookie 获取 access_token
 */
export function getAccessTokenFromCookie(): string | null {
    if (typeof document === 'undefined') return null;
    return getCookie('access_token');
}

/**
 * 从 cookie 获取 refresh_token
 */
export function getRefreshTokenFromCookie(): string | null {
    if (typeof document === 'undefined') return null;
    return getCookie('refresh_token');
}

/**
 * 清除认证 cookie
 */
export function clearAuthCookies(): void {
    if (typeof document === 'undefined') return;
    document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/';
    document.cookie = 'refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/';
}

/**
 * 检查用户是否已登录
 */
export function isLoggedIn(): boolean {
    return getAccessTokenFromCookie() !== null;
}

/**
 * 保存 token 到 cookie
 */
export function saveTokens(accessToken: string, refreshToken?: string): void {
    if (typeof window === 'undefined') return;

    const expirationDate = new Date();
    expirationDate.setTime(expirationDate.getTime() + (60 * 60 * 1000));
    document.cookie = `access_token=${encodeURIComponent(accessToken)}; expires=${expirationDate.toUTCString()}; path=/; SameSite=Lax;`;

    if (refreshToken) {
        const refreshExpirationDate = new Date();
        refreshExpirationDate.setTime(refreshExpirationDate.getTime() + (7 * 24 * 60 * 60 * 1000));
        document.cookie = `refresh_token=${encodeURIComponent(refreshToken)}; expires=${refreshExpirationDate.toUTCString()}; path=/; SameSite=Lax;`;
    }
}

/**
 * 认证状态存储键
 */
const AUTH_STATE_KEY = 'fastblog_auth';

/**
 * 广播登录状态事件 — 确保 Navbar 等组件同步
 */
export function dispatchAuthEvent(loggedIn: boolean): void {
    if (typeof window === 'undefined') return;
    if (loggedIn) {
        localStorage.setItem(AUTH_STATE_KEY, '1');
    } else {
        localStorage.removeItem(AUTH_STATE_KEY);
    }
    // 使用自定义事件同步同一页面内多个 React 岛
    window.dispatchEvent(new CustomEvent('auth:changed', { detail: { loggedIn } }));
}

/**
 * 获取本地持久化的登录状态
 */
export function getLocalAuthState(): boolean {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem(AUTH_STATE_KEY) === '1';
}

/**
 * 清除本地登录状态
 */
export function clearLocalAuthState(): void {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(AUTH_STATE_KEY);
}
