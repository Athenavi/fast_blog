/**
 * 健康探针与前端性能（RUM）接口（/api/v3/system/health，system 域）
 *
 * 逐条对照后端 `src/api/v3/modules/system/health/{controller.py,schema.py,service.py}`：
 *   - live / ready 为公开探针，返回 `HealthPayload`
 *   - site-report 需 `module_system:monitor:view`，query `format=json|text`
 *   - web-vitals/summary 需 `module_system:monitor:view`，query `hours` / `limit`
 *
 * 注意：RUM **上报**入口（`POST /system/health/web-vitals`）已由
 * `src/composables/useWebVitals.ts` 通过 sendBeacon 直接上报，本模块不重复接线。
 */

import http from '../request'

/** 探针载荷（后端 `HealthPayload`；live / ready 共用） */
export interface HealthPayload {
  /** ok / degraded */
  status: string
  /** 服务标识（后端常量 `fastblog-api-v3`） */
  service: string
  version: string
  environment: string
  /** 各依赖检查结果，例如 ready 探针的 `{database: "ok"}` */
  checks: Record<string, string>
}

/** 站点健康检查单项（`site_health.SiteHealthService` 各检查函数的元素） */
export interface SiteHealthItem {
  name: string
  value: string
  /** pass / warning / fail / info */
  status: string
  score?: number
  /** 可能为 null（无建议时） */
  recommendation?: string | null
  /** 仅部分检查（如磁盘 / 数据库失败）带此字段 */
  error?: string
  /** 仅存储目录检查带此字段 */
  path?: string
}

/** 站点健康分组（键固定为 system / database / storage / security / performance） */
export type SiteHealthGroups = Record<string, SiteHealthItem[]>

/** 站点健康报告（`run_full_check` 返回；format=json） */
export interface SiteHealthReport {
  overall_score: number
  /** good / warning / critical */
  status: string
  checks: SiteHealthGroups
  /** ISO8601 */
  timestamp: string
}

/** 站点健康报告（format=text，后端 `generate_report('text')`） */
export interface SiteHealthTextReport {
  report: string
}

/** CWV 汇总（`performance_tracker.get_overall_stats` 返回）
 *
 * 无数据时后端只返回 total_pages / total_samples / time_range，
 * 其余平均值与达标率为可选字段。
 */
export interface WebVitalsOverall {
  total_pages: number
  total_samples: number
  time_range: string
  avg_load_time?: number
  avg_first_contentful_paint?: number
  avg_largest_contentful_paint?: number
  avg_interaction_to_next_paint?: number
  /** 旧字段名（兼容历史脚本） */
  avg_first_input_delay?: number
  avg_time_to_first_byte?: number
  avg_cumulative_layout_shift?: number
  /** Core Web Vitals 达标率（百分比，后端已 round 到 2 位） */
  cwv_pass_rate?: number
}

/** 最慢页面单项（`get_slowest_pages` 元素） */
export interface WebVitalsSlowPage {
  url: string
  avg_load_time: number
  sample_count: number
}

/** `GET /web-vitals/summary` 返回体 */
export interface WebVitalsSummary {
  overall: WebVitalsOverall
  slowest_pages: WebVitalsSlowPage[]
}

/** `GET /site-report` 查询参数（用 type 而非 interface，便于赋给 http 的 Record 形参） */
type SiteReportQuery = {
  format?: 'json' | 'text'
}

/** `GET /web-vitals/summary` 查询参数（hours 1~720，limit 1~100） */
type WebVitalsSummaryQuery = {
  hours?: number
  limit?: number
}

export const healthApi = {
  /** 存活探针（公开，不触碰外部依赖）GET /system/health/live */
  live: () => http.get<HealthPayload>('/system/health/live'),

  /** 就绪探针（公开，含一次数据库连通性探测）GET /system/health/ready
   *
   * 数据库不可用时后端以 code=500 返回（`resp.fail`），此时 http 层会 reject；
   * 调用方应 `.catch(() => null)` 并按「不可用」展示。
   */
  ready: () => http.get<HealthPayload>('/system/health/ready'),

  /** 站点健康报告（JSON，需 module_system:monitor:view）GET /system/health/site-report */
  siteReport: (params: SiteReportQuery = {format: 'json'}) =>
    http.get<SiteHealthReport>('/system/health/site-report', params),

  /** 站点健康报告（纯文本）GET /system/health/site-report?format=text */
  siteReportText: () =>
    http.get<SiteHealthTextReport>('/system/health/site-report', {format: 'text'} as SiteReportQuery),

  /** 前端性能（CWV）汇总（需 module_system:monitor:view）GET /system/health/web-vitals/summary */
  webVitalsSummary: (params: WebVitalsSummaryQuery = {hours: 24, limit: 10}) =>
    http.get<WebVitalsSummary>('/system/health/web-vitals/summary', params),
}
