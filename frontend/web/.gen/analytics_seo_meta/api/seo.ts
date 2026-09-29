/** SEO 分析与内链接口（/api/v3/analytics/seo） */

import http from '../request'

export interface SeoAnalyzePayload {
  title?: string
  description?: string
  content?: string
  keywords?: string[]
  internal_links?: number
}

export interface SeoMetrics {
  [key: string]: unknown
}

export interface SeoAnalyzeResult {
  overall_score: number
  grade?: string | null
  metrics: SeoMetrics
  suggestions: string[]
  analyzed_at?: string | null
}

export interface ArticleSeoItem {
  article_id: number
  title?: string | null
  slug?: string | null
  status?: number | null
  score: number
  grade?: string | null
  suggestion_count: number
  top_suggestions: string[]
  metrics?: SeoMetrics
  suggestions?: string[]
}

/** 文章 SEO 元信息（对应后端 assistant_service.get_seo 返回） */
export interface ArticleSeoMeta {
  article_id: number
  article_title?: string | null
  slug?: string | null
  has_seo: boolean
  seo_title?: string | null
  seo_description?: string | null
  seo_keywords?: string | null
  og_title?: string | null
  og_description?: string | null
  og_image?: string | null
  og_type?: string | null
  twitter_title?: string | null
  twitter_description?: string | null
  twitter_image?: string | null
  twitter_card?: string | null
  canonical_url?: string | null
  robots_meta?: string | null
  schema_org_enabled?: boolean | null
  schema_org_type?: string | null
}

/** 手工保存 SEO 元信息的入参（对应后端 assistant_schema.SEOSaveRequest，字段全可选） */
export interface SeoSavePayload {
  seo_title?: string | null
  seo_description?: string | null
  seo_keywords?: string | null
  og_title?: string | null
  og_description?: string | null
  og_image?: string | null
  og_type?: string | null
  twitter_title?: string | null
  twitter_description?: string | null
  twitter_image?: string | null
  twitter_card?: string | null
  canonical_url?: string | null
  robots_meta?: string | null
  schema_org_enabled?: boolean | null
  schema_org_type?: string | null
}

/** 保存结果（对应后端 assistant_service.save_seo 返回：字段集 + saved_fields） */
export type SeoSaveResult = Omit<ArticleSeoMeta, 'has_seo'> & { saved_fields: string[] }

/** AI 生成 SEO 的入参（对应后端 assistant_schema.SEOGenerateRequest） */
export interface SeoGeneratePayload {
  config_id?: number | null
  apply?: boolean
  max_tokens?: number | null
}

/** AI 生成 SEO 的结果（对应后端 assistant_service.generate_for_article 返回） */
export interface SeoGenerateResult {
  article_id: number
  model: string
  task_type: string
  prompt_tokens: number
  completion_tokens: number
  generated: SeoSavePayload
  applied: string[]
}

/** 结构化数据类型清单项（对应后端 schema_org_service.types） */
export interface SchemaTypeItem {
  type: string
  label: string
}

/** 站点信息（对应后端 schema_org_service.site_context 返回） */
export interface SeoSiteContext {
  name: string
  base_url: string
  logo: string
  source: string
}

/** 文章结构化数据（对应后端 schema_org_service.for_article 返回） */
export interface ArticleSchemaResult {
  article_id: number
  enabled: boolean
  schema_type: string
  site: SeoSiteContext
  blocks: Array<Record<string, unknown>>
  json_ld: string
  script_tag: string
}

/** 结构化数据预览入参（对应后端 assistant_schema.SchemaPreviewRequest） */
export interface SchemaPreviewPayload {
  schema_type?: string
  params?: Record<string, unknown>
  base_url?: string | null
}

/** 结构化数据预览结果（对应后端 controller.schema_preview 返回） */
export interface SchemaPreviewResult {
  schema_type: string
  site: SeoSiteContext
  schema: Record<string, unknown>
  json_ld: string
  script_tag: string
}

