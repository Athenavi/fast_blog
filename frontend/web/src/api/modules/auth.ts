/** 认证相关接口（/api/v3/system/auth） */

import http from '../request'

export interface LoginParams {
  username?: string
  email?: string
  password: string
  remember_me?: boolean
}

export interface TokenData {
  access_token?: string
  refresh_token?: string
  token_type?: string
  expires_in?: number
  email_verified?: boolean
  requires_2fa?: boolean
  temp_token?: string
  message?: string
}

export interface CurrentUser {
  id: number
  username: string
  email?: string | null
  is_active: boolean
  is_staff: boolean
  is_superuser: boolean
  vip_level: number
  locale?: string | null
  profile_picture?: string | null
  /** 角色 slug 列表 */
  roles: string[]
  /** 权限码（resource:action），前端 v-auth 与菜单过滤都基于它 */
  permissions: string[]
}

export const authApi = {
  login: (data: LoginParams) => http.post<TokenData>('/system/auth/login', data),
  logout: () => http.post<null>('/system/auth/logout'),
  refresh: (refresh_token?: string) =>
    http.post<TokenData>('/system/auth/refresh', {refresh_token}),
  me: () => http.get<CurrentUser>('/system/auth/me'),
  status: () => http.get<{ logged_in: boolean; user_id?: number }>('/system/auth/status'),
}
