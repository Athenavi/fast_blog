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
