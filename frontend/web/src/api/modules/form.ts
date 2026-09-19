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
}
