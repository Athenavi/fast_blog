/** 企业版授权接口（/api/v3/ops/enterprise，ops 域）—— 企业许可证 + 数据保留策略
 *
 * 契约要点：
 *  - `license_key` 唯一，重复由拦截器统一提示（后端 409）；
 *  - `features` 库列是 JSON 字符串，出参已由后端还原为字符串列表；
 *  - `max_sites = -1` 表示不限站点数。
 */

import http from '../request'
import type {PageQuery} from '../types'

export interface EnterpriseLicenseItem {
  id: number
  license_key?: string | null
  license_type: string
  company_name?: string | null
  contact_email?: string | null
  /** -1 表示不限 */
  max_sites: number
  features?: string[] | null
  valid_from?: string | null
  valid_until?: string | null
  is_active: boolean
  support_level: string
  sla_enabled: boolean
  sla_uptime_guarantee?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export interface EnterpriseLicenseQuery extends PageQuery {
  keyword?: string
}

export interface EnterpriseLicensePayload {
  license_key?: string
  license_type?: string
  company_name?: string | null
  contact_email?: string | null
  max_sites?: number
  features?: string[] | null
  valid_from?: string | null
  valid_until?: string | null
  is_active?: boolean
  support_level?: string
  sla_enabled?: boolean
  sla_uptime_guarantee?: number | null
}

export interface DataRetentionPolicyItem {
  id: number
  data_category: string
  retention_days: number
  /** 到期动作：delete / archive */
  action: string
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface DataRetentionPolicyQuery extends PageQuery {
  keyword?: string
}

export interface DataRetentionPolicyPayload {
  data_category?: string
  retention_days?: number
  action?: string
  is_active?: boolean
}

export const enterpriseApi = {
  listLicenses: (params?: EnterpriseLicenseQuery) =>
    http.page<EnterpriseLicenseItem>('/ops/enterprise/license', params),

  createLicense: (data: EnterpriseLicensePayload) =>
    http.post<EnterpriseLicenseItem>('/ops/enterprise/license', data),

  updateLicense: (id: number, data: Partial<EnterpriseLicensePayload>) =>
    http.put<EnterpriseLicenseItem>(`/ops/enterprise/license/${id}`, data),

  removeLicense: (id: number) => http.delete<null>(`/ops/enterprise/license/${id}`),

  listPolicies: (params?: DataRetentionPolicyQuery) =>
    http.page<DataRetentionPolicyItem>('/ops/enterprise/retention-policy', params),

  createPolicy: (data: DataRetentionPolicyPayload) =>
    http.post<DataRetentionPolicyItem>('/ops/enterprise/retention-policy', data),

  updatePolicy: (id: number, data: Partial<DataRetentionPolicyPayload>) =>
    http.put<DataRetentionPolicyItem>(`/ops/enterprise/retention-policy/${id}`, data),

  removePolicy: (id: number) => http.delete<null>(`/ops/enterprise/retention-policy/${id}`),
}
