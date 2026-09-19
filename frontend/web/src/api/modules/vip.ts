/** VIP 会员接口（/api/v3/marketing/vip，marketing 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface VipPlanItem {
  id: number
  name?: string | null
  description?: string | null
  price?: number | null
  original_price?: number | null
  duration_days?: number | null
  level?: number
  features?: string[] | null
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface VipPlanPayload {
  name: string
  description?: string | null
  price: number
  original_price?: number | null
  duration_days: number
  level?: number
  features?: string[] | null
  is_active?: boolean
}

export interface VipFeatureItem {
  id: number
  code?: string | null
  name?: string | null
  description?: string | null
  required_level?: number
  is_active: boolean
  created_at?: string | null
}

export interface VipFeaturePayload {
  code: string
  name: string
  description?: string | null
  required_level?: number
  is_active?: boolean
}

export interface VipSubscriptionItem {
  id: number
  user_id?: number | null
  plan_id?: number | null
  starts_at?: string | null
  expires_at?: string | null
  status?: number
  payment_amount?: number | null
  transaction_id?: string | null
  created_at?: string | null
}

export interface VipSubscriptionPayload {
  user_id: number
  plan_id: number
  starts_at?: string | null
  payment_amount?: number | null
  transaction_id?: string | null
}

export interface VipSubscriptionQuery extends PageQuery {
  user_id?: number
  status?: number
}

export const vipApi = {
  plans: (params?: PageQuery) => http.page<VipPlanItem>('/marketing/vip/plan', params),

  createPlan: (data: VipPlanPayload) => http.post<VipPlanItem>('/marketing/vip/plan', data),

  updatePlan: (id: number, data: Partial<VipPlanPayload>) =>
    http.put<VipPlanItem>(`/marketing/vip/plan/${id}`, data),

  removePlan: (id: number) => http.delete<null>(`/marketing/vip/plan/${id}`),

  features: (params?: PageQuery) => http.page<VipFeatureItem>('/marketing/vip/feature', params),

  createFeature: (data: VipFeaturePayload) => http.post<VipFeatureItem>('/marketing/vip/feature', data),

  updateFeature: (id: number, data: Partial<VipFeaturePayload>) =>
    http.put<VipFeatureItem>(`/marketing/vip/feature/${id}`, data),

  removeFeature: (id: number) => http.delete<null>(`/marketing/vip/feature/${id}`),

  subscriptions: (params?: VipSubscriptionQuery) =>
    http.page<VipSubscriptionItem>('/marketing/vip/subscription', params),

  createSubscription: (data: VipSubscriptionPayload) =>
    http.post<VipSubscriptionItem>('/marketing/vip/subscription', data),

  cancelSubscription: (id: number) =>
    http.post<VipSubscriptionItem>(`/marketing/vip/subscription/${id}/cancel`),
}
