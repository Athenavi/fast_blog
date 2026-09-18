/** 日志接口（/api/v3/system/log） */

import http from '../request'
import type {PageQuery, PageResult} from '../types'

export interface AuditLogItem {
  id?: number
  user_id?: number | null
  user_name?: string | null
  action?: string | null
  level?: string | null
  resource_type?: string | null
  resource_id?: string | null
  description?: string | null
  ip_address?: string | null
  created_at?: string | null
}

export interface AuditLogQuery extends PageQuery {
  user_id?: number
  action?: string
  level?: string
  resource_type?: string
  start_date?: string
  end_date?: string
}

export const logApi = {
  audit: (params: AuditLogQuery): Promise<PageResult<AuditLogItem>> =>
    http.page<AuditLogItem>('/system/log/audit', params),
  exportAudit: (params?: AuditLogQuery) =>
    http.get<{ format: string; content: string; count: number }>('/system/log/audit/export', params),
  cleanup: (days: number) => http.post<{ deleted: number }>('/system/log/audit/cleanup', {days}),
  lockouts: () => http.page<Record<string, unknown>>('/system/log/lockouts'),
  userHistory: (username: string, limit = 50) =>
    http.get<{ username: string; history: Record<string, unknown>[]; count: number }>(
      `/system/log/users/${encodeURIComponent(username)}/history`,
      {limit},
    ),
  userStats: (username: string) =>
    http.get<{ username: string; stats: Record<string, unknown> }>(
      `/system/log/users/${encodeURIComponent(username)}/stats`,
    ),
}
