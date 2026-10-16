/** 部署脚本与执行日志接口（/api/v3/ops/deployment，ops 域）
 *
 * 契约要点：
 *  - `parameters` 库列是 JSON 字符串，出参已由后端还原为对象 / 数组；
 *  - **本期没有任何执行入口**（真实拉起脚本属高危动作，列为二期），
 *    日志只读 + 删除，脚本只做档案管理。
 */

import http from '../request'
import type {PageQuery} from '../types'

export interface DeploymentScriptItem {
  id: number
  name?: string | null
  script_type?: string | null
  content: string
  version?: string | null
  description?: string | null
  parameters?: Record<string, unknown> | unknown[] | null
  is_active: boolean
  created_by?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export interface DeploymentScriptQuery extends PageQuery {
  keyword?: string
  script_type?: string
}

export interface DeploymentScriptPayload {
  content?: string
  name?: string | null
  script_type?: string | null
  version?: string | null
  description?: string | null
  parameters?: Record<string, unknown> | unknown[] | null
  is_active?: boolean
}

export interface DeploymentLogItem {
  id: number
  script_id?: number | null
  user_id?: number | null
  status?: string | null
  output?: string | null
  error_message?: string | null
  started_at?: string | null
  completed_at?: string | null
  created_at?: string | null
}

export interface DeploymentLogQuery extends PageQuery {
  script_id?: number
  status?: string
}

export const deploymentApi = {
  listScripts: (params?: DeploymentScriptQuery) =>
    http.page<DeploymentScriptItem>('/ops/deployment/script', params),

  createScript: (data: DeploymentScriptPayload) =>
    http.post<DeploymentScriptItem>('/ops/deployment/script', data),

  updateScript: (id: number, data: Partial<DeploymentScriptPayload>) =>
    http.put<DeploymentScriptItem>(`/ops/deployment/script/${id}`, data),

  removeScript: (id: number) => http.delete<null>(`/ops/deployment/script/${id}`),

  listLogs: (params?: DeploymentLogQuery) =>
    http.page<DeploymentLogItem>('/ops/deployment/log', params),

  getLog: (id: number) => http.get<DeploymentLogItem>(`/ops/deployment/log/${id}`),

  removeLog: (id: number) => http.delete<null>(`/ops/deployment/log/${id}`),
}
