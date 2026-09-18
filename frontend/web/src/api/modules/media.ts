/** 媒体库接口（/api/v3/content/media） */

import http from '../request'
import type {PageQuery, PageResult} from '../types'

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
  upload: (files: File[]) => {
    const form = new FormData()
    files.forEach((file) => form.append('files', file))
    return http.upload<{ files: MediaItem[] }>('/content/media/upload', form)
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
