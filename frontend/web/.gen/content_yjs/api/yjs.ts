/** 协同文档接口（/api/v3/content/yjs，content 域）
 *
 * yjs 模块的**持久化面与访问面**：房间只读视图 / 访问权自检 / 协作者 / 版本历史与回滚 /
 * 正文快照落库。字段与后端 `content/yjs/schema.py` 一一对应。
 *
 * 权限码复用 `module_content:collaboration:{view,edit}`（`codes.COLLABORATION_*`）—— 后端
 * yjs 模块刻意不新造权限码，它本就是 content 协作能力的一部分。
 *
 * 实时协同（y-protocols sync + awareness）的 **WebSocket 通道不在这里**：前端用原生
 * `WebSocket` 直连 `/api/v3/content/collaboration/yjs/ws/{document_id}`。本模块与那边的房间
 * 视图共用同一份事实（后端共用同一个 `room_registry`），因此 `listRooms` 与
 * `collaborationApi.listRooms` 返回的是同一批房间。
 */

import http from '../request'
import type {PageQuery} from '../types'

/** 房间状态（后端 `room_state` 纯函数：连接数 <= 0 为 empty，> 10 为 crowded） */
export type RoomState = 'empty' | 'active' | 'crowded'

/** 协作邀请授予的权限（`collaboration_invites.permission`） */
export type InvitePermission = 'view' | 'edit'

/** 访问权的判定来源：文档作者 / 有效协作邀请；无权限时为 null */
export type AccessVia = 'author' | 'invite'

/** 本进程的活跃协同房间（运行时状态，只有连接数，不含文档内容）
 *  字段来源：`schema.RoomOut` */
export interface YjsRoomItem {
  /** 协同文档 = 文章 ID（`RoomOut.document_id`） */
  document_id: number
  /** 本进程内该文档的 WebSocket 连接数（`RoomOut.clients`） */
  clients: number
  /** empty / active / crowded（`RoomOut.state`） */
  state: RoomState
  /** clients > 0（`RoomOut.active`） */
  active: boolean
}

/** `GET /rooms` 的返回体：房间数组 + 计数 + 口径说明
 *  字段来源：`service.rooms()` 的字典（rooms / count / scope） */
export interface YjsRoomsResult {
  rooms: YjsRoomItem[]
  count: number
  /** 口径说明：仅本进程，跨 worker 状态在 Redis（`service.ROOM_SCOPE_NOTE`） */
  scope: string
}

/** 单房间详情：连接数（进程内）+ 版本统计（真表 `article_revisions` / `article_content`）
 *  字段来源：`schema.RoomDetailOut` */
export interface YjsRoomDetail extends YjsRoomItem {
  /** 该文档的修订总数（`article_revisions` 计数） */
  revision_count: number
  /** 最近写入的一条修订的版本号 */
  latest_revision_number: number | null
  /** 最近写入的一条修订的时间 */
  latest_revision_at: string | null
  /** 当前正文（`article_content.content`）字符数 */
  content_chars: number
  /** 当前是否存在正文 */
  has_content: boolean
}

/** 我在某份协同文档上的访问权（结构化返回，无权限也返回 200 + allowed=false）
 *  字段来源：`schema.DocumentAccessOut` */
export interface YjsDocumentAccess {
  document_id: number
  /** 文档标题（`article.title`） */
  title: string | null
  /** 文档作者用户 ID（`article.user`） */
  author_id: number | null
  /** 我是否就是作者 */
  is_author: boolean
  /** 是否可进入该文档的协同编辑（读） */
  allowed: boolean
  /** 是否可写入（作者或 permission=edit 的邀请） */
  can_edit: boolean
  /** author / invite；无权限时为 null */
  via: AccessVia | null
  /** 邀请授予的权限：view / edit；无权限时为 null */
  permission: InvitePermission | null
  /** 判定依据（人类可读） */
  reason: string | null
}

/** 文档作者（协同关系的 owner）
 *  字段来源：`schema.AuthorOut` */
export interface YjsAuthor {
  user_id: number | null
  username: string | null
  /** 固定为 "owner" */
  role: string
  /** 固定为 "author" */
  source: string
  /** 作者恒为 true */
  can_edit: boolean
}

/** 一条指向该文档的协作邀请（真表 `collaboration_invites`，target_type='article'）
 *  字段来源：`schema.InviteCollaboratorOut` */
export interface YjsInviteCollaborator {
  invite_id: number
  /** 邀请码（仅文档作者可见；非作者为 null） */
  invite_code: string | null
  /** view / edit */
  permission: string | null
  creator_id: number | null
  expires_at: string | null
  max_uses: number
  use_count: number
  /** 当前是否仍可用（激活 / 未过期 / 未超次数） */
  usable: boolean
  /** 是否授予写入权限（permission=edit） */
  can_edit: boolean
}

/** 文档的协作者来源：作者 + 仍有效的协作邀请
 *  字段来源：`schema.CollaboratorsOut` */
export interface YjsCollaborators {
  document_id: number
  author: YjsAuthor | null
  invites: YjsInviteCollaborator[]
  invite_count: number
}

/** 版本列表项（不含正文，避免列表返回几百 KB）
 *  字段来源：`schema.RevisionOut` */
