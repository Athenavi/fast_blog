/** 认证相关接口（/api/v3/system/auth） */

import http from '../request'

export interface LoginParams {
  username?: string
  email?: string
  password: string
  remember_me?: boolean
}

export interface Verify2FAParams {
  temp_token: string
  code: string
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
  /** 权限码（resource:action），前端 v-auth 与按钮级权限基于它 */
  permissions: string[]
  /**
   * 菜单授权标识（= 路由 name）。后端管授权、前端管结构：后端只下发"哪些菜单被授权"，
   * 菜单长什么样仍由前端 routes.ts 决定。已由后端补齐祖先目录。
   */
  menu_codes?: string[]
}

export const authApi = {
  login: (data: LoginParams) => http.post<TokenData>('/system/auth/login', data),
  /** 登录第二步：temp_token + TOTP/备用码换正式令牌 */
  verify2fa: (data: Verify2FAParams) =>
    http.post<TokenData>('/system/auth/verify-2fa', data),
  logout: () => http.post<null>('/system/auth/logout'),
  /** 重发邮箱验证邮件：匿名接口，无论邮箱是否存在都返回同一句话（防枚举） */
  sendEmailVerification: (email: string) =>
    http.post<null>('/system/auth/email/verify/send', {email}),
  refresh: (refresh_token?: string) =>
    http.post<TokenData>('/system/auth/refresh', {refresh_token}),
  me: () => http.get<CurrentUser>('/system/auth/me'),
  status: () => http.get<{ logged_in: boolean; user_id?: number }>('/system/auth/status'),
}
