/** 仪表盘接口（/api/v3/analytics/dashboard） */

import http from '../request'

export interface DashboardOverview {
  total_articles: number
  published_articles: number
  draft_articles: number
  total_users: number
  active_users: number
  total_comments: number
  pending_comments: number
  total_views: number
  total_likes: number
  total_categories: number
  total_media: number
}

export interface TrendPoint {
  day: string
  articles: number
  comments: number
  users: number
}

export interface TrendResult {
  days: number
  points: TrendPoint[]
}

export interface RecentArticle {
  id: number
  title?: string | null
  slug?: string | null
  status?: number | null
  views: number
  created_at?: string | null
  published_at?: string | null
}

export interface RecentComment {
  id: number
  article_id?: number | null
  content?: string | null
  author_name?: string | null
  is_approved: boolean
  created_at?: string | null
}

export interface TopArticle {
  id: number
  title?: string | null
  views: number
  likes: number
}

export const dashboardApi = {
  overview: () => http.get<DashboardOverview>('/analytics/dashboard/overview'),
  trend: (days = 30) => http.get<TrendResult>('/analytics/dashboard/trend', {days}),
  recentArticles: (limit = 5) =>
    http.get<RecentArticle[]>('/analytics/dashboard/recent-articles', {limit}),
  recentComments: (limit = 5) =>
    http.get<RecentComment[]>('/analytics/dashboard/recent-comments', {limit}),
  topArticles: (limit = 10, days?: number) =>
    http.get<TopArticle[]>('/analytics/dashboard/top-articles', {limit, days}),
}
