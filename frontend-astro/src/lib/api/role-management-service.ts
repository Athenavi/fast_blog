// Role management service for Next.js frontend
import {apiClient} from './base-client';
import type {ApiResponse, Stats, UserRole} from '@/lib/api/base-types';

// Role Management Types
export interface Role {
    id: number;
    name: string;
    description: string;
    permissions: Permission[];
    created_at?: string;
}

export interface Permission {
    id: number;
    code: string;
    name?: string;
    description: string;
    resource_type?: string;
    action?: string;
    is_active?: boolean;
    role_count?: number;
}

// Role management service
export class RoleManagementService {
    static async getRoles(): Promise<ApiResponse<UserRole[]>> {
        return apiClient.get('/security/rbac/roles');
    }

    static async assignRolesToUser(userId: number, roleIds: number[]): Promise<ApiResponse<{ message: string }>> {
        return apiClient.post(`/security/rbac/users/${userId}/roles`, {role_ids: roleIds});
    }

    static async getRolePermissionStats(): Promise<ApiResponse<Stats>> {
        // 后端没有直接的 permission-stats 端点，使用 roles 端点获取统计信息
        return apiClient.get('/security/rbac/roles');
    }

    static async getPermissions(): Promise<ApiResponse<Permission[]>> {
        return apiClient.get('/security/rbac/permissions');
    }

    static async deleteRole(roleId: number) {
        return apiClient.delete(`/security/rbac/roles/${roleId}`)
    }

    static async updateRole(id: number, param2: { name: string; description: string; permission_ids: number[] }) {
        // 后端使用 /security/rbac/roles/{role_id}/permissions 来更新角色权限
        return apiClient.put(`/security/rbac/roles/${id}/permissions`, {permission_ids: param2.permission_ids})
    }

    // 添加缺失的createRole方法
    static async createRole(param: { name: string; description: string; permission_ids: number[] }) {
        return apiClient.post('/security/rbac/roles', param);
    }

}