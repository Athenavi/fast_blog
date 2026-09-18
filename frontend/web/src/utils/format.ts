/** 展示层格式化工具（日期、大小、状态文案） */

import dayjs from 'dayjs'

export function formatDateTime(value?: string | null, fallback = '-'): string {
  if (!value) return fallback
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('YYYY-MM-DD HH:mm:ss') : fallback
}

export function formatDate(value?: string | null, fallback = '-'): string {
  if (!value) return fallback
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed.format('YYYY-MM-DD') : fallback
}

export function formatFileSize(bytes?: number | null): string {
  if (bytes === null || bytes === undefined) return '-'
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB', 'TB']
  let size = bytes / 1024
  let index = 0
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024
    index += 1
  }
  return `${size.toFixed(2)} ${units[index]}`
}

type TagType = 'success' | 'info' | 'warning' | 'danger' | 'primary'

/** 文章状态：-1 删除 / 0 草稿 / 1 已发布（与后端 articles.status 一致）。
 * 纯 util 不硬编码中文，只返回 i18n key，由调用方用 t() 渲染。 */
export type ArticleStatusKey =
  'common.published'
  | 'common.draft'
  | 'admin.dashboard.deleted'
  | 'admin.dashboard.unknown'

export function articleStatusKey(status?: number | null): ArticleStatusKey {
  if (status === 1) return 'common.published'
  if (status === 0) return 'common.draft'
  if (status === -1) return 'admin.dashboard.deleted'
  return 'admin.dashboard.unknown'
}

export function articleStatusTag(status?: number | null): TagType {
  if (status === 1) return 'success'
  if (status === 0) return 'warning'
  if (status === -1) return 'danger'
  return 'info'
}

/** 页面状态：0 草稿 / 1 已发布 */
export function pageStatusKey(status?: number | null): 'common.published' | 'common.draft' {
  return status === 1 ? 'common.published' : 'common.draft'
}

export function pageStatusTag(status?: number | null): TagType {
  return status === 1 ? 'success' : 'warning'
}

/** 截断长文本，避免表格被撑开 */
export function truncate(value?: string | null, max = 60): string {
  if (!value) return '-'
  return value.length > max ? `${value.slice(0, max)}…` : value
}

/** 逗号分隔的标签串 → 数组（后端 media.tags 是逗号分隔字符串） */
export function splitTags(value?: string | string[] | null): string[] {
  if (!value) return []
  if (Array.isArray(value)) return value
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}
