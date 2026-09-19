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

export const cdnApi = {
  getConfig: () => http.get<CdnConfig>('/ops/cdn/config'),

  saveConfig: (data: CdnConfigPayload) => http.put<CdnConfig>('/ops/cdn/config', data),
}
