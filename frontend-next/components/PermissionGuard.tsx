/**
 * 权限保护组件 - 基于权限控制内容显示
 */

'use client';

import React from 'react';
import {usePermission} from '@/hooks/usePermission';
import LoadingState from '@/components/LoadingState';

interface PermissionGuardProps {
    /** 需要的权限代码 */
    permission?: string;
    /** 需要的任一权限（满足一个即可） */
    anyPermissions?: string[];
    /** 需要的全部权限（必须全部满足） */
    allPermissions?: string[];
    /** 需要的角色 */
    role?: string;
    /** 是否需要管理员权限 */
    requireAdmin?: boolean;
    /** 无权限时显示的内容 */
    fallback?: React.ReactNode;
    /** 加载中显示的内容 */
    loadingFallback?: React.ReactNode;
    /** 子组件 */
    children: React.ReactNode;
}

/**
 * 权限守卫组件
 *
 * @example
 * // 单个权限
 * <PermissionGuard permission="article.create">
 *   <Button>新建文章</Button>
 * </PermissionGuard>
 *
 * // 任一权限
 * <PermissionGuard anyPermissions={['article.edit', 'article.delete']}>
 *   <Button>管理文章</Button>
 * </PermissionGuard>
 *
 * // 角色检查
 * <PermissionGuard role="editor">
 *   <EditorPanel />
 * </PermissionGuard>
 *
 * // 管理员检查
 * <PermissionGuard requireAdmin>
 *   <AdminSettings />
 * </PermissionGuard>
 */
const PermissionGuard: React.FC<PermissionGuardProps> = ({
                                                             permission,
                                                             anyPermissions,
                                                             allPermissions,
                                                             role,
                                                             requireAdmin = false,
                                                             fallback = null,
                                                             loadingFallback = <LoadingState
                                                                 message="正在检查权限..."/>,
                                                             children
                                                         }) => {
    const {
        hasPermission,
        hasAnyPermission,
        hasAllPermissions,
        hasRole,
        isAdmin,
        isLoading
    } = usePermission();

    if (isLoading) {
        return <>{loadingFallback}</>;
    }

    // 检查权限
    let authorized = true;

    if (requireAdmin && !isAdmin) {
        authorized = false;
    }

    if (permission && !hasPermission(permission)) {
        authorized = false;
    }

    if (anyPermissions && !hasAnyPermission(anyPermissions)) {
        authorized = false;
    }

    if (allPermissions && !hasAllPermissions(allPermissions)) {
        authorized = false;
    }

    if (role && !hasRole(role)) {
        authorized = false;
    }

    if (!authorized) {
        return <>{fallback}</>;
    }

    return <>{children}</>;
};

export default PermissionGuard;
