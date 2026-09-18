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

/** 文章状态：-1 删除 / 0 草稿 / 1 已发布（与后端 articles.status 一致） */
export function articleStatusText(status?: number | null): string {
  if (status === 1) return '已发布'
  if (status === 0) return '草稿'
  if (status === -1) return '已删除'
  return '未知'
}

export function articleStatusTag(status?: number | null): TagType {
  if (status === 1) return 'success'
  if (status === 0) return 'warning'
  if (status === -1) return 'danger'
  return 'info'
}

/** 页面状态：0 草稿 / 1 已发布 */
export function pageStatusText(status?: number | null): string {
  return status === 1 ? '已发布' : '草稿'
}

export function pageStatusTag(status?: number | null): TagType {
  return status === 1 ? 'success' : 'warning'
}

export function boolText(value?: boolean | null, trueText = '是', falseText = '否'): string {
  return value ? trueText : falseText
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
