/** 协作接口（/api/v3/content/collaboration，content 域）
 *
 * 五块：workspace（工作区）/ member（成员）/ task（任务）/ comment（团队评论）/ invite（邀请），
 * 外加 yjs 的 HTTP 部分（房间列表、保存快照）。
 * 实时协同的 **WebSocket 通道不在这里** —— 前端用原生 `WebSocket` 直连
 * `/api/v3/content/collaboration/yjs/ws/{document_id}`（token 走子协议 `bearer.<token>`，
 * 避免进访问日志）。
 */

import http from '../request'
import type {PageQuery} from '../types'

export type MemberRole = 'viewer' | 'editor' | 'admin' | 'owner'
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled'
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent'
export type InviteTarget = 'article' | 'workspace'

export interface WorkspaceItem {
  id: number
  name?: string | null
  slug?: string | null
  description?: string | null
  owner_id?: number | null
  is_active: boolean
  member_count: number
  /** 我在该工作区的角色（列表 / 详情接口会带） */
  role?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface WorkspacePayload {
  name?: string
  slug?: string | null
  description?: string | null
  is_active?: boolean
}

export interface MemberItem {
  id: number
  workspace_id?: number | null
  user_id?: number | null
  role?: string | null
  joined_at?: string | null
  is_active: boolean
  username?: string | null
  email?: string | null
}

export interface TaskItem {
  id: number
  workspace_id?: number | null
  title?: string | null
  description?: string | null
  status?: string | null
  priority?: string | null
  assigned_to?: number | null
  created_by?: number | null
  due_date?: string | null
  completed_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface TaskPayload {
  title?: string
  description?: string | null
  status?: string
  priority?: string
  assigned_to?: number | null
  due_date?: string | null
}

export interface TeamCommentItem {
  id: number
  content_type?: string | null
  content_id?: number | null
  author_id?: number | null
  author_name?: string | null
  parent_id?: number | null
  text?: string | null
  mentions?: number[] | null
  is_resolved: boolean
  resolved_by?: number | null
  resolved_at?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface CommentPayload {
  content_type: string
  content_id: number
  text: string
  parent_id?: number | null
  mentions?: number[] | null
}

export interface InviteItem {
  id: number
  invite_code?: string | null
  target_type?: string | null
  target_id?: number | null
  permission?: string | null
  creator_id?: number | null
  expires_at?: string | null
  max_uses: number
  use_count: number
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface InvitePayload {
  target_type: InviteTarget
  target_id: number
  permission?: string
  expire_hours?: number
  max_uses?: number
}

export interface WorkspaceRoom {
  document_id: number
  clients: number
}

export const collaborationApi = {
  // ---- 工作区 ----
  listWorkspaces: () => http.get<WorkspaceItem[]>('/content/collaboration/workspace'),

  createWorkspace: (data: WorkspacePayload) =>
    http.post<WorkspaceItem>('/content/collaboration/workspace', data),

  getWorkspace: (id: number) =>
    http.get<WorkspaceItem>(`/content/collaboration/workspace/${id}`),

  getWorkspaceBySlug: (slug: string) =>
    http.get<WorkspaceItem>(`/content/collaboration/workspace/by-slug/${slug}`),

  updateWorkspace: (id: number, data: WorkspacePayload) =>
    http.put<WorkspaceItem>(`/content/collaboration/workspace/${id}`, data),

  removeWorkspace: (id: number) => http.delete<null>(`/content/collaboration/workspace/${id}`),

  // ---- 成员 ----
  listMembers: (workspaceId: number) =>
    http.get<MemberItem[]>(`/content/collaboration/workspace/${workspaceId}/member`),

  addMember: (workspaceId: number, data: { user_id: number; role: MemberRole }) =>
    http.post<MemberItem>(`/content/collaboration/workspace/${workspaceId}/member`, data),

  updateMemberRole: (workspaceId: number, userId: number, role: MemberRole) =>
    http.put<MemberItem>(`/content/collaboration/workspace/${workspaceId}/member/${userId}`, {
      role,
    }),

  removeMember: (workspaceId: number, userId: number) =>
    http.delete<null>(`/content/collaboration/workspace/${workspaceId}/member/${userId}`),

  // ---- 任务 ----
  listTasks: (workspaceId: number, params?: PageQuery & { status?: string; assigned_to?: number }) =>
    http.page<TaskItem>(`/content/collaboration/workspace/${workspaceId}/task`, params),

  createTask: (workspaceId: number, data: TaskPayload) =>
    http.post<TaskItem>(`/content/collaboration/workspace/${workspaceId}/task`, data),

  updateTask: (taskId: number, data: TaskPayload) =>
    http.put<TaskItem>(`/content/collaboration/task/${taskId}`, data),

  removeTask: (taskId: number) => http.delete<null>(`/content/collaboration/task/${taskId}`),

  // ---- 团队评论 ----
  listComments: (
    params: PageQuery & { content_type: string; content_id: number; include_resolved?: boolean },
  ) => http.page<TeamCommentItem>('/content/collaboration/comment', params),

  listMentions: (params?: { limit?: number; unread_only?: boolean }) =>
    http.get<TeamCommentItem[]>('/content/collaboration/comment/mentions', params),

  commentStatistics: (contentType?: string) =>
    http.get<{
      total_comments: number
      resolved_comments: number
      unresolved_comments: number
      by_author: { author_id: number; count: number }[]
    }>('/content/collaboration/comment/statistics', contentType ? {content_type: contentType} : undefined),

  createComment: (data: CommentPayload) =>
    http.post<TeamCommentItem>('/content/collaboration/comment', data),

  updateComment: (id: number, text: string) =>
    http.put<TeamCommentItem>(`/content/collaboration/comment/${id}`, {text}),

  removeComment: (id: number) => http.delete<{ deleted: number }>(`/content/collaboration/comment/${id}`),

  resolveComment: (id: number) =>
    http.post<TeamCommentItem>(`/content/collaboration/comment/${id}/resolve`),

  // ---- 协作邀请 ----
  listInvites: (params?: PageQuery & { target_type?: string; target_id?: number }) =>
    http.page<InviteItem>('/content/collaboration/invite', params),

  createInvite: (data: InvitePayload) =>
    http.post<InviteItem>('/content/collaboration/invite', data),

  acceptInvite: (inviteCode: string) =>
    http.post<Record<string, unknown>>('/content/collaboration/invite/accept', {
      invite_code: inviteCode,
    }),

  getInvite: (id: number) => http.get<InviteItem>(`/content/collaboration/invite/${id}`),

  revokeInvite: (id: number) => http.delete<null>(`/content/collaboration/invite/${id}`),

  // ---- yjs（HTTP 部分；实时通道用原生 WebSocket） ----
  listRooms: () =>
    http.get<{ rooms: WorkspaceRoom[]; count: number }>('/content/collaboration/yjs/rooms'),

  saveDocument: (
    documentId: number,
    data: { html: string; change_summary?: string | null },
    invite?: string | null,
  ) =>
    http.post<{ document_id: number; revision_number: number }>(
      `/content/collaboration/yjs/document/${documentId}/save`,
      data,
      invite ? {invite} : undefined,
    ),
}
