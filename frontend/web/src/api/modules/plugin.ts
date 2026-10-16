/** 插件接口（/api/v3/extension/plugin）
 *
 * 危险操作（install / activate / deactivate / uninstall）后端要求 `confirm=true`，
 * 前端在 UI 上做二次确认后必须显式传该参数。
 */

import http from '../request'

export interface PluginItem {
  slug?: string | null
  name?: string | null
  version?: string | null
  description?: string | null
  author?: string | null
  category?: string | null
  icon?: string | null
  is_active?: boolean | null
  is_installed?: boolean | null
  capabilities?: string[]
  tags?: string[]
  settings?: Record<string, unknown>
  settings_schema?: unknown

  [key: string]: unknown
}

export interface PluginAction {
  slug: string
  action: string
  success: boolean
  detail?: string | null
}

export const pluginApi = {
  list: () => http.page<PluginItem>('/extension/plugin'),
  scan: () =>
    http.get<{ new_plugins: string[]; count: number }>('/extension/plugin/scan'),
  detail: (slug: string) => http.get<PluginItem>(`/extension/plugin/${slug}`),
  settings: (slug: string) =>
    http.get<{ slug: string; settings: Record<string, unknown>; settings_schema: unknown }>(
      `/extension/plugin/${slug}/settings`,
    ),
  saveSettings: (slug: string, settings: Record<string, unknown>) =>
    http.put<{ slug: string; settings: Record<string, unknown> }>(
      `/extension/plugin/${slug}/settings`,
      {settings},
    ),
  /** 以下四个都是危险操作，必须 confirm=true */
  install: (slug: string) =>
    http.post<PluginAction>(`/extension/plugin/${slug}/install`, undefined, {confirm: true}),
  activate: (slug: string) =>
    http.post<PluginAction>(`/extension/plugin/${slug}/activate`, undefined, {confirm: true}),
  deactivate: (slug: string) =>
    http.post<PluginAction>(`/extension/plugin/${slug}/deactivate`, undefined, {confirm: true}),
  uninstall: (slug: string) =>
    http.delete<PluginAction>(`/extension/plugin/${slug}`, {confirm: true}),
}
