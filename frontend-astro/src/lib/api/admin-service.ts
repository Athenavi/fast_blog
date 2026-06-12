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
// 仪表盘
// ================================================================

export const adminDashboardService = {
  stats: () =>
    adminApi.get('/api/v3/admin/dashboard/stats', '/dashboard/stats'),

  recentArticles: (limit = 10) =>
    adminApi.get('/api/v3/admin/dashboard/recent-articles', '/dashboard/recent-articles', {limit}),

  traffic: () =>
    adminApi.get('/api/v3/admin/dashboard/traffic', '/dashboard/traffic'),
};

// ================================================================
// 评论管理
// ================================================================

export const adminCommentService = {
  pending: () =>
    adminApi.get('/api/v3/admin/comments/pending', '/comments/pending'),

  approve: (id: number) =>
    adminApi.post(`/api/v3/admin/comments/${id}/approve`, `/comments/${id}/approve`),

  reject: (id: number) =>
    adminApi.post(`/api/v3/admin/comments/${id}/reject`, `/comments/${id}/reject`),

  delete: (id: number) =>
    adminApi.delete(`/api/v3/admin/comments/${id}`, `/comments/${id}`),
};

// ================================================================
// 插件管理
// ================================================================

export const adminPluginService = {
  list: () =>
    adminApi.get('/api/v3/admin/plugins', '/plugins/'),

  activate: (slug: string) =>
    adminApi.post(`/api/v3/admin/plugins/${slug}/activate`, `/plugins/${slug}/activate`),

  deactivate: (slug: string) =>
    adminApi.post(`/api/v3/admin/plugins/${slug}/deactivate`, `/plugins/${slug}/deactivate`),

  getSettings: (slug: string) =>
    adminApi.get(`/api/v3/admin/plugins/${slug}/settings`, `/plugins/${slug}/settings`),

  updateSettings: (slug: string, settings: Record<string, any>) =>
    adminApi.put(`/api/v3/admin/plugins/${slug}/settings`, `/plugins/${slug}/settings`, settings),

  uninstall: (slug: string) =>
    adminApi.delete(`/api/v3/admin/plugins/${slug}`, `/plugins/${slug}`),
};

// ================================================================
// 主题管理
// ================================================================

export const adminThemeService = {
  list: () =>
    adminApi.get('/api/v3/admin/themes', '/themes/installed'),

  activate: (slug: string) =>
    adminApi.post(`/api/v3/admin/themes/${slug}/activate`, `/themes/${slug}/activate`),

  getConfig: (slug: string) =>
    adminApi.get(`/api/v3/admin/themes/${slug}/config`, `/themes/${slug}/config`),

  updateConfig: (slug: string, config: Record<string, any>) =>
    adminApi.put(`/api/v3/admin/themes/${slug}/config`, `/themes/${slug}/config`, config),

  uninstall: (slug: string) =>
    adminApi.delete(`/api/v3/admin/themes/${slug}`, `/themes/${slug}`),
};

// ================================================================
// SEO 管理
// ================================================================

export const adminSeoService = {
  dashboard: () =>
    adminApi.get('/api/v3/admin/seo/dashboard', '/seo/dashboard'),

  keywords: () =>
    adminApi.get('/api/v3/admin/seo/keywords', '/seo/top-keywords'),

  orphanArticles: () =>
    adminApi.get('/api/v3/admin/seo/orphan-articles', '/seo/orphan-articles'),
};

// ================================================================
// 备份管理
// ================================================================

export const adminBackupService = {
  create: () =>
    adminApi.post('/api/v3/admin/backup', '/backup/full'),

  restore: (filename: string) =>
    adminApi.post('/api/v3/admin/backup/restore', '/backup/database', {filename}),

  delete: (id: string) =>
    adminApi.delete(`/api/v3/admin/backup/${id}`, `/backup/delete?filename=${id}`),
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
  dashboard: adminDashboardService,
  comments: adminCommentService,
  plugins: adminPluginService,
  themes: adminThemeService,
  seo: adminSeoService,
  backup: adminBackupService,
};
