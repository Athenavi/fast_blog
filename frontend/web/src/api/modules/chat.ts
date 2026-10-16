/** 群聊管理接口（/api/v3/chat/group，chat 域） */

import http from '../request'
import type {PageQuery} from '../types'

export interface ChatGroupItem {
  id: number
  name?: string | null
  description?: string | null
  avatar?: string | null
  creator?: number | null
  member_count: number
  last_message_at?: string | null
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface ChatGroupQuery extends PageQuery {
  is_active?: boolean
}

export interface ChatGroupPayload {
  name: string
  description?: string | null
  avatar?: string | null
  creator: number
  is_active?: boolean
}

export interface ChatMemberItem {
  id: number
  group: number
  user: number
  role?: string | null
  joined_at?: string | null
  last_read_at?: string | null
  is_muted: boolean
}

export interface ChatMemberAddPayload {
  user_id: number
  role?: string
}

export interface ChatMemberUpdatePayload {
  role?: string
  is_muted?: boolean
}

export const chatApi = {
  listGroups: (params?: ChatGroupQuery) => http.page<ChatGroupItem>('/chat/group', params),

  createGroup: (data: ChatGroupPayload) => http.post<ChatGroupItem>('/chat/group', data),

  updateGroup: (id: number, data: Partial<ChatGroupPayload>) =>
    http.put<ChatGroupItem>(`/chat/group/${id}`, data),

  removeGroup: (id: number) => http.delete<null>(`/chat/group/${id}`),

  listMembers: (groupId: number, params?: PageQuery) =>
    http.page<ChatMemberItem>(`/chat/group/${groupId}/member`, params),

  addMember: (groupId: number, data: ChatMemberAddPayload) =>
    http.post<ChatMemberItem>(`/chat/group/${groupId}/member`, data),

  updateMember: (memberId: number, data: ChatMemberUpdatePayload) =>
    http.put<ChatMemberItem>(`/chat/group/member/${memberId}`, data),

  removeMember: (memberId: number) => http.delete<null>(`/chat/group/member/${memberId}`),
}
