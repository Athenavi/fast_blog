/** 专家认证接口（`/api/v3/gamification/certification`，gamification 域）
 *
 * 公开只读：`types` / `experts` / `experts/{user_id}`（专家列表**自动排除已过期**的认证）；
 * 「我的」相关端点**仅需认证**；`pending` / `stats` / `review` / `revoke` 需要权限码
 * `module_gamification:certification:{view,review}`。
 *
 * 约定（与后端一致）：
 *  - 状态机 `pending → approved / rejected`，`approved → revoked`；通过后有效期**两年**；
 *  - `id_number`（证件号）**只收不回显** —— 响应里根本没有该字段，前端也不提供输入之外的展示；
 *  - 没有申请过时 `mine()` 返回 `null`（不是 404）。
 */

import http from '../request'
import type {PageQuery} from '../types'

/** 认证状态（后端 STATUSES） */
export type CertificationStatus = 'pending' | 'approved' | 'rejected' | 'revoked'

export interface CertTypeItem {
  code: string
  name: string
}

export interface CertificationDocumentItem {
  id: number
  file_name?: string | null
  file_url: string
  file_type?: string | null
  file_size: number
  created_at?: string | null
}

export interface CertificationItem {
  id: number
  user_id: number
  username?: string | null
  cert_type: string
  /** 认证类型的中文名（服务端由 `cert_type` 映射） */
  cert_type_name?: string | null
  status: CertificationStatus | string
  real_name?: string | null
  organization?: string | null
  position?: string | null
  department?: string | null
  work_years: number
  intro?: string | null
  achievements?: string | null
  portfolio_url?: string | null
  applied_at?: string | null
  reviewed_at?: string | null
  review_comment?: string | null
  issued_at?: string | null
  expires_at?: string | null
  /** 已过有效期（后端按 `expires_at` 现算） */
  is_expired: boolean
  documents: CertificationDocumentItem[]
}

export interface CertificationDocumentPayload {
  file_url: string
  file_name?: string | null
  file_type?: string | null
  file_size?: number
}

/** 申请材料（`id_number` 仅提交，接口不会回显） */
export interface CertificationApplyPayload {
  cert_type: string
  real_name: string
  id_number?: string | null
  phone?: string | null
  email?: string | null
  organization?: string | null
  position?: string | null
  department?: string | null
  work_years?: number
  intro?: string | null
  achievements?: string | null
  portfolio_url?: string | null
  documents?: CertificationDocumentPayload[]
}

/** 修改待审申请（字段全部可选，`cert_type` 也可改） */
export type CertificationUpdatePayload = Partial<CertificationApplyPayload>

export interface CertificationReviewItem {
  id: number
  certification_id: number
  reviewer_id?: number | null
  action?: string | null
  comment?: string | null
  created_at?: string | null
}

export interface CertificationStats {
  total: number
  pending: number
  approved: number
  rejected: number
  revoked: number
  /** 30 天内到期 */
  expiring_soon: number
  expired: number
  by_type: Array<{ cert_type: string; cert_type_name?: string | null; count: number }>
}

export interface ExpertQuery extends PageQuery {
  cert_type?: string
}

export const certificationApi = {
  /** 认证类型（公开） */
  types: () => http.get<CertTypeItem[]>('/gamification/certification/types'),

  /** 认证专家列表（公开，自动排除已过期） */
  experts: (params?: ExpertQuery) =>
    http.page<CertificationItem>('/gamification/certification/experts', params),

  /** 某专家详情（公开） */
  expertDetail: (userId: number) =>
    http.get<CertificationItem>(`/gamification/certification/experts/${userId}`),

  /** 我的认证（仅认证；没有申请过返回 null） */
  mine: () => http.get<CertificationItem | null>('/gamification/certification/mine'),

  /** 提交认证申请（仅认证） */
  apply: (data: CertificationApplyPayload) =>
    http.post<CertificationItem>('/gamification/certification/apply', data),

  /** 修改待审申请（仅认证） */
  updateMine: (data: CertificationUpdatePayload) =>
    http.put<CertificationItem>('/gamification/certification/mine', data),

  /** 撤回申请（仅认证；只有待审可撤回） */
  withdraw: (comment?: string) =>
    http.post<CertificationItem>('/gamification/certification/mine/withdraw', {comment: comment ?? null}),

  /** 待审队列（管理员，分页） */
  pending: (params?: PageQuery) =>
    http.page<CertificationItem>('/gamification/certification/pending', params),

  /** 审核（管理员；`approve=false` 即驳回） */
  review: (certId: number, approve: boolean, comment?: string) =>
    http.post<CertificationItem>(`/gamification/certification/${certId}/review`, {
      approve,
      comment: comment ?? null,
    }),

  /** 撤销已通过的认证（管理员） */
  revoke: (certId: number, comment?: string) =>
    http.post<CertificationItem>(`/gamification/certification/${certId}/revoke`, {
      comment: comment ?? null,
    }),

  /** 认证统计（管理员） */
  stats: () => http.get<CertificationStats>('/gamification/certification/stats'),
}
