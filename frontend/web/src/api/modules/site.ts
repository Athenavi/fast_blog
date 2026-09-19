/** 多站点管理接口（/api/v3/system/site，system 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface SiteItem {
  id: number
  name?: string | null
  slug?: string | null
  domain?: string | null
  additional_domains?: string[] | null
  description?: string | null
  logo_url?: string | null
  favicon_url?: string | null
  theme?: string | null
  language?: string | null
  timezone?: string | null
  settings?: Record<string, unknown> | null
  is_active: boolean
  is_default: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface SiteQuery extends PageQuery {
  is_active?: boolean
}

export interface SitePayload {
  name: string
  slug?: string
  domain?: string
  additional_domains?: string[] | null
  description?: string | null
  logo_url?: string | null
  favicon_url?: string | null
  theme?: string
  language?: string
  timezone?: string
  settings?: Record<string, unknown> | null
  is_active?: boolean
  is_default?: boolean
}

export const siteApi = {
  list: (params?: SiteQuery) => http.page<SiteItem>('/system/site', params),

  create: (data: SitePayload) => http.post<SiteItem>('/system/site', data),

  update: (id: number, data: Partial<SitePayload>) =>
    http.put<SiteItem>(`/system/site/${id}`, data),

  remove: (id: number) => http.delete<null>(`/system/site/${id}`),
}
