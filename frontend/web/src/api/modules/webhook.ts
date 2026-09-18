/** Webhook 接口（/api/v3/ops/webhook） */

import http from '../request'

export interface WebhookItem {
  id: number
  name?: string | null
  url?: string | null
  events: string[]
  is_active: boolean
  has_secret: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface WebhookPayload {
  name: string
  url: string
  events?: string[]
  secret?: string
  is_active?: boolean
}

export const webhookApi = {
  list: () => http.page<WebhookItem>('/ops/webhook'),
  events: () => http.get<Array<{ event: string }>>('/ops/webhook/events'),
  detail: (id: number) => http.get<WebhookItem>(`/ops/webhook/${id}`),
  create: (data: WebhookPayload) => http.post<WebhookItem>('/ops/webhook', data),
  update: (id: number, data: Partial<WebhookPayload>) =>
    http.put<WebhookItem>(`/ops/webhook/${id}`, data),
  remove: (id: number) => http.delete<null>(`/ops/webhook/${id}`),
  test: (id: number) =>
    http.post<{ triggered: boolean; event: string; webhook_id: number; detail?: string | null }>(
      `/ops/webhook/${id}/test`,
    ),
}
