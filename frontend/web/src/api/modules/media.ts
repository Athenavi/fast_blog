/** 媒体库接口（/api/v3/content/media）
 *
 * 另含**封面缓存**端点（公开 GET，返回**图片文件流**，非 `{code,msg,data}` 信封）：
 *   GET /api/v3/content/media/cover/{cover_filename}
 * 供后端 `cover_image_service` 生成的封面缓存文件（`storage/cache/cover`），
 * 文件名格式 `{media_id}_{hash}.{ext}`，公开可读、带强缓存，故：
 *   - 仅用于 `<img :src>` 时用模块导出的 `mediaCoverUrl()` 直接拼 URL（无需 token）；
 *   - 需要文件本体时用 `cover()`，走 `http.raw` + `responseType: 'blob'`
 *     （端点不走统一信封，不能用 `http.get`，其 `unwrap` 会误判 —— 同 `systemExport`）。
 */

import http from '../request'
import type {PageQuery, PageResult} from '../types'
import {API_BASE_URL} from '@/constants'

export interface MediaItem {
  id: number
  user_id?: number | null
  filename?: string | null
  original_filename?: string | null
  file_url?: string | null
  file_size?: number | null
  mime_type?: string | null
  file_type?: string | null
  width?: number | null
  height?: number | null
  duration?: number | null
  thumbnail_url?: string | null
  description?: string | null
  alt_text?: string | null
  is_public: boolean
  download_count: number
  category?: string | null
  tags: string[]
  folder_id?: number | null
  created_at?: string | null
  updated_at?: string | null
}

export interface MediaFolder {
  id: number
  name: string
  parent_id?: number | null
  user_id?: number | null
  description?: string | null
  sort_order: number
  is_public: boolean
  media_count: number
  children: MediaFolder[]
}

export interface MediaQuery extends PageQuery {
  folder_id?: number
  mime_type?: string
  user_id?: number
  is_public?: boolean
  category?: string
}

/** 封面缓存文件名：`{media_id}_{hash}.{ext}`（后端 `cover_image_service` 生成） */
export type MediaCoverFilename = string

/** 封面缓存文件的完整 URL（`/api/v3/content/media/cover/...`），适合直接用于 `<img :src>` */
export function mediaCoverUrl(coverFilename: MediaCoverFilename): string {
  return `${API_BASE_URL}/content/media/cover/${encodeURIComponent(coverFilename)}`
}

export const mediaApi = {
  list: (params?: MediaQuery): Promise<PageResult<MediaItem>> =>
    http.page<MediaItem>('/content/media', params),
  detail: (id: number) => http.get<MediaItem>(`/content/media/${id}`),
  update: (
    id: number,
    data: Partial<{
      description: string
      alt_text: string
      category: string
      tags: string[]
      folder_id: number | null
      is_public: boolean
    }>,
  ) => http.put<MediaItem>(`/content/media/${id}`, data),
  remove: (id: number) => http.delete<null>(`/content/media/${id}`),
  batchDelete: (ids: number[]) =>
    http.post<{ affected: number }>('/content/media/batch/delete', {ids}),
  /** 批量更新：只提交要改的字段；`folder_id: null` 表示移出文件夹 */
  batchUpdate: (payload: { ids: number[]; is_public?: boolean; folder_id?: number | null }) =>
    http.post<{ affected: number }>('/content/media/batch/update', payload),
  upload: (files: File[]) => {
    const form = new FormData()
    files.forEach((file) => form.append('files', file))
    return http.upload<{ files: MediaItem[] }>('/content/media/upload', form)
  },

  // ---- 封面缓存（公开文件流）----
  /** 取封面缓存文件本体（图片 Blob）；端点公开可读、返回文件流而非统一信封 */
  cover: async (coverFilename: MediaCoverFilename): Promise<Blob> => {
    const resp = await http.raw.get<Blob>(
      `/content/media/cover/${encodeURIComponent(coverFilename)}`,
      {responseType: 'blob'},
    )
    return resp.data
  },

  // ---- 文件夹 ----
  folders: () => http.page<MediaFolder>('/content/media/folders'),
  folderTree: () => http.get<MediaFolder[]>('/content/media/folders/tree'),
  createFolder: (data: { name: string; parent_id?: number | null; description?: string }) =>
    http.post<MediaFolder>('/content/media/folders', data),
  updateFolder: (id: number, data: { name?: string; parent_id?: number | null; description?: string }) =>
    http.put<MediaFolder>(`/content/media/folders/${id}`, data),
  removeFolder: (id: number) => http.delete<null>(`/content/media/folders/${id}`),
}