export const seoApi = {
  analyze: (payload: SeoAnalyzePayload) =>
    http.post<SeoAnalyzeResult>('/analytics/seo/analyze', payload),
  analyzeArticle: (articleId: number) =>
    http.get<ArticleSeoItem>(`/analytics/seo/articles/${articleId}`),
  bulkCheck: (payload?: { ids?: number[]; limit?: number; only_published?: boolean }) =>
    http.post<{
      checked: number
      average_score: number
      grade_distribution: Record<string, number>
      items: ArticleSeoItem[]
    }>('/analytics/seo/bulk-check', payload ?? {}),
  keywords: (params?: { limit?: number; scan_limit?: number }) =>
    http.get<{ keywords: Array<{ keyword: string; count: number }>; total: number }>(
      '/analytics/seo/keywords',
      params,
    ),
  orphans: (limit = 100) =>
    http.get<{
      items: Array<{ article_id: number; title?: string; slug?: string; inbound_links: number }>
      total: number
      total_articles: number
    }>('/analytics/seo/orphan-articles', {limit}),
  linkDistribution: () =>
    http.get<Record<string, unknown>>('/analytics/seo/link-distribution'),
  internalLinks: (articleId: number) =>
    http.get<Record<string, unknown>>(`/analytics/seo/internal-links/${articleId}`),
  report: (limit = 100) =>
    http.get<{
      generated_at: string
      total_articles: number
      average_score: number
      grade_distribution: Record<string, number>
      common_suggestions: Array<{ suggestion: string; count: number }>
      orphan_count: number
      top_keywords: Array<{ keyword: string; count: number }>
    }>('/analytics/seo/report', {limit}),
  /** 读取文章 SEO 元信息。后端 GET /analytics/seo/articles/{article_id}/seo */
  articleSeo: (articleId: number) =>
    http.get<ArticleSeoMeta>(`/analytics/seo/articles/${articleId}/seo`),
  /** 保存文章 SEO 元信息。后端 PUT /analytics/seo/articles/{article_id}/seo */
  saveArticleSeo: (articleId: number, payload: SeoSavePayload) =>
    http.put<SeoSaveResult>(`/analytics/seo/articles/${articleId}/seo`, payload),
  /** 用 LLM 生成文章 SEO 元信息。后端 POST /analytics/seo/articles/{article_id}/seo/generate */
  generateArticleSeo: (articleId: number, payload: SeoGeneratePayload) =>
    http.post<SeoGenerateResult>(`/analytics/seo/articles/${articleId}/seo/generate`, payload),
  /** 结构化数据支持的类型清单。后端 GET /analytics/seo/schema/types */
  schemaTypes: () => http.get<SchemaTypeItem[]>('/analytics/seo/schema/types'),
  /** 文章的结构化数据。后端 GET /analytics/seo/schema/article/{article_id} */
  articleSchema: (articleId: number, baseUrl?: string) =>
    http.get<ArticleSchemaResult>(`/analytics/seo/schema/article/${articleId}`, {base_url: baseUrl}),
  /** 结构化数据预览（不落库）。后端 POST /analytics/seo/schema/preview */
  schemaPreview: (payload: SchemaPreviewPayload) =>
    http.post<SchemaPreviewResult>('/analytics/seo/schema/preview', payload),
}

/** 搜索行为分析（/api/v3/analytics/search） */
export const searchAnalyticsApi = {
  summary: (days?: number) =>
    http.get<{
      total_searches: number
      unique_keywords: number
      zero_result_searches: number
      zero_result_rate: number | null
    }>('/analytics/search/summary', {days}),
  popular: (params?: { limit?: number; days?: number }) =>
    http.get<Array<{ keyword: string; count: number; avg_results: number }>>(
      '/analytics/search/popular',
      params,
    ),
  zeroResult: (params?: { limit?: number; days?: number }) =>
    http.get<Array<{ keyword: string; count: number }>>('/analytics/search/zero-result', params),
  trend: (days = 30) =>
    http.get<{ days: number; points: Array<{ day: string; searches: number; zero_result: number }> }>(
      '/analytics/search/trend',
      {days},
    ),
}
