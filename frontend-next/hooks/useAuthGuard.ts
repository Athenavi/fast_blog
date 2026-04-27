import {useEffect, useRef, useState} from 'react';
import {useRouter} from 'next/navigation';
import {useAuth} from '@/hooks/useAuth';

interface UseAuthGuardOptions {
    redirectTo?: string;
    redirectIfUnauthenticated?: boolean;
    saveRedirectPath?: boolean;
}

interface AuthUser {
    id: number;
    username: string;
    email: string;
    avatar?: string;
    is_active: boolean;
    is_superuser: boolean;
    created_at: string;
    last_login?: string;
}

interface UseAuthGuardReturn {
    isAuthenticated: boolean;
    isLoading: boolean;
    user: AuthUser | null;
    requireAuth: () => void;
}

/**
 * 认证守卫 Hook
 * 统一处理页面级别的认证检查和重定向逻辑
 */
export const useAuthGuard = (options: UseAuthGuardOptions = {}): UseAuthGuardReturn => {
    const {
        redirectTo = '/login',
        redirectIfUnauthenticated = true,
        saveRedirectPath = true
    } = options;

    const router = useRouter();
    const {user, loading: authLoading} = useAuth();
    const [checked, setChecked] = useState(false);
    const checkedRef = useRef(false);

    const isAuthenticated = !!user && !authLoading;
    const isLoading = authLoading || !checked;

    // 检查认证状态并处理重定向
    useEffect(() => {
        if (!authLoading && checked) {
            if (!isAuthenticated && redirectIfUnauthenticated) {
                // 保存当前路径用于登录后重定向
                if (saveRedirectPath && typeof window !== 'undefined') {
                    const currentPath = window.location.pathname + window.location.search;
                    localStorage.setItem('redirect_after_login', currentPath);
                }

                // 执行重定向
                window.location.href = redirectTo;
            }
        }
    }, [isAuthenticated, authLoading, checked, redirectIfUnauthenticated, redirectTo, router, saveRedirectPath]);

    // 初始化检查完成标记
    useEffect(() => {
        if (!authLoading && !checkedRef.current) {
            checkedRef.current = true;
            // 使用 setTimeout 避免在 effect 中同步设置状态
            setTimeout(() => {
                if (checkedRef.current) {
                    setChecked(true);
                }
            }, 0);
        }
    }, [authLoading]);

    /**
     * 手动触发认证检查
     */
    const requireAuth = () => {
        if (!isAuthenticated && redirectIfUnauthenticated) {
            if (saveRedirectPath && typeof window !== 'undefined') {
                const currentPath = window.location.pathname + window.location.search;
                localStorage.setItem('redirect_after_login', currentPath);
            }
            window.location.href = redirectTo;
        }
    };

    return {
        isAuthenticated,
        isLoading,
        user,
        requireAuth
    };
};