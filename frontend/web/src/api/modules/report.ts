/** 报表接口（/api/v3/analytics/report，analytics 域）
 *
 * 报表正文是**结构随类型变化**的对象（真实聚合结果），这里只给到够用的类型；
 * 导出与历史下载是**文件下载**（服务端带 `Content-Disposition`），
 * 因此绕开 `@/api/request` 的 axios 实例，用 `$fetch` + `responseType: 'blob'`。
 */

import http from '../request'
import {STORAGE_TOKEN} from '@/constants'
import {storage} from '@/utils/storage'
import type {PageQuery} from '../types'

export type ReportFormat = 'json' | 'csv'
export type ReportType = 'content' | 'user-activity' | 'traffic' | 'custom'
export type ReportFrequency = 'daily' | 'weekly' | 'monthly'
export type CustomMetric = 'content' | 'users' | 'traffic' | 'engagement'

export interface ReportPeriod {
  start: string
  end: string
  days: number
}

export interface ContentReport {
  report_type: string
  period: ReportPeriod
  summary: {
    total_articles: number
    published_articles: number
    new_articles: number
    total_views: number
    total_likes: number
    comments_in_period: number
    avg_views_per_article: number
  }
  top_articles: {
    id: number
    title?: string | null
    slug?: string | null
    views: number
    likes: number
  }[]
  trend: { day: string; articles: number; comments: number }[]
  generated_at: string
}

export interface UserActivityReport {
  report_type: string
  period: ReportPeriod
  metrics: {
    total_users: number
    new_users: number
    active_users: number
    returning_users: number
    user_retention_rate: number
  }
  activity_distribution: { by_hour: Record<string, number>; by_weekday: Record<string, number> }
  trend: { day: string; new_users: number; active_users: number }[]
  generated_at: string
}

export interface TrafficReport {
  report_type: string
  period: ReportPeriod
  overview: {
    total_visits: number
    unique_visitors: number
    total_sessions: number
    bounce_rate: number
  }
  sources: Record<string, number>
  top_pages: { page_url: string; views: number }[]
  trend: { day: string; page_views: number; unique_visitors: number }[]
  generated_at: string
}

export interface CustomReport {
  report_type: string
  period: ReportPeriod
  metrics: Record<string, Record<string, number>>
  requested_metrics: string[]
  filters?: Record<string, unknown> | null
  generated_at: string
}

export interface ReportTemplate {
  id: string
  name: string
  description: string
  report_type: string
  metrics?: string[]
  default_days: number
}

export interface ScheduledReportItem {
  id: number
  name?: string | null
  report_type?: string | null
  frequency?: string | null
  metrics?: string[] | null
  days: number
  export_format?: string | null
  is_active: boolean
  last_run_at?: string | null
  next_run_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface ScheduledReportQuery extends PageQuery {
  report_type?: string
  is_active?: boolean
}

export interface ScheduledReportPayload {
  name: string
  report_type: string
  frequency: string
  metrics?: string[] | null
  days?: number
  export_format?: string
  is_active?: boolean
}

export interface ReportHistoryItem {
  id: number
  scheduled_report_id?: number | null
  report_name?: string | null
  report_type?: string | null
  format?: string | null
  generated_at?: string | null
}

export interface ReportHistoryQuery extends PageQuery {
  report_type?: string
  scheduled_report_id?: number
}

/** blob 下载：`$fetch` 带 Bearer token，落地为浏览器下载（不走 axios 的 envelope 解析） */
async function downloadPost(
  url: string,
  body: Record<string, unknown>,
  filename: string,
): Promise<void> {
  const token = storage.get<string>(STORAGE_TOKEN)
  const blob = await $fetch<Blob>(url, {
    method: 'POST',
    body,
    headers: token ? {Authorization: `Bearer ${token}`} : {},
    responseType: 'blob',
  })
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(href)
}

function stamp(): string {
  const now = new Date()
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
}

export const reportApi = {
  // ---- 报表生成 ----
  content: (days: number) => http.get<ContentReport>('/analytics/report/content', {days}),

  userActivity: (days: number) =>
    http.get<UserActivityReport>('/analytics/report/user-activity', {days}),

  traffic: (days: number) => http.get<TrafficReport>('/analytics/report/traffic', {days}),

  custom: (data: { metrics: string[]; days: number; filters?: Record<string, unknown> | null }) =>
    http.post<CustomReport>('/analytics/report/custom', data),

  templates: () =>
    http.get<{ templates: ReportTemplate[]; count: number }>('/analytics/report/templates'),

  exportReport: (data: {
    report_type: string
    format: ReportFormat
    days: number
    metrics?: string[] | null
  }) =>
    downloadPost(
      '/api/v3/analytics/report/export',
      data,
      `report-${data.report_type}-${stamp()}.${data.format}`,
    ),

  // ---- 定时报表 ----
  listScheduled: (params?: ScheduledReportQuery) =>
    http.page<ScheduledReportItem>('/analytics/report/scheduled', params),

  createScheduled: (data: ScheduledReportPayload) =>
    http.post<ScheduledReportItem>('/analytics/report/scheduled', data),

  updateScheduled: (id: number, data: Partial<ScheduledReportPayload>) =>
    http.put<ScheduledReportItem>(`/analytics/report/scheduled/${id}`, data),

  removeScheduled: (id: number) => http.delete<null>(`/analytics/report/scheduled/${id}`),

  toggleScheduled: (id: number) =>
    http.post<ScheduledReportItem>(`/analytics/report/scheduled/${id}/toggle`),

  runScheduled: (id: number) =>
    http.post<ReportHistoryItem>(`/analytics/report/scheduled/${id}/run`),

  // ---- 报表历史 ----
  listHistory: (params?: ReportHistoryQuery) =>
    http.page<ReportHistoryItem>('/analytics/report/history', params),
}
