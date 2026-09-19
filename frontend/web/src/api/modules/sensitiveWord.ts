/** 敏感词库接口（/api/v3/system/sensitive-word，system 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface SensitiveWordItem {
  id: number
  word: string
  level: number
  action: 'block' | 'replace' | 'warn' | string
  replacement?: string | null
  category?: string | null
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface SensitiveWordQuery extends PageQuery {
  level?: number
  category?: string
  is_active?: boolean
}

export interface SensitiveWordPayload {
  word: string
  level?: number
  action?: 'block' | 'replace' | 'warn' | string
  replacement?: string | null
  category?: string | null
  is_active?: boolean
}

export const sensitiveWordApi = {
  list: (params?: SensitiveWordQuery) => http.page<SensitiveWordItem>('/system/sensitive-word', params),

  create: (data: SensitiveWordPayload) => http.post<SensitiveWordItem>('/system/sensitive-word', data),

  update: (id: number, data: Partial<SensitiveWordPayload>) =>
    http.put<SensitiveWordItem>(`/system/sensitive-word/${id}`, data),

  remove: (id: number) => http.delete<null>(`/system/sensitive-word/${id}`),

  batchImport: (words: string[], opts?: { level?: number; action?: string; category?: string }) =>
    http.post<{ total: number; added: number; duplicated: number }>(
      '/system/sensitive-word/batch/import',
      {words, ...opts},
    ),
}
