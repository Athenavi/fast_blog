/** GDPR 合规同意记录接口（/api/v3/system/gdpr，system 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface GdprConsentItem {
  id: number
  user_id?: number | null
  consent_type?: string | null
  granted: boolean
  details?: string | null
  ip_address?: string | null
  user_agent?: string | null
  created_at?: string | null
}

export interface GdprConsentQuery extends PageQuery {
  user_id?: number
  consent_type?: string
  granted?: boolean
}

export interface GdprStats {
  total: number
  granted: number
  revoked: number
  by_type: Record<string, number>
}

export const gdprApi = {
  list: (params?: GdprConsentQuery) => http.page<GdprConsentItem>('/system/gdpr/consent', params),

  stats: () => http.get<GdprStats>('/system/gdpr/consent/stats'),

  remove: (id: number) => http.delete<null>(`/system/gdpr/consent/${id}`),
}
