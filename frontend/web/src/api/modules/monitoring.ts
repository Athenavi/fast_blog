/** 监控中心的告警 / 指标 / SLA 接口（/api/v3/system/monitor/*，system 域）
 *
 * 与 `monitor.ts` 的分工：那个是「实时状态」（服务器信息 / 在线会话），
 * 这个是「历史与治理」（告警 / 时序指标 / SLA 报表）。
 * 数据由外部探针 / 脚本写入，前端只做管理与查询。
 */

import http from '../request'
import type {PageQuery} from '../types'
import type {ServerInfo} from './monitor'

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

// ================================================================ 告警推送渠道
// 逐条对照 `alert_channel_service.py` 的 `_channel_out()`：
//   id / site_id / platform / webhook_url / channel_id / has_token（**明文与密文都不出网**）
//   / enable_new_article_notification / enable_comment_notification / enable_system_alert
//   / notification_template / is_active / created_at / updated_at
/** 支持的推送平台（`PLATFORMS` 键） */
export type AlertPlatform = 'telegram' | 'discord' | 'slack' | 'webhook' | 'email'

export interface AlertChannelItem {
  id: number
  site_id?: number | null
  platform?: string | null
  webhook_url?: string | null
  channel_id?: string | null
  /** 是否已配置 bot_token（只回「有没有」，不回明文） */
  has_token: boolean
  enable_new_article_notification: boolean
  enable_comment_notification: boolean
  enable_system_alert: boolean
  notification_template?: string | null
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface AlertChannelQuery extends PageQuery {
  platform?: string
  is_active?: boolean
}

/** 对应 `AlertChannelCreate`；`bot_token` 落库前 AES-256-GCM 加密 */
export interface AlertChannelPayload {
  platform: string
  webhook_url?: string | null
  bot_token?: string | null
  channel_id?: string | null
  enable_new_article_notification?: boolean
  enable_comment_notification?: boolean
  enable_system_alert?: boolean
  notification_template?: string | null
  is_active?: boolean
  site_id?: number | null
}

/** 单渠道发送结果（`_send()` 的 `(sent, status_code, detail)` + 渠道标识） */
export interface AlertChannelSendResult {
  channel_id: number
  platform?: string | null
  sent: boolean
  status_code?: number | null
  detail?: string | null
}

/** 推送历史条目（`notified_users` JSON 里的对象，`dispatch_alert` 写入） */
export interface AlertDeliveryItem {
  channel_id: number
  platform?: string | null
  sent: boolean
  status_code?: number | null
  detail?: string | null
  at?: string | null
}

/** 对应 `deliveries()` 返回 */
export interface AlertDeliveriesResult {
  alert_id: number
  total: number
  sent: number
  items: AlertDeliveryItem[]
}

/** 对应 `dispatch_alert()` 返回；无可用渠道时额外带 `detail` */
export interface AlertDispatchResult {
  alert_id: number
  channels: number
  sent: number
  failed: number
  results: AlertChannelSendResult[]
  detail?: string | null
}

// ================================================================ 慢查询（引擎真实采集）
// 逐条对照 `shared/services/performance/slow_query_logger.py`
/** 慢查询明细（`log_query()` 写入的单条） */
export interface SlowQueryItem {
  sql: string
  duration: number
  params?: Record<string, unknown> | null
  table?: string | null
  query_type?: string | null
  timestamp?: string | null
}

/** `get_statistics()` 的 `by_table` 值 */
export interface SlowQueryTableStat {
  count: number
  total_time: number
  avg_time: number
  max_time: number
}

/** `get_statistics()` 返回 */
export interface SlowQueryStatistics {
  period_hours: number
  total_queries: number
  slow_queries: number
  avg_duration: number
  max_duration: number
  by_table: Record<string, SlowQueryTableStat>
  by_type: Record<string, { count: number; total_time: number }>
}

/** `get_optimization_suggestions()` 单条（字段随建议来源不同而不同，均为可选） */
export interface SlowQuerySuggestion {
  type?: string | null
  title?: string | null
  message?: string | null
  recommendation?: string | null
  table?: string | null
  duration?: number | null
  sql?: string | null
  pattern?: string | null
}

/** `GET /system/monitor/slow-queries` 返回 */
export interface SlowQueryResult {
  threshold_ms: number
  items: SlowQueryItem[]
  statistics: SlowQueryStatistics
  suggestions: SlowQuerySuggestion[]
}

// ================================================================ 查询优化（真实采集 + 真实计划）
/** `get_fingerprint_stats()` / `detect_n_plus_one()` 的单条指纹（N+1 条目额外带 `hint`） */
export interface QueryFingerprintStat {
  fingerprint: string
  sample_sql: string
  table?: string | null
  query_type?: string | null
  executions: number
  total_duration: number
  max_duration: number
  avg_duration: number
  /** 仅 `detect_n_plus_one()` 的条目带此字段 */
  hint?: string | null
}

/** `GET /system/monitor/query-optimizer/analysis` 返回 */
export interface QueryOptimizerAnalysis {
  data_source: string
  threshold_ms: number
  period_hours: number
  statistics: SlowQueryStatistics
  by_fingerprint: QueryFingerprintStat[]
  n_plus_one: QueryFingerprintStat[]
  suggestions: SlowQuerySuggestion[]
}

/** `analyze_explain_plan()` 的 `bottlenecks` 单条 */
export interface ExplainBottleneck {
  node_type: string
  relation?: string | null
  total_cost?: number | null
  plan_rows?: number | null
  actual_time_ms?: number | null
}

/** `analyze_explain_plan()` 返回 */
export interface ExplainAnalysis {
  parsed: boolean
  node_types: Record<string, number>
  uses_sequential_scan: boolean
  sequential_scan_tables: string[]
  bottlenecks: ExplainBottleneck[]
  recommendations: string[]
}

/** `POST /system/monitor/query-optimizer/explain` 返回（`executed` 恒为 false） */
export interface QueryExplainResult {
  sql: string
  executed: boolean
  analysis: ExplainAnalysis
}

// ================================================================ 性能综合报告
// 逐条对照 `performance_report.py::report()` 与 `performance_tracker.py`
/** `performance_tracker.get_overall_stats()`（无样本时只回前三个字段） */
export interface PerfOverallStats {
  total_pages: number
  total_samples: number
  time_range: string
  avg_load_time?: number
  avg_first_contentful_paint?: number
  avg_largest_contentful_paint?: number
  avg_interaction_to_next_paint?: number
  avg_first_input_delay?: number
  avg_time_to_first_byte?: number
  avg_cumulative_layout_shift?: number
  cwv_pass_rate?: number
}

/** `performance_tracker.get_slowest_pages()` 单条 */
export interface PerfSlowestPage {
  url: string
  avg_load_time: number
  sample_count: number
}

/** 性能报告里 `metrics.by_type` 单条 */
export interface PerfMetricTypeStat {
  metric_type: string
  count: number
  avg_value?: number | null
}

/** `GET /system/monitor/performance-report` 返回 */
export interface PerformanceReport {
  period_hours: number
  generated_at: string
  runtime: {
    overall: PerfOverallStats
    slowest_pages: PerfSlowestPage[]
  }
  database: {
    statistics: SlowQueryStatistics
    threshold_ms: number
    top_fingerprints: QueryFingerprintStat[]
    n_plus_one: QueryFingerprintStat[]
  }
  server: ServerInfo
  alerts: AlertStats
  metrics: { total: number; by_type: PerfMetricTypeStat[] }
  sla: SLAStats
  notes: string[]
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