export interface YjsRevision {
  id: number
  article_id: number | null
  revision_number: number | null
  title: string | null
  /** 该版本的作者用户 ID（`article_revisions.author_id`） */
  author_id: number | null
  /** 该版本作者用户名（由 `service._author_names` 关联 `users` 得到） */
  author_name: string | null
  change_summary: string | null
  /** 正文 sha256 十六进制摘要（变更检测用） */
  hash_code: string | null
  content_chars: number
  created_at: string | null
}

/** 单个版本详情（含正文；超上限时截断返回并标记）
 *  字段来源：`schema.RevisionDetailOut` */
export interface YjsRevisionDetail extends YjsRevision {
  /** 该版本完整正文（超过 20 万字符时截断） */
  content: string | null
  /** 正文是否被截断 */
  content_is_truncated: boolean
  /** `html_stats` 纯函数的结果（chars / lines / is_empty / has_markup / exceeds_limit） */
  stats: Record<string, unknown> | null
}

/** 保存快照的请求体
 *  字段来源：`schema.SnapshotRequest` */
export interface YjsSnapshotPayload {
  /** 富文本正文的 HTML 快照（完整入库） */
  html: string
  change_summary?: string | null
  /** 正文与最新修订一致时也强制新建一条修订（默认去重跳过） */
  force?: boolean
}

/** 快照结果：saved=false 表示因去重跳过了写入（不是失败）
 *  字段来源：`schema.SnapshotResultOut` */
export interface YjsSnapshotResult {
  document_id: number
  saved: boolean
  /** 新建（或跳过时指向的最新区）修订号 */
  revision_number: number | null
  /** 正文 sha256 */
  content_hash: string | null
  /** `diff_summary` 纯函数的结果 */
  change: Record<string, unknown> | null
  reason: string | null
}

/** 回滚请求体
 *  字段来源：`schema.RestoreRequest` */
export interface YjsRestorePayload {
  change_summary?: string | null
}

/** 回滚结果
 *  字段来源：`schema.RestoreResultOut` */
export interface YjsRestoreResult {
  document_id: number
  /** 被恢复的历史版本号 */
  restored_from: number
  /** 回滚产生的新版本号（= 现有最大 + 1） */
  new_revision_number: number
  content_hash: string
}

export const yjsApi = {
  /** GET /content/yjs/rooms —— 本进程活跃协同房间（需 collaboration:view） */
  listRooms: () => http.get<YjsRoomsResult>('/content/yjs/rooms'),

  /** GET /content/yjs/rooms/{document_id} —— 单房间详情 + 版本统计
   *  （需 collaboration:view + 文档准入） */
  getRoom: (documentId: number, invite?: string | null) =>
    http.get<YjsRoomDetail>(
      `/content/yjs/rooms/${documentId}`,
      invite ? {invite} : undefined,
    ),

  /** GET /content/yjs/document/{document_id}/access —— 我的协同访问权（需 collaboration:view） */
  getAccess: (documentId: number, invite?: string | null) =>
    http.get<YjsDocumentAccess>(
      `/content/yjs/document/${documentId}/access`,
      invite ? {invite} : undefined,
    ),

  /** GET /content/yjs/document/{document_id}/collaborators —— 协作者
   *  （作者 + 有效协作邀请；需 collaboration:view + 文档准入） */
  listCollaborators: (documentId: number, invite?: string | null) =>
    http.get<YjsCollaborators>(
      `/content/yjs/document/${documentId}/collaborators`,
      invite ? {invite} : undefined,
    ),

  /** GET /content/yjs/document/{document_id}/versions —— 版本历史（分页，不含正文）
   *  （需 collaboration:view + 文档准入） */
  listVersions: (documentId: number, params?: PageQuery & { invite?: string | null }) =>
    http.page<YjsRevision>(`/content/yjs/document/${documentId}/versions`, params),

  /** GET /content/yjs/document/{document_id}/version/{revision_number} —— 版本详情（含正文）
   *  （需 collaboration:view + 文档准入） */
  getVersion: (documentId: number, revisionNumber: number, invite?: string | null) =>
    http.get<YjsRevisionDetail>(
      `/content/yjs/document/${documentId}/version/${revisionNumber}`,
      invite ? {invite} : undefined,
    ),

  /** POST /content/yjs/document/{document_id}/snapshot —— 保存正文快照（幂等去重）
   *  （需 collaboration:edit + 写准入：作者或 permission=edit 的邀请码） */
  saveSnapshot: (documentId: number, data: YjsSnapshotPayload, invite?: string | null) =>
    http.post<YjsSnapshotResult>(
      `/content/yjs/document/${documentId}/snapshot`,
      data,
      invite ? {invite} : undefined,
    ),

  /** POST /content/yjs/document/{document_id}/version/{revision_number}/restore —— 回滚到历史版本
   *  （需 collaboration:edit + 写准入；历史不被改写，回滚会追加一条新修订） */
  restoreVersion: (
    documentId: number,
    revisionNumber: number,
    data: YjsRestorePayload,
    invite?: string | null,
  ) =>
    http.post<YjsRestoreResult>(
      `/content/yjs/document/${documentId}/version/${revisionNumber}/restore`,
      data,
      invite ? {invite} : undefined,
    ),
}
