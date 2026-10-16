/** 关注流接口（/api/v3/mobile/feed，mobile 域）
 *
 * 按当前登录用户的**真实**关注关系聚合**已发布**文章（后端复用公开列表的排序：
 * 置顶 → sort_order → 发布时间倒序）。**仅需认证**；关注为空时返回空列表
 * （不会退化成全站文章）。
 */

import type {ArticleItem} from '@/types/content'

import http from '../request'
import type {PageQuery} from '../types'

export interface FeedQuery extends PageQuery {
}

export const feedApi = {
  /** 我的关注流（分页；page_size ≤ 50） */
  list: (params?: FeedQuery) => http.page<ArticleItem>('/mobile/feed', params),
}
