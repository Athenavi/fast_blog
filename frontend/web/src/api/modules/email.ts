/** 邮件服务接口（/api/v3/ops/email，ops 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface EmailConfigItem {
  id: number
  provider?: string | null
  has_api_key: boolean
  smtp_host?: string | null
  smtp_port?: number | null
  smtp_username?: string | null
  has_smtp_password: boolean
  from_email?: string | null
  from_name?: string | null
  enable_batch_sending: boolean
  batch_size: number
  daily_limit: number
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface EmailConfigPayload {
  provider?: string
  api_key?: string | null
  smtp_host?: string | null
  smtp_port?: number | null
  smtp_username?: string | null
  smtp_password?: string | null
  from_email?: string
  from_name?: string | null
  enable_batch_sending?: boolean
  batch_size?: number
  daily_limit?: number
  is_active?: boolean
}

export interface EmailSubscriptionItem {
  id: number
  user_id?: number | null
  subscribed: boolean
  created_at?: string | null
}

export const emailApi = {
  configs: () => http.get<EmailConfigItem[]>('/ops/email/config'),

  createConfig: (data: EmailConfigPayload) => http.post<EmailConfigItem>('/ops/email/config', data),

  updateConfig: (id: number, data: Partial<EmailConfigPayload>) =>
    http.put<EmailConfigItem>(`/ops/email/config/${id}`, data),

  removeConfig: (id: number) => http.delete<null>(`/ops/email/config/${id}`),

  subscriptions: (params?: PageQuery) =>
    http.page<EmailSubscriptionItem>('/ops/email/subscription', params),
}
