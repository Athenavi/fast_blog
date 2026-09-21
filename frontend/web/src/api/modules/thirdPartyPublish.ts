/**
 * 多平台发布接口（`/api/v3/content/third-party-publish`，content 域）
 *
 * **底座**：渠道配置（凭据加密、永不回传）+ 发布任务 + 尝试记录 + 手动重试。
 * "往某个平台真发内容"由后端适配器决定：`platforms()` 返回**已接入**的平台清单，
 * 当前可能为空 —— 页面据此如实提示"平台适配器尚未接入"，不伪造可用平台。
 */

import http from '../request'
import type {PageQuery} from '../types'

/** 已接入的平台适配器 */
export interface PublishPlatform {
  platform: string
  display_name: string
}

/** 发布渠道 */
export interface PublishChannelItem {
  id: number
  name: string
  platform: string
  endpoint?: string | null
  is_active: boolean
  /** 是否已配置凭据（密文永不回传） */
  has_credentials: boolean
  /** 该平台是否已注册适配器（false = 底座就绪、适配器待接入） */
  adapter_ready: boolean
  created_by?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export interface PublishChannelPayload {
  name: string
  platform: string
  endpoint?: string | null
  /** 凭据字典；更新时留空表示保持原值 */
  credentials?: Record<string, unknown>
  is_active?: boolean
}

export interface PublishChannelQuery extends PageQuery {
  platform?: string
  is_active?: boolean
}

export interface PublishChannelVerifyResult {
  success: boolean
  message?: string | null
  channel_id: number
  platform: string
}

/** 发布任务状态 */
export type PublishTaskStatus = 'pending' | 'publishing' | 'success' | 'failed'

/** 发布任务 */
export interface PublishTaskItem {
  id: number
  article_id: number
  channel_id: number
  status: PublishTaskStatus | string
  attempts: number
  last_error?: string | null
  external_id?: string | null
  external_url?: string | null
  created_by?: number | null
  started_at?: string | null
  finished_at?: string | null
  created_at?: string | null
  updated_at?: string | null
  /** 列表展示用（后端填充） */
  article_title?: string | null
  channel_name?: string | null
  channel_platform?: string | null
}

/** 任务详情：额外带载荷快照 + 最近日志 */
export interface PublishTaskDetail extends PublishTaskItem {
  payload?: Record<string, unknown> | null
  logs?: PublishLogItem[]
}

/** 一次发布尝试的记录 */
export interface PublishLogItem {
  id: number
  task_id: number
  status: string
  message?: string | null
  duration_ms?: number | null
  created_at?: string | null
}

export interface PublishTaskQuery extends PageQuery {
  article_id?: number
  channel_id?: number
  status?: string
}

const BASE = '/content/third-party-publish'

export const thirdPartyPublishApi = {
  /** 已接入的平台适配器（当前可能为空列表） */
  platforms: () => http.get<{ items: PublishPlatform[]; total: number }>(`${BASE}/platform`),

  // ---- 渠道 ----
  listChannels: (params?: PublishChannelQuery) =>
    http.page<PublishChannelItem>(`${BASE}/channel`, params),

  createChannel: (data: PublishChannelPayload) =>
    http.post<PublishChannelItem>(`${BASE}/channel`, data),

  /** 更新渠道（凭据留空 = 保持原值） */
  updateChannel: (id: number, data: Partial<PublishChannelPayload>) =>
    http.put<PublishChannelItem>(`${BASE}/channel/${id}`, data),

  removeChannel: (id: number) => http.delete<null>(`${BASE}/channel/${id}`),

  /** 凭据 / 连通性自检；平台适配器未接入时后端返回 400 并说明原因 */
  verifyChannel: (id: number) =>
    http.post<PublishChannelVerifyResult>(`${BASE}/channel/${id}/verify`),

  // ---- 任务 ----
  listTasks: (params?: PublishTaskQuery) => http.page<PublishTaskItem>(`${BASE}/task`, params),

  /** 创建发布任务（后端创建后立即尝试执行；同文章+渠道已有任务时复用） */
  createTask: (data: { article_id: number; channel_id: number }) =>
    http.post<PublishTaskDetail>(`${BASE}/task`, data),

  getTask: (id: number) => http.get<PublishTaskDetail>(`${BASE}/task/${id}`),

  removeTask: (id: number) => http.delete<null>(`${BASE}/task/${id}`),

  /** 手动重试（复用创建时冻结的载荷快照） */
  retryTask: (id: number) => http.post<PublishTaskDetail>(`${BASE}/task/${id}/retry`),

  listLogs: (id: number, params?: PageQuery) =>
    http.page<PublishLogItem>(`${BASE}/task/${id}/log`, params),
}
