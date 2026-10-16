/** 跳转规则接口（/api/v3/content/redirect） */

import http from '../request'
import type {PageQuery} from '../types'

/** 规则行（对应后端 service._out） */
export interface RedirectItem {
  id: number
  from_path: string
  to_path: string
  status_code: number
  is_active: boolean
  hits: number
  source: string | null
  source_reference: string | null
  notes: string | null
  created_by: number | null
  created_at: string | null
  updated_at: string | null
}

/** 新建入参（对应后端 schema.RedirectCreate） */
export interface RedirectCreatePayload {
  from_path: string
  to_path: string
  status_code?: number
  is_active?: boolean
  notes?: string | null
}

/** 更新入参（对应后端 schema.RedirectUpdate，字段全可选） */
export interface RedirectUpdatePayload {
  from_path?: string
  to_path?: string
  status_code?: number
  is_active?: boolean
  notes?: string | null
}

/** 批量导入入参（对应后端 schema.RedirectBatchRequest） */
export interface RedirectBatchPayload {
  items: RedirectCreatePayload[]
  overwrite?: boolean
}

/** 批量导入结果（对应后端 service.bulk_import 返回） */
export interface RedirectBatchResult {
  created: number
  updated: number
  skipped: number
}

/** 统计（对应后端 service.stats 返回） */
export interface RedirectStats {
  total: number
  active: number
  inactive: number
  total_hits: number
  by_source: Record<string, number>
  top_hits: Array<{ from_path: string; to_path: string; hits: number }>
}

/** 路径解析结果（对应后端 service.resolve_path 返回） */
export interface RedirectResolveResult {
  matched: boolean
  from_path: string
  to_path: string | null
  status_code: number | null
  hits: number
}

/** 列表查询参数 */
export interface RedirectQuery extends PageQuery {
  keyword?: string
  is_active?: boolean
  source?: string
}

export const redirectApi = {
  /** 列表（分页）。后端 GET /content/redirect */
  list: (params?: RedirectQuery) => http.page<RedirectItem>('/content/redirect', params),
  /** 详情。后端 GET /content/redirect/{id} */
  detail: (id: number) => http.get<RedirectItem>(`/content/redirect/${id}`),
  /** 新建。后端 POST /content/redirect */
  create: (payload: RedirectCreatePayload) => http.post<RedirectItem>('/content/redirect', payload),
  /** 更新。后端 PUT /content/redirect/{id} */
  update: (id: number, payload: RedirectUpdatePayload) =>
    http.put<RedirectItem>(`/content/redirect/${id}`, payload),
  /** 删除。后端 DELETE /content/redirect/{id} */
  remove: (id: number) => http.delete<null>(`/content/redirect/${id}`),
  /** 批量导入。后端 POST /content/redirect/bulk */
  bulk: (payload: RedirectBatchPayload) => http.post<RedirectBatchResult>('/content/redirect/bulk', payload),
  /** 按路径解析跳转（公开接口，命中即累加 hits）。后端 GET /content/redirect/resolve */
  resolve: (path: string) => http.get<RedirectResolveResult>('/content/redirect/resolve', {path}),
  /** 统计。后端 GET /content/redirect/stats */
  stats: () => http.get<RedirectStats>('/content/redirect/stats'),
}
