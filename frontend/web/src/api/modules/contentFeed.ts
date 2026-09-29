/** 动态流接口（/api/v3/content/feed，content 域）
 *
 * 与 `mobile/feed`（关注流，**不是**同一个模块）的区别：
 *  - `mobile/feed`：只按登录用户的关注关系聚合**已发布文章**（一页文章）；
 *  - `content/feed`（本模块）：把 `articles`（关注的人发帖）/ `article_likes`
 *    （关注的人点赞）/ `comments`（关注的人评论）三类事件用 `UNION ALL`
 *    聚合成**统一事件流**，在库内排序分页。
 *
 * 端点与鉴权：
 *   GET /content/feed/timeline     关注时间线（**仅需认证**）
 *   GET /content/feed/discover     发现流（**公开**）
 *   GET /content/feed/user/{id}    某用户公开动态（**公开**）
 *   GET /content/feed/stats        我的流概览（**仅需认证**）
 *
 * 四个端点均无权限码：读接口不改数据，`user_id` 一律由后端从登录态或路径取。
 */

import http from '../request'
import type {PageQuery} from '../types'

/** 事件类型（与后端 service.EVENT_TYPES 一致） */
export type FeedEventType = 'article' | 'like' | 'comment'

/** 事件流里内联的文章摘要（后端 FeedService._article_out 的字段） */
export interface FeedArticle {
  id: number
  title: string
  slug: string | null
  excerpt: string | null
  /** 作者（发布者）用户 id */
  user: number | null
  /** 分类 id */
  category: number | null
  views: number
  likes: number
  published_at: string | null
}

/** 一条动态事件（时间线 / 发现 / 用户动态的统一结构） */
export interface FeedEvent {
  type: FeedEventType
  /** 事件时间（ISO 字符串；后端可能为 null） */
  at: string | null
  /** 触发者用户 id（新文章=作者，点赞=点赞者，评论=评论者） */
  actor_id: number | null
  /** 评论事件的正文摘要（后端截取至 120 字；其它类型为 null） */
  extra: string | null
  /** 关联文章；文章不存在时为 null */
  article: FeedArticle | null
}

/** 事件流查询参数（timeline / discover / user 共用） */
export interface FeedStreamQuery extends PageQuery {
  /** 逗号分隔的事件类型（仅 timeline 生效）：`article` / `like` / `comment`；留空=全部 */
  event_types?: string
  /** true 时把全站最新点赞 / 评论也纳入（仅 discover 生效；默认只看新文章） */
  include_interactions?: boolean
}

/** 我的流概览（stats） */
export interface FeedStats {
  user_id: number
  /** 我关注的人数 */
  following: number
  /** 时间线事件总数 */
  timeline_events: number
  /** 各事件类型的计数，如 `{article: 3, like: 5}` */
  by_type: Record<string, number>
  /** 关注为空时后端给的提示文案（非空时才有） */
  hint?: string
}

export const contentFeedApi = {
  /** 关注时间线（登录）：关注的人产生的文章 / 点赞 / 评论，按时间倒序 */
  timeline: (params?: FeedStreamQuery) => http.page<FeedEvent>('/content/feed/timeline', params),

  /** 发现流（公开）：全站最新动态；`include_interactions` 打开后含最新点赞 / 评论 */
  discover: (params?: FeedStreamQuery) => http.page<FeedEvent>('/content/feed/discover', params),

  /** 某用户的公开动态（公开）：TA 发布的文章 + 通过审核的评论 */
  userFeed: (userId: number, params?: FeedStreamQuery) =>
    http.page<FeedEvent>(`/content/feed/user/${userId}`, params),

  /** 我的流概览（登录）：关注数 / 时间线事件数 / 各类型分布 */
  stats: () => http.get<FeedStats>('/content/feed/stats'),
}
