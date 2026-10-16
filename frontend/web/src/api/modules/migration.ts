/** 数据迁移接口（/api/v3/ops/migration，ops 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface MigrationTaskItem {
  id: number
  task_name?: string | null
  source_platform?: string | null
  status?: string | null
  config?: Record<string, unknown> | null
  progress: number
  total_items: number
  migrated_items: number
  error_message?: string | null
  started_at?: string | null
  completed_at?: string | null
  created_by?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export interface MigrationTaskPayload {
  task_name: string
  source_platform: string
  config?: Record<string, unknown> | null
  total_items?: number
}

export interface MigrationLogItem {
  id: number
  task_id: number
  log_level?: string | null
  message?: string | null
  item_type?: string | null
  item_id?: number | null
  created_at?: string | null
}

export const migrationApi = {
  list: (params?: PageQuery & { status?: string }) => http.page<MigrationTaskItem>('/ops/migration', params),

  create: (data: MigrationTaskPayload) => http.post<MigrationTaskItem>('/ops/migration', data),

  update: (id: number, data: Partial<MigrationTaskPayload>) =>
    http.put<MigrationTaskItem>(`/ops/migration/${id}`, data),

  remove: (id: number) => http.delete<null>(`/ops/migration/${id}`),

  start: (id: number) => http.post<MigrationTaskItem>(`/ops/migration/${id}/start`),

  cancel: (id: number) => http.post<MigrationTaskItem>(`/ops/migration/${id}/cancel`),

  logs: (taskId: number, params?: PageQuery) =>
    http.page<MigrationLogItem>(`/ops/migration/${taskId}/log`, params),
}
