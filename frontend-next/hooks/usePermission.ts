/**
 * 鏉冮檺妫€鏌?Hook - 鐢ㄤ簬鍓嶇�鏉冮檺楠岃瘉
 *
 * @example
 * ```tsx
 * // 鍩虹�鐢ㄦ硶
 * const { hasPermission, hasRole } = usePermission();
 *
 * if (hasPermission('article.create')) {
 *   return <Button>鏂板缓鏂囩珷</Button>;
 * }
 *
 * // 瑙掕壊妫€鏌? * if (hasRole('editor')) {
 *   return <EditorPanel />;
 * }
 *
 * // 缁勫悎浣跨敤
 * if (hasAnyPermission(['article.edit', 'article.delete'])) {
 *   return <ManageArticles />;
 * }
 * ```
 */

import {useEffect, useState} from 'react';
import {useAuth} from './useAuth';
import apiClient from '@/lib/api-client';

interface UsePermissionReturn {
    hasPermission: (permissionCode: string) => boolean;
    hasAnyPermission: (permissionCodes: string[]) => boolean;
    hasAllPermissions: (permissionCodes: string[]) => boolean;
    hasRole: (roleSlug: string) => boolean;
    isAdmin: boolean;
    isLoading: boolean;
    userPermissions: string[];
    userRole: string | null;
}

/**
 * 鏉冮檺妫€鏌?Hook
 *
 * @example
 * const { hasPermission, hasRole } = usePermission();
 * if (hasPermission('article.create')) { ... }
 * if (hasRole('editor')) { ... }
 */
export const usePermission = (): UsePermissionReturn => {
    const {user, loading: authLoading} = useAuth();
    const [userPermissions, setUserPermissions] = useState<string[]>([]);
    const [userRole, setUserRole] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        loadUserPermissions();
    }, [user]);

    const loadUserPermissions = async () => {
        if (!user) {
            setUserPermissions([]);
            setUserRole(null);
            setIsLoading(false);
            return;
        }

        try {
            // 获取用户角色和权限
            const response = await apiClient.get(`/security/rbac/users/${user.id}/permissions`);

            if (response.success && (response.data as any)) {
                const data = response.data as any;
                const permissions = data.permissions || [];
                setUserPermissions(permissions.map((p: any) => p.code || p));

                // 获取用户角色（后端没有直接GET接口，从用户对象中获取）
                const userWithRole = user as any;
                if (userWithRole.role) {
                    setUserRole(userWithRole.role);
                }
            }
        } catch (error) {
            console.error('Failed to load user permissions:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const hasPermission = (permissionCode: string): boolean => {
        if (user?.is_superuser) {
            return true;
        }

        return userPermissions.includes(permissionCode);
    };

    /**
     * 妫€鏌ユ槸鍚︽湁浠讳竴鏉冮檺
     */
    const hasAnyPermission = (permissionCodes: string[]): boolean => {
        if (user?.is_superuser) {
            return true;
        }

        return permissionCodes.some(code => userPermissions.includes(code));
    };

    /**
     * 妫€鏌ユ槸鍚︽湁鎵€鏈夋潈闄?     */
    const hasAllPermissions = (permissionCodes: string[]): boolean => {
        if (user?.is_superuser) {
            return true;
        }

        return permissionCodes.every(code => userPermissions.includes(code));
    };

    /**
     * 妫€鏌ユ槸鍚︽湁鎸囧畾瑙掕壊
     */
    const hasRole = (roleSlug: string): boolean => {
        if (user?.is_superuser) {
            return true;
        }

        return userRole === roleSlug;
    };

    return {
        hasPermission,
        hasAnyPermission,
        hasAllPermissions,
        hasRole,
        isAdmin: user?.is_superuser || false,
        isLoading: authLoading || isLoading,
        userPermissions,
        userRole
    };
}
