/** 单页接口（/api/v3/content/page） */

import http from '../request'
import type {PageQuery, PageResult} from '../types'

export interface PageItem {
  id: number
  title?: string | null
  slug?: string | null
  excerpt?: string | null
  template?: string | null
  status?: number | null
  author_id?: number | null
  parent_id?: number | null
  order_index: number
  meta_title?: string | null
  meta_description?: string | null
  meta_keywords?: string | null
  published_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface PageDetail extends PageItem {
  content?: string | null
}

export interface PagePayload {
  title: string
  slug?: string
  content?: string
  excerpt?: string
  template?: string
  status?: number
  parent_id?: number | null
  order_index?: number
  meta_title?: string
  meta_description?: string
  meta_keywords?: string
}

export const pageApi = {
  list: (params?: PageQuery & { status?: number; parent_id?: number }): Promise<PageResult<PageItem>> =>
    http.page<PageItem>('/content/page', params),
  detail: (id: number) => http.get<PageDetail>(`/content/page/${id}`),
  create: (data: PagePayload) => http.post<PageDetail>('/content/page', data),
  update: (id: number, data: Partial<PagePayload>) =>
    http.put<PageDetail>(`/content/page/${id}`, data),
  remove: (id: number) => http.delete<null>(`/content/page/${id}`),
  batchDelete: (ids: number[]) =>
    http.post<{ affected: number }>('/content/page/batch/delete', {ids}),
  publish: (id: number, publish = true) =>
    http.post<PageItem>(`/content/page/${id}/publish`, {publish}),
  publicList: () => http.page<PageItem>('/content/page/public/list'),
  publicBySlug: (slug: string) =>
    http.get<PageDetail>(`/content/page/public/slug/${encodeURIComponent(slug)}`),
}
