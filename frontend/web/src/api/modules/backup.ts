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

export const backupApi = {
  list: (params?: { backup_type?: string; limit?: number }) =>
    http.page<BackupItem>('/ops/backup', params),
  createDatabase: (backup_type = 'full') =>
    http.post<Record<string, unknown>>('/ops/backup/database', undefined, {backup_type}),
  createFiles: () => http.post<Record<string, unknown>>('/ops/backup/files'),
  createFull: () => http.post<Record<string, unknown>>('/ops/backup/full'),
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
