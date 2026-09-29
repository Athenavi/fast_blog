/** 表单构建器接口（/api/v3/marketing/form，marketing 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface FormItem {
  id: number
  title?: string | null
  slug?: string | null
  description?: string | null
  status?: string | null
  submit_message?: string | null
  email_notification: boolean
  notification_email?: string | null
  store_submissions: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface FormPayload {
  title: string
  slug?: string
  description?: string | null
  status?: string
  submit_message?: string | null
  email_notification?: boolean
  notification_email?: string | null
  store_submissions?: boolean
}

export interface FormFieldItem {
  id: number
  form_id: number
  label?: string | null
  field_type?: string | null
  placeholder?: string | null
  help_text?: string | null
  required: boolean
  options?: string | null
  validation_rules?: string | null
  default_value?: string | null
  order_index: number
  is_active: boolean
}

export interface FormFieldPayload {
  label: string
  field_type?: string
  placeholder?: string | null
  help_text?: string | null
  required?: boolean
  options?: string | null
  validation_rules?: string | null
  default_value?: string | null
  order_index?: number
  is_active?: boolean
}

export interface FormSubmissionItem {
  id: number
  form_id: number
  data?: Record<string, unknown> | null
  ip_address?: string | null
  user_agent?: string | null
  user_id?: number | null
  status?: string | null
  created_at?: string | null
}

/** 公开表单定义（`GET /marketing/form/public/{slug}`，无需鉴权）
 *
 * 后端只回 `status=published` 的表单，`fields` 只含 `is_active=True` 的激活字段。
 */
export interface FormPublicDetail extends FormItem {
  fields: FormFieldItem[]
}

/** 匿名提交入参：`data` 的键是字段的 `label`（与后端 `service.public_submit` 的取值一致） */
export interface FormPublicSubmitPayload {
  data: Record<string, unknown>
}

/** 匿名提交回执：`store_submissions=false` 时只回执不落库（`stored=false`） */
export interface FormPublicSubmitResult {
  accepted: boolean
  stored?: boolean
  submission_id?: number
}

export const formApi = {
  list: (params?: PageQuery) => http.page<FormItem>('/marketing/form', params),

  create: (data: FormPayload) => http.post<FormItem>('/marketing/form', data),

  update: (id: number, data: Partial<FormPayload>) => http.put<FormItem>(`/marketing/form/${id}`, data),

  remove: (id: number) => http.delete<null>(`/marketing/form/${id}`),

  fields: (formId: number) => http.get<FormFieldItem[]>(`/marketing/form/${formId}/field`),

  createField: (formId: number, data: FormFieldPayload) =>
    http.post<FormFieldItem>(`/marketing/form/${formId}/field`, data),

  updateField: (id: number, data: Partial<FormFieldPayload>) =>
    http.put<FormFieldItem>(`/marketing/form/field/${id}`, data),

  removeField: (id: number) => http.delete<null>(`/marketing/form/field/${id}`),

  submissions: (params?: PageQuery & { form_id?: number }) =>
    http.page<FormSubmissionItem>('/marketing/form/submission', params),

  removeSubmission: (id: number) => http.delete<null>(`/marketing/form/submission/${id}`),

  /** 公开：取已发布表单的定义（含激活字段），前台渲染用
   *
   * 路径参数是表单 `slug`（非 id，见后端 `controller.public_form`）。
   */
  publicDetail: (slug: string) =>
    http.get<FormPublicDetail>(`/marketing/form/public/${encodeURIComponent(slug)}`),

  /** 公开：匿名提交（`data` 的键为字段 `label`） */
  publicSubmit: (slug: string, payload: FormPublicSubmitPayload) =>
    http.post<FormPublicSubmitResult>(
      `/marketing/form/public/${encodeURIComponent(slug)}/submit`,
      payload,
    ),
}
