/** 积分接口（`/api/v3/gamification/points`，gamification 域）
 *
 * 「我的」相关端点**仅需认证**；排行榜 / 积分规则 / 兑换项**公开**；
 * `stats` / `grant` / `deduct` / `rule` 需要权限码 `module_gamification:points:{view,edit}`。
 *
 * 注意：v3 **没有** v2 的 `record-action`（前端自报动作加分）—— 那是刷分口子。
 * 本期只有**每日签到**（幂等）与管理端加减分。
 */

import http from '../request'
import type {PageQuery} from '../types'

export interface PointsAccount {
  user_id: number
  balance: number
  total_earned: number
  total_spent: number
  last_checkin_at?: string | null
  /** 今天是否已签到 */
  checked_in_today: boolean
  updated_at?: string | null
}

export interface PointsTransaction {
  id: number
  user_id?: number | null
  /** 正数为获得，负数为消耗 */
  amount?: number | null
  balance_after?: number | null
  action?: string | null
  description?: string | null
  reference_id?: number | null
  reference_type?: string | null
  created_at?: string | null
}

export interface PointsRule {
  id: number
  action?: string | null
  points?: number | null
  description?: string | null
  /** 每日最多计入次数（0 = 不限） */
  daily_limit: number
  is_active: boolean
  sort_order: number
}

export interface ExchangeRule {
  action: string
  /** 需要消耗的积分（正数） */
  cost: number
  description?: string | null
  is_active: boolean
}

export interface LeaderboardItem {
  rank: number
  user_id: number
  username?: string | null
  balance: number
}

export interface PointsStats {
  total_accounts: number
  total_balance: number
  total_earned: number
  total_spent: number
  transaction_count: number
  active_rules: number
  top_holders: LeaderboardItem[]
}

/** 签到结果 = 账户 + 本次加分 */
export interface CheckinResult extends PointsAccount {
  awarded: number
}

/** 加分 / 扣分结果：账户 + 那条流水 */
export interface PointsLedger {
  account: PointsAccount
  transaction: PointsTransaction
}

/** 兑换结果：账户 + 流水 + 真实开通的订阅 */
export interface ExchangeResult extends PointsLedger {
  subscription: Record<string, unknown>
}

export const pointsApi = {
  /** 我的积分账户（仅认证） */
  mine: () => http.get<PointsAccount>('/gamification/points/mine'),

  /** 我的积分流水（仅认证，分页） */
  history: (params?: PageQuery) => http.page<PointsTransaction>('/gamification/points/history', params),

  /** 每日签到（仅认证；幂等，今天已签到会报「今天已经签到过了」） */
  checkin: () => http.post<CheckinResult>('/gamification/points/checkin'),

  /** 积分兑换（仅认证；真实开通对应套餐） */
  exchange: (action: string, planId: number) =>
    http.post<ExchangeResult>('/gamification/points/exchange', {action, plan_id: planId}),

  /** 排行榜（公开） */
  leaderboard: (limit = 20) => http.get<LeaderboardItem[]>('/gamification/points/leaderboard', {limit}),

  /** 积分规则（公开） */
  rules: () => http.get<PointsRule[]>('/gamification/points/rules'),

  /** 兑换项（公开） */
  exchangeRules: () => http.get<ExchangeRule[]>('/gamification/points/exchange-rules'),

  /** 积分统计（管理员） */
  stats: () => http.get<PointsStats>('/gamification/points/stats'),

  /** 管理员加分 */
  grant: (userId: number, amount: number, reason?: string) =>
    http.post<PointsLedger>('/gamification/points/grant', {user_id: userId, amount, reason}),

  /** 管理员扣分 */
  deduct: (userId: number, amount: number, reason?: string) =>
    http.post<PointsLedger>('/gamification/points/deduct', {user_id: userId, amount, reason}),

  /** 更新积分规则（点数 / 说明 / 日上限 / 启停 / 排序） */
  updateRule: (
    ruleId: number,
    data: { points?: number; description?: string; daily_limit?: number; is_active?: boolean; sort_order?: number },
  ) => http.put<PointsRule>(`/gamification/points/rule/${ruleId}`, data),
}
