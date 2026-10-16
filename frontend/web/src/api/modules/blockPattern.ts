/** 区块模板接口（/api/v3/extension/block-pattern，extension 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface BlockPatternItem {
  id: number
  name?: string | null
  title?: string | null
  description?: string | null
  category?: string | null
  blocks?: string | null
  keywords?: string | null
  thumbnail?: string | null
  is_public: boolean
  viewport_width?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export interface BlockPatternPayload {
  name: string
  title: string
  description?: string | null
  category?: string | null
  blocks?: string | null
  keywords?: string | null
  thumbnail?: string | null
  is_public?: boolean
}

export interface BlockPatternQuery extends PageQuery {
  category?: string
}

export const blockPatternApi = {
  list: (params?: BlockPatternQuery) => http.page<BlockPatternItem>('/extension/block-pattern', params),

  create: (data: BlockPatternPayload) => http.post<BlockPatternItem>('/extension/block-pattern', data),

  update: (id: number, data: Partial<BlockPatternPayload>) =>
    http.put<BlockPatternItem>(`/extension/block-pattern/${id}`, data),

  remove: (id: number) => http.delete<null>(`/extension/block-pattern/${id}`),
}
