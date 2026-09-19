/** 安全中心接口（/api/v3/system/security，system 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface SecurityOverview {
  attempts_24h: number
  failures_24h: number
  success_rate: number
  locked_users: number
  blacklist_count: number
  top_failure_reasons: Record<string, number>
}

export interface LoginAttemptItem {
  id: number
  username?: string | null
  ip_address?: string | null
  user_agent?: string | null
  is_success: boolean
  failure_reason?: string | null
  created_at?: string | null
}

export interface LoginAttemptQuery extends PageQuery {
  username?: string
  is_success?: boolean
}

export interface BlacklistItem {
  id: number
  token_identifier?: string | null
  reason?: string | null
  expires_at?: string | null
  created_at?: string | null
}

export const securityApi = {
  overview: () => http.get<SecurityOverview>('/system/security/overview'),

  attempts: (params?: LoginAttemptQuery) =>
    http.page<LoginAttemptItem>('/system/security/attempts', params),

  blacklist: (params?: PageQuery) =>
    http.page<BlacklistItem>('/system/security/blacklist', params),

  removeBlacklist: (id: number) => http.delete<null>(`/system/security/blacklist/${id}`),
}
