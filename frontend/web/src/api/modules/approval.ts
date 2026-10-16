/** 内容审批接口（/api/v3/content/approval，content 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface ApprovalStepItem {
  id: number
  record_id: number
  level: number
  approver_id?: number | null
  action?: string | null
  comment?: string | null
  reviewed_at?: string | null
  created_at?: string | null
}

export interface ApprovalRecordItem {
  id: number
  content_type?: string | null
  content_id?: number | null
  applicant_id?: number | null
  current_level: number
  max_level: number
  status?: string | null
  created_at?: string | null
  updated_at?: string | null
  completed_at?: string | null
  steps?: ApprovalStepItem[]
}

export interface ApprovalRecordQuery extends PageQuery {
  content_type?: string
  status?: string
}

export const approvalApi = {
  list: (params?: ApprovalRecordQuery) => http.page<ApprovalRecordItem>('/content/approval/record', params),

  detail: (id: number) => http.get<ApprovalRecordItem>(`/content/approval/record/${id}`),

  create: (data: { content_type?: string; content_id: number; max_level?: number }) =>
    http.post<ApprovalRecordItem>('/content/approval/record', data),

  decide: (id: number, data: { action: 'approve' | 'reject'; comment?: string | null }) =>
    http.post<ApprovalRecordItem>(`/content/approval/record/${id}/decision`, data),

  remove: (id: number) => http.delete<null>(`/content/approval/record/${id}`),
}
