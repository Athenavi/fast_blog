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

// ---------------------------------------------------------------- 前台自助（mobile/vip，批次 16）
//
// 套餐列表仍走 marketing/vip 的公开端点（`/marketing/vip/public/plans`，前台 SSR 用 apiGet）；
// 这里封装**只有登录用户能做**的事：我的订阅、开通下单、取消、付费内容与访问判定。

/** 我的 VIP 状态 */
export interface MyVipStatus {
  is_vip: boolean
  level: number
  plan_name?: string | null
  subscription_id?: number | null
  starts_at?: string | null
  expires_at?: string | null
  days_left: number
}

/** 订阅记录（含历史）：status 0=进行中 / 1=已过期 / 2=已取消 */
export interface MyVipSubscription {
  id: number
  plan_id?: number | null
  plan_name?: string | null
  level?: number | null
  starts_at?: string | null
  expires_at?: string | null
  status: number
  payment_amount?: number | null
  transaction_id?: string | null
  created_at?: string | null
}

/** 支付订单：pending / paid / failed */
export interface VipOrderItem {
  id: number
  order_no: string
  plan_id: number
  plan_name?: string | null
  amount: number
  status: string
  provider?: string | null
  transaction_id?: string | null
  paid_at?: string | null
  created_at?: string | null
}

export interface MyVipInfo {
  status: MyVipStatus
  subscriptions: MyVipSubscription[]
  pending_orders: VipOrderItem[]
}

/** 下单结果：`payment` 是支付插件的调起参数（支付宝 / Stripe 是 payment_url，微信是 prepay_id） */
export interface VipPaymentResult {
  order: VipOrderItem
  payment: Record<string, unknown>
}

export interface VipAccessInfo {
  has_access: boolean
  reason?: string | null
  article_id?: number | null
  required_level: number
  current_level: number
  is_vip: boolean
}

/** 付费内容条目（`accessible` = 当前用户是否读得到） */
export interface PremiumContentItem {
  id: number
  title?: string | null
  slug?: string | null
  excerpt?: string | null
  cover_image?: string | null
  views: number
  likes: number
  required_vip_level: number
  accessible: boolean
  user_id?: number | null
  category_id?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export const vipSelfApi = {
  /** 我的订阅（状态 + 历史 + 待支付订单） */
  my: () => http.get<MyVipInfo>('/mobile/vip/my-subscription'),

  /** 开通 / 续费下单（金额由服务端按套餐价格取，不接受前端传入） */
  createPayment: (planId: number, options?: { provider?: string; return_url?: string }) =>
    http.post<VipPaymentResult>('/mobile/vip/create-payment', {
      plan_id: planId,
      provider: options?.provider ?? null,
      return_url: options?.return_url ?? null,
    }),

  /** 取消当前生效的订阅 */
  cancel: (comment?: string) =>
    http.post<{ success: boolean; subscription_id: number }>('/mobile/vip/my-subscription/cancel', {
      comment: comment ?? null,
    }),

  /** 我能不能读这篇（article_id）或这个等级 */
  checkAccess: (params: { article_id?: number; required_level?: number }) =>
    http.get<VipAccessInfo>('/mobile/vip/check-access', params),

  /** 付费内容列表（每条带 accessible） */
  premiumContent: (params?: PageQuery) =>
    http.page<PremiumContentItem>('/mobile/vip/premium-content', params),
}
