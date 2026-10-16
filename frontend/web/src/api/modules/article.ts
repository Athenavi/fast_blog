/** 文章接口（/api/v3/content/article），含公开读 */

import http from '../request'
import {CODE_SUCCESS, type ApiResponse, type PageQuery, type PageResult} from '../types'

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

/** 草稿预览令牌（对应后端 preview_service `_token_out`，绝不含口令哈希） */
export interface ArticlePreviewToken {
  id: number
  article_id: number
  token: string
  max_views?: number | null
  view_count: number
  is_active: boolean
  has_password: boolean
  expires_at?: string | null
  created_by?: number | null
  created_at?: string | null
}

/** 生成预览令牌入参（对应后端 `ArticlePreviewTokenCreate`） */
export interface ArticlePreviewTokenCreatePayload {
  expires_hours?: number
  password?: string
  max_views?: number
}

/** 公开预览下发的文章字段（后端 `_PREVIEW_FIELDS` 白名单子集） */
export interface ArticlePreviewPublicArticle {
  id: number
  title?: string | null
  slug?: string | null
  excerpt?: string | null
  cover_image?: string | null
  category?: number | null
  tags: string[]
  content?: string | null
  language_code?: string | null
  status?: number | null
  published_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

/** 公开预览的令牌元信息（访问计数 / 上限 / 有效期） */
export interface ArticlePreviewMeta {
  view_count: number
  max_views?: number | null
  expires_at?: string | null
}

/** `GET /public/preview/{token}` 的响应 `data` */
export interface ArticlePreviewResult {
  article: ArticlePreviewPublicArticle
  preview: ArticlePreviewMeta
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

  // ---- 草稿预览令牌（管理端，需 article:edit / article:view）----
  /** 为草稿签发预览令牌（返回结构含 token 明文，仅创建者可见） */
  createPreviewToken: (articleId: number, data: ArticlePreviewTokenCreatePayload = {}) =>
    http.post<ArticlePreviewToken>(`/content/article/${articleId}/preview-token`, data),
  /** 列出某文章的全部预览令牌 */
  listPreviewTokens: (articleId: number) =>
    http.get<ArticlePreviewToken[]>(`/content/article/${articleId}/preview-tokens`),
  /** 清理过期 / 已失效的令牌，返回删除条数 */
  cleanupPreviewTokens: () =>
    http.post<{ removed: number }>('/content/article/preview-token/cleanup'),
  /** 吊销指定令牌（后端置 is_active = false） */
  revokePreviewToken: (tokenId: number) =>
    http.delete<null>(`/content/article/preview-token/${tokenId}`),

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
  /**
   * 凭令牌读取未发布草稿（公开端点，无鉴权）。
   * 口令走请求头 `X-Preview-Password`（后端契约，避免出现在 URL 与访问日志），
   * `http.get` 不支持自定义请求头，故改用同一 axios 实例的 `http.raw`。
   */
  publicPreview: async (token: string, password?: string): Promise<ArticlePreviewResult> => {
    const resp = await http.raw.get<ApiResponse<ArticlePreviewResult>>(
      `/content/article/public/preview/${encodeURIComponent(token)}`,
      {headers: password ? {'X-Preview-Password': password} : undefined},
    )
    const body = resp.data
    if (body?.code === CODE_SUCCESS) return body.data
    throw new Error(body?.msg || String(body?.code))
  },
}
