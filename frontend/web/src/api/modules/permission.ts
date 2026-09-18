/** 权限码接口（/api/v3/system/permission） */

import http from '../request'

export interface CapabilityItem {
  id: number
  code: string
  name: string
  description?: string | null
  resource_type?: string | null
  action?: string | null
  is_active: boolean
}

export interface CapabilityGroup {
  resource_type: string
  capabilities: CapabilityItem[]
}

export interface PermissionCheckResult {
  granted: Record<string, boolean>
  all_granted: boolean
  missing: string[]
}

export const permissionApi = {
  list: (params?: { resource_type?: string; keyword?: string; is_active?: boolean }) =>
    http.page<CapabilityItem>('/system/permission', params),
  grouped: () => http.get<CapabilityGroup[]>('/system/permission/grouped'),
  mine: () => http.get<string[]>('/system/permission/my'),
  check: (codes: string[]) => http.post<PermissionCheckResult>('/system/permission/check', {codes}),
  cacheStats: () => http.get<Record<string, unknown>>('/system/permission/cache-stats'),
  invalidateCache: (user_id?: number) =>
    http.post<null>('/system/permission/cache/invalidate', undefined, {user_id}),
}
