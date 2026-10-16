/** 社交账号绑定管理接口（/api/v3/system/social，system 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface SocialAccountItem {
  id: number
  user_id?: number | null
  provider?: string | null
  provider_user_id?: string | null
  has_token: boolean
  token_expires_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface SocialAccountQuery extends PageQuery {
  user_id?: number
  provider?: string
}

export const socialApi = {
  list: (params?: SocialAccountQuery) =>
    http.page<SocialAccountItem>('/system/social/account', params),

  unbind: (id: number) => http.delete<null>(`/system/social/account/${id}`),
}
