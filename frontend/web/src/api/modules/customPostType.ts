/** 自定义内容类型接口（/api/v3/content/custom-post-type，content 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface CustomPostTypeItem {
  id: number
  name?: string | null
  slug?: string | null
  description?: string | null
  supports?: string | null
  has_archive: boolean
  menu_icon?: string | null
  menu_position?: number
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
  /** 字段定义（JSON 字符串，形如 [{"key":"price","type":"number","label":"价格","required":true}]） */
  fields?: string | null
}

/** 字段定义条目（与后端 `field_spec.py` 规范化后的结构一致）
 *
 * 支持的类型：text / textarea / richtext / number / boolean / select / date / url / email / json
 */
export interface CustomFieldEntry {
  key: string
  type: string
  label: string
  required?: boolean
  /** select 的候选项 */
  options?: string[]
  /** select 是否多选（多选值以 JSON 数组存） */
  multiple?: boolean
  min?: number | null
  max?: number | null
  /** 关联目标的语义提示（如 article / media） */
  target?: string
  help?: string

  [key: string]: unknown
}

/** 字段值读写结果：`values` 为 {字段 key: 值}，未填字段按定义补 null */
export interface CustomFieldValues {
  type_id: number
  content_id: number
  values: Record<string, unknown>
  updated?: string[]
}

export interface CustomPostTypePayload {
  name: string
  slug?: string
  description?: string | null
  supports?: string | null
  has_archive?: boolean
  menu_icon?: string | null
  menu_position?: number
  is_active?: boolean
}

export const customPostTypeApi = {
  list: (params?: PageQuery) =>
    http.page<CustomPostTypeItem>('/content/custom-post-type', params),

  create: (data: CustomPostTypePayload) =>
    http.post<CustomPostTypeItem>('/content/custom-post-type', data),

  update: (id: number, data: Partial<CustomPostTypePayload>) =>
    http.put<CustomPostTypeItem>(`/content/custom-post-type/${id}`, data),

  remove: (id: number) => http.delete<null>(`/content/custom-post-type/${id}`),
  /** 读取某内容实例的字段值（未填字段按定义补 null） */
  getValues: (typeId: number, contentId: number) =>
    http.get<CustomFieldValues>(`/content/custom-post-type/${typeId}/values/${contentId}`),
  /** 写入字段值：**全量语义** —— 必填缺失、类型不符、含未定义字段名都会被后端拒绝（400） */
  setValues: (typeId: number, contentId: number, values: Record<string, unknown>) =>
    http.put<CustomFieldValues>(`/content/custom-post-type/${typeId}/values/${contentId}`, {values}),
}
