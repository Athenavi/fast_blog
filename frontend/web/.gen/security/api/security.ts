/** 安全中心接口（/api/v3/system/security，system 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface SecurityOverview {
  attempts_24h: number
  failures_24h: number
  success_rate: number
  locked_users: number
  blacklist_count: number
  top_failure_reasons: Record<string, number>
}

export interface LoginAttemptItem {
  id: number
  username?: string | null
  ip_address?: string | null
  user_agent?: string | null
  is_success: boolean
  failure_reason?: string | null
  created_at?: string | null
}

export interface LoginAttemptQuery extends PageQuery {
  username?: string
  is_success?: boolean
}

export interface BlacklistItem {
  id: number
  token_identifier?: string | null
  reason?: string | null
  expires_at?: string | null
  created_at?: string | null
}

// ------------------------------------------------------------------ 异常行为检测
// 对齐 /system/security/anomalies（GET）与 /system/security/anomalies/thresholds（PUT）。
// 字段逐条对照 anomaly_service.AnomalyDetectionService.detect() 与 schema.AnomalyThresholdUpdate。

/** 异常阈值（键与 anomaly_service.DEFAULT_THRESHOLDS 完全一致） */
export interface AnomalyThresholds {
  brute_force_failures: number
  brute_force_window_minutes: number
  spray_usernames: number
  spray_window_minutes: number
  unusual_hour_start: number
  unusual_hour_end: number
  unusual_hour_logins: number
  unusual_hour_window_hours: number
  rate_abuse_actions: number
  rate_abuse_window_minutes: number
  max_items: number
}

/** 阈值增量更新载荷：只传要改的项（对齐 schema.AnomalyThresholdUpdate 的 Optional 语义） */
export type AnomalyThresholdUpdate = Partial<AnomalyThresholds>

/** 单条异常项：四类检测返回字段不完全相同，故可选字段较多 */
export interface AnomalyItem {
  type: string
  severity: string
  target?: string | null
  ip_address?: string | null
  count: number
  threshold: number
  window_minutes?: number
  window_hours?: number
  attempts?: number
  first_at?: string | null
  last_at?: string | null
  detail: string
}

/** 可疑 IP 加权排行项 */
export interface SuspiciousIp {
  ip_address: string
  score: number
  anomalies: string[]
}

/** /system/security/anomalies 响应 */
export interface AnomalyResult {
  generated_at: string
  data_source: string
  thresholds: AnomalyThresholds
  summary: {
    total: number
    by_type: Record<string, number>
    by_severity: Record<string, number>
  }
  items: AnomalyItem[]
  top_suspicious_ips: SuspiciousIp[]
}

// ------------------------------------------------------------------ 安全周期报表
// 对齐 /system/security/report/{weekly,monthly,archive,history}。
// 字段逐条对照 report_service.SecurityReportService.build() / history()。

/** 报表统计周期 */
export interface SecurityReportPeriod {
  start: string
  end: string
  days: number
}

/** 报表摘要（审计总数/失败率 + 登录总数/失败率） */
export interface SecurityReportSummary {
  total_audit_events: number
  failed_operations: number
  audit_failure_rate: number
  total_login_attempts: number
  failed_logins: number
  login_failure_rate: number
}

/** 趋势单点 */
export interface SecurityReportTrendPoint {
  day: string
  audit_events: number
  failed_logins: number
}

/** 安全评分（仅月报返回） */
export interface SecurityScore {
  score: number
  grade: string
  level: number
}

/** 一份安全报表（weekly / monthly / archive 的返回体） */
export interface SecurityReport {
  report_type: string
  period: SecurityReportPeriod
  summary: SecurityReportSummary
  audit: {
    by_level: Record<string, number>
    by_status: Record<string, number>
    top_actions: Record<string, number>
  }
  logins: { top_failed_ips: Record<string, number> }
  trend: SecurityReportTrendPoint[]
  generated_at: string
  security_score?: SecurityScore
}

/** 报表历史条目（history 不返回正文 content） */
export interface SecurityReportHistoryItem {
  id: number
  report_name: string
  report_type: string
  format: string
  generated_at?: string | null
}

/** 报表历史查询（对齐 controller 的 report_type / limit 查询参数） */
export interface SecurityReportHistoryQuery {
  report_type?: string
  limit?: number
}

/** 报表历史响应 */
export interface SecurityReportHistoryResult {
  reports: SecurityReportHistoryItem[]
  count: number
}

export const securityApi = {
  overview: () => http.get<SecurityOverview>('/system/security/overview'),

  attempts: (params?: LoginAttemptQuery) =>
    http.page<LoginAttemptItem>('/system/security/attempts', params),

  blacklist: (params?: PageQuery) =>
    http.page<BlacklistItem>('/system/security/blacklist', params),

  removeBlacklist: (id: number) => http.delete<null>(`/system/security/blacklist/${id}`),

  // ---------------------------------------------------------------- 异常行为检测
  /** 异常行为检测（真表窗口聚合，limit 控制每类返回条数，默认 50） */
  anomalies: (limit?: number) =>
    http.get<AnomalyResult>('/system/security/anomalies', limit === undefined ? undefined : {limit}),

  /** 增量更新异常检测阈值（返回合并后的完整阈值并落库 system_settings） */
  updateAnomalyThresholds: (payload: AnomalyThresholdUpdate) =>
    http.put<AnomalyThresholds>('/system/security/anomalies/thresholds', payload),

  // ---------------------------------------------------------------- 安全周期报表
  /** 安全周报（近 7 天，只生成不落库） */
  weeklyReport: () => http.get<SecurityReport>('/system/security/report/weekly'),

  /** 安全月报（近 30 天 + 安全评分，只生成不落库） */
  monthlyReport: () => http.get<SecurityReport>('/system/security/report/monthly'),

  /** 归档一份周期报表（写入 report_history） */
  archiveReport: (kind: 'weekly' | 'monthly') =>
    http.post<SecurityReport>('/system/security/report/archive', {kind}),

  /** 安全报表历史（读 report_history，不返回正文） */
  reportHistory: (params?: SecurityReportHistoryQuery) =>
    http.get<SecurityReportHistoryResult>(
      '/system/security/report/history',
      params as Record<string, unknown> | undefined,
    ),
}