  // ---- 告警推送渠道（任务 9）----
  /** 渠道列表（notification_integrations 真表；bot_token 只回 has_token） */
  listAlertChannels: (params?: AlertChannelQuery) =>
    http.page<AlertChannelItem>('/system/monitor/alert-channel', params),

  /** 新建渠道；bot_token 落库前 AES-256-GCM 加密 */
  createAlertChannel: (data: AlertChannelPayload) =>
    http.post<AlertChannelItem>('/system/monitor/alert-channel', data),

  /** 更新渠道；bot_token 留空表示保持原值 */
  updateAlertChannel: (channelId: number, data: Partial<AlertChannelPayload>) =>
    http.put<AlertChannelItem>(`/system/monitor/alert-channel/${channelId}`, data),

  removeAlertChannel: (channelId: number) =>
    http.delete<null>(`/system/monitor/alert-channel/${channelId}`),

  /** 真实发一条测试消息（失败也如实返回 status_code / detail） */
  testAlertChannel: (channelId: number) =>
    http.post<AlertChannelSendResult>(`/system/monitor/alert-channel/${channelId}/test`),

  /** 某告警的推送历史（来自 notified_users JSON） */
  alertDeliveries: (alertId: number) =>
    http.get<AlertDeliveriesResult>(`/system/monitor/alert/${alertId}/deliveries`),

  /** 推送告警到所有启用渠道；force=true 忽略 enable_system_alert（手工补发） */
  dispatchAlert: (alertId: number, force = false) =>
    http.post<AlertDispatchResult>(`/system/monitor/alert/${alertId}/dispatch`, {force}),

  // ---- 慢查询（引擎 after_cursor_execute 真实采集）----
  /** 慢查询明细 + 汇总统计 + 优化建议（统计为进程内） */
  listSlowQueries: (params?: { limit?: number; hours?: number; table?: string; query_type?: string }) =>
    http.get<SlowQueryResult>('/system/monitor/slow-queries', params),

  /** 更新慢查询阈值（毫秒）；后端为 query 参数 threshold_ms */
  updateSlowQueryThreshold: (thresholdMs: number) =>
    http.put<{ threshold_ms: number }>('/system/monitor/slow-queries/threshold', null, {
      threshold_ms: thresholdMs,
    }),

  /** 清空进程内慢查询记录（需 module_system:monitor:manage） */
  clearSlowQueries: () => http.delete<null>('/system/monitor/slow-queries'),

  // ---- 查询优化（真实采集数据 + 真实计划分析）----
  /** 按 SQL 指纹聚合的慢查询排行 + N+1 嫌疑 + 规则化建议 */
  queryOptimizerAnalysis: (params?: {
    hours?: number
    limit?: number
    min_executions?: number
    max_avg_duration?: number
  }) => http.get<QueryOptimizerAnalysis>('/system/monitor/query-optimizer/analysis', params),

  /** 对指定 SELECT 真跑 EXPLAIN (FORMAT JSON)，**不执行**该语句 */
  queryOptimizerExplain: (sql: string) =>
    http.post<QueryExplainResult>('/system/monitor/query-optimizer/explain', {sql}),

  // ---- 性能综合报告 ----
  /** 聚合 RUM + 慢查询 + 服务器 + 告警 / 指标 / SLA 真实数据源 */
  performanceReport: (params?: { hours?: number; top?: number }) =>
    http.get<PerformanceReport>('/system/monitor/performance-report', params),
}
