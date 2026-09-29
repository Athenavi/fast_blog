/** 站点配额接口（/api/v3/system/quota，system 域）
 *
 * 对齐后端 quota controller：
 *   GET  /system/quota/{site_id}          读取配额 + 用量（module_system:site:view）
 *   POST /system/quota/{site_id}/check    校验追加后是否超配额（module_system:site:view）
 *   PUT  /system/quota/{site_id}          更新配额（module_system:site:edit）
 *
 * 配额键与后端 ``RESOURCE_TYPES`` 一致（articles / media / users / storage_mb）；
 * 值 ``0`` 或 ``null`` 均表示**不限**（见后端 ``is_unlimited``）。
 */

import http from '../request'

/** 受支持的资源类型（= 配额键，与后端 RESOURCE_TYPES 对齐） */
export type QuotaResource = 'articles' | 'media' | 'users' | 'storage_mb'

/** 一份配额：非负整数为上限，``null`` 表示不限（``0`` 后端亦视为不限） */
export type QuotaLimits = Record<QuotaResource, number | null>

/** 资源用量：storage_mb 为小数 MB，其余为计数；无法统计的资源为 ``null`` */
export type QuotaUsage = Record<QuotaResource, number | null>

/** GET /system/quota/{site_id} 返回值（site_quota_service.get） */
export interface QuotaSnapshot {
  site_id: number
  site_name?: string | null
  quota: QuotaLimits
  usage: QuotaUsage
  remaining: Record<QuotaResource, number | null>
  usage_percent: Record<QuotaResource, number | null>
  exceeded: QuotaResource[]
  /** 各资源用量的统计口径说明（后端 USAGE_SCOPE，如实标注） */
  usage_scope: Record<string, string>
}

/** POST /system/quota/{site_id}/check 请求体（QuotaCheckRequest） */
export interface QuotaCheckPayload {
  resource_type: QuotaResource
  requested_amount?: number
}

/** 配额校验结果（check_resource 返回体） */
export interface QuotaCheckResult {
  allowed: boolean
  resource_type: string
  reason: string
  current: number | null
  limit: number | null
  remaining: number | null
}

/** PUT /system/quota/{site_id} 请求体（只接受已知配额键，未知键会被 400 拒绝） */
export type QuotaUpdatePayload = Partial<Record<QuotaResource, number | null>>

/** PUT /system/quota/{site_id} 返回值（site_quota_service.update） */
export interface QuotaUpdateResult {
  site_id: number
  quota: QuotaLimits
  updated: QuotaResource[]
}

export const quotaApi = {
  /** 读取站点配额与用量 */
  get: (siteId: number) => http.get<QuotaSnapshot>(`/system/quota/${siteId}`),

  /** 校验追加 requested_amount 后是否仍在配额内 */
  check: (siteId: number, data: QuotaCheckPayload) =>
    http.post<QuotaCheckResult>(`/system/quota/${siteId}/check`, data),

  /** 更新站点配额 */
  update: (siteId: number, data: QuotaUpdatePayload) =>
    http.put<QuotaUpdateResult>(`/system/quota/${siteId}`, data),
}
