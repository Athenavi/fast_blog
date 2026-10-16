/** 打赏与提现接口（`/api/v3/commerce/tipping`，commerce 域）
 *
 * **金额单位统一为「分」**（与支付插件一致）；展示用 `*_yuan` 或本地换算。
 *
 * 链路：`POST /tip` → 写 `tips`（pending）→ 调 payment-gateway 插件下单，
 * 返回 `payment` 是插件给的调起参数（支付宝 / Stripe 是 `payment_url`，微信是 `prepay_id`）；
 * 网关回调经插件**验签通过**才置为 `paid` —— 没有验签就永远停在 pending。
 *
 * 提现走**人工打款**：`pending → approved / rejected → paid`，置 `paid` 必须带打款流水号。
 */

import http from '../request'
import type {PageQuery} from '../types'

export type TipStatus = 'pending' | 'paid' | 'failed' | 'refunded'
export type WithdrawalStatus = 'pending' | 'approved' | 'rejected' | 'paid'

export interface TipConfig {
  min_amount: number
  max_amount: number
  /** 预设金额（分） */
  presets: number[]
  min_withdraw: number
  /** 提现手续费率（如 0.06） */
  withdraw_fee_rate: number
  withdraw_methods: string[]
}

export interface TipItem {
  id: number
  user_id: number
  username?: string | null
  author_id: number
  author_name?: string | null
  article_id?: number | null
  /** 分 */
  amount: number
  amount_yuan: number
  message?: string | null
  status: TipStatus | string
  order_no?: string | null
  provider?: string | null
  transaction_id?: string | null
  paid_at?: string | null
  created_at?: string | null
}

export interface TipCreatePayload {
  author_id: number
  amount: number
  article_id?: number | null
  message?: string | null
  provider?: string | null
  return_url?: string | null
  cancel_url?: string | null
  notify_url?: string | null
}

/** 支付插件返回的调起参数（结构由插件决定：`payment_url` / `prepay_id` …） */
export interface PaymentLaunchInfo {
  success?: boolean
  provider?: string
  payment_url?: string
  prepay_id?: string
  transaction_id?: string
  error?: string

  [key: string]: unknown
}

export interface TipCreateResult {
  tip: TipItem
  payment: PaymentLaunchInfo
}

export interface TipRankingItem {
  rank: number
  author_id: number
  username?: string | null
  /** 累计收到（分） */
  total: number
  count: number
}

export interface TipEarnings {
  total_received: number
  settled: number
  pending: number
  withdrawn: number
  /** 可提现额（已结算 − 已占用） */
  available: number
}

export interface WithdrawalItem {
  id: number
  user_id: number
  username?: string | null
  amount: number
  /** 手续费（分） */
  fee: number
  actual_amount: number
  method?: string | null
  account_name?: string | null
  status: WithdrawalStatus | string
  reviewed_at?: string | null
  review_comment?: string | null
  paid_at?: string | null
  transaction_id?: string | null
  created_at?: string | null
}

export interface TipStats {
  tip_count: number
  paid_count: number
  total_amount: number
  paid_amount: number
  withdrawal_count: number
  withdrawal_pending: number
  withdrawal_paid: number
  top_authors: TipRankingItem[]
}

export interface WithdrawalQuery extends PageQuery {
  status?: string
}

export const tippingApi = {
  /** 打赏配置（公开；金额范围 / 预设 / 提现门槛与费率） */
  config: () => http.get<TipConfig>('/commerce/tipping/config'),

  /** 打赏排行（公开，只统计已支付） */
  ranking: (limit = 20) => http.get<TipRankingItem[]>('/commerce/tipping/ranking', {limit}),

  /** 某文章的打赏（公开，只列已支付） */
  articleTips: (articleId: number, params?: PageQuery) =>
    http.page<TipItem>(`/commerce/tipping/article/${articleId}`, params),

  /** 发起打赏（仅认证；返回 `{tip, payment}`） */
  tip: (data: TipCreatePayload) => http.post<TipCreateResult>('/commerce/tipping/tip', data),

  /** 我打赏出去的（仅认证） */
  mine: (params?: PageQuery) => http.page<TipItem>('/commerce/tipping/mine', params),

  /** 我收到的打赏（仅认证） */
  received: (params?: PageQuery) => http.page<TipItem>('/commerce/tipping/received', params),

  /** 我的收益概要（仅认证） */
  earnings: () => http.get<TipEarnings>('/commerce/tipping/earnings'),

  /** 申请提现（仅认证） */
  withdraw: (data: { amount: number; method: string; account: string; account_name: string }) =>
    http.post<WithdrawalItem>('/commerce/tipping/withdraw', data),

  /** 我的提现记录（仅认证） */
  myWithdrawals: (params?: PageQuery) =>
    http.page<WithdrawalItem>('/commerce/tipping/withdrawals/mine', params),

  /** 提现列表（管理员） */
  withdrawals: (params?: WithdrawalQuery) =>
    http.page<WithdrawalItem>('/commerce/tipping/withdrawals', params),

  /** 审核提现（管理员；`approve=false` 即驳回） */
  reviewWithdrawal: (id: number, approve: boolean, comment?: string) =>
    http.post<WithdrawalItem>(`/commerce/tipping/withdrawals/${id}/review`, {
      approve,
      comment: comment ?? null,
    }),

  /** 标记已打款（管理员；**必须**带打款流水号） */
  markPaid: (id: number, transactionId: string, comment?: string) =>
    http.post<WithdrawalItem>(`/commerce/tipping/withdrawals/${id}/paid`, {
      transaction_id: transactionId,
      comment: comment ?? null,
    }),

  /** 打赏统计（管理员） */
  stats: () => http.get<TipStats>('/commerce/tipping/stats'),
}
