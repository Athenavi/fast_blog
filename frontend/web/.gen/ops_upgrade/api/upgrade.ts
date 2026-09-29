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

/** GET /ops/upgrade/settings → 升级设置（重启命令会被服务端真实执行） */
export interface UpgradeSettings {
  restart_command: string | null
  configured: boolean
}

/** PUT /ops/upgrade/settings 请求体：升级后重启命令；留空表示不自动重启 */
export interface UpgradeSettingsPayload {
  restart_command?: string | null
}

/** 版本明细里的字典（来自 version.txt：release / database / author 及前后端版本） */
export type UpgradeVersionInfo = Record<string, string>

/** GET /ops/upgrade/versions → 发布信息 + 数据库迁移 + 前后端版本 */
export interface UpgradeVersions {
  current_version: string
  release: UpgradeVersionInfo
  database: UpgradeVersionInfo
  author: UpgradeVersionInfo
  backend: UpgradeVersionInfo
  frontend: UpgradeVersionInfo
}

/** GET /ops/upgrade/paths → 路径策略（会替换哪些代码 / 绝不触碰哪些数据） */
export interface UpgradePathPolicy {
  allowed_prefixes: string[]
  allowed_files: string[]
  protected_dirs: string[]
  protected_files: string[]
  project_root: string
  releases_dir: string
  backup_root: string
}

/** 本地更新包（releases/update_*.zip） */
export interface UpgradePackageItem {
  filename: string
  version: string
  size: number
  modified_at: string | null
  build_time: string | null
  /** 是否存在同名 .sha256（有则执行时会做摘要校验） */
  sha256_file: boolean
  metadata: Record<string, unknown>
}

/** GET /ops/upgrade/packages → 本地更新包清单 */
export interface UpgradePackages {
  items: UpgradePackageItem[]
  total: number
  releases_dir: string
}

/** POST /ops/upgrade/plan → 执行预演：包里将被替换 / 被跳过的文件 */
export interface UpgradePlan {
  target_version: string
  package: string
  package_detail: string
  will_replace_count: number
  skipped_count: number
  will_replace: string[]
  skipped: string[]
  /** 既会替换又命中保护清单的路径（理论上应为空，非空要警惕） */
  collisions_with_protected: string[]
}

/** 真实执行 / 回滚的单个步骤 */
export interface UpgradeStep {
  step: string
  ok: boolean
  detail: string
}

/** POST /ops/upgrade/execute 请求体（**真实升级**，confirm 必须为 true 才会执行） */
export interface UpgradeExecutePayload {
  target_version: string
  confirm: boolean
  /** 替换后执行 alembic upgrade head */
  run_migration?: boolean
  /** 替换后清理 storage/cache */
  clear_cache?: boolean
  /** 可选：ops/supervisor 里登记的进程名，给了就走「停服 → 替换 → 起服」编排 */
  stop_service?: string | null
}

/**
 * POST /ops/upgrade/execute 与 /rollback 的响应，字段全可选以覆盖两种形状：
 *  - 后台执行（默认）：{ started, target_version, in_progress, need_restart, detail }；
 *  - 完成 / 同步：{ dry_run, ok, from_version, target_version, backup_id,
 *      files_replaced, skipped, need_restart, restart_detail, steps }。
 */
export interface UpgradeExecuteResult {
  started?: boolean
  dry_run?: boolean
  ok?: boolean
  in_progress?: boolean
  from_version?: string
  target_version?: string
  backup_id?: string | null
  files_replaced?: number
  skipped?: number
  need_restart?: boolean
  restart_detail?: string | null
  /** 后台执行时的提示文案 */
  detail?: string
  steps?: UpgradeStep[]
}

/** 本地升级备份（backups/update_backups/<id>/，含 manifest.json） */
export interface UpgradeBackupItem {
  backup_id: string
  from_version?: string | null
  target_version?: string | null
  created_at?: string | null
  files: number
  path: string
}

