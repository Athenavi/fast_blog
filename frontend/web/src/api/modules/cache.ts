/** 缓存管理接口（/api/v3/system/cache，system 域） */

import http from '../request'

/** 单个缓存层级的统计 */
export interface CacheLevelStats {
  hits?: number
  misses?: number
  sets?: number
  deletes?: number
  /** L1 特有：当前缓存条目数 */
  size?: number
  /** L2/L3 特有 */
  enabled?: boolean
  available?: boolean
  errors?: number
}

/** 多级缓存整体统计（对应后端 `multi_level_cache.get_stats()`） */
export interface MultiLevelCacheStats {
  total_requests?: number
  total_hits?: number
  /** 形如 `"93.21%"` */
  hit_rate?: string
  levels?: {
    L1_memory?: CacheLevelStats
    L2_redis?: CacheLevelStats
    L3_file?: CacheLevelStats
  }
  /** 统计失败时后端会返回 error 而不是让页面 500 */
  error?: string
}

export interface CacheStats {
  multi_level: MultiLevelCacheStats
  /** 权限缓存统计（来自 `core/permission/invalidate.py::cache_stats`） */
  permission: Record<string, unknown>
}

export interface CacheWarmupItem {
  key: string
  value: unknown
  ttl?: number | null
}

export const cacheApi = {
  stats: () => http.get<CacheStats>('/system/cache/stats'),
  clear: () => http.post<null>('/system/cache/clear'),
  warmup: (items: CacheWarmupItem[]) =>
    http.post<{ warmed: number }>('/system/cache/warmup', {items}),
  getItem: (key: string) =>
    http.get<{ key: string; value: unknown }>(`/system/cache/items/${encodeURIComponent(key)}`),
  setItem: (key: string, value: unknown, ttl?: number | null) =>
    http.put<{ key: string }>(`/system/cache/items/${encodeURIComponent(key)}`, {value, ttl}),
  removeItem: (key: string) =>
    http.delete<null>(`/system/cache/items/${encodeURIComponent(key)}`),
}
