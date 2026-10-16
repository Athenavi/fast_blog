/** 搜索设置接口（/api/v3/system/search，system 域）
 *
 * 对应后端 `src/api/v3/modules/system/search/controller.py` 的 5 个端点。
 *
 * `api_key` 只入不出：读取时只给 `has_api_key`，保存时留空表示保持原值 ——
 * 密钥不回显就不会进浏览器历史、日志、截图或前端报错上报。
 */

import http from '../request'

export interface SearchConfig {
  enabled: boolean
  host: string
  index_name: string
  /** 是否已配置密钥（**不回显密钥本身**） */
  has_api_key: boolean
  /** 环境变量侧的地址（用于排查"为什么没生效"） */
  env_host?: string | null
  env_has_api_key: boolean
}

export interface SearchConfigPayload {
  enabled: boolean
  host: string
  index_name: string
  /** 留空表示**保持原值**，不修改已保存的密钥 */
  api_key?: string | null
  /** 显式清空密钥（与"留空"区分开，避免误提交静默丢凭据） */
  clear_api_key?: boolean
}

export interface SearchTestResult {
  ok: boolean
  message: string
  version?: string | null
  latency_ms?: number | null
}

export interface SearchReindexResult {
  ok: boolean
  message: string
  indexed: number
  skipped: number
}

export interface SearchStats {
  ok: boolean
  available: boolean
  message: string
  index_name: string
  documents: number
  is_indexing: boolean
}

export const searchSettingsApi = {
  getConfig: () => http.get<SearchConfig>('/system/search/config'),
  updateConfig: (data: SearchConfigPayload) =>
    http.put<SearchConfig>('/system/search/config', data),
  /** 真实连通性测试（连不上会返回 ok=false 与真实原因） */
  test: () => http.post<SearchTestResult>('/system/search/test'),
  /** 从数据库重建索引（只索引当前站点可见文章） */
  reindex: () => http.post<SearchReindexResult>('/system/search/reindex'),
  stats: () => http.get<SearchStats>('/system/search/stats'),
}
