/**
 * V3 管理端 API 服务层
 *
 * 组件只调用此服务的方法 — 不关心是 V3 还是 V2。
 * 降级由 admin-api-client.ts 自动处理。
 *
 * V3 路径前缀: /api/v3/admin
 * V2 回退路径: 参照 api-paths.ts
 */
import {adminApi} from '@/lib/api/admin-api-client';
import type {ApiResponse} from '@/lib/api/base-types';

// ================================================================
// 用户管理
// ================================================================

export const adminUserService = {
  list: (params?: {page?: number; per_page?: number; search?: string}) =>
    adminApi.get('/api/v3/admin/users', '/users/', params),

  detail: (id: number) =>
    adminApi.get(`/api/v3/admin/users/${id}`, `/users/${id}`),

  create: (data: {username: string; email: string; password: string; is_active?: boolean}) =>
    adminApi.post('/api/v3/admin/users', '/users/', data),

  update: (id: number, data: {username?: string; email?: string; is_active?: boolean}) =>
    adminApi.put(`/api/v3/admin/users/${id}`, `/users/${id}`, data),

  delete: (id: number) =>
    adminApi.delete(`/api/v3/admin/users/${id}`, `/users/${id}`),

  assignRoles: (userId: number, roleIds: number[]) =>
    adminApi.post(`/api/v3/admin/users/${userId}/roles`, `/security/rbac/users/${userId}/roles`, {role_ids: roleIds}),
};

// ================================================================
// 文章管理
// ================================================================

export const adminArticleService = {
  list: (params?: {page?: number; per_page?: number; category_id?: number; status?: number}) =>
    adminApi.get('/api/v3/admin/articles', '/articles', params),

  detail: (id: number) =>
    adminApi.get(`/api/v3/admin/articles/${id}`, `/articles/${id}`),

  create: (data: {
    title: string; content?: string; excerpt?: string;
    category_id?: number; cover_image?: string; status?: number;
  }) =>
    adminApi.post('/api/v3/admin/articles', '/articles', data),

  update: (id: number, data: {
    title?: string; content?: string; excerpt?: string;
    category_id?: number; cover_image?: string;
  }) =>
    adminApi.put(`/api/v3/admin/articles/${id}`, `/articles/${id}`, data),

  delete: (id: number) =>
    adminApi.delete(`/api/v3/admin/articles/${id}`, `/articles/${id}`),

  publish: (id: number) =>
    adminApi.post(`/api/v3/admin/articles/${id}/publish`, `/articles/${id}`),
};

// ================================================================
// 媒体管理
// ================================================================

export const adminMediaService = {
  list: (params?: {page?: number; per_page?: number; type?: string}) =>
    adminApi.get('/api/v3/admin/media', '/media/files', params),

  upload: (file: File, folder_id?: number) => {
    const formData = new FormData();
    formData.append('file', file);
    if (folder_id !== undefined) formData.append('folder_id', String(folder_id));
    // FormData: adminApi 的特殊处理在 requestWithFallback 中传递 FormData
    return adminApi.post('/api/v3/admin/media/upload', '/media/upload', formData);
  },

  delete: (id: number) =>
    adminApi.delete(`/api/v3/admin/media/${id}`, `/media/?file-id-list=${id}`),
};

// ================================================================
// 系统设置
// ================================================================

export const adminSystemService = {
  getSettings: () =>
    adminApi.get('/api/v3/admin/settings', '/system/settings/'),

  updateSettings: (settings: Record<string, string>) =>
    adminApi.put('/api/v3/admin/settings', '/system/settings/', settings),

  createBackup: () =>
    adminApi.post('/api/v3/admin/backup', '/backup/full'),

  restoreBackup: (filename: string) =>
    adminApi.post('/api/v3/admin/backup/restore', '/backup/database', {filename}),
};

// ================================================================
// 角色权限管理
// ================================================================

export const adminRoleService = {
  listRoles: (includeSystem = true) =>
    adminApi.get('/api/v3/admin/roles', '/security/rbac/roles', {include_system: includeSystem}),

  createRole: (data: {name: string; slug: string; description?: string; permission_codes?: string[]}) =>
    adminApi.post('/api/v3/admin/roles', '/security/rbac/roles', data),

  updateRolePermissions: (roleId: number, permissionCodes: string[]) =>
    adminApi.put(`/api/v3/admin/roles/${roleId}/permissions`, `/security/rbac/roles/${roleId}/permissions`, {permission_codes: permissionCodes}),

  deleteRole: (roleId: number) =>
    adminApi.delete(`/api/v3/admin/roles/${roleId}`, `/security/rbac/roles/${roleId}`),

  listPermissions: (resourceType?: string) =>
    adminApi.get('/api/v3/admin/permissions', '/security/rbac/permissions', {resource_type: resourceType}),
};

// ================================================================
// 统一导出
// ================================================================

export const adminService = {
  users: adminUserService,
  articles: adminArticleService,
  media: adminMediaService,
  system: adminSystemService,
  roles: adminRoleService,
};
