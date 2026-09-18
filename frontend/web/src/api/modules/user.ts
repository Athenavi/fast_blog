/** 用户管理接口（/api/v3/system/user） */

import http from '../request'
import type {PageQuery, PageResult} from '../types'

export interface UserItem {
  id: number
  username: string
  email?: string | null
  is_active: boolean
  is_staff: boolean
  is_superuser: boolean
  vip_level: number
  vip_expires_at?: string | null
  locale?: string | null
  profile_picture?: string | null
  bio?: string | null
  date_joined?: string | null
  last_login_at?: string | null
}

export interface UserQuery extends PageQuery {
  is_active?: boolean
  is_superuser?: boolean
}

export interface UserCreatePayload {
  username: string
  email: string
  password: string
  is_active?: boolean
  is_staff?: boolean
  is_superuser?: boolean
  role_ids?: number[]
}

export interface UserUpdatePayload {
  email?: string
  password?: string
  is_active?: boolean
  is_staff?: boolean
  locale?: string
  profile_picture?: string
  bio?: string
  vip_level?: number
}

export interface RoleBrief {
  id: number
  name: string
  slug: string
}

export const userApi = {
  list: (params: UserQuery): Promise<PageResult<UserItem>> => http.page<UserItem>('/system/user', params),
  detail: (id: number) => http.get<UserItem>(`/system/user/${id}`),
  create: (data: UserCreatePayload) => http.post<UserItem>('/system/user', data),
  update: (id: number, data: UserUpdatePayload) => http.put<UserItem>(`/system/user/${id}`, data),
  /** 默认停用；force=true 才物理删除 */
  remove: (id: number, force = false) => http.delete<null>(`/system/user/${id}`, {force}),
  setStatus: (id: number, is_active: boolean) =>
    http.post<UserItem>(`/system/user/${id}/status`, {is_active}),
  roles: (id: number) => http.get<RoleBrief[]>(`/system/user/${id}/roles`),
  setRoles: (id: number, role_ids: number[]) =>
    http.post<RoleBrief[]>(`/system/user/${id}/roles`, {role_ids}),
  permissions: (id: number) => http.get<string[]>(`/system/user/${id}/permissions`),
}
