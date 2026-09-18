/**
 * 前台用户端接口（v3 的 `mobile` 域）
 *
 * 与 `system/auth` 的差异：这里面向站内读者（注册、我的资料、我的统计），
 * 需要登录的接口走浏览器 cookie / Bearer，与后台共用同一套 token 机制。
 */
import http from '../request'

export interface MobileTokenData {
  access_token?: string
  refresh_token?: string
  token_type?: string
  expires_in?: number
  user_id?: number
  username?: string
  requires_2fa?: boolean
  temp_token?: string
  message?: string
}

export interface RegisterPayload {
  /** 3-30 位，仅字母/数字/下划线（与后端校验一致） */
  username: string
  email: string
  /** 至少 8 位 */
  password: string
}

export interface MobileLoginPayload {
  username?: string
  email?: string
  password: string
  remember_me?: boolean
}

export interface MobileProfile {
  id?: number
  username?: string
  email?: string
  profile_picture?: string | null
  bio?: string | null
  locale?: string | null
  is_active?: boolean
  created_at?: string | null
  updated_at?: string | null
}

/** 用户可自助修改的字段（用户名 / 邮箱 / 权限不可改） */
export interface MobileProfileUpdate {
  profile_picture?: string
  bio?: string
  locale?: string
  password?: string
}

export interface MobileUserStats {
  articles: number
  comments: number
  likes_received: number
}

export const mobileApi = {
  register: (payload: RegisterPayload) => http.post<MobileTokenData>('/mobile/auth/register', payload),

  login: (payload: MobileLoginPayload) => http.post<MobileTokenData>('/mobile/auth/login', payload),

  profile: () => http.get<MobileProfile>('/mobile/user/profile'),

  updateProfile: (payload: MobileProfileUpdate) =>
    http.put<MobileProfile>('/mobile/user/profile', payload),

  stats: () => http.get<MobileUserStats>('/mobile/user/stats'),
}
