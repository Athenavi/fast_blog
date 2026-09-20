/** 短代码接口（/api/v3/content/shortcode，content 域）—— code 创建后锁定，重复返回 409 */

import http from '../request'
import type {PageQuery} from '../types'

export interface ShortcodeItem {
  id: number
  code: string
  name: string
  description?: string | null
  content: string
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface ShortcodeQuery extends PageQuery {
  is_active?: boolean
}

export interface ShortcodePayload {
  code?: string
  name: string
  description?: string | null
  content: string
  is_active?: boolean
}

export const shortcodeApi = {
  list: (params?: ShortcodeQuery) => http.page<ShortcodeItem>('/content/shortcode', params),

  create: (data: ShortcodePayload) => http.post<ShortcodeItem>('/content/shortcode', data),

  /** code 创建后锁定，更新负载不含 code */
  update: (id: number, data: Partial<Omit<ShortcodePayload, 'code'>>) =>
    http.put<ShortcodeItem>(`/content/shortcode/${id}`, data),

  remove: (id: number) => http.delete<null>(`/content/shortcode/${id}`),
}
