/** 主题接口（/api/v3/extension/theme）—— 数据源是 PluginManager 的当前主题 */

import http from '../request'

export interface ThemeInfo {
  slug?: string | null
  name?: string | null
  version?: string | null
  description?: string | null
  author?: string | null
  screenshot?: string | null
  is_active?: boolean | null

  [key: string]: unknown
}

export interface ThemeConfig {
  slug?: string | null
  settings: Record<string, unknown>
  component_slots: Record<string, unknown>
  settings_schema?: unknown
}

export const themeApi = {
  active: () => http.get<ThemeInfo>('/extension/theme/active'),
  config: () => http.get<ThemeConfig>('/extension/theme/active/config'),
  saveConfig: (settings: Record<string, unknown>, component_slots?: Record<string, unknown>) =>
    http.put<ThemeConfig>('/extension/theme/active/config', {settings, component_slots}),
  schema: () =>
    http.get<{ slug?: string; settings_schema: Record<string, unknown>; slots: string[] }>(
      '/extension/theme/active/schema',
    ),
  contract: () => http.get<{ contract: Record<string, unknown> }>('/extension/theme/active/contract'),
  publicCss: () => http.get<{ slug?: string; css: string; length: number }>(
    '/extension/theme/public/css',
  ),
  publicConfig: () => http.get<ThemeConfig>('/extension/theme/public/config'),
}