/** GET /ops/upgrade/backups → 升级备份列表 */
export interface UpgradeBackupList {
  items: UpgradeBackupItem[]
  total: number
}

/** POST /ops/upgrade/rollback 请求体（confirm 必须为 true） */
export interface UpgradeRollbackPayload {
  backup_id: string
  confirm: boolean
}

/** 触发浏览器下载：临时 `<a download>` + objectURL（用后释放） */
function triggerDownload(blob: Blob, filename: string): void {
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(href)
}

/** 从 `content-disposition` 解析文件名（优先 RFC 5987 的 `filename*`，回退 `filename`） */
function parseFilename(disposition: unknown): string | null {
  if (!disposition) return null
  const text = String(disposition)
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(text)
  if (encoded && encoded[1]) {
    try {
      return decodeURIComponent(encoded[1].trim())
    } catch {
      /* 解码失败则回退到 filename */
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(text)
  return plain && plain[1] ? plain[1].trim() : null
}

/**
 * GET 二进制下载：用同一 axios 实例（自动注入 Bearer token）以 blob 拉取，
 * 文件名从响应头解析，解析失败回退到 `fallbackName`。下载端点返回的是
 * FileResponse（不是 JSON 信封），因此用 `http.raw` 绕开 code===200 的解析。
 */
async function downloadFile(url: string, fallbackName: string): Promise<void> {
  const resp = await http.raw.get<Blob>(url, {responseType: 'blob'})
  const filename = parseFilename(resp.headers?.['content-disposition']) ?? fallbackName
  if (import.meta.client) triggerDownload(resp.data, filename)
}

export const upgradeApi = {
  status: () => http.get<UpgradeStatus>('/ops/upgrade/status'),

  check: () => http.post<UpgradeCheckResult>('/ops/upgrade/check'),

  apply: () => http.post<UpgradeApplyResult>('/ops/upgrade/apply'),

  /** 读取升级设置（重启命令） */
  getSettings: () => http.get<UpgradeSettings>('/ops/upgrade/settings'),

  /** 保存升级设置（**该重启命令会被服务端真实执行**） */
  saveSettings: (data: UpgradeSettingsPayload) =>
    http.put<UpgradeSettings>('/ops/upgrade/settings', data),

  /** 版本明细（发布信息 / 数据库迁移 / 前后端版本） */
  versions: () => http.get<UpgradeVersions>('/ops/upgrade/versions'),

  /** 路径策略（会替换哪些代码路径 / 绝不触碰哪些数据路径） */
  paths: () => http.get<UpgradePathPolicy>('/ops/upgrade/paths'),

  /** 本地升级备份列表（limit 1..100，默认 20） */
  backups: (limit = 20) => http.get<UpgradeBackupList>('/ops/upgrade/backups', {limit}),

  /** 本地更新包清单（releases/update_*.zip） */
  packages: () => http.get<UpgradePackages>('/ops/upgrade/packages'),

  /** 下载本地更新包（FileResponse，非 JSON 信封，走 blob → 浏览器下载） */
  downloadPackage: (filename: string) =>
    downloadFile(`/ops/upgrade/packages/${encodeURIComponent(filename)}/download`, filename),

  /** 执行预演（只读：列出将替换 / 将跳过的文件，不改任何文件） */
  plan: (target_version: string) =>
    http.post<UpgradePlan>('/ops/upgrade/plan', {target_version}),

  /** **真实升级**（改写代码文件 + 迁移 + 清缓存 + 可选重启；必须 confirm=true） */
  execute: (payload: UpgradeExecutePayload) =>
    http.post<UpgradeExecuteResult>('/ops/upgrade/execute', payload),

  /** 按备份回滚代码文件（必须 confirm=true） */
  rollback: (payload: UpgradeRollbackPayload) =>
    http.post<UpgradeExecuteResult>('/ops/upgrade/rollback', payload),
}
