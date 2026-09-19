/** 广告管理接口（/api/v3/marketing/ad，marketing 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface AdPlacementItem {
  id: number
  name?: string | null
  code?: string | null
  description?: string | null
  position?: string | null
  width?: number | null
  height?: number | null
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface AdPlacementPayload {
  name: string
  code: string
  description?: string | null
  position?: string
  width?: number | null
  height?: number | null
  is_active?: boolean
}

export interface AdItem {
  id: number
  title?: string | null
  content?: string | null
  image_url?: string | null
  link_url?: string | null
  alt_text?: string | null
  ad_type?: string | null
  placement_id?: number | null
  start_date?: string | null
  end_date?: string | null
  click_count?: number
  impression_count?: number
  budget?: number | null
  cost_per_click?: number | null
  cost_per_impression?: number | null
  is_active: boolean
  priority?: number
  target_audience?: string | null
  device_targeting?: string | null
  geo_targeting?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface AdPayload {
  title: string
  content?: string | null
  image_url?: string | null
  link_url?: string | null
  alt_text?: string | null
  ad_type?: string
  placement_id?: number | null
  start_date?: string | null
  end_date?: string | null
  budget?: number | null
  cost_per_click?: number | null
  cost_per_impression?: number | null
  is_active?: boolean
  priority?: number
  target_audience?: string | null
  device_targeting?: string | null
  geo_targeting?: string | null
}

export interface AdQuery extends PageQuery {
  placement_id?: number
  is_active?: boolean
}

export interface AdStats {
  total_ads: number
  active_ads: number
  total_clicks: number
  total_impressions: number
  total_budget: number
}

export const adApi = {
  list: (params?: AdQuery) => http.page<AdItem>('/marketing/ad', params),

  create: (data: AdPayload) => http.post<AdItem>('/marketing/ad', data),

  update: (id: number, data: Partial<AdPayload>) => http.put<AdItem>(`/marketing/ad/${id}`, data),

  remove: (id: number) => http.delete<null>(`/marketing/ad/${id}`),

  stats: () => http.get<AdStats>('/marketing/ad/stats'),

  placements: (params?: PageQuery) => http.page<AdPlacementItem>('/marketing/ad/placement', params),

  createPlacement: (data: AdPlacementPayload) => http.post<AdPlacementItem>('/marketing/ad/placement', data),

  updatePlacement: (id: number, data: Partial<AdPlacementPayload>) =>
    http.put<AdPlacementItem>(`/marketing/ad/placement/${id}`, data),

  removePlacement: (id: number) => http.delete<null>(`/marketing/ad/placement/${id}`),
}
