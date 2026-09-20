/** 页面搭建接口（/api/v3/content/page-builder，content 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface PageBuilderItem {
  id: number
  title?: string | null
  slug?: string | null
  blocks_data: Array<Record<string, unknown>>
  template_name?: string | null
  is_published: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface PageBuilderQuery extends PageQuery {
  is_published?: boolean
}

export interface PageBuilderPayload {
  title: string
  slug?: string
  blocks_data: Array<Record<string, unknown>>
  template_name?: string | null
  is_published?: boolean
}

export const pageBuilderApi = {
  list: (params?: PageBuilderQuery) => http.page<PageBuilderItem>('/content/page-builder', params),

  create: (data: PageBuilderPayload) => http.post<PageBuilderItem>('/content/page-builder', data),

  detail: (id: number) => http.get<PageBuilderItem>(`/content/page-builder/${id}`),

  /** 更新（契约约定 PUT 不携带 slug：slug 创建后锁定） */
  update: (id: number, data: Partial<Omit<PageBuilderPayload, 'slug'>>) =>
    http.put<PageBuilderItem>(`/content/page-builder/${id}`, data),

  remove: (id: number) => http.delete<null>(`/content/page-builder/${id}`),

  publish: (id: number, is_published: boolean) =>
    http.post<PageBuilderItem>(`/content/page-builder/${id}/publish`, {is_published}),
}
