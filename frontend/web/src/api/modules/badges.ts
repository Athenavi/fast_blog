/** 勋章接口（`/api/v3/gamification/badge`，gamification 域）
 *
 * 「我的」/ 进度 / check-and-award **仅需认证**；available / categories / details **公开**；
 * `award` / `stats` 需要权限码 `module_gamification:badge:{view,edit}`。
 *
 * 进度里的 `current_value` 是**真实统计**（v2 的统计函数恒返回 0，所以进度永远是 0%）。
 */

import http from '../request'

export interface BadgeDefinition {
  id: number
  badge_key?: string | null
  name?: string | null
  description?: string | null
  category?: string | null
  icon?: string | null
  /** 获得时奖励的积分 */
  points_reward: number
  /** 条件类型（article_count / max_article_likes / follower_count / comment_count / like_received） */
  condition_type?: string | null
  condition_value: number
  /** 是否仅可手工授予（无统计源的条件一律为 true，不假装能自动判定） */
  is_manual: boolean
  is_active: boolean
  sort_order: number
}

export interface UserBadge {
  badge_key: string
  name?: string | null
  description?: string | null
  category?: string | null
  icon?: string | null
  points_reward: number
  awarded_at?: string | null
  awarded_by?: number | null
  /** 手工授予时：是否本来就已拥有（授予接口幂等） */
  already_awarded?: boolean
}

export interface BadgeProgress {
  badge_key: string
  name?: string | null
  description?: string | null
  category?: string | null
  condition_type?: string | null
  condition_value: number
  current_value: number
  achieved: boolean
  progress_percent: number
  awarded: boolean
}

export interface BadgeCheckResult {
  /** 本次新授予的 */
  awarded: UserBadge[]
  /** `is_manual` 被跳过（不自动授予）的 badge_key */
  skipped_manual: string[]
  /** 全部勋章的进度 */
  progress: BadgeProgress[]
}

export interface BadgeCategory {
  category: string
  count: number
}

export interface BadgeStats {
  total_definitions: number
  active_definitions: number
  total_awarded: number
  by_category: Array<{ category: string; count: number }>
  top_badges: Array<{ badge_key: string; name?: string | null; count: number }>
}

export const badgeApi = {
  /** 我的勋章（仅认证） */
  mine: () => http.get<UserBadge[]>('/gamification/badge/mine'),

  /** 全部可获得勋章（公开，可按分类过滤） */
  available: (category?: string) =>
    http.get<BadgeDefinition[]>('/gamification/badge/available', category ? {category} : undefined),

  /** 勋章分类（公开） */
  categories: () => http.get<BadgeCategory[]>('/gamification/badge/categories'),

  /** 勋章详情（公开） */
  details: (badgeKey: string) => http.get<BadgeDefinition>(`/gamification/badge/details/${badgeKey}`),

  /** 我的某个勋章进度（仅认证） */
  progress: (badgeKey: string) => http.get<BadgeProgress>(`/gamification/badge/progress/${badgeKey}`),

  /** 检查并授予（仅认证；幂等，is_manual 的不自动授予） */
  checkAndAward: () => http.post<BadgeCheckResult>('/gamification/badge/check-and-award'),

  /** 手工授予（管理员） */
  award: (userId: number, badgeKey: string) =>
    http.post<UserBadge>('/gamification/badge/award', {user_id: userId, badge_key: badgeKey}),

  /** 勋章统计（管理员） */
  stats: () => http.get<BadgeStats>('/gamification/badge/stats'),
}
