/** 文章接口（/api/v3/content/article），含公开读 */

import http from '../request'
import type {PageQuery, PageResult} from '../types'

export interface ArticleItem {
  id: number
  title?: string | null
  slug?: string | null
  excerpt?: string | null
  cover_image?: string | null
  category_id?: number | null
  tags: string[]
  views: number
  likes: number
  user_id?: number | null
  status?: number | null
  hidden: boolean
  is_featured: boolean
  is_sticky: boolean
  is_vip_only: boolean
  required_vip_level: number
  post_type?: string | null
  sort_order: number
  scheduled_publish_at?: string | null
  published_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface ArticleDetail extends ArticleItem {
  content?: string | null
  language_code?: string | null
  seo?: Record<string, unknown> | null
}

export interface ArticleQuery extends PageQuery {
  status?: number
  category_id?: number
  user_id?: number
  post_type?: string
  is_featured?: boolean
  is_sticky?: boolean
}

export interface ArticlePayload {
  title: string
  slug?: string
  excerpt?: string
  content?: string
  cover_image?: string
  category_id?: number | null
  tags?: string[]
  status?: number
  hidden?: boolean
  is_featured?: boolean
  is_sticky?: boolean
  is_vip_only?: boolean
  required_vip_level?: number
  post_type?: string
  sort_order?: number
  scheduled_publish_at?: string | null
  language_code?: string
}

export const articleApi = {
  // ---- 管理端 ----
  list: (params: ArticleQuery): Promise<PageResult<ArticleItem>> =>
    http.page<ArticleItem>('/content/article', params),
  detail: (id: number, language_code?: string) =>
    http.get<ArticleDetail>(`/content/article/${id}`, {language_code}),
  create: (data: ArticlePayload) => http.post<ArticleDetail>('/content/article', data),
  update: (id: number, data: Partial<ArticlePayload>) =>
    http.put<ArticleDetail>(`/content/article/${id}`, data),
  /** 软删除（后端 status = -1） */
  remove: (id: number) => http.delete<null>(`/content/article/${id}`),
  publish: (id: number, publish = true) =>
    http.post<ArticleItem>(`/content/article/${id}/publish`, {publish}),
  batchDelete: (ids: number[]) =>
    http.post<{ affected: number }>('/content/article/batch/delete', {ids}),
  /** 批量发布 / 撤回（后端在单次请求内逐条处理，返回实际处理条数） */
  batchPublish: (ids: number[], publish = true) =>
    http.post<{ affected: number }>('/content/article/batch/publish', {ids, publish}),
  reorder: (items: Array<{ id: number; sort_order: number }>) =>
    http.post<{ affected: number }>('/content/article/reorder', items),

  // ---- 公开读（前台/预览）----
  publicList: (params?: PageQuery & { category_id?: number; tag?: string; post_type?: string }) =>
    http.page<ArticleItem>('/content/article/public/list', params),
  publicDetail: (id: number, language_code?: string) =>
    http.get<ArticleDetail>(`/content/article/public/detail/${id}`, {language_code}),
  publicBySlug: (slug: string, language_code?: string) =>
    http.get<ArticleDetail>(`/content/article/public/slug/${encodeURIComponent(slug)}`, {
      language_code,
    }),
  addViews: (id: number) => http.post<{ views: number }>(`/content/article/public/${id}/views`),
}
