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
}
