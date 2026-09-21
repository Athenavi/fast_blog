/**
 * 群聊消息接口（`/api/v3/chat/message`，chat 域）
 *
 * 历史读取与发送走 HTTP；实时收发走原生 WebSocket（由 `wsUrl` 构造连接地址）。
 * 认证与 `message.ts` 一致：走 `@/api/request`，自动注入 Bearer token 并在 401 时静默刷新。
 */
import {STORAGE_TOKEN} from '@/constants'
import {storage} from '@/utils/storage'

import http from '../request'
import type {PageQuery} from '../types'

/** 一条群聊消息（HTTP 列表项与 WS 广播负载共用同一字段集） */
export interface ChatMessageItem {
  id: number
  group_id: number
  user_id: number
  username?: string | null
  /** 撤回（`is_deleted`）时后端置为空串 */
  content: string
  message_type?: string | null
  attachment_url?: string | null
  parent_message?: number | null
  is_deleted: boolean
  created_at?: string | null
}

/** 群内消息查询参数（后端取最新 N 条后按时间升序返回） */
export interface ChatMessageQuery extends PageQuery {
  page?: number
  page_size?: number
}

/** 发送消息入参 */
export interface ChatMessagePayload {
  group_id: number
  content: string
  message_type?: string
  attachment_url?: string | null
  parent_message?: number | null
}

/** 发送后落库返回的消息对象 */
export type ChatMessageSendResult = ChatMessageItem

/** 我加入的群聊（前台聊天页左栏；`GET /chat/message/my-groups`）
 *
 * 只列**本人加入**的群，因此不需要后台的 `module_chat:group:view` 权限。
 */
export interface MyChatGroup {
  id: number
  name?: string | null
  avatar?: string | null
  description?: string | null
  member_count: number
  last_message_at?: string | null
  role?: string | null
}

export const chatMessageApi = {
  /** 我加入的群聊（前台左栏；仅需登录） */
  myGroups: () => http.get<MyChatGroup[]>('/chat/message/my-groups'),

  /** 群内历史消息（分页；`page=1` 即最近一段，返回按时间升序） */
  list: (groupId: number, params?: ChatMessageQuery) =>
    http.page<ChatMessageItem>(`/chat/message/${groupId}`, params),

  /** 发送消息，返回落库后的消息对象 */
  send: (payload: ChatMessagePayload) =>
    http.post<ChatMessageSendResult>('/chat/message', payload),

  /** 撤回本人消息（软删除 + 广播 recall） */
  remove: (messageId: number) => http.delete<null>(`/chat/message/item/${messageId}`),

  /**
   * 构造 WebSocket 连接地址。
   *
   * 浏览器原生 WebSocket **无法自定义请求头**，因此不能沿用 `Authorization: Bearer`；
   * 这里把 token 拼进 query（`?token=`）——后端 `resolve_ws_user` 的第三级回退会读取它
   * （优先级：Cookie `access_token` → 子协议 `bearer.<token>` → query `token`）。
   */
  wsUrl: (groupId: number): string => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const token = storage.get<string>(STORAGE_TOKEN) || ''
    const query = token ? `?token=${encodeURIComponent(token)}` : ''
    return `${proto}//${window.location.host}/api/v3/chat/message/ws/${groupId}${query}`
  },
}
