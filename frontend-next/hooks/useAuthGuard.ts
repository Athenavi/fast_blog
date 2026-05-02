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

    // 检查认证状态并处理重定向（合并两个 useEffect，避免相互触发）
    useEffect(() => {
        if (authLoading) return;

        // 首次检查完成
        if (!checkedRef.current) {
            checkedRef.current = true;
            setChecked(true);
            return;
        }

        // 已检查完毕，处理重定向
        if (checked && !isAuthenticated && redirectIfUnauthenticated) {
            if (saveRedirectPath && typeof window !== 'undefined') {
                const currentPath = window.location.pathname + window.location.search;
                const nextParam = encodeURIComponent(currentPath);
                window.location.href = `${redirectTo}?next=${nextParam}`;
            } else {
                window.location.href = redirectTo;
            }
        }
    }, [authLoading, checked, isAuthenticated, redirectIfUnauthenticated, redirectTo, saveRedirectPath]);

    /**
     * 手动触发认证检查
     */
    const requireAuth = () => {
        if (!isAuthenticated && redirectIfUnauthenticated) {
            if (saveRedirectPath && typeof window !== 'undefined') {
                const currentPath = window.location.pathname + window.location.search;
                const nextParam = encodeURIComponent(currentPath);
                window.location.href = `${redirectTo}?next=${nextParam}`;
            } else {
                window.location.href = redirectTo;
            }
        }
    };

    return {
        isAuthenticated,
        isLoading,
        user,
        requireAuth
    };
};