/** CDN 配置接口（/api/v3/ops/cdn，ops 域） */

import http from '../request'

export interface CdnConfig {
  provider?: string | null
  domain?: string | null
  cdn_url?: string | null
  has_api_token: boolean
  zone_id?: string | null
  settings?: Record<string, unknown> | null
  is_active: boolean
  updated_at?: string | null
}

export interface CdnConfigPayload {
  provider: string
  domain?: string | null
  cdn_url?: string | null
  api_token?: string | null
  zone_id?: string | null
  settings?: Record<string, unknown> | null
  is_active?: boolean
}

export interface CdnPurgePayload {
  urls: string[]
  purge_everything?: boolean
}

/** 远端动作结果；失败会由 request 层抛出（后端把厂商拒绝/未实现都写成 400 + 原因） */
export interface CdnPurgeResult {
  provider: string
  success: boolean
  status_code?: number | null
  purge_everything: boolean
  urls: string[]
  message?: string | null
}

export const cdnApi = {
  getConfig: () => http.get<CdnConfig>('/ops/cdn/config'),

  saveConfig: (data: CdnConfigPayload) => http.put<CdnConfig>('/ops/cdn/config', data),

  /** 清缓存（真实调用厂商接口；未实现/未配置会带原因报错） */
  purge: (data: CdnPurgePayload) => http.post<CdnPurgeResult>('/ops/cdn/purge', data),

  /** 预热（cloudflare 无此接口，会如实报错） */
  preheat: (data: CdnPurgePayload) => http.post<CdnPurgeResult>('/ops/cdn/preheat', data),
}
