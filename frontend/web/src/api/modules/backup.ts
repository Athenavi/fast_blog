/** 备份接口（/api/v3/ops/backup） */

import http from '../request'

export interface BackupItem {
  filename?: string
  path?: string
  type?: string
  backup_type?: string
  size?: number
  size_human?: string
  created_at?: string
  status?: string

  [key: string]: unknown
}

export interface BackupSchedule {
  enabled?: boolean
  schedule?: string | null
  retention_days?: number | null
  compress?: boolean | null
  backup_database?: boolean | null
  backup_files?: boolean | null

  [key: string]: unknown
}

/** 恢复链上的一环（基准在前、目标在后） */
export interface BackupChainItem {
  filename?: string | null
  type?: string | null
  created_at?: string | null
  tables?: string[]
  size_human?: string | null
}

export interface BackupChainPlan {
  length: number
  items: BackupChainItem[]
}

/** 校验结果里的一项检查 */
export interface BackupVerifyCheck {
  name: string
  passed: boolean
  detail: string
}

export interface BackupVerifyResult {
  valid: boolean
  path?: string | null
  kind?: string | null
  size?: number | null
  size_human?: string | null
  checksum?: { expected?: string; actual?: string; matched?: boolean } | null
  checks: BackupVerifyCheck[]
}

/** 增量 / 差异备份结果（`skipped` 表示没有检测到变化） */
export interface BackupIncrementalResult {
  success?: boolean
  skipped?: boolean
  message?: string
  changed_tables?: string[]
  backup_path?: string | null

  [key: string]: unknown
}

/** 云存储配置（密钥只写不读，响应只有 has_secret） */
export interface BackupCloudConfig {
  provider?: string | null
  bucket?: string | null
  region?: string | null
  endpoint?: string | null
  prefix?: string | null
  access_key_id?: string | null
  has_secret: boolean
  updated_at?: string | null

  [key: string]: unknown
}

export interface BackupCloudPayload {
  provider?: string
  bucket?: string
  region?: string
  endpoint?: string
  prefix?: string
  access_key_id?: string
  secret?: string
}

/** 云上传结果 */
export interface BackupCloudUploadResult {
  provider: string
  bucket?: string | null
  key?: string | null
  size?: number | null
  endpoint?: string | null
  location?: string | null

  [key: string]: unknown
}

export const backupApi = {
  list: (params?: { backup_type?: string; limit?: number }) =>
    http.page<BackupItem>('/ops/backup', params),
  createDatabase: (backup_type = 'full') =>
    http.post<Record<string, unknown>>('/ops/backup/database', undefined, {backup_type}),
  createFiles: () => http.post<Record<string, unknown>>('/ops/backup/files'),
  createFull: () => http.post<Record<string, unknown>>('/ops/backup/full'),
  /** 增量 / 差异备份：只导出相对基准变化的表的数据（base_path 缺省取最近一次全量） */
  createIncremental: (payload?: {
    base_path?: string | null
    tables?: string[] | null
    differential?: boolean
  }) => http.post<BackupIncrementalResult>('/ops/backup/incremental', payload ?? {}),
  /** 恢复链预览：增量要挂在哪些备份后面才能还原 */
  chain: (backup_path: string) =>
    http.get<BackupChainPlan>('/ops/backup/chain', {backup_path}),
  /** 按恢复链还原（基准 → 增量依次应用） */
  restoreChain: (backup_path: string, truncate = true) =>
    http.post<Record<string, unknown>>('/ops/backup/restore-chain', {backup_path, truncate}),
  /** 校验备份完整性（真读文件：sha256 / 归档可读 / pg_restore --list） */
  verify: (backup_path: string) =>
    http.post<BackupVerifyResult>('/ops/backup/verify', {backup_path}),
  /** 云存储配置（密钥不回传，只有 has_secret） */
  cloud: () => http.get<BackupCloudConfig>('/ops/backup/cloud'),
  saveCloud: (data: BackupCloudPayload) =>
    http.put<BackupCloudConfig>('/ops/backup/cloud', data),
  /** 把某个备份上传到云存储（真实调用 S3 / OSS） */
  uploadToCloud: (backup_path: string) =>
    http.post<BackupCloudUploadResult>('/ops/backup/cloud/upload', {backup_path}),
  restore: (backup_file: string, backup_type = 'database') =>
    http.post<Record<string, unknown>>('/ops/backup/restore', {backup_file, backup_type}),
  remove: (backup_path: string) => http.delete<{ deleted: boolean }>('/ops/backup', {backup_path}),
  cleanup: (days_to_keep?: number) =>
    http.post<Record<string, unknown>>('/ops/backup/cleanup', undefined, {days_to_keep}),
  stats: () => http.get<Record<string, unknown>>('/ops/backup/stats'),
  schedule: () => http.get<BackupSchedule>('/ops/backup/schedule'),
  updateSchedule: (data: Partial<BackupSchedule>) =>
    http.put<BackupSchedule>('/ops/backup/schedule', data),
}
