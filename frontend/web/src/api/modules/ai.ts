/** AI 能力接口（/api/v3/ai/*，ai 域：config + workflow）
 *
 * 两种协议：openai 兼容系（deepseek/qwen/ollama/azure…）与 anthropic；
 * api_url / model / api_version / extra_headers / max_tokens 都可自定义（自建网关、代理、内网）。
 * api_key 只写不读：响应只有 has_api_key，且落库前按「用户密码 + SECRET_KEY」派生密钥加密。
 */

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
  api_version?: string | null
  extra_headers?: Record<string, unknown> | null
  max_tokens: number
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
  api_version?: string | null
  extra_headers?: Record<string, unknown> | null
  max_tokens?: number
  is_active?: boolean
  sort_order?: number
}

/** 连接测试结果（后端真实调用一次模型） */
export interface AiConfigTestResult {
  ok: boolean
  provider?: string | null
  protocol?: string | null
  model?: string | null
  reply?: string | null
  latency_ms?: number | null
  usage?: Record<string, number>
}

export interface AiProviderItem {
  provider: string
  protocol: string
}

export interface AiTaskTypeItem {
  task_type: string
  label: string
  has_system_prompt: boolean
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

export interface AiWorkflowExecutePayload {
  config_id: number
  task_type: string
  input: string
  user_id?: number
  target_lang?: string
  max_tokens?: number
}

export const aiApi = {
  // 配置
  listConfigs: (params?: AiConfigQuery) => http.page<AiConfigItem>('/ai/config', params),

  /** 支持的 provider 与协议（前端下拉） */
  listProviders: () => http.get<AiProviderItem[]>('/ai/config/providers'),

  createConfig: (data: AiConfigPayload) => http.post<AiConfigItem>('/ai/config', data),

  updateConfig: (id: number, data: Partial<AiConfigPayload>) =>
    http.put<AiConfigItem>(`/ai/config/${id}`, data),

  /** 测试连接：后端会真实调用一次模型（会消耗少量 token） */
  testConfig: (id: number) => http.post<AiConfigTestResult>(`/ai/config/${id}/test`),

  removeConfig: (id: number) => http.delete<null>(`/ai/config/${id}`),

  // 工作流记录 + 执行
  listWorkflows: (params?: AiWorkflowQuery) => http.page<AiWorkflowItem>('/ai/workflow', params),

  /** 可用任务类型（与后端执行引擎同一份定义） */
  listTaskTypes: () => http.get<AiTaskTypeItem[]>('/ai/workflow/task-types'),

  /** 发起任务：真实调用模型 */
  executeWorkflow: (data: AiWorkflowExecutePayload) =>
    http.post<AiWorkflowItem>('/ai/workflow/execute', data),

  /** 用原输入重跑 */
  retryWorkflow: (id: number) => http.post<AiWorkflowItem>(`/ai/workflow/${id}/retry`),

  removeWorkflow: (id: number) => http.delete<null>(`/ai/workflow/${id}`),
}
