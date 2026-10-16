/** 站内通知接口（/api/v3/ops/notification）——全部以当前用户为 recipient */

import http from '../request'
import type {PageQuery, PageResult} from '../types'

export interface NotificationItem {
  id: number
  recipient?: number | null
  type?: string | null
  title?: string | null
  message?: string | null
  is_read: boolean
  read_at?: string | null
  created_at?: string | null
}

export const notificationApi = {
  list: (params?: PageQuery & { unread_only?: boolean }): Promise<PageResult<NotificationItem>> =>
    http.page<NotificationItem>('/ops/notification', params),
  unreadCount: () => http.get<{ unread: number }>('/ops/notification/unread-count'),
  markRead: (id: number) => http.post<null>(`/ops/notification/${id}/read`),
  readAll: () => http.post<{ affected: number }>('/ops/notification/read-all'),
  remove: (id: number) => http.delete<null>(`/ops/notification/${id}`),
  clean: () => http.delete<{ affected: number }>('/ops/notification/clean'),
  /** 批量标记已读（仅本人通知） */
  batchRead: (ids: number[]) =>
    http.post<{ affected: number }>('/ops/notification/batch/read', {ids}),
  /** 批量删除（仅本人通知） */
  batchDelete: (ids: number[]) =>
    http.post<{ affected: number }>('/ops/notification/batch/delete', {ids}),
}
