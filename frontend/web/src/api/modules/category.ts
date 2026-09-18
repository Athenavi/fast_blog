/** 分类接口（/api/v3/content/category） */

import http from '../request'

export interface CategoryItem {
  id: number
  name: string
  slug?: string | null
  description?: string | null
  parent_id?: number | null
  sort_order: number
  icon?: string | null
  color?: string | null
  is_visible: boolean
  articles_count: number
  created_at?: string | null
  updated_at?: string | null
  children: CategoryItem[]
}

export interface CategoryPayload {
  name: string
  slug?: string
  description?: string
  parent_id?: number | null
  sort_order?: number
  icon?: string
  color?: string
  is_visible?: boolean
}

export const categoryApi = {
  list: (params?: { is_visible?: boolean; keyword?: string }) =>
    http.page<CategoryItem>('/content/category', params),
  tree: (is_visible?: boolean) =>
    http.get<CategoryItem[]>('/content/category/tree', {is_visible}),
  detail: (id: number) => http.get<CategoryItem>(`/content/category/${id}`),
  create: (data: CategoryPayload) => http.post<CategoryItem>('/content/category', data),
  update: (id: number, data: Partial<CategoryPayload>) =>
    http.put<CategoryItem>(`/content/category/${id}`, data),
  remove: (id: number) => http.delete<null>(`/content/category/${id}`),
  publicList: () => http.page<CategoryItem>('/content/category/public'),
  publicTree: () => http.get<CategoryItem[]>('/content/category/public/tree'),
}
