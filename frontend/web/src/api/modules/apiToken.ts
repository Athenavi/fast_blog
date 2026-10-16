/** API 令牌接口（/api/v3/system/api-token） */

import http from '../request'

export interface ApiTokenItem {
  id: number
  name: string
  /** 明文里的可识别前缀（用于在列表里分辨令牌） */
  token_prefix?: string
  /** 权限范围；令牌实际权限 = scopes ∩ 你当前拥有的权限码 */
  scopes?: string[]
  expires_at?: string | null
  last_used_at?: string | null
  is_active?: boolean
  created_at?: string

  [key: string]: unknown
}

/** 创建响应：`token` 是**明文**，仅在创建时返回这一次 */
export interface ApiTokenCreated extends ApiTokenItem {
  token: string
}

export interface ApiTokenCreatePayload {
  name: string
  /** 权限范围；必须是当前账号已有权限码的子集，后端会校验 */
  scopes: string[]
  /** 有效期（天）；留空表示不过期 */
  expires_in_days?: number
}

export const apiTokenApi = {
  list: () => http.get<ApiTokenItem[]>('/system/api-token'),
  create: (payload: ApiTokenCreatePayload) => http.post<ApiTokenCreated>('/system/api-token', payload),
  revoke: (id: number) => http.delete<null>(`/system/api-token/${id}`),
}
