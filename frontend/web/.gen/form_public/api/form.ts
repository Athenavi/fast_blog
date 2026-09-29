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

/** 公开字段（GET /marketing/form/public/{slug} 的 fields 元素，对齐后端 FormFieldOut） */
export interface FormPublicField {
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
  created_at?: string | null
  updated_at?: string | null
}

/** 公开表单定义（后端 FormOut 叠加 fields） */
export interface FormPublicDetail extends FormItem {
  fields: FormPublicField[]
}

/** 匿名提交回执（后端 public_submit 返回值） */
export interface FormPublicSubmitResult {
  accepted: boolean
  stored: boolean
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

  /** 公开：取已发布表单定义与激活字段（无需登录） */
  publicForm: (slug: string) => http.get<FormPublicDetail>(`/marketing/form/public/${slug}`),

  /**
   * 公开：匿名提交。
   * 请求体为 `{data: {字段 label: 值}}`——后端按字段 label 从 data 中取值，
   * 因此调用方必须以 label 作为键。
   */
  publicSubmit: (slug: string, data: Record<string, unknown>) =>
    http.post<FormPublicSubmitResult>(`/marketing/form/public/${slug}/submit`, {data}),
}
