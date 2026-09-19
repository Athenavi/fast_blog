/** AI 能力接口（/api/v3/ai/*，ai 域：config + workflow） */

import http from '../request'
import type {PageQuery} from '../types'

export interface AiConfigItem {
  id: number
  user_id: number
  name?: string | null
  api_url?: string | null
  has_api_key: boolean
  model?: string | null
  provider?: string | null
  is_active: boolean
  sort_order: number
  created_at?: string | null
  updated_at?: string | null
}

export interface AiConfigQuery extends PageQuery {
  user_id?: number
  provider?: string
  is_active?: boolean
}

export interface AiConfigPayload {
  user_id: number
  name: string
  api_url: string
  api_key?: string
  model: string
  provider?: string
  is_active?: boolean
  sort_order?: number
}

export interface AiWorkflowItem {
  id: number
  user_id?: number | null
  task_type?: string | null
  input_data?: Record<string, unknown> | null
  output_data?: Record<string, unknown> | null
  model_used?: string | null
  tokens_used: number
  status: string
  error_message?: string | null
  created_at?: string | null
  completed_at?: string | null
}

export interface AiWorkflowQuery extends PageQuery {
  user_id?: number
  task_type?: string
  status?: string
}

export const aiApi = {
  // 配置
  listConfigs: (params?: AiConfigQuery) => http.page<AiConfigItem>('/ai/config', params),

  createConfig: (data: AiConfigPayload) => http.post<AiConfigItem>('/ai/config', data),

  updateConfig: (id: number, data: Partial<AiConfigPayload>) =>
    http.put<AiConfigItem>(`/ai/config/${id}`, data),

  removeConfig: (id: number) => http.delete<null>(`/ai/config/${id}`),

  // 工作流记录
  listWorkflows: (params?: AiWorkflowQuery) => http.page<AiWorkflowItem>('/ai/workflow', params),

  removeWorkflow: (id: number) => http.delete<null>(`/ai/workflow/${id}`),
}
