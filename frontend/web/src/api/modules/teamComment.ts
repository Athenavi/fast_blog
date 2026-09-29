/** 团队内部评论接口（/api/v3/content/team_comment，content 域）
 *
 * 对齐后端 v3 模块 `content/team_comment`（controller.py 为准）：
 *   - GET    /content/team_comment               按内容查评论树（顶层分页）
 *   - POST   /content/team_comment               发表评论
 *   - GET    /content/team_comment/{id}          评论详情
 *   - PUT    /content/team_comment/{id}          修改评论
 *   - DELETE /content/team_comment/{id}          删除评论（级联子孙）
 *   - POST   /content/team_comment/{id}/resolve  标记已解决
 *   - GET    /content/team_comment/mentions      @ 到我的评论（静态路径）
 *   - GET    /content/team_comment/statistics    评论统计（静态路径）
 *
 * 权限码复用 `module_content:collaboration:{view,create,edit,delete}`（`codes.COLLABORATION_*`）。
 * 写操作（修改 / 删除 / 解决）后端在 service 层额外要求「评论作者或管理员」，前端只做提示。
 *
 * 与 `modules/collaboration.ts` 的团队评论方法区分：后者走 `content/collaboration/comment`
 * 旧前缀；本模块是 v3 `content/team_comment` 独立入口，命名一律带 `TeamComment` 前缀，
 * 不复用 `TeamCommentItem`（那是 collaboration 模块的类型）。
 */

import http from '../request'
import type {PageQuery, PageResult} from '../types'

/** 按作者的评论计数（来源：schema.AuthorCountOut） */
export interface TeamCommentAuthorCount {
  author_id: number
  count: number
}

/** 团队评论统计（来源：schema.TeamCommentStatisticsOut） */
export interface TeamCommentStatistics {
  total_comments: number
  resolved_comments: number
  unresolved_comments: number
  by_author: TeamCommentAuthorCount[]
}

/** 单条团队评论 / 线程节点（来源：schema.TeamCommentOut）
 *
 * `mentions` 与 `children` 后端保证非空数组（`Field(default_factory=list)`）；
 * `children` 仅在「按内容查评论树」接口里被填充为子回复（详见 service.build_threads）。
 */
export interface TeamCommentOut {
  id: number
  content_type?: string | null
  content_id?: number | null
  author_id?: number | null
  author_name?: string | null
  parent_id?: number | null
  text?: string | null
  mentions: number[]
  is_resolved: boolean
  resolved_by?: number | null
  resolved_at?: string | null
  created_at?: string | null
  updated_at?: string | null
  children: TeamCommentOut[]
}

/** 发表评论请求体（来源：schema.TeamCommentCreate；text 入库前后端会 html.escape） */
export interface TeamCommentCreatePayload {
  content_type: string
  content_id: number
  text: string
  parent_id?: number | null
  mentions?: number[] | null
}

/** 修改评论请求体（来源：schema.TeamCommentUpdate，仅正文） */
export interface TeamCommentUpdatePayload {
  text: string
}

/** 列表查询参数（来源：controller.list_team_comments 的 Query 声明） */
export interface TeamCommentListQuery extends PageQuery {
  content_type: string
  content_id?: number
  include_resolved: boolean
}

/** @ 到我的评论查询参数（来源：controller.list_my_mentions；
 *  `unread_only` 后端语义 = 未解决，既有表无独立已读状态）。
 *  用 `type` 别名以便赋值给 `http.get` 的 `Record<string, unknown>` 形参。 */
export type TeamCommentMentionsQuery = {
  limit?: number
  unread_only?: boolean
}

/** 统计查询参数（来源：controller.comment_statistics 的 Query 声明）。同上的 `type` 别名。 */
export type TeamCommentStatisticsQuery = {
  content_type?: string
  content_id?: number
}

export const teamCommentApi = {
  /** GET /content/team_comment —— 按内容查评论树（顶层分页，子回复随行返回） */
  list: (params: TeamCommentListQuery): Promise<PageResult<TeamCommentOut>> =>
    http.page<TeamCommentOut>('/content/team_comment', params),

  /** GET /content/team_comment/{id} —— 单条评论详情 */
  detail: (id: number): Promise<TeamCommentOut> =>
    http.get<TeamCommentOut>(`/content/team_comment/${id}`),

  /** POST /content/team_comment —— 发表评论 */
  create: (data: TeamCommentCreatePayload): Promise<TeamCommentOut> =>
    http.post<TeamCommentOut>('/content/team_comment', data),

  /** PUT /content/team_comment/{id} —— 修改评论正文 */
  update: (id: number, data: TeamCommentUpdatePayload): Promise<TeamCommentOut> =>
    http.put<TeamCommentOut>(`/content/team_comment/${id}`, data),

  /** DELETE /content/team_comment/{id} —— 删除评论（级联子孙，返回实际删除条数） */
  remove: (id: number): Promise<{ deleted: number }> =>
    http.delete<{ deleted: number }>(`/content/team_comment/${id}`),

  /** POST /content/team_comment/{id}/resolve —— 标记已解决 */
  resolve: (id: number): Promise<TeamCommentOut> =>
    http.post<TeamCommentOut>(`/content/team_comment/${id}/resolve`),

  /** GET /content/team_comment/mentions —— @ 到我的评论（静态路径，先于 /{id} 注册） */
  mentions: (params?: TeamCommentMentionsQuery): Promise<TeamCommentOut[]> =>
    http.get<TeamCommentOut[]>('/content/team_comment/mentions', params),

  /** GET /content/team_comment/statistics —— 评论统计（静态路径） */
  statistics: (params?: TeamCommentStatisticsQuery): Promise<TeamCommentStatistics> =>
    http.get<TeamCommentStatistics>('/content/team_comment/statistics', params),
}
