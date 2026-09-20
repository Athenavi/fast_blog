/** 监控中心的告警 / 指标 / SLA 接口（/api/v3/system/monitor/*，system 域）
 *
 * 与 `monitor.ts` 的分工：那个是「实时状态」（服务器信息 / 在线会话），
 * 这个是「历史与治理」（告警 / 时序指标 / SLA 报表）。
 * 数据由外部探针 / 脚本写入，前端只做管理与查询。
 */

import http from '../request'
import type {PageQuery} from '../types'

export type AlertSeverity = 'info' | 'warning' | 'error' | 'critical'
export type MetricBucket = 'minute' | 'hour' | 'day'

export interface AlertItem {
  id: number
  alert_type?: string | null
  severity?: string | null
  title?: string | null
  message?: string | null
  source?: string | null
  metric_name?: string | null
  metric_value?: number | null
  threshold?: number | null
  is_resolved: boolean
  resolved_at?: string | null
  notified_users?: number[] | null
  created_at?: string | null
  updated_at?: string | null
}

export interface AlertQuery extends PageQuery {
  alert_type?: string
  severity?: string
  is_resolved?: boolean
  source?: string
}

export interface AlertPayload {
  alert_type?: string
  message?: string
  severity?: string
  title?: string | null
  source?: string | null
  metric_name?: string | null
  metric_value?: number | null
  threshold?: number | null
  is_resolved?: boolean
}

export interface AlertStats {
  total: number
  unresolved: number
  resolved: number
  by_type: { alert_type?: string | null; count: number }[]
  by_severity: { severity?: string | null; count: number }[]
}

export interface MetricItem {
  id: number
  metric_name?: string | null
  metric_value?: number | null
  metric_type?: string | null
  labels?: Record<string, unknown> | null
  timestamp?: string | null
  site_id?: number | null
}

export interface MetricQuery extends PageQuery {
  metric_name?: string
  metric_type?: string
  site_id?: number
  start?: string
  end?: string
}

export interface MetricPayload {
  metric_name: string
  metric_value: number
  metric_type?: string | null
  labels?: Record<string, unknown> | null
  timestamp?: string | null
  site_id?: number | null
}

export interface MetricSeriesPoint {
  bucket: string
  avg?: number | null
  min?: number | null
  max?: number | null
  count: number
}

export interface MetricSeriesResult {
  metric_name: string
  bucket: string
  points: MetricSeriesPoint[]
}

export interface SLAItem {
  id: number
  license_id?: number | null
  period_start?: string | null
  period_end?: string | null
  uptime_percentage?: number | null
  target_percentage?: number | null
  is_compliant: boolean
  downtime_minutes: number
  total_minutes?: number | null
  created_at?: string | null
  checked_at?: string | null
}

export interface SLAQuery extends PageQuery {
  license_id?: number
  is_compliant?: boolean
}

export interface SLAPayload {
  license_id: number
  period_start: string
  period_end: string
  target_percentage?: number
  uptime_percentage?: number | null
  downtime_minutes?: number | null
}

export interface SLAComputePayload {
  license_id: number
  period_start: string
  period_end: string
  target_percentage?: number
}

export interface SLAStats {
  total_reports: number
  compliant: number
  breached: number
  compliance_rate: number
  avg_uptime_percentage?: number | null
}

export const monitoringApi = {
  // ---- 告警 ----
  listAlerts: (params?: AlertQuery) => http.page<AlertItem>('/system/monitor/alert', params),

  createAlert: (data: AlertPayload) => http.post<AlertItem>('/system/monitor/alert', data),

  alertStats: () => http.get<AlertStats>('/system/monitor/alert/stats'),

  getAlert: (id: number) => http.get<AlertItem>(`/system/monitor/alert/${id}`),

  updateAlert: (id: number, data: AlertPayload) =>
    http.put<AlertItem>(`/system/monitor/alert/${id}`, data),

  resolveAlert: (id: number) => http.post<AlertItem>(`/system/monitor/alert/${id}/resolve`),

  removeAlert: (id: number) => http.delete<null>(`/system/monitor/alert/${id}`),

  // ---- 指标 ----
  listMetrics: (params?: MetricQuery) => http.page<MetricItem>('/system/monitor/metric', params),

  createMetric: (data: MetricPayload) => http.post<MetricItem>('/system/monitor/metric', data),

  metricSeries: (params: { metric_name: string; bucket?: MetricBucket; start?: string; end?: string }) =>
    http.get<MetricSeriesResult>('/system/monitor/metric/series', params),

  pruneMetrics: (retentionDays: number) =>
    http.delete<{ deleted: number }>('/system/monitor/metric/prune', {
      retention_days: retentionDays,
    }),

  removeMetric: (id: number) => http.delete<null>(`/system/monitor/metric/${id}`),

  // ---- SLA ----
  listSlaReports: (params?: SLAQuery) => http.page<SLAItem>('/system/monitor/sla', params),

  createSlaReport: (data: SLAPayload) => http.post<SLAItem>('/system/monitor/sla', data),

  /** 按周期内 critical 告警的真实时长计算并写入一条报表 */
  computeSla: (data: SLAComputePayload) => http.post<SLAItem>('/system/monitor/sla/compute', data),

  slaStats: () => http.get<SLAStats>('/system/monitor/sla/stats'),

  getSlaReport: (id: number) => http.get<SLAItem>(`/system/monitor/sla/${id}`),

  updateSlaReport: (id: number, data: Partial<SLAPayload>) =>
    http.put<SLAItem>(`/system/monitor/sla/${id}`, data),

  removeSlaReport: (id: number) => http.delete<null>(`/system/monitor/sla/${id}`),
}
