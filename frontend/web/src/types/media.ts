/** 媒体预览相关类型 */

export interface MediaPreviewItem {
  id: number
  url?: string | null
  name?: string | null
  mimeType?: string | null
  size?: number | null
  createdAt?: string | null
}

/** 离线下载候选项 */
export interface OfflineCandidate {
  id: number
  url?: string | null
  name?: string | null
  size?: number | null
}
