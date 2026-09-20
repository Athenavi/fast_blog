/**
 * 站内信接口（v3 的 `mobile/message` 域）
 *
 * 前台登录用户之间的私信：会话列表、消息流、发送、已读、删除。
 * 认证与 `mobile.ts` 一致：走 `@/api/request`，自动注入 Bearer token
 * 并在 401 时静默刷新重放。
 */
import http from '../request'
import type {PageQuery} from '../types'

/** 消息方向：`in`=收到，`out`=发出 */
export type MessageDirection = 'in' | 'out'

/** 会话（按联系人聚合：最后一条消息 + 未读数） */
export interface MessageContact {
  peer_id: number
  peer_name: string | null
  last_content: string
  last_at: string | null
  unread: number
}

/** 单条消息 */
export interface MessageItem {
  id: number
  direction: MessageDirection
  content: string
  message_type: string
  attachment_url: string | null
  is_read: boolean
  created_at: string | null
}

/** 发送消息入参（`message_type` 默认 text；附件类消息需带 `attachment_url`） */
export interface MessagePayload {
  recipient_id: number
  content: string
  message_type?: string
  attachment_url?: string | null
  parent_message?: number | null
}

/** 消息流查询参数 */
export interface MessageListQuery extends PageQuery {
  peer_id: number
  page?: number
  page_size?: number
}

export const messageApi = {
  /** 会话列表（每个联系人一条，含未读数） */
  contacts: () => http.get<MessageContact[]>('/mobile/message/contacts'),

  /** 与某人的消息流（分页，按时间正序返回） */
  list: (params: MessageListQuery) => http.page<MessageItem>('/mobile/message/list', params),

  /** 发送消息，返回落库后的消息对象 */
  send: (payload: MessagePayload) => http.post<MessageItem>('/mobile/message', payload),

  /** 标记单条消息已读 */
  markRead: (id: number) => http.post<null>(`/mobile/message/${id}/read`),

  /** 删除单条消息 */
  remove: (id: number) => http.delete<null>(`/mobile/message/${id}`),
}
