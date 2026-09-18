/** 系统设置接口（/api/v3/system/setting） */

import http from '../request'

export interface SettingItem {
  id: number
  setting_key: string
  setting_value?: string | null
  parsed_value?: unknown
  setting_type?: string | null
  description?: string | null
  is_public: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface SettingUpsert {
  setting_key: string
  setting_value?: string | null
  setting_type?: string
  description?: string
  is_public?: boolean
}

export const settingApi = {
  list: (params?: { is_public?: boolean; keyword?: string }) =>
    http.page<SettingItem>('/system/setting', params),
  publicSettings: () => http.get<Record<string, unknown>>('/system/setting/public'),
  detail: (key: string) => http.get<SettingItem>(`/system/setting/${key}`),
  save: (key: string, data: Partial<SettingUpsert>) =>
    http.put<SettingItem>(`/system/setting/${key}`, data),
  batchSave: (items: SettingUpsert[]) => http.put<SettingItem[]>('/system/setting', {items}),
  remove: (key: string) => http.delete<null>(`/system/setting/${key}`),
}
