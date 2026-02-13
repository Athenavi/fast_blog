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
    description: string;
    role_count?: number;
}

// Role management service
export class RoleManagementService {
    static async getRoles(): Promise<ApiResponse<UserRole[]>> {
        return apiClient.get('/role-management/roles');
    }

    static async assignRolesToUser(userId: number, roleIds: number[]): Promise<ApiResponse<{ message: string }>> {
        return apiClient.put(`/admin/user/${userId}/roles`, {role_ids: roleIds});
    }

    static async getRolePermissionStats(): Promise<ApiResponse<Stats>> {
        return apiClient.get('/role-management/permission-stats');
    }

    static async getPermissions(): Promise<ApiResponse<Permission[]>> {
        return apiClient.get('/role-management/permissions');
    }

    static async createPermission(param: { code: string; description: string }) {
        return apiClient.post('/role-management/permissions', param)
    }

    static async deleteRole(roleId: number) {
        return apiClient.delete(`/role-management/roles/${roleId}`)
    }

    static async deletePermission(permissionId: number) {
        return apiClient.delete(`/role-management/permissions/${permissionId}`)
    }

    static async updateRole(id: number, param2: { name: string; description: string; permission_ids: number[] }) {
        return apiClient.put(`/role-management/roles/${id}`, param2)
    }

    // 添加缺失的createRole方法
    static async createRole(param: { name: string; description: string; permission_ids: number[] }) {
        return apiClient.post('/role-management/roles', param);
    }

    // 添加缺失的updatePermission方法
    static async updatePermission(id: number, param: { code: string; description: string }) {
        return apiClient.put(`/role-management/permissions/${id}`, param);
    }
}