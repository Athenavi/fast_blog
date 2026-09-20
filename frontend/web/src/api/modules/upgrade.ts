/** 在线升级接口（/api/v3/ops/upgrade，ops 域） */

import http from '../request'

/** 升级历史条目 */
export interface UpgradeHistoryItem {
  target_version: string
  /** success / failed / running / pending 等，页面按前缀映射 tag */
  status: string
  started_at: string | null
  finished_at: string | null
  message: string | null
}

/** GET /ops/upgrade/status → 当前版本与升级状态 */
export interface UpgradeStatus {
  current_version: string
  app_path: string
  /** 有升级任务进行中（此时检查/升级按钮禁用） */
  in_progress: boolean
  history: Array<UpgradeHistoryItem>
}

/** POST /ops/upgrade/check → 检查更新结果 */
export interface UpgradeCheckResult {
  current_version: string
  latest_version: string | null
  has_update: boolean
  /** remote=远程源 / local_releases=本地发布包 / none=无可用来源 */
  source: 'remote' | 'local_releases' | 'none'
  detail: string
}

/** apply 返回的前置检查项（干跑形态） */
export interface UpgradeApplyCheck {
  name: string
  passed: boolean
  detail: string
}

/**
 * POST /ops/upgrade/apply → 后端二选一实现，字段全可选以同时覆盖两种形状：
 *  - 立即执行形态：{ started, message }
 *  - 干跑形态：{ dry_run, ready, checks }
 */
export interface UpgradeApplyResult {
  started?: boolean
  message?: string
  dry_run?: boolean
  ready?: boolean
  checks?: Array<UpgradeApplyCheck>
}

export const upgradeApi = {
  status: () => http.get<UpgradeStatus>('/ops/upgrade/status'),

  check: () => http.post<UpgradeCheckResult>('/ops/upgrade/check'),

  apply: () => http.post<UpgradeApplyResult>('/ops/upgrade/apply'),
}
