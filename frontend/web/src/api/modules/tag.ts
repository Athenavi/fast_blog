/** 标签接口（/api/v3/content/tag）—— 标签存在 articles.tags_list（JSON），不建表 */

import http from '../request'
import type {PageQuery} from '../types'

export interface TagItem {
  name: string
  count: number
}

export const tagApi = {
  list: (params?: { limit?: number; min_count?: number; keyword?: string }) =>
    http.page<TagItem>('/content/tag', params),
  /** 标签重命名（目标已存在时等于合并） */
  rename: (old_name: string, new_name: string) =>
    http.post<{ old_name: string; new_name: string; affected: number; merged: boolean }>(
      '/content/tag/rename',
      {old_name, new_name},
    ),
  remove: (name: string) =>
    http.post<{ name: string; affected: number }>('/content/tag/delete', {name}),
  articles: (tag: string, params?: PageQuery & { published_only?: boolean }) =>
    http.page<Record<string, unknown>>(`/content/tag/${encodeURIComponent(tag)}/articles`, params),
  publicArticles: (tag: string, params?: PageQuery) =>
    http.page<Record<string, unknown>>(
      `/content/tag/public/${encodeURIComponent(tag)}/articles`,
      params,
    ),
}
