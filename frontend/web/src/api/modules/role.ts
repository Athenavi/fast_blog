/** 角色管理接口（/api/v3/system/role） */

import http from '../request'
import type {PageQuery, PageResult} from '../types'

export interface RoleItem {
  id: number
  name: string
  slug: string
  description?: string | null
  is_system: boolean
  is_active: boolean
  parent_id?: number | null
  /** 数据范围（1 仅本人 / 2 本组及以下 / 3 全部 / 5 自定义组） */
  data_scope?: number | null
  created_at?: string | null
  permission_count: number
  user_count: number
}

export interface RoleQuery extends PageQuery {
  is_system?: boolean
  is_active?: boolean
}

export interface RoleCreatePayload {
  name: string
  slug: string
  description?: string
  parent_id?: number | null
  permission_codes?: string[]
}

export interface RoleUpdatePayload {
  name?: string
  description?: string
  parent_id?: number | null
  is_active?: boolean
}

export const roleApi = {
  list: (params: RoleQuery): Promise<PageResult<RoleItem>> => http.page<RoleItem>('/system/role', params),
  detail: (id: number) => http.get<RoleItem>(`/system/role/${id}`),
  create: (data: RoleCreatePayload) => http.post<RoleItem>('/system/role', data),
  update: (id: number, data: RoleUpdatePayload) => http.put<RoleItem>(`/system/role/${id}`, data),
  remove: (id: number) => http.delete<null>(`/system/role/${id}`),
  permissions: (id: number) => http.get<string[]>(`/system/role/${id}/permissions`),
  setPermissions: (id: number, permission_codes: string[]) =>
    http.put<string[]>(`/system/role/${id}/permissions`, {permission_codes}),
}
