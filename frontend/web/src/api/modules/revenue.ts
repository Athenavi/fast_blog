/** 收益分成接口（/api/v3/commerce/revenue，commerce 域）
 *
 * 四个资源：record（收益记录）/ payout（提现申请）/ config（分成配置）/ stats（统计）。
 * 用户「我的收益」是另一组端点（`/mobile/revenue`），见 `mobile.ts` 之外的 `revenueMineApi`。
 */

import http from '../request'
import type {PageQuery} from '../types'

export interface RevenueRecordItem {
  id: number
  user_id?: number | null
  revenue_type?: string | null
  amount?: number | null
  platform_fee?: number | null
  creator_earnings?: number | null
  description?: string | null
  reference_id?: number | null
  reference_type?: string | null
  status?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface RevenueRecordQuery extends PageQuery {
  user_id?: number
  revenue_type?: string
  status?: string
  reference_type?: string
}

export interface RevenueRecordPayload {
  user_id: number
  revenue_type: string
  amount: number
  description?: string | null
  reference_id?: number | null
  reference_type?: string | null
}

export interface PayoutRequestItem {
  id: number
  user_id?: number | null
  amount?: number | null
  payment_method?: string | null
  payment_account?: string | null
  account_name?: string | null
  status?: string | null
  admin_notes?: string | null
  processed_by?: number | null
  processed_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface PayoutRequestQuery extends PageQuery {
  user_id?: number
  status?: string
}

export interface SharingConfigItem {
  id: number
  revenue_type?: string | null
  platform_percentage?: number | null
  creator_percentage?: number | null
  min_payout_amount?: number | null
  is_active: boolean
  description?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface SharingConfigPayload {
  platform_percentage?: number
  creator_percentage?: number
  min_payout_amount?: number
  description?: string | null
  is_active?: boolean
}

export interface RevenueTypeStat {
  revenue_type?: string | null
  count: number
  amount: number
}

export interface PayoutStatusStat {
  count: number
  amount: number
}

export interface PlatformRevenueStats {
  total_revenue: number
  total_platform_fee: number
  total_creator_earnings: number
  record_count: number
  total_payouts: number
  pending_payouts: number
  by_type: RevenueTypeStat[]
  payouts: Record<string, PayoutStatusStat>
}

export interface UserRevenueStatsSnapshot {
  user_id: number
  total_earnings?: number | null
  total_paid?: number | null
  pending_earnings?: number | null
  available_balance?: number | null
  last_payout_at?: string | null
}

export interface UserRevenueSummary {
  user_id: number
  record_count: number
  total_amount: number
  total_creator_earnings: number
  total_platform_fee: number
  by_type: (RevenueTypeStat & { creator_earnings: number; platform_fee: number })[]
  stats: UserRevenueStatsSnapshot | null
}

export const revenueApi = {
  // ---- 收益记录 ----
  listRecords: (params?: RevenueRecordQuery) =>
    http.page<RevenueRecordItem>('/commerce/revenue/record', params),

  createRecord: (data: RevenueRecordPayload) =>
    http.post<RevenueRecordItem>('/commerce/revenue/record', data),

  removeRecord: (id: number) => http.delete<null>(`/commerce/revenue/record/${id}`),

  // ---- 提现申请 ----
  listPayouts: (params?: PayoutRequestQuery) =>
    http.page<PayoutRequestItem>('/commerce/revenue/payout', params),

  approvePayout: (id: number, notes?: string) =>
    http.post<PayoutRequestItem>(`/commerce/revenue/payout/${id}/approve`, {notes: notes ?? null}),

  completePayout: (id: number, notes?: string) =>
    http.post<PayoutRequestItem>(`/commerce/revenue/payout/${id}/complete`, {notes: notes ?? null}),

  rejectPayout: (id: number, notes?: string) =>
    http.post<PayoutRequestItem>(`/commerce/revenue/payout/${id}/reject`, {notes: notes ?? null}),

  // ---- 分成配置 ----
  listConfigs: () => http.get<SharingConfigItem[]>('/commerce/revenue/config'),

  updateConfig: (revenueType: string, data: SharingConfigPayload) =>
    http.put<SharingConfigItem>(`/commerce/revenue/config/${revenueType}`, data),

  // ---- 统计 ----
  platformStats: (params?: { start_date?: string; end_date?: string }) =>
    http.get<PlatformRevenueStats>('/commerce/revenue/stats', params),

  userSummary: (userId: number) =>
    http.get<UserRevenueSummary>(`/commerce/revenue/stats/user/${userId}`),
}

/** 前台「我的收益」（/api/v3/mobile/revenue，仅需登录） */
export interface MyPayoutPayload {
  amount: number
  payment_method: string
  payment_account: string
  account_name?: string | null
}

export const revenueMineApi = {
  listRecords: (params?: PageQuery) =>
    http.page<RevenueRecordItem>('/mobile/revenue/record', params),

  summary: () => http.get<UserRevenueSummary>('/mobile/revenue/stats'),

  createPayout: (data: MyPayoutPayload) =>
    http.post<unknown>('/mobile/revenue/payout', data),
}
