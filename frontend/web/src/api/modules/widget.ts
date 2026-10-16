/** 小部件接口（/api/v3/extension/widget） */

import http from '../request'

export interface WidgetItem {
  id: number
  widget_type: string
  area: string
  title?: string | null
  config?: Record<string, unknown> | null
  order_index: number
  is_active: boolean
  conditions?: Record<string, unknown> | null
  created_at?: string | null
  updated_at?: string | null
}

export interface WidgetPayload {
  widget_type: string
  area: string
  title?: string
  config?: Record<string, unknown>
  order_index?: number
  is_active?: boolean
  conditions?: Record<string, unknown>
}

export const widgetApi = {
  list: (params?: { area?: string; widget_type?: string; is_active?: boolean }) =>
    http.page<WidgetItem>('/extension/widget', params),
  detail: (id: number) => http.get<WidgetItem>(`/extension/widget/${id}`),
  create: (data: WidgetPayload) => http.post<WidgetItem>('/extension/widget', data),
  update: (id: number, data: Partial<WidgetPayload>) =>
    http.put<WidgetItem>(`/extension/widget/${id}`, data),
  toggle: (id: number, is_active: boolean) =>
    http.patch<WidgetItem>(`/extension/widget/${id}/toggle`, {is_active}),
  remove: (id: number) => http.delete<null>(`/extension/widget/${id}`),
  reorder: (items: Array<{ id: number; order_index: number }>) =>
    http.post<{ affected: number }>('/extension/widget/reorder', {items}),
  types: () => http.get<Array<Record<string, unknown>>>('/extension/widget/types'),
  areas: () => http.get<Array<Record<string, unknown>>>('/extension/widget/areas'),
  publicByArea: (area: string) => http.get<WidgetItem[]>(`/extension/widget/public/area/${area}`),
}
