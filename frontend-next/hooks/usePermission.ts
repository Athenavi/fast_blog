/**
 * 权限检查 Hook - 用于前端权限验证
 *
 * @example
 * ```tsx
 * // 基础用法
 * const { hasPermission, hasRole } = usePermission();
 *
 * if (hasPermission('article.create')) {
 *   return <Button>新建文章</Button>;
 * }
 *
 * // 角色检查
 * if (hasRole('editor')) {
 *   return <EditorPanel />;
 * }
 *
 * // 组合使用
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
 * 权限检查 Hook
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
            const response = await apiClient.get(`/api/v1/permissions/users/${user.id}/permissions`);

            if (response.success && (response.data as any)) {
                const data = response.data as any;
                const permissions = data.permissions || [];
                setUserPermissions(permissions.map((p: any) => p.code || p));

                // 获取用户角色
                const userWithRole = user as any; // 临时类型断言
                if (userWithRole.role_id) {
                    const roleResponse = await apiClient.get(`/api/v1/admin/user/${user.id}/roles`);
                    if (roleResponse.success && (roleResponse.data as any)) {
                        const roleData = roleResponse.data as any;
                        if (roleData.roles?.length > 0) {
                            setUserRole(roleData.roles[0].slug);
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Failed to load user permissions:', error);
        } finally {
            setIsLoading(false);
        }
    };

    /**
     * 检查是否有指定权限
     */
    const hasPermission = (permissionCode: string): boolean => {
        // 超级管理员拥有所有权限
        if (user?.is_superuser) {
            return true;
        }

        return userPermissions.includes(permissionCode);
    };

    /**
     * 检查是否有任一权限
     */
    const hasAnyPermission = (permissionCodes: string[]): boolean => {
        if (user?.is_superuser) {
            return true;
        }

        return permissionCodes.some(code => userPermissions.includes(code));
    };

    /**
     * 检查是否有所有权限
     */
    const hasAllPermissions = (permissionCodes: string[]): boolean => {
        if (user?.is_superuser) {
            return true;
        }

        return permissionCodes.every(code => userPermissions.includes(code));
    };

    /**
     * 检查是否有指定角色
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
};
